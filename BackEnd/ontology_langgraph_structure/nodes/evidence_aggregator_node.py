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

    inference_paths = state.get("inference_paths", {})
    thread_weights = state.get("thread_weights", {})
    query_type = state.get("query_type", "causal")

    print(f"\n📚 근거 통합 중... ({len(inference_paths)}개 Thread)")

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

    print(f"   - 통합 근거: {len(top_evidences)}개")
    for ev in top_evidences[:5]:  # 상위 5개만 출력
        print(f"   {ev['rank']}. [{ev['type']}] {ev['description']} (가중치: {ev['weight']:.2%})")

    # 5. Thread별 통계
    thread_stats = {}
    for ev in top_evidences:
        thread_type = ev["type"]
        thread_stats[thread_type] = thread_stats.get(thread_type, 0) + 1

    print(f"\n   - Thread별 근거 분포:")
    for thread_type, count in sorted(thread_stats.items(), key=lambda x: -x[1]):
        print(f"     • {thread_type}: {count}개")

    return {
        **state,
        "evidences": top_evidences,
        "executed_nodes": state.get("executed_nodes", []) + ["evidence_aggregator"]
    }
