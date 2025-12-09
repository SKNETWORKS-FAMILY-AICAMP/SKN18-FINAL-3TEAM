from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),

    # 인증/계정 API
    path('api/', include('accounts.urls')),

    # 사용자 관리 API
    path('api/users/', include('users.urls')),

    # 검색 API
    path('api/search/', include('search.urls')),

    # 영상/LLM 관련 API
    path('api/video/', include('video.urls')),
]
