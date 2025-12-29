import json
import os
import time
import glob
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
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from openai import OpenAI
from dotenv import load_dotenv
from asgiref.sync import sync_to_async

# 모델 및 시리얼라이저
from .models import Video
from .serializers import VideoSerializer, VideoDetailSerializer, VideoCreateSerializer
from config.permissions import IsAdminUser

# LangGraph 임포트
from backend.langgraph_structure1.graph import create_graph_flow
from backend.langgraph_structure1.state import GraphState

# .env 파일 로드
load_dotenv()

# ============================================
# 유니티 에셋 로드
# ============================================
def load_asset_context():
    """views.py와 같은 폴더에 있는 unityassets.json 파일을 읽는 함수"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'unityassets.json')
        
        if not os.path.exists(file_path):
            return "No asset file found. Use default actions."

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        actors = ", ".join(data.get('actors', []))
        bgms = ", ".join(data.get('bgm_files', []))
        sfxs = ", ".join(data.get('sfx_files', []))
        
        actions_str = ""
        for group in data.get('action_groups', []):
            mood = group.get('mood', 'General')
            tags = ", ".join(group.get('tags', []))
            actions_str += f"- [{mood}]: {tags}\n"

        context_prompt = f"""
        [Available Assets from Unity Engine]
        1. Characters: {actors}
        2. Background Music: {bgms}
        3. Sound Effects: {sfxs}
        4. Actor Actions (Grouped by Mood):
        {actions_str}
        WARNING: You MUST use ONLY the assets listed above. Do not hallucinate file names.
        """
        return context_prompt

    except Exception as e:
        print(f"❌ 에셋 파일 읽기 실패: {e}")
        return "Error loading assets."

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
# [메인 기능] 유니티 시나리오 생성 (복구됨!)
# ============================================
@csrf_exempt
async def generate_scenario(request):
    """
    [Frontend] -> [Django] -> [File Save] -> [Unity Polling]
    원래 코드는 결과를 바로 리턴했지만, 유니티 자동화를 위해선 파일 저장이 필수
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        body_unicode = request.body.decode('utf-8')
        data = json.loads(body_unicode)
        topic = data.get('topic', '')
        
        # 1. 에셋 정보 로드 (파일 기반)
        asset_context_prompt = load_asset_context()

        # 2. LangGraph 실행
        app = create_graph_flow()
        initial_state = {
            "query": topic,
            "asset_context": asset_context_prompt,
            "tag": "video"
        }

        print("🔹 [View] LangGraph 실행 시작... (시나리오 생성)")
        result = await app.ainvoke(initial_state)
        final_script = result.get('scene_script')

        if not final_script:
            return JsonResponse({'error': 'Failed to generate script'}, status=500)

        # 3. [핵심] 파일 시스템 큐(Queue)에 저장
        save_dir = os.path.join(settings.MEDIA_ROOT, 'pending_scripts')
        os.makedirs(save_dir, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_script.json"
        file_path = os.path.join(save_dir, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(final_script, f, indent=4, ensure_ascii=False)
            
        print(f"📂 [Queue] 대본 대기열 저장 완료: {filename}")

        return JsonResponse({
            'message': 'Scenario generated and queued successfully.',
            'file_name': filename,
            'status': 'queued'
        }, status=200)

    except Exception as e:
        print(f"❌ [View Error] {e}")
        return JsonResponse({'error': str(e)}, status=500)

# ============================================
# 비디오 생성
# ============================================
@csrf_exempt
async def create_video_from_langgraph(request):
    """
    프론트에서 바로 비디오 DB 레코드를 생성하는 로직
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    description = body.get("description", "") or ""
    video_url = body.get("video_url", "") or ""
    thumbnail_url = body.get("thumbnail_url") 

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
    if title and not any("가" <= ch <= "힣" for ch in title):
        title = description[:50] or title
    tags = result_state.get("video_tags") or []
    
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

    serialized = await sync_to_async(lambda: VideoSerializer(video).data)()

    return JsonResponse(
        {
            "data": serialized,
            "message": "Video created via LangGraph",
        },
        status=201,
    )

# ============================================
# [유니티 폴링 API]
# ============================================
class PendingScriptView(APIView):
    """
    GET /api/video/pending/
    - 유니티가 5초마다 호출함.
    - pending_scripts 폴더에서 '가장 오래된' 파일을 찾아 반환하고 '삭제'함.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        save_dir = os.path.join(settings.MEDIA_ROOT, 'pending_scripts')
        # glob import 확인
        files = glob.glob(os.path.join(save_dir, "*.json"))
        
        if not files:
            return Response({"message": "No pending scripts."}, status=status.HTTP_404_NOT_FOUND)

        files.sort()
        target_file = files[0]

        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            os.remove(target_file)
            print(f"🚀 [Queue] 유니티로 전송 및 삭제: {os.path.basename(target_file)}")
            
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"⚠️ [Queue Error] 파일 처리 중 오류: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================================
# [Video 관련 뷰] (수정됨: AllowAny & Import Fix)
# ============================================

class VideoListView(ListAPIView):
    """ 전체 영상 목록 조회 """
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [AllowAny] # [수정] 누구나 조회 가능 -> 일단 장고가 유니티에서 보내는 영상을 reject하는 상태라 테스트 용으로 열어둠
    
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
    """ 영상 상세 조회 """
    queryset = Video.objects.all()
    serializer_class = VideoDetailSerializer
    permission_classes = [AllowAny] # [수정] 누구나 조회 가능
    
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return Response({'data': response.data, 'message': 'ok'})

class VideoUploadView(CreateAPIView):
    """
    영상 업로드 API
    - 유니티 자동 업로드를 위해 AllowAny 적용
    - import time 버그 수정 완료
    """
    queryset = Video.objects.all()
    serializer_class = VideoCreateSerializer
    permission_classes = [AllowAny] # [수정] 누구나 업로드 가능 (유니티용)

    def create(self, request, *args, **kwargs):
        thumbnail_url = None

        # 1. 썸네일 처리
        if 'thumbnail_file' in request.FILES:
            thumbnail_file = request.FILES['thumbnail_file']
            thumbnail_dir = 'thumbnails'
            os.makedirs(os.path.join(settings.MEDIA_ROOT, thumbnail_dir), exist_ok=True)
            
            file_extension = os.path.splitext(thumbnail_file.name)[1]
            # [Fix] 전역 time 모듈 사용 (함수 내 import 제거)
            file_name = f"{int(time.time())}_thumbnail{file_extension}"
            file_path = os.path.join(thumbnail_dir, file_name)
            
            saved_thumbnail_path = default_storage.save(file_path, thumbnail_file)
            thumbnail_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_thumbnail_path}")

        # 2. 비디오 파일 처리
        if 'video_file' in request.FILES:
            video_file = request.FILES['video_file']
            upload_dir = 'videos'
            os.makedirs(os.path.join(settings.MEDIA_ROOT, upload_dir), exist_ok=True)
            
            file_extension = os.path.splitext(video_file.name)[1]
            # [Fix] 전역 time 모듈 사용
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
            # URL로 업로드하는 경우 등
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
    """ 영상 수정 API """
    queryset = Video.objects.all()
    serializer_class = VideoCreateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser] # 수정은 관리자만

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        thumbnail_url = instance.thumbnail_url

        if 'thumbnail_file' in request.FILES:
            thumbnail_file = request.FILES['thumbnail_file']
            thumbnail_dir = 'thumbnails'
            os.makedirs(os.path.join(settings.MEDIA_ROOT, thumbnail_dir), exist_ok=True)
            
            file_extension = os.path.splitext(thumbnail_file.name)[1]
            file_name = f"{int(time.time())}_thumbnail{file_extension}"
            file_path = os.path.join(thumbnail_dir, file_name)
            
            saved_thumbnail_path = default_storage.save(file_path, thumbnail_file)
            thumbnail_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_thumbnail_path}")

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
    """ 영상 삭제 API """
    queryset = Video.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser] # 삭제는 관리자만

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        video_title = instance.title
        self.perform_destroy(instance)
        return Response({'message': f'영상 "{video_title}"이(가) 삭제되었습니다.'}, status=status.HTTP_200_OK)

class PopularVideosView(ListAPIView):
    """ 인기 영상 조회 """
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return Video.objects.all().order_by('-likes_count', '-comments_count')[:20]
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({'data': response.data, 'message': 'ok'})

class PopularTagsView(APIView):
    """ 인기 태그 조회 """
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
    
# ============================================
# [연결 테스트 뷰 복구]
# ============================================
class ConnectionTestView(APIView):
    """
    POST /api/video/test/ (경로는 urls.py에 따라 다름)
    - 유니티 연결 테스트용
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        print(f"🔔 [유니티에서 신호 옴!] 받은 데이터: {request.data}")
        return Response({"message": "연결 성공! 장고가 응답합니다."}, status=status.HTTP_200_OK)