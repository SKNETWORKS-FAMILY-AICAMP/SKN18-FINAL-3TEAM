from django.db import models
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
        queryset = WatchingHistory.objects.filter(user=self.request.user).select_related('video').order_by('-created_at')
        video_id = self.request.query_params.get('video_id')
        if video_id:
            return queryset.filter(video_id=video_id)
        return queryset

    def get_serializer_class(self):
        # GET: 조회용 Serializer, POST: 생성용 Serializer
        if self.request.method == 'POST':
            return WatchingHistoryCreateSerializer
        return WatchingHistorySerializer

    def list(self, request, *args, **kwargs):
        video_id = request.query_params.get('video_id')
        if video_id:
            record = self.get_queryset().order_by('-created_at').first()
            data = WatchingHistorySerializer(record).data if record else None
            return Response({
                'data': data,
                'message': 'ok'
            })

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
            "recommended_keyword": ["rec1", "rec2", ..., "rec8"]
        },
        "message": "ok"
    }

    Logic:
    - tag: 최근 시청 기록에서 2-3개
    - video_keyword: 최근 시청 영상별 1개씩, 최대 3개
    - recommended_keyword: 최근 시청 영상에서 8개
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
                'recommended_keyword': []
            },
            'message': '시청 기록이 없습니다.'
        })

    # 1. tag 수집 (시청 기록의 tags 필드에서)
    # DB에 해당 태그를 가진 영상이 있는 경우만 포함
    from video.models import Video

    all_tag = []
    for watch in recent_watches:
        if watch.tags:
            # tags는 쉼표로 구분된 문자열이므로 split 후 extend
            tag_list = [t.strip() for t in watch.tags.split(',') if t.strip()]
            all_tag.extend(tag_list)

    # 중복 제거 및 최대 3개 (DB에 영상이 있는 태그만)
    unique_tag = []
    for tag in all_tag:
        if tag not in unique_tag:
            # 해당 태그를 가진 영상이 DB에 존재하는지 확인
            if Video.objects.filter(tags__icontains=tag).exists():
                unique_tag.append(tag)
        if len(unique_tag) >= 3:
            break

    # 2. video_keyword 수집 (영상별 1개씩, 최대 3개)
    # DB에 해당 키워드를 가진 영상이 있는 경우만 포함
    # 중복 제거를 위한 set 사용
    video_keyword_set = set()
    video_keyword_list = []

    for watch in recent_watches:
        if watch.video_keyword:
            # watching_history의 video_keyword 필드에서 직접 가져옴
            keywords = [k.strip() for k in watch.video_keyword.split(',') if k.strip()]
            for keyword in keywords:
                if keyword not in video_keyword_set:
                    # 해당 키워드를 가진 영상이 DB에 존재하는지 확인
                    if Video.objects.filter(video_keyword__icontains=keyword).exists():
                        video_keyword_set.add(keyword)
                        video_keyword_list.append(keyword)
                        break  # 영상별 1개만
                if len(video_keyword_list) >= 3:
                    break
        if len(video_keyword_list) >= 3:
            break

    # 3. recommended_keyword 수집 (최대 8개)
    # 추천 키워드가 다른 영상의 video_keyword에만 존재하는 경우만 포함
    # video_keyword와 중복되지 않고, recommended_keyword끼리도 중복 제거
    recommended_keyword_set = set(video_keyword_set)  # video_keyword와 중복 방지
    recommended_keyword_list = []

    for watch in recent_watches:
        if watch.recommended_keyword:
            # watching_history의 recommended_keyword 필드에서 직접 가져옴
            keywords = [k.strip() for k in watch.recommended_keyword.split(',') if k.strip()]
            for kw in keywords:
                if kw not in recommended_keyword_set:
                    # 해당 키워드가 다른 영상의 video_keyword에만 존재하는지 확인
                    # (추천 키워드나 태그에만 있으면 안 됨)
                    if Video.objects.filter(video_keyword__icontains=kw).exists():
                        recommended_keyword_set.add(kw)
                        recommended_keyword_list.append(kw)
                if len(recommended_keyword_list) >= 8:
                    break
            if len(recommended_keyword_list) >= 8:
                break

    return Response({
        'data': {
            'tag': unique_tag[:3],
            'video_keyword': video_keyword_list[:3],
            'recommended_keyword': recommended_keyword_list[:8]
        },
        'message': 'ok'
    })
