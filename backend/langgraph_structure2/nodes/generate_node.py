from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.state_type import Evidence, EvidencePayload
from backend.langgraph_structure1.utils import create_model
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

    prompt = f"""
    당신은 한국사를 설명하는 교사입니다.

    아래에는 학생의 질문과, 그 질문과 직접적으로 관련된 근거 자료들이 주어집니다.
    이 근거들을 바탕으로, 학생이 읽으면 한 단원 설명처럼 느껴질 정도로 **충분히 자세한** 설명 글을 작성해 주세요.

    [질문]
    {question}

    [근거 자료]
    {evidence_block}

    지침:
    - 답변은 반드시 한국어로 작성합니다.
    - 한두 줄짜리 요약이 아니라, 배경 → 전개 → 결과·의의가 드러나는 **완성된 설명문**을 작성합니다.
    - 전체 분량은 3~5단락 정도로 작성합니다.
    - 각 단락은 서로 다른 초점을 가지게 합니다.
    - 1단락: 사건의 배경과 원인
    - 2단락: 주요 전개 과정과 핵심 인물
    - 3단락: 결과와 역사적 의의
    - 필요하면 4단락 정도까지는 허용하되, 같은 내용을 다시 반복해서 설명하지 않습니다.
    - 같은 사실(연도, 전쟁 기간, 주요 인물의 역할, 원인·결과 등)은 한 번만 명확히 설명하고, 이후에 다시 반복하거나 비슷한 문장을 다시 쓰지 않습니다.
    - 근거 자료에 있는 정보들을 중심으로 서술하고, 근거에 전혀 없는 사실은 새로 지어내지 않습니다.
    - 서로 다른 근거의 내용을 자연스럽게 이어 붙여, 시간 순서 또는 인과 관계가 드러나게 구성합니다.
    - 목록, 불릿, 번호 매기기를 사용하지 말고, 연속된 문단 형태로만 작성합니다.
    - 최종 출력에는 위의 [질문], [근거 자료], '지침'이라는 말은 포함하지 말고, 설명 본문만 출력합니다.
    """
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
    if not vector_evidences and not neo4j_results:
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
            evidences = neo4j_evidences
    elif vector_evidences and not neo4j_results:
        evidences = vector_evidences

    # 둘 다 없을 때
    elif not vector_evidences and not neo4j_results:
        return {
            **state,
            "final_answer": (
                "주어진 자료에서는 해당 질문에 대한 관련 정보를 찾을 수 없습니다. "
                "더 구체적인 질문이나 추가 자료가 필요합니다."
            )
        }


    prompt = build_llm_prompt(question, evidences)

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

    print("[최종 답변]")
    print(final_answer)
    print("-" * 60)

    return {
        **state,
        "final_answer": final_answer,
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