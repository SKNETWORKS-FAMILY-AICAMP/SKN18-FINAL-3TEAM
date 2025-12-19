from django.urls import path
from .views import (
    VideoCommentView,
    CommentReplyView,
    CommentUpdateView,
    CommentDeleteView,
    ReplyUpdateView,
    ReplyDeleteView,
    VideoLikeView,
    CommentLikeView,
    ReplyLikeView,
    UserActivityView,
)

# community 앱 URL 패턴
# 댓글 + 답글 + 좋아요 관리

urlpatterns = [
    # ============================================
    # 댓글 API
    # ============================================
    # GET /api/community/videos/<video_id>/comments/ - 영상별 댓글 목록
    # POST /api/community/videos/<video_id>/comments/ - 댓글 작성
    path('videos/<int:video_id>/comments/', VideoCommentView.as_view(), name='video-comments'),

    # ============================================
    # 답글 API
    # ============================================
    # GET /api/community/comments/<comment_id>/replies/ - 댓글별 답글 목록
    # POST /api/community/comments/<comment_id>/replies/ - 답글 작성
    path('comments/<int:comment_id>/replies/', CommentReplyView.as_view(), name='comment-replies'),

    # ============================================
    # 댓글 수정/삭제 API (작성자 본인 또는 관리자)
    # ============================================
    # PATCH /api/community/comments/<comment_id>/ - 댓글 수정
    # DELETE /api/community/comments/<comment_id>/delete/ - 댓글 삭제
    path('comments/<int:comment_id>/', CommentUpdateView.as_view(), name='comment-update'),
    path('comments/<int:comment_id>/delete/', CommentDeleteView.as_view(), name='comment-delete'),

    # PATCH /api/community/replies/<reply_id>/update/ - 답글 수정
    # DELETE /api/community/replies/<reply_id>/ - 답글 삭제
    path('replies/<int:reply_id>/update/', ReplyUpdateView.as_view(), name='reply-update'),
    path('replies/<int:reply_id>/', ReplyDeleteView.as_view(), name='reply-delete'),

    # ============================================
    # 좋아요 API
    # ============================================
    # POST/DELETE /api/community/videos/<video_id>/like/ - 영상 좋아요
    path('videos/<int:video_id>/like/', VideoLikeView.as_view(), name='video-like'),

    # POST/DELETE /api/community/comments/<comment_id>/like/ - 댓글 좋아요
    path('comments/<int:comment_id>/like/', CommentLikeView.as_view(), name='comment-like'),

    # POST/DELETE /api/community/replies/<reply_id>/like/ - 답글 좋아요
    path('replies/<int:reply_id>/like/', ReplyLikeView.as_view(), name='reply-like'),

    # ============================================
    # 사용자 커뮤니티 활동 API
    # ============================================
    # GET /api/community/me/activities/ - 내 커뮤니티 활동 내역
    path('me/activities/', UserActivityView.as_view(), name='user-activities'),
]
