"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.contrib.auth import logout
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from allauth.socialaccount.models import SocialToken, SocialApp
import requests

# 인증 상태 확인 API (DRF APIView - 토큰 있으면 검증, 없으면 False 반환)
@api_view(['GET'])
@permission_classes([AllowAny])  # 누구나 호출 가능 (401 에러 방지)
def check_auth(request):
    # JWT 토큰이 있으면 수동으로 검증
    jwt_auth = JWTAuthentication()
    try:
        # Authorization 헤더에서 JWT 토큰 검증 시도
        user_auth = jwt_auth.authenticate(request)
        if user_auth is not None:
            user, token = user_auth
            # username이 없으면 email 사용
            display_name = user.username if user.username else user.email

            return Response({
                'isAuthenticated': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': display_name,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
            })
    except Exception:
        # JWT 토큰이 없거나 유효하지 않은 경우
        pass

    # 세션 기반 인증도 확인 (fallback)
    if request.user.is_authenticated:
        user = request.user
        display_name = user.username if user.username else user.email
        return Response({
            'isAuthenticated': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': display_name,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })

    # 인증되지 않은 경우 (401 에러 대신 isAuthenticated: False 반환)
    return Response({'isAuthenticated': False})

# 로그아웃 API (CSRF 제외)
@csrf_exempt
def logout_view(request):
    logout(request)
    return JsonResponse({'message': 'Logged out successfully'})

# 회원탈퇴 API (Google OAuth 연동 해제 포함)
@api_view(['DELETE'])
@permission_classes([AllowAny])  # JWT 토큰으로 인증 확인
def delete_account(request):
    """
    회원탈퇴 API
    - Google OAuth 토큰 revoke (권한 해제)
    - 사용자 계정 삭제
    """
    # JWT 토큰으로 사용자 인증
    jwt_auth = JWTAuthentication()
    try:
        user_auth = jwt_auth.authenticate(request)
        if user_auth is None:
            # JWT 토큰이 없으면 세션 확인
            if not request.user.is_authenticated:
                return Response(
                    {'error': '인증되지 않은 사용자입니다.'},
                    status=401
                )
            user = request.user
        else:
            user, token = user_auth
    except Exception:
        return Response({'error': '인증 실패'}, status=401)

    # 1. Google OAuth 토큰 revoke (연동 해제)
    try:
        # SocialToken에서 Google access token 조회
        social_tokens = SocialToken.objects.filter(
            account__user=user,
            account__provider='google'
        )

        for social_token in social_tokens:
            access_token = social_token.token

            # Google OAuth2 revoke 엔드포인트 호출
            revoke_url = 'https://oauth2.googleapis.com/revoke'
            requests.post(
                revoke_url,
                params={'token': access_token},
                headers={'content-type': 'application/x-www-form-urlencoded'}
            )
            # revoke 실패해도 계정 삭제는 진행

    except Exception:
        # 오류가 발생해도 계정 삭제는 진행
        pass

    # 2. 사용자 계정 삭제 (연결된 SocialAccount, SocialToken도 CASCADE로 자동 삭제됨)
    try:
        # Django의 CASCADE 삭제:
        # - auth_user 삭제
        # - socialaccount_socialaccount 자동 삭제 (ForeignKey on_delete=CASCADE)
        # - socialaccount_socialtoken 자동 삭제 (ForeignKey on_delete=CASCADE)
        user.delete()

        return Response({
            'message': '회원탈퇴가 완료되었습니다. Google 연동도 해제되었습니다.'
        }, status=200)
    except Exception:
        return Response({'error': '회원탈퇴 처리 중 오류가 발생했습니다.'}, status=500)

urlpatterns = [
    path('admin/', admin.site.urls),

    # ============================================
    # Authentication API Endpoints
    # ============================================
    path('api/check-auth/', check_auth, name='check_auth'),
    path('api/logout/', logout_view, name='logout'),
    path('api/delete-account/', delete_account, name='delete_account'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # ============================================
    # Google OAuth (django-allauth)
    # ============================================
    path('accounts/', include('allauth.urls')),

    # ============================================
    # App API Routes (currently empty, add API endpoints in each app)
    # Note: React frontend handles all UI routing
    # ============================================
    path('api/home/', include('home.urls')),
    path('api/search/', include('search.urls')),
    path('api/video/', include('video.urls')),
    path('api/mypage/', include('mypage.urls')),
    # login APIs are handled above in Authentication section
]
