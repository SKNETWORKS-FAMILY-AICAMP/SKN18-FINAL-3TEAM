"""
Path Extractor & Evidence Aggregator Node (통합)

Parallel Knowledge Retrieval의 5개 Thread 결과에서 경로 추출 및 근거 통합을 한 번에 수행
- Thread별로 서로 다른 경로 추출 로직 적용
- 개선된 점수 체계로 관련성 평가
- 하이브리드 방식: 점수 기반 선별 → LLM 기반 최종 선택 (15개)
"""

import os
import json
from backend.langgraph_fuseki.state import GraphState
from backend.langgraph_fuseki.config import (
    THREAD_WEIGHT_OUTGOING_RELATIONS,
    THREAD_WEIGHT_INCOMING_RELATIONS,
    THREAD_WEIGHT_ENTITY_PROPERTIES,
    THREAD_WEIGHT_TYPE_AND_SUMMARY,
    THREAD_WEIGHT_CONNECTED_ENTITIES,
    THREAD_TYPE_PENALTY_NO_MATCH,
    QUERY_ENTITY_MATCH_BOOST_EXACT,
    QUERY_ENTITY_MATCH_BOOST_PARTIAL,
    QUERY_ENTITY_MATCH_BOOST_NORMALIZED
)
from backend.langgraph_fuseki.utils.token_utils import extract_and_accumulate_tokens
from langchain_openai import ChatOpenAI


def calculate_improved_relevance_score(path_data: dict, query_entities: list = None, thread_type: str = "", entity_boost_mode: str = None) -> float:
    """
    개선된 경로의 relevance score 계산

    개선 사항:
    1. 쿼리 엔티티와의 직접 연결성 강화
    2. Thread 타입별 가중치 조정

    Args:
        path_data: 경로 데이터 (binding 정보)
        query_entities: 쿼리에서 추출된 엔티티 리스트
        thread_type: Thread 타입 (outgoing_relations, incoming_relations 등)
        entity_boost_mode: 엔티티 부스트 모드 ("exact_match", "partial_match", "normalized_match", "penalty_match", None)

    Returns:
        relevance score (테스트 모드에서 조건 안 맞으면 0.0 반환하여 필터링)
    """
    score = 1.0

    # 1. 쿼리 엔티티와의 직접 연결 여부 (강화 - 차별화를 위해)
    query_entity_match_boost = 1.0  # 기본값 (매칭 없음)
    match_type = None  # "exact", "partial", "normalized", None
    if query_entities:
        subject = path_data.get("subject", {}).get("value", "")
        obj = path_data.get("object", {}).get("value", "")
        entity_label = path_data.get("entityLabel", {}).get("value", "")
        subject_label = path_data.get("subjectLabel", {}).get("value", "")
        object_label = path_data.get("objectLabel", {}).get("value", "")

        # 모든 가능한 엔티티 이름 수집 (정규화)
        # Thread 타입에 따라 우선순위 다르게 처리
        all_entity_names = []
        all_entity_names_normalized = []

        def normalize_name(name):
            """이름 정규화 (공백 제거, 소문자 변환)"""
            if not name:
                return ""
            return name.replace(" ", "").replace("_", "").lower()

        # Thread별 매칭 대상 선택
        if thread_type == "incoming_relations":
            # incoming: entityLabel(목적지)를 우선 체크
            priority_sources = [entity_label, subject_label]
        elif thread_type == "outgoing_relations":
            # outgoing: entityLabel(출발지)를 우선 체크
            priority_sources = [entity_label, object_label]
        else:
            # 나머지: 모든 라벨 체크
            priority_sources = [entity_label, subject_label, object_label]

        for name_source in priority_sources:
            if name_source:
                raw_name = name_source.split("#")[-1] if "#" in name_source else name_source
                all_entity_names.append(raw_name)
                all_entity_names_normalized.append(normalize_name(raw_name))

        # URI도 추가 (subject, obj)
        for uri_source in [subject, obj]:
            if uri_source:
                raw_name = uri_source.split("#")[-1] if "#" in uri_source else uri_source
                if raw_name not in all_entity_names:
                    all_entity_names.append(raw_name)
                    all_entity_names_normalized.append(normalize_name(raw_name))

        # 쿼리 엔티티와 직접 매칭 확인 (더 정확하게)
        for entity in query_entities:
            entity_name = entity.get("name", "") or entity.get("label", "")
            if not entity_name:
                continue
            
            entity_name_normalized = normalize_name(entity_name)
            
            # 정확한 매칭 (매우 높은 부스트) - 차별화 강화
            if entity_name in all_entity_names or entity_name_normalized in all_entity_names_normalized:
                query_entity_match_boost = QUERY_ENTITY_MATCH_BOOST_EXACT
                match_type = "exact"
                break
            # 부분 매칭 (중간 부스트)
            elif any(entity_name in name or name in entity_name for name in all_entity_names if name):
                query_entity_match_boost = QUERY_ENTITY_MATCH_BOOST_PARTIAL
                match_type = "partial"
                break
            # 정규화된 부분 매칭
            elif any(entity_name_normalized in norm_name or norm_name in entity_name_normalized
                    for norm_name in all_entity_names_normalized if norm_name):
                query_entity_match_boost = QUERY_ENTITY_MATCH_BOOST_NORMALIZED
                match_type = "normalized"
                break

    # 테스트 모드: entity_boost_mode에 따라 필터링
    if entity_boost_mode:
        if entity_boost_mode == "exact_match":
            if match_type != "exact":
                return 0.0  # 정확 매칭이 아니면 필터링
        elif entity_boost_mode == "partial_match":
            if match_type != "partial":
                return 0.0  # 부분 매칭이 아니면 필터링
        elif entity_boost_mode == "normalized_match":
            if match_type != "normalized":
                return 0.0  # 정규화 매칭이 아니면 필터링
        elif entity_boost_mode == "penalty_match":
            if match_type is not None:
                return 0.0  # 매칭되면 필터링 (매칭 안 된 것만)

    score *= query_entity_match_boost

    # 2. Thread 타입별 추가 가중치 (환경변수로 설정 가능)
    if thread_type == "outgoing_relations":
        score *= THREAD_WEIGHT_OUTGOING_RELATIONS
    elif thread_type == "incoming_relations":
        score *= THREAD_WEIGHT_INCOMING_RELATIONS
    elif thread_type == "entity_properties":
        score *= THREAD_WEIGHT_ENTITY_PROPERTIES
    elif thread_type == "type_and_summary":
        score *= THREAD_WEIGHT_TYPE_AND_SUMMARY
    elif thread_type == "connected_entities":
        score *= THREAD_WEIGHT_CONNECTED_ENTITIES

    # 3. 관계 중요도에 따른 추가 차별화
    # 쿼리 엔티티와 매칭되지 않은 경우 페널티 적용 (환경변수로 설정 가능)
    # 테스트 모드가 아닐 때만 적용
    if not entity_boost_mode and query_entity_match_boost == 1.0 and query_entities:
        # 매칭되지 않은 경로는 페널티
        score *= THREAD_TYPE_PENALTY_NO_MATCH

    return score


