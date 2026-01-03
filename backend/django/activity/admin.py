from django.contrib import admin
from .models import WatchingHistory, SearchHistory


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


@admin.register(WatchingHistory)
class WatchingHistoryAdmin(AdminPermissionMixin, admin.ModelAdmin):
    """
    시청 기록 Admin 설정
    - permission='admin'인 사용자만 접근 가능
    """

    # 목록 페이지 설정
    list_display = ('id', 'user', 'video', 'watched_seconds', 'display_tags', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__nickname', 'video__title', 'tags')
    ordering = ('-created_at',)

    # 상세 페이지 필드셋
    fieldsets = (
        ('시청 정보', {
            'fields': ('user', 'video', 'watched_seconds')
        }),
        ('태그', {
            'fields': ('tags',)
        }),
        ('날짜', {
            'fields': ('created_at',)
        }),
    )

    # 읽기 전용 필드
    readonly_fields = ('created_at',)

    # 페이지당 항목 수
    list_per_page = 30

    def display_tags(self, obj):
        """태그를 콤마로 구분해서 표시"""
        if obj.tags:
            tags = [t.strip() for t in obj.tags.split(',') if t.strip()]
            return ', '.join(tags[:3])  # 처음 3개만 표시
        return '-'
    display_tags.short_description = '태그'


@admin.register(SearchHistory)
class SearchHistoryAdmin(AdminPermissionMixin, admin.ModelAdmin):
    """
    검색 기록 Admin 설정
    - permission='admin'인 사용자만 접근 가능
    """

    # 목록 페이지 설정
    list_display = ('id', 'user', 'search_query', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__nickname', 'search_query')
    ordering = ('-created_at',)

    # 상세 페이지 필드셋
    fieldsets = (
        ('검색 정보', {
            'fields': ('user', 'search_query')
        }),
        ('날짜', {
            'fields': ('created_at',)
        }),
    )

    # 읽기 전용 필드
    readonly_fields = ('created_at',)

    # 페이지당 항목 수
    list_per_page = 30
