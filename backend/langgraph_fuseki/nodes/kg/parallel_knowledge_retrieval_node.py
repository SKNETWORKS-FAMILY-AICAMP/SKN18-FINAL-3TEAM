"""
Parallel Knowledge Retrieval Node

5개의 Thread에서 쿼리 생성 + 지식 검색을 병렬로 수행
- ThreadPoolExecutor로 병렬 처리
- 각 Thread마다: SPARQL 템플릿 쿼리 → Fuseki 직접 쿼리
- 지식 검색 결과를 TTL 형식으로 저장
"""

import os
import time
import requests
import concurrent.futures
from datetime import datetime
from pathlib import Path
from backend.langgraph_fuseki.state import GraphState
from backend.langgraph_fuseki.config import (
    FUSEKI_URL,
    INFERENCE_OUTPUT_DIR,
    THREAD_WEIGHT_OUTGOING_RELATIONS,
    THREAD_WEIGHT_INCOMING_RELATIONS,
    THREAD_WEIGHT_CONNECTED_ENTITIES,
    THREAD_WEIGHT_ENTITY_PROPERTIES,
    THREAD_WEIGHT_TYPE_AND_SUMMARY
)


SAVE_INFERENCE_TRIPLES = os.getenv("SAVE_INFERENCE_TRIPLES", "true").lower() == "true"

# 질문 유형별 Thread 가중치 (config에서 가져온 값 사용)
THREAD_WEIGHTS = {
    "causal": {
        "outgoing_relations": THREAD_WEIGHT_OUTGOING_RELATIONS,
        "incoming_relations": THREAD_WEIGHT_INCOMING_RELATIONS,
        "connected_entities": THREAD_WEIGHT_CONNECTED_ENTITIES,
        "entity_properties": THREAD_WEIGHT_ENTITY_PROPERTIES,
        "type_and_summary": THREAD_WEIGHT_TYPE_AND_SUMMARY
    },
    "deep_analysis": {
        "outgoing_relations": THREAD_WEIGHT_OUTGOING_RELATIONS,
        "incoming_relations": THREAD_WEIGHT_INCOMING_RELATIONS,
        "connected_entities": THREAD_WEIGHT_CONNECTED_ENTITIES,
        "entity_properties": THREAD_WEIGHT_ENTITY_PROPERTIES,
        "type_and_summary": THREAD_WEIGHT_TYPE_AND_SUMMARY
    },
    "factual": {
        "outgoing_relations": THREAD_WEIGHT_OUTGOING_RELATIONS,
        "incoming_relations": THREAD_WEIGHT_INCOMING_RELATIONS,
        "connected_entities": THREAD_WEIGHT_CONNECTED_ENTITIES,
        "entity_properties": THREAD_WEIGHT_ENTITY_PROPERTIES,
        "type_and_summary": THREAD_WEIGHT_TYPE_AND_SUMMARY
    },
    "comparative": {
        "outgoing_relations": THREAD_WEIGHT_OUTGOING_RELATIONS,
        "incoming_relations": THREAD_WEIGHT_INCOMING_RELATIONS,
        "connected_entities": THREAD_WEIGHT_CONNECTED_ENTITIES,
        "entity_properties": THREAD_WEIGHT_ENTITY_PROPERTIES,
        "type_and_summary": THREAD_WEIGHT_TYPE_AND_SUMMARY
    }
}

