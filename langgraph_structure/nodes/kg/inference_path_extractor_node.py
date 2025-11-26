"""
Inference Path Extractor Node

추론 결과에서 인과관계 경로 추출
- A → B → C → D 체인 찾기
- 추론에 사용된 규칙 추적
- 근거 트리플 수집
"""

from langgraph_structure.state import GraphState


def extract_causal_chains(bindings: list) -> list:
    """추론 결과에서 인과관계 체인 추출"""

    # leadsTo 관계 수집
    leads_to_map = {}  # {subject: [object1, object2, ...]}

    for binding in bindings:
        pred = binding.get("p", {}).get("value", "")

        if "leadsTo" in pred or "causedBy" in pred:
            subj = binding.get("s", {}).get("value", "").split("#")[-1]
            obj = binding.get("o", {}).get("value", "").split("#")[-1]

            if subj and obj:
                if subj not in leads_to_map:
                    leads_to_map[subj] = []
                leads_to_map[subj].append({
                    "predicate": pred.split("#")[-1],
                    "object": obj
                })

    # 체인 구성 (최대 5단계)
    chains = []

    for start_node in leads_to_map.keys():
        chain = build_chain(start_node, leads_to_map, max_depth=5)
        if len(chain) > 1:  # 최소 2단계 이상
            chains.append(chain)

    return chains


def build_chain(node: str, graph: dict, current_chain=None, max_depth=5, visited=None):
    """재귀적으로 인과관계 체인 구성"""

    if current_chain is None:
        current_chain = [{"node": node}]
    if visited is None:
        visited = set()

    if len(current_chain) >= max_depth or node in visited:
        return current_chain

    visited.add(node)

    # 다음 노드들
    next_nodes = graph.get(node, [])

    if not next_nodes:
        return current_chain

    # 첫 번째 경로만 따라가기 (여러 경로는 별도 체인으로)
    next_obj = next_nodes[0]["object"]
    next_pred = next_nodes[0]["predicate"]

    current_chain.append({
        "node": next_obj,
        "from_predicate": next_pred
    })

    return build_chain(next_obj, graph, current_chain, max_depth, visited)


def inference_path_extractor_node(state: GraphState) -> GraphState:
    """추론 경로 추출"""

    inference_results = state.get("inference_results", {})
    bindings = inference_results.get("bindings", [])

    print(f"🔍 추론 경로 추출 중... (트리플 {len(bindings)}개)")

    # 1. 인과관계 체인 추출
    causal_chains = extract_causal_chains(bindings)

    print(f"   - 발견된 인과 체인: {len(causal_chains)}개")
    for i, chain in enumerate(causal_chains[:3], 1):  # 상위 3개만 출력
        chain_str = " → ".join([node.get("node", "?") for node in chain])
        print(f"   {i}. {chain_str}")

    # 2. 추론 경로 상세 정보
    inference_paths = []

    for chain in causal_chains:
        path_info = {
            "chain": chain,
            "length": len(chain),
            "start": chain[0]["node"] if chain else None,
            "end": chain[-1]["node"] if chain else None,
            "predicates": [node.get("from_predicate") for node in chain[1:]]
        }
        inference_paths.append(path_info)

    # 3. 간접 원인 관계 추출
    indirect_causes = []
    for binding in bindings:
        pred = binding.get("p", {}).get("value", "")
        if "indirectlyCausedBy" in pred:
            indirect_causes.append({
                "effect": binding.get("s", {}).get("value", "").split("#")[-1],
                "cause": binding.get("o", {}).get("value", "").split("#")[-1]
            })

    if indirect_causes:
        print(f"   - 간접 원인 관계: {len(indirect_causes)}개")

    return {
        **state,
        "causal_chains": causal_chains,
        "inference_paths": inference_paths,
        "executed_nodes": state.get("executed_nodes", []) + ["inference_path_extractor"]
    }
