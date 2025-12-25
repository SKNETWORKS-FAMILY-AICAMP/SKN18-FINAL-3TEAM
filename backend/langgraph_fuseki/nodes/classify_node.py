"""
Query Classifier Node

전제 조건: 0단계에서 역사 관련 질문으로 확인된 경우에만 실행

사용자 질문을 분석하여:
1. 질문 유형 분류 (causal/deep_analysis)
2. 관련 프로퍼티 그룹 선택 (TTL 기반)
3. 핵심 의도(관계) 파악

프로퍼티 그룹: property_groups.json에서 로드
"""

import os
import sys
import json
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from langchain_openai import ChatOpenAI

from backend.langgraph_fuseki.state import GraphState
from backend.langgraph_fuseki.config import PROPERTY_GROUPS_PATH
from backend.langgraph_fuseki.utils.token_utils import extract_and_accumulate_tokens
from backend.langgraph_fuseki.nodes.intent_clarification_templates import (
    generate_expansion_directions,
    generate_clarification_question
)

# 한국어 형태소 분석기 (키워드 추출용)
try:
    from kiwipiepy import Kiwi
    _kiwi = Kiwi()
    USE_KIWI = True
except ImportError:
    _kiwi = None
    USE_KIWI = False

# 프로퍼티 그룹 로드 (1회)
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
        # 기본 그룹 (파일 없을 경우)
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


def get_group_list() -> str:
    """LLM에 제공할 그룹 목록 생성 (명확한 행위 그룹만)"""
    groups = load_property_groups()
    
    # ★ 항상 포함해야 할 핵심 그룹 (인과관계, 시기, 연결관계)
    always_include = {"인과관계", "시기", "연결관계"}
    
    # 모든 그룹이 의미 있는 관계 추출 가능하므로 제외 그룹 없음
    # 적절한 크기의 그룹만 선택 (1개 이상, 100개 이하)
    main_groups = [
        name for name, props in groups.items() 
        if (name in always_include) or (  # 핵심 그룹은 항상 포함
            1 <= len(props) <= 100  # 모든 그룹 포함 (1개 이상)
        )
    ]
    
    return ", ".join(sorted(main_groups))


def detect_korean_content(text: str) -> bool:
    """
    텍스트에 한국어가 포함되어 있는지 확인
    
    Args:
        text: 확인할 텍스트
    
    Returns:
        한국어 포함 여부
    """
    # 한글 유니코드 범위: AC00-D7A3
    for char in text:
        if '\uAC00' <= char <= '\uD7A3':
            return True
    return False


def translate_english_query_to_korean(query: str, llm: ChatOpenAI) -> str:
    """
    영어 질문을 한글로 번역 (TTL 데이터에 맞는 단어 선택)
    
    Args:
        query: 영어 질문
        llm: LLM 인스턴스
    
    Returns:
        번역된 한글 질문
    """
    translation_prompt = f"""당신은 조선시대 한국 역사 데이터에 특화된 번역 전문가입니다.

## 영어 질문
{query}

## 번역 규칙 (반드시 준수)

### 1. 역사 데이터에 맞는 전문 용어 사용
- "kill" → "살해" (절대 "살인" 사용 금지)
- "murder" → "살해" 또는 "시해" (맥락에 따라)
- "assassinate" → "시해"
- "timeline" → "연대기"가 아니라 "연대순으로" 또는 "시기별로" 등 자연스러운 표현
- "show me" → "보여주세요"가 아니라 "알려주세요" 또는 "설명해주세요" 등 자연스러운 표현
- "who" → "누가"
- "what" → "무엇" 또는 "어떤"
- "when" → "언제"
- "where" → "어디"
- "why" → "왜"
- "how" → "어떻게"

### 2. 조선시대 역사 데이터에 맞는 어투
- 현대적 표현보다는 역사적 맥락에 맞는 표현 사용
- 예: "Who killed the king?" → "누가 왕을 살해하였나?" (절대 "살인" 사용 금지)
- 예: "Show me the timeline" → "연대순으로 알려주세요" 또는 "시기별로 설명해주세요"
- 예: "What happened in 1592?" → "1592년에 무슨 일이 일어났나?"

### 3. 자연스러운 한국어 표현
- 직역보다는 자연스러운 한국어로 번역
- 질문의 의도와 맥락을 정확히 전달
- 조선시대 역사 데이터에 적합한 어투 사용

## 출력 형식
번역된 한글 질문만 출력하세요. 다른 설명이나 주석은 포함하지 마세요.

번역 결과:"""
    
    try:
        response = llm.invoke(translation_prompt)
        translated = response.content.strip()
        
        # 마크다운 코드 블록 제거
        if "```" in translated:
            translated = translated.split("```")[1]
            if translated.startswith("한국어") or translated.startswith("korean"):
                translated = translated.split("\n", 1)[1] if "\n" in translated else translated
        
        return translated.strip()
    except Exception as e:
        print(f"    번역 실패: {e}")
        return query  # 번역 실패 시 원본 반환


