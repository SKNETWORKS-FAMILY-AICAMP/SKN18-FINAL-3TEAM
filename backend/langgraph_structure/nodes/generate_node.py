from backend.langgraph_structure.state import GraphState
from backend.langgraph_structure.state_type import Evidence
from backend.db_pipeline.services.embedding_model import get_embedding
from typing import List, Dict, Any
from numpy import dot
from numpy.linalg import norm

def neo4j_row_to_text(row: dict) -> str:
    """
    Neo4j 결과 한 개(row)를 임베딩 입력용 문자열로 변환.
    """
    parts = [f"{k}: {v}" for k, v in row.items()]
    return ", ".join(parts)

def cosine_similarity(a, b):
    return dot(a, b) / (norm(a) * norm(b))

embed = get_embedding()

def compute_neo4j_similarity(query_text, row):
    row_text = neo4j_row_to_text(row)
    q_emb = embed.embed_query(query_text)
    r_emb = embed.embed_query(row_text)
    return cosine_similarity(q_emb, r_emb)

def generate_node(state: GraphState) -> GraphState:
    """
    - evaluate_node 에서 넘어온 context_chunks / num
    - neo4j_query_node 에서 넘어온 neo4j_results
    를 기반으로 최종 답변(final_answer)을 생성하는 노드.

    현재는 규칙 기반으로 간단히 문장을 만드는 더미 구현이며,
    나중에 이 안의 로직을 LLM 호출로 교체하면 됨.
    """

    vector_evidences: List[Evidence] = state.get("vector_evidences", [])
    neo4j_results: List[Dict[str, Any]] = state.get("neo4j_results", [])
    num: int = state.get("num", 0)

    # 1) 유사도 점수로 sorting 후 상위 정보 활용
    if neo4j_results or vector_evidences:
        question = state["query"]
        
        # Neo4j 결과로 유사도 점수 매기기
        neo4j_evidences = []
        for row in neo4j_results:
            score = compute_neo4j_similarity(question, row)
            neo4j_evidences.append({
                "source": "graph",
                "score": float(score),
                "payload": row
            })
        

        # VectorDB 청크 요약
        top_chunk = vector_evidences[0]
        content_preview = str(top_chunk.get("content", ""))[:150]  # 앞 150자만

        # 유사도 점수로 정렬
        all_evidences = vector_evidences + neo4j_evidences
        all_evidences.sort(key=lambda e: e["score"], reverse=True)

        top_evidences = all_evidences[:3]

        # 취합된 상위 정보로 요약 텍스트 생성
        # openai 호출

        
        final_answer = (
            "질문과 관련된 정보를 지식그래프(Neo4j)와 문서에서 모두 찾았습니다.\n\n"
            f"- 지식그래프 주요 결과: {kv_text}\n\n"
            f"- 문서 요약 내용(일부 발췌):\n{content_preview}\n\n"
            f"위 정보는 그래프 데이터와 총 {num}개의 관련 청크에서 추출된 내용입니다. "
            "추가적인 맥락이나 세부사항이 필요하시면 더 구체적인 질문을 해 주세요."
        )


    # 2) 둘 다 없을 때: 아무 정보도 못 찾은 경우
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
