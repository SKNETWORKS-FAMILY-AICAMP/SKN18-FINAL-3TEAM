"""
Query Classifier Node (Stage 1)

질문 분류 및 사용자 의도 확인을 위한 노드
- 규칙 기반 query_type 분류
- 키워드 추출 (kiwipiepy)
- LLM 기반 확장 방향 생성
- 재질문 텍스트 생성
"""

import os
import json
import time
from langchain_openai import ChatOpenAI

from backend.langgraph_fuseki.state import GraphState
from backend.langgraph_fuseki.config import PROPERTY_GROUPS_PATH
from backend.langgraph_fuseki.utils.token_utils import extract_and_accumulate_tokens
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
    """규칙 기반 질문 유형 분류"""
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
    1. 규칙 기반 질문 분류
    2. 키워드 추출 (kiwipiepy)
    3. LLM 기반 확장 방향 생성
    4. 재질문 텍스트 생성
    """
    node_start = time.time()

    query = state.get("query", "")
    thinking_callback = state.get("thinking_callback")
    
    print(f"\n{'='*70}")
    print(f"[Stage 1] Query Classifier")
    print(f"  질문: {query}")

    # 🎯 Thinking 이벤트: 질문 분석 시작
    if thinking_callback:
        thinking_callback("question_analysis_started", {
            "title": "질문 분석 시작",
            "query": query,
            "stage": "Stage 1: Query Classifier"
        })

    # 1. 규칙 기반 분류
    query_type_initial = classify_query_type_by_rules(query)
    print(f"  규칙 기반 분류: {query_type_initial}")

    # 🎯 Thinking 이벤트: 질문 유형 분류 완료
    if thinking_callback:
        thinking_callback("question_type_classified", {
            "title": "질문 유형 분류 완료",
            "query_type": query_type_initial,
            "classification_method": "규칙 기반"
        })

    # 2. 키워드 추출
    basic_keywords = extract_keywords_with_kiwi(query)
    print(f"  추출된 키워드: {basic_keywords}")

    # 🎯 Thinking 이벤트: 키워드 추출 완료
    if thinking_callback:
        thinking_callback("keywords_extracted", {
            "title": "키워드 추출 완료",
            "keywords": basic_keywords,
            "keyword_count": len(basic_keywords),
            "extraction_method": "kiwipiepy 형태소 분석"
        })

    # 🎯 Thinking 이벤트: 확장 방향 생성 시작
    if thinking_callback:
        thinking_callback("direction_generation_started", {
            "title": "확장 방향 생성 시작",
            "input_keywords": basic_keywords[:5],
            "query_type": query_type_initial
        })

    # 3. LLM 기반 확장 방향 생성
    strategy, expansion_directions = generate_expansion_directions(
        query_type=query_type_initial,
        query=query,
        keywords=basic_keywords[:5]
    )

    # 🎯 Thinking 이벤트: 확장 방향 생성 완료
    if thinking_callback:
        direction_titles = [d.get("title", "") for d in expansion_directions]
        thinking_callback("direction_generation_completed", {
            "title": "확장 방향 생성 완료",
            "direction_count": len(expansion_directions),
            "directions": direction_titles,
            "generation_method": "LLM 기반 동적 생성"
        })

    # 4. 재질문 텍스트 생성
    clarification_question = generate_clarification_question(
        strategy=strategy,
        directions=expansion_directions,
        query=query,
        use_llm=False
    )

    # 🎯 Thinking 이벤트: Stage 1 완료
    if thinking_callback:
        thinking_callback("stage1_completed", {
            "title": "Stage 1 완료 - 사용자 선택 대기",
            "ready_for_user_selection": True,
            "available_directions": len(expansion_directions)
        })

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