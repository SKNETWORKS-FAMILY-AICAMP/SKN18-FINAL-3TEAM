from langgraph.state import GraphState


def generate_node(state: GraphState) -> GraphState:
    kg_results = state.get("kg_results", [])

    if kg_results:
        final_answer = f"추론 결과 {len(kg_results)}개를 생성했습니다."
    else:
        final_answer = "추론 결과를 생성하지 못했습니다."

    return {
        **state,
        "final_answer": final_answer,
    }
