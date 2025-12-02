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


def clean_entity_name(name: str) -> str:
    """정규화된 ID를 사람이 읽을 수 있는 이름으로 변환"""
    import re
    
    # hist:Entity_해시코드 형태 제거
    if "_" in name and len(name.split("_")[-1]) == 8:
        # 해시코드가 있는 경우 (예: Institution_d4c9663e)
        parts = name.split("_")
        if len(parts) >= 2 and parts[-1].isalnum():
            # 해시 제거하고 타입만 남김
            return "_".join(parts[:-1])
    
    # hist: 접두사 제거
    name = re.sub(r'^hist:', '', name)
    
    # 언더스코어를 공백으로
    name = name.replace("_", " ")
    
    return name


def format_evidence_for_prompt(evidences: list) -> tuple:
    """근거를 프롬프트용으로 포맷팅 (본문용 + 각주용)"""
    
    formatted_list = []
    footnotes = []
    
    for i, ev in enumerate(evidences, 1):
        # raw_data에서 실제 내용 추출
        raw_data = ev.get('raw_data', {})
        
        # 실제 내용 (content > summary > description 순)
        content = raw_data.get('content', '') or raw_data.get('summary', '') or ''
        
        # 설명에서 정규화된 ID 정리
        desc = ev.get('description', '')
        desc = clean_entity_name(desc)
        
        # 엔티티명 추출 (desc에서 : 앞부분)
        entity_name = desc.split(':')[0].strip() if ':' in desc else desc[:30]
        entity_name = clean_entity_name(entity_name)
        
        # 실제 내용이 있으면 사용, 없으면 description 사용
        if content:
            display_text = f"{entity_name}: {content[:150]}"
        else:
            display_text = desc[:150] if desc else entity_name
        
        # 프롬프트용 (상세)
        formatted_list.append(f"[{i}] {display_text}")
        
        # 각주용 (간략)
        footnotes.append(f"{i}. {entity_name}: {content[:80] if content else '관련 정보'}{'...' if len(content) > 80 else ''}")
    
    return "\n".join(formatted_list), "\n".join(footnotes)


def story_generator_node(state: GraphState) -> GraphState:
    """근거 기반 스토리 생성 (가독성 개선)"""

    query = state.get("query", "")
    query_type = state.get("query_type", "causal")
    query_intent = state.get("query_intent", "")  # 핵심 의도 (예: "건축/창건 관계")
    relation_keywords = state.get("relation_keywords", [])  # 관계 키워드
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
1. 해당 주제에 대한 상세 데이터가 아직 구축되지 않았습니다.
2. 질문의 범위가 현재 데이터로 커버하기 어렵습니다.
3. 쿼리 처리 중 시간 초과가 발생했습니다.

더 구체적인 질문이나 특정 인물/사건에 대한 질문을 시도해 주세요."""

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

    # 근거 정보 포맷팅 (정규화된 ID 정리)
    evidence_text, footnotes = format_evidence_for_prompt(evidences)

    # 질문 유형별 프롬프트 조정
    if query_type == "what_if":
        instruction = """가상 시나리오에 기반한 대체 역사 스토리를 작성해 주세요.
- "만약 ~했다면" 형식으로 시작합니다
- 추론된 인과관계를 자연스럽게 설명합니다
- 실제 역사와의 차이점을 명확히 합니다"""

    elif query_type == "deep_analysis":
        instruction = """역사의 이면과 숨은 동기를 분석해 주세요.
- 여러 근거를 종합하여 깊이 있는 해석을 제시합니다
- 당시 정치적/사회적 맥락을 설명합니다
- 다양한 관점에서 분석합니다"""

    else:  # causal
        instruction = """인과관계를 명확히 설명해 주세요.
