"""
Story Generator Node

추론 경로와 근거를 바탕으로 자연스러운 스토리 생성
- 인과관계 표현 ("~때문에", "~로 인해")
- 근거 제시
- 질문 유형별 스타일 조정
"""

import os
from langgraph_structure.state import GraphState
from langchain_openai import ChatOpenAI


def story_generator_node(state: GraphState) -> GraphState:
    """근거 기반 스토리 생성"""

    query = state.get("query", "")
    query_type = state.get("query_type", "causal")
    evidences = state.get("evidences", [])
    causal_chains = state.get("causal_chains", [])

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        temperature=0.7  # 스토리 생성은 창의성 필요
    )

    # 근거 정보 포맷팅
    evidence_text = "\n".join([
        f"{i}. {ev['description']} (근거 강도: {ev['weight']:.0%})"
        for i, ev in enumerate(evidences, 1)
    ])

    # 질문 유형별 프롬프트 조정
    if query_type == "what_if":
        instruction = """가상 시나리오에 기반한 대체 역사 스토리를 작성하세요.
- "만약 ~했다면" 형식
- 추론된 인과관계를 명확히 설명
- 실제 역사와의 차이점 강조"""

    elif query_type == "deep_analysis":
        instruction = """역사의 이면과 숨은 동기를 분석하는 스토리를 작성하세요.
- "진짜 이유는..." 형식
- 여러 근거를 종합하여 깊이 있는 분석
- 당시 상황과 맥락 설명"""

    else:  # causal
        instruction = """인과관계를 명확히 설명하는 스토리를 작성하세요.
- "~때문에", "~로 인해" 같은 인과 표현 사용
- 시간 순서대로 설명
- 각 단계의 영향 설명"""

    story_prompt = f"""당신은 조선시대 역사 스토리텔러입니다.

질문: {query}
질문 유형: {query_type}

추론된 근거:
{evidence_text or "근거가 부족합니다."}

{instruction}

요구사항:
1. 자연스러운 한국어 (2-3문단, 200-300자)
2. 모든 주장에 근거 번호 표시 (예: "명량해전의 승리로 [근거 1]")
3. 역사적 사실 기반
4. 마지막에 핵심 요약 한 문장

출력 형식:
[스토리 본문]
"""

    try:
        response = llm.invoke(story_prompt)
        final_answer = response.content.strip()

        print(f"📖 스토리 생성 완료 ({len(final_answer)}자)")

        # 근거 포함 답변 구성
        answer_with_sources = {
            "story": final_answer,
            "sources": evidences,
            "query_type": query_type,
            "evidence_count": len(evidences)
        }

    except Exception as e:
        print(f"❌ 스토리 생성 실패: {e}")
        final_answer = f"죄송합니다. 질문 '{query}'에 대한 답변을 생성하지 못했습니다."
        answer_with_sources = {"story": final_answer, "sources": [], "error": str(e)}

    return {
        **state,
        "final_answer": final_answer,
        "answer_with_sources": answer_with_sources,
        "executed_nodes": state.get("executed_nodes", []) + ["story_generator"]
    }
