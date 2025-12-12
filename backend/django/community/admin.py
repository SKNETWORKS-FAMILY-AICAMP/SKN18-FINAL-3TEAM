from django.contrib import admin
from .models import Comment, Reply, Likes


class AdminPermissionMixin:
    """
    permission='admin'인 사용자만 Django Admin에 접근 가능하도록 제한
    """
    def has_module_permission(self, request):
        """모듈 접근 권한: is_staff=True이고 permission='admin'인 경우만"""
        return (
            request.user.is_active and
            request.user.is_staff and
            request.user.permission == 'admin'
        )


@admin.register(Comment)
class CommentAdmin(AdminPermissionMixin, admin.ModelAdmin):
    """
    댓글 Admin 설정
    - permission='admin'인 사용자만 접근 가능
    """

    # 목록 페이지 설정
    list_display = ('id', 'user', 'video', 'short_content', 'comment_likes_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__nickname', 'video__title', 'comment_content')
    ordering = ('-created_at',)

    # 상세 페이지 필드셋
    fieldsets = (
        ('댓글 정보', {
            'fields': ('user', 'video', 'comment_content')
        }),
        ('통계', {
            'fields': ('comment_likes_count',)
        }),
        ('날짜', {
            'fields': ('created_at',)
        }),
    )

    # 읽기 전용 필드
    readonly_fields = ('created_at', 'comment_likes_count')

    # 페이지당 항목 수
    list_per_page = 25

    def short_content(self, obj):
        """댓글 내용을 30자로 축약해서 표시"""
        return obj.comment_content[:30] + '...' if len(obj.comment_content) > 30 else obj.comment_content
    short_content.short_description = '댓글 내용'


@admin.register(Reply)
class ReplyAdmin(AdminPermissionMixin, admin.ModelAdmin):
    """
    답글 Admin 설정
    - permission='admin'인 사용자만 접근 가능
    """

    # 목록 페이지 설정
    list_display = ('id', 'user', 'comment', 'short_content', 'parent_reply', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__nickname', 'comment__comment_content', 'reply_content')
    ordering = ('created_at',)

    # 상세 페이지 필드셋
    fieldsets = (
        ('답글 정보', {
            'fields': ('user', 'comment', 'reply_content', 'parent_reply')
        }),
        ('날짜', {
            'fields': ('created_at',)
        }),
    )

    # 읽기 전용 필드
    readonly_fields = ('created_at',)

    # 페이지당 항목 수
    list_per_page = 25

    def short_content(self, obj):
        """답글 내용을 30자로 축약해서 표시"""
        return obj.reply_content[:30] + '...' if len(obj.reply_content) > 30 else obj.reply_content
    short_content.short_description = '답글 내용'


@admin.register(Likes)
class LikesAdmin(AdminPermissionMixin, admin.ModelAdmin):
    """
    좋아요 Admin 설정
    - permission='admin'인 사용자만 접근 가능
    """

    # 목록 페이지 설정
    list_display = ('id', 'user', 'target_type', 'target_object', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__nickname')
    ordering = ('-created_at',)

    # 상세 페이지 필드셋
    fieldsets = (
        ('좋아요 정보', {
            'fields': ('user', 'video', 'comment', 'reply')
        }),
        ('날짜', {
            'fields': ('created_at',)
        }),
    )

    # 읽기 전용 필드
    readonly_fields = ('created_at',)

    # 페이지당 항목 수
    list_per_page = 30

    def target_type(self, obj):
        """좋아요 대상 타입 표시"""
        if obj.video:
            return '영상'
        elif obj.comment:
            return '댓글'
        elif obj.reply:
            return '답글'
        return '-'
    target_type.short_description = '대상 타입'

    def target_object(self, obj):
        """좋아요 대상 객체 표시"""
        target = obj.video or obj.comment or obj.reply
        if target:
            return str(target)[:50]
        return '-'
    target_object.short_description = '대상'
