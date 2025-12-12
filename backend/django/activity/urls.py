from django.urls import path
from .views import (
    SearchHistoryListView,
    SearchHistoryCreateView,
    WatchingHistoryListView,
    WatchingHistoryCreateView,
)

# activity 앱 URL 패턴
# 검색 기록 + 시청 기록 관리

urlpatterns = [
    # ============================================
    # 검색 기록 API
    # ============================================
    # GET /api/activity/search-logs/ - 내 검색 기록 조회
    # POST /api/activity/search-logs/ - 검색 기록 적재
    path('search-logs/', SearchHistoryListView.as_view(), name='search-history-list'),
    path('search-logs/', SearchHistoryCreateView.as_view(), name='search-history-create'),

    # ============================================
    # 시청 기록 API
    # ============================================
    # GET /api/activity/watch-logs/ - 내 시청 기록 조회
    # POST /api/activity/watch-logs/ - 시청 기록 적재
    path('watch-logs/', WatchingHistoryListView.as_view(), name='watching-history-list'),
    path('watch-logs/', WatchingHistoryCreateView.as_view(), name='watching-history-create'),
]
