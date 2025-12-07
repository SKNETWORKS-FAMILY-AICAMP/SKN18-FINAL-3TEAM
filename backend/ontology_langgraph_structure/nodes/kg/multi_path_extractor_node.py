"""
Multi-Path Extractor Node

5개 Thread의 추론 결과에서 각각 경로 추출
- Thread별로 서로 다른 경로 추출 로직 적용
- 각 Thread의 가중치 반영
- 속성/관계별 relevance score 계산
"""

from state import GraphState

# ========================================
# 속성/관계 타입별 Relevance Score 가중치
# ========================================

# 관계(Predicate) 타입별 가중치
RELATION_WEIGHTS = {
    # 인과관계 (가장 중요)
    "leadsTo": 1.5,
    "causedBy": 1.5,
    "causes": 1.5,
    "ledTo": 1.5,
    "triggeredBy": 1.4,

    # 참여/지휘 (높은 관련성)
    "participatesIn": 1.3,
    "commands": 1.3,
    "involved": 1.3,
    "involves": 1.3,

    # 부분 관계 (높은 관련성)
    "partOf": 1.2,

    # 설립/건설
    "establishedBy": 1.2,
    "founded": 1.2,
    "built": 1.2,

    # 시간적 관계
    "occursBefore": 1.1,
    "occursAfter": 1.1,
    "followedBy": 1.1,
    "precededBy": 1.1,

    # 연결관계
    "relatedTo": 1.0,
    "associatedWith": 1.0,
    "connectedTo": 1.0,

    # 일반 속성 (낮은 관련성)
    "hasYear": 0.8,
    "hasCategory": 0.7,
    "hasDescription": 0.6,

    # 기본값 (매칭 안되는 경우)
    "_default": 1.0
}

# 속성 이름 패턴별 가중치 (관계가 아닌 속성값)
PROPERTY_WEIGHTS = {
    # 핵심 속성
    "Achievement": 1.2,
    "Rank": 1.1,
    "Role": 1.1,

    # 시간 속성
    "Year": 0.9,
    "StartYear": 0.9,
    "EndYear": 0.9,
    "Month": 0.8,

    # 일반 속성
    "Category": 0.7,
    "Type": 0.7,

    # 기본값
    "_default": 0.8
}

def calculate_path_relevance(path_data: dict, query_entities: list = None) -> float:
    """
    경로의 relevance score 계산

    Args:
        path_data: 경로 데이터 (binding 정보)
        query_entities: 쿼리에서 추출된 엔티티 리스트

    Returns:
        relevance score (0.5 ~ 1.5)
    """
    score = 1.0

    # 1. 관계(predicate) 가중치
    predicate = path_data.get("predicate", {}).get("value", "")
    if predicate:
        pred_name = predicate.split("#")[-1]  # hist:leadsTo → leadsTo
        score *= RELATION_WEIGHTS.get(pred_name, RELATION_WEIGHTS["_default"])

    # 2. 속성명 가중치
    property_name = path_data.get("property", {}).get("value", "")
    if property_name:
        prop_name = property_name.split("#")[-1]
        # 속성명에서 키워드 추출 (예: hasAchievement → Achievement)
        for keyword, weight in PROPERTY_WEIGHTS.items():
            if keyword != "_default" and keyword.lower() in prop_name.lower():
                score *= weight
                break
        else:
            score *= PROPERTY_WEIGHTS["_default"]

    # 3. 쿼리 엔티티와의 직접 연결 여부
    if query_entities:
        # subject나 object가 쿼리 엔티티와 일치하면 부스트
        subject = path_data.get("subject", {}).get("value", "")
        obj = path_data.get("object", {}).get("value", "")

        subject_name = subject.split("#")[-1] if subject else ""
        obj_name = obj.split("#")[-1] if obj else ""

        for entity in query_entities:
            entity_name = entity.get("name", "")
            if entity_name and (entity_name in subject_name or entity_name in obj_name):
                score *= 1.2  # 20% 부스트
                break

    # 4. 범위 제한 (0.5 ~ 1.5)
    return max(0.5, min(1.5, score))


