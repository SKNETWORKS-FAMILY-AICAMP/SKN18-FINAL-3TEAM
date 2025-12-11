# vector db에서 문서 검색 노드
# neo4j를 타기 위해서는 해당 노드에서 조정 필요!
import time
from typing import Any, Dict, List
# 상위 절대 경로

from backend.langgraph_structure1.state import GraphState
from backend.db_pipeline.ETL.load_to_pgvector import get_embedding
from backend.db_pipeline.services.custom_pgvector import CustomPGVector
from backend.db_pipeline.config import POSTGRES_CONN_STR

def retrieval_node(state: GraphState) -> GraphState:
    question = state.get("query")
    if not question:
        raise ValueError("retrieval_node: 'query' 값이 state에 없습니다.")
    
    MIN_SIMILARITY = 0.0

    embed = get_embedding()

    # Postgres(pgvector) 연결 설정
    vectorstore = CustomPGVector(
        conn_str=POSTGRES_CONN_STR,
        embedding_fn=embed,
        table="korean_history",  # 실제 테이블명
    )
    
    start_time = time.time()
    # 유사도 기반 검색
    results = vectorstore.similarity_search_with_score(
            query=question,
            k=2
        )
    end_time = time.time()
    print("\n⏰", end_time - start_time)


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

    print(f"[벡터 검색 결과] {len(filtered_docs)}개 문서 반환 (최소 유사도 {MIN_SIMILARITY})")
    print("-" * 60)
    
    return {
        **state,
        "vector_evidences": filtered_docs,
    }

if __name__ == "__main__":
    # 간단 테스트
    while True:
            q = input("질문: ").strip()
            if q in {"exit", "quit", "q", "종료", "끝"}:
                print("종료")
                break
            if q:
                test_state : GraphState = {
                    "query": q
                    }

                updated_state = retrieval_node(test_state)
                print("Updated State:", updated_state)
