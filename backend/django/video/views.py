import json
import os
import time
import glob
import subprocess
import requests
import shutil  # 하이재킹용 추가
import traceback # 디버깅용 추가
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

# 이 놈이 나중에 ALB IP로 바뀌어야 하는 그놈이에요!
SITE_URL = "https://tara-multiflorous-frowsily.ngrok-free.dev"

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
# [통합 완료] 유니티 시나리오 생성 (가공 + 하이재킹)
# ============================================
@csrf_exempt
async def generate_scenario(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        body_unicode = request.body.decode('utf-8')
        data = json.loads(body_unicode)
        topic = data.get('topic', '')
        
        # 1. LangGraph 실행 (dev의 asset_context 로직 적용)
        asset_context_prompt = load_asset_context()
        app = create_graph_flow()
        initial_state = {"query": topic, "asset_context": asset_context_prompt, "tag": "video"}
        
        print("🔹 [1/4] LangGraph 실행 중...")
        result = await app.ainvoke(initial_state)
        final_script = result.get('scene_script')

        # 2. 가공 대상 영상 주소 추출 (사용자님의 정밀 탐색 로직)
        candidate_video = (
            result.get('video_url') or 
            result.get('background_video_url') or 
            result.get('video_path') or 
            final_script.get('background_video_url') or
            final_script.get('background_url')
        )

        if not candidate_video and 'scenes' in final_script and len(final_script['scenes']) > 0:
            candidate_video = final_script['scenes'][0].get('location')
            print(f"🔍 [Notice] 씬 데이터에서 주소 발견: {candidate_video}")
        
        print(f"🔍 [2/4] 가공 대상 후보 확인: {candidate_video}")

        target_url = ""
        # 3. 가공 로직 (성공해야만 target_url이 .webm으로 바뀜)
        if candidate_video and any(ext in str(candidate_video).lower() for ext in [".mp4", ".webm", ".mov"]):
            original_url = str(candidate_video)
            try:
                temp_raw_dir = os.path.join(settings.MEDIA_ROOT, 'temp_raw')
                bg_final_dir = os.path.join(settings.MEDIA_ROOT, 'backgrounds')
                os.makedirs(temp_raw_dir, exist_ok=True)
                os.makedirs(bg_final_dir, exist_ok=True)

                file_id = int(time.time())
                raw_path = os.path.join(temp_raw_dir, f"raw_{file_id}.mp4")
                output_name = f"unity_{file_id}.webm"
                local_output = os.path.join(bg_final_dir, output_name)

                print(f"🎬 [3/4] 가공 시작: {original_url} -> {output_name}")

                r = requests.get(original_url, stream=True, timeout=30)
                with open(raw_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)

                # FFmpeg 세탁 (인코딩 및 에러 처리 보강)
                cmd = [
                    'ffmpeg', '-y', '-i', raw_path,
                    '-map_metadata', '-1',
                    '-c:v', 'libvpx', '-b:v', '2M', '-crf', '10',
                    '-c:a', 'libvorbis',
                    local_output
                ]
                process = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='ignore')

                if process.returncode == 0:
                    target_url = f"{SITE_URL}{settings.MEDIA_URL}backgrounds/{output_name}"
                    print(f"✅ [Success] 가공 완료: {target_url}")
                    if os.path.exists(raw_path): os.remove(raw_path)
                else:
                    print(f"❌ FFmpeg 에러: {process.stderr}")
                    target_url = original_url
            except Exception as e:
                print(f"❌ 가공 중 예외 발생: {e}")
                target_url = original_url
        else:
            target_url = candidate_video or (final_script.get('background_url') if final_script else "")

        # 4. JSON 대본 업데이트 및 하이재킹 저장
        if target_url and final_script and 'scenes' in final_script:
            final_script['background_url'] = target_url
            for scene in final_script['scenes']:
                scene['location'] = target_url

        save_dir = os.path.join(settings.MEDIA_ROOT, 'pending_scripts')
        hijack_dir = os.path.join(settings.MEDIA_ROOT, 'script_logs')
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs(hijack_dir, exist_ok=True)

        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_script.json"
        full_path = os.path.join(save_dir, filename)
        hijack_path = os.path.join(hijack_dir, filename)

        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(final_script, f, indent=4, ensure_ascii=False)

        try:
            shutil.copy(full_path, hijack_path)
            print(f"📄 [4/4] 대본 생성 및 하이재킹 성공: {hijack_path}")
        except Exception as copy_e:
            print(f"⚠️ 하이재킹 복사 실패: {copy_e}")

        return JsonResponse({'message': 'Queued', 'file_name': filename}, status=200)

    except Exception as e:
        print(f"🔥 [Critical] 전체 프로세스 실패: {e}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

# ============================================
# 비디오 생성 (dev의 Celery 로직 통합)
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

    thumbnail_url = result_state.get("thumbnail_url") or body.get("thumbnail_url")
    
    payload = {
        "title": title, 
        "video_url": body.get("video_url", "https://skn18-3-dev-temp.s3.amazonaws.com/background_scene_1_video.mp4"), 
        "tags": result_state.get("video_tags") or [], 
        "thumbnail_url": thumbnail_url
    }
    serializer = VideoCreateSerializer(data=payload)
    await sync_to_async(serializer.is_valid)(raise_exception=True)
    video = await sync_to_async(serializer.save)()

    # ========== 영상 키워드 생성 Task 등록 (dev 기능 유지) ==========
    from backend.langgraph_recommendation.tasks import generate_video_keywords_task
    try:
        task = generate_video_keywords_task.delay(video.id, title, description)
        print(f"✓ 키워드 생성 Task 등록 완료: video_id={video.id}, task_id={task.id}")
    except Exception as e:
        print(f"⚠️ Celery Task 등록 실패: {e}")

    serialized = await sync_to_async(lambda: VideoSerializer(video).data)()
    return JsonResponse({"data": serialized}, status=201)

# ============================================
# [유니티 폴링 API] (기존 유지) -> 얘가 대본 보내기 담당!
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
        
        json_str = json.dumps(data, ensure_ascii=False).replace("http://127.0.0.1:8000", SITE_URL).replace("http://localhost:8000", SITE_URL)
        data = json.loads(json_str)
        
        os.remove(target_file)
        return Response(data, status=200)

# ============================================
# VideoUploadView 및 기타 CRUD (기존 유지) -> 얘가 동영상 받기 담당!
# ============================================
class VideoUploadView(CreateAPIView):
    queryset = Video.objects.all()
    serializer_class = VideoCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        thumbnail_url = None
        video_url = None

        if 'thumbnail_file' in request.FILES:
            thumb = request.FILES['thumbnail_file']
            t_dir = 'thumbnails'
            os.makedirs(os.path.join(settings.MEDIA_ROOT, t_dir), exist_ok=True)
            t_name = f"{int(time.time())}_thumb{os.path.splitext(thumb.name)[1]}"
            t_path = default_storage.save(os.path.join(t_dir, t_name), thumb)
            thumbnail_url = f"{SITE_URL}{settings.MEDIA_URL}{t_path}"

        if 'video_file' in request.FILES:
            video = request.FILES['video_file']
            v_dir = 'videos'
            os.makedirs(os.path.join(settings.MEDIA_ROOT, v_dir), exist_ok=True)
            v_name = f"{int(time.time())}_{video.name}"
            v_path = default_storage.save(os.path.join(v_dir, v_name), video)
            video_url = f"{SITE_URL}{settings.MEDIA_URL}{v_path}"

            data = {
                'title': request.data.get('title'),
                'video_url': video_url,
                'tags': request.data.getlist('tags[]') if 'tags[]' in request.data else [],
                'thumbnail_url': thumbnail_url
            }
        else:
            data = request.data.copy()
            if thumbnail_url: data['thumbnail_url'] = thumbnail_url

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'data': VideoSerializer(serializer.instance).data, 'message': 'ok'}, status=201)

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

class PopularVideosView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        videos = Video.objects.all().order_by('-likes_count', '-comments_count')[:20]
        serializer = VideoSerializer(videos, many=True)
        return Response({'data': serializer.data, 'message': 'ok'})

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