def detect_convergence_nodes(inference_paths: dict, query_entities: list) -> dict:
    """
    수렴 노드 감지: 여러 쿼리 엔티티를 연결하는 중간 노드 찾기

    Args:
        inference_paths: 쓰레드별 추론 경로
        query_entities: 추출된 엔티티 목록

    Returns:
        {node_uri: {"count": N, "connected_entities": [...], "boost": 2.0}}
    """

    entity_connections = {}  # node_uri → set of query entities it connects

    # 모든 경로에서 엔티티 간 연결 추출
    for thread_type, paths in inference_paths.items():
        for path in paths:
            raw_data = path.get("raw_data", {})

            # connected_entities 쓰레드에서 수렴 노드 추출
            if thread_type == "connected_entities":
                convergence_node = raw_data.get("convergence_node")# ==========(,default)인지 체크해볼것 ============
                entity1_label = raw_data.get("label1", "")
                entity2_label = raw_data.get("label2", "")

                if convergence_node:
                    if convergence_node not in entity_connections:
                        entity_connections[convergence_node] = set()

                    entity_connections[convergence_node].add(entity1_label)
                    entity_connections[convergence_node].add(entity2_label)

            # 일반 경로에서도 중간 노드 추출
            entities_in_path = raw_data.get("entities", [])
            if len(entities_in_path) >= 2:
                # 경로 중간의 모든 노드를 잠재적 수렴 노드로 간주
                for entity_uri in entities_in_path:
                    if entity_uri not in entity_connections:
                        entity_connections[entity_uri] = set()

                    # 이 경로에 포함된 쿼리 엔티티 추가
                    for query_entity in query_entities:
                        query_name = query_entity.get("name", "")
                        if query_name in str(entities_in_path):
                            entity_connections[entity_uri].add(query_name)

    # 수렴 노드 필터링 (2개 이상의 쿼리 엔티티를 연결)
    convergence_nodes = {}
    for node_uri, connected_entities in entity_connections.items():
        if len(connected_entities) >= 2:
            convergence_nodes[node_uri] = {
                "count": len(connected_entities),
                "connected_entities": list(connected_entities),
                "boost": 1.1  # 1.1배 가중치 부스트
            }

    return convergence_nodes


