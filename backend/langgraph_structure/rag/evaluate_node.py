# 질문과 답변이 연관성 있는지 평가하는 노드
from langgraph_structure.state import GraphState
from langgraph.graph import END
from typing import Dict, Any, List

def evaluate_node(state: GraphState) -> GraphState:
    """
    search_chunks 중 similarity >= 0.7 인 것만 context로 사용.
    num = relevance 통과한 청크 개수
    """
    search_chunks: List[Dict[str, Any]] = state.get("search_chunks")

    context_chunks: List[Dict[str, Any]] = []

    # 더미 relevance 평가 로직    
    for chunk in search_chunks:

        # # generate node 라우팅용 더미 점수
        # relevance_score = 0.98  # 실제로는 평가 LLM모델로 산출

        # cypher 노드 라우팅용 더미 점수
        relevance_score = 0.65  # 실제로는 평가 LLM모델로 산출

        if relevance_score >= 0.7:
            context_chunks.append(chunk)

    num = len(context_chunks)

    return {
        **state,
        "related_num": num,                       # 라우팅에 사용
        "context_chunks": context_chunks  # generate_node에서 사용
    }


# top k
def route_evaluate(state: GraphState) -> str:
    """
    아무 청크도 relevance 통과 못했으면 cypher 노드로 라우팅
    그렇지 않으면 generate_node로 라우팅
    """
    if state.get("related_num", 0) >= 1:
        return "generate_node"
    else:
        return END