# 데이터 기반 Thread 설정 (SPARQL 템플릿)
# ⚡ 라벨 기반 검색: URI 대신 라벨로 검색하여 데이터 불일치 문제 해결
DATA_THREADS = {
    "outgoing_relations": {
        "description": "엔티티에서 나가는 모든 관계 (엔티티 → ?)",
        "sparql_template": """
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            SELECT ?entity ?entityLabel ?predicate ?object ?objectLabel WHERE {{
                ?entity rdfs:label ?entityLabel .
                FILTER ({label_filter})
                ?entity ?predicate ?object .
                FILTER(isURI(?object))
                OPTIONAL {{ ?object rdfs:label ?objectLabel }}
                FILTER(?predicate != rdf:type)
                FILTER(?predicate != rdfs:label)
            }} LIMIT 100
        """
    },
    "incoming_relations": {
        "description": "엔티티로 들어오는 모든 관계 (? → 엔티티)",
        "sparql_template": """
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            SELECT ?subject ?subjectLabel ?predicate ?entity ?entityLabel WHERE {{
                ?entity rdfs:label ?entityLabel .
                FILTER ({label_filter})
                ?subject ?predicate ?entity .
                FILTER(isURI(?subject))
                OPTIONAL {{ ?subject rdfs:label ?subjectLabel }}
                FILTER(?predicate != rdf:type)
                FILTER(?predicate != rdfs:label)
            }} LIMIT 100
        """
    },
    "entity_properties": {
        "description": "엔티티의 모든 속성 (리터럴 값)",
        "sparql_template": """
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?entity ?entityLabel ?predicate ?value WHERE {{
                ?entity rdfs:label ?entityLabel .
                FILTER ({label_filter})
                ?entity ?predicate ?value .
                FILTER(isLiteral(?value))
                FILTER(?predicate != rdfs:label)
            }} LIMIT 100
        """
    },
    "connected_entities": {
        "description": "두 엔티티 사이의 모든 관계 (A ↔ B) + 다중 hop 경로 탐색",
        "sparql_template": """
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            SELECT DISTINCT ?entity1 ?label1 ?predicate ?entity2 ?label2 WHERE {{
                {{
                    # A → B 방향 (직접 연결)
                    ?entity1 rdfs:label ?label1 .
                    ?entity2 rdfs:label ?label2 .
                    FILTER ({label_filter1})
                    FILTER ({label_filter2})
                    ?entity1 ?predicate ?entity2 .
                }}
                UNION
                {{
                    # B → A 방향 (직접 연결)
                    ?entity2 rdfs:label ?label2 .
                    ?entity1 rdfs:label ?label1 .
                    FILTER ({label_filter1})
                    FILTER ({label_filter2})
                    ?entity2 ?predicate ?entity1 .
                }}
                FILTER(?entity1 != ?entity2)
                FILTER(?predicate != rdf:type)
                FILTER(?predicate != rdfs:label)
            }} LIMIT 100
        """,
        "use_bidirectional_bfs": True  # 양방향 BFS 활성화 플래그
    },
    "type_and_summary": {
        "description": "엔티티 타입과 요약 정보",
        "sparql_template": """
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?entity ?entityLabel ?type ?summary ?category ?year WHERE {{
                ?entity rdfs:label ?entityLabel .
                FILTER ({label_filter})
                OPTIONAL {{ ?entity rdf:type ?type }}
                OPTIONAL {{ ?entity hist:hasSummary ?summary }}
                OPTIONAL {{ ?entity hist:hasCategory ?category }}
                OPTIONAL {{ ?entity hist:hasYear ?year }}
            }} LIMIT 50
        """
    }
}



