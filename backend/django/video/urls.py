from django.urls import path
from . import views
from .views import VideoListView, VideoDetailView, VideoUploadView

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
]
