from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    check_auth,
    logout_view,
    delete_account,
    ProfileView,
    ProfileImageUploadView,
    AdminUserListView,
    AdminUserDetailView,
    AdminUserUpdateView,
    AdminUserDeleteView,
)

# users 앱 URL 패턴 (accounts + users 통합)
# Google OAuth는 config/urls.py의 /accounts/에서 처리 (django-allauth)

urlpatterns = [
    # ============================================
    # 인증 API (accounts에서 통합)
    # ============================================
    # 인증 상태 확인
    path('check-auth/', check_auth, name='check_auth'),

    # 로그아웃
    path('logout/', logout_view, name='logout'),

    # 회원탈퇴
    path('delete-account/', delete_account, name='delete_account'),

    # JWT 토큰 관리
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

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
    # GET /api/users/admin/ - 회원 목록
    path('admin/', AdminUserListView.as_view(), name='admin-user-list'),

    # GET /api/users/admin/<id>/ - 회원 상세
    path('admin/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),

    # PATCH /api/users/admin/<id>/ - 회원 정보 수정
    path('admin/<int:pk>/update/', AdminUserUpdateView.as_view(), name='admin-user-update'),

    # DELETE /api/users/admin/<id>/ - 회원 삭제
    path('admin/<int:pk>/delete/', AdminUserDeleteView.as_view(), name='admin-user-delete'),
]
