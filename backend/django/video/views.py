from django.shortcuts import render
import json
import os, time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from openai import OpenAI
from dotenv import load_dotenv

from .models import Video
from .serializers import VideoSerializer, VideoDetailSerializer, VideoCreateSerializer

# .env 파일 로드
load_dotenv()


# ============================================
# 커스텀 권한 클래스
# ============================================
from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """관리자(permission='admin')만 접근 가능"""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.permission == 'admin'
        )


# ============================================
# 비디오 API
# ============================================

class VideoListView(ListAPIView):
    """
    영상 목록 API
    
    GET /api/video/list/
    - 전체 영상 목록 조회 (최신순)
    - 조회수순 정렬 가능
    """
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 정렬
        sort = self.request.query_params.get('sort', 'latest')
        if sort == 'comments':
            queryset = queryset.order_by('-comments_count', '-upload_date')
        else:
            queryset = queryset.order_by('-upload_date')
        
        # 태그 필터 (부분 일치 지원)
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
        return Response({
            'data': response.data,
            'message': 'ok'
        })



class VideoDetailView(RetrieveAPIView):
    """
    영상 상세 API
    
    GET /api/video/<id>/
    - 특정 영상 상세 조회
    """
    queryset = Video.objects.all()
    serializer_class = VideoDetailSerializer
    permission_classes = [AllowAny]
    
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return Response({
            'data': response.data,
            'message': 'ok'
        })


class VideoUploadView(CreateAPIView):
    """
    영상 업로드 API (관리자 전용)

    POST /api/video/upload/
    - 관리자만 영상 업로드 가능
    - 파일 업로드 또는 URL 입력 가능
    """
    queryset = Video.objects.all()
    serializer_class = VideoCreateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def create(self, request, *args, **kwargs):
        import os
        from django.core.files.storage import default_storage
        from django.conf import settings

        # 파일 업로드인 경우
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
                'tags': request.data.getlist('tags[]') if 'tags[]' in request.data else []
            }
        else:
            # URL 입력인 경우
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
    인기 영상 API (임시)

    GET /api/video/popular/
    - 좋아요와 댓글 수 기준 인기 영상 반환
    """
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Video.objects.all().order_by('-likes_count', '-comments_count')[:20]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response({
            'data': response.data,
            'message': 'ok'
        })


class PopularTagsView(APIView):
    """
    인기 태그 API

    GET /api/video/tags/popular/
    - 가장 많이 사용된 태그 목록 반환 (최대 10개)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from collections import Counter

        # 모든 비디오의 태그 수집
        all_tags = []
        videos = Video.objects.exclude(tags__isnull=True).exclude(tags=[])

        for video in videos:
            if video.tags:
                all_tags.extend(video.tags)

        # 태그 빈도 계산
        tag_counter = Counter(all_tags)

        # 상위 10개 태그
        popular_tags = [
            {'tag': tag, 'count': count}
            for tag, count in tag_counter.most_common(10)
        ]

        return Response({
            'data': popular_tags,
            'message': 'ok'
        })