def parallel_knowledge_retrieval_node(state: GraphState) -> GraphState:
    """
    Parallel Knowledge Retrieval: 5개 Thread에서 SPARQL 쿼리 생성 + 실행을 병렬로 수행

    성능 최적화:
    - 쿼리 생성과 실행을 Thread별로 동시 처리 (~3-5초)
    - ThreadPoolExecutor로 병렬 실행

    프로퍼티 필터링:
    - classify_node에서 선택된 프로퍼티 그룹으로 SPARQL FILTER 적용
    - 관련 프로퍼티만 검색하여 정확도 향상
    """

    import time
    node_start = time.time()

    query = state.get("query", "")
    query_type = state.get("query_type", "causal")
    entities = state.get("extracted_entities", [])
    hypothetical_triples = state.get("hypothetical_triples", [])
    test_config = state.get("test_config")  # 테스트 설정

    # 질문에서 핵심 키워드 추출 (kiwipiepy 사용)
    try:
        from kiwipiepy import Kiwi
        kiwi = Kiwi()
        tokens = kiwi.tokenize(query)
        # 명사만 추출 (핵심 키워드)
        core_keywords = [t.form for t in tokens if t.tag in ('NNG', 'NNP') and len(t.form) >= 2]
    except:
        # kiwipiepy 없으면 기본 키워드 추출
        import re
        core_keywords = re.findall(r'[가-힣]{2,}', query)

    # 엔티티를 핵심 키워드와의 관련도로 정렬
    # 핵심 키워드가 엔티티 이름에 포함되면 우선순위 높임
    def entity_priority(entity):
        name = entity.get("name", "").lower()
        score = 0
        for kw in core_keywords:
            if kw.lower() in name:
                score += 10  # 핵심 키워드 매칭 시 높은 점수
        # URI가 있으면 추가 점수
        if entity.get("uri"):
            score += 1
        return score

    entities_sorted = sorted(entities, key=entity_priority, reverse=True)

    # 선택된 프로퍼티 (classify_node에서 전달)
    selected_properties = state.get("selected_properties", [])
    selected_groups = state.get("selected_property_groups", [])

    # Thread 가중치 설정
    thread_weights = THREAD_WEIGHTS.get(query_type, THREAD_WEIGHTS["causal"])

    # 실행할 Thread 선택 (test_config에 따라)
    if test_config and "aggregator_threads" in test_config:
        thread_config = test_config["aggregator_threads"]
        active_threads = [t for t, enabled in thread_config.items() if enabled]
        print(f"\n{'='*70}")
        print(f"[Stage 4/6] 병렬 지식 검색 (Parallel Knowledge Retrieval)")
        print(f"{'='*70}")
        print(f"  ├─ [테스트 모드] 활성화된 Thread:")
        for thread in active_threads:
            print(f"  │  └─ {thread}: ON")
        print(f"  ├─ 엔티티: {len(entities)}개")
    else:
        active_threads = list(DATA_THREADS.keys())
        print(f"\n{'='*70}")
        print(f"[Stage 4/6] 병렬 지식 검색 (Parallel Knowledge Retrieval)")
        print(f"{'='*70}")
        print(f"  ├─ [일반 모드] Thread 수: {len(DATA_THREADS)}개")
        print(f"  ├─ 엔티티: {len(entities)}개")

    if selected_groups:
        print(f"  └─ 프로퍼티 필터: {', '.join(selected_groups[:3])}{'...' if len(selected_groups) > 3 else ''} ({len(selected_groups)}개)")
    start_time = time.time()

    # ThreadPoolExecutor로 병렬 실행 (템플릿 기반 SPARQL 쿼리)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_threads)) as executor:
        futures = {
            executor.submit(
                execute_unified_thread,
                thread_type=thread_type,
                query=query,
                query_type=query_type,
                entities=entities_sorted,  # 정렬된 엔티티 사용 (핵심 키워드 우선)
                hypothetical=hypothetical_triples,
                thread_config=DATA_THREADS[thread_type],
                selected_properties=selected_properties  # 프로퍼티 필터 전달
            ): thread_type
            for thread_type in active_threads  # 활성화된 Thread만 실행
        }
        
        # 결과 수집
        results = {}
        multi_queries = {}  # 생성된 쿼리도 저장 (디버깅용)
        
        for future in concurrent.futures.as_completed(futures):
            thread_type = futures[future]
            try:
                result = future.result(timeout=45)  # 쿼리 생성 + 실행이므로 timeout 증가
                results[thread_type] = result
                multi_queries[thread_type] = result.get("sparql", "")
                
                # 성공적으로 완료 (로그 최소화)
                pass

            except concurrent.futures.TimeoutError:
                results[thread_type] = {"status": "timeout", "bindings": [], "thread_type": thread_type}
            except Exception as e:
                results[thread_type] = {"status": "error", "bindings": [], "error": str(e), "thread_type": thread_type}

    elapsed = time.time() - start_time
    total_bindings = sum(len(r.get("bindings", [])) for r in results.values())

    # Thread별 검색 결과 상세
    print(f"\n      [Thread별 검색 결과]")
    for thread_type, result in results.items():
        bindings = result.get("bindings", [])
        status = result.get("status", "unknown")

        # 상태 아이콘
        status_icon = "✓" if status == "success" else "✗"

        # Thread 이름 정규화 (가독성)
        thread_name_map = {
            "outgoing_relations": "나가는 관계",
            "incoming_relations": "들어오는 관계",
            "entity_properties": "엔티티 속성",
            "connected_entities": "연결 엔티티",
            "type_and_summary": "타입/요약"
        }
        thread_display = thread_name_map.get(thread_type, thread_type)

        print(f"      {status_icon} {thread_display:15s}: {len(bindings):3d}개")

        # 상위 3개 결과 샘플 표시 (라벨만)
        if bindings and len(bindings) > 0:
            for i, binding in enumerate(bindings[:3], 1):
                # 라벨 추출 (정규화된 라벨 우선)
                label = (
                    binding.get("entityLabel", {}).get("value") or
                    binding.get("label", {}).get("value") or
                    binding.get("label1", {}).get("value") or
                    binding.get("subjectLabel", {}).get("value") or
                    binding.get("entity", {}).get("value", "")
                )

                # URI에서 라벨 추출 (라벨이 없는 경우)
                if not label or label.startswith("http"):
                    for key in ["entity", "subject", "event"]:
                        if key in binding:
                            uri = binding[key].get("value", "")
                            if "#" in uri:
                                label = uri.split("#")[-1]
                                break
                            elif "/" in uri:
                                label = uri.split("/")[-1]
                                break

                if label and len(label) > 0:
                    # 라벨 길이 제한
                    label_display = label[:40] + "..." if len(label) > 40 else label
                    print(f"         {i}. {label_display}")

    node_elapsed = time.time() - node_start
    print(f"  └─ 완료: {total_bindings}개 결과 ({node_elapsed:.2f}초)")
    print()

    # 지식 검색 결과를 TTL로 저장 (옵션)
    inference_ttl_path = None
    if SAVE_INFERENCE_TRIPLES and total_bindings > 0:
        try:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            inference_ttl_path = save_inference_results_as_ttl(
                results=results,
                query=query,
                session_id=session_id,
                execution_time=elapsed
            )
            # 지식 검색 결과 저장 완료 (로그 간소화)
        except Exception as e:
            print(f"   경고: 지식 검색 결과 저장 실패: {e}")

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["parallel_knowledge_retrieval"] = node_elapsed

    return {
        **state,
        "multi_queries": multi_queries,  # 생성된 쿼리도 state에 저장
        "thread_weights": thread_weights,
        "parallel_inference_results": results,
        "execution_time": elapsed,
        "inference_ttl_path": inference_ttl_path,
        "executed_nodes": state.get("executed_nodes", []) + ["parallel_knowledge_retrieval"],
        "node_execution_times": node_times
    }