def extract_keywords_with_kiwi(query: str) -> list:
    """kiwipiepy로 키워드 추출"""
    if not USE_KIWI or _kiwi is None:
        # fallback: 정규식으로 한글 단어 추출
        return re.findall(r'[가-힣]{2,}', query)
    
    try:
        tokens = _kiwi.tokenize(query)
        # 명사만 추출 (NNG: 일반명사, NNP: 고유명사)
        # 1글자 명사도 포함 (왕, 신, 법 등 중요한 키워드)
        nouns = [t.form for t in tokens if t.tag in ('NNG', 'NNP') and len(t.form) >= 1]
        return nouns
    except Exception as e:
        print(f"    kiwipiepy 키워드 추출 실패: {e}")
        return re.findall(r'[가-힣]{2,}', query)


def query_classifier_node(state: GraphState) -> GraphState:
    """
    질문 분류 및 키워드 확장 노드 (LLM 기반 상세 분석)
    
    플로우:
    1. LLM으로 질문 분석 및 키워드 확장 (필수)
    2. 프로퍼티 그룹 선택
    3. 확장 방향 생성
    4. 사용자 의도 확인 질문 생성
    
    사용자 재질문 전에 모든 분석을 완료하여 의미 있는 선택지 제공
    """
    
    print("\n" + "=" * 70)
    print("[Stage 1/6] 질문 분류 및 키워드 확장 (Query Classifier)")
    print("=" * 70)
    
    query = state["query"]
    
    # 성능 최적화: 간단한 질문은 빠른 분류 시도
    if len(query) < 20 and any(pattern in query for pattern in ["언제", "누구", "어디"]):
        quick_result = try_quick_classification(query)
        if quick_result:
            print("[INFO] 간단한 질문 - 빠른 분류 사용")
            state.update(quick_result)
            
            # 확장 방향 생성 (간단한 버전)
            classification_strategy, expansion_directions = generate_simple_expansion_directions(
                query, quick_result["query_type"]
            )
            
            # 의도 확인 질문 생성
            clarification_question = generate_clarification_question(
                strategy=classification_strategy,
                directions=expansion_directions,
                query=query
            )
            
            state["classification_strategy"] = classification_strategy
            state["expansion_directions"] = expansion_directions
            state["clarification_question"] = clarification_question
            state["needs_clarification"] = True  # 사용자 선택 필요
            
            return state
    
    # 복잡한 질문: LLM 기반 상세 분석 (기본값)
    print("[INFO] LLM 기반 상세 분석 시작")
    return original_query_classifier_node(state)


def try_quick_classification(query: str) -> dict:
    """
    빠른 규칙 기반 분류 시도
    
    Returns:
        분류 결과 딕셔너리 또는 None (실패 시)
    """
    # 1. 쿼리 타입 분류
    query_type = None
    
    # Factual 패턴
    factual_patterns = ["언제", "시기", "연도", "년도", "몇년", "어느 해"]
    if any(pattern in query for pattern in factual_patterns):
        query_type = "factual"
    
    # Causal 패턴  
    elif any(pattern in query for pattern in ["왜", "이유", "원인", "때문", "배경"]):
        query_type = "causal"
    
    # Comparative 패턴
    elif any(pattern in query for pattern in ["비교", "차이", "다른점", "같은점", "vs"]):
        query_type = "comparative"
    
    # Deep analysis (기본값)
    else:
        query_type = "deep_analysis"
    
    # 2. 기본 키워드 추출
    try:
        keywords = extract_keywords_from_query_simple(query)
    except:
        keywords = query.split()
    
    # 3. 프로퍼티 그룹 선택 (규칙 기반)
    property_groups = select_property_groups_by_type(query_type, keywords)
    
    return {
        "query_type": query_type,
        "query_type_initial": query_type,
        "query_intent": f"{query_type} 관련 질문 분석",
        "expanded_keywords": keywords,
        "expanded_keywords_dict": {kw: [kw] for kw in keywords[:5]},
        "selected_property_groups": property_groups,
        "selected_properties": []
    }


def extract_keywords_from_query_simple(query: str) -> list:
    """간단한 키워드 추출 (형태소 분석기 사용)"""
    if USE_KIWI and _kiwi:
        # 형태소 분석
        tokens = _kiwi.analyze(query)
        keywords = []
        
        for token in tokens[0][0]:
            if token.tag in ['NNG', 'NNP', 'NNB']:  # 명사만
                if len(token.form) > 1:  # 2글자 이상
                    keywords.append(token.form)
        
        return list(set(keywords))[:10]  # 중복 제거, 최대 10개
    else:
        # 간단한 공백 분할
        return [word for word in query.split() if len(word) > 1][:10]


def select_property_groups_by_type(query_type: str, keywords: list) -> list:
    """쿼리 타입별 프로퍼티 그룹 선택"""
    
    # 기본 그룹 매핑
    type_groups = {
        "factual": ["시기", "연도", "기간중", "날짜"],
        "causal": ["인과관계", "배경", "결과", "영향"],
        "comparative": ["비교", "연결관계", "공통점", "차이점"],
        "deep_analysis": ["분석", "의미", "영향", "배경"]
    }
    
    base_groups = type_groups.get(query_type, ["기본정보"])
    
    # 키워드 기반 추가 그룹
    keyword_groups = []
    for keyword in keywords:
        if any(word in keyword for word in ["왕", "임금", "대왕"]):
            keyword_groups.append("통치")
        elif any(word in keyword for word in ["전쟁", "싸움", "전투"]):
            keyword_groups.append("전쟁")
        elif any(word in keyword for word in ["궁궐", "건물", "건축"]):
            keyword_groups.append("건설")
    
    return list(set(base_groups + keyword_groups))[:5]  # 최대 5개


