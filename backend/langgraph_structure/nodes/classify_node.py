# 질문이 역사 관련인지 아닌지만 판별
from langgraph_structure.state import GraphState
from langgraph.graph import END

def classify_node(state: GraphState) -> GraphState:
    query = state.get("query")

    if not query:
        raise ValueError("classify_node: 'query' 값이 state에 없습니다.")

    query = query.lower()

    # 임시: 일단 전부 history로 간주
    is_history_related = "history"

    # # 임시: 일단 전부 irrelevant로 간주
    # is_history_related = "irrelevant"
    
    return {
        **state,
        "is_history_related": is_history_related,
    }

def route_classify(state: GraphState) -> str:
    if state.get("is_history_related") == "irrelevant":
        return END
    return "retrieval_node"