from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from users.views import oauth_login_cancelled

urlpatterns = [
    path('health/', lambda request: HttpResponse('ok'), name='health'),
    path('admin/', admin.site.urls),

    # OAuth 취소 처리 (allauth.urls보다 먼저 선언하여 오버라이드)
    path('accounts/3rdparty/login/cancelled/', oauth_login_cancelled, name='socialaccount_login_cancelled'),

    path('accounts/', include('allauth.urls')),

    # 인증/계정 API
    path('api/', include('users.urls')),

    # 사용자 관리 API
    path('api/users/', include('users.urls')),

    # 검색 API
    path('api/search/', include('search.urls')),

    # 영상/LLM 관련 API
    path('api/video/', include('video.urls')),

    # 검색 + 시청 기록 API
    path('api/activity/', include('activity.urls')),

    # 댓글 + 답글 + 좋아요 API
    path('api/community/', include('community.urls')),
    # 챗봇 API
    path('api/chatbot/', include('chatbot.urls')),
    path('api/chat/', include('chatbot.urls')),

    # API 문서화
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
]

# 개발 환경에서 media 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
