from django.contrib import admin
from .models import Video


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


@admin.register(Video)
class VideoAdmin(AdminPermissionMixin, admin.ModelAdmin):
    """
    Video 모델 Admin 설정
    - permission='admin'인 사용자만 접근 가능
    """

    # 목록 페이지 설정
    list_display = ('id', 'title', 'upload_date', 'likes_count', 'comments_count', 'display_tags')
    list_filter = ('upload_date',)
    search_fields = ('title', 'tags')
    ordering = ('-upload_date',)

    # 상세 페이지 필드셋
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'tags')
        }),
        ('통계', {
            'fields': ('likes_count', 'comments_count')
        }),
        ('날짜', {
            'fields': ('upload_date',)
        }),
    )

    # 읽기 전용 필드
    readonly_fields = ('upload_date', 'likes_count', 'comments_count')

    # 페이지당 항목 수
    list_per_page = 25

    def display_tags(self, obj):
        """태그를 콤마로 구분해서 표시"""
        if obj.tags:
            return ', '.join(obj.tags[:3])  # 처음 3개만 표시
        return '-'
    display_tags.short_description = '태그'
