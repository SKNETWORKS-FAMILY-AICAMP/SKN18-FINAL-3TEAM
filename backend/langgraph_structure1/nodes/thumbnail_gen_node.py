"""
썸네일 생성 노드
- nanobanana API (Gemini Image API)를 사용하여 썸네일 이미지 생성
- 대본의 제목을 기반으로 썸네일 프롬프트 생성
- minji&minseok.png 캐릭터를 주인공으로 사용
- 조선시대 배경, 16:9 비율
"""

import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from django.conf import settings
from backend.langgraph_structure1.state import GraphState
from google import genai
from google.genai import types
from PIL import Image

# Load environment variables
load_dotenv()

# Gemini API 설정 (백그라운드 이미지 생성과 동일한 방식)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API for Image Generation
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None

# 캐릭터 이미지 경로 (프로젝트 루트 기준)
# BASE_DIR은 backend/django이므로, BASE_DIR.parent.parent가 프로젝트 루트
if hasattr(settings, 'BASE_DIR'):
    project_root = settings.BASE_DIR.parent.parent
else:
    project_root = Path(__file__).resolve().parent.parent.parent.parent

CHARACTER_IMAGE_PATH = "https://skn18-3-dev-frontend-533124807326.s3.ap-northeast-2.amazonaws.com/videos/minji%26minseok.png"


def generate_thumbnail_prompt(title: str) -> str:
    """
    대본 제목을 기반으로 썸네일 프롬프트 생성
    
    Args:
        title: 영상 제목
        
    Returns:
        썸네일 생성 프롬프트
    """
    prompt = f"""Create a dynamic thumbnail image for a historical Korean drama video titled "{title}".

MAIN CHARACTERS (Minji & Minseok - 3D chibi style):
- **3D rendered chibi style** - smooth, polished 3D models with soft curves and glossy finish
- **EXTREMELY LARGE HEADS, VERY SMALL BODIES** - head-to-body ratio 1:1.5 or 1:2 (2.5 head-to-body ratio)
- **Large, exaggerated faces** - faces should be very large and dominant with exaggerated proportions
- **Dynamic, expressive faces** - faces should show dynamic, lively expressions (excitement, curiosity, wonder, joy, surprise) - very expressive and animated
- **Dynamic, energetic movements** - characters should be in active, dynamic poses (pointing, examining, running, jumping, reaching, interacting with objects) - avoid static poses
- **Clothing**: Characters should wear clothing appropriate to the story/situation in "{title}" - NOT the same clothes as the reference image (minji&minseok.png). Adapt hanbok or period-appropriate clothing to match the story context and situation
- **Characters**: Minji (girl with braided brown hair) and/or Minseok (boy with black hair) - choose 1-2 based on composition

BACKGROUND CHARACTERS (OPTIONAL - only if needed):
- **Realistic human proportions ONLY** - head-to-body ratio 1:7 or 1:8 (normal adult proportions)
- **MUST look like real people** - normal-sized heads and bodies, realistic anatomy (NOT chibi style)
- **BLURRED/OUT OF FOCUS** - background characters must be blurred or soft-focused
- **Only include if they add meaningful context** - avoid unnecessary random people

STORY & COMPOSITION (Related to video title "{title}"):
- **Visual elements must relate to "{title}"** - include props, objects, settings related to the story
- **Characters should interact with story elements** - engage with objects/props related to the title
- **Thumbnail-optimized camera angle** - use camera angle that emphasizes main characters and key objects (dramatic angle, close-up, or dynamic perspective that highlights the focal point)
- **Main characters and key objects should stand out** - clear focal point, characters and important story elements prominent
- **16:9 aspect ratio**

SETTING & COLORS:
- **Joseon Dynasty period** - traditional Korean architecture (palaces, courtyards, traditional houses)
- **Warm color palette** - warm, inviting, cozy colors throughout
- **Natural lighting** - soft shadows and gentle lighting

CRITICAL - NO TEXT:
- **ABSOLUTELY NO TEXT, NO LETTERS, NO WORDS ANYWHERE IN THE IMAGE**
- Books, scrolls, documents must be blank or show only abstract patterns

STYLE REQUIREMENTS:
- **3D rendered style only** - do NOT use 2D anime illustration style
- **Consistent 3D rendering** - all main characters use the same 3D technique
- **Match reference image style** (minji&minseok.png) - smooth, polished, glossy finish
"""
    return prompt


