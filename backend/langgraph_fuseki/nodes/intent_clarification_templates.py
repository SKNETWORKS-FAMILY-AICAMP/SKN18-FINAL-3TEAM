"""
대화형 의도 확인 시스템 - 템플릿 및 전략 매핑

Phase 1: 고정 매핑 방식 (Fixed Mapping)
- 쿼리 타입에 따라 고정된 1:1 매핑으로 분류 전략 선택
- 각 전략별로 미리 정의된 방향 템플릿 사용
"""

from typing import Dict, List, Literal, Any

# ========== 전략 매핑 (Phase 1: 고정) ==========

STRATEGY_MAPPING: Dict[str, str] = {
    "causal": "time-based",        # 인과관계 → 시간축 기반
    "factual": "class-based",      # 사실 확인 → 클래스 기반
    "deep_analysis": "scope-based", # 심층 분석 → 범위 기반
    "comparative": "depth-based"    # 비교 분석 → 깊이 기반
}


def select_strategy(query_type: Literal["causal", "factual", "deep_analysis", "comparative"]) -> str:
    """
    질문 유형에 따라 분류 전략 선택 (Phase 1: 고정 매핑)

    Args:
        query_type: 질문 유형

    Returns:
        분류 전략 ("time-based", "class-based", "depth-based", "scope-based")
    """
    return STRATEGY_MAPPING.get(query_type, "time-based")


# ========== 방향 생성 템플릿 ==========

def generate_time_based_directions(query: str, keywords: List[str]) -> List[Dict[str, Any]]:
    """
    시간축 기반 방향 생성 (causal 질문용)

    Args:
        query: 사용자 질문
        keywords: 추출된 키워드

    Returns:
        3가지 시간축 방향
    """
    return [
        {
            "id": 1,
            "direction_id": "cause",
            "title": "원인 및 배경 (사건 이전)",
            "description": f"'{keywords[0] if keywords else '해당 사건'}'이 일어난 정치적·사회적 배경과 원인",
            "time_direction": "before",
            "time_scope": "background",
            "property_groups": ["인과관계", "외교", "통치", "시기"],
            "example_keywords": []  # 실제 LLM이 채울 예정
        },
        {
            "id": 2,
            "direction_id": "immediate_consequence",
            "title": "직후 발생한 사건 (몇 개월~1년)",
            "description": "사건 직후 발생한 즉각적인 결과와 사건들",
            "time_direction": "after",
            "time_scope": "short_term",
            "property_groups": ["인과관계", "사건", "연도", "변경"],
            "example_keywords": []
        },
        {
            "id": 3,
            "direction_id": "long_term_impact",
            "title": "장기적 영향 (수년~수십년 후)",
            "description": "사건이 조선 사회와 역사에 미친 장기적 영향",
            "time_direction": "after",
            "time_scope": "long_term",
            "property_groups": ["외교", "통치", "변경", "조약"],
            "example_keywords": []
        }
    ]


def generate_class_based_directions(query: str, keywords: List[str]) -> List[Dict[str, Any]]:
    """
    클래스 기반 방향 생성 (factual 질문용)

    Args:
        query: 사용자 질문
        keywords: 추출된 키워드

    Returns:
        3-4가지 온톨로지 클래스 방향
    """
    # 질문에 따라 동적으로 클래스 선택
    # 예: "누구" → Person, "무엇" → Event/Institution, "어디서" → Location

    base_directions = [
        {
            "id": 1,
            "direction_id": "person_focus",
            "title": "인물 중심 정보",
            "description": "관련된 주요 인물, 역할, 관계",
            "target_class": "Person",
            "property_groups": ["참여", "인물", "직위", "역할"],
            "example_keywords": []
        },
        {
            "id": 2,
            "direction_id": "event_focus",
            "title": "사건 중심 정보",
            "description": "관련 사건들의 경과, 내용, 결과",
            "target_class": "Event",
            "property_groups": ["사건", "연도", "인과관계", "문서"],
            "example_keywords": []
        },
        {
            "id": 3,
            "direction_id": "institution_focus",
            "title": "제도·기구 중심 정보",
            "description": "관련 제도, 관직, 법률, 조직",
            "target_class": "Institution",
            "property_groups": ["설립", "변경", "직위", "법률"],
            "example_keywords": []
        }
    ]

    return base_directions


