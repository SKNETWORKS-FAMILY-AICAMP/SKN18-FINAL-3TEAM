from django.urls import path
from .views import (
    ProfileView,
    ProfileImageUploadView,
    AdminUserListView,
    AdminUserDetailView,
    AdminUserUpdateView,
    AdminUserDeleteView,
)

urlpatterns = [
    # ============================================
    # 프로필 API (인증된 사용자)
    # ============================================
    # GET/PATCH /api/users/profile/ - 내 프로필 조회/수정
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # POST/DELETE /api/users/profile/image/ - 프로필 이미지 업로드/삭제
    path('profile/image/', ProfileImageUploadView.as_view(), name='profile-image'),
    
    # ============================================
    # 관리자 API (admin 권한)
    # ============================================
    # GET /api/users/ - 회원 목록
    path('', AdminUserListView.as_view(), name='admin-user-list'),
    
    # GET /api/users/<id>/ - 회원 상세
    path('<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    
    # PATCH /api/users/<id>/ - 회원 정보 수정
    path('<int:pk>/update/', AdminUserUpdateView.as_view(), name='admin-user-update'),
    
    # DELETE /api/users/<id>/ - 회원 삭제
    path('<int:pk>/delete/', AdminUserDeleteView.as_view(), name='admin-user-delete'),
]
