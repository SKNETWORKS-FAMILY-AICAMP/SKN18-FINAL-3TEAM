"""
Evidence Aggregator Node

다중 추론 경로를 집계하여 근거 구성
- 여러 인과 체인 병합
- 근거 우선순위 정렬 (체인 길이, 관련성 등)
- 중복 제거
"""

from langgraph_structure.state import GraphState


def evidence_aggregator_node(state: GraphState) -> GraphState:
    """다중 근거 집계"""

    causal_chains = state.get("causal_chains", [])
    inference_paths = state.get("inference_paths", [])
    query_type = state.get("query_type", "causal")
    entities = state.get("extracted_entities", [])

    print(f"📚 근거 집계 중... (경로 {len(inference_paths)}개)")

    # 1. 엔티티 관련성 점수 계산
    entity_names = {e.get("name", "").lower() for e in entities if "name" in e}

    for path in inference_paths:
        # 엔티티와 관련된 노드 개수
        chain_nodes = {node.get("node", "").lower() for node in path["chain"]}
        overlap = len(entity_names & chain_nodes)

        path["relevance_score"] = overlap / len(entity_names) if entity_names else 0
        path["weight"] = path["length"] * 0.3 + path["relevance_score"] * 0.7

    # 2. 우선순위 정렬 (weight 높은 순)
    sorted_paths = sorted(inference_paths, key=lambda x: x.get("weight", 0), reverse=True)

    # 3. 근거 구성 (상위 5개)
    evidences = []

    for i, path in enumerate(sorted_paths[:5]):
        evidence = {
            "rank": i + 1,
            "type": "causal_chain",
            "chain": path["chain"],
            "weight": path.get("weight", 0),
            "description": format_chain_description(path["chain"])
        }
        evidences.append(evidence)

    print(f"   - 집계된 근거: {len(evidences)}개")
    for ev in evidences:
        print(f"   {ev['rank']}. {ev['description']} (가중치: {ev['weight']:.2f})")

    return {
        **state,
        "evidences": evidences,
        "executed_nodes": state.get("executed_nodes", []) + ["evidence_aggregator"]
    }


def format_chain_description(chain: list) -> str:
    """체인을 한글 설명으로 변환"""
    if len(chain) < 2:
        return "근거 부족"

    nodes = [node.get("node", "?") for node in chain]
    return " → ".join(nodes)
