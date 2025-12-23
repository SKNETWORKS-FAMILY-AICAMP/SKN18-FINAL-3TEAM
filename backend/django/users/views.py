import os
import uuid
from django.conf import settings
from django.contrib.auth import logout
from django.core.cache import cache
from django.db import models
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, DestroyAPIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from allauth.socialaccount.models import SocialToken, SocialAccount
import requests

from .models import User
from .serializers import (
    ProfileSerializer,
    ProfileUpdateSerializer,
    ProfileImageSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
)
from config.permissions import IsAdminUser


# ============================================
# 인증 API (accounts에서 통합)
# ============================================

# 인증 상태 확인 API (DRF APIView - 토큰 있으면 검증, 없으면 False 반환)
@api_view(['GET'])
@permission_classes([AllowAny])  # 누구나 호출 가능 (401 에러 방지)
def check_auth(request):
    """
    인증 상태 확인 API
    - JWT 토큰 또는 세션으로 사용자 인증 확인
    - 인증된 경우 사용자 정보 반환

    커스텀 User 모델 사용:
    - user.user_id (PK)
    - user.email
    - user.nickname (또는 display_name)
    - user.permission ('user' / 'admin')
    - user.profile_image
    """
    # JWT 토큰이 있으면 수동으로 검증
    jwt_auth = JWTAuthentication()
    try:
        # Authorization 헤더에서 JWT 토큰 검증 시도
        user_auth = jwt_auth.authenticate(request)
        if user_auth is not None:
            user, token = user_auth

            return Response({
                'isAuthenticated': True,
                'user': {
                    'id': user.id,  # Django 기본 pk
                    'email': user.email,
                    'nickname': user.nickname,
                    'display_name': user.display_name,  # nickname 또는 email 앞부분
                    'permission': user.permission,  # 직접 접근 (profile 없음)
                    'profile_image': user.profile_image,
                }
            })
    except Exception:
        # JWT 토큰이 없거나 유효하지 않은 경우
        pass

    # 세션 기반 인증도 확인 (fallback - OAuth 과정에서 사용)
    if request.user.is_authenticated:
        user = request.user

        return Response({
            'isAuthenticated': True,
            'user': {
                'id': user.id,  # Django 기본 pk
                'email': user.email,
                'nickname': user.nickname,
                'display_name': user.display_name,
                'permission': user.permission,
                'profile_image': user.profile_image,
            }
        })

    # 인증되지 않은 경우 (401 에러 대신 isAuthenticated: False 반환)
    return Response({'isAuthenticated': False})


# 로그아웃 API (CSRF 제외)
@csrf_exempt
def logout_view(request):
    """
    로그아웃 API
    - Django 세션 로그아웃 처리
    """
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

    커스텀 User 모델 사용:
    - user 테이블 삭제 시 CASCADE로 연관 데이터 자동 삭제
      - socialaccount_socialaccount
      - socialaccount_socialtoken
      - (향후) comment, reply, likes, watching_history 등
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

    # 2. 사용자 계정 삭제
    try:
        # Django의 CASCADE 삭제:
        # - user 테이블 삭제
        # - socialaccount_socialaccount 자동 삭제 (ForeignKey on_delete=CASCADE)
        # - socialaccount_socialtoken 자동 삭제 (ForeignKey on_delete=CASCADE)
        # - (향후) comment, reply, likes 등 자동 삭제

        # 먼저 SocialAccount 관련 데이터 삭제 (CASCADE가 작동하지 않는 경우 대비)
        SocialAccount.objects.filter(user=user).delete()

        # 그 다음 사용자 삭제
        user.delete()

        return Response({
            'message': '회원탈퇴가 완료되었습니다. Google 연동도 해제되었습니다.'
        }, status=200)
    except Exception as e:
        import traceback
        print(f"❌ 회원탈퇴 오류: {e}")
        print(traceback.format_exc())
        return Response({'error': f'회원탈퇴 처리 중 오류가 발생했습니다: {str(e)}'}, status=500)