def multi_path_extractor_node(state: GraphState) -> GraphState:
    """5개 Thread별 추론 경로 추출"""

    import time
    node_start = time.time()

    parallel_results = state.get("parallel_inference_results", {})
    thread_weights = state.get("thread_weights", {})
    query_entities = state.get("extracted_entities", [])  # 쿼리 엔티티 가져오기

    print(f"\n{'='*70}")
    print(f"[4/6] 다중 경로 추출 (Multi-Path Extractor)")
    print(f"{'='*70}")

    inference_paths = {}

    for thread_type, result in parallel_results.items():
        bindings = result.get("bindings", [])

        if not bindings:
            inference_paths[thread_type] = []
            continue

        # Thread별 경로 추출 (범용 관계 검색 기반)
        base_weight = thread_weights.get(thread_type, 0.2)

        if thread_type == "outgoing_relations":
            paths = extract_outgoing_relations(bindings, base_weight, query_entities)
        elif thread_type == "incoming_relations":
            paths = extract_incoming_relations(bindings, base_weight, query_entities)
        elif thread_type == "entity_properties":
            paths = extract_entity_properties(bindings, base_weight, query_entities)
        elif thread_type == "connected_entities":
            paths = extract_connected_entities(bindings, base_weight)
        elif thread_type == "type_and_summary":
            paths = extract_type_and_summary(bindings, base_weight)
        # 이전 버전 호환성 (레거시 Thread 타입)
        elif thread_type in ["event_context", "actor_network", "timeline", "similar_events", "background"]:
            paths = extract_generic_paths(bindings, base_weight, thread_type)
        elif thread_type == "causal":
            paths = extract_causal_paths(bindings, base_weight)
        elif thread_type == "person":
            paths = extract_person_paths(bindings, base_weight)
        elif thread_type == "temporal":
            paths = extract_temporal_paths(bindings, base_weight)
        elif thread_type == "pattern":
            paths = extract_pattern_paths(bindings, base_weight)
        elif thread_type == "motive":
            paths = extract_motive_paths(bindings, base_weight)
        elif thread_type == "comparison":
            paths = extract_comparison_paths(bindings, base_weight)
        else:
            # 알 수 없는 Thread는 범용 추출
            paths = extract_generic_paths(bindings, base_weight, thread_type)

        inference_paths[thread_type] = paths

    # 총 경로 수 계산
    total_paths = sum(len(paths) for paths in inference_paths.values())
    node_elapsed = time.time() - node_start
    print(f"  └─ 완료: {total_paths}개 경로 추출 ({node_elapsed:.2f}초)")
    print()

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["multi_path_extractor"] = node_elapsed

    return {
        **state,
        "inference_paths": inference_paths,
        "executed_nodes": state.get("executed_nodes", []) + ["multi_path_extractor"],
        "node_execution_times": node_times
    }


def extract_causal_paths(bindings: list, base_weight: float) -> list:
    """인과관계 체인 추출"""
    paths = []

    # leadsTo 관계 수집 (다양한 변수명 지원)
    for binding in bindings:
        # 원인 추출 (cause, subject, s 등 다양한 변수명 지원)
        cause_binding = (
            binding.get("cause") or 
            binding.get("subject") or 
            binding.get("s") or 
            binding.get("entity") or
            {}
        )
        cause = cause_binding.get("value", "").split("#")[-1] if cause_binding else ""
        
        # 라벨이 있으면 사용
        cause_label = (
            binding.get("causeLabel") or 
            binding.get("subjectLabel") or 
            binding.get("sLabel") or
            {}
        )
        cause_name = cause_label.get("value", cause) if cause_label else cause
        
        # 결과 추출 (effect, object, o 등 다양한 변수명 지원)
        effect_binding = (
            binding.get("effect") or 
            binding.get("object") or 
            binding.get("o") or
            {}
        )
        effect = effect_binding.get("value", "").split("#")[-1] if effect_binding else ""
        
        # 라벨이 있으면 사용
        effect_label = (
            binding.get("effectLabel") or 
            binding.get("objectLabel") or 
            binding.get("oLabel") or
            {}
        )
        effect_name = effect_label.get("value", effect) if effect_label else effect

        if cause and effect:
            paths.append({
                "type": "causal",
                "chain": [cause_name, effect_name],
                "weight": base_weight,
                "description": f"{cause_name} → {effect_name}"
            })

    return paths[:10]  # 상위 10개


