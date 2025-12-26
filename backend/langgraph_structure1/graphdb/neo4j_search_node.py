import json
from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.graphdb.create_cypher import create_cypher
from backend.langgraph_structure1.graphdb.summary_utils import run_gain


def neo4j_search_node(state: GraphState) -> GraphState:
    """
    질문을 기반으로 Cypher를 생성하고 Neo4j에서 검색한 결과를 state에 합쳐 반환한다.
    """
    question = state.get("translated_query") or state.get("query")
    if not question:
        raise ValueError("neo4j_search_node: 'query'가 필요합니다.")

    cypher = create_cypher({**state, "query": question})
    print("[생성된 Cypher]")
    print(cypher)
    print("-" * 60)

    candidates = run_gain(ko_question=question, cypher=cypher)

    print("[Neo4j 검색 결과] (preview 30 / total 표시)")
    preview = candidates[:30]
    print(json.dumps(preview, ensure_ascii=False, indent=2))
    if len(candidates) > 30:
        print(f"... (total={len(candidates)})")
    print("-" * 60)

    return {
        **state,
        "cypher": cypher,
        "neo4j_candidates": candidates,  # ✅ 키 통일
    }