# ============================================
# 프로필 API
# ============================================
class ProfileView(APIView):
    """
    내 프로필 조회/수정 API
    
    GET /api/users/profile/
    - 내 프로필 정보 조회
    
    PATCH /api/users/profile/
    - 프로필 수정 (nickname, profile_image, gender, age)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """내 프로필 조회 (Redis 캐싱)"""
        # 캐시 키 생성
        cache_key = f'user_profile:{request.user.id}'
        
        # 1. 캐시 조회
        cached_data = cache.get(cache_key)
        
        if cached_data:
            # 캐시 HIT
            return Response({
                'data': cached_data,
                'message': 'ok',
                'cached': True
            })
        
        # 2. 캐시 MISS - DB 조회
        serializer = ProfileSerializer(request.user)
        profile_data = serializer.data
        
        # 3. Redis에 저장 (5분 TTL)
        cache.set(cache_key, profile_data, 300)
        
        return Response({
            'data': profile_data,
            'message': 'ok',
            'cached': False
        })
    
    def patch(self, request):
        """프로필 수정"""
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # 캐시 무효화
            cache_key = f'user_profile:{request.user.id}'
            cache.delete(cache_key)
            
            return Response({
                'data': ProfileSerializer(request.user).data,
                'message': '프로필이 수정되었습니다.'
            })
        
        return Response({
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '입력값을 확인해주세요.',
                'fields': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class ProfileImageUploadView(APIView):
    """
    프로필 이미지 업로드 API
    
    POST /api/users/profile/image/
    - 이미지 파일 업로드 (multipart/form-data)
    - 파일은 media/profiles/ 에 저장
    - DB에는 경로만 저장
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """프로필 이미지 업로드"""
        serializer = ProfileImageSerializer(data=request.data)
        
        if serializer.is_valid():
            image = serializer.validated_data['image']
            
            # 파일명 생성 (user_id + uuid + 확장자)
            ext = image.name.split('.')[-1].lower()
            filename = f"user_{request.user.id}_{uuid.uuid4().hex[:8]}.{ext}"
            
            # 저장 경로
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            
            # 기존 이미지 삭제 (있으면)
            if request.user.profile_image:
                old_path = os.path.join(settings.MEDIA_ROOT, request.user.profile_image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # 새 이미지 저장
            with open(filepath, 'wb+') as f:
                for chunk in image.chunks():
                    f.write(chunk)
            
            # DB에 경로 저장
            request.user.profile_image = f"profiles/{filename}"
            request.user.save(update_fields=['profile_image'])
            
            # 캐시 무효화
            cache_key = f'user_profile:{request.user.id}'
            cache.delete(cache_key)
            
            # 전체 URL 반환
            image_url = request.build_absolute_uri(
                f"{settings.MEDIA_URL}profiles/{filename}"
            )
            
            return Response({
                'data': {
                    'profile_image': request.user.profile_image,
                    'image_url': image_url,
                },
                'message': '프로필 이미지가 업로드되었습니다.'
            })
        
        return Response({
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '이미지 업로드 실패',
                'fields': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """프로필 이미지 삭제"""
        if request.user.profile_image:
            # 파일 삭제
            filepath = os.path.join(settings.MEDIA_ROOT, request.user.profile_image)
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # DB 업데이트
            request.user.profile_image = None
            request.user.save(update_fields=['profile_image'])
            
            # 캐시 무효화
            cache_key = f'user_profile:{request.user.id}'
            cache.delete(cache_key)
            
            return Response({
                'data': None,
                'message': '프로필 이미지가 삭제되었습니다.'
            })
        
        return Response({
            'error': {
                'code': 'NOT_FOUND',
                'message': '삭제할 프로필 이미지가 없습니다.'
            }
        }, status=status.HTTP_404_NOT_FOUND)


# ============================================
# 관리자 API
# ============================================
class AdminUserListView(ListAPIView):
    """
    관리자용 회원 목록 API
    
    GET /api/users/
    - 전체 회원 목록 조회
    - 페이징, 검색, 정렬 지원
    """
    queryset = User.objects.all().order_by('-sign_up_date')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 검색 (email, nickname)
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                models.Q(email__icontains=search) |
                models.Q(nickname__icontains=search)
            )
        
        # 권한 필터
        permission = self.request.query_params.get('permission', '')
        if permission:
            queryset = queryset.filter(permission=permission)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'data': response.data,
            'message': 'ok'
        })


class AdminUserDetailView(RetrieveAPIView):
    """
    관리자용 회원 상세 API
    
    GET /api/users/<id>/
    - 특정 회원 상세 조회
    """
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return Response({
            'data': response.data,
            'message': 'ok'
        })


class AdminUserUpdateView(APIView):
    """
    관리자용 회원 정보 수정 API
    
    PATCH /api/users/<id>/
    - 회원 정보 수정 (permission 변경 등)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': '사용자를 찾을 수 없습니다.'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AdminUserUpdateSerializer(
            user,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'data': AdminUserSerializer(user).data,
                'message': '사용자 정보가 수정되었습니다.'
            })
        
        return Response({
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '입력값을 확인해주세요.',
                'fields': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class AdminUserDeleteView(DestroyAPIView):
    """
    관리자용 회원 삭제 API
    
    DELETE /api/users/<id>/
    - 회원 삭제 (hard delete)
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # 자기 자신은 삭제 불가
        if instance.id == request.user.id:
            return Response({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': '자기 자신은 삭제할 수 없습니다.'
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        self.perform_destroy(instance)
        return Response({
            'data': None,
            'message': '사용자가 삭제되었습니다.'
        }, status=status.HTTP_200_OK)


# ============================================
# OAuth 취소 처리
# ============================================

def oauth_login_cancelled(request):
    """
    Google OAuth 로그인 취소 시 처리
    /accounts/3rdparty/login/cancelled/ 요청을 프론트엔드로 리다이렉트
    """
    return redirect('http://localhost:3000/')
