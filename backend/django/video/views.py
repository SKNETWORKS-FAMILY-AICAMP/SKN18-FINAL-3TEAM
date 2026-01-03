import json
import os
import time
import glob
import subprocess
import requests
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

# 팀원 추가 라이브러리: 번역기
from deep_translator import GoogleTranslator

# 모델 및 시리얼라이저
from .models import Video
from .serializers import VideoSerializer, VideoDetailSerializer, VideoCreateSerializer

# .env 파일 로드
load_dotenv()

# LangGraph 임포트
from backend.langgraph_structure1.graph import create_graph_flow
from backend.langgraph_structure1.state import GraphState

# ============================================
# 유니티 에셋 로드 (기존 유지)
# ============================================
def load_asset_context():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'unityassets.json')
        if not os.path.exists(file_path):
            return "No asset file found."
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
        return f"[Assets] Characters: {actors}, BGM: {bgms}, SFX: {sfxs}\n{actions_str}"
    except Exception as e:
        return f"Error: {e}"

class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'permission', '') == 'admin'

# ============================================
# [핵심] 유니티 시나리오 생성 (VP8 가공 통합)
# ============================================
@csrf_exempt
async def generate_scenario(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        body_unicode = request.body.decode('utf-8')
        data = json.loads(body_unicode)
        topic = data.get('topic', '')
        
        asset_context_prompt = load_asset_context()
        app = create_graph_flow()
        initial_state = {"query": topic, "asset_context": asset_context_prompt, "tag": "video"}

        print("🔹 [View] LangGraph 실행...")
        result = await app.ainvoke(initial_state)
        final_script = result.get('scene_script')

        # VP8 가공 로직
        candidate_video = (result.get('video_url') or result.get('background_video_url') or 
                           result.get('video_path') or final_script.get('background_video_url'))
        
        target_url = ""
        if candidate_video and ".mp4" in str(candidate_video):
            original_url = str(candidate_video)
            print(f"🎬 [Process] VP8 가공 시작: {original_url}")
            try:
                bg_dir = os.path.join(settings.MEDIA_ROOT, 'backgrounds')
                os.makedirs(bg_dir, exist_ok=True)
                file_id = int(time.time())
                raw_path = os.path.join(bg_dir, f"raw_{file_id}.mp4")
                output_name = f"unity_{file_id}.webm"
                local_output = os.path.join(bg_dir, output_name)

                r = requests.get(original_url, stream=True)
                with open(raw_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)

                cmd = ['ffmpeg', '-y', '-i', raw_path, '-c:v', 'libvpx', '-b:v', '2M', '-crf', '10', '-c:a', 'libvorbis', local_output]
                subprocess.run(cmd, check=True, capture_output=True)

                ngrok_url = "https://tara-multiflorous-frowsily.ngrok-free.dev"
                target_url = f"{ngrok_url}{settings.MEDIA_URL}backgrounds/{output_name}"
            except Exception as e:
                print(f"❌ 가공 실패: {e}")
                target_url = original_url
        else:
            target_url = result.get('background_url') or final_script.get('background_url')

        if target_url and 'scenes' in final_script:
            final_script['background_url'] = target_url
            for scene in final_script['scenes']: scene['location'] = target_url

        save_dir = os.path.join(settings.MEDIA_ROOT, 'pending_scripts')
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_script.json"
        with open(os.path.join(save_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(final_script, f, indent=4, ensure_ascii=False)
            
        return JsonResponse({'message': 'Queued', 'file_name': filename}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ============================================
# 비디오 생성 (팀원 번역 통합)
# ============================================
@csrf_exempt
async def create_video_from_langgraph(request):
    if request.method != "POST": return JsonResponse({"error": "POST only"}, status=405)
    body = json.loads(request.body.decode("utf-8"))
    description = body.get("description", "")
    app = create_graph_flow()
    initial_state = {"query": description, "tag": "video"}
    result_state = await app.ainvoke(initial_state)
    script_json = result_state.get("scene_script") or {}
    title = script_json.get("title") or description[:50]

    if title:
        try: title = GoogleTranslator(source="en", target="ko").translate(title)
        except: pass

    payload = {"title": title, "video_url": body.get("video_url", "https://skn18-3-dev-temp.s3.amazonaws.com/background_scene_1_video.mp4"), "tags": result_state.get("video_tags") or [], "thumbnail_url": body.get("thumbnail_url")}
    serializer = VideoCreateSerializer(data=payload)
    await sync_to_async(serializer.is_valid)(raise_exception=True)
    video = await sync_to_async(serializer.save)()

    # ========== 영상 키워드 생성 Task 등록 (Celery) ==========
    # DB 저장 완료 후 비동기로 키워드 생성
    from backend.langgraph_recommendation.tasks import generate_video_keywords_task

    try:
        # Celery Task 등록 (비동기 실행, 즉시 반환)
        # user_query (description)와 video_title (title)을 모두 전달
        task = generate_video_keywords_task.delay(video.id, title, description)
        print(f"✓ 키워드 생성 Task 등록 완료: video_id={video.id}, task_id={task.id}")
    except Exception as e:
        # Celery 실패해도 영상 생성은 성공 처리
        print(f"⚠️ Celery Task 등록 실패 (영상은 정상 저장됨): {e}")
    serialized = await sync_to_async(lambda: VideoSerializer(video).data)()
    return JsonResponse({"data": serialized}, status=201)

# ============================================
# [유니티 폴링 API] (Ngrok 세탁 유지)
# ============================================
class PendingScriptView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        save_dir = os.path.join(settings.MEDIA_ROOT, 'pending_scripts')
        files = glob.glob(os.path.join(save_dir, "*.json"))
        if not files: return Response(status=404)
        files.sort()
        target_file = files[0]
        with open(target_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        ngrok_url = "https://tara-multiflorous-frowsily.ngrok-free.dev"
        json_str = json.dumps(data, ensure_ascii=False).replace("http://127.0.0.1:8000", ngrok_url).replace("http://localhost:8000", ngrok_url)
        data = json.loads(json_str)
        
        os.remove(target_file)
        return Response(data, status=200)

# ============================================
# [복구 완본] VideoUploadView (물리적 파일 저장 로직)
# ============================================
class VideoUploadView(CreateAPIView):
    queryset = Video.objects.all()
    serializer_class = VideoCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        thumbnail_url = None
        video_url = None
        ngrok_url = "https://tara-multiflorous-frowsily.ngrok-free.dev"

        # 1. 썸네일 파일 저장
        if 'thumbnail_file' in request.FILES:
            thumb = request.FILES['thumbnail_file']
            t_dir = 'thumbnails'
            os.makedirs(os.path.join(settings.MEDIA_ROOT, t_dir), exist_ok=True)
            t_name = f"{int(time.time())}_thumb{os.path.splitext(thumb.name)[1]}"
            t_path = default_storage.save(os.path.join(t_dir, t_name), thumb)
            thumbnail_url = f"{ngrok_url}{settings.MEDIA_URL}{t_path}"

        # 2. 비디오 파일 저장 (여기가 구버전에서 가져온 핵심!)
        if 'video_file' in request.FILES:
            video = request.FILES['video_file']
            v_dir = 'videos'
            os.makedirs(os.path.join(settings.MEDIA_ROOT, v_dir), exist_ok=True)
            v_name = f"{int(time.time())}_{video.name}"
            v_path = default_storage.save(os.path.join(v_dir, v_name), video)
            video_url = f"{ngrok_url}{settings.MEDIA_URL}{v_path}"
            print(f"🎬 [Local Save] 영상이 media/videos 폴더에 저장되었습니다: {v_name}")

            data = {
                'title': request.data.get('title'),
                'video_url': video_url,
                'tags': request.data.getlist('tags[]') if 'tags[]' in request.data else [],
                'thumbnail_url': thumbnail_url
            }
        else:
            data = request.data.copy()
            if thumbnail_url: data['thumbnail_url'] = thumbnail_url

        # DB 저장
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'data': VideoSerializer(serializer.instance).data, 'message': 'ok'}, status=201)

# ... (이하 ListView, DetailView 등 기타 CRUD는 기존 유지)
class VideoListView(ListAPIView):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]
    def list(self, request, *args, **kwargs):
        return Response({'data': super().list(request, *args, **kwargs).data})

class VideoDetailView(RetrieveAPIView):
    queryset = Video.objects.all()
    serializer_class = VideoDetailSerializer
    permission_classes = [AllowAny]

class VideoUpdateView(UpdateAPIView):
    queryset = Video.objects.all()
    serializer_class = VideoCreateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class VideoDeleteView(DestroyAPIView):
    queryset = Video.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]

class PopularVideosView(ListAPIView):
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]
    def get_queryset(self): return Video.objects.all().order_by('-likes_count', '-comments_count')[:20]

class PopularTagsView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        from collections import Counter
        tags = []
        for v in Video.objects.exclude(tags__isnull=True): tags.extend(v.tags)
        return Response({'data': [{'tag': k, 'count': v} for k, v in Counter(tags).most_common(10)]})

class ConnectionTestView(APIView):
    permission_classes = [AllowAny]
    def post(self, request): return Response({"message": "Success"}, status=200)