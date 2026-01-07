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

CHARACTER_IMAGE_PATH = project_root / "frontend" / "react" / "public" / "videos" / "minji&minseok.png"


def generate_thumbnail_prompt(title: str) -> str:
    """
    대본 제목을 기반으로 썸네일 프롬프트 생성
    
    Args:
        title: 영상 제목
        
    Returns:
        썸네일 생성 프롬프트
    """
    prompt = f"""Create a dynamic, engaging thumbnail image for a historical Korean drama video titled "{title}".

CHARACTER REQUIREMENTS (Inspired by minji&minseok.png reference):
1. **Character Style - CHIBI/ANIME with Large Heads**:
   - **Large, round heads** - heads should be disproportionately large compared to bodies (chibi/super deformed style)
   - **Character options** (choose 1-2 characters based on composition):
     * **Minji (Girl)**: Long brown hair styled in a **braid hanging down below the shoulders** (not over the shoulder, but hanging down), large round warm brown eyes, expressive face
     * **Minseok (Boy)**: Short straight black hair with bangs, large dark eyes, expressive face
   - **Facial features**: Large expressive eyes, tiny dot nose, small mouth
   - **3D glossy/chibi animation style** - inspired by but not limited to the reference image
   - **Dynamic, engaging expressions** - can be smiling, surprised, determined, or action-oriented

2. **Character Proportions & Poses**:
   - Head-to-body ratio: approximately 1:2 or 1:3 (head is very large)
   - Small, stout bodies
   - **DYNAMIC POSES**: Characters should be in action or expressive poses
     * Running, jumping, pointing, reaching, reading, writing, or other engaging actions
     * Avoid static standing poses - make it lively and energetic
   - Characters can be positioned anywhere in the frame (center, left, right, foreground, midground)
   - One or both characters can appear - composition is flexible

3. **Clothing & Appearance**:
   - **Traditional Korean clothing (hanbok) is preferred but can be varied**
   - Clothing can be simplified, stylized, or adapted for the scene
   - Colors can be adjusted to match the mood and composition
   - Characters should look polished and appealing (beautified/stylized)

4. **Background Characters**:
   - **Additional background people are welcome** - can include other characters in the scene
   - **Background characters MUST use DIFFERENT art style**:
     * Normal human proportions (realistic or semi-realistic)
     * Standard head-to-body ratio (approximately 1:7 or 1:8)
     * NOT chibi style - contrast with main characters
     * Can be in traditional Korean clothing (hanbok) or period-appropriate attire
   - Background characters should be:
     * Smaller in size compared to main characters
     * Less detailed than main characters
     * Positioned in midground or background
     * Support the scene but not compete with main characters
   - Examples: scholars, servants, guards, villagers, court officials, etc.

5. **Background Setting**: 
   - Joseon Dynasty period (16th century Korea)
   - Historical Korean architecture (palaces, traditional houses, courtyards, or natural settings)
   - Authentic Joseon Dynasty atmosphere and environment
   - Background should complement the dynamic character action
   - Can include background characters in the scene

6. **Composition**:
   - Thumbnail-style composition (eye-catching, clear focal point)
   - Dynamic, energetic layout with movement and action
   - Main characters (Minji/Minseok) can be positioned creatively (not fixed to center)
   - Background characters add depth and context to the scene
   - Balanced layout suitable for video thumbnail
   - 16:9 aspect ratio

7. **Art Style - DUAL STYLE APPROACH**:
   - **Main characters (Minji/Minseok)**: 
     * **Chibi/anime style with large heads** - inspired by reference but can be stylized
     * 3D rendered look with glossy finish OR 2D anime illustration style
     * Large heads, small bodies (chibi proportions)
   - **Background characters**:
     * **Normal human proportions** - realistic or semi-realistic style
     * Standard head-to-body ratio (1:7 or 1:8)
     * Can be in same art medium but different proportions
     * Less detailed, smaller, supporting role
   - Clean, polished, beautified appearance overall
   - Bright, vibrant colors
   - Main character design should be recognizable as Minji/Minseok but can be enhanced/stylized

8. **Color & Lighting**:
   - Warm, inviting colors suitable for a thumbnail
   - Good contrast to make the main characters stand out
   - Dynamic lighting that enhances the action
   - Bright and clear

9. **Mood**:
   - Energetic, dynamic, and engaging
   - Historical but approachable
   - Action-oriented or expressive
   - Professional thumbnail quality

CRITICAL - ABSOLUTELY NO TEXT:
- **ABSOLUTELY NO TEXT, NO LETTERS, NO WORDS, NO CAPTIONS, NO SUBTITLES, NO KOREAN CHARACTERS, NO ENGLISH LETTERS, NO NUMBERS**
- **NO TEXT ON CLOTHING, NO TEXT ON SIGNS, NO TEXT ON SCROLLS, NO TEXT ON BOOKS**
- **NO TEXT ANYWHERE IN THE IMAGE - COMPLETELY TEXT-FREE**
- If books, scrolls, or documents appear, they must be blank or show only abstract patterns/lines

IMPORTANT: 
- Main characters (Minji/Minseok) should be DYNAMIC and in ACTION - avoid static poses
- One or both main characters can appear - composition is flexible
- Main characters can be positioned anywhere - not fixed to center
- Clothing can vary - traditional hanbok preferred but can be adapted
- Main characters should be beautified/stylized - don't need to match reference exactly
- **Main characters: Large heads, chibi proportions - this is CRITICAL**
- **Background characters: Normal human proportions (1:7 or 1:8 ratio) - DIFFERENT art style**
- Background characters are optional but welcome - they add depth and context
- Background should clearly show Joseon Dynasty setting
- Clear visual distinction between chibi main characters and normal-proportioned background characters
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
    
    # Minji & Minseok 캐릭터 이미지 로드 및 전달
    character_image_part = None
    if CHARACTER_IMAGE_PATH.exists():
        try:
            with open(CHARACTER_IMAGE_PATH, 'rb') as f:
                image_bytes = f.read()
            character_image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/png"
            )
            print(f"   ✅ 캐릭터 이미지 로드 완료: {CHARACTER_IMAGE_PATH}")
        except Exception as e:
            print(f"   ⚠️ 캐릭터 이미지 로드 실패: {e}")
    else:
        print(f"   ⚠️ 캐릭터 이미지 파일을 찾을 수 없습니다: {CHARACTER_IMAGE_PATH}")
    
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
    - 생성된 썸네일 URL을 state에 저장
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

