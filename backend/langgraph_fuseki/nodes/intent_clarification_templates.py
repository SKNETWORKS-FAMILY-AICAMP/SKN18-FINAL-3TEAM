"""
대화형 의도 확인 시스템 - 템플릿 및 전략 매핑

쿼리 타입에 따라 기본 전략을 선택하고,
LLM이 질문을 분석하여 동적으로 적절한 방향 설명을 생성합니다.
property_groups.json에서 사용 가능한 그룹만 선택하도록 제약합니다.
"""

from typing import Dict, List, Any
import os
import json
from langchain_openai import ChatOpenAI

from backend.langgraph_fuseki.config import PROPERTY_GROUPS_PATH


# ========== Property Groups 로드 ==========

# 캐싱용 변수
_AVAILABLE_PROPERTY_GROUPS = None


def load_available_property_groups() -> List[str]:
    """property_groups.json에서 사용 가능한 그룹 목록 로드 (캐싱)"""
    global _AVAILABLE_PROPERTY_GROUPS
    
    if _AVAILABLE_PROPERTY_GROUPS is not None:
        return _AVAILABLE_PROPERTY_GROUPS
    
    try:
        if PROPERTY_GROUPS_PATH.exists():
            with open(PROPERTY_GROUPS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _AVAILABLE_PROPERTY_GROUPS = list(data.get("groups", {}).keys())
                print(f"[intent_clarification] 사용 가능한 프로퍼티 그룹: {len(_AVAILABLE_PROPERTY_GROUPS)}개")
        else:
            print(f"[intent_clarification] property_groups.json 없음, 기본 그룹 사용")
            _AVAILABLE_PROPERTY_GROUPS = [
                "속성", "문서", "연결관계", "연도", "소속", "인과관계", "장소",
                "참여", "부분", "포함", "직위", "기간중", "시기", "재위",
                "법률", "시행", "지휘", "변경", "역할", "조사", "위치",
                "세금", "협력", "저술", "시대", "반대", "설립", "날짜",
                "복원", "승진", "외교", "교육"
            ]
    except Exception as e:
        print(f"[intent_clarification] property_groups.json 로드 실패: {e}")
        _AVAILABLE_PROPERTY_GROUPS = ["속성", "인과관계", "참여", "변경"]
    
    return _AVAILABLE_PROPERTY_GROUPS


def validate_property_groups(directions: List[Dict], available_groups: List[str]) -> List[Dict]:
    """
    LLM이 생성한 property_groups를 검증하고 유효한 것만 유지
    
    Args:
        directions: LLM이 생성한 방향 리스트
        available_groups: 사용 가능한 그룹 목록
    
    Returns:
        검증된 방향 리스트
    """
    for direction in directions:
        original_groups = direction.get("property_groups", [])
        valid_groups = [g for g in original_groups if g in available_groups]
        
        if not valid_groups:
            # 유효한 그룹이 없으면 기본값 사용
            valid_groups = ["속성", "인과관계"]
            print(f"[intent_clarification] 유효하지 않은 그룹 '{original_groups}' → 기본값 사용")
        elif len(valid_groups) < len(original_groups):
            removed = set(original_groups) - set(valid_groups)
            print(f"[intent_clarification] 유효하지 않은 그룹 제거: {removed}")
        
        direction["property_groups"] = valid_groups
    
    return directions


# ========== LLM 기반 방향 생성 ==========

def generate_llm_based_directions(
    query: str,
    keywords: List[str],
    query_type: str = None
) -> List[Dict[str, Any]]:
    """
    LLM을 사용하여 질문에 최적화된 확장 방향을 생성
    property_groups.json에서 사용 가능한 그룹만 선택하도록 제약

    Args:
        query: 사용자 질문
        keywords: 추출된 키워드
        query_type: 질문 유형 (참고용, 필수 아님)

    Returns:
        방향 리스트 (2-4개, 검증된 property_groups 포함)
    """
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0.3
    )
    
    # 사용 가능한 프로퍼티 그룹 로드
    available_groups = load_available_property_groups()
    groups_list = ', '.join(available_groups)

    # 전략 설명 (사용 가능한 그룹 포함)
    strategy_descriptions = f"""
**사용 가능한 분석 차원:**
1. **시간축**: 원인(이전), 직후 결과, 장기 영향
2. **클래스**: 인물 중심, 사건 중심, 제도 중심
3. **범위**: 개인적, 제도적, 국가적, 국제적 영향
4. **깊이**: 기본 정보, 내용 비교, 성패 분석

**중요**: 질문에 가장 적합한 2-4가지 방향을 **자유롭게 조합**하세요.
- 같은 차원에서만 선택할 필요 없음
- 예: "시간축(원인)" + "클래스(인물)" + "범위(국제)" 조합 가능

**사용 가능한 프로퍼티 그룹 (반드시 이 목록에서만 선택!):**
{groups_list}
"""

    prompt = f"""다음 질문을 분석하여, 사용자가 선택할 수 있는 2-4가지 답변 방향을 제시하세요.

질문: "{query}"
키워드: {', '.join(keywords) if keywords else '없음'}

{strategy_descriptions}

**출력 형식 (JSON)**:
{{
  "directions": [
    {{
      "direction_id": "고유ID (영문_조합, 예: time_cause, class_person)",
      "title": "방향 제목 (15자 이내)",
      "description": "구체적 설명 (20-40자)",
      "property_groups": ["관련 프로퍼티 그룹 3-5개"]
    }},
    ...
  ]
}}

**예시 1** (임진왜란 질문):
{{
  "directions": [
    {{"direction_id": "time_cause", "title": "전쟁 발생 원인", "description": "조선과 일본의 정치 상황, 도요토미의 야망", "property_groups": ["인과관계", "외교", "통치"]}},
    {{"direction_id": "scope_national", "title": "조선 내부 피해", "description": "인명 피해, 문화재 소실, 경제 타격", "property_groups": ["참여", "변경", "경제"]}},
    {{"direction_id": "class_person", "title": "주요 인물", "description": "이순신, 권율, 선조 등 핵심 인물들", "property_groups": ["인물", "직위", "참여"]}}
  ]
}}

**예시 2** (세종대왕 훈민정음 질문):
{{
  "directions": [
    {{"direction_id": "time_background", "title": "창제 배경", "description": "한자의 어려움, 백성 소통 필요성", "property_groups": ["인과관계", "문화", "통치"]}},
    {{"direction_id": "class_event", "title": "창제 과정", "description": "1443년 창제, 집현전 학자 참여", "property_groups": ["사건", "연도", "참여"]}},
    {{"direction_id": "time_impact", "title": "문화적 영향", "description": "한글 보급, 문자 생활 혁명", "property_groups": ["문화", "변경", "문서"]}}
  ]
}}

위 예시를 참고하여, 주어진 질문에 최적화된 방향을 생성하세요."""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        # JSON 블록 추출
        if '```' in content:
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)
        llm_directions = result.get("directions", [])

        # 방향 리스트 변환
        directions = []
        for idx, d in enumerate(llm_directions[:4], 1):  # 최대 4개
            directions.append({
                "id": idx,
                "direction_id": d.get("direction_id", f"custom_{idx}"),
                "title": d.get("title", ""),
                "description": d.get("description", ""),
                "property_groups": d.get("property_groups", []),
                "example_keywords": []
            })

        # property_groups 검증 (유효한 그룹만 유지)
        directions = validate_property_groups(directions, available_groups)
        
        print(f"[intent_clarification] LLM 방향 생성 완료: {len(directions)}개")
        for d in directions:
            print(f"  - {d['title']}: {d['property_groups']}")

        return directions

    except Exception as e:
        print(f"[WARNING] LLM 자유 조합 생성 실패: {e}, 기본 방향 반환")

        # Fallback: 간단한 기본 방향
        return [
            {
                "id": 1,
                "direction_id": "time_cause",
                "title": "원인 및 배경",
                "description": "해당 사건이나 현상의 배경과 원인",
                "property_groups": ["인과관계", "외교", "통치"],
                "example_keywords": []
            },
            {
                "id": 2,
                "direction_id": "time_consequence",
                "title": "결과 및 영향",
                "description": "사건 이후의 결과와 영향",
                "property_groups": ["인과관계", "사건", "변경"],
                "example_keywords": []
            },
            {
                "id": 3,
                "direction_id": "class_person",
                "title": "관련 인물",
                "description": "주요 인물과 그들의 역할",
                "property_groups": ["인물", "참여", "직위"],
                "example_keywords": []
            }
        ]