def generate_simple_expansion_directions(query: str, query_type: str) -> tuple:
    """간단한 확장 방향 생성 (LLM 없이)"""
    
    strategy_map = {
        "factual": "time-based",
        "causal": "depth-based", 
        "comparative": "scope-based",
        "deep_analysis": "depth-based"
    }
    
    classification_strategy = strategy_map.get(query_type, "time-based")
    
    # 키워드 기반 확장 방향 생성
    keywords = extract_keywords_with_kiwi(query)
    
    # 질문 유형별 확장 방향
    if query_type == "factual":
        directions = [
            {
                "id": 1,
                "direction_id": "factual_timeline",
                "title": "시간순 정보",
                "description": f"'{' '.join(keywords[:3])}'의 시간순 정보와 연대기",
                "property_groups": ["시기", "연결관계", "속성"]
            },
            {
                "id": 2,
                "direction_id": "factual_details",
                "title": "상세 정보",
                "description": f"'{' '.join(keywords[:3])}'의 구체적 사실과 세부사항",
                "property_groups": ["속성", "연결관계", "참여"]
            }
        ]
    elif query_type == "causal":
        directions = [
            {
                "id": 1,
                "direction_id": "causal_background",
                "title": "배경과 원인",
                "description": f"'{' '.join(keywords[:3])}'의 배경 상황과 근본 원인",
                "property_groups": ["인과관계", "시기", "연결관계"]
            },
            {
                "id": 2,
                "direction_id": "causal_impact",
                "title": "결과와 영향",
                "description": f"'{' '.join(keywords[:3])}'의 결과와 후속 영향",
                "property_groups": ["인과관계", "연결관계", "참여"]
            }
        ]
    else:  # deep_analysis, comparative
        directions = [
            {
                "id": 1,
                "direction_id": "analysis_comprehensive",
                "title": "종합 분석",
                "description": f"'{' '.join(keywords[:3])}'에 대한 다각도 분석",
                "property_groups": ["인과관계", "연결관계", "속성"]
            },
            {
                "id": 2,
                "direction_id": "analysis_context",
                "title": "맥락과 배경",
                "description": f"'{' '.join(keywords[:3])}'의 역사적 맥락과 배경",
                "property_groups": ["시기", "인과관계", "참여"]
            }
        ]
    
    return classification_strategy, directions