def execute_unified_thread(
    thread_type: str,
    query: str,
    query_type: str,
    entities: list,
    hypothetical: list,
    thread_config: dict,
    selected_properties: list = None
) -> dict:
    """
    개별 Thread에서 템플릿 기반 SPARQL 쿼리 생성 + 지식 검색 수행

    Args:
        thread_type: Thread 타입 (outgoing_relations/incoming_relations/entity_properties/connected_entities/type_and_summary)
        query: 사용자 질문
        query_type: 질문 유형
        entities: 추출된 엔티티 목록
        hypothetical: 가상 트리플 목록 (미사용)
        thread_config: Thread 설정 (sparql_template, use_bidirectional_bfs, description)
        selected_properties: 필터링할 프로퍼티 목록 (classify_node에서 선택)

    Returns:
        검색 결과 딕셔너리
    """

    description = thread_config.get("description", "")
    use_bidirectional_bfs = thread_config.get("use_bidirectional_bfs", False)
    sparql_template = thread_config.get("sparql_template", "")
    selected_properties = selected_properties or []

    # connected_entities는 양방향 BFS 추가 실행
    if use_bidirectional_bfs and thread_type == "connected_entities" and len(entities) >= 2:
        print(f"    ├─ 양방향 BFS 경로 탐색 시작 (엔티티 {len(entities)}개)")
        
        # 양방향 BFS로 엔티티 간 경로 탐색
        bfs_paths = execute_bidirectional_path_search(entities)
        print(f"    │  └─ BFS 경로 발견: {len(bfs_paths)}개")

        # SPARQL 쿼리도 실행 (직접 연결 찾기)
        if sparql_template:
            sparql = generate_template_sparql(thread_type, entities, sparql_template, selected_properties)
        else:
            sparql = generate_fallback_sparql(thread_type, entities)

        sparql_result = execute_inference_api(
            thread_type=thread_type,
            sparql=sparql,
            hypothetical=hypothetical,
            query_type=query_type
        )

        # BFS 경로와 SPARQL 결과 병합
        sparql_bindings = sparql_result.get("bindings", [])
        combined_bindings = sparql_bindings + bfs_paths
        
        print(f"    └─ SPARQL 직접 연결: {len(sparql_bindings)}개, BFS 경로: {len(bfs_paths)}개, 합계: {len(combined_bindings)}개")

        sparql_result["bindings"] = combined_bindings
        sparql_result["sparql"] = sparql
        sparql_result["used_bfs"] = True

        return sparql_result

    # 1️⃣ SPARQL 쿼리 생성 (템플릿 기반)
    if sparql_template:
        # 템플릿 모드: 미리 정의된 SPARQL 템플릿 사용
        # 선택된 프로퍼티로 FILTER 적용
        sparql = generate_template_sparql(thread_type, entities, sparql_template, selected_properties)
    else:
        # Fallback 쿼리 사용
        sparql = generate_fallback_sparql(thread_type, entities)

    # 2️⃣ 지식 검색 실행
    result = execute_inference_api(
        thread_type=thread_type,
        sparql=sparql,
        hypothetical=hypothetical,
        query_type=query_type
    )

    # 생성된 쿼리도 결과에 포함
    result["sparql"] = sparql

    return result


