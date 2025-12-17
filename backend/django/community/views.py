from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import DestroyAPIView, UpdateAPIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from video.models import Video
from .models import Comment, Reply, Likes
from .serializers import (
    CommentSerializer,
    CommentCreateSerializer,
    ReplySerializer,
    ReplyCreateSerializer,
    LikesSerializer,
    UserActivitySerializer,
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


class IsOwnerOrAdmin(BasePermission):
    """
    작성자 본인 또는 관리자만 삭제 가능
    """
    def has_object_permission(self, request, view, obj):
        # Admin은 모든 댓글/답글 삭제 가능
        if request.user.permission == 'admin':
            return True
        # 작성자 본인만 자신의 댓글/답글 삭제 가능
        return obj.user == request.user


# ============================================
# 댓글 API
# ============================================

class VideoCommentView(APIView):
    """
    영상 댓글 API

    GET /api/community/videos/{video_id}/comments/
    - 댓글 목록 조회 (최신순 정렬)

    POST /api/community/videos/{video_id}/comments/
    - 댓글 작성
    - request body: {"comment_content": "댓글 내용"}
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="댓글 목록 조회",
        description="특정 영상의 댓글 목록을 최신순으로 조회합니다.",
        responses={200: CommentSerializer(many=True)},
        tags=["댓글"]
    )
    def get(self, request, video_id):
        """댓글 목록 조회"""
        comments = Comment.objects.filter(
            video_id=video_id
        ).select_related('user', 'video').prefetch_related('replies__user', 'likes').order_by('-created_at')

        serializer = CommentSerializer(comments, many=True, context={'request': request})
        return Response({
            'data': serializer.data,
            'message': 'ok'
        })

    @extend_schema(
        summary="댓글 작성",
        description="영상에 댓글을 작성합니다.",
        request=CommentCreateSerializer,
        responses={201: CommentSerializer},
        tags=["댓글"]
    )
    def post(self, request, video_id):
        """댓글 작성"""
        video = get_object_or_404(Video, id=video_id)
        serializer = CommentCreateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user, video=video)
            return Response({
                'data': CommentSerializer(serializer.instance, context={'request': request}).data,
                'message': '댓글이 작성되었습니다.'
            }, status=status.HTTP_201_CREATED)

        return Response({
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '입력값을 확인해주세요.',
                'fields': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# 답글 API
# ============================================

class CommentReplyView(APIView):
    """
    댓글 답글 API

    GET /api/community/comments/{comment_id}/replies/
    - 답글 목록 조회 (오래된 순 정렬)

    POST /api/community/comments/{comment_id}/replies/
    - 답글 작성
    - request body: {"reply_content": "답글 내용", "parent_reply": 1} (parent_reply는 선택)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="답글 목록 조회",
        description="특정 댓글의 답글 목록을 오래된 순으로 조회합니다.",
        responses={200: ReplySerializer(many=True)},
        tags=["답글"]
    )
    def get(self, request, comment_id):
        """답글 목록 조회 (최상위 답글만, 자식은 재귀적으로 포함)"""
        # 최상위 답글만 가져오기 (parent_reply가 없는 것들)
        replies = Reply.objects.filter(
            comment_id=comment_id,
            parent_reply__isnull=True
        ).select_related('user', 'comment').prefetch_related('child_replies__user', 'likes').order_by('created_at')

        serializer = ReplySerializer(replies, many=True, context={'request': request})
        return Response({
            'data': serializer.data,
            'message': 'ok'
        })

    @extend_schema(
        summary="답글 작성",
        description="댓글에 답글을 작성합니다.",
        request=ReplyCreateSerializer,
        responses={201: ReplySerializer},
        tags=["답글"]
    )
    def post(self, request, comment_id):
        """답글 작성"""
        comment = get_object_or_404(Comment, id=comment_id)
        serializer = ReplyCreateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user, comment=comment)
            return Response({
                'data': ReplySerializer(serializer.instance, context={'request': request}).data,
                'message': '답글이 작성되었습니다.'
            }, status=status.HTTP_201_CREATED)

        return Response({
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '입력값을 확인해주세요.',
                'fields': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# 관리자 API (댓글/답글 삭제)
# ============================================

class CommentUpdateView(UpdateAPIView):
    """
    댓글 수정 API
    - 작성자 본인 또는 관리자만 수정 가능

    PATCH /api/community/comments/{comment_id}/
    """
    queryset = Comment.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = CommentCreateSerializer
    lookup_url_kwarg = 'comment_id'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # 수정된 댓글을 CommentSerializer로 반환
        updated_comment = CommentSerializer(instance, context={'request': request})
        return Response({
            'data': updated_comment.data,
            'message': '댓글이 수정되었습니다.'
        }, status=status.HTTP_200_OK)


class CommentDeleteView(DestroyAPIView):
    """
    댓글 삭제 API
    - 작성자 본인 또는 관리자만 삭제 가능

    DELETE /api/community/comments/{comment_id}/
    """
    queryset = Comment.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    lookup_url_kwarg = 'comment_id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'data': None,
            'message': '댓글이 삭제되었습니다.'
        }, status=status.HTTP_200_OK)


class ReplyDeleteView(DestroyAPIView):
    """
    답글 삭제 API
    - 작성자 본인 또는 관리자만 삭제 가능

    DELETE /api/community/replies/{reply_id}/
    """
    queryset = Reply.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    lookup_url_kwarg = 'reply_id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'data': None,
            'message': '답글이 삭제되었습니다.'
        }, status=status.HTTP_200_OK)


