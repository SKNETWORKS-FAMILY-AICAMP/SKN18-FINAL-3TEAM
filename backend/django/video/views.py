import json
import os
import time
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage

# Rest Framework 임포트
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from dotenv import load_dotenv

# 모델 및 시리얼라이저 (Dev 브랜치 기준)
from .models import Video
from .serializers import VideoSerializer, VideoDetailSerializer, VideoCreateSerializer

# LangGraph 임포트 (작성자님 기능 유지)
from backend.langgraph_structure1.graph import create_graph_flow

# .env 파일 로드
load_dotenv()

# ============================================
# 커스텀 권한 클래스 (관리자용)
# ============================================
class IsAdminUser(BasePermission):
    """관리자(permission='admin')만 접근 가능"""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, 'permission', '') == 'admin'
        )

# ============================================
# [메인 기능] 유니티 시나리오 생성 (LangGraph 버전)
# ============================================
@csrf_exempt
async def generate_scenario(request):
    """
    [Unity] -> [Django View] -> [LangGraph] -> [Django View] -> [Unity]
    유니티의 자산 정보를 LangGraph로 전달하여 시나리오를 생성하는 비동기 뷰
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        # 1. 유니티 데이터 수신
        body_unicode = request.body.decode('utf-8')
        data = json.loads(body_unicode)
        
        topic = data.get('topic', '')
        asset_info = data.get('asset_info', {}) # 유니티가 보낸 ProjectContextData

        print(f"🔹 [View] 유니티 요청 수신: Topic='{topic}'")

        # 2. 자산 정보를 LangGraph용 프롬프트로 변환
        actors = ", ".join(asset_info.get('actors', []))
        locations = ", ".join(asset_info.get('locations', []))
        bgms = ", ".join(asset_info.get('bgm_files', []))
        sfxs = ", ".join(asset_info.get('sfx_files', []))
        
        actions_str = ""
        for group in asset_info.get('action_groups', []):
            mood = group.get('mood', 'General')
            tags = group.get('tags', [])
            actions_str += f"- [{mood}]: {', '.join(tags)}\n"

        asset_context_prompt = f"""
        [Available Assets from Unity Engine]
        1. Characters: {actors}
        2. Locations: {locations} (IMPORTANT: Use strictly exactly these names for 'location' field)
        3. Background Music: {bgms}
        4. Sound Effects: {sfxs}
        5. Actor Actions (Animation Tags):
        {actions_str}
        
        WARNING: You MUST use ONLY the assets listed above. Do not hallucinate file names.
        """

        # 3. LangGraph 앱 생성 및 실행
        app = create_graph_flow()
        initial_state = {
            "query": topic,
            "asset_context": asset_context_prompt 
        }

        print("🔹 [View] LangGraph 실행 시작... (검색 및 생성 중)")
        result = await app.ainvoke(initial_state)
        print("✅ [View] LangGraph 실행 완료")

        # 4. 결과 추출 및 반환
        final_script = result.get('scene_script')

        if not final_script:
            print("⚠️ [View] 대본 생성 실패. 결과 State:", result.keys())
            return JsonResponse({'error': 'Failed to generate script from LangGraph'}, status=500)

        return JsonResponse(final_script, safe=False)

    except Exception as e:
        print(f"❌ [View Error] {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================
# [Dev 브랜치 복구] 비디오 API (서버 에러 해결용)
# ============================================

class VideoListView(ListAPIView):
    """
    GET /api/video/list/ - 전체 영상 목록 조회
    """
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        sort = self.request.query_params.get('sort', 'latest')
        if sort == 'comments':
            queryset = queryset.order_by('-comments_count', '-upload_date')
        else:
            queryset = queryset.order_by('-upload_date')
        
        tag = self.request.query_params.get('tag', '')
        if tag:
            queryset = queryset.extra(
                where=["""
                    EXISTS (
                        SELECT 1 FROM unnest(tags) AS t
                        WHERE t ILIKE %s
                    )
                """],
                params=[f'%{tag}%']
            )
        return queryset
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({'data': response.data, 'message': 'ok'})

class VideoDetailView(RetrieveAPIView):
    """
    GET /api/video/<id>/ - 영상 상세 조회
    """
    queryset = Video.objects.all()
    serializer_class = VideoDetailSerializer
    permission_classes = [AllowAny]
    
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return Response({'data': response.data, 'message': 'ok'})

class VideoUploadView(CreateAPIView):
    """
    POST /api/video/upload/ - 영상 업로드 (관리자)
    """
    queryset = Video.objects.all()
    serializer_class = VideoCreateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def create(self, request, *args, **kwargs):
        if 'video_file' in request.FILES:
            video_file = request.FILES['video_file']
            upload_dir = 'videos'
            os.makedirs(os.path.join(settings.MEDIA_ROOT, upload_dir), exist_ok=True)

            file_extension = os.path.splitext(video_file.name)[1]
            file_name = f"{int(time.time())}_{video_file.name}"
            file_path = os.path.join(upload_dir, file_name)
            saved_path = default_storage.save(file_path, video_file)
            video_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_path}")

            data = {
                'title': request.data.get('title'),
                'video_url': video_url,
                'tags': request.data.getlist('tags[]') if 'tags[]' in request.data else []
            }
        else:
            data = request.data

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response({
            'data': VideoSerializer(serializer.instance).data,
            'message': '영상이 업로드되었습니다.'
        }, status=status.HTTP_201_CREATED)

class PopularVideosView(ListAPIView):
    """
    GET /api/video/popular/ - 인기 영상
    """
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Video.objects.all().order_by('-likes_count', '-comments_count')[:20]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({'data': response.data, 'message': 'ok'})

class PopularTagsView(APIView):
    """
    GET /api/video/tags/popular/ - 인기 태그
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from collections import Counter
        all_tags = []
        videos = Video.objects.exclude(tags__isnull=True).exclude(tags=[])

        for video in videos:
            if video.tags:
                all_tags.extend(video.tags)

        tag_counter = Counter(all_tags)
        popular_tags = [{'tag': tag, 'count': count} for tag, count in tag_counter.most_common(10)]

        return Response({'data': popular_tags, 'message': 'ok'})