"""
Query Classifier Node (Stage 1) - 동기 병렬 처리 버전

질문 분류 및 사용자 의도 확인을 위한 노드
- LLM 기반 query_type 분류
- ThreadPoolExecutor를 사용한 동기 병렬 처리
- 비동기 처리 완전 제거
"""

import os
import json
import time
import re
import concurrent.futures
from langchain_openai import ChatOpenAI

from backend.langgraph_fuseki.state import GraphState
from backend.langgraph_fuseki.config import PROPERTY_GROUPS_PATH
from backend.langgraph_fuseki.utils.token_utils import extract_and_accumulate_tokens
from backend.langgraph_fuseki.utils.thinking_events import send_thinking_event, get_stage_info
from backend.langgraph_fuseki.nodes.intent_clarification_templates import (
    generate_expansion_directions,
    generate_clarification_question
)

# 한국어 형태소 분석기
try:
    from kiwipiepy import Kiwi
    _kiwi = Kiwi()
    USE_KIWI = True
except ImportError:
    _kiwi = None
    USE_KIWI = False

# 프로퍼티 그룹 캐시
_PROPERTY_GROUPS = None


def load_property_groups() -> dict:
    """프로퍼티 그룹 로드 (캐싱)"""
    global _PROPERTY_GROUPS
    
    if _PROPERTY_GROUPS is not None:
        return _PROPERTY_GROUPS
    
    if PROPERTY_GROUPS_PATH.exists():
        with open(PROPERTY_GROUPS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _PROPERTY_GROUPS = data.get("groups", {})
    else:
        # 기본 그룹
        _PROPERTY_GROUPS = {
            "건설": ["built", "builtBy", "construct"],
            "설립": ["founded", "establish", "create"],
            "임명": ["appointed", "appointedAs"],
            "폐지": ["abolished", "abolishedBy"],
            "사망": ["death", "died", "killed"],
            "처벌": ["punished", "executed", "exiled"],
            "통치": ["reign", "ruled", "governed"],
            "참여": ["participated", "involved"],
            "원인": ["caused", "causedBy", "leadsTo"],
            "속성": ["has", "contains", "includes"],
        }
    
    return _PROPERTY_GROUPS


def classify_query_type_by_rules(query: str) -> str:
    """규칙 기반 질문 유형 분류 (fallback용)"""
    query_lower = query.lower()
    
    # 인과관계 질문
    causal_keywords = ["왜", "이유", "원인", "결과", "영향", "때문", "인해", "으로 인해", "패턴"]
    if any(kw in query_lower for kw in causal_keywords):
        return "causal"
    
    # 심화 분석 질문
    deep_keywords = ["진짜", "실제", "숨은", "이면", "배경", "의도", "목적"]
    if any(kw in query_lower for kw in deep_keywords):
        return "deep_analysis"
    
    # 비교 질문
    comparative_keywords = ["차이", "비교", "다른", "같은", "유사", "대비"]
    if any(kw in query_lower for kw in comparative_keywords):
        return "comparative"
    
    # 기본값: 사실 질문
    return "factual"


def classify_query_type_with_llm(query: str) -> str:
    """LLM 기반 질문 유형 분류 (동기 방식) - 실패 시 규칙 기반으로 폴백"""
    try:
        # 다른 노드들과 동일한 방식으로 LLM 초기화 (timeout, max_tokens 제거)
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            temperature=0.1
        )
        
        prompt = f"""질문을 4가지 유형 중 하나로 분류: factual, causal, comparative, deep_analysis

질문: {query}

JSON만 응답: {{"query_type": "factual"}}
"""
        
        response = llm.invoke(prompt)
        content = response.content.strip() if response.content else ""
        
        # 응답이 비어있는 경우 즉시 폴백
        if not content:
            print(f"  ⚠️ LLM 응답이 비어있음, 규칙 기반 분류로 폴백")
            return classify_query_type_by_rules(query)
        
        # 1단계: 정규식으로 query_type 값 직접 추출 (가장 빠름)
        match = re.search(r'"query_type"\s*:\s*"(\w+)"', content)
        if match:
            query_type = match.group(1)
        else:
            # 2단계: 코드 블록 제거 후 JSON 파싱
            content_clean = re.sub(r'```json\s*|\s*```', '', content).strip()
            if not content_clean:
                print(f"  ⚠️ LLM 응답 파싱 실패 (빈 응답), 규칙 기반 분류로 폴백")
                return classify_query_type_by_rules(query)
            
            # 중괄호로 시작하는 JSON 객체 찾기 (중첩 중괄호 처리)
            brace_start = content_clean.find('{')
            if brace_start == -1:
                print(f"  ⚠️ LLM 응답에서 JSON 객체를 찾을 수 없음, 규칙 기반 분류로 폴백")
                return classify_query_type_by_rules(query)
            
            # 중괄호 매칭으로 완전한 JSON 객체 추출
            brace_count = 0
            brace_end = -1
            for i in range(brace_start, len(content_clean)):
                if content_clean[i] == '{':
                    brace_count += 1
                elif content_clean[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        brace_end = i + 1
                        break
            
            if brace_end == -1:
                print(f"  ⚠️ LLM 응답에서 완전한 JSON 객체를 찾을 수 없음, 규칙 기반 분류로 폴백")
                return classify_query_type_by_rules(query)
            
            try:
                json_str = content_clean[brace_start:brace_end]
                result = json.loads(json_str)
                query_type = result.get("query_type", "")
                
                if not query_type:
                    print(f"  ⚠️ query_type 필드가 비어있음, 규칙 기반 분류로 폴백")
                    return classify_query_type_by_rules(query)
            except json.JSONDecodeError as e:
                print(f"  ⚠️ JSON 파싱 실패: {e}, 규칙 기반 분류로 폴백")
                return classify_query_type_by_rules(query)
        
        # 4가지 유형 중 하나인지 확인
        valid_types = ["factual", "causal", "comparative", "deep_analysis"]
        if query_type not in valid_types:
            print(f"  ⚠️ 유효하지 않은 query_type: {query_type}, 규칙 기반 분류로 폴백")
            return classify_query_type_by_rules(query)
        
        return query_type
        
    except Exception as e:
        # 모든 예외 발생 시 규칙 기반 분류로 폴백
        print(f"  ⚠️ LLM 분류 중 예외 발생: {type(e).__name__}: {e}")
        print(f"  ⚠️ 규칙 기반 분류로 폴백")
        return classify_query_type_by_rules(query)


def extract_keywords_with_kiwi(query: str) -> list:
    """kiwipiepy로 키워드 추출"""
    if not USE_KIWI or _kiwi is None:
        # fallback: 간단한 한글 단어 추출
        import re
        words = re.findall(r'[가-힣]{2,}', query)
        return [w for w in words if w not in {'무엇', '누구', '어디', '언제', '어떤', '왜'}]
    
    try:
        tokens = _kiwi.tokenize(query)
        keywords = []
        
        for token in tokens:
            if token.tag in ('NNG', 'NNP') and len(token.form) >= 2:
                # 불용어 제거
                if token.form not in {'무엇', '누구', '어디', '언제', '어떤', '왜', '조선', '조선시대'}:
                    keywords.append(token.form)
        
        return keywords
    except Exception as e:
        print(f"키워드 추출 실패: {e}")
        return []




def query_classifier_node(state: GraphState) -> GraphState:
    """
    Stage 1: Query Classifier - 질문 분류 및 사용자 의도 확인 준비
    
    작업:
    1. LLM 기반 질문 분류 (병렬 처리)
    2. 키워드 추출 (kiwipiepy, 병렬 처리)
    3. LLM 기반 확장 방향 생성
    4. 재질문 텍스트 생성
    """
    node_start = time.time()

    query = state.get("query", "")
    thinking_callback = state.get("thinking_callback")
    stage_info = get_stage_info("query_classifier")

    print(f"\n{'='*70}")
    print(f"[Stage 1] Query Classifier")
    print(f"  질문: {query}")

    # Thinking 이벤트: 질문 분석 시작
    send_thinking_event(
        callback=thinking_callback,
        event_type="question_analysis_started",
        title="질문 분석 시작",
        stage_number=stage_info["number"],
        stage_name=stage_info["name"],
        data={"query": query},
        is_pre_clarification=True
    )

    # 1. LLM 기반 분류 + 키워드 추출 (동기 병렬 처리)
    print(f"  LLM 쿼리 타입 분류 및 키워드 추출 중 (ThreadPoolExecutor 사용)...")
    parallel_start = time.time()
    
    try:
        # ThreadPoolExecutor로 병렬 처리 (완전 동기 방식)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_query_type = executor.submit(classify_query_type_with_llm, query)
            future_keywords = executor.submit(extract_keywords_with_kiwi, query)
            
            # 두 작업 결과 수집 (타임아웃 설정)
            query_type_initial = future_query_type.result(timeout=20)
            basic_keywords = future_keywords.result(timeout=20)
    except concurrent.futures.TimeoutError as e:
        print(f"  ⚠️ 병렬 처리 타임아웃, 순차 처리로 대체: {e}")
        # 타임아웃 발생 시 순차 처리로 대체
        query_type_initial = classify_query_type_with_llm(query)
        basic_keywords = extract_keywords_with_kiwi(query)
    except Exception as e:
        print(f"  ⚠️ 병렬 처리 실패 ({type(e).__name__}), 순차 처리로 대체: {e}")
        # 병렬 처리 실패 시 순차 처리로 대체
        query_type_initial = classify_query_type_with_llm(query)
        basic_keywords = extract_keywords_with_kiwi(query)
    
    # 쿼리 타입이 4가지 중 하나인지 확인
    valid_types = ["factual", "causal", "comparative", "deep_analysis"]
    if query_type_initial not in valid_types:
        raise ValueError(f"Invalid query_type: {query_type_initial}. Must be one of {valid_types}")
    
    parallel_elapsed = time.time() - parallel_start
    print(f"  ✓ 병렬 처리 완료 ({parallel_elapsed:.2f}초)")
    print(f"  LLM 기반 분류: {query_type_initial}")
    print(f"  추출된 키워드: {basic_keywords} ({len(basic_keywords)}개)")

    # Thinking 이벤트: 질문 유형 분류 완료
    send_thinking_event(
        callback=thinking_callback,
        event_type="question_type_classified",
        title="질문 유형 분류 완료",
        stage_number=stage_info["number"],
        stage_name=stage_info["name"],
        data={
            "query_type": query_type_initial,
            "classification_method": "LLM 기반"
        },
        is_pre_clarification=True
    )

    # Thinking 이벤트: 키워드 추출 완료
    send_thinking_event(
        callback=thinking_callback,
        event_type="keywords_extracted",
        title="키워드 추출 완료",
        stage_number=stage_info["number"],
        stage_name=stage_info["name"],
        data={
            "keywords": basic_keywords,
            "keyword_count": len(basic_keywords),
            "extraction_method": "kiwipiepy 형태소 분석"
        },
        is_pre_clarification=True
    )

    # Thinking 이벤트: 확장 방향 생성 시작
    send_thinking_event(
        callback=thinking_callback,
        event_type="direction_generation_started",
        title="확장 방향 생성 시작",
        stage_number=stage_info["number"],
        stage_name=stage_info["name"],
        data={
            "input_keywords": basic_keywords[:5],
            "query_type": query_type_initial
        },
        is_pre_clarification=True
    )

    # 3. LLM 기반 확장 방향 생성
    strategy, expansion_directions = generate_expansion_directions(
        query_type=query_type_initial,
        query=query,
        keywords=basic_keywords[:5]
    )

    # Thinking 이벤트: 확장 방향 생성 완료
    direction_titles = [d.get("title", "") for d in expansion_directions]
    send_thinking_event(
        callback=thinking_callback,
        event_type="direction_generation_completed",
        title="확장 방향 생성 완료",
        stage_number=stage_info["number"],
        stage_name=stage_info["name"],
        data={
            "direction_count": len(expansion_directions),
            "directions": direction_titles,
            "generation_method": "LLM 기반 동적 생성"
        },
        is_pre_clarification=True
    )

    # 4. 재질문 텍스트 생성
    clarification_question = generate_clarification_question(
        strategy=strategy,
        directions=expansion_directions,
        query=query,
        use_llm=False
    )

    # Thinking 이벤트: Stage 1 완료
    send_thinking_event(
        callback=thinking_callback,
        event_type="stage1_completed",
        title="Stage 1 완료 - 사용자 선택 대기",
        stage_number=stage_info["number"],
        stage_name=stage_info["name"],
        data={
            "ready_for_user_selection": True,
            "available_directions": len(expansion_directions)
        },
        is_pre_clarification=True
    )

    # 실행 시간 계산
    node_end = time.time()
    execution_time = node_end - node_start
    node_times = state.get("node_execution_times", {})
    node_times["query_classifier"] = execution_time

    print(f"  확장 방향 수: {len(expansion_directions)}")
    print(f"  실행 시간: {execution_time:.2f}초")

    return {
        **state,
        "query_type_initial": query_type_initial,
        "basic_keywords": basic_keywords,
        "needs_clarification": True,
        "expansion_directions": expansion_directions,
        "clarification_question": clarification_question,
        "executed_nodes": state.get("executed_nodes", []) + ["query_classifier"],
        "node_execution_times": node_times
    }
