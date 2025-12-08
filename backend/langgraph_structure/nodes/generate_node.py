from backend.langgraph_structure.state import GraphState
from backend.langgraph_structure.state_type import Evidence, EvidencePayload
from backend.langgraph_structure.utils import create_model
from typing import List, Dict, Any


def build_llm_prompt(question: str, evidences: List[Evidence]) -> str:
    """
    상위 evidence들을 사람이 읽기 좋은 텍스트로 펼쳐서
    LLM에게 줄 프롬프트를 만든다.
    """
    parts = []
    for idx, ev in enumerate(evidences, start=1):
        src = ev["source"]
        payload = ev["payload"]
        meta = payload.get("metadata", {})
        content = str(payload.get("content", ""))

        if src == "graph":
            title = meta.get("title", "")
            category = meta.get("category", "")
            header = f"[그래프 근거 #{idx}]"
            if category:
                header += f" (분류: {category})"
            if title:
                header += f" 제목: {title}"
            parts.append(f"{header}\n요약: {content}")
        else:  # vector
            header = f"[문서 근거 #{idx}]"
            parts.append(f"{header}\n내용: {content[:1200]}")  # 길이 적당히 제한

    evidence_block = "\n\n".join(parts)

    prompt = (
        "아래에는 질문과 근거 자료들이 제공됩니다.\n"
        "당신의 임무는 이 근거들에서 확인할 수 있는 사실만을 사용하여, "
        "**최종 자연어 답변이 아니라 구조화된 '중간 답변(ANSWER_DRAFT)'** 을 만드는 것입니다.\n\n"

        "출력 형식은 반드시 다음과 동일하게 해주세요:\n"
        "[ANSWER_DRAFT]\n"
        "background: | 리스트\n"
        "causes: | 리스트\n"
        "events: | 리스트\n"
        "results: | 리스트\n"
        "limitations: | 리스트\n"
        "[/ANSWER_DRAFT]\n\n"

        "각 섹션은 bullet 리스트 형태로 작성하며, 자연어 문장 스타일로 꾸미지 마세요.\n"
        "요약형도 아니고, 최종 문장도 아니며, **단지 사실의 정리 목록**만 제공하면 됩니다.\n\n"

        f"[QUESTION]\n{question}\n\n"
        f"[EVIDENCES]\n{evidence_block}\n\n"
        "위 형식에 맞는 ANSWER_DRAFT 만 출력하세요."
    )
    return prompt


def generate_node(state: GraphState) -> GraphState:
    """
    - vector_evidences : retrieval_node 에서 넘어온 벡터 검색 결과 (Evidence 리스트)
    - neo4j_results    : neo4j_query_node 에서 넘어온 검색 결과(JSON, similarity 포함)
    를 기반으로 최종 답변(final_answer)을 생성하는 노드.
    """
    question = state["query"]
    vector_evidences: List[Evidence] = state.get("vector_evidences", [])
    neo4j_results: List[Dict[str, Any]] = state.get("neo4j_results", [])

    # 1) Neo4j 결과를 Evidence 형식으로 변환
    neo4j_evidences: List[Evidence] = []
    for row in neo4j_results:
        similarity = float(row.get("similarity", 0.0))
        payload: EvidencePayload = {
            "content": row.get("summary", ""),
            "metadata": {
                "title": row.get("title", ""),
                "category": row.get("category", ""),
                "raw": row,
            },
        }
        neo4j_evidences.append(
            {
                "source": "graph",
                "score": similarity,
                "payload": payload,
            }
        )

    # 2) 벡터/그래프 evidence를 한 줄로 모아서 score 기준 정렬
    all_evidences: List[Evidence] = vector_evidences + neo4j_evidences

    if all_evidences:
        all_evidences.sort(key=lambda e: e["score"], reverse=True)

        # 상위 2~3개만 사용 (원하면 top_k 조절)
        top_evidences = all_evidences[:3]

        prompt = build_llm_prompt(question, top_evidences)

        # LLM 호출, 최종 답변 생성
        client = create_model()
        MODEL_NAME = "gpt-5-mini"

        response = client.chat.completions.create(
            model=MODEL_NAME,
            response_format={"type": "text"},
            messages=[
                {"role": "user", "content": prompt},
            ],
        )

        final_answer = response.choices[0].message.content.strip()

        return {
            **state,
            "final_answer": final_answer,
        }


    # 2) 둘 다 없을 때: 아무 정보도 못 찾은 경우
    else:
        # evidence 없을 때는 그냥 안내 문구를 draft로 써도 됨
        return {
            **state,
            "final_answer": (
                "[ANSWER_DRAFT]\n"
                "background:\n- 근거 부족\n\n"
                "causes:\n- 근거 부족\n\n"
                "events:\n- 근거 부족\n\n"
                "results:\n- 근거 부족\n\n"
                "limitations:\n- 관련 근거 자료를 찾지 못함\n"
                "[/ANSWER_DRAFT]"
            ),
        }


# 테스트용
if __name__ == "__main__":
    test_state: GraphState = {
        "query": "임진왜란에 대해 설명해줘.",
        "vector_evidences": [
            {
                "source": "vector",
                "score": 0.95,
                "payload": {
                    "content": "임진왜란은 1592년부터 1598년까지 일본이 조선을 침략한 전쟁입니다...",
                    "metadata": {
                        "title": "임진왜란 개요",
                        "category": "역사",
                    },
                },
            },
            {
                "source": "vector",
                "score": 0.89,
                "payload": {
                    "content": "이순신 장군은 임진왜란 당시 조선 수군을 이끌며 많은 승리를 거두었습니다...",
                    "metadata": {
                        "title": "이순신과 임진왜란",
                        "category": "역사",
                    },
                },
            },
        ],
        "neo4j_results": [
            {
                "title": "임진왜란의 원인",
                "category": "역사",
                "summary": "임진왜란의 주요 원인은 일본의 팽창주의와 조선의 내부 분열 등이 있습니다.",
                "similarity": 0.92,
            }
        ],
    }
    result_state = generate_node(test_state)
    print("최종 답변:")
    print(result_state["final_answer"])