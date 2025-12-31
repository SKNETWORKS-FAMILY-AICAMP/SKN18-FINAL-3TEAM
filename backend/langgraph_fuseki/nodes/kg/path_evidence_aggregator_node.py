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
from backend.langgraph_fuseki.utils.fuseki_client import execute_sparql_query
from backend.langgraph_fuseki.utils.evidence_scoring import calculate_final_evidence_score
from langchain_openai import ChatOpenAI


def detect_entity_match_type(path_data: dict, query_entities: list, thread_type: str) -> str:
    """
    Entity 매칭 타입만 감지 (부스트 없음)
    
    ⭐ 핵심 변경: 부스트 제거, 매칭 타입만 반환
    - evidence_scoring.py에서 entity_match_type으로 점수 계산에 사용
    
    Args:
        path_data: 경로 데이터 (binding 정보)
        query_entities: 쿼리에서 추출된 엔티티 리스트
        thread_type: Thread 타입

    Returns:
        "exact" | "partial" | "normalized" | "none"
    """
    if not query_entities:
        return "none"

    subject = path_data.get("subject", {}).get("value", "")
    obj = path_data.get("object", {}).get("value", "")
    entity_label = path_data.get("entityLabel", {}).get("value", "")
    subject_label = path_data.get("subjectLabel", {}).get("value", "")
    object_label = path_data.get("objectLabel", {}).get("value", "")

    def normalize_name(name):
        if not name:
            return ""
        return name.replace(" ", "").replace("_", "").lower()

    # Thread별 매칭 대상 선택
    if thread_type == "incoming_relations":
        priority_sources = [entity_label, subject_label]
    elif thread_type == "outgoing_relations":
        priority_sources = [entity_label, object_label]
    else:
        priority_sources = [entity_label, subject_label, object_label]

    all_entity_names = []
    all_entity_names_normalized = []

    for name_source in priority_sources:
        if name_source:
            raw_name = name_source.split("#")[-1] if "#" in name_source else name_source
            all_entity_names.append(raw_name)
            all_entity_names_normalized.append(normalize_name(raw_name))

    # URI도 추가
    for uri_source in [subject, obj]:
        if uri_source:
            raw_name = uri_source.split("#")[-1] if "#" in uri_source else uri_source
            if raw_name not in all_entity_names:
                all_entity_names.append(raw_name)
                all_entity_names_normalized.append(normalize_name(raw_name))

    # 매칭 타입 감지 (우선순위: exact > partial > normalized)
    for entity in query_entities:
        entity_name = entity.get("name", "") or entity.get("label", "")
        if not entity_name:
            continue

        entity_name_normalized = normalize_name(entity_name)

        # Exact match
        if entity_name in all_entity_names or entity_name_normalized in all_entity_names_normalized:
            return "exact"

        # Partial match
        if any(entity_name in name or name in entity_name for name in all_entity_names if name):
            return "partial"

        # Normalized match
        if any(entity_name_normalized in norm_name or norm_name in entity_name_normalized
               for norm_name in all_entity_names_normalized if norm_name):
            return "normalized"

    return "none"