# 기존 함수를 백업
def original_query_classifier_node(state: GraphState) -> GraphState:
    """
    질문 분석 통합 노드 (README 플로우 준수)

    순서:
    1. 의도 파악 (사용자 질문만 사용)
    2. kiwipiepy로 키워드 추출: ["궁궐", "건축", "왕"]
    3. LLM 1회 호출 (추출된 키워드 사용):
       - 프로퍼티 그룹 선택 (의도 기반)
       - 키워드 확장: {"궁궐": ["경복궁", "창덕궁"], "왕": ["태조", "세종"]}
    """

    import time
    node_start = time.time()

    query = state.get("query", "")

    # LLM 초기화
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0
    )

    # ========== 0단계: 영어 질문 번역 (가장 먼저 진행) ==========
    original_query = query
    is_english = not detect_korean_content(query)
    
    if is_english:
        # 번역 전에 임시로 response를 받아서 토큰 추출
        translation_prompt = f"""당신은 조선시대 한국 역사 데이터에 특화된 번역 전문가입니다.

## 영어 질문
{query}

## 번역 규칙 (반드시 준수)

### 1. 역사 데이터에 맞는 전문 용어 사용
- "kill" → "살해" (절대 "살인" 사용 금지)
- "murder" → "살해" 또는 "시해" (맥락에 따라)
- "assassinate" → "시해"
- "timeline" → "연대기"가 아니라 "연대순으로" 또는 "시기별로" 등 자연스러운 표현
- "show me" → "보여주세요"가 아니라 "알려주세요" 또는 "설명해주세요" 등 자연스러운 표현
- "who" → "누가"
- "what" → "무엇" 또는 "어떤"
- "when" → "언제"
- "where" → "어디"
- "why" → "왜"
- "how" → "어떻게"

### 2. 조선시대 역사 데이터에 맞는 어투
- 현대적 표현보다는 역사적 맥락에 맞는 표현 사용
- 예: "Who killed the king?" → "누가 왕을 살해하였나?" (절대 "살인" 사용 금지)
- 예: "Show me the timeline" → "연대순으로 알려주세요" 또는 "시기별로 설명해주세요"
- 예: "What happened in 1592?" → "1592년에 무슨 일이 일어났나?"

### 3. 자연스러운 한국어 표현
- 직역보다는 자연스러운 한국어로 번역
- 질문의 의도와 맥락을 정확히 전달
- 조선시대 역사 데이터에 적합한 어투 사용

## 출력 형식
번역된 한글 질문만 출력하세요. 다른 설명이나 주석은 포함하지 마세요.

번역 결과:"""
        response = llm.invoke(translation_prompt)
        # 토큰 사용량 추출 및 state에 누적
        token_update = extract_and_accumulate_tokens(state, response)
        state.update(token_update)
        
        translated_query = response.content.strip()
        # 마크다운 코드 블록 제거
        if "```" in translated_query:
            translated_query = translated_query.split("```")[1]
            if translated_query.startswith("한국어") or translated_query.startswith("korean"):
                translated_query = translated_query.split("\n", 1)[1] if "\n" in translated_query else translated_query
        query = translated_query.strip()
        print(f"\n{'='*70}")
        print(f"[0/6] 질문 번역 (Query Translation)")
        print(f"{'='*70}")
        print(f"  ├─ 원문: {original_query}")
        print(f"  └─ 번역: {query}")
        print()

    # ========== 1단계: 의도 파악 (사용자 질문만 사용) ==========
    # ========== 2단계: kiwipiepy로 키워드 추출 ==========
    keywords = extract_keywords_with_kiwi(query)

    # 불용어 제거
    # 모든 데이터가 조선 데이터이므로 "조선" 관련 키워드는 제외
    stopwords = {
        '무엇', '누구', '어디', '언제', '무슨', '어떤', '것', '수', '등', '때', '중', '후', '전',
        '조선', '조선시대', '조선왕조', '한국', '우리나라'  # 모든 데이터가 조선 데이터이므로 제외
    }
    keywords = [kw for kw in keywords if kw not in stopwords]

    keywords_text = ", ".join(keywords) if keywords else "없음"

    # 프로퍼티 그룹 목록
    group_list = get_group_list()

    # ========== 3단계: LLM 2개 병렬 호출 (시간 단축) ==========
    # Thread 1: 의도 분석 + 프로퍼티 그룹 선택
    def analyze_intent_and_properties():
        """의도 분석 + 프로퍼티 그룹 선택 (병렬 실행 Thread 1)"""
        intent_prompt = f"""당신은 역사 질문을 분석하는 전문가입니다.

## 질문
{query}

## 분석 항목

### 1. 질문 유형 (query_type)

**causal (인과관계)**: 직접적인 원인-결과 관계를 묻는 질문
- 특징: 사실 기반, 시간순서, 객관적 설명
- 키워드: "원인은?", "결과는?", "영향은?", "발생한 사건은?", "이로 인해", "왜?"
- 예시:
  - "명성황후 시해사건의 원인과 이로 인해 발발된 사건을 알려줘" → causal
  - "임진왜란이 조선에 미친 영향은?" → causal
  - "을미사변의 원인은?" → causal
  - "갑술환국이 발생한 배경은?" → causal

**deep_analysis (심화 분석)**: 숨은 동기, 이면의 의도, 심층적 배경을 묻는 질문
- 특징: 해석적, 분석적, 주관적 관점 포함
- 키워드: "진짜 이유는?", "숨은 의도는?", "이면에는?", "배경은?", "왜 그랬을까?", "실제 목적은?"
- 예시:
  - "을미사변의 진짜 이유는 무엇인가?" → deep_analysis
  - "갑술환국 이면의 숨은 의도는?" → deep_analysis
  - "명성황후 시해의 배경과 진실은?" → deep_analysis
  - "당쟁의 실제 목적은 무엇이었나?" → deep_analysis

**구분 기준**:
- causal: "무엇이 원인인가?" (사실, 객관적)
- deep_analysis: "왜 그랬을까?" (동기, 의도, 해석)

### 2. 핵심 의도 (intent)
질문의 핵심 의도를 한 문장으로 설명하세요.

예시:
- "궁궐을 지은 왕은?" → "궁궐을 건설한 왕 찾기"
- "을미사변의 원인은?" → "을미사변이 발생한 원인과 배경 분석"

### 3. 관련 프로퍼티 그룹 (property_groups)
아래 목록에서 질문과 관련된 그룹을 **최대 5개** 선택하세요.

사용 가능한 그룹:
{group_list}

예시:
- "궁궐을 지은 왕" → ["건설", "설립", "통치"]
- "을미사변에서 죽은 사람" → ["사망", "참여", "원인"]
- "세종이 만든 정책" → ["설립", "창제", "시행"]

## 출력 형식 (JSON만)
{{
  "query_type": "causal",
  "intent": "궁궐을 건설한 왕 찾기",
  "property_groups": ["건설", "설립", "통치"]
}}
"""
        response = llm.invoke(intent_prompt)
        content = response.content.strip()

        # JSON 파싱
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        return response, json.loads(content)  # response도 함께 반환

    # Thread 2: 키워드 확장
    def expand_keywords():
        """키워드 확장 (병렬 실행 Thread 2)"""
        expansion_prompt = f"""당신은 역사 키워드를 확장하는 전문가입니다.

## 질문
{query}

## 추출된 키워드 (kiwipiepy)
{keywords_text}

## 작업
**질문의 맥락을 파악하여** 추출된 키워드와 관련된 구체적인 역사적 인스턴스를 확장하세요.

**확장 규칙:**
- 추출된 키워드 중 일반명사나 추상적 개념이 있으면 구체적인 인스턴스로 확장
- 질문의 의도와 맥락을 고려하여 관련성 높은 인스턴스 선택
- 최대 5-10개의 구체적 인스턴스로 확장
- 집합 개념의 경우, 관련 인물과 사건을 모두 포함
- **중요: "조선", "조선시대", "조선왕조"는 확장하지 마세요. 모든 데이터가 조선 데이터이므로 의미가 없습니다.**

**키워드 확장 예시 (참고용):**
- "궁궐" → ["경복궁", "창덕궁", "경덕궁", "창경궁", "경희궁"]
- "환국" → ["갑술환국", "기사환국", "경신환국", "갑인환국"]
- "남인" → ["윤선도", "채제공", "기사환국", "남인 집권", "남인 분열"]
- "서인" → ["송시열", "이이", "갑술환국", "서인 재집권", "1575년 동인과 서인으로 분열"]
- "왕" → 질문 맥락에 맞는 구체적 왕명 (예: ["태조", "세종", "숙종"])
- "사건" → 질문 맥락에 맞는 구체적 사건명 (예: ["갑자사화", "임진왜란"])
- "정치" → 정치 관련 사건/제도 (예: ["환국", "사화", "당쟁"])
- "제도" → 구체적 제도명 (예: ["의금부", "비변사", "경국대전"])

**중요:** 
- 위 예시는 참고용이며, 실제로는 질문의 맥락에 맞는 키워드만 확장하세요.
- "연관", "주요" 같은 추상적 단어는 확장하지 마세요.예시이며, 실제로는 질문의 맥락에 맞는 키워드만 확장하세요.
확장할 키워드가 없으면 빈 객체를 출력하세요.

## 출력 형식 (JSON만)
{{
  "expanded_keywords": {{"궁궐": ["경복궁", "창덕궁"], "왕": ["태조", "세종"]}}
}}

또는 확장 없는 경우:
{{
  "expanded_keywords": {{}}
}}
"""
        response = llm.invoke(expansion_prompt)
        content = response.content.strip()

        # JSON 파싱
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        return response, json.loads(content)  # response도 함께 반환

    # ========== 병렬 실행 ==========
    executor = None
    try:
        executor = ThreadPoolExecutor(max_workers=2)
        future1 = executor.submit(analyze_intent_and_properties)
        future2 = executor.submit(expand_keywords)

        response1, result1 = future1.result()
        response2, result2 = future2.result()

        # 토큰 사용량 추출 및 state에 누적
        token_update1 = extract_and_accumulate_tokens(state, response1)
        token_update2 = extract_and_accumulate_tokens(state, response2)
        # 두 응답의 토큰을 합산
        state.update({
            "total_tokens": token_update1["total_tokens"] + token_update2["total_tokens"],
            "prompt_tokens": token_update1["prompt_tokens"] + token_update2["prompt_tokens"],
            "completion_tokens": token_update1["completion_tokens"] + token_update2["completion_tokens"]
        })

        # ========== 결과 병합 ==========
        # Thread 1 결과 (의도 분석 + 프로퍼티 그룹)
        query_type = result1.get("query_type", "causal")
        selected_groups = result1.get("property_groups", [])
        intent = result1.get("intent", "")

        # Thread 2 결과 (키워드 확장)
        expanded_keywords_dict = result2.get("expanded_keywords", {})

        # 검증 (Phase 1: 4가지 유형 지원)
        valid_types = ["causal", "factual", "deep_analysis", "comparative"]
        if query_type not in valid_types:
            query_type = "causal"  # fallback

        # 선택된 그룹에서 실제 프로퍼티 목록 추출
        all_groups = load_property_groups()
        selected_properties = []
        for group_name in selected_groups:
            if group_name in all_groups:
                selected_properties.extend(all_groups[group_name][:10])  # 그룹당 최대 10개

        # 키워드 확장 결과 처리
        # "조선" 관련 키워드는 제외 (모든 데이터가 조선 데이터이므로)
        joseon_keywords = {'조선', '조선시대', '조선왕조', '한국', '우리나라'}
        expanded_keywords = []
        filtered_expanded_keywords_dict = {}

        for general_noun, instances in expanded_keywords_dict.items():
            # "조선" 관련 키워드는 확장하지 않음
            if general_noun not in joseon_keywords:
                # 확장된 인스턴스에서도 "조선" 관련 항목 제거
                filtered_instances = [inst for inst in instances if inst not in joseon_keywords]
                if filtered_instances:
                    filtered_expanded_keywords_dict[general_noun] = filtered_instances
                    expanded_keywords.extend(filtered_instances)

        # 필터링된 결과로 업데이트
        expanded_keywords_dict = filtered_expanded_keywords_dict

        if expanded_keywords:
            print(f"    확장된 키워드: {expanded_keywords_dict}")

    except Exception as e:
        print(f"    질문 분석 실패: {e}")
        # 분석 실패 시 기본값으로 진행 (안전하게)
        query_type = "causal"
        selected_groups = []
        selected_properties = []
        intent = ""
        expanded_keywords = []
        expanded_keywords_dict = {}
    finally:
        # ThreadPoolExecutor 명시적 종료
        if executor is not None:
            executor.shutdown(wait=True)

    # ========== Phase 1: 의도 확인 방향 생성 (고정 매핑) ==========
    # 질문 유형에 따라 확장 방향 생성
    classification_strategy, expansion_directions = generate_expansion_directions(
        query_type=query_type,
        query=query,
        keywords=expanded_keywords[:5] if expanded_keywords else []  # 상위 5개 키워드만 전달
    )

    # 사용자 질문 텍스트 생성
    clarification_question = generate_clarification_question(
        strategy=classification_strategy,
        directions=expansion_directions,
        query=query
    )

    node_elapsed = time.time() - node_start

    print(f"\n{'='*70}")
    print(f"[Stage 1/6] 질문 분석 (Query Classifier)")
    print(f"{'='*70}")
    print(f"  ├─ 질문 유형: {query_type} (초기)")
    print(f"  ├─ 분류 전략: {classification_strategy}")
    print(f"  ├─ 핵심 의도: {intent}")
    print(f"  ├─ 추출 키워드: {keywords_text}")
    if selected_groups:
        print(f"  ├─ 프로퍼티 그룹: {', '.join(selected_groups[:3])}{'...' if len(selected_groups) > 3 else ''} ({len(selected_groups)}개)")
    if expanded_keywords:
        # 확장된 키워드를 간결하게 표시 (최대 3개 그룹)
        sample_expansions = list(expanded_keywords_dict.items())[:3]
        expansion_summary = ', '.join([f"{k}→{len(v)}개" for k, v in sample_expansions])
        print(f"  ├─ 확장 키워드: {expansion_summary}{'...' if len(expanded_keywords_dict) > 3 else ''}")
    print(f"  └─ 사용자 선택 방향: {len(expansion_directions)}개 생성 ({node_elapsed:.2f}초)")
    print()

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["query_classifier"] = node_elapsed

    # 번역된 query를 state에 반영
    updated_state = {
        **state,
        "is_historical": True,  # 역사 관련 질문임을 명시
        "query_type_initial": query_type,  # 초기 예측 (사용자 선택 후 변경될 수 있음)
        "query_intent": intent,
        "selected_property_groups": selected_groups,
        "selected_properties": selected_properties,
        "expanded_keywords": expanded_keywords,  # 확장된 키워드 리스트
        "expanded_keywords_dict": expanded_keywords_dict,  # 원본 매핑 (디버깅용)

        # Phase 1: 의도 확인 관련 필드
        "needs_clarification": True,  # 사용자 선택 필요
        "classification_strategy": classification_strategy,
        "expansion_directions": expansion_directions,
        "clarification_question": clarification_question,

        "executed_nodes": state.get("executed_nodes", []) + ["query_classifier"],
        "node_execution_times": node_times
    }
    
    # 영어 질문이 번역된 경우, 번역된 query를 state에 반영
    if is_english and query != original_query:
        updated_state["query"] = query
        updated_state["original_query"] = original_query

    return updated_state


