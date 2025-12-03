"""
Query Classifier Node

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
from langchain_openai import ChatOpenAI

# 환경변수 로드
sys.path.insert(0, str(Path(__file__).parent.parent))
import __init__  # 환경변수 및 LangSmith 설정 로드

from state import GraphState

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
    
    groups_path = Path(__file__).parent.parent / "ontology" / "instances" / "property_groups.json"
    
    if groups_path.exists():
        with open(groups_path, 'r', encoding='utf-8') as f:
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
    
    # ★ 항상 포함해야 할 핵심 그룹 (인과관계, 시간순서, 연결관계)
    always_include = {"인과관계", "시간순서", "연결관계"}
    
    # 제외할 범용 그룹 (너무 많아서 필터링 비효율적)
    # 주의: "인과관계", "시간순서", "연결관계"는 제외하지 않음
    exclude_groups = {"기타", "속성", "포함", "소속", "위치", "장소", "연도", "날짜", "시기", "시대", "기간중"}
    
    # 명확한 행위/관계 그룹만 선택 (3~100개 사이)
    # 너무 적으면 의미 없고, 너무 많으면 필터링 비효율적
    main_groups = [
        name for name, props in groups.items() 
        if (name in always_include) or (  # 핵심 그룹은 항상 포함
            name not in exclude_groups 
            and 3 <= len(props) <= 100  # 적절한 크기의 그룹만
        )
    ]
    
    return ", ".join(sorted(main_groups))


def extract_keywords_with_kiwi(query: str) -> list:
    """kiwipiepy로 키워드 추출"""
    if not USE_KIWI or _kiwi is None:
        # fallback: 정규식으로 한글 단어 추출
        return re.findall(r'[가-힣]{2,}', query)
    
    try:
        tokens = _kiwi.tokenize(query)
        # 명사만 추출 (NNG: 일반명사, NNP: 고유명사)
        nouns = [t.form for t in tokens if t.tag in ('NNG', 'NNP') and len(t.form) >= 2]
        return nouns
    except Exception as e:
        print(f"⚠️ kiwipiepy 키워드 추출 실패: {e}")
        return re.findall(r'[가-힣]{2,}', query)


def query_classifier_node(state: GraphState) -> GraphState:
    """
    질문 분석 통합 노드 (README 플로우 준수)

    순서:
    1. 의도 파악 (사용자 질문만 사용)
    2. kiwipiepy로 키워드 추출: ["궁궐", "건축", "왕"]
    3. LLM 1회 호출 (추출된 키워드 사용):
       - 프로퍼티 그룹 선택 (의도 기반)
       - 키워드 확장: {"궁궐": ["경복궁", "창덕궁"], "왕": ["태조", "세종"]}
    """

    query = state.get("query", "")

    # LLM 초기화
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0
    )

    # ========== 1단계: 의도 파악 (사용자 질문만 사용) ==========
    # ========== 2단계: kiwipiepy로 키워드 추출 ==========
    keywords = extract_keywords_with_kiwi(query)

    # 불용어 제거
    stopwords = {'무엇', '누구', '어디', '언제', '무슨', '어떤', '것', '수', '등', '때', '중', '후', '전'}
    keywords = [kw for kw in keywords if kw not in stopwords]

    keywords_text = ", ".join(keywords) if keywords else "없음"

    # 프로퍼티 그룹 목록
    group_list = get_group_list()

    # ========== 3단계: LLM 1회 호출 (의도 + 프로퍼티 그룹 + 키워드 확장) ==========
    classification_prompt = f"""당신은 역사 질문을 분석하는 전문가입니다.

## 질문 (의도 파악용)
{query}

## 추출된 키워드 (kiwipiepy) - 키워드 확장용
{keywords_text}

## 분석 항목

### 1. 역사 관련 여부 (is_historical) - 질문만 보고 판단
질문이 **조선시대 한국 역사**와 관련이 있는지 판단하세요.
- true: 조선시대의 인물, 사건, 제도, 정책, 장소 등에 대한 질문
- false: 현대, 다른 나라 역사, 과학, 수학, 일반 상식 등

예시 (false):
- "파이썬 프로그래밍 방법"
- "2024년 대선 결과"
- "태양계 행성 개수"
- "미국의 독립전쟁"

예시 (true):
- "조선의 환국"
- "경복궁을 지은 왕"
- "세종대왕의 업적"

### 2. 질문 유형 (query_type) - is_historical이 true일 때만, 질문만 보고 판단
- causal: 인과관계/패턴 ("왜?", "영향은?", "결과는?", "패턴은?")
- deep_analysis: 심화 분석 ("진짜 이유?", "숨은 의도?", "이면에는?")

### 3. 핵심 의도 (intent) - is_historical이 true일 때만, 질문만 보고 판단
질문의 핵심 의도를 한 문장으로 설명하세요.

예시:
- "궁궐을 지은 왕은?" → "궁궐을 건설한 왕 찾기"
- "을미사변의 원인은?" → "을미사변이 발생한 원인과 배경 분석"

### 4. 관련 프로퍼티 그룹 (property_groups) - is_historical이 true일 때만, 핵심 의도 기반으로 선택
아래 목록에서 질문과 관련된 그룹을 **최대 5개** 선택하세요.

사용 가능한 그룹:
{group_list}

예시:
- "궁궐을 지은 왕" (의도: 궁궐 건설한 왕 찾기) → ["건설", "설립", "통치"]
- "을미사변에서 죽은 사람" (의도: 을미사변 희생자 찾기) → ["사망", "참여", "원인"]
- "세종이 만든 정책" (의도: 세종의 정책 찾기) → ["설립", "창제", "시행"]