def detect_convergence_nodes(inference_paths: dict, query_entities: list) -> list:
    """
    수렴 노드 감지 및 상세 정보 조회: 여러 쿼리 엔티티를 연결하는 중간 노드 찾기

    Args:
        inference_paths: 쓰레드별 추론 경로
        query_entities: 추출된 엔티티 목록

    Returns:
        수렴 노드 리스트 (각 노드의 URI, 연결된 엔티티, 속성, 관계 정보 포함)
        [{"uri": "...", "label": "...", "count": N, "connected_entities": [...],
          "properties": {...}, "relations": [...]}]
    """
    from backend.langgraph_fuseki.config import FUSEKI_URL
    import requests

    entity_connections = {}  # node_uri → set of query entities it connects

    # 모든 경로에서 엔티티 간 연결 추출
    for thread_type, paths in inference_paths.items():
        for path in paths:
            raw_data = path.get("raw_data", {})

            # connected_entities 쓰레드에서 수렴 노드 추출
            if thread_type == "connected_entities":
                convergence_node_raw = raw_data.get("convergence_node")
                label1_raw = raw_data.get("label1", "")
                label2_raw = raw_data.get("label2", "")

                # dict 형태면 value 추출, 아니면 그대로 사용
                if isinstance(convergence_node_raw, dict):
                    convergence_node = convergence_node_raw.get("value", "")
                else:
                    convergence_node = convergence_node_raw
                
                if isinstance(label1_raw, dict):
                    entity1_label = label1_raw.get("value", "")
                else:
                    entity1_label = label1_raw
                
                if isinstance(label2_raw, dict):
                    entity2_label = label2_raw.get("value", "")
                else:
                    entity2_label = label2_raw

                if convergence_node:
                    if convergence_node not in entity_connections:
                        entity_connections[convergence_node] = set()

                    if entity1_label:
                        entity_connections[convergence_node].add(entity1_label)
                    if entity2_label:
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
    convergence_candidates = {}
    for node_uri, connected_entities in entity_connections.items():
        if len(connected_entities) >= 2:
            convergence_candidates[node_uri] = {
                "count": len(connected_entities),
                "connected_entities": list(connected_entities)
            }

    if not convergence_candidates:
        return []

    # 각 수렴 노드에 대해 추가 SPARQL 조회
    convergence_nodes_with_details = []

    for node_uri, info in convergence_candidates.items():
        # URI 형식 처리
        if node_uri.startswith("hist:"):
            uri_sparql = node_uri
        elif node_uri.startswith("http://"):
            uri_sparql = f"<{node_uri}>"
        elif node_uri.startswith("<"):
            uri_sparql = node_uri
        else:
            uri_sparql = f"<{node_uri}>"

        # SPARQL 쿼리: 수렴 노드의 속성 및 관계 조회
        sparql_query = f"""
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            SELECT ?label ?type ?predicate ?value ?relatedLabel WHERE {{
                # 노드 라벨
                OPTIONAL {{ {uri_sparql} rdfs:label ?label . }}

                # 노드 타입
                OPTIONAL {{ {uri_sparql} rdf:type ?type . }}

                # 노드의 속성 (리터럴 값)
                OPTIONAL {{
                    {uri_sparql} ?predicate ?value .
                    FILTER(isLiteral(?value))
                    FILTER(?predicate != rdfs:label)
                }}

                # 노드의 관계 (다른 엔티티와의 연결)
                OPTIONAL {{
                    {{
                        {uri_sparql} ?predicate ?related .
                        ?related rdfs:label ?relatedLabel .
                        FILTER(?predicate != rdf:type && ?predicate != rdfs:label)
                    }}
                    UNION
                    {{
                        ?related ?predicate {uri_sparql} .
                        ?related rdfs:label ?relatedLabel .
                        FILTER(?predicate != rdf:type && ?predicate != rdfs:label)
                    }}
                }}
            }} LIMIT 50
        """

        try:
            import requests  # 로컬 import 유지
            from backend.langgraph_fuseki.config import FUSEKI_URL

            results = execute_sparql_query(FUSEKI_URL, sparql_query, timeout=3)
            if results:
                bindings = results.get("results", {}).get("bindings", [])

                # 결과 파싱
                node_label = ""
                node_type = ""
                properties = {}
                relations = []

                for binding in bindings:
                    if not node_label and binding.get("label"):
                        node_label = binding.get("label", {}).get("value", "")

                    if not node_type and binding.get("type"):
                        node_type = binding.get("type", {}).get("value", "").split("#")[-1]

                    # 속성 추가
                    predicate = binding.get("predicate", {}).get("value", "").split("#")[-1]
                    value = binding.get("value", {}).get("value", "")
                    if predicate and value and predicate not in properties:
                        properties[predicate] = value

                    # 관계 추가
                    related_label = binding.get("relatedLabel", {}).get("value", "")
                    if predicate and related_label:
                        relation_key = f"{predicate}:{related_label}"
                        if relation_key not in [r["key"] for r in relations]:
                            relations.append({
                                "predicate": predicate,
                                "related": related_label,
                                "key": relation_key
                            })

                convergence_nodes_with_details.append({
                    "uri": node_uri,
                    "label": node_label or extract_label_from_uri(node_uri),
                    "type": node_type,
                    "count": info["count"],
                    "connected_entities": info["connected_entities"],
                    "properties": properties,
                    "relations": relations[:10]  # 관계는 최대 10개만
                })

        except Exception as e:
            # SPARQL 실패 시 기본 정보만 포함
            convergence_nodes_with_details.append({
                "uri": node_uri,
                "label": extract_label_from_uri(node_uri),
                "type": "",
                "count": info["count"],
                "connected_entities": info["connected_entities"],
                "properties": {},
                "relations": []
            })

    return convergence_nodes_with_details


def extract_label_from_uri(uri: str) -> str:
    """URI에서 라벨 추출 (hist:Person_정약용 → 정약용)"""
    if "#" in uri:
        return uri.split("#")[-1]
    elif "/" in uri:
        return uri.split("/")[-1]
    return uri



