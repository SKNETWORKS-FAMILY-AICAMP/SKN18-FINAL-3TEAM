from django.urls import path
from .views import (
    SearchHistoryListCreateView,
    WatchingHistoryListCreateView,
    get_recommended_keyword,
    get_recommended_videos,
)

# activity 앱 URL 패턴
# 검색 기록 + 시청 기록 관리

urlpatterns = [
    # ============================================
    # 검색 기록 API
    # ============================================
    # GET /api/activity/search-logs/ - 내 검색 기록 조회
    # POST /api/activity/search-logs/ - 검색 기록 적재
    path('search-logs/', SearchHistoryListCreateView.as_view(), name='search-history'),

    # ============================================
    # 시청 기록 API
    # ============================================
    # GET /api/activity/watch-logs/ - 내 시청 기록 조회
    # POST /api/activity/watch-logs/ - 시청 기록 적재
    path('watch-logs/', WatchingHistoryListCreateView.as_view(), name='watching-history'),

    # ============================================
    # 추천 키워드 API
    # ============================================
    # GET /api/activity/recommended-keyword/ - 시청 기록 기반 추천 키워드
    path('recommended-keyword/', get_recommended_keyword, name='recommended-keyword'),
    
    # ============================================
    # 추천 영상 API
    # ============================================
    # GET /api/activity/recommended-videos/ - 최근 시청 기록 기반 추천 영상 (created_at 최신순)
    path('recommended-videos/', get_recommended_videos, name='recommended-videos'),
]