def extract_person_paths(bindings: list, base_weight: float) -> list:
    """인물 관계 추출"""
    paths = []

    for binding in bindings:
        # 인물 추출 (다양한 변수명 지원)
        person_binding = (
            binding.get("person") or 
            binding.get("entity") or 
            binding.get("s") or
            {}
        )
        person = person_binding.get("value", "").split("#")[-1] if person_binding else ""
        
        # 라벨
        person_label = (
            binding.get("personLabel") or 
            binding.get("entityLabel") or 
            binding.get("sLabel") or
            {}
        )
        person_name = person_label.get("value", person) if person_label else person
        
        # 이벤트/값 추출
        event_binding = (
            binding.get("event") or 
            binding.get("value") or 
            binding.get("o") or
            {}
        )
        event = event_binding.get("value", "").split("#")[-1] if event_binding else ""
        
        # 역할
        role_binding = binding.get("role") or binding.get("property") or {}
        role = role_binding.get("value", "") if role_binding else ""

        if person and event:
            paths.append({
                "type": "person",
                "person": person_name,
                "event": event,
                "role": role,
                "weight": base_weight,
                "description": f"{person_name} - {event}" + (f" ({role})" if role else "")
            })

    return paths[:10]


def extract_temporal_paths(bindings: list, base_weight: float) -> list:
    """시대 배경 추출"""
    paths = []

    for binding in bindings:
        # 이벤트/엔티티 추출 (다양한 변수명 지원)
        event_binding = (
            binding.get("event") or 
            binding.get("entity") or 
            binding.get("s") or
            {}
        )
        event = event_binding.get("value", "").split("#")[-1] if event_binding else ""
        
        # 라벨
        event_label = (
            binding.get("eventLabel") or 
            binding.get("entityLabel") or 
            binding.get("sLabel") or
            {}
        )
        event_name = event_label.get("value", event) if event_label else event
        
        # 연도
        year_binding = binding.get("year") or binding.get("date") or {}
        year = year_binding.get("value", "") if year_binding else ""
        
        # 컨텍스트
        context_binding = binding.get("context") or binding.get("description") or {}
        context = context_binding.get("value", "") if context_binding else ""

        if event and year:
            paths.append({
                "type": "temporal",
                "event": event_name,
                "year": year,
                "context": context,
                "weight": base_weight,
                "description": f"{year}년: {event_name}" + (f" ({context})" if context else "")
            })

    return paths[:10]


def extract_pattern_paths(bindings: list, base_weight: float) -> list:
    """패턴 추출"""
    paths = []

    for binding in bindings:
        # 엔티티 추출 (다양한 변수명 지원)
        e1_binding = (
            binding.get("e1") or 
            binding.get("entity") or 
            binding.get("s") or
            {}
        )
        e1 = e1_binding.get("value", "").split("#")[-1] if e1_binding else ""
        
        e1_label = (
            binding.get("e1Label") or 
            binding.get("entityLabel") or 
            binding.get("sLabel") or
            {}
        )
        e1_name = e1_label.get("value", e1) if e1_label else e1
        
        e2_binding = binding.get("e2") or binding.get("o") or {}
        e2 = e2_binding.get("value", "").split("#")[-1] if e2_binding else ""
        
        # 패턴
        pattern_binding = binding.get("pattern") or binding.get("p") or {}
        pattern = pattern_binding.get("value", "") if pattern_binding else ""

        if e1:
            paths.append({
                "type": "pattern",
                "events": [e1_name, e2] if e2 else [e1_name],
                "pattern": pattern,
                "weight": base_weight,
                "description": f"{e1_name} ↔ {e2}" + (f" ({pattern})" if pattern else "") if e2 else e1_name
            })

    return paths[:10]


def extract_motive_paths(bindings: list, base_weight: float) -> list:
    """동기 분석 추출"""
    paths = []

    for binding in bindings:
        # 인물/엔티티 추출
        person_binding = (
            binding.get("person") or 
            binding.get("entity") or 
            binding.get("s") or
            {}
        )
        person = person_binding.get("value", "").split("#")[-1] if person_binding else ""
        
        person_label = (
            binding.get("personLabel") or 
            binding.get("entityLabel") or 
            binding.get("sLabel") or
            {}
        )
        person_name = person_label.get("value", person) if person_label else person
        
        # 동기
        motive_binding = (
            binding.get("motive") or 
            binding.get("value") or 
            binding.get("o") or
            {}
        )
        motive = motive_binding.get("value", "") if motive_binding else ""
        
        # 행동
        action_binding = binding.get("action") or {}
        action = action_binding.get("value", "").split("#")[-1] if action_binding else ""

        if person and motive:
            paths.append({
                "type": "motive",
                "person": person_name,
                "motive": motive,
                "action": action,
                "weight": base_weight,
                "description": f"{person_name}: {motive}" + (f" → {action}" if action else "")
            })

    return paths[:10]


