from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

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

    # 검색 + 시청 기록 API
    path('api/activity/', include('activity.urls')),

    # 댓글 + 답글 + 좋아요 API
    path('api/community/', include('community.urls')),

    # API 문서화
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
]

# 개발 환경에서 media 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
