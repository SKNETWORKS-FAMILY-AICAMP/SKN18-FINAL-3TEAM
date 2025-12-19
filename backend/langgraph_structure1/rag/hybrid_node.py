# hybrid retrieval node: vector db와 graph db를 동시에 검색

from backend.langgraph_structure1.state import GraphState

from backend.langgraph_structure1.rag.retrieval_node import retrieval_node
from backend.langgraph_structure1.nodes.extract_keywords_node import extract_keywords_node
from backend.langgraph_structure1.graphdb.neo4j_search_node import neo4j_search_node
import asyncio

# 벡터 검색 (Postgres/pgvector)
async def _run_vector(state: GraphState) -> GraphState:
    # sync 함수 → 쓰레드 풀에서 실행
    return await asyncio.to_thread(retrieval_node, state)

# 그래프 검색 (Cypher 생성 → Neo4j)
async def _run_graph(state: GraphState) -> GraphState:
    # sync 함수 → 쓰레드 풀에서 실행
    return await asyncio.to_thread(neo4j_search_node, state)

# 실제 Hybrid 노드
async def hybrid_node(state: GraphState) -> GraphState:
    # retrieval 직전에만 키워드 추출하여 state에 주입
    kw_state = extract_keywords_node(state)

    # vector만 실행 (Neo4j 비활성화)
    v_task = asyncio.create_task(_run_vector(kw_state))
    g_task = asyncio.create_task(_run_graph(state))  # 필요 시 활성화

    v_state = await asyncio.gather(v_task)
    v_state = v_state[0]
    g_state = await asyncio.gather(g_task)
    g_state = g_state[0]

    # 기존 state + 벡터/그래프 결과를 모두 합쳐서 반환
    return {
        **state,
        **kw_state,
        **v_state,
        **g_state,
    }
