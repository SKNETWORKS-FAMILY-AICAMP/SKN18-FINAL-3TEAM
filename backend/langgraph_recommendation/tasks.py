"""
Celery Tasks for Video Keyword Recommendation

영상 저장 후 비동기로 키워드 생성 및 DB 업데이트
"""

from celery import shared_task
from backend.langgraph_recommendation.graph import create_recommendation_graph


@shared_task(bind=True, max_retries=3)
def generate_video_keywords_task(self, video_id: int, video_title: str):
    """
    영상 키워드 + 추천 키워드 생성 Celery Task

    Args:
        video_id: 영상 ID
        video_title: 영상 제목

    Returns:
        {
            "status": "success" | "error",
            "video_id": int,
            "video_keywords": str,  # "키워드1,키워드2"
            "recommend_keywords": str  # "추천1,추천2,추천3"
        }

    에러 처리:
        - LLM API 장애 등으로 실패 시 자동 재시도 (exponential backoff)
        - 3회 재시도 후에도 실패하면 빈 문자열로 DB 업데이트
    """
    print(f"\n{'='*70}")
    print(f"[Celery Task] 영상 키워드 생성 시작")
    print(f"  video_id: {video_id}")
    print(f"  video_title: {video_title}")
    print(f"{'='*70}\n")

    try:
        # 1. 랭그래프 실행
        graph = create_recommendation_graph()
        result = graph.invoke({"video_title": video_title})

        video_keywords = result.get('video_keywords', '')
        recommend_keywords = result.get('recommend_keywords', '')

        print(f"\n[Celery Task] 랭그래프 실행 완료")
        print(f"  video_keywords: {video_keywords}")
        print(f"  recommend_keywords: {recommend_keywords}")

        # 2. DB 업데이트
        # ⚠️ TODO: DB 컬럼명이 확정되면 아래 필드명 수정 필요
        # 현재 가정: video_keywords, recommend_keywords 컬럼 추가 예정
        from backend.django.video.models import Video

        Video.objects.filter(id=video_id).update(
            # ⚠️ 주의: 아래 컬럼명은 DB 테이블에 컬럼 추가 후 수정 필요!
            # video_keywords=video_keywords,
            # recommend_keywords=recommend_keywords
        )

        print(f"[Celery Task] DB 업데이트 완료 (video_id={video_id})")
        print(f"⚠️ 주의: DB 컬럼 추가 후 tasks.py의 Video.objects.filter().update() 주석 해제 필요!\n")

        return {
            "status": "success",
            "video_id": video_id,
            "video_keywords": video_keywords,
            "recommend_keywords": recommend_keywords
        }

    except Exception as exc:
        print(f"\n[Celery Task] 에러 발생: {exc}")
        print(f"  재시도 횟수: {self.request.retries}/3")

        # 재시도 (exponential backoff: 2초, 4초, 8초)
        if self.request.retries < self.max_retries:
            print(f"  {2 ** self.request.retries}초 후 재시도...")
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        else:
            # 최종 실패 시 빈 문자열로 DB 업데이트
            print(f"  최종 실패, 빈 문자열로 DB 업데이트")
            from backend.django.video.models import Video

            Video.objects.filter(id=video_id).update(
                # ⚠️ 주의: 아래 컬럼명은 DB 테이블에 컬럼 추가 후 수정 필요!
                # video_keywords="",
                # recommend_keywords=""
            )

            return {
                "status": "error",
                "video_id": video_id,
                "video_keywords": "",
                "recommend_keywords": "",
                "error": str(exc)
            }
