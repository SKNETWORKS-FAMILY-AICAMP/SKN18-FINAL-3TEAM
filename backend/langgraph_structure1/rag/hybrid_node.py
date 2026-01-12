# hybrid retrieval node: vector db와 graph db를 동시에 검색
import asyncio
from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.rag.retrieval_node import retrieval_node
from backend.langgraph_structure1.nodes.extract_keywords_node import extract_keywords_node
from backend.langgraph_structure1.graphdb.neo4j_search_node import neo4j_search_node


async def _run_vector(state: GraphState) -> GraphState:
    return await asyncio.to_thread(retrieval_node, state)

async def _run_graph(state: GraphState) -> GraphState:
    return await asyncio.to_thread(neo4j_search_node, state)

def _score_of(x: dict) -> float:
    # 그래프는 similarity, 벡터는 similarity(혹은 score)로 들어옴
    v = x.get("similarity")
    if v is None:
        v = x.get("similarity_score")
    if v is None:
        v = x.get("score")
    try:
        return float(v)
    except Exception:
        return 0.0

async def hybrid_node(state: GraphState) -> GraphState:
    kw_state = extract_keywords_node(state)

    v_task = asyncio.create_task(_run_vector(kw_state))
    g_task = asyncio.create_task(_run_graph(kw_state))

    v_state, g_state = await asyncio.gather(v_task, g_task)

    neo = g_state.get("neo4j_candidates") or []
    vec = v_state.get("vector_candidates") or []

    merged = []
    for x in neo:
        merged.append({**x, "_src": "neo4j", "_score": _score_of(x)})
    for x in vec:
        merged.append({**x, "_src": "vector", "_score": _score_of(x)})

    merged.sort(key=lambda r: r["_score"], reverse=True)

    # 디버그
    print(f"[DEBUG] merged_candidates: neo4j={len(neo)} vector={len(vec)} merged={len(merged)}")
    if merged[:5]:
        print("[DEBUG] merged top5:")
        for m in merged[:5]:
            print(f"  - src={m.get('_src')} score={m.get('_score'):.4f} title={m.get('title')!r}")
    print("-" * 60)

    return {
        **state,
        **kw_state,
        **v_state,
        **g_state,
        # ✅ 최종 통합 후보 (이걸로 최종 답변 만들면 됨)
        "merged_candidates": merged,
    }
