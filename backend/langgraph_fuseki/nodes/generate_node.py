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
from langchain_openai import ChatOpenAI

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# config.py를 import하면 자동으로 환경변수가 로드됨
# (config.py에서 load_dotenv가 실행됨)
from backend.langgraph_fuseki.config import PROJECT_ROOT

from backend.langgraph_fuseki.state import GraphState


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


def deduplicate_and_select_top_evidences(evidences: list, top_k: int = 5) -> list:
    """근거 중복 제거 및 주요 top_k개 선택
    
    중복 기준:
    1. 같은 description
    2. 같은 URI (raw_data에서 추출)
    3. 같은 subject-predicate-object 조합
    
    Args:
        evidences: 근거 리스트
        top_k: 선택할 상위 개수 (기본 5개)
    
    Returns:
        중복 제거 후 weight 기준 상위 top_k개 근거
    """
    if not evidences:
        return []
    
    seen = set()
    unique_evidences = []
    
    for ev in evidences:
        # 중복 판단을 위한 키 생성
        description = ev.get('description', '').strip()
        raw_data = ev.get('raw_data', {})
        
        # URI 추출 (여러 경로 시도)
        uri = ''
        if isinstance(raw_data, dict):
            uri = raw_data.get('uri', '') or raw_data.get('subject_uri', '') or raw_data.get('object_uri', '')
        
        # subject-predicate-object 추출
        subject = raw_data.get('subject', '') or raw_data.get('subject_label', '')
        predicate = raw_data.get('predicate', '') or raw_data.get('relation', '')
        obj = raw_data.get('object', '') or raw_data.get('object_label', '')
        
        # 중복 키 생성 (우선순위: description > URI > subject-predicate-object)
        if description:
            key = f"desc:{description}"
        elif uri:
            key = f"uri:{uri}"
        elif subject and predicate and obj:
            key = f"triple:{subject}|{predicate}|{obj}"
        else:
            # 키를 만들 수 없으면 그냥 추가 (중복 가능하지만 최소한)
            key = f"fallback:{len(unique_evidences)}"
        
        # 중복 체크
        if key not in seen:
            seen.add(key)
            unique_evidences.append(ev)
    
    # weight 기준으로 정렬 (내림차순)
    sorted_evidences = sorted(unique_evidences, key=lambda x: x.get('weight', 0), reverse=True)
    
    # 상위 top_k개 선택
    return sorted_evidences[:top_k]


