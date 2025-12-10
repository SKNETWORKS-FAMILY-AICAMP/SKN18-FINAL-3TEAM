# hybrid retrieval node: vector db와 graph db를 동시에 검색
from backend.langgraph_structure.state import GraphState
from backend.langgraph_structure.rag.retrieval_node import retrieval_node
from backend.langgraph_structure.graphdb.generate_cypher_node import generate_cypher_node
from backend.langgraph_structure.graphdb.neo4j_query_node import main

import asyncio

# 벡터 검색 (Postgres/pgvector)
async def _run_vector(state: GraphState) -> GraphState:
    # sync 함수 → 쓰레드 풀에서 실행
    return await asyncio.to_thread(retrieval_node, state)

# 그래프 검색 (Cypher 생성 → Neo4j)
async def _run_graph(state: GraphState) -> GraphState:
    # 1) Cypher 생성
    cypher_state: GraphState = await asyncio.to_thread(generate_cypher_node, state)
    # 2) Neo4j 검색 (TODO: 실제 쿼리 구현 예정)
    # 현재 main()은 인자를 받지 않으므로 그대로 호출하면 TypeError가 발생.
    # 일단 Cypher 결과만 유지하고 neo4j_results는 빈 리스트로 반환.
    return {
        **cypher_state,
        "neo4j_results": [],
    }

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