# ============================================
# 좋아요 API
# ============================================

class VideoLikeView(APIView):
    """
    영상 좋아요 추가/삭제 API

    POST /api/community/videos/{video_id}/like/ - 좋아요 추가
    DELETE /api/community/videos/{video_id}/like/ - 좋아요 삭제
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, video_id):
        video = get_object_or_404(Video, id=video_id)

        # 이미 좋아요가 있는지 확인
        existing_like = Likes.objects.filter(user=request.user, video=video).first()
        if existing_like:
            return Response({
                'error': {
                    'code': 'ALREADY_LIKED',
                    'message': '이미 좋아요를 눌렀습니다.'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # 좋아요 추가
        like = Likes.objects.create(user=request.user, video=video)

        # 좋아요 수 증가
        video.likes_count += 1
        video.save(update_fields=['likes_count'])

        return Response({
            'data': LikesSerializer(like).data,
            'message': '좋아요가 추가되었습니다.'
        }, status=status.HTTP_201_CREATED)

    def delete(self, request, video_id):
        video = get_object_or_404(Video, id=video_id)

        # 좋아요 찾기
        like = Likes.objects.filter(user=request.user, video=video).first()
        if not like:
            return Response({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': '좋아요를 찾을 수 없습니다.'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        # 좋아요 삭제
        like.delete()

        # 좋아요 수 감소
        video.likes_count = max(0, video.likes_count - 1)
        video.save(update_fields=['likes_count'])

        return Response({
            'data': None,
            'message': '좋아요가 삭제되었습니다.'
        }, status=status.HTTP_200_OK)


class CommentLikeView(APIView):
    """
    댓글 좋아요 추가/삭제 API

    POST /api/community/comments/{comment_id}/like/ - 좋아요 추가
    DELETE /api/community/comments/{comment_id}/like/ - 좋아요 삭제
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)

        # 이미 좋아요가 있는지 확인
        existing_like = Likes.objects.filter(user=request.user, comment=comment).first()
        if existing_like:
            return Response({
                'error': {
                    'code': 'ALREADY_LIKED',
                    'message': '이미 좋아요를 눌렀습니다.'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # 좋아요 추가
        like = Likes.objects.create(user=request.user, comment=comment)

        # 좋아요 수 증가
        comment.comment_likes_count += 1
        comment.save(update_fields=['comment_likes_count'])

        return Response({
            'data': LikesSerializer(like).data,
            'message': '좋아요가 추가되었습니다.'
        }, status=status.HTTP_201_CREATED)

    def delete(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)

        # 좋아요 찾기
        like = Likes.objects.filter(user=request.user, comment=comment).first()
        if not like:
            return Response({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': '좋아요를 찾을 수 없습니다.'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        # 좋아요 삭제
        like.delete()

        # 좋아요 수 감소
        comment.comment_likes_count = max(0, comment.comment_likes_count - 1)
        comment.save(update_fields=['comment_likes_count'])

        return Response({
            'data': None,
            'message': '좋아요가 삭제되었습니다.'
        }, status=status.HTTP_200_OK)


class ReplyLikeView(APIView):
    """
    답글 좋아요 추가/삭제 API

    POST /api/community/replies/{reply_id}/like/ - 좋아요 추가
    DELETE /api/community/replies/{reply_id}/like/ - 좋아요 삭제
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, reply_id):
        reply = get_object_or_404(Reply, id=reply_id)

        # 이미 좋아요가 있는지 확인
        existing_like = Likes.objects.filter(user=request.user, reply=reply).first()
        if existing_like:
            return Response({
                'error': {
                    'code': 'ALREADY_LIKED',
                    'message': '이미 좋아요를 눌렀습니다.'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # 좋아요 추가
        like = Likes.objects.create(user=request.user, reply=reply)

        return Response({
            'data': LikesSerializer(like).data,
            'message': '좋아요가 추가되었습니다.'
        }, status=status.HTTP_201_CREATED)

    def delete(self, request, reply_id):
        reply = get_object_or_404(Reply, id=reply_id)

        # 좋아요 찾기
        like = Likes.objects.filter(user=request.user, reply=reply).first()
        if not like:
            return Response({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': '좋아요를 찾을 수 없습니다.'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        # 좋아요 삭제
        like.delete()

        return Response({
            'data': None,
            'message': '좋아요가 삭제되었습니다.'
        }, status=status.HTTP_200_OK)


# ============================================
# 사용자 커뮤니티 활동 API
# ============================================

class UserActivityView(APIView):
    """
    내 커뮤니티 활동 내역 조회 API

    GET /api/community/me/activities/
    - 내가 작성한 댓글, 답글, 좋아요 목록
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 내가 작성한 댓글
        comments = Comment.objects.filter(user=user).select_related('video').order_by('-created_at')

        # 내가 작성한 답글
        replies = Reply.objects.filter(user=user).select_related('comment').order_by('-created_at')

        # 내가 누른 좋아요
        likes = Likes.objects.filter(user=user).select_related('video', 'comment', 'reply').order_by('-created_at')

        serializer = UserActivitySerializer({
            'comments': comments,
            'replies': replies,
            'likes': likes,
        })

        return Response({
            'data': serializer.data,
            'message': 'ok'
        })