def execute_bidirectional_path_search(entities: list, max_pairs: int = 5) -> list:
    """
    여러 엔티티 쌍에 대해 양방향 BFS 경로 탐색 실행

    Args:
        entities: 엔티티 목록
        max_pairs: 최대 탐색 쌍 수

    Returns:
        Fuseki binding 형식의 경로 리스트
    """

    bindings = []

    # 엔티티 쌍 생성 (상위 N개만)
    entities_with_uri = [e for e in entities if e.get("uri")]

    if len(entities_with_uri) < 2:
        print(f"      └─ URI가 있는 엔티티가 2개 미만 ({len(entities_with_uri)}개)")
        return []

    print(f"      ├─ 엔티티 쌍 탐색: {len(entities_with_uri)}개 엔티티 중 최대 {max_pairs}개 쌍")

    # 모든 쌍 시도 (최대 max_pairs)
    pairs_tried = 0
    paths_found = 0
    
    for i in range(len(entities_with_uri)):
        for j in range(i + 1, len(entities_with_uri)):
            if pairs_tried >= max_pairs:
                break

            entity_a = entities_with_uri[i]
            entity_b = entities_with_uri[j]

            uri_a = entity_a.get("uri")
            uri_b = entity_b.get("uri")
            
            name_a = entity_a.get("name", "")
            name_b = entity_b.get("name", "")

            if not uri_a or not uri_b:
                continue

            # 양방향 BFS 실행
            paths = find_bidirectional_paths(uri_a, uri_b, max_depth=3)
            
            if paths:
                paths_found += len(paths)
                print(f"      │  ├─ [{name_a} ↔ {name_b}]: {len(paths)}개 경로 발견")

            # 경로를 Fuseki binding 형식으로 변환
            for path_info in paths:
                path_uris = path_info.get("path", [])
                predicates = path_info.get("predicates", [])
                convergence = path_info.get("convergence_node", "")

                if len(path_uris) >= 2:
                    # 경로 정보를 binding으로 변환
                    # URI에서 네임스페이스 제거 (hist:Person_xxx 형식 유지)
                    path_labels = []
                    for uri in path_uris:
                        if "#" in uri:
                            path_labels.append(uri.split("#")[-1])
                        elif ":" in uri:
                            path_labels.append(uri.split(":")[-1])
                        else:
                            path_labels.append(uri)
                    
                    path_str = " → ".join(path_labels)

                    bindings.append({
                        "entity1": {"value": uri_a},
                        "label1": {"value": name_a},
                        "entity2": {"value": uri_b},
                        "label2": {"value": name_b},
                        "path": {"value": path_str},
                        "path_length": {"value": str(len(path_uris))},
                        "convergence_node": {"value": convergence.split("#")[-1] if convergence and "#" in convergence else (convergence.split(":")[-1] if convergence and ":" in convergence else convergence)},
                        "method": {"value": "bidirectional_bfs"}
                    })

            pairs_tried += 1

        if pairs_tried >= max_pairs:
            break

    print(f"      └─ 총 {pairs_tried}개 쌍 탐색, {paths_found}개 경로 발견")
    return bindings


