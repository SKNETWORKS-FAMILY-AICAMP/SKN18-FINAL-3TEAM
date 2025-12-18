from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from video.models import Video
from activity.models import SearchHistory
from .serializers import VideoSearchSerializer


class VideoSearchView(APIView):
    """
    영상 검색 API (무한 스크롤 지원)

    GET /api/search/videos/?q=검색어&sort=latest&page=1&page_size=12&tags=tag1,tag2

    Query Parameters:
        - q: 검색어 (선택, 없으면 인기 영상 반환)
        - sort: 정렬 기준 (latest/popular/relevance, 기본: relevance)
        - page: 페이지 번호 (기본: 1)
        - page_size: 페이지당 개수 (기본: 12)
        - tags: 태그 필터 (쉼표로 구분, 예: "과학,역사")
    """

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        sort_by = request.query_params.get('sort', 'relevance')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 12))
        tags_param = request.query_params.get('tags', '').strip()

        # 페이지 유효성 검사
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 50:
            page_size = 12

        # 검색어가 없으면 인기 영상 반환
        if not query:
            videos = Video.objects.all().order_by('-likes_count', '-comments_count')
        else:
            # 검색어 길이 검증
            if len(query) < 2:
                return Response({
                    'error': {
                        'code': 'QUERY_TOO_SHORT',
                        'message': '검색어는 최소 2자 이상이어야 합니다.'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            # 검색 기록 저장 (로그인한 경우)
            if request.user.is_authenticated:
                try:
                    SearchHistory.objects.create(
                        user=request.user,
                        search_query=query
                    )
                except Exception as e:
                    # 검색 기록 저장 실패는 무시
                    pass

            # 검색 쿼리 (제목 + 태그)
            search_filter = Q(title__icontains=query) | Q(tags__icontains=query)
            videos = Video.objects.filter(search_filter)

        # 태그 필터링
        if tags_param:
            tag_list = [tag.strip() for tag in tags_param.split(',') if tag.strip()]
            if tag_list:
                # 모든 태그를 포함하는 영상만 필터링
                for tag in tag_list:
                    videos = videos.filter(tags__icontains=tag)

        # 정렬
        if sort_by == 'latest':
            videos = videos.order_by('-upload_date')
        elif sort_by == 'popular':
            videos = videos.order_by('-likes_count', '-comments_count')
        else:  # relevance
            videos = videos.order_by('-likes_count', '-upload_date')

        # 전체 개수 계산
        total_count = videos.count()

        # 페이지네이션
        start = (page - 1) * page_size
        end = start + page_size
        videos_page = videos[start:end]

        # 다음 페이지 존재 여부
        has_next = end < total_count

        # 응답
        serializer = VideoSearchSerializer(videos_page, many=True)

        return Response({
            'data': {
                'query': query if query else None,
                'results': serializer.data,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'has_next': has_next,
                    'total_pages': (total_count + page_size - 1) // page_size
                }
            },
            'message': 'ok'
        }, status=status.HTTP_200_OK)