# ============================================================
# 3단계 파이프라인 전략: Stage 1 분할
# ============================================================

def classify_query_type_by_rules(query: str) -> str:
    """
    규칙 기반 query_type 분류 (Stage 1-A용, 0.01초)

    LLM 없이 키워드 패턴으로 빠르게 분류
    정확도는 낮지만 재질문 표시용으로 충분

    Returns:
        "causal" | "factual" | "deep_analysis" | "comparative"
    """
    query_lower = query.lower()

    # 1. Factual (사실 기반) 패턴
    factual_keywords = [
        "언제", "시기", "연도", "년도", "몇년", "어느 해", "날짜",
        "누구", "무엇", "어디", "어느"
    ]
    if any(kw in query for kw in factual_keywords):
        return "factual"

    # 2. Comparative (비교) 패턴
    comparative_keywords = [
        "비교", "차이", "다른점", "같은점", "공통점", "vs", "대비",
        "어떻게 다른", "어떻게 같은"
    ]
    if any(kw in query for kw in comparative_keywords):
        return "comparative"

    # 3. Deep Analysis (심층 분석) 패턴
    deep_keywords = [
        "진짜", "실제", "숨은", "이면", "배경", "동기", "의도",
        "왜 그랬", "목적", "본질", "해석", "분석"
    ]
    if any(kw in query for kw in deep_keywords):
        return "deep_analysis"

    # 4. Causal (인과관계) 패턴 - 기본값
    causal_keywords = [
        "왜", "이유", "원인", "때문", "결과", "영향", "발생", "일어난"
    ]
    if any(kw in query for kw in causal_keywords):
        return "causal"

    # 5. 기본값 (분류 불가)
    return "causal"  # 가장 일반적인 유형