def extract_outgoing_relations(bindings: list, base_weight: float, query_entities: list = None, entity_boost_mode: str = None, selected_properties: list = None) -> list:
    """이미 검색된 결과(bindings)에서 엔티티의 나가는 관계 경로 추출 (엔티티 → ?)
    
    주의: 이 함수는 새로운 지식 검색을 수행하지 않습니다.
    parallel_knowledge_retrieval_node에서 이미 검색된 결과를 후처리하는 함수입니다.
    
    초기 프로퍼티 의도를 통해 선택된 그룹의 predicate만 사용합니다.
    selected_properties가 제공되면 해당 목록에 포함된 predicate만 추출합니다.
    
    주의: BFS 경로(method: "bidirectional_bfs")는 predicate 필터링을 건너뜁니다.
    
    필터링이 필요한 이유:
    1. Fallback 쿼리: generate_fallback_sparql은 selected_properties를 받지 않아 필터링 안 됨
    2. 방어적 프로그래밍: SPARQL 쿼리에서 필터링이 누락된 경우를 대비
    3. 일관성: 모든 경로에 동일한 필터링 로직 적용
    """
    paths = []
    seen = set()
    
    # selected_properties를 집합으로 변환 (빠른 검색용)
    allowed_predicates = set(selected_properties) if selected_properties else None

    for binding in bindings:
        entity_label = binding.get("entityLabel", {}).get("value", "")
        predicate = binding.get("predicate", {}).get("value", "").split("#")[-1]
        obj = binding.get("object", {}).get("value", "")
        obj_label = binding.get("objectLabel", {}).get("value", "") or obj.split("#")[-1]

        # BFS 경로는 predicate 필터링 건너뛰기
        is_bfs_path = binding.get("method", {}).get("value", "") == "bidirectional_bfs"
        
        # predicate 필터링: selected_properties가 있으면 해당 목록에 포함된 것만 허용 (BFS 경로 제외)
        if not is_bfs_path and allowed_predicates is not None and predicate not in allowed_predicates:
            continue

        # 중복 제거
        key = f"{entity_label}-{predicate}-{obj_label}"
        if key in seen or not predicate:
            continue
        seen.add(key)

        # Entity 매칭 타입 감지 (테스트 모드용)
        entity_match_type = detect_entity_match_type(binding, query_entities, "outgoing_relations")

        # 테스트 모드 필터링
        if entity_boost_mode:
            if entity_boost_mode == "exact_match" and entity_match_type != "exact":
                continue
            elif entity_boost_mode == "partial_match" and entity_match_type != "partial":
                continue
            elif entity_boost_mode == "normalized_match" and entity_match_type != "normalized":
                continue
            elif entity_boost_mode == "penalty_match" and entity_match_type != "none":
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
            "weight": base_weight,  # 단순 가중치 (최종 점수는 evidence_scoring.py에서 계산)
            "entity_match_type": entity_match_type,  # ⭐ 점수 계산용
            "description": description,
            "raw_data": binding
        })

    # weight 기준으로 정렬 (내림차순)
    paths.sort(key=lambda x: x["weight"], reverse=True)
    return paths


def extract_incoming_relations(bindings: list, base_weight: float, query_entities: list = None, entity_boost_mode: str = None, selected_properties: list = None) -> list:
    """이미 검색된 결과(bindings)에서 엔티티로 들어오는 관계 경로 추출 (? → 엔티티)
    
    주의: 이 함수는 새로운 지식 검색을 수행하지 않습니다.
    parallel_knowledge_retrieval_node에서 이미 검색된 결과를 후처리하는 함수입니다.
    
    초기 프로퍼티 의도를 통해 선택된 그룹의 predicate만 사용합니다.
    selected_properties가 제공되면 해당 목록에 포함된 predicate만 추출합니다.
    
    주의: BFS 경로(method: "bidirectional_bfs")는 predicate 필터링을 건너뜁니다.
    
    필터링이 필요한 이유:
    1. Fallback 쿼리: generate_fallback_sparql은 selected_properties를 받지 않아 필터링 안 됨
    2. 방어적 프로그래밍: SPARQL 쿼리에서 필터링이 누락된 경우를 대비
    3. 일관성: 모든 경로에 동일한 필터링 로직 적용
    """
    paths = []
    seen = set()
    
    # selected_properties를 집합으로 변환 (빠른 검색용)
    allowed_predicates = set(selected_properties) if selected_properties else None

    for binding in bindings:
        subject = binding.get("subject", {}).get("value", "")
        subject_label = binding.get("subjectLabel", {}).get("value", "") or subject.split("#")[-1]
        predicate = binding.get("predicate", {}).get("value", "").split("#")[-1]
        entity_label = binding.get("entityLabel", {}).get("value", "")

        # BFS 경로는 predicate 필터링 건너뛰기
        is_bfs_path = binding.get("method", {}).get("value", "") == "bidirectional_bfs"
        
        # predicate 필터링: selected_properties가 있으면 해당 목록에 포함된 것만 허용 (BFS 경로 제외)
        if not is_bfs_path and allowed_predicates is not None and predicate not in allowed_predicates:
            continue

        # 중복 제거
        key = f"{subject_label}-{predicate}-{entity_label}"
        if key in seen or not predicate:
            continue
        seen.add(key)

        # Entity 매칭 타입 감지 (테스트 모드용)
        entity_match_type = detect_entity_match_type(binding, query_entities, "incoming_relations")

        # 테스트 모드 필터링
        if entity_boost_mode:
            if entity_boost_mode == "exact_match" and entity_match_type != "exact":
                continue
            elif entity_boost_mode == "partial_match" and entity_match_type != "partial":
                continue
            elif entity_boost_mode == "normalized_match" and entity_match_type != "normalized":
                continue
            elif entity_boost_mode == "penalty_match" and entity_match_type != "none":
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
            "weight": base_weight,  # 단순 가중치
            "entity_match_type": entity_match_type,  # ⭐ 점수 계산용
            "description": description,
            "raw_data": binding
        })

    # weight 기준으로 정렬 (내림차순)
    paths.sort(key=lambda x: x["weight"], reverse=True)
    return paths