def generate_scope_based_directions(query: str, keywords: List[str]) -> List[Dict[str, Any]]:
    """
    범위 기반 방향 생성 (deep_analysis 질문용)

    Args:
        query: 사용자 질문
        keywords: 추출된 키워드

    Returns:
        4가지 영향 범위 방향
    """
    return [
        {
            "id": 1,
            "direction_id": "individual_impact",
            "title": "인적 영향 (개인·집단)",
            "description": "특정 인물이나 집단에 미친 직접적 영향",
            "scope": "individual",
            "property_groups": ["참여", "인물", "직위", "변경"],
            "example_keywords": []
        },
        {
            "id": 2,
            "direction_id": "institutional_impact",
            "title": "제도적 영향 (관직·법률)",
            "description": "제도, 관직, 법률 체계에 미친 변화",
            "scope": "institutional",
            "property_groups": ["설립", "변경", "법률", "직위"],
            "example_keywords": []
        },
        {
            "id": 3,
            "direction_id": "national_impact",
            "title": "국가적 영향 (정치·경제·문화)",
            "description": "조선의 정치, 경제, 사회, 문화에 미친 영향",
            "scope": "national",
            "property_groups": ["통치", "변경", "경제", "문화"],
            "example_keywords": []
        },
        {
            "id": 4,
            "direction_id": "international_impact",
            "title": "국제적 영향 (외교·주변국)",
            "description": "주변국 관계 및 국제 정세에 미친 영향",
            "scope": "international",
            "property_groups": ["외교", "조약", "통치"],
            "example_keywords": []
        }
    ]


def generate_depth_based_directions(query: str, keywords: List[str]) -> List[Dict[str, Any]]:
    """
    깊이 기반 방향 생성 (comparative 질문용)

    Args:
        query: 사용자 질문
        keywords: 추출된 키워드

    Returns:
        3가지 분석 깊이 방향
    """
    return [
        {
            "id": 1,
            "direction_id": "basic_info",
            "title": "기본 정보 비교",
            "description": "시기, 배경, 주도 세력, 개요 등 기본 사실 비교",
            "depth": "basic",
            "property_groups": ["연도", "참여", "소속", "문서"],
            "example_keywords": []
        },
        {
            "id": 2,
            "direction_id": "content_comparison",
            "title": "내용·방법 비교",
            "description": "구체적인 개혁 내용, 추진 방법, 정책 비교",
            "depth": "relational",
            "property_groups": ["변경", "설립", "법률", "인과관계"],
            "example_keywords": []
        },
        {
            "id": 3,
            "direction_id": "outcome_analysis",
            "title": "성공/실패 원인 비교",
            "description": "왜 성공했는지 또는 실패했는지, 역사적 의의 비교",
            "depth": "causal",
            "property_groups": ["인과관계", "반대", "외교", "법률"],
            "example_keywords": []
        }
    ]


# ========== 방향 생성 라우터 ==========

def generate_expansion_directions(
    query_type: Literal["causal", "factual", "deep_analysis", "comparative"],
    query: str,
    keywords: List[str]
) -> tuple[str, List[Dict[str, Any]]]:
    """
    질문 유형에 따라 적절한 방향 생성 함수 호출

    Args:
        query_type: 질문 유형
        query: 사용자 질문
        keywords: 추출된 키워드

    Returns:
        (선택된 전략, 방향 리스트)
    """
    strategy = select_strategy(query_type)

    if strategy == "time-based":
        directions = generate_time_based_directions(query, keywords)
    elif strategy == "class-based":
        directions = generate_class_based_directions(query, keywords)
    elif strategy == "scope-based":
        directions = generate_scope_based_directions(query, keywords)
    elif strategy == "depth-based":
        directions = generate_depth_based_directions(query, keywords)
    else:
        # fallback: time-based
        directions = generate_time_based_directions(query, keywords)

    return strategy, directions


# ========== 사용자 질문 텍스트 생성 ==========

def generate_clarification_question(
    strategy: str,
    directions: List[Dict[str, Any]],
    query: str
) -> str:
    """
    사용자에게 보여줄 의도 확인 질문 텍스트 생성

    Args:
        strategy: 선택된 전략
        directions: 방향 리스트
        query: 원본 질문

    Returns:
        사용자 친화적 질문 텍스트
    """
    # 전략별 인트로 메시지
    strategy_intro = {
        "time-based": "여러 시간 관점에서 답변할 수 있어요.",
        "class-based": "여러 측면에서 답변할 수 있어요.",
        "scope-based": "여러 범위로 분석할 수 있어요.",
        "depth-based": "여러 깊이로 비교할 수 있어요."
    }

    intro = strategy_intro.get(strategy, "여러 방향으로 답변할 수 있어요.")

    # 질문 텍스트 구성
    question_text = f'\n{"="*70}\n'
    question_text += f'"{query}"는 {intro}\n\n'

    # 전략별 질문 문구
    if strategy == "time-based":
        question_text += "어떤 시기의 정보가 더 궁금하신가요?\n\n"
    elif strategy == "class-based":
        question_text += "어떤 측면의 정보가 더 궁금하신가요?\n\n"
    elif strategy == "scope-based":
        question_text += "어떤 범위의 영향이 더 궁금하신가요?\n\n"
    elif strategy == "depth-based":
        question_text += "어떤 측면을 중심으로 비교하고 싶으신가요?\n\n"

    # 옵션 나열
    for direction in directions:
        question_text += f"{direction['id']}️⃣ {direction['title']}\n"
        question_text += f"   {direction['description']}\n"

        # 예시 키워드가 있으면 표시
        if direction.get("example_keywords"):
            keywords_str = ", ".join(direction["example_keywords"][:5])
            question_text += f"   → [{keywords_str}]\n"
        question_text += "\n"

    question_text += f'{"="*70}\n'

    return question_text
