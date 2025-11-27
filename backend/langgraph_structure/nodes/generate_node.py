from langgraph_structure.state import GraphState
from typing import List, Dict, Any


def generate_node(state: GraphState) -> GraphState:
    """
    - evaluate_node 에서 넘어온 context_chunks / num
    - neo4j_query_node 에서 넘어온 neo4j_results
    를 기반으로 최종 답변(final_answer)을 생성하는 노드.

    현재는 규칙 기반으로 간단히 문장을 만드는 더미 구현이며,
    나중에 이 안의 로직을 LLM 호출로 교체하면 됨.
    """

    context_chunks: List[Dict[str, Any]] = state.get("context_chunks", [])
    neo4j_results: List[Dict[str, Any]] = state.get("neo4j_results", [])
    num: int = state.get("num", 0)

    # 1) Neo4j 결과가 있을 때: KG 기반 답변
    if neo4j_results:
        # 간단히 첫 번째 결과만 사용 (나중에 요약/정제는 LLM이 담당)
        first_row: Dict[str, Any] = neo4j_results[0]

        # key-value를 간단히 나열해서 문장으로 변환
        kv_parts = []
        for k, v in first_row.items():
            kv_parts.append(f"{k}: {v}")
        kv_text = ", ".join(kv_parts)

        final_answer = (
            "질문과 관련된 정보를 지식그래프(Neo4j)에서 찾았습니다.\n"
            f"- 주요 결과: {kv_text}\n"
            "\n위 내용은 그래프 데이터에서 직접 조회한 결과이며, "
            "추가적인 맥락이 필요하다면 더 구체적인 질문을 해 주세요."
        )

    # 2) Neo4j 결과는 없고, RAG context만 있을 때: 문서 기반 답변
    elif context_chunks:
        # 가장 관련도가 높은 첫 청크 기준으로 간단 요약 (더미)
        top_chunk = context_chunks[0]
        content_preview = str(top_chunk.get("content", ""))[:150]  # 앞 150자만

        final_answer = (
            "질문과 유사한 문서를 기반으로 다음과 같은 정보를 찾았습니다.\n\n"
            f"요약 내용(일부 발췌):\n{content_preview}\n\n"
            f"위 정보는 총 {num}개의 관련 청크에서 추출된 내용입니다. "
            "자세한 내용이 필요하시면 특정 부분을 지정해서 다시 질문해 주세요."
        )

    # 3) 둘 다 없을 때: 아무 정보도 못 찾은 경우
    else:
        final_answer = (
            "죄송하지만, 현재 제공된 문서나 지식그래프에서 "
            "질문과 직접적으로 관련된 정보를 찾지 못했습니다.\n"
            "질문을 조금 더 구체적으로 표현해 주시거나, "
            "다른 키워드로 다시 시도해 주시면 도움이 될 수 있습니다."
        )

    return {
        **state,
        "final_answer": final_answer,
    }
