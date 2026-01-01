"""
LangGraph Recommendation - State Definition

영상 키워드 및 추천 키워드 생성을 위한 상태 정의
"""

from typing import TypedDict, NotRequired, List, Dict, Any


class RecommendationState(TypedDict):
    """영상 추천 키워드 생성용 상태"""

    # ========== 입력 ==========
    video_title: str  # 영상 제목

    # ========== Stage 1: video_keyword 추출 ==========
    basic_keywords: NotRequired[List[str]]  # Kiwi 형태소 분석 결과
    video_keywords: NotRequired[str]  # TTL 매칭된 키워드 (콤마 구분 문자열)
    # 예: "경복궁,태조,창덕궁"

    # ========== Stage 2: recommend_keyword 추출 ==========
    intent: NotRequired[str]  # LLM이 파악한 의도
    expanded_keywords: NotRequired[List[str]]  # LLM이 확장한 키워드
    extracted_entities: NotRequired[List[Dict[str, Any]]]  # TTL에서 추출한 엔티티
    # [{"uri": "hist:...", "name": "이순신", "type": "Person", ...}, ...]

    # Thread 병렬 실행 결과
    thread_results: NotRequired[Dict[str, Any]]  # 관계 정보
    # {
    #     "outgoing_relations": [...],
    #     "incoming_relations": [...],
    #     "connected_entities": [...]
    # }

    final_recommendations: NotRequired[List[str]]  # 최종 추천 엔티티 리스트
    recommend_keywords: NotRequired[str]  # 추천 키워드 (콤마 구분 문자열)
    # 예: "이순신,임진왜란,선조"

    # ========== 메타 정보 ==========
    executed_nodes: NotRequired[List[str]]  # 실행된 노드 추적
    errors: NotRequired[List[str]]  # 에러 메시지
