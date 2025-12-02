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
from pathlib import Path
from langchain_openai import ChatOpenAI

# 환경변수 로드
sys.path.insert(0, str(Path(__file__).parent.parent))
import __init__  # 환경변수 및 LangSmith 설정 로드

from state import GraphState

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


def query_classifier_node(state: GraphState) -> GraphState:
    """질문 유형 분류 + 관련 프로퍼티 그룹 선택"""

    query = state.get("query", "")
    
    # 프로퍼티 그룹 목록
    group_list = get_group_list()

    # LLM을 사용한 질문 분석
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0
    )

    # 질문 유형 + 프로퍼티 그룹을 한 번에 분석 (LLM 1회 호출)
    classification_prompt = f"""당신은 역사 질문을 분석하는 전문가입니다.

## 질문
{query}

## 분석 항목

### 1. 질문 유형 (query_type)
- causal: 인과관계/패턴 ("왜?", "영향은?", "결과는?", "패턴은?")
- deep_analysis: 심화 분석 ("진짜 이유?", "숨은 의도?", "이면에는?")

### 2. 관련 프로퍼티 그룹 (property_groups)
아래 목록에서 질문과 관련된 그룹을 **최대 5개** 선택하세요.

사용 가능한 그룹:
{group_list}

예시:
- "궁궐을 지은 왕" → ["건설", "설립", "통치"]
- "을미사변에서 죽은 사람" → ["사망", "참여", "원인"]
- "세종이 만든 정책" → ["설립", "창제", "시행"]

### 3. 핵심 의도 (intent)
질문의 핵심 의도를 한 문장으로 설명하세요.

## 출력 형식 (JSON만)
{{"query_type": "causal", "property_groups": ["건설", "설립"], "intent": "궁궐을 건설한 왕 찾기"}}
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
        
        query_type = result.get("query_type", "causal")
        selected_groups = result.get("property_groups", [])
        intent = result.get("intent", "")
        
        # 검증
        if query_type not in ["causal", "deep_analysis"]:
            query_type = "causal"
        
        # 선택된 그룹에서 실제 프로퍼티 목록 추출
        all_groups = load_property_groups()
        selected_properties = []
        for group_name in selected_groups:
            if group_name in all_groups:
                selected_properties.extend(all_groups[group_name][:10])  # 그룹당 최대 10개

    except Exception as e:
        print(f"⚠️ 질문 분석 실패: {e}")
        query_type = "causal"
        selected_groups = []
        selected_properties = []
        intent = ""

    print(f"📌 질문 유형: {query_type}")
    if selected_groups:
        print(f"📌 관련 그룹: {selected_groups}")
    if selected_properties:
        print(f"📌 검색 프로퍼티: {selected_properties[:10]}...")
    if intent:
        print(f"📌 핵심 의도: {intent}")

    return {
        **state,
        "query_type": query_type,
        "query_intent": intent,
        "selected_property_groups": selected_groups,
        "selected_properties": selected_properties,
        "executed_nodes": state.get("executed_nodes", []) + ["query_classifier"]
    }