- 원인과 결과를 논리적으로 연결합니다
- 시간 순서대로 전개합니다
- 각 사건의 영향 관계를 설명합니다"""

    # 참고 근거 상세 정보 (출력용) - 실제 내용 포함
    evidence_detail_list = []
    for i, ev in enumerate(evidences[:10], 1):
        raw_data = ev.get('raw_data', {})
        
        # 실제 내용 추출 (content > summary > description 순서)
        content = raw_data.get('content', '') or raw_data.get('summary', '') or ''
        
        # 연도 정보 추출
        year = raw_data.get('year', '') or raw_data.get('hasYear', '')
        year_str = f"({year}년) " if year else ""
        
        # 엔티티명 추출
        desc = ev.get('description', '')
        entity_name = desc.split(':')[0].strip() if ':' in desc else desc[:30]
        entity_name = clean_entity_name(entity_name)
        
        # 상세 설명 생성 - 실제 내용 포함 (관련 역사 정보 제거)
        if content:
            detail = f"[{i}] {year_str}{entity_name}: {content[:120]}{'...' if len(content) > 120 else ''}"
        else:
            # 내용이 없으면 description 사용
            desc_content = desc.replace(entity_name + ':', '').strip()[:100] if desc else ''
            if desc_content:
                detail = f"[{i}] {year_str}{entity_name}: {desc_content}"
            else:
                detail = f"[{i}] {year_str}{entity_name}"
        
        evidence_detail_list.append(detail)
    evidence_details = "\n".join(evidence_detail_list)

    # 의도 정보 추가
    intent_info = ""
    if query_intent:
        intent_info = f"\n## 질문의 핵심 의도\n{query_intent}"
        if relation_keywords:
            intent_info += f"\n관련 키워드: {', '.join(relation_keywords)}"
        intent_info += "\n→ 근거에서 이 의도와 관련된 정보를 우선적으로 사용하세요.\n"

    story_prompt = f"""당신은 조선시대 역사를 전문적으로 설명하는 역사가입니다.

## 질문
{query}
{intent_info}
## 참고 근거 ({len(evidences)}개)
{evidence_text}

## 작성 지침
{instruction}

## 필수 규칙

### 1. 말투: "-입니다" 체로 작성
   - 반드시 존댓말 "-입니다", "-습니다", "-됩니다" 체로 작성하세요.

### 2. 되묻지 않기
   - 추가 정보를 요청하거나 질문을 되묻지 마세요.
   - 주어진 근거만으로 최선의 답변을 작성하세요.

### 3. 명확한 근거 제시 (중요!)
   - 반드시 **연도, 사건명, 인물명, 문헌명**을 명시하세요.
   - 나쁜 예: "궁궐이 지어졌습니다."
   - 좋은 예: "1395년 태조 이성계가 경복궁을 창건하였습니다."
   - 나쁜 예: "왕이 정책을 시행했습니다."
   - 좋은 예: "세종대왕이 1446년 훈민정음을 반포하였습니다."

### 4. 각주 형식: [1][2][3]
   - 문장 끝에 **[1][2][3]** 형태로 근거 번호를 표시하세요.
   - 나쁜 예: "(참고: 1, 2)"
   - 좋은 예: "경복궁은 1395년에 창건되었습니다.[1][3]"

### 5. 정규화된 ID 사용 금지
   - "Institution_d4c9663e" 같은 코드 절대 사용 금지
   - 실제 이름을 모르면 "관련 기관" 등으로 대체

### 6. 추측 표시
   - 확실하지 않은 내용은 "~로 추정됩니다", "~했을 것으로 보입니다"로 표현

## 출력 형식 (반드시 이 형식 준수)

[본문]
2-3문단으로 자연스럽게 서술 (200-400자, "-입니다" 체)
- 연도, 사건명, 인물명을 명확히 언급
- 문장 끝에 [1][2] 형태로 근거 표시

[요약]
한 문장으로 핵심 정리 ("-입니다" 체)

[참고 근거]
{evidence_details}"""

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
        final_answer = f"죄송합니다. 질문 '{query}'에 대한 답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."
        answer_with_sources = {"story": final_answer, "sources": [], "error": str(e)}

    return {
        **state,
        "final_answer": final_answer,
        "answer_with_sources": answer_with_sources,
        "executed_nodes": state.get("executed_nodes", []) + ["story_generator"]
    }
