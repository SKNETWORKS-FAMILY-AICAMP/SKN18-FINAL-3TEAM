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

# nanobanana API 설정
GENAI_API_VERSION = os.getenv("GENAI_API_VERSION", "v1")
MODEL_IMAGE = os.getenv("MODEL_IMAGE", "imagen-4.0-fast-generate-001 ")
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

CHARACTER_IMAGE_PATH = project_root / "frontend" / "react" / "public" / "videos" / "minji&minseok.png"


def generate_thumbnail_prompt(title: str) -> str:
    """
    대본 제목을 기반으로 썸네일 프롬프트 생성
    
    Args:
        title: 영상 제목
        
    Returns:
        썸네일 생성 프롬프트
    """
    prompt = f"""Create a thumbnail image for a historical Korean drama video titled "{title}".

REQUIREMENTS:
1. **Main Character**: Feature the character from minji&minseok.png as the protagonist
   - The character should be prominently displayed in the foreground
   - Character should have a friendly, engaging expression
   - Character should be in Joseon Dynasty traditional clothing (hanbok)

2. **Background Setting**: 
   - Joseon Dynasty period (16th century Korea)
   - Historical Korean architecture (palaces, traditional houses, or courtyards)
   - Authentic Joseon Dynasty atmosphere and environment

3. **Composition**:
   - Thumbnail-style composition (eye-catching, clear focal point)
   - Character positioned prominently but not blocking important background elements
   - Balanced layout suitable for video thumbnail
   - 16:9 aspect ratio

4. **Art Style**:
   - Soft anime/animated illustration style
   - Digital painting with smooth brush strokes
   - Semi-realistic with stylized anime aesthetic
   - Clean and polished appearance
   - Medium detail level

5. **Color & Lighting**:
   - Warm, inviting colors suitable for a thumbnail
   - Good contrast to make the character stand out
   - Soft, diffused lighting
   - Atmospheric but clear

6. **Mood**:
   - Engaging and inviting
   - Historical but approachable
   - Professional thumbnail quality

IMPORTANT: 
- NO TEXT, NO CAPTIONS, NO KOREAN CHARACTERS, NO SUBTITLES
- Pure visual illustration only
- The character from minji&minseok.png should be clearly recognizable as the main subject
- Background should clearly show Joseon Dynasty setting
"""
    return prompt


def generate_thumbnail_with_nanobanana(prompt: str, output_path: str) -> str:
    """
    nanobanana API (Gemini Image API)를 사용하여 썸네일 생성
    
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
    
    print(f"🖼️ [Thumbnail] nanobanana API로 썸네일 생성 중...")
    print(f"   모델: {MODEL_IMAGE}, API 버전: {GENAI_API_VERSION}")
    
    try:
        response = gemini_client.models.generate_content(
            model=MODEL_IMAGE,
            contents=[prompt],
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
    - 생성된 썸네일 URL을 state에 저장
    """
    print("🖼️ [Thumbnail Node] 썸네일 생성 시작...")
    
    script_json = state.get("scene_script", {})
    title = script_json.get("title", "")
    
    if not title:
        print("⚠️ [Thumbnail] 제목이 없어 썸네일을 생성할 수 없습니다.")
        return {
            **state,
            "thumbnail_url": None,
        }
    
    # 타임스탬프 생성
    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 저장할 기본 경로 (Django media/thumbnails)
    save_dir = os.path.join(settings.MEDIA_ROOT, "thumbnails")
    os.makedirs(save_dir, exist_ok=True)
    
    # 파일 이름 생성
    query_type = state.get('query_type', 'gen')
    thumbnail_file_name = f"thumbnail_{query_type}_{current_time_str}.png"
    thumbnail_full_path = os.path.join(save_dir, thumbnail_file_name)
    
    try:
        # 1. 썸네일 프롬프트 생성
        thumbnail_prompt = generate_thumbnail_prompt(title)
        print(f"   📝 썸네일 프롬프트 생성 완료 (제목: {title})")
        
        # 2. nanobanana API로 썸네일 생성
        generate_thumbnail_with_nanobanana(thumbnail_prompt, thumbnail_full_path)
        
        # 3. URL 생성
        base_url = settings.MY_SERVER_URL.rstrip('/')
        media_url = settings.MEDIA_URL.strip('/')
        thumbnail_url = f"{base_url}/{media_url}/thumbnails/{thumbnail_file_name}"
        
        print(f"   ✅ 썸네일 URL 생성: {thumbnail_url}")
        
        return {
            **state,
            "thumbnail_url": thumbnail_url,
        }
        
    except Exception as e:
        print(f"❌ [Thumbnail] 썸네일 생성 실패: {e}")
        import traceback
        print(traceback.format_exc())
        return {
            **state,
            "thumbnail_url": None,
        }