def generate_fixed_expansion_directions(query_type: str, keywords: list) -> tuple:
    """
    고정 매핑으로 확장 방향 생성 (Stage 1-A용, 0.1초)

    LLM 없이 query_type과 키워드로 확장 방향 생성

    Returns:
        (classification_strategy: str, expansion_directions: list)
    """
    # 전략 매핑
    strategy_map = {
        "factual": "time-based",
        "causal": "depth-based",
        "comparative": "scope-based",
        "deep_analysis": "depth-based"
    }
    classification_strategy = strategy_map.get(query_type, "time-based")

    # 키워드 샘플 (최대 3개)
    keyword_sample = " ".join(keywords[:3]) if keywords else "관련 내용"

    # 질문 유형별 확장 방향 (고정 템플릿)
    if query_type == "factual":
        directions = [
            {
                "id": 1,
                "direction_id": "factual_timeline",
                "title": "시간순 정보",
                "description": f"'{keyword_sample}'의 시간순 정보와 연대기",
                "property_groups": ["시기", "연결관계", "속성"]
            },
            {
                "id": 2,
                "direction_id": "factual_details",
                "title": "상세 정보",
                "description": f"'{keyword_sample}'의 구체적 사실과 세부사항",
                "property_groups": ["속성", "연결관계", "참여"]
            }
        ]

    elif query_type == "causal":
        directions = [
            {
                "id": 1,
                "direction_id": "causal_background",
                "title": "배경과 원인",
                "description": f"'{keyword_sample}'의 배경 상황과 근본 원인",
                "property_groups": ["인과관계", "시기", "연결관계"]
            },
            {
                "id": 2,
                "direction_id": "causal_impact",
                "title": "결과와 영향",
                "description": f"'{keyword_sample}'의 결과와 후속 영향",
                "property_groups": ["인과관계", "연결관계", "참여"]
            }
        ]

    elif query_type == "comparative":
        directions = [
            {
                "id": 1,
                "direction_id": "comparative_similarities",
                "title": "공통점 분석",
                "description": f"'{keyword_sample}'의 공통점과 유사성",
                "property_groups": ["연결관계", "속성", "시기"]
            },
            {
                "id": 2,
                "direction_id": "comparative_differences",
                "title": "차이점 분석",
                "description": f"'{keyword_sample}'의 차이점과 대조",
                "property_groups": ["연결관계", "인과관계", "속성"]
            }
        ]

    else:  # deep_analysis
        directions = [
            {
                "id": 1,
                "direction_id": "analysis_comprehensive",
                "title": "종합 분석",
                "description": f"'{keyword_sample}'에 대한 다각도 분석",
                "property_groups": ["인과관계", "연결관계", "속성"]
            },
            {
                "id": 2,
                "direction_id": "analysis_context",
                "title": "맥락과 배경",
                "description": f"'{keyword_sample}'의 역사적 맥락과 배경",
                "property_groups": ["시기", "인과관계", "참여"]
            }
        ]

    return classification_strategy, directions


