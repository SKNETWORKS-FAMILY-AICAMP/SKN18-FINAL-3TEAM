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
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView
from openai import OpenAI
from dotenv import load_dotenv
from asgiref.sync import sync_to_async

# 모델 및 시리얼라이저 (Dev 브랜치 기준)
from .models import Video
from .serializers import VideoSerializer, VideoDetailSerializer, VideoCreateSerializer
from config.permissions import IsAdminUser

# LangGraph 임포트 (작성자님 기능 유지)
from backend.langgraph_structure1.graph import create_graph_flow
from backend.langgraph_structure1.state import GraphState

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
            "asset_context": asset_context_prompt ,
            "tag": "video"
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
# LangGraph로 스크립트 생성 후 Video DB 저장
# ============================================
@csrf_exempt
async def create_video_from_langgraph(request):
    """
    프론트에서 설명을 보내면 LangGraph(tag=video)로 스크립트/태그 생성 후
    title + tags를 사용해 Video 레코드를 생성합니다.
    video_url은 임시로 옵션 처리 (추후 필수화 예정).  # 수정 필요
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    description = body.get("description", "") or ""
    video_url = body.get("video_url", "") or ""
    thumbnail_url = body.get("thumbnail_url")  # 옵션
    # if not video_url:
    #     return JsonResponse({"error": "video_url is required"}, status=400)  # 수정 필요

    try:
        app = create_graph_flow()
        initial_state: GraphState = {
            "query": description,
            "tag": "video",
        }
        result_state = await app.ainvoke(initial_state)
    except Exception as e:
        print(f"[LangGraph Error] {e}")
        return JsonResponse({"error": "Failed to generate video script"}, status=500)

    script_json = result_state.get("scene_script") or {}
    title = (
        script_json.get("title_ko")
        or script_json.get("title")
        or (description[:50] or "Untitled Video")
    )
    # title이 한글이 아니라면 질의 일부를 사용해 한국어로 보정
    if title and not any("가" <= ch <= "힣" for ch in title):
        title = description[:50] or title
    tags = result_state.get("video_tags") or []
    # 문자열로 넘어오는 경우 대비
    if isinstance(tags, str):
        try:
            parsed = json.loads(tags)
            if isinstance(parsed, dict):
                tags = parsed.get("tags") or []
            elif isinstance(parsed, list):
                tags = parsed
        except Exception:
            tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not isinstance(tags, list):
        tags = []

    payload = {
        "title": title,
        "video_url": video_url,
        "tags": tags,
        "thumbnail_url": thumbnail_url,
    }

    try:
        serializer = VideoCreateSerializer(data=payload)
        await sync_to_async(serializer.is_valid)(raise_exception=True)
        video = await sync_to_async(serializer.save)()
    except Exception as e:
        print(f"[Video Save Error] {e}")
        return JsonResponse({"error": "Failed to save video"}, status=500)

    # serializer.data는 내부에서 동기 ORM을 호출하므로 스레드에서 실행
    serialized = await sync_to_async(lambda: VideoSerializer(video).data)()

    return JsonResponse(
        {
            "data": serialized,
            "message": "Video created via LangGraph",
        },
        status=201,
    )


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
        import os
        from django.core.files.storage import default_storage
        from django.conf import settings

        thumbnail_url = None

        # 썸네일 파일 처리
        if 'thumbnail_file' in request.FILES:
            thumbnail_file = request.FILES['thumbnail_file']

            # 썸네일 저장 경로 생성
            thumbnail_dir = 'thumbnails'
            os.makedirs(os.path.join(settings.MEDIA_ROOT, thumbnail_dir), exist_ok=True)

            # 파일명 생성 (중복 방지)
            import time
            file_extension = os.path.splitext(thumbnail_file.name)[1]
            file_name = f"{int(time.time())}_thumbnail{file_extension}"
            file_path = os.path.join(thumbnail_dir, file_name)

            # 파일 저장
            saved_thumbnail_path = default_storage.save(file_path, thumbnail_file)

            # URL 생성
            thumbnail_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_thumbnail_path}")

        # 파일 업로드인 경우
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
                'tags': request.data.getlist('tags[]') if 'tags[]' in request.data else [],
                'thumbnail_url': thumbnail_url
            }
        else:
            # URL 입력인 경우
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            if thumbnail_url:
                data['thumbnail_url'] = thumbnail_url

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response({
            'data': VideoSerializer(serializer.instance).data,
            'message': '영상이 업로드되었습니다.'
        }, status=status.HTTP_201_CREATED)


class VideoUpdateView(UpdateAPIView):
    """
    영상 수정 API
    - 관리자만 수정 가능

    PATCH /api/video/<int:pk>/
    """
    queryset = Video.objects.all()
    serializer_class = VideoCreateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def update(self, request, *args, **kwargs):
        import os
        from django.core.files.storage import default_storage
        from django.conf import settings

        instance = self.get_object()
        thumbnail_url = instance.thumbnail_url  # 기존 썸네일 유지

        # 썸네일 파일 처리 (새로 업로드한 경우)
        if 'thumbnail_file' in request.FILES:
            thumbnail_file = request.FILES['thumbnail_file']

            # 썸네일 저장 경로 생성
            thumbnail_dir = 'thumbnails'
            os.makedirs(os.path.join(settings.MEDIA_ROOT, thumbnail_dir), exist_ok=True)

            # 파일명 생성 (중복 방지)
            import time
            file_extension = os.path.splitext(thumbnail_file.name)[1]
            file_name = f"{int(time.time())}_thumbnail{file_extension}"
            file_path = os.path.join(thumbnail_dir, file_name)

            # 파일 저장
            saved_thumbnail_path = default_storage.save(file_path, thumbnail_file)

            # URL 생성
            thumbnail_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_thumbnail_path}")

        # 영상 파일 처리 (새로 업로드한 경우)
        if 'video_file' in request.FILES:
            video_file = request.FILES['video_file']

            # 파일 저장 경로 생성
            upload_dir = 'videos'
            os.makedirs(os.path.join(settings.MEDIA_ROOT, upload_dir), exist_ok=True)

            # 파일명 생성 (중복 방지)
            import time
            file_extension = os.path.splitext(video_file.name)[1]
            file_name = f"{int(time.time())}_{video_file.name}"
            file_path = os.path.join(upload_dir, file_name)

            # 파일 저장
            saved_path = default_storage.save(file_path, video_file)

            # URL 생성
            video_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_path}")

            # 데이터 준비
            data = {
                'title': request.data.get('title'),
                'video_url': video_url,
                'tags': request.data.getlist('tags[]') if 'tags[]' in request.data else [],
                'thumbnail_url': thumbnail_url
            }
        else:
            # URL 입력 또는 기존 데이터 수정
            data = {}
            if 'title' in request.data:
                data['title'] = request.data.get('title')
            if 'video_url' in request.data:
                data['video_url'] = request.data.get('video_url')
            if 'tags[]' in request.data:
                data['tags'] = request.data.getlist('tags[]')
            elif 'tags' in request.data:
                data['tags'] = request.data.get('tags')
            if thumbnail_url:
                data['thumbnail_url'] = thumbnail_url

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'data': VideoSerializer(serializer.instance).data,
            'message': '영상이 수정되었습니다.'
        }, status=status.HTTP_200_OK)


class VideoDeleteView(DestroyAPIView):
    """
    영상 삭제 API
    - 관리자만 삭제 가능

    DELETE /api/video/<int:pk>/
    """
    queryset = Video.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        video_title = instance.title
        self.perform_destroy(instance)

        return Response({
            'message': f'영상 "{video_title}"이(가) 삭제되었습니다.'
        }, status=status.HTTP_200_OK)


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