def find_bidirectional_paths(entity_a_uri: str, entity_b_uri: str, max_depth: int = 3) -> list:
    """
    양방향 BFS로 두 엔티티 간 최단 경로 탐색

    Args:
        entity_a_uri: 시작 엔티티 URI (예: hist:Person_정약용)
        entity_b_uri: 목표 엔티티 URI (예: hist:Person_사도세자)
        max_depth: 최대 탐색 깊이 (기본 3)

    Returns:
        경로 리스트 [{"path": [uri1, uri2, ..., uriN], "length": N, "predicates": [...]}]
    """

    if not entity_a_uri or not entity_b_uri:
        return []

    # 양방향 BFS 큐
    queue_a = [(entity_a_uri, [entity_a_uri], [])]  # (current_uri, path, predicates)
    queue_b = [(entity_b_uri, [entity_b_uri], [])]

    visited_a = {entity_a_uri: ([entity_a_uri], [])}  # uri → (path, predicates)
    visited_b = {entity_b_uri: ([entity_b_uri], [])}

    found_paths = []

    for depth in range(max_depth):
        # A에서 확장
        if queue_a:
            new_queue_a = []
            for current_uri, path, predicates in queue_a:
                neighbors = get_1hop_neighbors(current_uri)

                for neighbor_uri, predicate in neighbors:
                    # B측에서 이미 방문했는지 확인 (수렴점 발견)
                    if neighbor_uri in visited_b:
                        path_b, preds_b = visited_b[neighbor_uri]
                        # 전체 경로 = path_a + path_b (역순, 중복 제거)
                        # path_b[:-1]로 수렴점을 제외하고 역순으로 합침
                        # path_b = [B, Y, neighbor_uri] → path_b[:-1] = [B, Y] → [::-1] = [Y, B]
                        # full_path = [A, X, neighbor_uri] + [Y, B] = [A, X, neighbor_uri, Y, B]
                        full_path = path + path_b[:-1][::-1]
                        full_preds = predicates + preds_b[::-1]

                        found_paths.append({
                            "path": full_path,
                            "length": len(full_path),
                            "predicates": full_preds,
                            "convergence_node": neighbor_uri
                        })

                    # 방문하지 않은 노드만 큐에 추가
                    if neighbor_uri not in visited_a:
                        new_path = path + [neighbor_uri]
                        new_preds = predicates + [predicate]
                        visited_a[neighbor_uri] = (new_path, new_preds)
                        new_queue_a.append((neighbor_uri, new_path, new_preds))

            queue_a = new_queue_a

        # B에서 확장 (대칭)
        if queue_b:
            new_queue_b = []
            for current_uri, path, predicates in queue_b:
                neighbors = get_1hop_neighbors(current_uri)

                for neighbor_uri, predicate in neighbors:
                    # A측에서 이미 방문했는지 확인
                    if neighbor_uri in visited_a:
                        path_a, preds_a = visited_a[neighbor_uri]
                        # 전체 경로 = path_a + path (역순, 중복 제거)
                        # path = [B, Y, neighbor_uri] → path[:-1] = [B, Y] → [::-1] = [Y, B]
                        # full_path = [A, X, neighbor_uri] + [Y, B] = [A, X, neighbor_uri, Y, B]
                        full_path = path_a + path[:-1][::-1]
                        full_preds = preds_a + predicates[::-1]

                        found_paths.append({
                            "path": full_path,
                            "length": len(full_path),
                            "predicates": full_preds,
                            "convergence_node": neighbor_uri
                        })

                    # 방문하지 않은 노드만 큐에 추가
                    if neighbor_uri not in visited_b:
                        new_path = path + [neighbor_uri]
                        new_preds = predicates + [predicate]
                        visited_b[neighbor_uri] = (new_path, new_preds)
                        new_queue_b.append((neighbor_uri, new_path, new_preds))

            queue_b = new_queue_b

        # 경로를 찾았으면 조기 종료 (최단 경로 우선)
        if found_paths:
            break

    # 최단 경로 우선 정렬
    found_paths.sort(key=lambda x: x["length"])
    return found_paths[:5]  # 상위 5개 경로만


def get_1hop_neighbors(entity_uri: str, timeout: int = 2) -> list:
    """
    엔티티의 1-hop 이웃 조회 (양방향)

    Returns:
        [(neighbor_uri, predicate), ...]
    """

    # URI 형식 처리: hist:Entity_xxx 형태면 그대로 사용, full URI면 <> 감싸기
    if entity_uri.startswith("hist:"):
        # PREFIX 형식 (hist:Person_xxx) - 그대로 사용
        entity_ref = entity_uri
    elif entity_uri.startswith("http://"):
        # Full URI 형식 - <> 감싸기
        entity_ref = f"<{entity_uri}>"
    else:
        # 기타 형식 - hist: prefix 추가
        entity_ref = f"hist:{entity_uri}"

    sparql = f"""
        PREFIX hist: <http://www.example.org/korean-history#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT DISTINCT ?neighbor ?predicate WHERE {{
            {{
                # 나가는 관계
                {entity_ref} ?predicate ?neighbor .
                FILTER(?predicate != rdf:type)
                FILTER(?predicate != rdfs:label)
                FILTER(isURI(?neighbor))
            }}
            UNION
            {{
                # 들어오는 관계
                ?neighbor ?predicate {entity_ref} .
                FILTER(?predicate != rdf:type)
                FILTER(?predicate != rdfs:label)
                FILTER(isURI(?neighbor))
            }}
        }} LIMIT 50
    """

    try:
        response = requests.post(
            f"{FUSEKI_URL}/sparql",
            data={"query": sparql},
            headers={"Accept": "application/sparql-results+json"},
            timeout=timeout
        )

        if response.status_code == 200:
            results = response.json()
            bindings = results.get("results", {}).get("bindings", [])

            neighbors = []
            for binding in bindings:
                neighbor_uri = binding.get("neighbor", {}).get("value", "")
                predicate = binding.get("predicate", {}).get("value", "")
                if neighbor_uri and predicate:
                    neighbors.append((neighbor_uri, predicate))

            return neighbors
    except:
        pass

    return []


