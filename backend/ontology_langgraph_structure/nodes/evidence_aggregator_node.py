"""
Evidence Aggregator Node

5개 Thread의 추론 경로를 통합하여 최종 근거 구성
- Thread별 가중치 적용
- 우선순위 정렬
- 상위 근거 선택
"""

from state import GraphState


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
                convergence_node = raw_data.get("convergence_node")
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
                "boost": 2.0  # 2배 가중치 부스트
            }

    return convergence_nodes


def extract_label_from_uri(uri: str) -> str:
    """URI에서 라벨 추출 (hist:Person_정약용 → 정약용)"""
    if "#" in uri:
        return uri.split("#")[-1]
    elif "/" in uri:
        return uri.split("/")[-1]
    return uri


def evidence_aggregator_node(state: GraphState) -> GraphState:
    """5가지 관점의 근거 통합 + 수렴 노드 감지"""

    import time
    node_start = time.time()

    inference_paths = state.get("inference_paths", {})
    thread_weights = state.get("thread_weights", {})
    query_type = state.get("query_type", "causal")
    query_entities = state.get("extracted_entities", [])

    print(f"\n{'='*70}")
    print(f"[5/6] 근거 통합 (Evidence Aggregator)")
    print(f"{'='*70}")

    # 1. 수렴 노드 감지
    convergence_nodes = detect_convergence_nodes(inference_paths, query_entities)

    if convergence_nodes:
        print(f"  ├─ 수렴 노드 감지: {len(convergence_nodes)}개")
        for i, (node_uri, info) in enumerate(list(convergence_nodes.items())[:3], 1):
            node_label = extract_label_from_uri(node_uri)
            connected = ", ".join(info["connected_entities"][:3])
            print(f"  │  {i}. {node_label} (연결: {connected})")

    # 2. 모든 Thread의 경로를 하나로 병합
    all_evidences = []

    for thread_type, paths in inference_paths.items():
        base_weight = thread_weights.get(thread_type, 0.2)

        for path in paths:
            # Thread 가중치 적용
            final_weight = path.get("weight", base_weight) * base_weight

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
                "source": f"Thread: {thread_type}",
                "raw_data": path,
                "is_convergence": convergence_node in convergence_nodes if convergence_node else False
            }

            all_evidences.append(evidence)

    # 3. 가중치 기준으로 정렬
    sorted_evidences = sorted(all_evidences, key=lambda x: x["weight"], reverse=True)

    # ========================================
    # [테스트용] 쓰레드별 검색 결과 출력 (나중에 원복 가능하도록 주석 처리)
    # ========================================
    print(f"\n      [테스트용] 쓰레드별 검색 결과:")
    for thread_type, paths in inference_paths.items():
        print(f"        - {thread_type}: {len(paths)}개 경로")
        # 상위 5개만 미리보기
        for i, path in enumerate(paths[:5], 1):
            desc = path.get("description", "")[:50]
            weight = path.get("weight", 0)
            print(f"          {i}. {desc} (가중치: {weight:.3f})")
        if len(paths) > 5:
            print(f"          ... 외 {len(paths) - 5}개")
    
    # [테스트용] 전체 근거 목록 출력 (정렬 후)
    print(f"\n      [테스트용] 전체 근거 목록 (총 {len(sorted_evidences)}개, 가중치 순):")
    for i, ev in enumerate(sorted_evidences[:20], 1):  # 상위 20개만 출력
        ev_type = ev.get("type", "unknown")
        description = ev.get("description", "")
        weight = ev.get("weight", 0)
        
        type_map = {
            "outgoing_relations": "나가는관계",
            "incoming_relations": "들어오는관계",
            "entity_properties": "엔티티속성",
            "connected_entities": "연결엔티티",
            "type_and_summary": "타입/요약",
        }
        type_display = type_map.get(ev_type, ev_type)
        desc_display = description[:60] + "..." if len(description) > 60 else description
        
        print(f"        {i:2d}. [{type_display:12s}] {desc_display} (가중치: {weight:.4f})")
    if len(sorted_evidences) > 20:
        print(f"        ... 외 {len(sorted_evidences) - 20}개")
    # ========================================
    # [테스트용] 끝
    # ========================================

    # 3. 상위 5개 선택 (generate_node 성능 최적화)
    top_evidences = sorted_evidences[:5]

    # 4. 순위 부여
    for i, ev in enumerate(top_evidences, 1):
        ev["rank"] = i

    # 최종 선택된 근거 목록 (전체 표시)
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
                "outgoing_relation": "나가는관계",
                "incoming_relation": "들어오는관계",
                "property": "속성",
                "connection": "연결",
                "summary": "요약"
            }
            type_display = type_map.get(ev_type, ev_type)

            # 설명 길이 제한
            desc_display = description[:60] + "..." if len(description) > 60 else description

            print(f"      {rank}. [{type_display:12s}] {desc_display} (가중치: {weight:.2%})")

    node_elapsed = time.time() - node_start
    print(f"  └─ 완료: {len(top_evidences)}개 근거 통합 ({node_elapsed:.2f}초)")
    print()

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["evidence_aggregator"] = node_elapsed

    return {
        **state,
        "evidences": top_evidences,
        "executed_nodes": state.get("executed_nodes", []) + ["evidence_aggregator"],
        "node_execution_times": node_times
    }
