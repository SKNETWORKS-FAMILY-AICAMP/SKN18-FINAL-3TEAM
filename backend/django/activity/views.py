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

    # 디버깅: 시청 기록의 실제 데이터 확인
    print(f"\n[추천 키워드 API] 시청 기록 개수: {len(recent_watches)}")
    for i, watch in enumerate(recent_watches[:3]):
        print(f"  [{i+1}] 영상: {watch.video.title if watch.video else 'None'}")
        print(f"      - watch.tags: {watch.tags}")
        print(f"      - watch.video_keyword: {watch.video_keyword}")
        print(f"      - watch.recommended_keyword: {watch.recommended_keyword}")
        if watch.video:
            print(f"      - video.tags: {watch.video.tags}")
            print(f"      - video.video_keyword: {watch.video.video_keyword}")
            print(f"      - video.recommended_keyword: {watch.video.recommended_keyword}")

    # 시청한 영상 ID 목록 (추천 키워드에서 제외하기 위함)
    from video.models import Video
    watched_video_ids = set(watch.video.id for watch in recent_watches if watch.video)

    # 1. tag 수집 (최근 3개 영상에서 각 1개씩, 총 3개)
    unique_tag = []
    used_tags = set()

    for watch in recent_watches[:3]:  # 최근 3개 영상만
        if watch.tags and len(unique_tag) < 3:
            tag_list = [t.strip() for t in watch.tags.split(',') if t.strip()]
            for tag in tag_list:
                if tag not in used_tags:
                    # 시청 기록의 태그가 다른 영상의 tags(ArrayField)와 매칭되는지 확인
                    if Video.objects.filter(tags__contains=[tag]).exists():
                        unique_tag.append(tag)
                        used_tags.add(tag)
                        break  # 영상별 1개만

    # 2. video_keyword 수집 (최근 2개 영상에서 각 1개씩, 총 2개)
    video_keyword_list = []
    used_video_keywords = set()

    for watch in recent_watches[:2]:  # 최근 2개 영상만
        if watch.video_keyword and len(video_keyword_list) < 2:
            keywords = [k.strip() for k in watch.video_keyword.split(',') if k.strip()]
            for keyword in keywords:
                if keyword not in used_video_keywords and keyword not in used_tags:
                    # 시청 기록의 video_keyword가 다른 영상의 video_keyword와 매칭되는지 확인
                    if Video.objects.filter(video_keyword__icontains=keyword).exists():
                        video_keyword_list.append(keyword)
                        used_video_keywords.add(keyword)
                        break  # 영상별 1개만

    # 3. recommended_keyword 수집 (최근 시청부터 영상 상관없이 5개)
    recommended_keyword_list = []
    used_recommended_keywords = set(used_tags | used_video_keywords)

    for watch in recent_watches:
        if watch.recommended_keyword and len(recommended_keyword_list) < 5:
            keywords = [k.strip() for k in watch.recommended_keyword.split(',') if k.strip()]
            for kw in keywords:
                if kw not in used_recommended_keywords:
                    # 시청 기록의 recommended_keyword가 다른 영상의 video_keyword와 매칭되는지 확인
                    if Video.objects.filter(video_keyword__icontains=kw).exists():
                        recommended_keyword_list.append(kw)
                        used_recommended_keywords.add(kw)
                        if len(recommended_keyword_list) >= 5:
                            break

    # 디버깅: 수집된 키워드 출력
    print(f"[추천 키워드 API] tag: {unique_tag}")
    print(f"[추천 키워드 API] video_keyword: {video_keyword_list}")
    print(f"[추천 키워드 API] recommended_keyword: {recommended_keyword_list}")
    print(f"[추천 키워드 API] 총 개수: {len(unique_tag) + len(video_keyword_list) + len(recommended_keyword_list)}")

    return Response({
        'data': {
            'tag': unique_tag,
            'video_keyword': video_keyword_list,
            'recommended_keyword': recommended_keyword_list
        },
        'message': 'ok'
    })


