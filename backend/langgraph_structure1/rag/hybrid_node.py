# hybrid retrieval node: vector db와 graph db를 동시에 검색

from backend.langgraph_structure1.state import GraphState

from backend.langgraph_structure1.graphdb.neo4j_search_node import neo4j_search_node
from backend.langgraph_structure1.rag.retrieval_node import retrieval_node
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
    v_task = asyncio.create_task(_run_vector(state))
    g_task = asyncio.create_task(_run_graph(state))

    v_state, g_state = await asyncio.gather(v_task, g_task)

    # 기존 state + 벡터/그래프 결과를 모두 합쳐서 반환
    return {
        **state,
        **v_state,
        **g_state,
    }