def extract_entity_properties(bindings: list, base_weight: float, query_entities: list = None, entity_boost_mode: str = None, selected_properties: list = None) -> list:
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

        # Entity 매칭 타입 감지 (테스트 모드용)
        entity_match_type = detect_entity_match_type(binding, query_entities, "entity_properties")

        # 테스트 모드 필터링
        if entity_boost_mode:
            if entity_boost_mode == "exact_match" and entity_match_type != "exact":
                continue
            elif entity_boost_mode == "partial_match" and entity_match_type != "partial":
                continue
            elif entity_boost_mode == "normalized_match" and entity_match_type != "normalized":
                continue
            elif entity_boost_mode == "penalty_match" and entity_match_type != "none":
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
            "weight": base_weight,  # 단순 가중치
            "entity_match_type": entity_match_type,  # ⭐ 점수 계산용
            "description": description,
            "raw_data": binding
        })

    # weight 기준으로 정렬 (내림차순)
    paths.sort(key=lambda x: x["weight"], reverse=True)
    return paths


def extract_connected_entities(bindings: list, base_weight: float, query_entities: list = None, entity_boost_mode: str = None, selected_properties: list = None) -> list:
    """
    연결된 엔티티들 간의 관계 추출 (최대 3-hop)
    
    parallel_knowledge_retrieval_node에서 BFS는 max_depth=3으로 탐색하므로,
    최대 3-hop까지의 경로를 포함합니다.
    
    주의: BFS 경로(method: "bidirectional_bfs")는 predicate 필터링을 건너뜁니다.
    """
    paths = []
    seen = set()
    
    # selected_properties를 집합으로 변환 (빠른 검색용)
    allowed_predicates = set(selected_properties) if selected_properties else None

    for binding in bindings:
        entity1 = binding.get("label1", {}).get("value", "")
        predicate = binding.get("predicate", {}).get("value", "").split("#")[-1] if binding.get("predicate") else ""
        entity2 = binding.get("label2", {}).get("value", "")
        
        # BFS 경로 확인
        is_bfs_path = binding.get("method", {}).get("value", "") == "bidirectional_bfs"
        
        # BFS 경로가 아닌 경우에만 predicate 필터링 적용
        if not is_bfs_path:
            # predicate 필터링: selected_properties가 있으면 해당 목록에 포함된 것만 허용
            if allowed_predicates is not None and predicate and predicate not in allowed_predicates:
                continue

        # 중복 제거
        # BFS 경로는 path 정보로, 일반 경로는 predicate로 구분
        if is_bfs_path:
            path = binding.get("path", {}).get("value", "")
            key = f"{entity1}-BFS-{entity2}-{path}"
        else:
            key = f"{entity1}-{predicate}-{entity2}"
            
        if key in seen:
            continue
        seen.add(key)
        
        # BFS 경로가 아닌 경우 predicate가 없으면 건너뛰기
        if not is_bfs_path and not predicate:
            continue

        # Entity 매칭 타입 감지 (테스트 모드용)
        entity_match_type = detect_entity_match_type(binding, query_entities, "connected_entities")

        # 테스트 모드 필터링
        if entity_boost_mode:
            if entity_boost_mode == "exact_match" and entity_match_type != "exact":
                continue
            elif entity_boost_mode == "partial_match" and entity_match_type != "partial":
                continue
            elif entity_boost_mode == "normalized_match" and entity_match_type != "normalized":
                continue
            elif entity_boost_mode == "penalty_match" and entity_match_type != "none":
                continue

        # BFS 경로와 일반 경로를 다르게 처리
        if is_bfs_path:
            # BFS 경로: path 정보 사용
            path = binding.get("path", {}).get("value", "")
            path_length = binding.get("path_length", {}).get("value", "")
            convergence = binding.get("convergence_node", {}).get("value", "")
            
            description = f"{entity1} ↔ {entity2} (경로: {path})"
            
            paths.append({
                "type": "connection",
                "entity1": entity1,
                "entity2": entity2,
                "predicate": "",  # BFS 경로는 predicate 없음
                "predicate_display": "BFS 경로",
                "path": path,
                "path_length": path_length,
                "convergence_node": convergence,
                "method": "bidirectional_bfs",
                "weight": base_weight,  # 단순 가중치
                "entity_match_type": entity_match_type,  # ⭐ 점수 계산용
                "description": description,
                "raw_data": binding
            })
        else:
            # 일반 경로: predicate 사용
            # 프로퍼티 이름을 읽기 좋게 변환
            predicate_display = predicate.replace("has", "").replace("_", " ")

            description = f"{entity1} ↔ [{predicate_display}] ↔ {entity2}"

            paths.append({
                "type": "connection",
                "entity1": entity1,
                "predicate": predicate,
                "predicate_display": predicate_display,
                "entity2": entity2,
                "weight": base_weight,  # 단순 가중치
                "entity_match_type": entity_match_type,  # ⭐ 점수 계산용
                "description": description,
                "raw_data": binding
            })

    # weight 기준으로 정렬 (내림차순)
    paths.sort(key=lambda x: x["weight"], reverse=True)
    return paths


