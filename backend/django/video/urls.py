from django.urls import path
from . import views
from .views import (
    VideoListView,
    VideoDetailView,
    VideoUploadView,
    VideoUpdateView,
    VideoDeleteView,
    PopularVideosView,
    PopularTagsView
)

# Video app URLs

urlpatterns = [
    # 유니티가 /api/video/generate/ 로 접속하면 views.generate_scenario 실행
    path('generate/', views.generate_scenario, name='generate_scenario'),

    # ============================================
    # 영상 API
    # ============================================
    # GET /api/video/list/ - 영상 목록 조회
    path('list/', VideoListView.as_view(), name='video-list'),

    # GET /api/video/<id>/ - 영상 상세 조회
    path('<int:pk>/', VideoDetailView.as_view(), name='video-detail'),

    # POST /api/video/upload/ - 영상 업로드 (관리자 전용)
    path('upload/', VideoUploadView.as_view(), name='video-upload'),

    # PATCH /api/video/<id>/update/ - 영상 수정 (관리자 전용)
    path('<int:pk>/update/', VideoUpdateView.as_view(), name='video-update'),

    # DELETE /api/video/<id>/delete/ - 영상 삭제 (관리자 전용)
    path('<int:pk>/delete/', VideoDeleteView.as_view(), name='video-delete'),

    # GET /api/video/popular/ - 인기 영상 조회
    path('popular/', PopularVideosView.as_view(), name='popular-videos'),

    # GET /api/video/tags/popular/ - 인기 태그 조회
    path('tags/popular/', PopularTagsView.as_view(), name='popular-tags'),
]
