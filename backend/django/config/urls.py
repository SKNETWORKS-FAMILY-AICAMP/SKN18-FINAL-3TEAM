"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.contrib.auth import logout
from django.views.decorators.csrf import csrf_exempt

# 인증 상태 확인 API
def check_auth(request):
    if request.user.is_authenticated:
        user = request.user
        # username이 없으면 email 사용
        display_name = user.username if user.username else user.email

        return JsonResponse({
            'isAuthenticated': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': display_name,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })
    return JsonResponse({'isAuthenticated': False})

# 로그아웃 API (CSRF 제외)
@csrf_exempt
def logout_view(request):
    logout(request)
    return JsonResponse({'message': 'Logged out successfully'})

urlpatterns = [
    path('admin/', admin.site.urls),

    # API 엔드포인트
    path('api/check-auth/', check_auth, name='check_auth'),
    path('api/logout/', logout_view, name='logout'),

    path('', include('home.urls')),        # 메인 홈
    path('login/', include('login.urls')), # 로그인 페이지(UI)
    path('search/', include('search.urls')),
    path('video/', include('video.urls')),
    path('mypage/', include('mypage.urls')),

    path('accounts/', include('allauth.urls')),  # Google OAuth
]