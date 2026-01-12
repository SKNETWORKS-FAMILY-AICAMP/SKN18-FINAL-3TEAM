"""
공통 권한 클래스 모음
"""
from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    관리자(permission='admin')만 접근 가능
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.permission == 'admin'
        )
