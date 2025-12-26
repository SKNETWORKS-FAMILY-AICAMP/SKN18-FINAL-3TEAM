import json
from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.graphdb.create_cypher import create_cypher
from backend.langgraph_structure1.graphdb.summary_utils import run_gain


def neo4j_search_node(state: GraphState) -> GraphState:
    """
    질문을 기반으로 Cypher를 생성하고 Neo4j에서 검색한 결과를 state에 합쳐 반환한다.
    - run_gain은 이제 dict를 반환:
      {
        "candidates": [...],                 # ✅ 2/3-hop만
        "hop2_mean_similarity": float|None,
        "hop3_mean_similarity": float|None,
        "hop2_count": int,
        "hop3_count": int
      }
    """
    question = state.get("translated_query") or state.get("query")
    if not question:
        raise ValueError("neo4j_search_node: 'query'가 필요합니다.")

    cypher = create_cypher({**state, "query": question})
    print("[생성된 Cypher]")
    print(cypher)
    print("-" * 60)

    gain = run_gain(ko_question=question, cypher=cypher)

    candidates = gain.get("candidates", []) or []
    hop2_mean = gain.get("hop2_mean_similarity")
    hop3_mean = gain.get("hop3_mean_similarity")
    hop2_cnt = gain.get("hop2_count", 0)
    hop3_cnt = gain.get("hop3_count", 0)

    print("[Neo4j 검색 결과] (preview 30 / total 표시)")
    preview = candidates[:30]
    print(json.dumps(preview, ensure_ascii=False, indent=2))
    if len(candidates) > 30:
        print(f"... (total={len(candidates)})")

    print(f"[Neo4j] hop2_mean_similarity={hop2_mean} (n={hop2_cnt})")
    print(f"[Neo4j] hop3_mean_similarity={hop3_mean} (n={hop3_cnt})")
    print("-" * 60)

    return {
        **state,
        "cypher": cypher,
        "neo4j_candidates": candidates,      # ✅ 2/3-hop만 들어옴
        "hop2_mean_similarity": hop2_mean,   # ✅ 평균 저장
        "hop3_mean_similarity": hop3_mean,
        "hop2_sim_count": hop2_cnt,          # ✅ 평균에 반영된 개수
        "hop3_sim_count": hop3_cnt,
    }
