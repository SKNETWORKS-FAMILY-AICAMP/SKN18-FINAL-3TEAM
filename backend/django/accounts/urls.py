from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import check_auth, logout_view, delete_account

# accounts 앱 URL 패턴
# Google OAuth는 config/urls.py의 /accounts/에서 처리 (django-allauth)

urlpatterns = [
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
]
