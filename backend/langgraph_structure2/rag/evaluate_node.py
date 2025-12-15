from typing import Any, Dict, List

from backend.langgraph_structure2.state import GraphState
from backend.langgraph_structure2.rag.rag_config import COSINE_SIMILARITY_THRESHOLD


def evaluate_node(state: GraphState) -> GraphState:
    """
    retrieval_node가 넘긴 vector_evidences를 임계값으로 필터링.
    - related_num: 필터 통과 개수
    - vector_evidences: 필터링된 evidences
    """
    evidences: List[Dict[str, Any]] = state.get("vector_evidences", [])
    filtered: List[Dict[str, Any]] = []

    for ev in evidences:
        score = float(ev.get("score", 0.0))
        if score >= COSINE_SIMILARITY_THRESHOLD:
            filtered.append(ev)

    related_num = len(filtered)

    return {
        **state,
        "related_num": related_num,
        "vector_evidences": filtered,
    }


def route_evaluate(state: GraphState) -> str:
    """
    임계값 통과한 evidence가 없으면 cypher 생성 노드로 보낸다.
    """
    return "generate_node" if state.get("related_num", 0) >= 1 else "generate_cypher_node"
