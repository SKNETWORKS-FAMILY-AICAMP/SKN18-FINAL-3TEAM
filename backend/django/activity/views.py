from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListCreateAPIView

from .models import WatchingHistory, SearchHistory
from .serializers import (
    WatchingHistorySerializer,
    WatchingHistoryCreateSerializer,
    SearchHistorySerializer,
    SearchHistoryCreateSerializer,
)


# ============================================
# 검색 기록 API (GET + POST)
# ============================================

class SearchHistoryListCreateView(ListCreateAPIView):
    """
    검색 기록 조회/적재 API

    GET /api/activity/search-logs/  - 내 검색 기록 조회
    POST /api/activity/search-logs/ - 검색 기록 적재
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user).order_by('-created_at')

    def get_serializer_class(self):
        # GET: 조회용 Serializer, POST: 생성용 Serializer
        if self.request.method == 'POST':
            return SearchHistoryCreateSerializer
        return SearchHistorySerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'data': response.data,
            'message': 'ok'
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'data': serializer.data,
                'message': '검색 기록이 저장되었습니다.'
            }, status=status.HTTP_201_CREATED)

        return Response({
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '입력값을 확인해주세요.',
                'fields': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# 시청 기록 API (GET + POST)
# ============================================

class WatchingHistoryListCreateView(ListCreateAPIView):
    """
    시청 기록 조회/적재 API

    GET /api/activity/watch-logs/  - 내 시청 기록 조회
    POST /api/activity/watch-logs/ - 시청 기록 적재
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WatchingHistory.objects.filter(user=self.request.user).select_related('video').order_by('-created_at')

    def get_serializer_class(self):
        # GET: 조회용 Serializer, POST: 생성용 Serializer
        if self.request.method == 'POST':
            return WatchingHistoryCreateSerializer
        return WatchingHistorySerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'data': response.data,
            'message': 'ok'
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'data': serializer.data,
                'message': '시청 기록이 저장되었습니다.'
            }, status=status.HTTP_201_CREATED)

        return Response({
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '입력값을 확인해주세요.',
                'fields': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# 시청 기록 기반 추천 키워드 API
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommended_keyword(request):
    """
    시청 기록 기반 추천 키워드 반환

    GET /api/activity/recommended-keyword/

    Response:
    {
        "data": {
            "tag": ["tag1", "tag2", "tag3"],
            "video_keyword": ["keyword1", "keyword2", "keyword3"],
            "recommend_keyword": ["rec1", "rec2", ..., "rec8"]
        },
        "message": "ok"
    }

    Logic:
    - tag: 최근 시청 기록에서 2-3개
    - video_keyword: 최근 시청 영상별 1개씩, 최대 3개
    - recommend_keyword: 최근 시청 영상에서 8개
    """
    user = request.user

    # 최근 시청 기록 조회 (최대 10개 영상)
    recent_watches = WatchingHistory.objects.filter(
        user=user
    ).select_related('video').order_by('-created_at')[:10]

    if not recent_watches:
        return Response({
            'data': {
                'tag': [],
                'video_keyword': [],
                'recommend_keyword': []
            },
            'message': '시청 기록이 없습니다.'
        })

    # 1. tag 수집 (시청 기록의 tags 필드에서)
    all_tag = []
    for watch in recent_watches:
        if watch.tags:
            all_tag.extend(watch.tags)

    # 중복 제거 및 최대 3개
    unique_tag = []
    for tag in all_tag:
        if tag not in unique_tag:
            unique_tag.append(tag)
        if len(unique_tag) >= 3:
            break

    # 2. video_keyword 수집 (영상별 1개씩, 최대 3개)
    video_keyword_list = []
    for watch in recent_watches:
        if watch.video and hasattr(watch.video, 'video_keyword') and watch.video.video_keyword:
            # 쉼표로 구분된 문자열에서 첫 번째 키워드만 추출
            keyword = [k.strip() for k in watch.video.video_keyword.split(',') if k.strip()]
            if keyword and keyword[0] not in video_keyword_list:
                video_keyword_list.append(keyword[0])
            if len(video_keyword_list) >= 3:
                break

    # 3. recommend_keyword 수집 (최대 8개)
    recommend_keyword_list = []
    for watch in recent_watches:
        if watch.video and hasattr(watch.video, 'recommend_keyword') and watch.video.recommend_keyword:
            # 쉼표로 구분된 문자열 파싱
            keyword = [k.strip() for k in watch.video.recommend_keyword.split(',') if k.strip()]
            for kw in keyword:
                if kw not in recommend_keyword_list:
                    recommend_keyword_list.append(kw)
                if len(recommend_keyword_list) >= 8:
                    break
            if len(recommend_keyword_list) >= 8:
                break

    return Response({
        'data': {
            'tag': unique_tag[:3],
            'video_keyword': video_keyword_list[:3],
            'recommend_keyword': recommend_keyword_list[:8]
        },
        'message': 'ok'
    })
