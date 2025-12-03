"""
Evidence Aggregator Node

5개 Thread의 추론 경로를 통합하여 최종 근거 구성
- Thread별 가중치 적용
- 우선순위 정렬
- 상위 근거 선택
"""

from state import GraphState


def evidence_aggregator_node(state: GraphState) -> GraphState:
    """5가지 관점의 근거 통합"""

    import time
    node_start = time.time()

    inference_paths = state.get("inference_paths", {})
    thread_weights = state.get("thread_weights", {})
    query_type = state.get("query_type", "causal")

    print(f"\n{'='*70}")
    print(f"[5/6] 근거 통합 (Evidence Aggregator)")
    print(f"{'='*70}")

    # 1. 모든 Thread의 경로를 하나로 병합
    all_evidences = []

    for thread_type, paths in inference_paths.items():
        base_weight = thread_weights.get(thread_type, 0.2)

        for path in paths:
            # Thread 가중치 적용
            final_weight = path.get("weight", base_weight) * base_weight

            evidence = {
                "type": thread_type,
                "description": path.get("description", ""),
                "weight": final_weight,
                "source": f"Thread: {thread_type}",
                "raw_data": path
            }

            all_evidences.append(evidence)

    # 2. 가중치 기준으로 정렬
    sorted_evidences = sorted(all_evidences, key=lambda x: x["weight"], reverse=True)

    # 3. 상위 5-10개 선택
    top_evidences = sorted_evidences[:10]

    # 4. 순위 부여
    for i, ev in enumerate(top_evidences, 1):
        ev["rank"] = i

    # 최종 선택된 근거 목록 (상위 5개)
    if top_evidences:
        print(f"\n      [최종 근거 목록 (상위 5개)]")
        for ev in top_evidences[:5]:
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
