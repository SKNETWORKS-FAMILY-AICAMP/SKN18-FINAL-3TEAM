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

urlpatterns = [
    path('admin/', admin.site.urls),

    # ============================================
    # Google OAuth (django-allauth)
    # ============================================
    path('accounts/', include('allauth.urls')),

    # ============================================
    # App API Routes
    # Note: React frontend handles all UI routing
    # ============================================
    # 인증 API (로그인, 로그아웃, 토큰 등)
    path('api/', include('accounts.urls')),

    # 사용자 관리 API
    path('api/users/', include('users.urls')),

    # 검색 API
    path('api/search/', include('search.urls')),

    # 영상 API
    path('api/video/', include('video.urls')),
]
