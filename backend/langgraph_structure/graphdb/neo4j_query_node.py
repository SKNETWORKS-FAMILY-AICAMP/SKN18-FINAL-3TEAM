from langgraph_structure.state import GraphState
from langgraph.graph import END

def neo4j_query_node(state: GraphState) -> GraphState:
    """
    쿼리 받아서 List[Dict[str, Any]] 형태로 결과 반환
    """

    neo4j_results = [{"임진왜란":"1592"}]  # 실제로는 Neo4j에서 쿼리 결과 받아와야 함

    return {
        **state,
        "neo4j_results": neo4j_results,  # neo4j 결과 저장
    }


def route_neo4j_query(state: GraphState) -> str:
    
    if state.get("neo4j_results"):
        return "generate_node"

    return END