def extract_comparison_paths(bindings: list, base_weight: float) -> list:
    """실제 vs 가상 비교 추출 (What-if용)"""
    paths = []

    for binding in bindings:
        event = binding.get("event", {}).get("value", "").split("#")[-1]
        actual = binding.get("actual", {}).get("value", "")
        hypothetical = binding.get("hypothetical", {}).get("value", "")

        if event and (actual or hypothetical):
            paths.append({
                "type": "comparison",
                "event": event,
                "actual": actual,
                "hypothetical": hypothetical,
                "weight": base_weight,
                "description": f"{event}: 실제({actual}) vs 가상({hypothetical})"
            })

    return paths[:10]


def extract_event_context_paths(bindings: list, base_weight: float) -> list:
    """사건 맥락 경로 추출 + 1-hop 관계 확장"""
    paths = []
    seen_relations = set()  # 중복 관계 제거용
    
    for binding in bindings:
        entity_binding = binding.get("entity") or binding.get("event") or {}
        entity = entity_binding.get("value", "").split("#")[-1] if entity_binding else ""
        
        label_binding = binding.get("label") or {}
        label = label_binding.get("value", "") if label_binding else entity
        
        # 요약 추출
        summary_binding = binding.get("summary") or {}
        summary = summary_binding.get("value", "")[:150] if summary_binding.get("value") else ""
        
        # 1-hop 관계 확장 결과
        related_binding = binding.get("related") or {}
        related = related_binding.get("value", "").split("#")[-1] if related_binding else ""
        related_label_binding = binding.get("relatedLabel") or {}
        related_label = related_label_binding.get("value", "") if related_label_binding else related
        
        relation_type_binding = binding.get("relationType") or {}
        relation_type = relation_type_binding.get("value", "").split("#")[-1] if relation_type_binding else ""
        
        if entity:
            # 기본 엔티티 정보
            if label and (label, "") not in seen_relations:
                seen_relations.add((label, ""))
                display_desc = f"{label}: {summary}" if summary else label
                paths.append({
                    "type": "event_context",
                    "event": label,
                    "content": summary,
                    "weight": base_weight,
                    "description": display_desc
                })
            
            # 관계 확장 결과 추가
            if related_label and (label, related_label) not in seen_relations:
                seen_relations.add((label, related_label))
                
                # 관계 타입을 한글로 변환
                relation_map = {
                    "hasParticipant": "참여자",
                    "participatesIn": "참여",
                    "occursAt": "장소",
                    "leadsTo": "결과",
                    "causedBy": "원인",
                    "hasCommander": "지휘관",
                    "hasVictor": "승자",
                    "hasDefeated": "패자"
                }
                relation_kr = relation_map.get(relation_type, relation_type)
                
                display_desc = f"{label} → [{relation_kr}] → {related_label}"
                paths.append({
                    "type": "event_context",
                    "event": label,
                    "related": related_label,
                    "relation": relation_kr,
                    "content": f"{label}의 {relation_kr}: {related_label}",
                    "weight": base_weight * 1.2,  # 관계 정보는 가중치 높임
                    "description": display_desc
                })
    
    return paths[:15]  # 관계 확장으로 결과 많아짐


