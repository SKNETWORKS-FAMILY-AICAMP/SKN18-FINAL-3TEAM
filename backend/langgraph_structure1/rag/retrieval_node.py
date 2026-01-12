# vector db에서 문서 검색 노드
import time
from typing import Any, Dict, List, Tuple

from backend.langgraph_structure1.state import GraphState
from backend.db_pipeline.postgres.ETL.load_to_pgvector import get_embedding
from backend.db_pipeline.postgres.services.custom_pgvector import CustomPGVector
from backend.db_pipeline.common.config import POSTGRES_CONN_STR, HISTORY_TABLE_NAME
from backend.langgraph_structure1.rag.rag_config import (
    RETRIEVAL_TOP_K,
    FETCHED_COUNT,
)

DEBUG_PREVIEW_N = 5  # 디버그로 몇 개만 찍을지


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

    keywords: List[str] = state.get("keywords", []) or []
    combined_query = f"{question} {' '.join(keywords)}".strip() if keywords else question

    results = vectorstore.similarity_search_with_score(
        query=combined_query,
        k=FETCHED_COUNT,
    )

    # ✅ 점수 float 변환만 하고, threshold 필터는 제거(점수 의미 불명확해서 0개 되는 문제 방지)
    scored: List[Tuple[Any, float]] = []
    for doc, score in results:
        try:
            s = float(score)
        except Exception:
            continue
        scored.append((doc, s))

    # ✅ 일단 score 큰 순서로 정렬 (distance면 이후 단계에서 조정 가능)
    scored.sort(key=lambda x: x[1], reverse=True)

    top_k = scored[: int(RETRIEVAL_TOP_K)]

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

    # ✅ 그래프 후보랑 합치기 쉽게 "vector_candidates"도 같이 제공 (표준화)
    vector_candidates: List[Dict[str, Any]] = []
    for doc, score in top_k:
        meta = doc.metadata or {}
        vector_candidates.append(
            {
                "title": meta.get("title") or meta.get("source") or "",
                "category": meta.get("category") or meta.get("category_name") or "문서",
                "summary": doc.page_content[:400],  # 너무 길면 잘라
                "similarity": float(score),         # 일단 score를 similarity 슬롯에 넣음
                "source": "vector",
                "metadata": meta,
            }
        )

    elapsed = time.perf_counter() - t0

    print(f"[DEBUG] 벡터 검색 시간: {elapsed:.2f}초")

    # 디버그
    print(
        f"[DEBUG] 벡터 검색 결과: query={question!r}, keywords={keywords}, "
        f"retrieved={len(results)}, top_k={len(top_k)}"
    )
    if scored:
        sample = [s for _, s in scored[:10]]
        print(f"[DEBUG] vector score sample(Top10): {sample}")
    for ev in vector_evidences[:DEBUG_PREVIEW_N]:
        meta = ev["payload"].get("metadata", {}) or {}
        title = meta.get("title") or meta.get("source") or ""
        print(f"  - score={ev['score']:.4f} title={title!r}")
    if len(vector_evidences) > DEBUG_PREVIEW_N:
        print(f"  ... ({len(vector_evidences)} evidences)")
    print(f"[DEBUG] 벡터 검색 시간: {elapsed:.2f}초")
    print("-" * 60)

    return {
        **state,
        "vector_evidences": vector_evidences,      # 기존 호환
        "vector_candidates": vector_candidates,    # ✅ 병합용 표준 키
        "retrieval_elapsed": float(elapsed),
    }
