from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


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


@admin.register(User)
class UserAdmin(AdminPermissionMixin, BaseUserAdmin):
    """
    User 모델 Admin 설정
    - permission='admin'인 사용자만 접근 가능
    """

    # 목록 페이지 설정
    list_display = ('email', 'nickname', 'permission', 'is_staff', 'is_active', 'sign_up_date')
    list_filter = ('permission', 'is_staff', 'is_active', 'gender')
    search_fields = ('email', 'nickname')
    ordering = ('-sign_up_date',)

    # 상세 페이지 필드셋
    fieldsets = (
        ('기본 정보', {
            'fields': ('email', 'nickname', 'profile_image')
        }),
        ('권한', {
            'fields': ('permission', 'is_staff', 'is_active', 'is_superuser')
        }),
        ('개인 정보', {
            'fields': ('gender', 'age')
        }),
        ('중요 날짜', {
            'fields': ('sign_up_date', 'last_login')
        }),
    )

    # 사용자 추가 페이지 필드셋
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'permission', 'is_staff', 'is_active'),
        }),
    )

    # 읽기 전용 필드
    readonly_fields = ('sign_up_date', 'last_login')

    # 필터 사이드바
    list_per_page = 20

    # groups와 user_permissions를 User 모델에서 None으로 설정했으므로
    # filter_horizontal을 빈 튜플로 오버라이드
    filter_horizontal = ()