def extract_actor_network_paths(bindings: list, base_weight: float) -> list:
    """인물 네트워크 경로 추출 + 2-hop 관계 확장"""
    paths = []
    seen_relations = set()
    
    for binding in bindings:
        person_binding = binding.get("person") or {}
        person = person_binding.get("value", "").split("#")[-1] if person_binding else ""
        
        label_binding = binding.get("label") or {}
        label = label_binding.get("value", "") if label_binding else person
        
        # 1-hop: 인물과 직접 연결된 것
        hop1_binding = binding.get("hop1") or {}
        hop1 = hop1_binding.get("value", "").split("#")[-1] if hop1_binding else ""
        hop1_label_binding = binding.get("hop1Label") or {}
        hop1_label = hop1_label_binding.get("value", "") if hop1_label_binding else hop1
        hop1_type_binding = binding.get("hop1Type") or {}
        hop1_type = hop1_type_binding.get("value", "").split("#")[-1] if hop1_type_binding else ""
        
        # 2-hop: 관련 사건의 다른 참여자
        hop2_binding = binding.get("hop2") or {}
        hop2 = hop2_binding.get("value", "").split("#")[-1] if hop2_binding else ""
        hop2_label_binding = binding.get("hop2Label") or {}
        hop2_label = hop2_label_binding.get("value", "") if hop2_label_binding else hop2
        
        if person and label:
            # 1-hop 관계
            if hop1_label and (label, hop1_label) not in seen_relations:
                seen_relations.add((label, hop1_label))
                
                # 타입에 따라 관계 설명
                type_map = {"Event": "참여 사건", "Institution": "소속 기관", "Role": "역할", "Battle": "참여 전투"}
                relation_desc = type_map.get(hop1_type, "관련")
                
                display_desc = f"{label} → [{relation_desc}] → {hop1_label}"
                paths.append({
                    "type": "actor_network",
                    "person": label,
                    "related": hop1_label,
                    "related_type": hop1_type,
                    "content": f"{label}의 {relation_desc}: {hop1_label}",
                    "weight": base_weight * 1.2,
                    "description": display_desc
                })
                
                # 2-hop 관계: 같은 사건의 다른 인물
                if hop2_label and (label, hop2_label) not in seen_relations:
                    seen_relations.add((label, hop2_label))
                    display_desc = f"{label} ↔ [{hop1_label}] ↔ {hop2_label}"
                    paths.append({
                        "type": "actor_network",
                        "person": label,
                        "via_event": hop1_label,
                        "related_person": hop2_label,
                        "content": f"{label}와(과) {hop2_label}은(는) {hop1_label}에 함께 관여",
                        "weight": base_weight * 1.5,  # 2-hop은 더 높은 가중치
                        "description": display_desc
                    })
    
    return paths[:15]


def extract_timeline_paths(bindings: list, base_weight: float) -> list:
    """시간순 사건 경로 추출 + 인과관계 체인"""
    paths = []
    seen_events = set()
    
    for binding in bindings:
        event_binding = binding.get("event") or binding.get("entity") or {}
        event = event_binding.get("value", "").split("#")[-1] if event_binding else ""
        
        label_binding = binding.get("label") or {}
        label = label_binding.get("value", "") if label_binding else event
        
        year_binding = binding.get("year") or {}
        year = year_binding.get("value", "") if year_binding else ""
        
        summary_binding = binding.get("summary") or {}
        summary = summary_binding.get("value", "")[:100] if summary_binding.get("value") else ""
        
        # 인과관계 체인
        caused_by_binding = binding.get("causedBy") or {}
        caused_by_label_binding = binding.get("causedByLabel") or {}
        caused_by = caused_by_label_binding.get("value", "") if caused_by_label_binding else ""
        
        leads_to_binding = binding.get("leadsTo") or {}
        leads_to_label_binding = binding.get("leadsToLabel") or {}
        leads_to = leads_to_label_binding.get("value", "") if leads_to_label_binding else ""
        
        if event and label and label not in seen_events:
            seen_events.add(label)
            
            # 기본 시간 정보
            year_str = f"{year}년" if year else ""
            
            # 인과관계 체인 구성
            chain_parts = []
            if caused_by:
                chain_parts.append(f"원인: {caused_by}")
            if leads_to:
                chain_parts.append(f"결과: {leads_to}")
            
            if chain_parts:
                # 인과관계가 있으면 체인으로 표시
                chain_desc = " → ".join([caused_by, label, leads_to]) if caused_by and leads_to else ""
                if not chain_desc:
                    chain_desc = f"{caused_by} → {label}" if caused_by else f"{label} → {leads_to}"
                
                content = f"{year_str} {chain_desc}" if year_str else chain_desc
                display_desc = f"[인과] {content}"
            else:
                content = f"{year_str} {label}: {summary}" if summary else f"{year_str} {label}"
                display_desc = content
            
            paths.append({
                "type": "timeline",
                "event": label,
                "year": year,
                "caused_by": caused_by,
                "leads_to": leads_to,
                "content": summary or f"{label} ({year_str})",
                "weight": base_weight * (1.3 if (caused_by or leads_to) else 1.0),  # 인과관계 있으면 가중치 높임
                "description": display_desc
            })
    
    return paths[:15]