# ============================================
# 시청 기록 기반 추천 영상 API
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommended_videos(request):
    """
    최근 시청 기록 기반 추천 영상 반환

    정확도순 기준:
    1순위: recommended_keyword 매칭
    2순위: video_keyword 매칭
    3순위: tags 매칭
    같은 순위 내에서는 최신 영상 우선

    GET /api/activity/recommended-videos/

    Response:
    {
        "data": [
            {
                "id": 1,
                "title": "영상 제목",
                "tags": ["tag1", "tag2"],
                "thumbnail_url": "url",
                ...
            },
            ...
        ],
        "message": "ok"
    }
    """
    from video.models import Video
    from video.serializers import VideoSerializer
    from django.db.models import Q, Case, When, IntegerField

    user = request.user

    # 최근 시청 기록 조회 (최대 10개)
    recent_watches = WatchingHistory.objects.filter(
        user=user
    ).select_related('video').order_by('-created_at')[:10]

    if not recent_watches:
        return Response({
            'data': [],
            'message': '시청 기록이 없습니다.'
        })

    # 시청한 영상 ID 목록 (중복 제거)
    watched_video_ids = set(watch.video.id for watch in recent_watches)

    # recommended_keyword 수집 (시청 기록의 스냅샷 값 = 사용자 취향)
    recommended_keywords = []
    for watch in recent_watches:
        if watch.recommended_keyword:
            keywords = [k.strip() for k in watch.recommended_keyword.split(',') if k.strip()]
            recommended_keywords.extend(keywords)

    # video_keyword 수집 (시청 기록의 스냅샷 값 = 사용자 취향)
    video_keywords = []
    for watch in recent_watches:
        if watch.video_keyword:
            keywords = [k.strip() for k in watch.video_keyword.split(',') if k.strip()]
            video_keywords.extend(keywords)

    # 태그 수집 (시청 기록의 스냅샷 값 = 사용자 취향)
    tags = []
    for watch in recent_watches:
        if watch.tags:
            tag_list = [t.strip() for t in watch.tags.split(',') if t.strip()]
            tags.extend(tag_list)

    # 정확도순 매칭 점수 계산
    # 모든 키워드(recommended_keyword, video_keyword)를 다른 영상의 video_keyword와 매칭
    # 1순위: 시청한 영상의 recommended_keyword와 매칭 (300-280점)
    # 2순위: 시청한 영상의 video_keyword와 매칭 (200-180점)
    # 3순위: 시청한 영상의 tags와 매칭 (100-80점)
    recommended_keyword_whens = []
    for idx, kw in enumerate(recommended_keywords[:20]):
        recommended_keyword_whens.append(
            When(video_keyword__icontains=kw, then=300 - idx)
        )

    video_keyword_whens = []
    for idx, kw in enumerate(video_keywords[:20]):
        video_keyword_whens.append(
            When(video_keyword__icontains=kw, then=200 - idx)
        )

    tag_whens = []
    for idx, tag in enumerate(tags[:20]):
        tag_whens.append(
            When(tags__contains=[tag], then=100 - idx)
        )

    # 쿼리 필터 구성
    # - recommended_keyword, video_keyword → video_keyword와 매칭
    # - tags → tags와 매칭
    q_filter = Q()
    for kw in recommended_keywords[:20]:
        q_filter |= Q(video_keyword__icontains=kw)
    for kw in video_keywords[:20]:
        q_filter |= Q(video_keyword__icontains=kw)
    for tag in tags[:20]:
        q_filter |= Q(tags__contains=[tag])

    # 키워드/태그가 하나도 없으면 빈 배열 반환
    if not (recommended_keywords or video_keywords or tags):
        return Response({
            'data': [],
            'message': '추천할 영상이 없습니다.'
        })

    # 디버깅: 수집된 키워드 출력
    print(f"[추천 영상 API] recommended_keywords: {recommended_keywords[:5]}")
    print(f"[추천 영상 API] video_keywords: {video_keywords[:5]}")
    print(f"[추천 영상 API] tags: {tags[:5]}")

    # 점수 기반으로 정렬 (높은 점수 우선, 같은 점수면 최신 영상 우선)
    videos = Video.objects.filter(q_filter).exclude(
        id__in=watched_video_ids
    ).annotate(
        recommended_score=Case(*recommended_keyword_whens, default=0, output_field=IntegerField()) if recommended_keyword_whens else Case(default=0, output_field=IntegerField()),
        video_keyword_score=Case(*video_keyword_whens, default=0, output_field=IntegerField()) if video_keyword_whens else Case(default=0, output_field=IntegerField()),
        tag_score=Case(*tag_whens, default=0, output_field=IntegerField()) if tag_whens else Case(default=0, output_field=IntegerField()),
    ).order_by('-recommended_score', '-video_keyword_score', '-tag_score', '-upload_date').distinct()[:20]

    # 디버깅: 매칭된 영상의 점수 출력
    print(f"[추천 영상 API] 매칭된 영상 수: {videos.count()}")
    for v in videos[:5]:
        print(f"  - {v.title}: recommended={v.recommended_score}, video_keyword={v.video_keyword_score}, tag={v.tag_score}, video_keyword필드={v.video_keyword}")

    serializer = VideoSerializer(videos, many=True)

    return Response({
        'data': serializer.data,
        'message': 'ok'
    })


