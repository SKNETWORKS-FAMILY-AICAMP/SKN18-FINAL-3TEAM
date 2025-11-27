# vector db에서 문서 검색 노드
# neo4j를 타기 위해서는 해당 노드에서 조정 필요!
from typing import Any, Dict, List
from langgraph_structure.state import GraphState

def retrieval_node(state: GraphState) -> GraphState:
    query = state.get("query")
    if not query:
        raise ValueError("retrieval_node: 'query' 값이 state에 없습니다.")

    # 여기에 실제 vector DB 검색 로직이 들어가야 합니다.

    # # -----------------------------------
    # # vector DB에서 검색된 경우 - evaluate 노드로 라우팅
    # # -----------------------------------
    # # 예시로 더미 데이터를 반환합니다.
    # # 0.7 이하 시 cypher 노드로 라우팅
    # dummy_search_chunks: List[Dict[str, Any]] = [
    #     {
    #         "content": "이순신 장군은 임진왜란 당시 한산도 대첩을 비롯한 여러 해전에서 뛰어난 전략으로 조선을 지켜냈습니다.",
    #         "id": "doc1",
    #         "similarity": 0.83,
    #     },
    #     {
    #         "content": "이순신의 기록은 난중일기에 잘 남아있습니다.",
    #         "id": "doc2",
    #         "similarity": 0.78,
    #     },
    #     {
    #         "content": "오늘은 날씨가 맑아서 산책하기 좋습니다.",
    #         "id": "doc3",
    #         "similarity": 0.28,
    #     },
    # ]

    # -----------------------------------
    # vector DB에서 검색되지 않은 경우 - neo4j로 라우팅
    # -----------------------------------
    dummy_search_chunks = []

    # 유사도 점수 기반 필터링
    filtered_chunks = [chunk for chunk in dummy_search_chunks if chunk["similarity"] >= 0.7]    
    
    return {
        **state,
        "search_chunks": filtered_chunks,
    }

def route_retrieval(state: GraphState) -> str:
    """
    뽑힌 청크가 일정 개수(임시:1개) 미만이면 cypher 노드로 라우팅
    """
    search_chunks = state.get("search_chunks",[])
    if len(search_chunks) < 1:
        return "generate_cypher_node"
    else:
        return "evaluate_node"