def extract_similar_events_paths(bindings: list, base_weight: float) -> list:
    """유사 사건 경로 추출 (Milvus 벡터 검색 결과)"""
    paths = []
    
    for binding in bindings:
        entity_binding = binding.get("entity") or {}
        entity = entity_binding.get("value", "").split("#")[-1] if entity_binding else ""
        
        label_binding = binding.get("label") or {}
        label = label_binding.get("value", "") if label_binding else entity
        
        category_binding = binding.get("category") or {}
        category = category_binding.get("value", "") if category_binding else ""
        
        summary_binding = binding.get("summary") or {}
        summary = summary_binding.get("value", "")[:150] if summary_binding else ""
        
        score_binding = binding.get("score") or {}
        score = float(score_binding.get("value", 0)) if score_binding else 0.0
        
        if entity or label:
            # 설명에 summary 포함 (유사도는 내부용)
            display_name = label or entity
            display_desc = f"{display_name}: {summary}" if summary else display_name
            
            paths.append({
                "type": "similar_events",
                "event": display_name,
                "category": category,
                "content": summary,  # 원본 요약
                "similarity_score": score,
                "weight": base_weight * (1.0 + score),  # 유사도 점수 반영
                "description": display_desc  # 표시용 (유사도 숫자 제외)
            })
    
    return paths[:10]


def extract_background_paths(bindings: list, base_weight: float) -> list:
    """배경 정보 경로 추출 + 관련 정책/제도 확장"""
    paths = []
    seen_entities = set()
    
    for binding in bindings:
        entity_binding = binding.get("entity") or {}
        entity = entity_binding.get("value", "").split("#")[-1] if entity_binding else ""
        
        label_binding = binding.get("label") or {}
        label = label_binding.get("value", "") if label_binding else entity
        
        summary_binding = binding.get("summary") or {}
        summary = summary_binding.get("value", "")[:200] if summary_binding.get("value") else ""
        
        category_binding = binding.get("category") or {}
        category = category_binding.get("value", "") if category_binding else ""
        
        # 관련 정책/제도 확장
        policy_label_binding = binding.get("policyLabel") or {}
        policy_label = policy_label_binding.get("value", "") if policy_label_binding else ""
        policy_summary_binding = binding.get("policySummary") or {}
        policy_summary = policy_summary_binding.get("value", "")[:100] if policy_summary_binding.get("value") else ""
        
        if entity and label:
            display_name = label
            
            # 기본 엔티티 정보
            if display_name not in seen_entities:
                seen_entities.add(display_name)
                
                if summary:
                    display_desc = f"{display_name}: {summary}"
                    content = summary
                else:
                    display_desc = display_name
                    content = f"{display_name} 관련 배경 정보"
                
                paths.append({
                    "type": "background",
                    "entity": display_name,
                    "content": content,
                    "category": category,
                    "weight": base_weight,
                    "description": display_desc
                })
            
            # 관련 정책/제도 확장 결과 추가
            if policy_label and policy_label not in seen_entities:
                seen_entities.add(policy_label)
                
                policy_content = policy_summary or f"{label}과(와) 관련된 정책"
                display_desc = f"[관련 정책] {policy_label}: {policy_content}"
                
                paths.append({
                    "type": "background",
                    "entity": policy_label,
                    "related_to": display_name,
                    "content": policy_content,
                    "weight": base_weight * 1.2,  # 관련 정책은 가중치 높임
                    "description": display_desc
                })
    
    return paths[:15]


# ========================================
# 범용 관계 검색 경로 추출 함수들
# ========================================

