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
    
    # 모든 그룹이 의미 있는 관계 추출 가능하므로 제외 그룹 없음
    # 적절한 크기의 그룹만 선택 (1개 이상, 100개 이하)
    main_groups = [
        name for name, props in groups.items() 
        if (name in always_include) or (  # 핵심 그룹은 항상 포함
            1 <= len(props) <= 100  # 모든 그룹 포함 (1개 이상)
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
        # 1글자 명사도 포함 (왕, 신, 법 등 중요한 키워드)
        nouns = [t.form for t in tokens if t.tag in ('NNG', 'NNP') and len(t.form) >= 1]
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

    import time
    node_start = time.time()

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
- causal: 인과관계/패턴 ("왜?", "영향은?", "결과는?", "패턴은?")
- deep_analysis: 심화 분석 ("진짜 이유?", "숨은 의도?", "이면에는?")

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

        return json.loads(content)

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

        return json.loads(content)

    # ========== 병렬 실행 ==========
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(analyze_intent_and_properties)
            future2 = executor.submit(expand_keywords)

            result1 = future1.result()
            result2 = future2.result()

        # ========== 결과 병합 ==========
        # Thread 1 결과 (의도 분석 + 프로퍼티 그룹)
        query_type = result1.get("query_type", "causal")
        selected_groups = result1.get("property_groups", [])
        intent = result1.get("intent", "")

        # Thread 2 결과 (키워드 확장)
        expanded_keywords_dict = result2.get("expanded_keywords", {})
        
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
            print(f"📌 확장된 키워드: {expanded_keywords_dict}")

    except Exception as e:
        print(f"⚠️ 질문 분석 실패: {e}")
        # 분석 실패 시 기본값으로 진행 (안전하게)
        query_type = "causal"
        selected_groups = []
        selected_properties = []
        intent = ""
        expanded_keywords = []
        expanded_keywords_dict = {}

    node_elapsed = time.time() - node_start

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
        print(f"  └─ 확장 키워드: {expansion_summary}{'...' if len(expanded_keywords_dict) > 3 else ''} ({node_elapsed:.2f}초)")
    else:
        print(f"  └─ 완료 ({node_elapsed:.2f}초)")
    print()

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["query_classifier"] = node_elapsed

    return {
        **state,
        "is_historical": True,  # 역사 관련 질문임을 명시
        "query_type": query_type,
        "query_intent": intent,
        "selected_property_groups": selected_groups,
        "selected_properties": selected_properties,
        "expanded_keywords": expanded_keywords,  # 확장된 키워드 리스트
        "expanded_keywords_dict": expanded_keywords_dict,  # 원본 매핑 (디버깅용)
        "executed_nodes": state.get("executed_nodes", []) + ["query_classifier"],
        "node_execution_times": node_times
    }