# ========== 방향 생성 라우터 (수정됨) ==========

def generate_expansion_directions(
    query_type: str,
    query: str,
    keywords: List[str]
) -> tuple[str, List[Dict[str, Any]]]:
    """
    질문에 최적화된 확장 방향 생성 (자유 조합 방식)

    Args:
        query_type: 질문 유형 (참고용)
        query: 사용자 질문
        keywords: 추출된 키워드

    Returns:
        ("mixed", 방향 리스트) - 전략은 "mixed"로 반환
    """
    directions = generate_llm_based_directions(query, keywords, query_type)
    return "mixed", directions  # 전략은 혼합(mixed)으로 반환




# ========== 사용자 질문 텍스트 생성 ==========

def generate_clarification_question_template(
    strategy: str,
    directions: List[Dict[str, Any]],
    query: str
) -> str:
    """
    템플릿 기반 재질문 생성 (Fallback)

    Args:
        strategy: 선택된 전략 (혼합 시 "mixed")
        directions: 방향 리스트
        query: 원본 질문

    Returns:
        사용자 친화적 질문 텍스트
    """
    question_text = f'"{query}"는 여러 관점에서 답변할 수 있어요.\n\n'
    question_text += "어떤 방향의 정보가 더 궁금하신가요?\n\n"

    for direction in directions:
        question_text += f"{direction['id']}️⃣ {direction['title']}\n"
        question_text += f"   {direction['description']}\n\n"

    return question_text


def generate_clarification_question(
    strategy: str,
    directions: List[Dict[str, Any]],
    query: str,
    use_llm: bool = False
) -> str:
    """
    사용자에게 보여줄 의도 확인 질문 텍스트 생성 (템플릿 기반)

    Args:
        strategy: 선택된 전략 (혼합 시 "mixed")
        directions: 방향 리스트
        query: 원본 질문
        use_llm: LLM 사용 여부 (기본값: False, 템플릿 사용)

    Returns:
        사용자 친화적 질문 텍스트
    """
    # 템플릿 기반으로 원복 (기본 동작)
    return generate_clarification_question_template(strategy, directions, query)