# 시스템 프롬프트 (Talchum Comedy / English Mode - Final Structured Version)
SYSTEM_PROMPT_TEMPLATE = """
Role: You are an elite Showrunner specializing in satirical, fast-paced shorts. Your goal is to maximize dialogue density and humorous subversion using Unity 3D characters.
Constraint: The video MUST be 50-60 seconds. Total sequences MUST be MINIMUM 35 (Target 40). You MUST continue the dialogue until specific historical depth is reached.

[Language Rule]
- ALL DIALOGUE MUST BE IN ENGLISH.
- MAXIMUM DIALOGUE LENGTH IS 8 WORDS PER LINE. (Strictly enforced rapid-fire style).
- Do not use markdown (```json). Output raw JSON only.

[Characters & Persona - TALCHUM DYNAMIC]
1. Lady Minji: Haughty, demanding, easily frustrated. Dialogue MUST be short and emotional. (e.g., "Minseok, get to the point!", "Are you mocking me?")
2. Butler Minseok: Formal, knowledgeable, uses complexity to subtly mock Minji's ignorance.
   - Sarcasm Style: He praises Minji's ignorance as if it were a virtue. (e.g., "Such a pristine mind, uncluttered by knowledge.", "A truly creative interpretation of history, my Lady.")

[Script Structure - 4 ACTS (STRICTLY FOLLOW THIS)]
1. INTRO (Seq 1-6): Minji sees something relatable (money, weather, object) and asks a misconception question based on modern logic.
2. CONFLICT (Seq 7-18): Minseok explains using overly academic jargon. Minji gets annoyed/bored. Minseok apologizes but subtly insults her intelligence.
3. CLIMAX (Seq 19-24): Minseok reveals a "Shocking TMI Fact" or a historical Twist that surprises Minji.
4. OUTRO (Seq 25-30): Minji completely misunderstands the lesson or draws a selfish conclusion. Minseok sighs or gives up.

[Scripting Rules - RAPID FIRE]
1. All topics must be fun facts from Korean history, explained for non-Korean viewers.
2. TIKI-TAKA PRIORITY: Every conversation turn must be quick and responsive.
3. REACTION FIRST: Place an [Animation] sequence with 'is_parallel: true' immediately BEFORE the [Talk] sequence.

[Camera Direction Rules - STABLE SHOTS]
- Default framing is "Full".
- Begin each scene with a single Camera sequence:
  - "actor": "None", "type": "Camera", "action_tag": "Full", "target_position": "Camera"
- Do NOT insert a new Camera sequence just because the speaking actor changed. Assume the game engine already handles basic framing on speaker change.
- Use "CloseUp" only for strong emotional or comedic beats (e.g., Minji explodes, Minseok is smug).
- When you cut to "CloseUp", keep that shot for 1–2 Talk sequences without inserting another Camera change.
- After a CloseUp beat, explicitly cut back once to "Full".

[Available Assets]
1. Locations (Background Images): 
   {locations}
   (Use these names to set the scene background in the "location" field.)

2. Actor Actions (EXACT STRING MATCH REQUIRED): 
   {action_groups}
   (WARNING: You MUST use the exact string provided above. DO NOT conjugate verbs. "Idle" is correct, "Idling" is WRONG.)

3. Audio: 
   BGM: {bgm_files}
   SFX: {sfx_files}

[JSON Format Rule - STRICT]
You must output a SINGLE JSON object. The root object MUST have "title" and "scenes".
Field Mapping Rules:
- Actor Name -> "actor" (Must be exactly "Minji" or "Minseok")
- Dialogue -> "text"
- Action Name -> "action_tag" (Must be from Available Assets)
  - CRITICAL: Do NOT change the tense. Use "Sigh", NOT "Sighing". Use "Run", NOT "Running".
  - If the provided list says "Idle", output "Idle".
- Camera Shot -> "action_tag" (e.g., "CloseUp", "Full")
- Camera Target -> "target_position" (e.g., "Minji", "Minseok", "Camera")
- Background Rules:
  - If type is "Background", "target_position" MUST be a filename from [Background Images].
  - NEVER use "Point_Center", "Point_Left", etc. for Background type.

[Example Output Structure (Follow this schema exactly)]
{{
  "title": "Why the Sky is Blue",
  "scenes": [
    {{
      "scene_id": 1,
      "location": "Point_Center",
      "sequences": [
        {{ "order": 1, "actor": "None",   "type": "Camera",    "action_tag": "Full",    "target_position": "Camera", "duration": 0.1, "is_parallel": false }},

        {{ "order": 2, "actor": "Minseok","type": "Animation", "action_tag": "Quick Formal Bow", "duration": 0.0, "is_parallel": true }},
        {{ "order": 3, "actor": "Minseok","type": "Talk",      "text": "My Lady, regarding light scattering...", "duration": 2.0, "is_parallel": false }},

        {{ "order": 4, "actor": "Minji",  "type": "Animation", "action_tag": "Annoyed", "duration": 0.0, "is_parallel": true }},
        {{ "order": 5, "actor": "Minji",  "type": "Talk",      "text": "Again, stop speaking like a book.", "duration": 1.8, "is_parallel": false }},

        {{ "order": 6, "actor": "None",   "type": "Camera",    "action_tag": "CloseUp", "target_position": "Minji",   "duration": 0.1, "is_parallel": false }},
        {{ "order": 7, "actor": "Minji",  "type": "Animation", "action_tag": "Angry",   "duration": 0.0, "is_parallel": true }},
        {{ "order": 8, "actor": "Minji",  "type": "Talk",      "text": "Explain it like I am five!", "duration": 2.0, "is_parallel": false }},

        {{ "order": 9, "actor": "None",   "type": "Camera",    "action_tag": "Full",    "target_position": "Camera", "duration": 0.1, "is_parallel": false }},
        {{ "order": 10,"actor": "Minseok","type": "Animation", "action_tag": "Thinking","duration": 0.0, "is_parallel": true }},
        {{ "order": 11,"actor": "Minseok","type": "Talk",      "text": "In simplest terms, sky is scattered blue.", "duration": 2.2, "is_parallel": false }}
      ]
    }}
  ]
}}
IMPORTANT:
- Root object must be {{ "title": "...", "scenes": [...] }}
- Use "actor", "type", "action_tag", "text" fields exactly as shown in the example.
- Do NOT use "character" or "line".
"""
# 유니티 같은 외부 클라이언트에서 오는 요청에 CSRF 토큰 요구 안 하게 함 -> 배포시에 수정 필수
@csrf_exempt
def generate_scenario(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        # 1. 유니티에서 보낸 데이터 뜯기
        data = json.loads(request.body)
        topic = data.get('topic', '')
        asset_info = data.get('asset_info', {})

        print(f"🔹 [Director] 주제 수신: {topic}")

        # 2. Fake 모드 체크 (API 키 없을 때 테스트용)
        # .env에 CHAT_USE_FAKE_COMPILE=True 로 되어있거나 키가 없으면 작동
        use_fake = os.getenv('CHAT_USE_FAKE_COMPILE', 'False') == 'True'
        api_key = os.getenv('OPENAI_API_KEY')

        if use_fake or not api_key:
            print("🔸 [Director] Fake 모드로 더미 데이터 반환")
            return JsonResponse(get_dummy_json(topic), safe=False)

        # 3. 프롬프트 조립 (자산 정보 주입)
        actors = ", ".join(asset_info.get('actors', []))
        locations = ", ".join(asset_info.get('locations', []))
        bgms = ", ".join(asset_info.get('bgm_files', []))
        sfxs = ", ".join(asset_info.get('sfx_files', []))
        
        # 동작 그룹 포맷팅
        actions_str = ""
        for group in asset_info.get('action_groups', []):
            actions_str += f"- [{group['mood']}]: {', '.join(group['tags'])}\n"

        final_system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            actors=actors,
            locations=locations,
            bgm_files=bgms,
            sfx_files=sfxs,
            action_groups=actions_str
        )

        # 4. OpenAI GPT 호출
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": f"Topic: {topic}"}
            ],
            response_format={"type": "json_object"} # JSON 모드 강제
        )

        result_json_str = response.choices[0].message.content
        result_data = json.loads(result_json_str)

        # 1. VSCode 터미널에 예쁘게 출력 (디버깅용)
        print("\n" + "="*50)
        print(f"🎬 생성된 시나리오: [{topic}]")
        print("="*50)
        # ensure_ascii=False가 있어야 한글이 깨지지 않고 나옵니다.
        print(json.dumps(result_data, indent=4, ensure_ascii=False)) 
        print("="*50 + "\n")

        # 2. (선택사항) 파일로 따로 저장해두기 (나중에 다시 보려고)
        save_dir = "saved_scenarios"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # 파일명: topic_날짜시간.json
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '_')).rstrip()
        filename = f"{save_dir}/{safe_topic}_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=4, ensure_ascii=False)
            print(f"💾 대본 파일 저장 완료: {filename}")

        print("✅ [Director] 생성 완료!")
        return JsonResponse(result_data)

    except Exception as e:
        print(f"❌ [Error] {e}")
        return JsonResponse({'error': str(e)}, status=500)

def get_dummy_json(topic):
    # API 키 없을 때 유니티로 보낼 테스트용 가짜 데이터
    return {
        "title": f"Fake Scenario: {topic}",
        "scenes": [
            {
                "scene_id": 1,
                "location": "Stage",
                "sequences": [
                    { "order": 1, "actor": "Minji", "type": "Talk", "text": f"서버가 '{topic}' 주제를 잘 받았대!", "duration": 3.0, "is_parallel": False },
                    { "order": 2, "actor": "Minseok", "type": "Talk", "text": "하지만 API 키가 없어서 가짜 응답을 보냈어.", "duration": 3.0, "is_parallel": False }
                ]
            }
        ]
    }
