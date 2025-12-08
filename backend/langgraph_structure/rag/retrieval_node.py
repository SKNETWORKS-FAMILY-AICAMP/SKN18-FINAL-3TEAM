# vector db에서 문서 검색 노드
# neo4j를 타기 위해서는 해당 노드에서 조정 필요!
from typing import Any, Dict, List
# 상위 절대 경로

from backend.langgraph_structure.state import GraphState
from backend.db_pipeline.services.embedding_model import get_embedding
from backend.db_pipeline.services.custom_pgvector import CustomPGVector
from backend.db_pipeline.config import POSTGRES_CONN_STR

def retrieval_node(state: GraphState) -> GraphState:
    question = state.get("query")
    if not question:
        raise ValueError("retrieval_node: 'query' 값이 state에 없습니다.")
    
    search_chunks=[]
    MIN_SIMILARITY = 0.6

    embed = get_embedding()

    # Postgres(pgvector) 연결 설정
    vectorstore = CustomPGVector(
        conn_str=POSTGRES_CONN_STR,
        embedding_fn=embed,
        table="korean_history",  # 실제 테이블명
    )
    
    # 유사도 기반 검색
    results = vectorstore.similarity_search_with_score(
            query=question,
            k=2
        )


    filtered_docs = []
    
    for doc, score in results:
        if score >= MIN_SIMILARITY:
            filtered_docs.append({
                "source": "vector",
                "score": float(score),
                "payload": {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                }
            })
    
    return {
        **state,
        "search_chunks": filtered_docs,
    }

# 미사용 분기
# def route_retrieval(state: GraphState) -> str:
#     """
#     뽑힌 청크가 일정 개수(임시:1개) 미만이면 cypher 노드로 라우팅
#     """
#     search_chunks = state.get("search_chunks",[])
#     if len(search_chunks) < 1:
#         return "generate_cypher_node"
#     else:
#         return "evaluate_node"
