# vector db에서 문서 검색 노드
# neo4j를 타기 위해서는 해당 노드에서 조정 필요!
import time
from typing import Any, Dict, List

from backend.langgraph_structure1.state import GraphState
from backend.db_pipeline.vectordb.ETL.load_to_pgvector import get_embedding
from backend.db_pipeline.vectordb.services.custom_pgvector import CustomPGVector
from backend.db_pipeline.common.config import POSTGRES_CONN_STR, HISTORY_TABLE_NAME
from backend.langgraph_structure1.rag.rag_config import (
    RETRIEVAL_TOP_K,
    COSINE_SIMILARITY_THRESHOLD,
    FETCHED_COUNT
)

def retrieval_node(state: GraphState) -> GraphState:
    question = state.get("query")
    if not question:
        raise ValueError("retrieval_node: 'query' 값이 state에 없습니다.")

    embed = get_embedding()
    vectorstore = CustomPGVector(
        conn_str=POSTGRES_CONN_STR,
        embedding_fn=embed,
        table=HISTORY_TABLE_NAME,
    )

    t0 = time.perf_counter()

    # 넉넉히 FETCHED_COUNT(5)개 가져온 뒤 필터링
    results = vectorstore.similarity_search_with_score(
        query=question,
        k=FETCHED_COUNT,
    )

    # 점수 float 변환 및 필터
    filtered = [
        (doc, float(score))
        for doc, score in results
        if float(score) >= COSINE_SIMILARITY_THRESHOLD
    ]

    # (선택) 안정적인 순서 보장
    filtered.sort(key=lambda x: x[1], reverse=True)

    # 임계값 통과한 것 중 top-k
    top_k = filtered[:RETRIEVAL_TOP_K]

    # 증거 패킹은 top_k만 사용
    vector_evidences: List[Dict[str, Any]] = [
        {
            "source": "vector",
            "score": float(score),
            "payload": {
                "content": doc.page_content,
                "metadata": doc.metadata,
            },
        }
        for doc, score in top_k
    ]

    elapsed = time.perf_counter() - t0

    return {
        **state,
        "vector_evidences": vector_evidences,
        "retrieval_elapsed": float(elapsed),
    }


if __name__ == "__main__":
    while True:
        q = input("질문: ").strip()
        if q in {"exit", "quit", "q", "종료", "끝"}:
            print("종료")
            break
        if q:
            test_state: GraphState = {"query": q}
            updated_state = retrieval_node(test_state)
            print("Updated State:", updated_state)