def generate_template_sparql(thread_type: str, entities: list, template: str, selected_properties: list = None) -> str:
    """
    템플릿 기반 SPARQL 생성 (라벨 기반 검색)
    
    Args:
        thread_type: Thread 타입
        entities: 엔티티 목록
        template: SPARQL 템플릿
        selected_properties: 필터링할 프로퍼티 목록 (선택된 경우 FILTER 추가)
    """
    
    selected_properties = selected_properties or []
    
    # 엔티티에서 라벨(이름) 추출
    labels = [e.get("name", "") for e in entities if e.get("name")]
    
    if not labels:
        # 라벨이 없으면 URI에서 추출 시도
        for e in entities:
            uri = e.get("uri", "")
            if uri:
                # hist:Person_xxx → 라벨 추출 불가, 이름 필요
                name = e.get("label", "") or e.get("name", "")
                if name and name not in labels:
                    labels.append(name)
    
    if not labels:
        return ""  # 검색할 라벨 없음
    
    # 라벨 FILTER 생성 (정확 매칭 또는 포함 검색)
    label_conditions = []
    for label in labels[:10]:  # 최대 10개 라벨
        # 정확 매칭 우선, 2글자 이상만
        if len(label) >= 2:
            # 정확 매칭: ?entityLabel = "경복궁"
            label_conditions.append(f'?entityLabel = "{label}"')
            # 포함 검색: CONTAINS(?entityLabel, "경복궁")
            # label_conditions.append(f'CONTAINS(?entityLabel, "{label}")')
    
    if not label_conditions:
        return ""
    
    label_filter = " || ".join(label_conditions)

    # connected_entities는 두 개의 라벨 필터 필요 (A-B 관계 검색)
    if thread_type == "connected_entities":
        # 엔티티를 2개 그룹으로 나눔 (A 그룹, B 그룹)
        mid = len(labels) // 2 if len(labels) > 1 else 1
        group_a = labels[:mid] if mid > 0 else labels
        group_b = labels[mid:] if len(labels) > 1 else labels

        label_filter1 = " || ".join([f'?label1 = "{l}"' for l in group_a[:5]])
        label_filter2 = " || ".join([f'?label2 = "{l}"' for l in group_b[:5]])

        # label_filter1이 비어있으면 기본값 설정
        if not label_filter1:
            label_filter1 = f'?label1 = "{labels[0]}"' if labels else '?label1 != ""'
        if not label_filter2:
            label_filter2 = f'?label2 = "{labels[0]}"' if labels else '?label2 != ""'

        sparql = template.format(label_filter1=label_filter1, label_filter2=label_filter2)
    else:
        sparql = template.format(label_filter=label_filter)
    
    # 선택된 프로퍼티가 있으면 FILTER 추가 (outgoing/incoming/connected 관계 검색에)
    if selected_properties and thread_type in ["outgoing_relations", "incoming_relations", "connected_entities"]:
        # 프로퍼티 FILTER 생성
        prop_uris = [f"hist:{prop}" for prop in selected_properties[:20]]  # 최대 20개
        prop_filter = ", ".join(prop_uris)

        if prop_filter:
            # LIMIT 앞에 프로퍼티 FILTER 추가
            filter_clause = f"FILTER(?predicate IN ({prop_filter}))"
            sparql = sparql.replace("}} LIMIT", f"{filter_clause}\n            }} LIMIT")
    
    return sparql