def extract_label_from_uri(uri: str) -> str:
    """URI에서 라벨 추출 (hist:Person_정약용 → 정약용)"""
    if "#" in uri:
        return uri.split("#")[-1]
    elif "/" in uri:
        return uri.split("/")[-1]
    return uri


def extract_outgoing_relations(bindings: list, base_weight: float, query_entities: list = None, entity_boost_mode: str = None) -> list:
    """엔티티에서 나가는 모든 관계 추출 (엔티티 → ?)"""
    paths = []
    seen = set()

    for binding in bindings:
        entity_label = binding.get("entityLabel", {}).get("value", "")
        predicate = binding.get("predicate", {}).get("value", "").split("#")[-1]
        obj = binding.get("object", {}).get("value", "")
        obj_label = binding.get("objectLabel", {}).get("value", "") or obj.split("#")[-1]

        # 중복 제거
        key = f"{entity_label}-{predicate}-{obj_label}"
        if key in seen or not predicate:
            continue
        seen.add(key)

        # 개선된 Relevance score 계산
        relevance_score = calculate_improved_relevance_score(binding, query_entities, "outgoing_relations", entity_boost_mode)

        # 0점 경로는 필터링 (entity_boost_mode 테스트 시)
        if entity_boost_mode and relevance_score == 0.0:
            continue

        # 프로퍼티 이름을 읽기 좋게 변환
        predicate_display = predicate.replace("has", "").replace("_", " ")

        description = f"{entity_label} → [{predicate_display}] → {obj_label}"

        paths.append({
            "type": "outgoing_relation",
            "subject": entity_label,
            "predicate": predicate,
            "predicate_display": predicate_display,
            "object": obj_label,
            "weight": base_weight * relevance_score,
            "relevance_score": relevance_score,
            "description": description,
            "raw_data": binding
        })

    return paths[:30]


def extract_incoming_relations(bindings: list, base_weight: float, query_entities: list = None, entity_boost_mode: str = None) -> list:
    """엔티티로 들어오는 모든 관계 추출 (? → 엔티티)"""
    paths = []
    seen = set()

    for binding in bindings:
        subject = binding.get("subject", {}).get("value", "")
        subject_label = binding.get("subjectLabel", {}).get("value", "") or subject.split("#")[-1]
        predicate = binding.get("predicate", {}).get("value", "").split("#")[-1]
        entity_label = binding.get("entityLabel", {}).get("value", "")

        # 중복 제거
        key = f"{subject_label}-{predicate}-{entity_label}"
        if key in seen or not predicate:
            continue
        seen.add(key)

        # 개선된 Relevance score 계산
        relevance_score = calculate_improved_relevance_score(binding, query_entities, "incoming_relations", entity_boost_mode)

        # 0점 경로는 필터링 (entity_boost_mode 테스트 시)
        if entity_boost_mode and relevance_score == 0.0:
            continue

        # 프로퍼티 이름을 읽기 좋게 변환
        predicate_display = predicate.replace("has", "").replace("_", " ")

        description = f"{subject_label} → [{predicate_display}] → {entity_label}"

        paths.append({
            "type": "incoming_relation",
            "subject": subject_label,
            "predicate": predicate,
            "predicate_display": predicate_display,
            "object": entity_label,
            "weight": base_weight * relevance_score,
            "relevance_score": relevance_score,
            "description": description,
            "raw_data": binding
        })

    return paths[:30]