def extract_outgoing_relations(bindings: list, base_weight: float, query_entities: list = None) -> list:
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

        # Relevance score 계산
        relevance_score = calculate_path_relevance(binding, query_entities)

        # 프로퍼티 이름을 읽기 좋게 변환
        predicate_display = predicate.replace("has", "").replace("_", " ")

        description = f"{entity_label} → [{predicate_display}] → {obj_label}"

        paths.append({
            "type": "outgoing_relation",
            "subject": entity_label,
            "predicate": predicate,
            "predicate_display": predicate_display,
            "object": obj_label,
            "weight": base_weight * relevance_score,  # base_weight × relevance_score
            "relevance_score": relevance_score,
            "description": description,
            "raw_data": binding  # 원본 데이터 보관
        })

    return paths[:30]


def extract_incoming_relations(bindings: list, base_weight: float, query_entities: list = None) -> list:
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

        # Relevance score 계산
        relevance_score = calculate_path_relevance(binding, query_entities)

        # 프로퍼티 이름을 읽기 좋게 변환
        predicate_display = predicate.replace("has", "").replace("_", " ")

        description = f"{subject_label} → [{predicate_display}] → {entity_label}"

        paths.append({
            "type": "incoming_relation",
            "subject": subject_label,
            "predicate": predicate,
            "predicate_display": predicate_display,
            "object": entity_label,
            "weight": base_weight * relevance_score * 1.2,  # 들어오는 관계는 20% 추가 부스트
            "relevance_score": relevance_score,
            "description": description,
            "raw_data": binding
        })

    return paths[:30]


def extract_entity_properties(bindings: list, base_weight: float, query_entities: list = None) -> list:
    """엔티티의 모든 속성 추출 (리터럴 값)"""
    paths = []
    seen = set()

    for binding in bindings:
        entity_label = binding.get("entityLabel", {}).get("value", "")
        predicate = binding.get("predicate", {}).get("value", "").split("#")[-1]
        value = binding.get("value", {}).get("value", "")

        # 중복 제거
        key = f"{entity_label}-{predicate}"
        if key in seen or not predicate or not value:
            continue
        seen.add(key)

        # Relevance score 계산
        relevance_score = calculate_path_relevance(binding, query_entities)

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


def extract_connected_entities(bindings: list, base_weight: float) -> list:
    """연결된 엔티티들 간의 관계 추출 (2-hop)"""
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
        
        # 프로퍼티 이름을 읽기 좋게 변환
        predicate_display = predicate.replace("has", "").replace("_", " ")
        
        description = f"{entity1} ↔ [{predicate_display}] ↔ {entity2}"
        
        paths.append({
            "type": "connection",
            "entity1": entity1,
            "predicate": predicate,
            "predicate_display": predicate_display,
            "entity2": entity2,
            "weight": base_weight * 0.8,  # 가중치 낮춤 (무관한 결과 방지)
            "description": description
        })
    
    return paths[:20]


def extract_type_and_summary(bindings: list, base_weight: float) -> list:
    """엔티티 타입과 요약 정보 추출"""
    paths = []
    seen = set()
    
    for binding in bindings:
        entity_label = binding.get("entityLabel", {}).get("value", "")
        entity_type = binding.get("type", {}).get("value", "").split("#")[-1] if binding.get("type") else ""
        summary = binding.get("summary", {}).get("value", "") if binding.get("summary") else ""
        category = binding.get("category", {}).get("value", "") if binding.get("category") else ""
        year = binding.get("year", {}).get("value", "") if binding.get("year") else ""
        
        if entity_label in seen:
            continue
        seen.add(entity_label)
        
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
            "description": description
        })
    
    return paths[:20]


def extract_generic_paths(bindings: list, base_weight: float, thread_type: str) -> list:
    """범용 경로 추출 (알 수 없는 Thread 타입용)"""
    paths = []
    
    for i, binding in enumerate(bindings[:20]):
        # 바인딩에서 모든 값 추출
        parts = []
        for key, value in binding.items():
            if isinstance(value, dict) and "value" in value:
                val = value["value"]
                # URI면 마지막 부분만
                if val.startswith("http"):
                    val = val.split("#")[-1].split("/")[-1]
                parts.append(f"{key}: {val[:50]}")
        
        if parts:
            description = " | ".join(parts)
            paths.append({
                "type": thread_type,
                "index": i,
                "weight": base_weight,
                "description": description,
                "raw_binding": {k: v.get("value", "") if isinstance(v, dict) else v for k, v in binding.items()}
            })
    
    return paths