def extract_type_and_summary(bindings: list, base_weight: float, query_entities: list = None, entity_boost_mode: str = None, selected_properties: list = None) -> list:
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

        # Entity 매칭 타입 감지 (테스트 모드용)
        entity_match_type = detect_entity_match_type(binding, query_entities, "type_and_summary")

        # 테스트 모드 필터링
        if entity_boost_mode:
            if entity_boost_mode == "exact_match" and entity_match_type != "exact":
                continue
            elif entity_boost_mode == "partial_match" and entity_match_type != "partial":
                continue
            elif entity_boost_mode == "normalized_match" and entity_match_type != "normalized":
                continue
            elif entity_boost_mode == "penalty_match" and entity_match_type != "none":
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
            "weight": base_weight,  # 단순 가중치
            "entity_match_type": entity_match_type,  # ⭐ 점수 계산용
            "description": description,
            "raw_data": binding
        })
    
    # weight 기준으로 정렬 (내림차순)
    paths.sort(key=lambda x: x["weight"], reverse=True)
    return paths


def select_top_evidences_with_llm(
    candidate_evidences: list,
    query: str,
    query_intent: str = "",
    query_type: str = "causal",
    top_k: int = None,  # None이면 LLM이 개수 결정
    state: GraphState = None
) -> list:
    """
    LLM을 사용하여 질문 의도에 맞는 상위 근거 선택
    
    Args:
        candidate_evidences: 점수 기반으로 선별된 후보 근거 리스트
        query: 사용자 질문
        query_intent: 질문의 핵심 의도
        query_type: 질문 유형 (causal, deep_analysis 등)
        top_k: 선택할 근거 개수 (None이면 LLM이 결정)
    
    Returns:
        LLM이 선택한 근거 리스트
    """
    if len(candidate_evidences) == 0:
        return []
    
    # top_k가 None이 아니고 후보가 그보다 적으면 그대로 반환
    if top_k is not None and len(candidate_evidences) <= top_k:
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
        
        # 쿼리 타입별 권장 개수 (가이드라인)
        OPTIMAL_EVIDENCE_COUNT = {
            "factual": 5,
            "causal": 8,
            "comparative": 10,
            "deep_analysis": 13
        }
        recommended_count = OPTIMAL_EVIDENCE_COUNT.get(query_type, 10)
        
        if top_k is not None:
            # top_k가 지정된 경우: 기존 로직 (하위 호환성)
            count_instruction = f"정확히 **{top_k}개**를 선택하세요."
        else:
            # top_k가 None인 경우: LLM이 개수 결정
            count_instruction = f"""**개수 결정**: 질문 유형({query_type})에 따라 권장 개수는 약 {recommended_count}개입니다. 
질문에 답변하기에 충분한 개수를 스스로 판단하여 선택하세요. 
너무 적으면 정보가 부족하고, 너무 많으면 불필요한 정보가 포함될 수 있습니다."""
        
        prompt = f"""당신은 역사 질문에 가장 적합한 근거를 선택하는 전문가입니다.

## 질문
{query}
{intent_info}질문 유형: {query_type}

## 후보 근거 목록 (총 {len(candidate_evidences)}개)
아래 근거들은 점수 기반으로 선별된 상위 {len(candidate_evidences)}개 후보입니다. 질문의 의도와 가장 관련성이 높은 근거를 선택하세요.

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
- {count_instruction}
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
        
        # top_k가 지정된 경우에만 개수 제한 및 보완
        if top_k is not None:
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
        else:
            # LLM이 결정한 개수 그대로 반환
            return selected_evidences
        
    except Exception as e:
        print(f"        └─ LLM 기반 선택 실패: {e}, 점수 기반으로 대체")
        # 실패 시 점수 기반으로 대체
        if top_k is not None:
            return candidate_evidences[:top_k]
        else:
            # top_k가 None이면 권장 개수만큼 반환
            OPTIMAL_EVIDENCE_COUNT = {
                "factual": 5,
                "causal": 8,
                "comparative": 10,
                "deep_analysis": 13
            }
            recommended_count = OPTIMAL_EVIDENCE_COUNT.get(query_type, 10)
            return candidate_evidences[:recommended_count]


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
    expanded_entities = state.get("expanded_entities", [])  # 확장된 엔티티 정보
    selected_properties = state.get("selected_properties", [])  # Stage 1-B에서 선택된 프로퍼티
    test_config = state.get("test_config")  # 테스트 설정

    # 테스트 설정 추출
    entity_boost_mode = None
    thread_config = None
    if test_config:
        entity_boost_mode = test_config.get("entity_boost_mode")
        thread_config = test_config.get("aggregator_threads")

    print(f"\n{'='*70}")
    print(f"[Stage 5/6] 경로 추출 및 근거 통합 (Path Evidence Aggregator)")
    print(f"{'='*70}")
    if entity_boost_mode:
        print(f"  ├─ [테스트 모드] Entity Boost Mode: {entity_boost_mode}")
    if thread_config:
        print(f"  ├─ [테스트 모드] 활성화된 Thread:")
        for thread, enabled in thread_config.items():
            if enabled:
                print(f"  │  └─ {thread}: ON")

    # 1. Thread별 경로 추출
    inference_paths = {}

    for thread_type, result in parallel_results.items():
        # test_config에서 Thread 비활성화 확인
        if thread_config and not thread_config.get(thread_type, True):
            print(f"  ├─ {thread_type}: SKIPPED (테스트 모드로 비활성화)")
            inference_paths[thread_type] = []
            continue
        bindings = result.get("bindings", [])

        if not bindings:
            inference_paths[thread_type] = []
            continue

        # Thread별 경로 추출 - base_weight는 config에서 가져온 값 사용
        # thread_weights는 GraphState에서 전달됨 (config.py의 THREAD_WEIGHT_* 값들)
        base_weight = thread_weights.get(thread_type, 1.0)  # config 값 사용, 기본값 1.0

        if thread_type == "outgoing_relations":
            paths = extract_outgoing_relations(bindings, base_weight, query_entities, entity_boost_mode, selected_properties)
        elif thread_type == "incoming_relations":
            paths = extract_incoming_relations(bindings, base_weight, query_entities, entity_boost_mode, selected_properties)
        elif thread_type == "entity_properties":
            paths = extract_entity_properties(bindings, base_weight, query_entities, entity_boost_mode, selected_properties)
        elif thread_type == "connected_entities":
            paths = extract_connected_entities(bindings, base_weight, query_entities, entity_boost_mode, selected_properties)
        elif thread_type == "type_and_summary":
            paths = extract_type_and_summary(bindings, base_weight, query_entities, entity_boost_mode, selected_properties)
        else:
            # 알 수 없는 Thread는 빈 리스트
            paths = []

        inference_paths[thread_type] = paths

    # 총 경로 수 계산
    total_paths = sum(len(paths) for paths in inference_paths.values())
    print(f"  ├─ 경로 추출 완료: {total_paths}개 경로")

    # 2. 수렴 노드 감지 및 상세 정보 조회
    convergence_nodes_list = detect_convergence_nodes(inference_paths, query_entities)

    # 수렴 노드 URI를 집합으로 변환 (빠른 검색용)
    convergence_node_uris = {node["uri"] for node in convergence_nodes_list}

    if convergence_nodes_list:
        print(f"  ├─ 수렴 노드 감지: {len(convergence_nodes_list)}개")
        for i, node_info in enumerate(convergence_nodes_list[:3], 1):
            node_label = node_info["label"]
            connected = ", ".join(node_info["connected_entities"][:3])
            props_count = len(node_info.get("properties", {}))
            rels_count = len(node_info.get("relations", []))
            print(f"│ │  {i}. {node_label}")
            print(f"│ │     ├─ 연결 엔티티: {connected}")
            print(f"│ │     ├─ 속성: {props_count}개")
            print(f"│ │     └─ 관계: {rels_count}개")

    # 3. 모든 Thread의 경로를 하나로 병합
    all_evidences = []

    # Query metadata 준비 (v2.0 scoring system용)
    query = state.get("query", "")
    # 간단한 키워드 추출 (명사 추출)
    try:
        from kiwipiepy import Kiwi
        kiwi = Kiwi()
        tokens = kiwi.tokenize(query)
        core_keywords = [t.form for t in tokens if t.tag in ('NNG', 'NNP') and len(t.form) >= 2]
    except:
        import re
        core_keywords = re.findall(r'[가-힣]{2,}', query)

    query_metadata = {
        "keywords": core_keywords[:5],  # 최대 5개
        "query_type": query_type
    }

    for thread_type, paths in inference_paths.items():
        for path in paths:
            # 수렴 노드 플래그
            raw_data = path.get("raw_data", {})
            # convergence_node가 dict 형태면 value 추출
            convergence_node_raw = raw_data.get("convergence_node")
            if isinstance(convergence_node_raw, dict):
                convergence_node = convergence_node_raw.get("value", "")
            else:
                convergence_node = convergence_node_raw

            # Evidence metadata 추출 (v2.0 scoring system)
            expansion_method = raw_data.get("expansion_method", "none")
            entity_match_type = detect_entity_match_type(raw_data, query_entities, thread_type)

            # ⭐ 확장 방법 내 세부 정보 추출 (hop_count, year_distance, similarity)
            # 1. raw_data에서 직접 추출 시도
            hop_count = raw_data.get("hop_count")
            year_distance = raw_data.get("year_distance")
            pgvector_similarity = raw_data.get("pgvector_similarity") or raw_data.get("similarity")

            # 2. expanded_entities에서 확장 정보 찾기 (raw_data에 없을 경우)
            if expanded_entities and (hop_count is None or year_distance is None or pgvector_similarity is None):
                # path의 엔티티 URI나 label로 매칭
                path_entity_uri = None
                path_entity_label = None
                
                # raw_data에서 엔티티 정보 추출 (Thread 타입에 따라 다름)
                if thread_type in ["outgoing_relations", "incoming_relations"]:
                    path_entity_uri = raw_data.get("subject", {}).get("value", "") or raw_data.get("object", {}).get("value", "")
                    path_entity_label = raw_data.get("subjectLabel", {}).get("value", "") or raw_data.get("objectLabel", {}).get("value", "")
                elif thread_type == "entity_properties":
                    path_entity_uri = raw_data.get("entity", {}).get("value", "")
                    path_entity_label = raw_data.get("entityLabel", {}).get("value", "")
                elif thread_type in ["connected_entities", "type_and_summary"]:
                    path_entity_uri = raw_data.get("entity1", {}).get("value", "") or raw_data.get("entity2", {}).get("value", "")
                    path_entity_label = raw_data.get("label1", {}).get("value", "") or raw_data.get("label2", {}).get("value", "")
                
                # expanded_entities에서 매칭되는 엔티티 찾기
                for expanded_entity in expanded_entities:
                    expanded_uri = expanded_entity.get("uri", "")
                    expanded_name = expanded_entity.get("name", "")
                    
                    # URI 또는 이름으로 매칭
                    if (path_entity_uri and expanded_uri and path_entity_uri == expanded_uri) or \
                       (path_entity_label and expanded_name and path_entity_label == expanded_name):
                        # 확장 정보 추출
                        if expansion_method == "causal_chain" and hop_count is None:
                            hop_count = expanded_entity.get("hop_count")
                        elif expansion_method == "temporal" and year_distance is None:
                            year_distance = expanded_entity.get("year_distance")
                        elif expansion_method == "pgvector" and pgvector_similarity is None:
                            pgvector_similarity = expanded_entity.get("pgvector_similarity") or expanded_entity.get("similarity")
                        
                        break  # 첫 번째 매칭에서 중단

            # ⭐ 새로운 점수 계산 (v2.0 scoring system + 세부 점수 반영)
            # Predicate 정보 추출
            predicate_raw = raw_data.get("predicate", {})
            if isinstance(predicate_raw, dict):
                predicate_full = predicate_raw.get("value", "")
            else:
                predicate_full = predicate_raw or ""
            
            # predicate 이름만 추출 (URI에서 마지막 부분)
            predicate_name = ""
            if predicate_full:
                if "#" in predicate_full:
                    predicate_name = predicate_full.split("#")[-1]
                elif "/" in predicate_full:
                    predicate_name = predicate_full.split("/")[-1]
                else:
                    predicate_name = predicate_full

            evidence_metadata = {
                "expansion_method": expansion_method,
                "thread_type": thread_type,
                "entity_match_type": entity_match_type,
                "predicate": predicate_name,  # predicate 정보 추가
                "connected_keyword_count": 0,  # TODO: SPARQL 분석 결과 추가 가능
                # 확장 방법 내 세부 정보
                "hop_count": hop_count,
                "year_distance": year_distance,
                "pgvector_similarity": pgvector_similarity
            }

            # Baseline vs v3.0 구분: test_config에서 확인
            use_query_type_aware = True  # 기본값 (v3.0)
            if test_config:
                use_query_type_aware = test_config.get("use_query_type_aware", True)
            
            # calculate_final_evidence_score() 사용
            final_weight = calculate_final_evidence_score(
                evidence_metadata=evidence_metadata,
                query_metadata=query_metadata,
                base_weight=0.8,
                fit_weight=0.2,
                use_query_type_aware=use_query_type_aware
            )

            # ⭐ Trace 정보 구성 (프론트엔드 시각화용)
            # 경로 추적: 키워드 → 엔티티 → 프로퍼티/관계
            
            # 엔티티의 키워드 추적 정보 가져오기
            entity_name = raw_data.get("entityLabel", {}).get("value", "") or \
                         raw_data.get("subjectLabel", {}).get("value", "") or \
                         raw_data.get("label1", {}).get("value", "")
            
            # extracted_entities에서 해당 엔티티의 키워드 추적 정보 찾기
            keyword_trace_info = {}
            extracted_entities = state.get("extracted_entities", [])
            for entity in extracted_entities:
                if entity.get("name") == entity_name:
                    keyword_trace_info = entity.get("keyword_trace", {})
                    break
            
            trace_info = {
                "source_entity": {
                    "name": entity_name,
                    "type": raw_data.get("type", {}).get("value", "").split("#")[-1] if raw_data.get("type") else "",
                    "uri": raw_data.get("subject", {}).get("value", "") or
                          raw_data.get("entity1", {}).get("value", "")
                },
                "thread": thread_type,
                "predicate": raw_data.get("predicate", {}).get("value", "").split("#")[-1] if raw_data.get("predicate") else "",
                "predicate_display": path.get("predicate_display", ""),
                # 키워드 추적 정보 (핵심만)
                "matched_keyword": keyword_trace_info.get("matched_keyword", ""),
                "is_from_expansion": keyword_trace_info.get("is_from_expansion", False),
                "entity_match_type": entity_match_type,
                "expansion_method": expansion_method
            }

            evidence = {
                "type": thread_type,
                "description": path.get("description", ""),
                "weight": final_weight,  # 새로운 점수 (1점 만점)
                "relevance_score": path.get("relevance_score", 1.0),  # 유지 (참고용)
                "source": f"Thread: {thread_type}",
                "raw_data": path,
                "is_convergence": convergence_node in convergence_node_uris if convergence_node else False,
                "metadata": {
                    "expansion_method": expansion_method,
                    "thread_type": thread_type,
                    "entity_match_type": entity_match_type,
                },
                # 경로 추적 정보 (프론트엔드 시각화용)
                "trace": trace_info
            }

            all_evidences.append(evidence)

    # 4. 가중치 기준으로 정렬
    sorted_evidences = sorted(all_evidences, key=lambda x: x["weight"], reverse=True)

    # 쓰레드별 검색 결과 출력
    print(f"  │\n  │   [쓰레드별 검색 결과]")
    for thread_type, paths in inference_paths.items():
        if paths:
            print(f"  │     - {thread_type}: {len(paths)}개 경로")
            # 상위 3개만 미리보기
            for i, path in enumerate(paths[:3], 1):
                desc = path.get("description", "")[:50]
                weight = path.get("weight", 0)
                print(f"  │       {i}. {desc} (가중치: {weight:.3f})")
            if len(paths) > 3:
                print(f"  │       ... 외 {len(paths) - 3}개")

    # 전체 근거 목록 출력 (정렬 후)
    print(f"  │\n  │   [전체 근거 목록 (총 {len(sorted_evidences)}개, 가중치 순)]")
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
        
        print(f"  │     {i:2d}. [{type_display:12s}] {desc_display} (가중치: {weight:.4f})")
    if len(sorted_evidences) > 25:
        print(f"  │     ... 외 {len(sorted_evidences) - 25}개")


    # # 5. 점수 기반으로 쿼리 타입별 최적 개수 선택
    # # 5-1. 점수 기반으로 상위 후보 선별 (30-50개)
    # candidate_count = min(max(30, len(sorted_evidences) // 2), len(sorted_evidences))
    # # 쿼리 타입별 최적 Evidence 개수 (실험 데이터 기반)
    # # 출처: backend/ragas/ontology_evaluate/docs/experiments/EVIDENCE_CONTRIBUTION_ANALYSIS.md
    # OPTIMAL_EVIDENCE_COUNT = {
    #     "factual": 5,        # N=4~5 권장 (소수 핵심 정보, 상위 5개까지 0.55 유지)
    #     "causal": 8,         # N=5~8 권장 (인과 연결, 상위 8개까지 0.45 유지)
    #     "comparative": 10,   # N=7~10 권장 (간접기여 중심, 상위 10개까지 0.33 유지)
    #     "deep_analysis": 13  # N=10~15 권장 (다양한 정보, 상위 13개까지 0.81 유지)
    # }

    # query_type = state.get("query_type", "causal")
    # optimal_k = OPTIMAL_EVIDENCE_COUNT.get(query_type, 10)  # 기본값: 10개

    # # 점수 기반으로 상위 N개 선택 (LLM 없이)
    # top_evidences = sorted_evidences[:optimal_k]
    # print(f"  │\n  │   [점수 기반 근거 선택]")
    # print(f"  │     - 최종 선택: {len(top_evidences)}개 (점수 기반, {query_type} 최적: {optimal_k}개)")

    # 5. 하이브리드 방식: 점수 기반 선별 → LLM 기반 최종 선택
    # 5-1. 점수 기반으로 상위 후보 선별 (최소 30개, 최대 전체 개수)
    candidate_count = min(max(30, len(sorted_evidences) // 2), len(sorted_evidences))
    candidate_evidences = sorted_evidences[:candidate_count]
    
    print(f"  │\n  │   [LLM 기반 근거 선택]")
    print(f"  │     - 후보 근거: {len(candidate_evidences)}개 / 전체 {len(sorted_evidences)}개 (점수 기반 선별)")
    
    # 5-2. LLM이 질문 의도에 맞는 근거 선택 (개수는 LLM이 결정)
    # 쿼리 타입별 최적 Evidence 개수 (가이드라인으로 사용)
    OPTIMAL_EVIDENCE_COUNT = {
        "factual": 5,        # N=4~5 권장 (소수 핵심 정보, 상위 5개까지 0.55 유지)
        "causal": 8,         # N=5~8 권장 (인과 연결, 상위 8개까지 0.45 유지)
        "comparative": 10,   # N=7~10 권장 (간접기여 중심, 상위 10개까지 0.33 유지)
        "deep_analysis": 13  # N=10~15 권장 (다양한 정보, 상위 13개까지 0.81 유지)
    }

    query = state.get("query", "")
    query_intent = state.get("query_intent", "")
    query_type = state.get("query_type", "causal")


    # LLM이 직접 evidence 개수를 결정하도록 호출 (top_k=None)
    # OPTIMAL_EVIDENCE_COUNT는 가이드라인으로만 사용됨
    top_evidences = select_top_evidences_with_llm(
        candidate_evidences,
        query,
        query_intent,
        query_type,
        state=state,
        top_k=None  # LLM이 개수 결정 (OPTIMAL_EVIDENCE_COUNT는 가이드라인으로 사용)
    )
    optimal_k = OPTIMAL_EVIDENCE_COUNT.get(query_type, 10)
    print(f"  │     - 최종 선택: {len(top_evidences)}개 (LLM 판단, {query_type} 권장: {optimal_k}개)")

    # 6. 순위 부여
    for i, ev in enumerate(top_evidences, 1):
        ev["rank"] = i

    # 최종 선택된 근거 목록
    if top_evidences:
        print(f"  │\n  │   [최종 근거 목록 (상위 {len(top_evidences)}개)]")
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

            print(f"  │   {rank}. [{type_display:12s}] {desc_display} (가중치: {weight:.2%})")

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
        "convergence_nodes": convergence_nodes_list,
        "executed_nodes": state.get("executed_nodes", []) + ["path_evidence_aggregator"],
        "node_execution_times": node_times
    }