def extract_entity_properties(bindings: list, base_weight: float, query_entities: list = None, entity_boost_mode: str = None) -> list:
    """엔티티의 모든 속성 추출 (리터럴 값)"""
    paths = []
    seen = set()

    for binding in bindings:
        entity_label = binding.get("entityLabel", {}).get("value", "")
        predicate = binding.get("predicate", {}).get("value", "").split("#")[-1]
        value = binding.get("value", {}).get("value", "")

        # 중복 제거 (값도 포함하여 정확한 중복만 제거)
        key = f"{entity_label}-{predicate}-{value}"
        if key in seen or not predicate or not value:
            continue
        seen.add(key)

        # 개선된 Relevance score 계산
        relevance_score = calculate_improved_relevance_score(binding, query_entities, "entity_properties", entity_boost_mode)

        # 0점 경로는 필터링 (entity_boost_mode 테스트 시)
        if entity_boost_mode and relevance_score == 0.0:
            continue

        # 값 정리 (너무 길면 자르기)
        value_display = value[:100] + "..." if len(value) > 100 else value

        # 프로퍼티 이름을 읽기 좋게 변환
        predicate_display = predicate.replace("has", "").replace("_", " ")

        description = f"{entity_label}의 {predicate_display}: {value_display}"

        paths.append({
            "type": "property",
            "entity": entity_label,
            "predicate": predicate,
            "predicate_display": predicate_display,
            "value": value_display,
            "weight": base_weight * relevance_score,
            "relevance_score": relevance_score,
            "description": description,
            "raw_data": binding
        })

    return paths[:30]


def extract_connected_entities(bindings: list, base_weight: float, query_entities: list = None, entity_boost_mode: str = None) -> list:
    """
    연결된 엔티티들 간의 관계 추출 (2-hop)
    """
    paths = []
    seen = set()

    for binding in bindings:
        entity1 = binding.get("label1", {}).get("value", "")
        predicate = binding.get("predicate", {}).get("value", "").split("#")[-1]
        entity2 = binding.get("label2", {}).get("value", "")

        # 중복 제거
        key = f"{entity1}-{predicate}-{entity2}"
        if key in seen or not predicate:
            continue
        seen.add(key)

        # Relevance score 계산 (entity_boost_mode 테스트용)
        relevance_score = calculate_improved_relevance_score(binding, query_entities, "connected_entities", entity_boost_mode)

        # 0점 경로는 필터링
        if entity_boost_mode and relevance_score == 0.0:
            continue

        # 프로퍼티 이름을 읽기 좋게 변환
        predicate_display = predicate.replace("has", "").replace("_", " ")

        description = f"{entity1} ↔ [{predicate_display}] ↔ {entity2}"

        paths.append({
            "type": "connection",
            "entity1": entity1,
            "predicate": predicate,
            "predicate_display": predicate_display,
            "entity2": entity2,
            "weight": base_weight * relevance_score,
            "relevance_score": relevance_score,
            "description": description,
            "raw_data": binding
        })

    return paths[:20]


def extract_type_and_summary(bindings: list, base_weight: float, query_entities: list = None, entity_boost_mode: str = None) -> list:
    """엔티티 타입과 요약 정보 추출"""
    paths = []
    seen = set()

    for binding in bindings:
        entity_label = binding.get("entityLabel", {}).get("value", "")
        entity_type = binding.get("type", {}).get("value", "").split("#")[-1] if binding.get("type") else ""
        summary = binding.get("summary", {}).get("value", "") if binding.get("summary") else ""
        category = binding.get("category", {}).get("value", "") if binding.get("category") else ""
        year = binding.get("year", {}).get("value", "") if binding.get("year") else ""

        # 중복 제거: 완전히 동일한 조합만 제거 (엔티티만으로 제거하지 않음)
        key = f"{entity_label}-{entity_type}-{summary[:50] if summary else ''}"
        if key in seen:
            continue
        seen.add(key)

        # Relevance score 계산 (entity_boost_mode 테스트용)
        relevance_score = calculate_improved_relevance_score(binding, query_entities, "type_and_summary", entity_boost_mode)

        # 0점 경로는 필터링
        if entity_boost_mode and relevance_score == 0.0:
            continue
        
        # 설명 생성
        parts = []
        if entity_type:
            parts.append(f"[{entity_type}]")
        if year:
            parts.append(f"({year}년)")
        if category:
            parts.append(f"분류: {category}")
        if summary:
            parts.append(summary[:100])
        
        description = f"{entity_label} " + " ".join(parts) if parts else entity_label
        
        paths.append({
            "type": "summary",
            "entity": entity_label,
            "entity_type": entity_type,
            "summary": summary,
            "category": category,
            "year": year,
            "weight": base_weight,
            "description": description,
            "raw_data": binding
        })
    
    return paths[:20]


