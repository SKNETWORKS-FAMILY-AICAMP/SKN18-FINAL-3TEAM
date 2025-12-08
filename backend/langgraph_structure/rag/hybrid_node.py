# hybrid retrieval node: vector db와 graph db를 동시에 검색
from langgraph_structure.state import GraphState
from langgraph_structure.rag.retrieval_node import retrieval_node
from langgraph_structure.graphdb.generate_cypher_node import generate_cypher_node

import asyncio

# 벡터 검색 (Postgres/pgvector)
async def _run_vector(state: GraphState) -> GraphState:
    # sync 함수 → 쓰레드 풀에서 실행
    return await asyncio.to_thread(retrieval_node, state)

# 그래프 검색 (Cypher 생성 → Neo4j)
async def _run_graph(state: GraphState) -> GraphState:
    # 1) Cypher 생성
    cypher_state: GraphState = await asyncio.to_thread(generate_cypher_node, state)
    # 2) Neo4j 검색
    graph_state: GraphState = await asyncio.to_thread(neo4j_node, cypher_state)
    return graph_state

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