def query_classifier_stage1a_node(state: GraphState) -> GraphState:
    """
    Stage 1-A: 재질문에 필요한 최소 데이터만 생성 (0.2초)

    LLM 호출 없이 규칙 기반으로 빠르게 처리:
    1. 규칙 기반 query_type 분류 (~0.01초)
    2. 키워드 추출 (kiwipiepy, ~0.05초)
    3. 고정 매핑 확장 방향 생성 (~0.1초)
    4. 질문 텍스트 생성 (~0.04초)

    총 0.2초 내 완료 → 즉시 사용자 재질문 표시
    """
    import time
    node_start = time.time()

    print("\n" + "=" * 70)
    print("[Stage 1-A] 초고속 재질문 준비 (0.2초 목표)")
    print("=" * 70)

    query = state.get("query", "")

    # 1. 규칙 기반 query_type 분류
    query_type_initial = classify_query_type_by_rules(query)
    print(f"  ├─ [1/4] 규칙 기반 분류: {query_type_initial}")

    # 2. 키워드 추출 (kiwipiepy)
    basic_keywords = extract_keywords_with_kiwi(query)

    # 불용어 제거
    stopwords = {
        '무엇', '누구', '어디', '언제', '무슨', '어떤', '것', '수', '등', '때', '중', '후', '전',
        '조선', '조선시대', '조선왕조', '한국', '우리나라'
    }
    basic_keywords = [kw for kw in basic_keywords if kw not in stopwords]
    print(f"  ├─ [2/4] 키워드 추출: {basic_keywords[:5]}")

    # 3. 고정 매핑 방향 생성
    classification_strategy, expansion_directions = generate_fixed_expansion_directions(
        query_type=query_type_initial,
        keywords=basic_keywords[:5]
    )
    print(f"  ├─ [3/4] 확장 방향: {len(expansion_directions)}개 생성")

    # 4. 질문 텍스트 생성
    clarification_question = generate_clarification_question(
        strategy=classification_strategy,
        directions=expansion_directions,
        query=query
    )
    print(f"  └─ [4/4] 재질문 준비 완료")

    node_elapsed = time.time() - node_start

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["query_classifier_stage1a"] = node_elapsed

    print(f"\n[Stage 1-A] 완료 ({node_elapsed:.2f}초) - 사용자 재질문 표시 가능")
    print("=" * 70)

    return {
        **state,
        "query_type_initial": query_type_initial,  # 초기 분류 (백그라운드에서 정밀 분석)
        "classification_strategy": classification_strategy,
        "expansion_directions": expansion_directions,
        "clarification_question": clarification_question,
        "needs_clarification": True,
        "basic_keywords": basic_keywords[:10],  # 백그라운드 작업에 사용
        "node_execution_times": node_times,
        "executed_nodes": state.get("executed_nodes", []) + ["query_classifier_stage1a"]
    }


