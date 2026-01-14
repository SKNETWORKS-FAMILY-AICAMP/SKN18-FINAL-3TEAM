import json
import os
import time
import glob
import subprocess
import requests
import re
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

import boto3

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
                os.makedirs(temp_raw_dir, exist_ok=True)

                file_id = int(time.time())
                raw_path = os.path.join(temp_raw_dir, f"raw_{file_id}.mp4")
                output_name = f"unity_{file_id}.webm"
                temp_output = os.path.join(temp_raw_dir, output_name)

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
                    temp_output
                ]
                process = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='ignore')

                if process.returncode == 0:
                    # S3에 업로드
                    from config.storage_backends import upload_video
                    from django.core.files import File

                    with open(temp_output, 'rb') as f:
                        video_file = File(f, name=output_name)
                        target_url = upload_video(video_file, output_name)

                    # 임시 파일 삭제
                    if os.path.exists(raw_path): os.remove(raw_path)
                    if os.path.exists(temp_output): os.remove(temp_output)

                    print(f"✅ [Success] 가공 및 S3 업로드 완료: {target_url}")
                else:
                    print(f"❌ FFmpeg 에러: {process.stderr}")
                    target_url = original_url
            except Exception as e:
                print(f"❌ 가공 중 예외 발생: {e}")
                target_url = original_url
        else:
            target_url = candidate_video or (final_script.get('background_url') if final_script else "")

        # 4. JSON 대본 업데이트 및 S3 저장
        if target_url and final_script and 'scenes' in final_script:
            final_script['background_url'] = target_url
            for scene in final_script['scenes']:
                scene['location'] = target_url

        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_script.json"

        # S3에 저장 (pending_scripts 폴더)
        import boto3
        s3_client = boto3.client('s3')
        bucket_name = 'skn18-3-dev-scripts-533124807326'

        try:
            # pending_scripts 폴더에 저장
            s3_key_pending = f"pending_scripts/{filename}"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key_pending,
                Body=json.dumps(final_script, indent=4, ensure_ascii=False).encode('utf-8'),
                ContentType='application/json'
            )
            print(f"📄 [4/4] S3 pending_scripts 업로드 완료: s3://{bucket_name}/{s3_key_pending}")

            # script_logs 폴더에도 백업
            s3_key_logs = f"script_logs/{filename}"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key_logs,
                Body=json.dumps(final_script, indent=4, ensure_ascii=False).encode('utf-8'),
                ContentType='application/json'
            )
            print(f"📄 [4/4] S3 script_logs 백업 완료: s3://{bucket_name}/{s3_key_logs}")

        except Exception as s3_error:
            print(f"❌ S3 업로드 실패: {s3_error}")
            # S3 실패 시 로컬에 fallback
            save_dir = os.path.join(settings.MEDIA_ROOT, 'pending_scripts')
            os.makedirs(save_dir, exist_ok=True)
            full_path = os.path.join(save_dir, filename)
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(final_script, f, indent=4, ensure_ascii=False)
            print(f"⚠️ 로컬 저장으로 fallback: {full_path}")

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

    # ========== S3에 script 저장 (Unity 폴링용) ==========
    if script_json and 'scenes' in script_json:
        import boto3
        s3_client = boto3.client('s3')
        bucket_name = 'skn18-3-dev-scripts-533124807326'
        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_script.json"

        try:
            # pending_scripts 폴더에 저장
            s3_key_pending = f"pending_scripts/{filename}"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key_pending,
                Body=json.dumps(script_json, indent=4, ensure_ascii=False).encode('utf-8'),
                ContentType='application/json'
            )
            print(f"📄 S3 pending_scripts 업로드 완료: s3://{bucket_name}/{s3_key_pending}")

            # script_logs 폴더에도 백업
            s3_key_logs = f"script_logs/{filename}"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key_logs,
                Body=json.dumps(script_json, indent=4, ensure_ascii=False).encode('utf-8'),
                ContentType='application/json'
            )
            print(f"📄 S3 script_logs 백업 완료: s3://{bucket_name}/{s3_key_logs}")
        except Exception as s3_error:
            print(f"❌ S3 업로드 실패: {s3_error}")

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
# [유니티 폴링 API] S3에서 대본 읽기 -> 얘가 대본 보내기 담당!
# ============================================
class PendingScriptView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        s3_client = boto3.client('s3')
        bucket_name = 'skn18-3-dev-scripts-533124807326'
        prefix = 'pending_scripts/'

        try:
            # 1. S3 목록 조회
            response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

            # Contents 키가 아예 없으면 데이터가 하나도 없는 것임
            if 'Contents' not in response:
                return Response({"detail": "No scripts found."}, status=404)

            # 2. '폴더명 자체'인 객체 제외하고 실제 파일만 추출
            # endswith('/')를 체크하여 서브 디렉토리 객체도 필터링하면 더 안전합니다.
            files = [
                obj for obj in response['Contents'] 
                if obj['Key'] != prefix and not obj['Key'].endswith('/')
            ]

            # 3. 실제 파일이 하나도 없다면 404
            if not files:
                return Response({"detail": "No pending script files found."}, status=404)

            # 4. 파일명 기준 정렬 (오래된 순/이름 순)
            files.sort(key=lambda x: x['Key'])
            target_key = files[0]['Key']
                # S3에서 파일 읽기
            obj = s3_client.get_object(Bucket=bucket_name, Key=target_key)
            data = json.loads(obj['Body'].read().decode('utf-8'))

            # Presigned URL 변환 함수
            def convert_to_presigned_url(url_string):
                """S3 URL을 Presigned URL로 변환"""
                if not url_string or not isinstance(url_string, str):
                    return url_string

                # S3 URL 패턴 체크: https://bucket.s3.region.amazonaws.com/key
                s3_pattern = r'https://([^.]+)\.s3\.([^.]+)\.amazonaws\.com/(.+)'
                match = re.match(s3_pattern, url_string)

                if match:
                    bucket, region, key = match.groups()
                    try:
                        presigned_url = s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': bucket, 'Key': key},
                            ExpiresIn=3600  # 1시간
                        )
                        print(f"🔗 Presigned URL 생성: {key[:50]}... -> 1시간 유효")
                        return presigned_url
                    except Exception as e:
                        print(f"⚠️ Presigned URL 생성 실패 ({key}): {e}")
                        return url_string

                return url_string

            # 모든 S3 URL 수집 및 Presigned URL로 변환
            original_s3_urls = []  # 원본 S3 URL 수집 (삭제용)

            if 'scenes' in data and isinstance(data['scenes'], list):
                for scene in data['scenes']:
                    # location (배경 영상) URL 변환
                    if 'location' in scene:
                        original_url = scene['location']
                        if original_url and isinstance(original_url, str) and 's3.amazonaws.com' in original_url:
                            original_s3_urls.append(original_url)
                        scene['location'] = convert_to_presigned_url(original_url)

                    # sequences 내부의 URL도 변환 (혹시 오디오/이미지 URL이 있을 경우)
                    if 'sequences' in scene and isinstance(scene['sequences'], list):
                        for seq in scene['sequences']:
                            if 'audio_url' in seq:
                                original_url = seq['audio_url']
                                if original_url and isinstance(original_url, str) and 's3.amazonaws.com' in original_url:
                                    original_s3_urls.append(original_url)
                                seq['audio_url'] = convert_to_presigned_url(original_url)
                            if 'image_url' in seq:
                                original_url = seq['image_url']
                                if original_url and isinstance(original_url, str) and 's3.amazonaws.com' in original_url:
                                    original_s3_urls.append(original_url)
                                seq['image_url'] = convert_to_presigned_url(original_url)

            # URL 치환 (기존 로직 유지)
            base_url = os.getenv('BASE_URL', 'http://skn18-3-dev-alb-806066579.ap-northeast-2.elb.amazonaws.com')
            json_str = json.dumps(data, ensure_ascii=False).replace("http://127.0.0.1:8000", base_url).replace("http://localhost:8000", base_url)
            data = json.loads(json_str)

            # S3 미디어 URL들을 별도 파일로 저장 (나중에 정리용)
            if original_s3_urls:
                cleanup_filename = target_key.replace('pending_scripts/', 'cleanup_queue/').replace('.json', '_cleanup.txt')
                cleanup_content = '\n'.join(original_s3_urls)
                try:
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=cleanup_filename,
                        Body=cleanup_content.encode('utf-8'),
                        ContentType='text/plain'
                    )
                    print(f"🗂️ 정리 대기 파일 생성: {cleanup_filename} ({len(original_s3_urls)}개 URL)")
                except Exception as e:
                    print(f"⚠️ 정리 파일 생성 실패: {e}")

            print(f"📦 수집된 미디어 URL {len(original_s3_urls)}개")

            # S3에서 스크립트 파일 삭제
            s3_client.delete_object(Bucket=bucket_name, Key=target_key)
            print(f"✅ S3 script 전송 및 삭제 완료: {target_key}")

            return Response(data, status=200)

        except Exception as e:
            print(f"❌ S3 script 읽기 실패: {e}")
            # S3 실패 시 로컬 fallback
            save_dir = os.path.join(settings.MEDIA_ROOT, 'pending_scripts')
            files = glob.glob(os.path.join(save_dir, "*.json"))
            if not files: return Response(status=404)
            files.sort()
            target_file = files[0]
            with open(target_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            base_url = os.getenv('BASE_URL', 'http://skn18-3-dev-alb-806066579.ap-northeast-2.elb.amazonaws.com')
            json_str = json.dumps(data, ensure_ascii=False).replace("http://127.0.0.1:8000", base_url).replace("http://localhost:8000", base_url)
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
        from config.storage_backends import upload_video, upload_thumbnail
        import boto3
        import re

        thumbnail_url = None
        video_url = None
        use_s3 = getattr(settings, 'USE_S3', False)
        base_url = os.getenv('BASE_URL', 'http://skn18-3-dev-alb-806066579.ap-northeast-2.elb.amazonaws.com')

        if 'thumbnail_file' in request.FILES:
            thumb = request.FILES['thumbnail_file']

            if use_s3:
                thumbnail_url = upload_thumbnail(thumb, thumb.name)
            else:
                t_dir = 'thumbnails'
                os.makedirs(os.path.join(settings.MEDIA_ROOT, t_dir), exist_ok=True)
                t_name = f"{int(time.time())}_thumb{os.path.splitext(thumb.name)[1]}"
                t_path = default_storage.save(os.path.join(t_dir, t_name), thumb)
                thumbnail_url = f"{base_url}{settings.MEDIA_URL}{t_path}"

        if 'video_file' in request.FILES:
            video = request.FILES['video_file']

            if use_s3:
                video_url = upload_video(video, video.name)
            else:
                v_dir = 'videos'
                os.makedirs(os.path.join(settings.MEDIA_ROOT, v_dir), exist_ok=True)
                v_name = f"{int(time.time())}_{video.name}"
                v_path = default_storage.save(os.path.join(v_dir, v_name), video)
                video_url = f"{base_url}{settings.MEDIA_URL}{v_path}"

            data = {
                'title': request.data.get('title'),
                'video_url': video_url,
                'tags': request.data.getlist('tags[]') if 'tags[]' in request.data else [],
                'thumbnail_url': thumbnail_url
            }
        else:
            data = request.data.copy()
            if thumbnail_url: data['thumbnail_url'] = thumbnail_url

        # ========== S3 미디어 파일 정리 (cleanup_queue에서 가장 오래된 항목 처리) ==========
        try:
            s3_client = boto3.client('s3')
            script_bucket = 'skn18-3-dev-scripts-533124807326'
            cleanup_prefix = 'cleanup_queue/'

            # cleanup_queue에서 가장 오래된 파일 찾기
            response = s3_client.list_objects_v2(Bucket=script_bucket, Prefix=cleanup_prefix)

            if 'Contents' in response and len(response['Contents']) > 1:
                cleanup_files = [obj for obj in response['Contents'] if obj['Key'] != cleanup_prefix]

                if cleanup_files:
                    # 가장 오래된 cleanup 파일 선택
                    cleanup_files.sort(key=lambda x: x['Key'])
                    cleanup_key = cleanup_files[0]['Key']

                    # cleanup 파일 읽기
                    obj = s3_client.get_object(Bucket=script_bucket, Key=cleanup_key)
                    urls_to_delete = obj['Body'].read().decode('utf-8').strip().split('\n')

                    deleted_count = 0
                    for url in urls_to_delete:
                        url = url.strip()
                        if not url:
                            continue

                        # S3 URL 파싱
                        s3_pattern = r'https://([^.]+)\.s3\.([^.]+)\.amazonaws\.com/(.+)'
                        match = re.match(s3_pattern, url)

                        if match:
                            bucket, _, key = match.groups()
                            try:
                                s3_client.delete_object(Bucket=bucket, Key=key)
                                deleted_count += 1
                                print(f"🗑️ S3 미디어 파일 삭제: s3://{bucket}/{key}")
                            except Exception as e:
                                print(f"⚠️ S3 파일 삭제 실패 ({key}): {e}")

                    # cleanup 파일도 삭제
                    s3_client.delete_object(Bucket=script_bucket, Key=cleanup_key)
                    print(f"✅ 정리 완료: {deleted_count}개 파일 삭제, cleanup 파일 제거: {cleanup_key}")

        except Exception as e:
            print(f"❌ S3 미디어 정리 중 에러: {e}")
            # 에러가 나도 비디오 업로드는 계속 진행

        # video_id가 제공되면 해당 Video 업데이트
        # 없으면 가장 최근에 생성된 Video를 찾아서 video_url 업데이트
        video_id = request.data.get('video_id')

        if video_id:
            try:
                video = Video.objects.get(id=video_id)
            except Video.DoesNotExist:
                return Response({'error': f'Video with id {video_id} not found'}, status=404)
        else:
            # video_id가 없으면 가장 최근에 생성된 Video 찾기
            # video_url이 null이거나 temp 버킷 URL인 Video 찾기
            video = Video.objects.filter(
                video_url__isnull=True
            ).order_by('-upload_date').first()

            if not video:
                # null인 Video가 없으면 temp URL을 가진 가장 최근 Video 찾기
                video = Video.objects.filter(
                    video_url__startswith='https://skn18-3-dev-temp.s3.'
                ).order_by('-upload_date').first()

            if not video:
                # 업데이트할 Video가 없으면 새로 생성
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                return Response({'data': VideoSerializer(serializer.instance).data, 'message': 'ok'}, status=201)

        # 찾은 Video의 video_url 업데이트
        if video_url:
            video.video_url = video_url
        if thumbnail_url and not video.thumbnail_url:
            video.thumbnail_url = thumbnail_url
        video.save()

        return Response({'data': VideoSerializer(video).data, 'message': 'Video updated successfully'}, status=200)

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
    parser_classes = [MultiPartParser, FormParser]

    def update(self, request, *args, **kwargs):
        from config.storage_backends import upload_thumbnail

        instance = self.get_object()
        data = request.data.copy()

        # 썸네일 파일 업로드 처리 (S3)
        if 'thumbnail_file' in request.FILES:
            thumb = request.FILES['thumbnail_file']
            thumbnail_url = upload_thumbnail(thumb, thumb.name)
            data['thumbnail_url'] = thumbnail_url

        # tags[] 처리
        if 'tags[]' in request.data:
            data['tags'] = request.data.getlist('tags[]')

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({'data': VideoSerializer(serializer.instance).data, 'message': 'ok'})

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