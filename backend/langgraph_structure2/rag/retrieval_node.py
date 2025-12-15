# vector db에서 문서 검색 노드
import time
from typing import Any, Dict, List

from backend.langgraph_structure2.state import GraphState
from backend.db_pipeline.vectordb.ETL.load_to_pgvector import get_embedding
from backend.db_pipeline.vectordb.services.custom_pgvector import CustomPGVector
from backend.db_pipeline.common.config import POSTGRES_CONN_STR, HISTORY_TABLE_NAME
from backend.langgraph_structure2.rag.rag_config import RETRIEVAL_TOP_K

def retrieval_node(state: GraphState) -> GraphState:
    question = state.get("query")
    if not question:
        raise ValueError("retrieval_node: 'query' 값이 state에 없습니다.")

    # 한 질문당 한 번 실행된다는 가정으로 호출마다 embed/vectorstore 생성
    embed = get_embedding()
    vectorstore = CustomPGVector(
        conn_str=POSTGRES_CONN_STR,
        embedding_fn=embed,
        table=HISTORY_TABLE_NAME,
    )

    t0 = time.perf_counter()
    results = vectorstore.similarity_search_with_score(
        query=question,
        k=int(RETRIEVAL_TOP_K),
    )
    elapsed = time.perf_counter() - t0

    # Top-K 후보를 그대로 넘깁니다. (평가/라우팅은 evaluate_node에서)
    vector_candidates: List[Dict[str, Any]] = []

    max_sim = 0.0
    for doc, raw_score in results:
        sim = float(raw_score)
        if sim > max_sim:
            max_sim = sim

        vector_candidates.append({
            "source": "vector",
            # score는 "정규화된 코사인 유사도(0~1, 클수록 좋음)"로 통일
            "score": float(sim),
            "payload": {
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
        })

    return {
        **state,
        # evaluate_node가 판단할 수 있도록 후보를 그대로 전달
        "vector_evidences": vector_candidates,
        "retrieval_elapsed": float(elapsed),
        "retrieval_max_similarity": float(max_sim),
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
