from django.contrib import admin

# 로그인한 사용자만 접근 가능하도록 설정
class ChatbotAccess:
    def has_module_permission(self, request):
        return request.user.is_authenticated
