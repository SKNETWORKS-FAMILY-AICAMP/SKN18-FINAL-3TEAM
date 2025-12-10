import os
import uuid
from django.conf import settings
from django.db import models
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, DestroyAPIView

from .models import User
from .serializers import (
    ProfileSerializer,
    ProfileUpdateSerializer,
    ProfileImageSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
)


# ============================================
# 커스텀 권한 클래스
# ============================================
from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """관리자(permission='admin')만 접근 가능"""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.permission == 'admin'
        )


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
        """내 프로필 조회"""
        serializer = ProfileSerializer(request.user)
        return Response({
            'data': serializer.data,
            'message': 'ok'
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
