"""
Story Generator Node

추론 경로와 근거를 바탕으로 자연스러운 스토리 생성
- 인과관계 표현 ("~때문에", "~로 인해")
- 근거 제시
- 질문 유형별 스타일 조정
- 근거 없을 시 환각 방지
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# .env 파일 로드 (프로젝트 루트에서)
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path, override=True)

from state import GraphState


def story_generator_node(state: GraphState) -> GraphState:
    """근거 기반 스토리 생성"""

    query = state.get("query", "")
    query_type = state.get("query_type", "causal")
    evidences = state.get("evidences", [])
    causal_chains = state.get("causal_chains", [])
    extracted_entities = state.get("extracted_entities", [])

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0.7  # 스토리 생성은 창의성 필요
    )

    # 근거가 없는 경우 처리
    if not evidences or len(evidences) == 0:
        print(f"⚠️ 근거 없음 - 데이터 부족 안내 생성")
        
        # 추출된 엔티티 정보
        entity_info = ""
        if extracted_entities:
            entity_names = [e.get("label", e.get("name", "")) for e in extracted_entities[:5]]
            entity_info = f"관련 엔티티({', '.join(entity_names)})는 발견되었으나, "
        
        final_answer = f"""죄송합니다. 질문 "{query}"에 대해 충분한 근거 데이터를 찾지 못했습니다.

{entity_info}현재 온톨로지 데이터베이스에서 해당 질문에 답변할 수 있는 구체적인 관계 정보가 부족합니다.

가능한 원인:
1. 해당 주제에 대한 상세 데이터가 아직 구축되지 않음
2. 질문의 범위가 현재 데이터로 커버하기 어려움
3. 쿼리 처리 중 시간 초과 발생

더 구체적인 질문이나 특정 인물/사건에 대한 질문을 시도해 보세요."""

        answer_with_sources = {
            "story": final_answer,
            "sources": [],
            "query_type": query_type,
            "evidence_count": 0,
            "data_insufficient": True
        }

        return {
            **state,
            "final_answer": final_answer,
            "answer_with_sources": answer_with_sources,
            "executed_nodes": state.get("executed_nodes", []) + ["story_generator"]
        }

    # 근거 정보 포맷팅 (명확한 번호 매핑)
    evidence_text = "\n".join([
        f"[근거 {i}] {ev['description']} (출처: {ev.get('source', 'unknown')}, 신뢰도: {ev['weight']:.0%})"
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

=== 제공된 근거 (총 {len(evidences)}개) ===
{evidence_text}
=== 근거 끝 ===

{instruction}

⚠️ 중요 규칙:
1. 오직 위에 제공된 근거만 사용하세요
2. 제공되지 않은 정보를 추가하거나 만들어내지 마세요
3. 근거 번호는 위에 명시된 [근거 N] 형식을 정확히 사용하세요
4. 근거가 {len(evidences)}개이므로, [근거 1]~[근거 {len(evidences)}]만 사용 가능합니다
5. 추측이나 가정은 "~로 추정된다", "~했을 가능성이 있다"로 명확히 표시하세요

요구사항:
1. 자연스러운 한국어 (2-3문단, 200-300자)
2. 모든 주장에 해당 근거 번호 표시 (예: "이순신이 전략을 바꾼 것은 [근거 1]에서 확인됩니다")
3. 제공된 근거에 기반한 사실만 서술
4. 마지막에 핵심 요약 한 문장

출력 형식:
[스토리 본문]
"""

    try:
        response = llm.invoke(story_prompt)
        final_answer = response.content.strip()

        print(f"📖 스토리 생성 완료 ({len(final_answer)}자, 근거 {len(evidences)}개 사용)")

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