def generate_fallback_sparql(thread_type: str, entities: list) -> str:
    """SPARQL 템플릿 실패 시 기본 SPARQL 쿼리 반환"""
    
    # 엔티티 URI 추출 (hist:Person_xxx 형식)
    entity_uris = []
    for e in entities:
        uri = e.get("uri", "")
        if uri:
            if uri.startswith("hist:"):
                entity_uris.append(uri)
            else:
                entity_uris.append(f"hist:{uri}")
    
    # VALUES 절 생성 (더 효율적인 엔티티 필터링)
    if entity_uris:
        values_clause = "VALUES ?entity { " + " ".join(entity_uris) + " }"
    else:
        values_clause = ""
    
    # 기본 SPARQL 쿼리 (모든 thread_type에 공통)
    return f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?s ?p ?o ?sLabel WHERE {{
    {values_clause}
    ?entity ?p ?o .
    BIND(?entity AS ?s)
    OPTIONAL {{ ?s rdfs:label ?sLabel }}
}} LIMIT 100"""


def execute_inference_api(thread_type: str, sparql: str, hypothetical: list = None, query_type: str = None) -> dict:
    """
    SPARQL 쿼리 실행 (Fuseki 직접 쿼리)
    
    Args:
        thread_type: Thread 타입
        sparql: SPARQL 쿼리
        hypothetical: 미사용 (하위 호환성 유지)
        query_type: 미사용 (하위 호환성 유지)
    """
    return execute_fuseki_direct(thread_type, sparql)


def execute_fuseki_direct(thread_type: str, sparql: str, debug: bool = False) -> dict:
    """
    Fuseki에 직접 SPARQL 쿼리 (경량 모드)
    
    Java Reasoner 없이 이미 Fuseki에 저장된 데이터에서 쿼리.
    추론은 제한되지만 메모리 부족 환경에서 유용.
    """
    
    endpoint = f"{FUSEKI_URL}/sparql"
    
    # 디버그 모드: SPARQL 쿼리 출력
    if debug:
        print(f"\n[DEBUG] {thread_type} SPARQL:")
        print(sparql[:500])
    
    try:
        response = requests.post(
            endpoint,
            data={"query": sparql},
            headers={"Accept": "application/sparql-results+json"},
            timeout=30
        )
        
        # 에러 응답 상세 로그
        if response.status_code != 200:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            if debug:
                print(f"[DEBUG] {thread_type} 에러: {error_msg}")
            return {
                "status": "error",
                "bindings": [],
                "error": error_msg,
                "thread_type": thread_type
            }
        
        result = response.json()
        bindings = result.get("results", {}).get("bindings", [])
        
        return {
            "status": "success",
            "bindings": bindings,
            "fuseki_endpoint": endpoint,
            "thread_type": thread_type,
            "mode": "light"
        }
        
    except requests.exceptions.ConnectionError:
        return {
            "status": "error", 
            "bindings": [], 
            "error": f"Fuseki 서버 연결 실패 ({endpoint}). Docker 컨테이너가 실행 중인지 확인하세요.",
            "thread_type": thread_type
        }
    except requests.exceptions.Timeout:
        return {"status": "timeout", "bindings": [], "thread_type": thread_type}
    except Exception as e:
        return {"status": "error", "bindings": [], "error": str(e), "thread_type": thread_type}


def save_inference_results_as_ttl(
    results: dict,
    query: str,
    session_id: str,
    execution_time: float
) -> str:
    """Parallel Knowledge Retrieval의 지식 검색 결과를 TTL 파일로 저장"""
    
    try:
        from backend.langgraph_fuseki.utils.inference_triple_generator import InferenceTripleGenerator

        output_dir = Path(INFERENCE_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"inference_{session_id}.ttl"
        
        generator = InferenceTripleGenerator()
        
        generator.save_triples_to_file(
            inference_results=results,
            output_path=str(output_path),
            session_id=session_id
        )
        
        metadata_ttl = generator.generate_inference_metadata(
            inference_results=results,
            session_id=session_id,
            query=query,
            execution_time=execution_time
        )
        
        with open(output_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(metadata_ttl)
        
        return str(output_path)
        
    except ImportError:
        # InferenceTripleGenerator가 없는 경우 단순 저장
        output_dir = Path(INFERENCE_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"inference_{session_id}.json"
        
        import json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"query": query, "results": results, "execution_time": execution_time}, f, ensure_ascii=False, indent=2)
        
        return str(output_path)
