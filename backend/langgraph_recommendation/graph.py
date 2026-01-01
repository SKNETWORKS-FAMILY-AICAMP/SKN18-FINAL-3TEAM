"""
LangGraph Recommendation - Graph Definition

영상 키워드 및 추천 키워드 생성 그래프

Flow:
    START → video_keyword_extraction → recommend_keyword_generation → END

특징:
- 단순한 순차 실행 (사용자 상호작용 없음)
- Celery 백그라운드 Task로 실행
- 결과: video_keywords, recommend_keywords (콤마 구분 문자열)
"""

from langgraph.graph import StateGraph, END
from backend.langgraph_recommendation.state import RecommendationState
from backend.langgraph_recommendation.nodes.video_keyword_node import video_keyword_node
from backend.langgraph_recommendation.nodes.recommend_keyword_node import recommend_keyword_node


def create_recommendation_graph():
    """
    영상 키워드 추천 그래프 생성

    Returns:
        Compiled LangGraph
    """
    workflow = StateGraph(RecommendationState)

    # 노드 등록
    workflow.add_node("video_keyword_extraction", video_keyword_node)
    workflow.add_node("recommend_keyword_generation", recommend_keyword_node)

    # 플로우 정의
    workflow.set_entry_point("video_keyword_extraction")
    workflow.add_edge("video_keyword_extraction", "recommend_keyword_generation")
    workflow.add_edge("recommend_keyword_generation", END)

    return workflow.compile()


# 테스트용 (직접 실행 시)
if __name__ == "__main__":
    print("="*70)
    print("LangGraph Recommendation - 테스트 실행")
    print("="*70)

    graph = create_recommendation_graph()

    # 테스트 입력
    test_input = {
        "video_title": "경복궁을 지은 왕"
    }

    print(f"\n입력: {test_input}")
    print("\n그래프 실행 중...\n")

    result = graph.invoke(test_input)

    print("\n" + "="*70)
    print("결과:")
    print("="*70)
    print(f"video_keywords: {result.get('video_keywords')}")
    print(f"recommend_keywords: {result.get('recommend_keywords')}")
    print(f"실행된 노드: {result.get('executed_nodes')}")

    if result.get('errors'):
        print(f"\n에러: {result.get('errors')}")