# ============================================
# 시청 기록 분석 API
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_watching_analytics(request):
    """
    시청 기록 기반 분석 데이터 반환
    
    video_keyword와 tags를 분리하여 빈도수 분석
    
    GET /api/activity/watching-analytics/
    
    Response:
    {
        "data": {
            "video_keywords": [
                {"keyword": "키워드1", "count": 5},
                {"keyword": "키워드2", "count": 3},
                ...
            ],
            "tags": [
                {"tag": "태그1", "count": 8},
                {"tag": "태그2", "count": 4},
                ...
            ],
            "total_videos": 10,
            "total_keywords": 15,
            "total_tags": 12
        },
        "message": "ok"
    }
    """
    from collections import Counter
    
    user = request.user
    
    # 사용자의 모든 시청 기록 조회
    watch_histories = WatchingHistory.objects.filter(
        user=user
    ).select_related('video').order_by('-created_at')
    
    if not watch_histories.exists():
        return Response({
            'data': {
                'video_keywords': [],
                'tags': [],
                'total_videos': 0,
                'total_keywords': 0,
                'total_tags': 0
            },
            'message': '시청 기록이 없습니다.'
        })
    
    # video_keyword 수집 및 빈도 계산
    video_keyword_counter = Counter()
    for watch in watch_histories:
        if watch.video_keyword:
            keywords = [k.strip() for k in watch.video_keyword.split(',') if k.strip()]
            video_keyword_counter.update(keywords)
    
    # tags 수집 및 빈도 계산
    tags_counter = Counter()
    for watch in watch_histories:
        if watch.tags:
            tag_list = [t.strip() for t in watch.tags.split(',') if t.strip()]
            tags_counter.update(tag_list)
    
    # 상위 10개만 추출 (빈도수 기준 내림차순)
    top_video_keywords = [
        {'keyword': kw, 'count': count}
        for kw, count in video_keyword_counter.most_common(10)
    ]
    
    top_tags = [
        {'tag': tag, 'count': count}
        for tag, count in tags_counter.most_common(10)
    ]
    
    return Response({
        'data': {
            'video_keywords': top_video_keywords,
            'tags': top_tags,
            'total_videos': watch_histories.count(),
            'total_keywords': len(video_keyword_counter),
            'total_tags': len(tags_counter)
        },
        'message': 'ok'
    })