def generate_thumbnail_with_nanobanana(prompt: str, output_path: str) -> str:
    """
    nanobanana API (Gemini Image API)를 사용하여 썸네일 생성
    - Minji & Minseok 캐릭터 이미지를 참조로 전달
    
    Args:
        prompt: 썸네일 생성 프롬프트
        output_path: 출력 이미지 경로
        
    Returns:
        생성된 이미지 경로
    """
    if not gemini_client:
        print(f"⚠️ [Thumbnail] Gemini API 키가 설정되지 않았습니다. 플레이스홀더 이미지 생성")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img = Image.new('RGB', (1024, 576), color=(200, 220, 240))
        img.save(output_path)
        return output_path
    
    print(f"🖼️ [Thumbnail] Gemini Image API로 썸네일 생성 중...")
    print(f"   모델: gemini-2.5-flash-image")
    
    # Minji & Minseok 캐릭터 이미지 로드 및 전달 (S3에서 boto3로 직접 읽기)
    character_image_part = None
    try:
        import boto3
        from urllib.parse import urlparse, unquote

        # S3 URL 파싱
        parsed_url = urlparse(CHARACTER_IMAGE_PATH)
        bucket_name = parsed_url.netloc.split('.')[0]  # skn18-3-dev-frontend-533124807326
        object_key = unquote(parsed_url.path.lstrip('/'))  # videos/minji&minseok.png

        print(f"   📥 캐릭터 이미지 S3 다운로드 중: {bucket_name}/{object_key}")

        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        image_bytes = response['Body'].read()

        character_image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png"
        )
        print(f"   ✅ 캐릭터 이미지 S3 다운로드 완료 ({len(image_bytes)} bytes)")
    except Exception as e:
        print(f"   ⚠️ 캐릭터 이미지 로드 실패: {e}")
    
    try:
        # 이미지와 텍스트 프롬프트를 함께 전달
        contents = []
        if character_image_part:
            contents.append(character_image_part)
        contents.append(prompt)
        
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=['Image'],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",  # 메인페이지 비디오 썸네일 비율과 동일
                )
            )
        )
        
        for part in response.parts:
            if part.text is not None:
                print(f"   [Thumbnail] Gemini response text: {part.text}")
            elif part.inline_data is not None:
                image = part.as_image()
                # 디렉토리 생성
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                image.save(output_path)
                print(f"   ✅ 썸네일 저장 완료: {output_path}")
                return output_path
        
        raise Exception("No image generated")
    
    except Exception as e:
        print(f"❌ [Thumbnail] Gemini Image API error: {e}")
        print(f"   ⚠️ 플레이스홀더 이미지 생성")
        # 디렉토리 생성
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img = Image.new('RGB', (1024, 576), color=(200, 220, 240))
        img.save(output_path)
        return output_path


def thumbnail_gen_node(state: GraphState) -> GraphState:
    """
    썸네일 생성 노드
    - 대본의 제목을 기반으로 썸네일 프롬프트 생성
    - nanobanana API를 사용하여 썸네일 이미지 생성
    - S3에 업로드하고 URL을 state에 저장
    """
    print("🖼️ [Thumbnail Node] 썸네일 생성 시작...")

    script_json = state.get("scene_script", {})
    title = script_json.get("title", "")

    if not title:
        print("⚠️ [Thumbnail] 제목이 없어 썸네일을 생성할 수 없습니다.")
        # 병렬 실행 시 LangGraph 오류 방지: 업데이트하는 키만 반환
        return {
            "thumbnail_url": None,
        }

    # 타임스탬프 생성
    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 임시 저장 경로 (로컬)
    temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_thumbnails")
    os.makedirs(temp_dir, exist_ok=True)

    # 파일 이름 생성
    query_type = state.get('query_type', 'gen')
    thumbnail_file_name = f"thumbnail_{query_type}_{current_time_str}.png"
    temp_full_path = os.path.join(temp_dir, thumbnail_file_name)

    try:
        # 1. 썸네일 프롬프트 생성
        thumbnail_prompt = generate_thumbnail_prompt(title)
        print(f"   📝 썸네일 프롬프트 생성 완료 (제목: {title})")

        # 2. nanobanana API로 썸네일 생성 (임시 로컬 저장)
        generate_thumbnail_with_nanobanana(thumbnail_prompt, temp_full_path)

        # 3. S3에 업로드
        from config.storage_backends import upload_thumbnail
        from django.core.files import File

        with open(temp_full_path, 'rb') as f:
            thumbnail_file = File(f, name=thumbnail_file_name)
            thumbnail_url = upload_thumbnail(thumbnail_file, thumbnail_file_name)

        # 4. 임시 파일 삭제
        if os.path.exists(temp_full_path):
            os.remove(temp_full_path)

        print(f"   ✅ 썸네일 S3 업로드 완료: {thumbnail_url}")

        # 병렬 실행 시 LangGraph 오류 방지: 업데이트하는 키만 반환
        return {
            "thumbnail_url": thumbnail_url,
        }

    except Exception as e:
        print(f"❌ [Thumbnail] 썸네일 생성 실패: {e}")
        import traceback
        print(traceback.format_exc())
        # 병렬 실행 시 LangGraph 오류 방지: 업데이트하는 키만 반환
        return {
            "thumbnail_url": None,
        }
