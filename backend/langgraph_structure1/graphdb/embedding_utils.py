import math
from typing import Any, Dict, List
from backend.db_pipeline.common.embedding_model import get_embedding


def get_query_embedding(text: str):
    embed = get_embedding()
    return embed.embed_query(text)


def cosine_sim(a, b):
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _compute_similarity_on_node(node_dict: Dict[str, Any], query_emb: List[float]) -> None:
    """serialize_records node: {'_type':'node','props':{...}}"""
    if not isinstance(node_dict, dict):
        return
    if node_dict.get("_type") != "node":
        return

    props = node_dict.get("props") or {}
    emb = props.get("embedding")

    # ✅ embedding이 list가 아닐 수도 있으니 list로 변환 시도
    if emb is None:
        return
    if not isinstance(emb, list):
        try:
            emb = list(emb)
        except Exception:
            return

    props["similarity_score"] = cosine_sim(query_emb, emb)

    # (옵션) embedding 제거해서 payload 가볍게
    # 삭제 싫으면 아래 2줄 지워도 됨
    try:
        del props["embedding"]
    except Exception:
        pass


def add_similarity(records: List[Dict[str, Any]], query_emb: List[float]) -> None:
    """
    ✅ rec 안의 node dict 뿐 아니라
    ✅ hop2_nodes/hop3_nodes 같은 'list of nodes'까지 전부 similarity_score 계산
    """
    for rec in records:
        if not isinstance(rec, dict):
            continue

        for _, v in rec.items():
            # 1) 단일 노드(dict)
            if isinstance(v, dict):
                _compute_similarity_on_node(v, query_emb)

            # 2) 노드 리스트(list)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        _compute_similarity_on_node(item, query_emb)
