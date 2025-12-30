from typing import Any, Dict, List, Optional, Tuple

from backend.db_pipeline.neo4j.services.neo4j_connection import get_driver
from backend.db_pipeline.neo4j.services.neo4j_service import run_cypher, serialize_records
from backend.langgraph_structure1.graphdb.embedding_utils import get_query_embedding, add_similarity


def _node_to_info(node_dict: Dict[str, Any], depth: int) -> Optional[Dict[str, Any]]:
    # serialize_records 결과 node 형태: {"_type":"node", "props":{...}, "labels":[...]}
    if not isinstance(node_dict, dict) or node_dict.get("_type") != "node":
        return None

    props = node_dict.get("props") or {}
    title = props.get("title") or props.get("value")
    if not title:
        return None

    return {
        "title": title,
        "category": props.get("category") or "기타",
        "summary": props.get("summary") or props.get("content") or props.get("contents") or "",
        "similarity": props.get("similarity_score"),
        "source_depth": depth,  # ✅ 2 or 3
    }


def _mean(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    return sum(vals) / len(vals)


def run_gain(ko_question: str, cypher: str) -> Dict[str, Any]:
    """
    반환:
      {
        "candidates": [ ... ],          # ✅ 2/3-hop만 (✅ 2/3 중복 제거됨: 같은 노드면 2hop 우선)
        "hop2_mean_similarity": float|None,
        "hop3_mean_similarity": float|None,
        "hop2_count": int,
        "hop3_count": int
      }
    """
    driver = get_driver()
    try:
        q_emb = get_query_embedding(ko_question)

        raw = run_cypher(driver, cypher)
        ser = serialize_records(raw)

        # ✅ main/hop 노드에 similarity_score 달기 (hop 리스트까지 계산되도록 add_similarity가 수정돼 있어야 함)
        add_similarity(ser, q_emb)

        hop2_sims: List[float] = []
        hop3_sims: List[float] = []

        # ✅ depth별 중복은 허용(평균 계산용), but candidates 출력용은 2hop 우선으로 dedup
        # key = (title, category) 기준으로 같은 노드면 depth 작은(2) 것을 남김
        best_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for rec in ser:
            # ✅ 0-hop(main)은 anchor로만 쓰고 candidates에 넣지 않음

            # 2-hop
            for n in rec.get("hop2_nodes", []) or []:
                info = _node_to_info(n, depth=2)
                if not info:
                    continue

                s = info.get("similarity")
                if isinstance(s, (int, float)):
                    hop2_sims.append(float(s))

                k = (info["title"], info["category"])
                prev = best_by_key.get(k)
                if prev is None or info["source_depth"] < prev.get("source_depth", 999):
                    best_by_key[k] = info

            # 3-hop
            for n in rec.get("hop3_nodes", []) or []:
                info = _node_to_info(n, depth=3)
                if not info:
                    continue

                s = info.get("similarity")
                if isinstance(s, (int, float)):
                    hop3_sims.append(float(s))

                k = (info["title"], info["category"])
                prev = best_by_key.get(k)
                # ✅ 같은 노드가 2hop로 이미 있으면 2hop 유지 (3hop은 덮어쓰지 않음)
                if prev is None or info["source_depth"] < prev.get("source_depth", 999):
                    best_by_key[k] = info

        candidates: List[Dict[str, Any]] = list(best_by_key.values())

        # ✅ candidates는 similarity 내림차순(None은 뒤로)
        candidates.sort(
            key=lambda x: (x.get("similarity") is not None, x.get("similarity") or 0.0),
            reverse=True
        )

        return {
            "candidates": candidates,
            "hop2_mean_similarity": _mean(hop2_sims),
            "hop3_mean_similarity": _mean(hop3_sims),
            "hop2_count": len(hop2_sims),
            "hop3_count": len(hop3_sims),
        }

    finally:
        driver.close()
