# create_cypher.py와 graph_summary.py 호출하는 neo4j검색 노드

import json

from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.graphdb.create_cypher import create_cypher
from backend.langgraph_structure1.graphdb.summary_utils import run_gain


def neo4j_search_node(state: GraphState) -> GraphState:
    """
    질문을 기반으로 Cypher를 생성하고 Neo4j에서 검색한 결과를 state에 합쳐 반환한다.
    """
    # 번역된 질문이 있으면 우선 사용, 없으면 원본 사용
    question = state.get("translated_query") or state.get("query")
    if not question:
        raise ValueError("neo4j_search_node: 'query'가 필요합니다.")

    # Cypher 생성 (검색용 질문을 query 필드로 강제 세팅)
    cypher = create_cypher({**state, "query": question})
    print("[생성된 Cypher]")
    print(cypher)
    print("-" * 60)

    # Neo4j에서 Cypher 실행
    summary_nodes = run_gain(ko_question=question, cypher=cypher)

    print("[검색 결과 요약] (카테고리별 최대 3개 → 전체 similarity 정렬)")
    print(json.dumps(summary_nodes, ensure_ascii=False, indent=2))
    print("-" * 60)

    return {
        **state,
        "cypher": cypher,
        "neo4j_results": summary_nodes,
    }