def select_top_evidences_with_llm(
    candidate_evidences: list,
    query: str,
    query_intent: str = "",
    query_type: str = "causal",
    top_k: int = 15,
    state: GraphState = None
) -> list:
    """
    LLM을 사용하여 질문 의도에 맞는 상위 근거 선택
    
    Args:
        candidate_evidences: 점수 기반으로 선별된 후보 근거 리스트
        query: 사용자 질문
        query_intent: 질문의 핵심 의도
        query_type: 질문 유형 (causal, deep_analysis 등)
        top_k: 선택할 근거 개수
    
    Returns:
        LLM이 선택한 상위 top_k개 근거
    """
    if len(candidate_evidences) <= top_k:
        return candidate_evidences
    
    try:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            temperature=0  # 일관성을 위해 temperature=0
        )
        
        # 근거 목록 포맷팅 (간결하게)
        evidence_list = []
        for i, ev in enumerate(candidate_evidences, 1):
            desc = ev.get("description", "")
            ev_type = ev.get("type", "unknown")
            weight = ev.get("weight", 0)
            
            # 간결한 설명 (최대 100자)
            desc_short = desc[:100] + "..." if len(desc) > 100 else desc
            
            evidence_list.append(f"[{i}] {desc_short} (타입: {ev_type}, 점수: {weight:.3f})")
        
        evidence_text = "\n".join(evidence_list)
        
        intent_info = f"\n질문의 핵심 의도: {query_intent}\n" if query_intent else ""
        
        prompt = f"""당신은 역사 질문에 가장 적합한 근거를 선택하는 전문가입니다.

## 질문
{query}
{intent_info}질문 유형: {query_type}

## 후보 근거 목록 (총 {len(candidate_evidences)}개)
아래 근거들은 점수 기반으로 선별된 후보입니다. 질문의 의도와 가장 관련성이 높은 **상위 {top_k}개**를 선택하세요.

{evidence_text}

## 선택 기준
1. **질문 의도와의 관련성**: 질문에 직접적으로 답변할 수 있는 근거 우선
2. **정보의 중요성**: 핵심 사건, 주요 인물, 중요한 제도 등
3. **다양성**: 중복을 피하고 다양한 관점의 근거 포함
4. **시간적/인과적 연결**: 질문과 시간적/인과적으로 연결된 근거 우선

## 출력 형식 (JSON만)
선택한 근거의 번호를 리스트로 출력하세요:
{{"selected_indices": [1, 3, 5, 7, 9, 12, 15, 18, 20, 22, 25, 28, 30, 33, 35]}}

**중요:**
- 정확히 {top_k}개를 선택하세요.
- 번호는 1부터 시작합니다 (위 목록의 [1], [2], ...).
- JSON 형식만 출력하세요."""
        
        response = llm.invoke(prompt)
        
        # 토큰 사용량 추출 및 state에 누적
        if state is not None:
            token_update = extract_and_accumulate_tokens(state, response)
            state.update(token_update)
        
        content = response.content.strip()
        
        # JSON 파싱
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        result = json.loads(content)
        selected_indices = result.get("selected_indices", [])
        
        # 인덱스를 0-based로 변환하고 근거 선택
        selected_evidences = []
        for idx in selected_indices:
            if 1 <= idx <= len(candidate_evidences):
                selected_evidences.append(candidate_evidences[idx - 1])
        
        # 선택된 개수가 top_k보다 적으면 나머지는 점수 순으로 채움
        if len(selected_evidences) < top_k:
            remaining_count = top_k - len(selected_evidences)
            selected_set = {id(ev) for ev in selected_evidences}
            for ev in candidate_evidences:
                if len(selected_evidences) >= top_k:
                    break
                if id(ev) not in selected_set:
                    selected_evidences.append(ev)
        
        return selected_evidences[:top_k]
        
    except Exception as e:
        print(f"        └─ LLM 기반 선택 실패: {e}, 점수 기반으로 대체")
        # 실패 시 점수 기반으로 대체
        return candidate_evidences[:top_k]