def query_classifier_stage1b_background(state: GraphState) -> dict:
    """
    Stage 1-B: 백그라운드 상세 분석 (LLM 2회 병렬)

    사용자 선택 중 백그라운드에서 실행:
    1. LLM으로 정밀 query_type 분류
    2. LLM으로 키워드 확장
    3. 프로퍼티 그룹 선택

    Returns:
        백그라운드 결과 딕셔너리
    """
    import time
    start_time = time.time()

    print("  ├─ [BACKGROUND] Stage 1-B 상세 분석 시작...")

    query = state.get("query", "")
    basic_keywords = state.get("basic_keywords", [])

    # LLM 초기화
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0
    )

    # 프로퍼티 그룹 목록
    group_list = get_group_list()
    keywords_text = ", ".join(basic_keywords) if basic_keywords else "없음"

    # Thread 1: 의도 분석 + 프로퍼티 그룹 선택
    def analyze_intent_and_properties():
        intent_prompt = f"""당신은 역사 질문을 분석하는 전문가입니다.

## 질문
{query}

## 분석 항목

### 1. 질문 유형 (query_type)

**causal (인과관계)**: 직접적인 원인-결과 관계를 묻는 질문
- 특징: 사실 기반, 시간순서, 객관적 설명
- 키워드: "원인은?", "결과는?", "영향은?", "발생한 사건은?", "이로 인해", "왜?"

**deep_analysis (심화 분석)**: 숨은 동기, 이면의 의도, 심층적 배경을 묻는 질문
- 특징: 해석적, 분석적, 주관적 관점 포함
- 키워드: "진짜 이유는?", "숨은 의도는?", "이면에는?", "배경은?"

**factual (사실 기반)**: 객관적 사실을 묻는 질문
- 특징: 시간, 장소, 인물 등 구체적 정보
- 키워드: "언제", "누구", "어디", "무엇"

**comparative (비교)**: 두 대상을 비교하는 질문
- 특징: 차이점, 공통점, 대조
- 키워드: "비교", "차이", "같은점", "다른점"

### 2. 핵심 의도 (intent)
질문의 핵심 의도를 한 문장으로 설명하세요.

### 3. 관련 프로퍼티 그룹 (property_groups)
아래 목록에서 질문과 관련된 그룹을 **최대 5개** 선택하세요.

사용 가능한 그룹:
{group_list}

## 출력 형식 (JSON만)
{{
  "query_type": "causal",
  "intent": "궁궐을 건설한 왕 찾기",
  "property_groups": ["건설", "설립", "통치"]
}}
"""
        response = llm.invoke(intent_prompt)
        content = response.content.strip()

        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        return response, json.loads(content)

    # Thread 2: 키워드 확장
    def expand_keywords():
        expansion_prompt = f"""당신은 역사 키워드를 확장하는 전문가입니다.

## 질문
{query}

## 추출된 키워드
{keywords_text}

## 작업
질문의 맥락을 파악하여 추출된 키워드와 관련된 구체적인 역사적 인스턴스를 확장하세요.

**확장 규칙:**
- 일반명사나 추상적 개념을 구체적인 인스턴스로 확장
- 질문의 의도와 맥락을 고려하여 관련성 높은 인스턴스 선택
- 최대 5-10개의 구체적 인스턴스로 확장
- "조선", "조선시대"는 확장하지 마세요 (모든 데이터가 조선 데이터)

**예시:**
- "궁궐" → ["경복궁", "창덕궁", "경덕궁", "창경궁"]
- "환국" → ["갑술환국", "기사환국", "경신환국"]
- "왕" → 질문 맥락에 맞는 구체적 왕명 (예: ["태조", "세종", "숙종"])

## 출력 형식 (JSON만)
{{
  "expanded_keywords": {{"궁궐": ["경복궁", "창덕궁"], "왕": ["태조", "세종"]}}
}}
"""
        response = llm.invoke(expansion_prompt)
        content = response.content.strip()

        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        return response, json.loads(content)

    # 병렬 실행
    executor = None
    try:
        executor = ThreadPoolExecutor(max_workers=2)
        future1 = executor.submit(analyze_intent_and_properties)
        future2 = executor.submit(expand_keywords)

        response1, result1 = future1.result()
        response2, result2 = future2.result()

        # 결과 추출
        query_type = result1.get("query_type", "causal")
        intent = result1.get("intent", "")
        selected_groups = result1.get("property_groups", [])
        expanded_keywords_dict = result2.get("expanded_keywords", {})

        # 선택된 그룹에서 프로퍼티 추출
        all_groups = load_property_groups()
        selected_properties = []
        for group_name in selected_groups:
            if group_name in all_groups:
                selected_properties.extend(all_groups[group_name][:10])

        # 조선 키워드 필터링
        joseon_keywords = {'조선', '조선시대', '조선왕조', '한국', '우리나라'}
        filtered_expanded_keywords_dict = {}
        expanded_keywords = []

        for general_noun, instances in expanded_keywords_dict.items():
            if general_noun not in joseon_keywords:
                filtered_instances = [inst for inst in instances if inst not in joseon_keywords]
                if filtered_instances:
                    filtered_expanded_keywords_dict[general_noun] = filtered_instances
                    expanded_keywords.extend(filtered_instances)

        elapsed = time.time() - start_time
        print(f"  ├─ [BACKGROUND] Stage 1-B 완료: query_type={query_type} ({elapsed:.2f}초)")

        return {
            "status": "success",
            "query_type": query_type,  # 정밀 분류 결과
            "query_intent": intent,
            "selected_property_groups": selected_groups,
            "selected_properties": selected_properties,
            "expanded_keywords_dict": filtered_expanded_keywords_dict,
            "expanded_keywords": expanded_keywords,
            "processing_time": elapsed,
            "token_responses": [response1, response2]  # 토큰 추출용
        }

    except Exception as e:
        print(f"  ├─ [BACKGROUND] Stage 1-B 실패: {e}")
        return {"status": "error", "error": str(e)}

    finally:
        if executor is not None:
            executor.shutdown(wait=True)