def format_convergence_nodes(convergence_nodes: list) -> str:
    """
    수렴 노드 정보를 포맷팅하여 프롬프트에 추가

    Args:
        convergence_nodes: 수렴 노드 리스트

    Returns:
        포맷팅된 수렴 노드 정보 문자열
    """
    if not convergence_nodes:
        return ""

    formatted = []
    for i, node in enumerate(convergence_nodes[:5], 1):  # 최대 5개만
        label = node.get("label", "")
        node_type = node.get("type", "")
        connected = ", ".join(node.get("connected_entities", []))
        properties = node.get("properties", {})
        relations = node.get("relations", [])

        # 기본 정보
        node_desc = f"[수렴노드 {i}] {label}"
        if node_type:
            node_desc += f" ({node_type})"
        node_desc += f" - 연결된 엔티티: {connected}"

        # 주요 속성 추가
        prop_parts = []
        for key, value in list(properties.items())[:3]:  # 최대 3개 속성
            key_clean = key.replace("has", "").replace("_", " ")
            prop_parts.append(f"{key_clean}: {value}")
        if prop_parts:
            node_desc += f", 속성: {', '.join(prop_parts)}"

        # 주요 관계 추가
        if relations:
            rel_parts = [f"{r['predicate']} → {r['related']}" for r in relations[:3]]
            node_desc += f", 관계: {', '.join(rel_parts)}"

        formatted.append(node_desc)

    return "\n".join(formatted)


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

            # 기본 정보 추출 (summary 우선, 없으면 content, 없으면 description에서 추출)
            # raw_data에서 summary 찾기 (다양한 경로 시도)
            summary = ''
            summary_val = raw_data.get('summary', '')
            if isinstance(summary_val, dict):
                summary = summary_val.get('value', '')
            elif isinstance(summary_val, str):
                summary = summary_val
            
            # raw_data 내부의 raw_data에서도 찾기
            if not summary:
                inner_raw_data = raw_data.get('raw_data', {})
                if isinstance(inner_raw_data, dict):
                    summary_val = inner_raw_data.get('summary', '')
                    if isinstance(summary_val, dict):
                        summary = summary_val.get('value', '')
                    elif isinstance(summary_val, str):
                        summary = summary_val
            
            content = raw_data.get('content', '') or ''
            
            # summary나 content가 없으면 description에서 더 많은 정보 추출 시도
            if not summary and not content:
                # description에 ":" 가 있으면 그 뒤가 summary일 수 있음
                if ':' in desc:
                    parts = desc.split(':', 1)
                    if len(parts) > 1:
                        content = parts[1].strip()
            
            # 최종 content 결정 (summary 우선, 없으면 content)
            # summary가 있으면 LLM에게 더 풍부한 설명을 위해 summary를 명시적으로 포함
            final_content = summary if summary else content
            year = raw_data.get('year', '') or raw_data.get('hasYear', '')

            # 관계 정보 파싱
            subject = ""
            predicate = ""
            obj = ""
            
            # 엔티티 타입 확인 (raw_data에서)
            subject_type = raw_data.get('subject_type', '') or raw_data.get('type', '')
            object_type = raw_data.get('object_type', '') or raw_data.get('obj_type', '')

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
                        # 사건과 다른 엔티티의 관계 표현
                        if predicate in ['participatesIn', 'participatedIn']:
                            # 사건이 다른 사건에 "참여"하는 것은 부적절
                            sentence += f"는 {obj}와 관련이 있습니다"
                        elif predicate in ['commands', 'command']:
                            # 사건이 다른 것을 "지휘"하는 것은 부적절
                            sentence += f"는 {obj}와 관련이 있습니다"
                        elif predicate in ['partOf', 'part_of']:
                            sentence += f"는 {obj}의 일부입니다"
                        elif predicate in ['leadsTo', 'leads_to']:
                            sentence += f"는 {obj}로 이어졌습니다"
                        elif predicate in ['causedBy', 'caused_by']:
                            sentence += f"는 {obj}로 인해 발생했습니다"
                        else:
                            sentence += f"는 {obj}와 관련이 있습니다"
                    # summary가 있으면 더 상세한 설명 추가
                    if summary:
                        sentence += f". {summary}"  # summary를 명시적으로 추가
                    elif final_content:
                        sentence += f". {final_content}"
                    elif not obj:  # 관계 정보가 없으면 description 사용
                        sentence += f"는 {desc.split('→')[0].strip() if '→' in desc else desc}"
                elif final_content:
                    sentence = final_content
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
                        # 왕이나 고위 인물이 사건에 "참여"하는 표현 개선
                        is_king_or_royal = any(keyword in subject.lower() for keyword in ['왕', '군', '대군', '공주', '옹주'])
                        is_event = object_type == 'Event' or any(keyword in obj for keyword in ['전쟁', '사변', '정변', '왜란', '호란'])
                        
                        if predicate in ['participatesIn', 'participatedIn', 'participated']:
                            if is_king_or_royal and is_event:
                                # 왕이 사건에 "참여"했다는 표현 대신, 그 시대에 발생한 사건이라고 표현
                                sentence += f" 재위 시기(또는 생존 시기)에 {obj}가 발생했습니다"
                            else:
                                sentence += f"는 {obj}에 참여한 인물입니다"
                        elif predicate in ['commands', 'command']:
                            if is_king_or_royal and is_event:
                                # 왕이 사건을 "지휘"했다는 표현 대신, 그 시대에 발생한 사건이라고 표현
                                sentence += f" 재위 시기에 {obj}가 발생했습니다"
                            else:
                                sentence += f"는 {obj}를 지휘했습니다"
                        elif predicate in ['appointed', 'served']:
                            sentence += f"는 {obj}의 직책을 역임했습니다"
                        elif predicate in ['died', 'diedIn']:
                            sentence += f"는 {obj}에서 사망했습니다"
                        elif predicate in ['contemporaryWith', 'contemporary_with']:
                            sentence += f"는 {obj}와 동시대 인물입니다"
                        elif predicate in ['servedUnder', 'served_under']:
                            sentence += f"는 {obj}의 휘하에서 활동했습니다"
                        else:
                            sentence += f"는 {obj}와 관련된 활동을 했습니다"
                    # summary가 있으면 더 상세한 설명 추가
                    if summary:
                        sentence += f". {summary}"  # summary를 명시적으로 추가
                    elif final_content:
                        sentence += f". {final_content}"
                elif summary:
                    sentence = summary  # summary가 있으면 우선 사용
                elif final_content:
                    sentence = final_content
                else:
                    sentence = desc

            elif ev_type == 'Institution':
                # 제도/기관: "제도명은 연도에 설립/운영..."
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
                    # summary가 있으면 더 상세한 설명 추가
                    if summary:
                        sentence += f". {summary}"  # summary를 명시적으로 추가
                    elif final_content:
                        sentence += f". {final_content}"
                elif summary:
                    sentence = summary  # summary가 있으면 우선 사용
                elif final_content:
                    sentence = final_content
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
                    # summary가 있으면 더 상세한 설명 추가
                    if summary:
                        sentence += f". {summary}"  # summary를 명시적으로 추가
                    elif final_content:
                        sentence += f". {final_content}"
                elif summary:
                    sentence = summary  # summary가 있으면 우선 사용
                elif final_content:
                    sentence = final_content
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
                    # summary가 있으면 더 상세한 설명 추가
                    if summary:
                        sentence += f". {summary}"  # summary를 명시적으로 추가
                    elif final_content:
                        sentence += f". {final_content}"
                elif summary:
                    sentence = summary  # summary가 있으면 우선 사용
                elif final_content:
                    sentence = final_content
                else:
                    sentence = desc
            else:
                # 기타
                sentence = final_content if final_content else desc

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
    convergence_nodes = state.get("convergence_nodes", [])  # 수렴 노드

    # 사용자가 선택한 의도 방향
    user_selected_direction = state.get("user_selected_direction")
    expansion_directions = state.get("expansion_directions", [])
    selected_direction_detail = None
    if user_selected_direction and expansion_directions:
        for direction in expansion_directions:
            if direction["direction_id"] == user_selected_direction:
                selected_direction_detail = direction
                break

    # 스트리밍 모드 확인 (state에서 전달)
    stream_mode = state.get("stream_mode", False)
    stream_callback = state.get("stream_callback", None)
    thinking_callback = state.get("thinking_callback", None)
    
    # 🎯 Thinking 이벤트: 답변 생성 시작
    if thinking_callback:
        thinking_callback("answer_generation_started", {
            "title": "답변 생성 시작",
            "evidence_count": len(evidences),
            "query_type": query_type,
            "stream_mode": stream_mode,
            "status": "processing"
        })
    
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0.7,  # 스토리 생성은 창의성 필요
        streaming=stream_mode  # 스트리밍 모드 활성화
    )

    print(f"\n{'='*70}")
    print(f"[Stage 6/6] 스토리 생성 (Story Generator)")
    print(f"{'='*70}")
    if convergence_nodes:
        print(f"  ├─ 수렴 노드: {len(convergence_nodes)}개 (핵심 연결 노드 사용)")

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

        # Input 누적 문제 해결: 필요한 필드만 명시적으로 반환
        return {
            # 필수 입력 (유지)
            "query": query,
            "is_historical": False,
            "query_type": query_type,
            
            # 최종 결과만 반환
            "final_answer": final_answer,
            "answer_with_sources": answer_with_sources,
            
            # 메타 정보
            "executed_nodes": state.get("executed_nodes", []) + ["story_generator"],
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
    if query_type == "deep_analysis":
        instruction = """역사의 이면과 숨은 동기를 분석해 주세요.
- 여러 근거를 종합하여 깊이 있는 해석을 제시합니다
- 당시 정치적/사회적 맥락을 설명합니다
- 다양한 관점에서 분석합니다"""

    else:  # causal
        instruction = """인과관계를 명확히 설명해 주세요.
- 원인과 결과를 논리적으로 연결합니다
- 시간 순서대로 전개합니다
- 각 사건의 영향 관계를 설명합니다"""

    # 중복 제거 (전체 근거)
    print(f"  ├─ 전체 근거: {len(evidences)}개")
    deduplicated_evidences = deduplicate_and_select_top_evidences(evidences, top_k=len(evidences))
    print(f"  ├─ 중복 제거 후: {len(deduplicated_evidences)}개")
    
    # 전체 근거 포맷팅 (중복 제거된 것)
    evidence_list_all, _ = format_evidence_for_prompt(deduplicated_evidences, query)

    # 의도 정보 추가 (초기 의도 + 사용자 선택 방향)
    intent_info = ""
    if query_intent:
        intent_info = f"\n## 질문의 핵심 의도\n{query_intent}"
        if relation_keywords:
            intent_info += f"\n관련 키워드: {', '.join(relation_keywords)}"

    # 사용자가 선택한 구체적 방향 추가
    if selected_direction_detail:
        intent_info += f"\n\n## 사용자가 선택한 답변 방향\n"
        intent_info += f"**{selected_direction_detail['title']}**\n"
        intent_info += f"{selected_direction_detail['description']}\n"
        intent_info += "\n→ 초기 질문에 답하되, 위에서 선택한 방향을 중심으로 답변을 구성하세요.\n"
    elif query_intent:
        intent_info += "\n→ 근거에서 이 의도와 관련된 정보를 우선적으로 사용하세요.\n"

    # 수렴 노드 정보 추가
    convergence_info = ""
    if convergence_nodes:
        convergence_formatted = format_convergence_nodes(convergence_nodes)
        convergence_info = f"\n## 핵심 연결 노드 (수렴 노드)\n다음은 여러 엔티티를 연결하는 중요한 노드들입니다. 이 노드들을 답변에서 명시적으로 언급하고 설명하세요.\n\n{convergence_formatted}\n\n→ 이 수렴 노드들은 여러 인물/사건을 연결하는 중심 역할을 하므로, 답변에서 이들의 역할과 관계를 반드시 설명하세요.\n"

    story_prompt = f"""당신은 조선시대 역사를 전문적으로 설명하는 역사가입니다.
사용자와 자연스럽게 대화하듯 답변하되, 필요한 경우에만 구조화된 마크다운 형식을 사용하세요.

## 질문
{query}

{entity_info_text}
{intent_info}

**중요: 위 질문에 대한 명확하고 직접적인 답변을 반드시 제공하세요.**
## 참고 근거 (전체 {len(deduplicated_evidences)}개)
{evidence_list_all}

## 응답 스타일 가이드

### 기본 원칙
1. **질문에 대한 답을 첫 문장에서 바로 제시**하세요
2. 그 다음 맥락과 배경을 설명하세요
3. 형식보다 가독성과 자연스러움을 우선하세요
4. 언어: 한국어만 사용
   - 반드시 한국어로만 작성하세요. 영어 단어나 영어 문장을 절대 사용하지 마세요.
   - 영어가 필요한 경우에도 한글로 번역하여 작성하세요.
   - 예: "affiliatedWith" → "관련된", "participatesIn" → "참여한"

### 다중 질문 처리 (매우 중요!)
- 질문에 여러 개의 하위 질문이 포함된 경우 (예: "원인과 결과를 알려줘", "A와 B를 설명해줘"), **모든 하위 질문에 대해 각각 답변**하세요.
- 예시: "명성황후 시해사건의 원인과 이로 인해 발발된 사건을 알려줘"
  → 1) 원인을 먼저 설명하고, 2) 그 다음 발발된 사건을 설명하세요.
- 각 하위 질문에 대한 답변을 명확히 구분하여 제공하세요.
- 하나의 질문만 답변하고 나머지를 누락하지 마세요.

### 답변 길이 지시
**중요: 사용자의 질문에 주어진 답변 길이 내에 충분한 답을 제시하세요.**

- **사실 기반 질문**: 핵심 답변 + 배경 설명 (약 400-600자)
- **인과관계 질문**: 원인과 결과를 충분히 설명 (약 600-800자)
- **비교 질문**: 비교 대상의 차이점을 명확히 설명 (약 600-800자)
- **심층 분석 질문**: 다양한 관점과 영향 분석 (약 800-1000자)

**답변 완성도 체크리스트:**
- 질문에 대한 직접적인 답변이 포함되어 있는가?
- 핵심 내용이 모두 설명되었는가?

### 쿼리 타입별 스타일

**[사실 기반 질문]** (예: "~은 언제/누가/무엇인가요?")
- 답을 먼저 말하고, 1-2문단으로 배경 설명
- 글머리 기호 사용 최소화, 서술형으로 작성

**[인과관계 질문]** (예: "~의 원인/결과는?", "왜 ~했나요?")
- 원인과 결과를 명확히 구분하여 설명
- 시간 순서대로 자연스럽게 서술
- 필요시 표, 글머리등을 활용하여 사건의 흐름 파악이 용이하도록 함

**[비교 질문]** (예: "A와 B의 차이는?", "어느 것이 더~?")
- 결론(어느 쪽이 더/차이점)을 먼저 제시
- 비교 대상의 열거 항목이 3개 이상일 때만 표 형식 고려

**[심층 분석 질문]** (예: "~의 의의/영향/평가는?")
- 핵심 평가를 먼저 제시
- 다양한 관점이나 시대별 영향을 문단으로 나눠 서술
- 필요시 소제목(### ) 사용 가능

### 마크다운 사용 규칙
- **굵은 글씨**: 인물명, 사건명, 연도, 핵심 키워드에만 사용
- 글머리 기호(-): 3개 이상 항목을 나열할 때만 사용, 그 외에는 "A, B, C가 있습니다" 형태로
- 소제목(###): 답변이 길어질 때(400자 이상) 가독성을 위해 사용
- 표: 3개 이상 대상의 여러 항목 비교 시에만 사용

### 말투: "-입니다" 체로 작성
   - 반드시 존댓말 "-입니다", "-습니다", "-됩니다" 체로 작성
   - 글머리 기호를 활용하여 내용 나열시에는 간결한 명사형 문장으로 작성

### 피해야 할 것
- 모든 답변을 동일한 구조로 작성하는 것
- 짧은 답변에 불필요한 소제목 넣기
- 한두 개 항목을 글머리 기호로 나열하기
- "핵심 답변", "상세 설명", "요약" 같은 메타 라벨

## 필수 규칙
- 한국어 "-입니다" 체 사용
- 연도, 인물명, 사건명 명시
- 영어/기술 용어/각주 번호 사용 금지
- 되묻지 않고 주어진 근거로 최선의 답변 제공
- **답변을 반드시 완전히 완성하세요**: 중간에 끊기거나 미완성 상태로 끝나지 않도록 주의하세요. 마지막 문장은 완전한 문장으로 자연스럽게 마무리하세요.

## 좋은 응답 예시

**사실 기반 질문 예시:**
> 훈민정음은 **1443년 세종대왕**이 창제하고 **1446년**에 반포하였습니다. 
> 
> 당시 백성들이 한자를 몰라 자신의 뜻을 표현하지 못하는 것을 안타깝게 여긴 세종은 누구나 쉽게 배울 수 있는 문자를 만들고자 했습니다. 집현전 학자들과 함께 연구를 진행하여 자음 17자, 모음 11자로 구성된 28자의 문자 체계를 완성하였습니다.

**인과관계 질문 예시:**
> **임진왜란**이 발발한 가장 직접적인 원인은 **도요토미 히데요시**의 대륙 진출 야욕이었습니다.
>
> 일본 내 전국시대를 통일한 히데요시는 휘하 무사들의 불만을 외부로 돌리고 자신의 권위를 높이기 위해 명나라 정복을 계획했습니다. 조선에 길을 빌려달라는 '정명가도' 요청이 거부되자, **1592년** 20만 대군을 이끌고 조선을 침략하였습니다.
>
> 이 전쟁으로 조선은 국토가 황폐해지고 인구가 급감했으며, 이후 **광해군** 대에 이르러서야 점차 회복되기 시작했습니다.

**비교 질문 예시:**
> **경신환국**과 **기사환국**의 가장 큰 차이는 정권을 잡은 세력입니다. 경신환국에서는 서인이, 기사환국에서는 남인이 집권하였습니다.
>
> **경신환국(1680년)**은 숙종이 남인의 전횡에 불만을 품고 서인을 등용하면서 일어났습니다. 반면 **기사환국(1689년)**은 장희빈 소생의 원자 책봉 문제로 서인이 반대하자 숙종이 서인을 내치고 다시 남인을 등용한 사건입니다. 두 환국 모두 숙종의 왕권 강화 의지가 반영된 것으로 평가됩니다.

**복합 분석 질문 예시 (마크다운 필수):**
> **조선시대 반란의 원인**은 시기별로 다르지만, 핵심적으로는 **권력 다툼과 파벌 갈등**, 지방 관리의 권력 남용과 재정 문제로 인한 민심 이반, 그리고 외부 침략에 대한 방어 동원으로 인한 저항으로 요약됩니다.
>
> 이 맥락은 주어진 자료들에서도 확인됩니다. 예를 들어 **1402년**의 왕지에서 **성석린**에게 영의정부사 겸 판개성유후사사를 제수한 사실은 왕권 강화와 중앙 집권의 흐름을 보여 주며, 이는 파벌 간의 견제와 갈등의 토대를 제공합니다. **정묘호란**이 발발하자 **김장생**의 휘하에서 의병으로 활동하며 군사 및 군량미를 모집한 기록은 외부 침략에 대한 방어 차원에서의 지역 의병 동원을 보여 주고, 이는 외부 위협에 대한 대응이 내부 반란으로 연결될 수 있음을 시사합니다.

**❌ 잘못된 예시 (마크다운 미사용):**
> 반란의 원인은 시기별로 다르지만, 핵심적으로는 권력 다툼과 파벌 갈등으로 요약됩니다. 1402년의 왕지에서 성석린에게 영의정부사를 제수한 사실은...

**✅ 올바른 예시 (마크다운 사용):**
> **반란의 원인**은 시기별로 다르지만, 핵심적으로는 **권력 다툼과 파벌 갈등**으로 요약됩니다. **1402년**의 왕지에서 **성석린**에게 영의정부사를 제수한 사실은...
"""

    try:
        if stream_mode and stream_callback:
            # 스트리밍 모드: 청크 단위로 스트리밍
            llm_answer = ""
            for chunk in llm.stream(story_prompt):
                if hasattr(chunk, 'content') and chunk.content:
                    chunk_text = chunk.content
                    llm_answer += chunk_text
                    # 스트리밍 콜백 호출 (프론트엔드로 전송)
                    if callable(stream_callback):
                        try:
                            stream_callback(chunk_text)
                        except Exception:
                            pass
            
            # 스트리밍 완료 후 최종 응답 생성
            response = type('Response', (), {'content': llm_answer})()
        else:
            # 일반 모드: 전체 응답 한 번에 받기
            response = llm.invoke(story_prompt)
            llm_answer = response.content.strip()
        
        # 토큰 사용량 추출 및 state에 누적 (스트리밍 모드에서는 추정값 사용)
        if not stream_mode:
            from backend.langgraph_fuseki.utils.token_utils import extract_and_accumulate_tokens
            token_update = extract_and_accumulate_tokens(state, response)
            state.update(token_update)

        # LLM이 핵심 답변과 상세 설명을 생성하므로 그대로 사용
        final_answer = llm_answer

        print(f"  └─ 완료: {len(llm_answer)}자 생성 (근거 {len(evidences)}개 사용)")
        print()

        # 근거 포함 답변 구성 (전체 근거 포함)
        answer_with_sources = {
            "story": final_answer,
            "sources": deduplicated_evidences,  # 전체 근거 포함
            "query_type": query_type,
            "evidence_count": len(deduplicated_evidences)  # 근거 개수
        }

    except Exception as e:
        final_answer = f"죄송합니다. 질문 '{query}'에 대한 답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."
        answer_with_sources = {"story": final_answer, "sources": [], "error": str(e)}

    # 노드 실행 시간 기록
    node_elapsed = time.time() - node_start
    node_times = state.get("node_execution_times", {})
    node_times["story_generator"] = node_elapsed

    # Input 누적 문제 해결: 필요한 필드만 명시적으로 반환
    # 이전 노드의 중간 결과는 제외하고 최종 결과만 반환
    return {
        # 필수 입력 (유지)
        "query": query,
        "is_historical": is_historical,
        "query_type": query_type,
        "query_intent": query_intent,
        
        # 최종 결과만 반환 (중간 결과 제외)
        "final_answer": final_answer,
        "answer_with_sources": answer_with_sources,
        
        # 메타 정보
        "executed_nodes": state.get("executed_nodes", []) + ["story_generator"],
        "node_execution_times": node_times,

        # 필요한 경우에만 포함 (선택적)
        "extracted_entities": extracted_entities[:10] if extracted_entities else [],  # 최대 10개만
        "evidences": evidences if evidences else [],  # 전체 evidences 사용
    }