def path_evidence_aggregator_node(state: GraphState) -> GraphState:
    """
    통합 노드: 경로 추출 + 근거 통합
    
    1. Parallel Knowledge Retrieval의 5개 Thread 결과에서 경로 추출
    2. 개선된 점수 체계로 관련성 평가
    3. 모든 경로를 통합하여 가중치 기준 정렬
    4. 하이브리드 방식으로 상위 15개 근거 선택:
       - 점수 기반으로 상위 30-50개 후보 선별
       - LLM이 질문 의도에 맞는 최종 15개 선택
    """

    import time
    node_start = time.time()

    parallel_results = state.get("parallel_inference_results", {})
    thread_weights = state.get("thread_weights", {})
    query_type = state.get("query_type", "causal")
    query_entities = state.get("extracted_entities", [])
    test_config = state.get("test_config")  # 테스트 설정

    # 엔티티 부스트 모드 추출
    entity_boost_mode = None
    if test_config and "entity_boost_mode" in test_config:
        entity_boost_mode = test_config["entity_boost_mode"]

    print(f"\n{'='*70}")
    print(f"[4/6] 경로 추출 및 근거 통합 (Path Extractor & Evidence Aggregator)")
    print(f"{'='*70}")
    if entity_boost_mode:
        print(f"  ├─ [테스트 모드] Entity Boost Mode: {entity_boost_mode}")

    # 1. Thread별 경로 추출
    inference_paths = {}

    for thread_type, result in parallel_results.items():
        bindings = result.get("bindings", [])

        if not bindings:
            inference_paths[thread_type] = []
            continue

        # Thread별 경로 추출 - base_weight를 thread별로 차별화() / 1.00 ~ 1.05
        default_weights = {
            "outgoing_relations": 0.5,  # 나가는 관계는 높게
            "incoming_relations": 0.4,   # 들어오는 관계는 중간
            "entity_properties": 0.3,   # 속성은 낮게
            "connected_entities": 0.3,  # 연결은 낮게
            "type_and_summary": 0.2     # 요약은 가장 낮게
        }
        base_weight = thread_weights.get(thread_type, default_weights.get(thread_type, 0.3))

        if thread_type == "outgoing_relations":
            paths = extract_outgoing_relations(bindings, base_weight, query_entities, entity_boost_mode)
        elif thread_type == "incoming_relations":
            paths = extract_incoming_relations(bindings, base_weight, query_entities, entity_boost_mode)
        elif thread_type == "entity_properties":
            paths = extract_entity_properties(bindings, base_weight, query_entities, entity_boost_mode)
        elif thread_type == "connected_entities":
            paths = extract_connected_entities(bindings, base_weight, query_entities, entity_boost_mode)
        elif thread_type == "type_and_summary":
            paths = extract_type_and_summary(bindings, base_weight, query_entities, entity_boost_mode)
        else:
            # 알 수 없는 Thread는 빈 리스트
            paths = []

        inference_paths[thread_type] = paths

    # 총 경로 수 계산
    total_paths = sum(len(paths) for paths in inference_paths.values())
    print(f"  ├─ 경로 추출 완료: {total_paths}개 경로")

    # 2. 수렴 노드 감지
    convergence_nodes = detect_convergence_nodes(inference_paths, query_entities)

    if convergence_nodes:
        print(f"  ├─ 수렴 노드 감지: {len(convergence_nodes)}개")
        for i, (node_uri, info) in enumerate(list(convergence_nodes.items())[:3], 1):
            node_label = extract_label_from_uri(node_uri)
            connected = ", ".join(info["connected_entities"][:3])
            print(f"  │  {i}. {node_label} (연결: {connected})")

    # 3. 모든 Thread의 경로를 하나로 병합
    all_evidences = []

    for thread_type, paths in inference_paths.items():
        for path in paths:
            final_weight = path.get("weight", 0.2)

            # 수렴 노드 부스트 적용
            raw_data = path.get("raw_data", {})
            convergence_node = raw_data.get("convergence_node")

            if convergence_node and convergence_node in convergence_nodes:
                boost = convergence_nodes[convergence_node]["boost"]
                final_weight *= boost
                path["convergence_boost"] = boost

            evidence = {
                "type": thread_type,
                "description": path.get("description", ""),
                "weight": final_weight,
                "relevance_score": path.get("relevance_score", 1.0),
                "source": f"Thread: {thread_type}",
                "raw_data": path,
                "is_convergence": convergence_node in convergence_nodes if convergence_node else False
            }

            all_evidences.append(evidence)

    # 4. 가중치 기준으로 정렬
    sorted_evidences = sorted(all_evidences, key=lambda x: x["weight"], reverse=True)

    # 쓰레드별 검색 결과 출력
    print(f"\n      [쓰레드별 검색 결과]")
    for thread_type, paths in inference_paths.items():
        if paths:
            print(f"        - {thread_type}: {len(paths)}개 경로")
            # 상위 3개만 미리보기
            for i, path in enumerate(paths[:3], 1):
                desc = path.get("description", "")[:50]
                weight = path.get("weight", 0)
                print(f"          {i}. {desc} (가중치: {weight:.3f})")
            if len(paths) > 3:
                print(f"          ... 외 {len(paths) - 3}개")

    # 전체 근거 목록 출력 (정렬 후)
    print(f"\n      [전체 근거 목록 (총 {len(sorted_evidences)}개, 가중치 순)]")
    for i, ev in enumerate(sorted_evidences[:25], 1):  # 상위 25개만 출력
        ev_type = ev.get("type", "unknown")
        description = ev.get("description", "")
        weight = ev.get("weight", 0)
        
        type_map = {
            "outgoing_relations": "나가는관계",
            "incoming_relations": "들어오는관계",
            "entity_properties": "엔티티속성",
            "connected_entities": "연결엔티티",
            "type_and_summary": "타입/요약",
            "property": "속성",
            "connection": "연결",
            "summary": "요약"
        }
        type_display = type_map.get(ev_type, ev_type)
        desc_display = description[:60] + "..." if len(description) > 60 else description
        
        print(f"        {i:2d}. [{type_display:12s}] {desc_display} (가중치: {weight:.4f})")
    if len(sorted_evidences) > 25:
        print(f"        ... 외 {len(sorted_evidences) - 25}개")

    # 5. 하이브리드 방식: 점수 기반 선별 → LLM 기반 최종 선택
    # 5-1. 점수 기반으로 상위 후보 선별 (30-50개)
    candidate_count = min(max(30, len(sorted_evidences) // 2), len(sorted_evidences))
    candidate_evidences = sorted_evidences[:candidate_count]
    
    print(f"\n      [LLM 기반 근거 선택]")
    print(f"        - 후보 근거: {len(candidate_evidences)}개 (점수 기반 선별)")
    
    # 5-2. LLM이 질문 의도에 맞는 상위 15개 선택
    query = state.get("query", "")
    query_intent = state.get("query_intent", "")
    query_type = state.get("query_type", "causal")
    
    if len(candidate_evidences) <= 15:
        # 후보가 15개 이하면 그대로 사용
        top_evidences = candidate_evidences
        print(f"        - 최종 선택: {len(top_evidences)}개 (후보가 15개 이하)")
    else:
        # LLM으로 최종 선택
        top_evidences = select_top_evidences_with_llm(
            candidate_evidences, 
            query, 
            query_intent, 
            query_type,
            state=state,
            top_k=15
        )
        print(f"        - 최종 선택: {len(top_evidences)}개 (LLM 판단)")

    # 6. 순위 부여
    for i, ev in enumerate(top_evidences, 1):
        ev["rank"] = i

    # 최종 선택된 근거 목록
    if top_evidences:
        print(f"\n      [최종 근거 목록 (상위 {len(top_evidences)}개)]")
        for ev in top_evidences:
            rank = ev.get("rank", 0)
            ev_type = ev.get("type", "unknown")
            description = ev.get("description", "")
            weight = ev.get("weight", 0)

            # Thread 이름 정규화
            type_map = {
                "outgoing_relations": "나가는관계",
                "incoming_relations": "들어오는관계",
                "entity_properties": "엔티티속성",
                "connected_entities": "연결엔티티",
                "type_and_summary": "타입/요약",
                "property": "속성",
                "connection": "연결",
                "summary": "요약"
            }
            type_display = type_map.get(ev_type, ev_type)

            desc_display = description[:60] + "..." if len(description) > 60 else description

            print(f"      {rank}. [{type_display:12s}] {desc_display} (가중치: {weight:.2%})")

    node_elapsed = time.time() - node_start
    print(f"  └─ 완료: {len(top_evidences)}개 근거 통합 ({node_elapsed:.2f}초)")
    print()

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["path_evidence_aggregator"] = node_elapsed

    return {
        **state,
        "inference_paths": inference_paths,
        "evidences": top_evidences,
        "executed_nodes": state.get("executed_nodes", []) + ["path_evidence_aggregator"],
        "node_execution_times": node_times
    }