### 5. 키워드 확장 (expanded_keywords) - is_historical이 true일 때만, 추출된 키워드 사용
**질문의 맥락을 파악하여** 추출된 키워드와 관련된 구체적인 역사적 인스턴스를 확장하세요.

**확장 규칙:**
- 추출된 키워드 중 일반명사나 추상적 개념이 있으면 구체적인 인스턴스로 확장
- 질문의 의도와 맥락을 고려하여 관련성 높은 인스턴스 선택
- 최대 5-10개의 구체적 인스턴스로 확장

**키워드 확장 예시 (참고용):**
- "궁궐" → ["경복궁", "창덕궁", "경덕궁", "창경궁", "경희궁"]
- "환국" → ["갑술환국", "기사환국", "경신환국", "갑인환국"]
- "왕" → 질문 맥락에 맞는 구체적 왕명 (예: ["태조", "세종", "숙종"])
- "사건" → 질문 맥락에 맞는 구체적 사건명 (예: ["갑자사화", "임진왜란"])
- "정치" → 정치 관련 사건/제도 (예: ["환국", "사화", "당쟁"])
- "제도" → 구체적 제도명 (예: ["의금부", "비변사", "경국대전"])

**중요:** 위 예시는 참고용이며, 실제로는 질문의 맥락에 맞는 키워드만 확장하세요.
확장할 키워드가 없으면 빈 객체를 출력하세요.

## 출력 형식 (JSON만)

is_historical이 true인 경우:
{{
  "is_historical": true,
  "query_type": "causal",
  "intent": "궁궐을 건설한 왕 찾기",
  "property_groups": ["건설", "설립"],
  "expanded_keywords": {{"궁궐": ["경복궁", "창덕궁"], "왕": ["태조", "세종"]}}
}}

is_historical이 false인 경우:
{{
  "is_historical": false
}}
"""

    try:
        response = llm.invoke(classification_prompt)
        content = response.content.strip()
        
        # JSON 파싱
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        result = json.loads(content)
        
        is_historical = result.get("is_historical", True)  # 기본값은 true (안전하게)
        
        # 역사 관련이 아닌 경우 조기 종료
        if not is_historical:
            print(f"⚠️ 역사 관련 질문이 아님 - 조기 종료")
            final_answer = f"""죄송합니다. "{query}"는 조선시대 한국 역사와 관련된 질문이 아닙니다.

이 시스템은 조선시대의 인물, 사건, 제도, 정책, 장소 등에 대한 질문에만 답변할 수 있습니다.

조선시대 역사 관련 질문을 해주시면 도와드리겠습니다."""
            
            return {
                **state,
                "is_historical": False,
                "final_answer": final_answer,
                "answer_with_sources": {
                    "story": final_answer,
                    "sources": [],
                    "query_type": "non_historical",
                    "evidence_count": 0
                },
                "executed_nodes": state.get("executed_nodes", []) + ["query_classifier"]
            }
        
        query_type = result.get("query_type", "causal")
        selected_groups = result.get("property_groups", [])
        intent = result.get("intent", "")
        expanded_keywords_dict = result.get("expanded_keywords", {})
        
        # 검증
        if query_type not in ["causal", "deep_analysis"]:
            query_type = "causal"
        
        # 선택된 그룹에서 실제 프로퍼티 목록 추출
        all_groups = load_property_groups()
        selected_properties = []
        for group_name in selected_groups:
            if group_name in all_groups:
                selected_properties.extend(all_groups[group_name][:10])  # 그룹당 최대 10개
        
        # 키워드 확장 결과 처리
        expanded_keywords = []
        for general_noun, instances in expanded_keywords_dict.items():
            expanded_keywords.extend(instances)
        
        if expanded_keywords:
            print(f"📌 확장된 키워드: {expanded_keywords_dict}")

    except Exception as e:
        print(f"⚠️ 질문 분석 실패: {e}")
        # 분석 실패 시 기본값으로 진행 (안전하게)
        is_historical = True
        query_type = "causal"
        selected_groups = []
        selected_properties = []
        intent = ""
        expanded_keywords = []
        expanded_keywords_dict = {}

    print(f"\n{'='*70}")
    print(f"[1/6] 질문 분석 (Query Classifier)")
    print(f"{'='*70}")
    print(f"  ├─ 질문 유형: {query_type}")
    print(f"  ├─ 핵심 의도: {intent}")
    print(f"  ├─ 추출 키워드: {keywords_text}")
    if selected_groups:
        print(f"  ├─ 프로퍼티 그룹: {', '.join(selected_groups[:3])}{'...' if len(selected_groups) > 3 else ''} ({len(selected_groups)}개)")
    if expanded_keywords:
        # 확장된 키워드를 간결하게 표시 (최대 3개 그룹)
        sample_expansions = list(expanded_keywords_dict.items())[:3]
        expansion_summary = ', '.join([f"{k}→{len(v)}개" for k, v in sample_expansions])
        print(f"  └─ 확장 키워드: {expansion_summary}{'...' if len(expanded_keywords_dict) > 3 else ''}")
    print()

    return {
        **state,
        "is_historical": True,  # 역사 관련 질문임을 명시
        "query_type": query_type,
        "query_intent": intent,
        "selected_property_groups": selected_groups,
        "selected_properties": selected_properties,
        "expanded_keywords": expanded_keywords,  # 확장된 키워드 리스트
        "expanded_keywords_dict": expanded_keywords_dict,  # 원본 매핑 (디버깅용)
        "executed_nodes": state.get("executed_nodes", []) + ["query_classifier"]
    }
