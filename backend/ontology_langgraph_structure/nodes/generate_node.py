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


def format_evidence_for_prompt(evidences: list, query: str = "") -> tuple:
    """근거를 학술적 서적 스타일로 포맷팅

    참고문헌처럼 신뢰성 있게 작성:
    - 인물: 생몰년, 주요 활동, 역할 명시
    - 사건: 연도, 배경, 참여자, 결과 서술
    - 제도: 시행 시기, 목적, 내용 설명
    """

    formatted_list = []
    footnotes = []

    # 엔티티 타입별로 그룹화
    evidence_by_type = {
        'Person': [],
        'Event': [],
        'Institution': [],
        'Place': [],
        'Concept': [],
        'Other': []
    }

    for ev in evidences:
        ev_type = ev.get('type', 'Other')
        if ev_type not in evidence_by_type:
            ev_type = 'Other'
        evidence_by_type[ev_type].append(ev)

    idx = 1

    # 타입별로 정리하여 출력 (Event → Person → Institution → Place → Concept → Other 순서)
    for ev_type in ['Event', 'Person', 'Institution', 'Place', 'Concept', 'Other']:
        items = evidence_by_type[ev_type]
        if not items:
            continue

        for ev in items:
            raw_data = ev.get('raw_data', {})
            desc = ev.get('description', '')
            desc = clean_entity_name(desc)

            # 기본 정보 추출
            content = raw_data.get('content', '') or raw_data.get('summary', '') or ''
            year = raw_data.get('year', '') or raw_data.get('hasYear', '')

            # 관계 정보 파싱
            subject = ""
            predicate = ""
            obj = ""

            if "↔" in desc or "→" in desc:
                parts = desc.split("↔") if "↔" in desc else desc.split("→")
                if len(parts) >= 3:
                    subject = parts[0].strip()
                    predicate = parts[1].strip().replace("[", "").replace("]", "")
                    obj = parts[2].strip()

            # 타입별로 학술적 문장 생성
            sentence = ""
            footnote_prefix = ""

            if ev_type == 'Event':
                # 사건: "연도에 발생한 사건명은..."
                footnote_prefix = "【사건】 "
                if year and subject:
                    sentence = f"{year}년에 발생한 {subject}"
                    if obj and predicate:
                        sentence += f"는 {obj}와 관련이 있습니다"
                    if content:
                        sentence += f". {content}"
                elif content:
                    sentence = content
                else:
                    sentence = desc

            elif ev_type == 'Person':
                # 인물: "인물명(연도)은 역할..."
                footnote_prefix = "【인물】 "
                if subject:
                    sentence = f"{subject}"
                    if year:
                        sentence += f"({year}년)"
                    if obj and predicate:
                        if predicate in ['appointed', 'served']:
                            sentence += f"는 {obj}의 직책을 역임했습니다"
                        elif predicate in ['participated', 'participatedIn']:
                            sentence += f"는 {obj}에 참여한 인물입니다"
                        elif predicate in ['died', 'diedIn']:
                            sentence += f"는 {obj}에서 사망했습니다"
                        else:
                            sentence += f"는 {obj}와 관련된 활동을 했습니다"
                    if content:
                        sentence += f". {content}"
                elif content:
                    sentence = content
                else:
                    sentence = desc

            elif ev_type == 'Institution':
                # 제도/기관: "제도명은 연도에 설립/운��..."
                footnote_prefix = "【제도】 "
                if subject:
                    sentence = f"{subject}"
                    if year:
                        sentence += f"({year}년)"
                    if obj and predicate:
                        if predicate in ['founded', 'established']:
                            sentence += "는 설립되었습니다"
                        elif predicate in ['abolished', 'dissolved']:
                            sentence += "는 폐지되었습니다"
                        else:
                            sentence += f"는 {obj}와 관련이 있습니다"
                    if content:
                        sentence += f". {content}"
                elif content:
                    sentence = content
                else:
                    sentence = desc

            elif ev_type == 'Place':
                # 장소: "장소명은 연도에 건립..."
                footnote_prefix = "【장소】 "
                if subject:
                    sentence = f"{subject}"
                    if year:
                        sentence += f"({year}년)"
                    if obj and predicate:
                        if predicate in ['built', 'constructed']:
                            sentence += "가 건축되었습니다"
                        elif predicate == 'located':
                            sentence += f"는 {obj}에 위치합니다"
                        else:
                            sentence += f"는 {obj}와 관련이 있습니다"
                    if content:
                        sentence += f". {content}"
                elif content:
                    sentence = content
                else:
                    sentence = desc

            elif ev_type == 'Concept':
                # 개념/사상: "개념명은..."
                footnote_prefix = "【개념】 "
                if subject:
                    sentence = f"{subject}"
                    if obj and predicate:
                        if predicate == 'adoptsIdeology':
                            sentence += f"는 {obj}의 핵심 이념으로 채택되었습니다"
                        elif predicate == 'influences':
                            sentence += f"는 {obj}에 사상적 영향을 미쳤습니다"
                        else:
                            sentence += f"는 {obj}와 관련된 사상입니다"
                    if content:
                        sentence += f". {content}"
                elif content:
                    sentence = content
                else:
                    sentence = desc
            else:
                # 기타
                sentence = content if content else desc

            # 프롬프트용 (LLM이 참고할 용도 - 간결하게)
            formatted_list.append(f"[{idx}] {sentence}")

            # 각주용 (사용자에게 보여질 용도 - 타입 명시 + 상세하게)
            footnote = f"[{idx}] {footnote_prefix if footnote_prefix else ''}{sentence}"

            footnotes.append(footnote)
            idx += 1

    return "\n".join(formatted_list), "\n".join(footnotes)


