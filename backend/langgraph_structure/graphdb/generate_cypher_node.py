# LLM 이 Cypher 쿼리를 생성하는 노드
from langgraph_structure.state import GraphState

def generate_cypher_node(state: GraphState) -> GraphState:
    """
    LLM이 Cypher를 생성하는 노드.
    - cypher_keywords : 선택적인 중간 정보 (리스트)
    - cypher_query : Neo4j에서 실행할 실제 Cypher 문자열
    """

    cypher_keywords = ["Lee Sun Shin", "Choseon", "1592"]

    # 최종 Cypher 쿼리 (더미)
    cypher_query = """
    MATCH (p:Person {name: "이순신"})
    RETURN p
    """

    return {
        **state,
        "cypher_keywords": cypher_keywords,  # 선택
        "cypher_query": cypher_query.strip(),  # 필수
    }