def story_generator_node(state: GraphState) -> GraphState:
    """근거 기반 스토리 생성 (가독성 개선)"""

    import time
    node_start = time.time()

    query = state.get("query", "")
    is_historical = state.get("is_historical", True)
    
    # 역사 관련이 아닌 경우 (classify_node에서 이미 설정된 답변 사용)
    if not is_historical:
        final_answer = state.get("final_answer", f"""죄송합니다. "{query}"는 조선시대 한국 역사와 관련된 질문이 아닙니다.

이 시스템은 조선시대의 인물, 사건, 제도, 정책, 장소 등에 대한 질문에만 답변할 수 있습니다.

조선시대 역사 관련 질문을 해주시면 도와드리겠습니다.""")
        
        return {
            **state,
            "final_answer": final_answer,
            "answer_with_sources": state.get("answer_with_sources", {
                "story": final_answer,
                "sources": [],
                "query_type": "non_historical",
                "evidence_count": 0
            }),
            "executed_nodes": state.get("executed_nodes", []) + ["story_generator"]
        }
    
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

    print(f"\n{'='*70}")
    print(f"[6/6] 스토리 생성 (Story Generator)")
    print(f"{'='*70}")

    # 근거가 없는 경우 처리
    if not evidences or len(evidences) == 0:
        
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

    # 추출된 엔티티 정보 포맷팅 (프롬프트에 포함)
    entity_info_text = ""
    if extracted_entities:
        entity_names = []
        for e in extracted_entities[:10]:  # 상위 10개만
            name = e.get("name", "") or e.get("label", "")
            entity_type = e.get("type", "Unknown")
            if name:
                entity_names.append(f"{entity_type}: {name}")
        if entity_names:
            entity_info_text = f"\n## 추출된 핵심 엔티티\n{', '.join(entity_names)}\n→ 이 엔티티들을 반드시 답변에 포함하고 설명하세요.\n"
    
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

    # 참고 근거를 학술적 스타일로 포맷팅 (format_evidence_for_prompt 함수 사용)
    evidence_list, evidence_footnotes = format_evidence_for_prompt(evidences, query)
    evidence_details = "\n".join(evidence_footnotes)

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
{entity_info_text}
{intent_info}
## 참고 근거 (총 {len(evidences)}개)
아래 근거를 참고하여 답변을 작성하세요:

{evidence_details}

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

### 3-1. 추출된 엔티티 우선 사용
   - 질문에서 추출된 핵심 엔티티(예: 갑술환국, 기사환국, 경신환국)를 반드시 언급하세요.
   - 추출된 엔티티가 근거에 없으면, 해당 엔티티에 대한 정보를 명시적으로 설명하세요.

### 4. 각주 형식: [1][2][3]
   - 문장 끝에 **[1][2][3]** 형태로 근거 번호를 표시하세요.
   - 나쁜 예: "(참고: 1, 2)"
   - 좋은 예: "경복궁은 1395년에 창건되었습니다.[1][3]"

### 5. 정규화된 ID 사용 금지
   - "Institution_d4c9663e" 같은 코드 절대 사용 금지
   - 실제 이름을 모르면 "관련 기관" 등으로 대체

### 6. 추측 표시
   - 확실하지 않은 내용은 "~로 추정됩니다", "~했을 것으로 보입니다"로 표현

## 출력 형식 (반드시 준수)

[본문]
2-3문단으로 자연스럽게 서술 (200-400자, "-입니다" 체)
- 연도, 사건명, 인물명을 명확히 언급
- 문장 끝에 [1][2] 형태로 근거 번호 표시

[요약]
한 문장으로 핵심 정리 ("-입니다" 체)

**주의: [본문]과 [요약]만 출력하세요. 다른 섹션은 출력하지 마세요.**"""

    try:
        response = llm.invoke(story_prompt)
        llm_answer = response.content.strip()

        # LLM 생성 답변 ([본문], [요약])에 [참고 근거] 섹션 추가
        if llm_answer and evidence_details:
            final_answer = f"{llm_answer}\n\n[참고 근거]\n{evidence_details}"
        else:
            final_answer = llm_answer

        print(f"  └─ 완료: {len(llm_answer)}자 생성 (근거 {len(evidences)}개 사용)")
        print()

        # 근거 포함 답변 구성
        answer_with_sources = {
            "story": final_answer,
            "sources": evidences,
            "query_type": query_type,
            "evidence_count": len(evidences)
        }

    except Exception as e:
        print(f"오류: 스토리 생성 실패: {e}")
        final_answer = f"죄송합니다. 질문 '{query}'에 대한 답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."
        answer_with_sources = {"story": final_answer, "sources": [], "error": str(e)}

    # 노드 실행 시간 기록
    node_elapsed = time.time() - node_start
    node_times = state.get("node_execution_times", {})
    node_times["story_generator"] = node_elapsed

    return {
        **state,
        "final_answer": final_answer,
        "answer_with_sources": answer_with_sources,
        "executed_nodes": state.get("executed_nodes", []) + ["story_generator"],
        "node_execution_times": node_times
    }
