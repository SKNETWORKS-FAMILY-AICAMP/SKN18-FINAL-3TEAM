"""
이미지 생성 서비스 모듈
- Gemini Image API를 사용한 배경 이미지 생성
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API for Image Generation
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None

# ============================================
# COMMON STYLE GUIDE (Applied to all scenes)
# ============================================
COMMON_STYLE = """FIXED ART STYLE FOR ALL SCENES - Treat this as a consistent visual style guide for an animated series.

📐 CORE VISUAL IDENTITY (MUST BE IDENTICAL ACROSS ALL SCENES):

**ART TECHNIQUE**: 
- Soft anime/animated illustration painting style
- Digital painting with smooth brush strokes
- Semi-realistic backgrounds with stylized anime aesthetic
- Painterly but clean (not sketchy or rough)
- Medium detail level - not photorealistic, not overly simplified

**COLOR PALETTE** (Use this exact palette):
- Base: Cool blue/gray atmospheric tones (RGB: 140-180 in blue/gray range)
- Accent: Muted desaturated colors for structures and objects
- Lighting: Cold dramatic lighting with blue undertones
- Avoid: Pure blacks, pure whites, oversaturated colors
- Consistency: Same color temperature across all scenes

**LIGHTING STYLE** (Always use):
- Soft diffused atmospheric lighting
- Gentle shadows with soft edges (not harsh contrast)
- Atmospheric haze/fog for depth
- Consistent light direction within each scene
- Cinematic but gentle quality

**DETAIL LEVEL** (Maintain this balance):
- Architecture: Medium detail, historically accurate but stylized
- Environment: Atmospheric perspective with depth
- Foreground: Clear and defined but not overly detailed
- Background: Softer with atmospheric fade
- NO photorealistic textures or excessive detail

**COMPOSITION RULES**:
- 16:9 widescreen ratio
- Cinematic framing
- Balanced composition with visual interest
- Environmental storytelling

**ATMOSPHERE**:
- Joseon Dynasty period (16th century Korea)
- Dramatic historical war atmosphere
- Cold blue/gray tone for mood consistency
- Atmospheric depth with layers
- Unified emotional tone

**CONSISTENCY RULES** (CRITICAL):
- All scenes must look like they're from the SAME animated series
- Same painting technique in every scene
- Same color grading and temperature
- Same level of detail and stylization
- Viewer should recognize it's the same artist/style

**REFERENCE STYLE**: Think high-quality historical anime backgrounds (like "Kingdom" anime or similar) - historically grounded but artistically consistent, atmospheric but not overly realistic, dramatic but visually cohesive.

IMPORTANT: NO TEXT, NO CAPTIONS, NO KOREAN CHARACTERS, NO SUBTITLES in the image. Pure visual illustration only."""


def generate_image_with_gemini(prompt: str, output_path: str, apply_common_style: bool = True) -> str:
    """
    Generate background image using Google Gemini Image API
    
    Args:
        prompt: 이미지 생성 프롬프트
        output_path: 출력 이미지 경로
        apply_common_style: 공통 스타일 가이드 적용 여부
    
    Returns:
        생성된 이미지 경로
    """
    if not gemini_client:
        print(f"[-] Gemini API 키가 설정되지 않았습니다. 플레이스홀더 이미지 생성")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img = Image.new('RGB', (1024, 576), color=(200, 220, 240))
        img.save(output_path)
        return output_path
    
    if apply_common_style:
        style_consistency = """CRITICAL STYLE CONSISTENCY:
- This is ONE scene from an animated series - maintain EXACT same art style as all other scenes
- Same painting technique, same brush strokes, same level of detail
- Same color palette and color temperature (cool blue/gray)
- Same lighting approach (soft diffused atmospheric)
- All backgrounds must look like they were painted by the SAME artist for the SAME series

CHARACTER COMPOSITION RULE (IMPORTANT):
- Background crowds, soldiers, armies in the distance = OK (small, not detailed)
- NO prominent main character in foreground or center
- NO close-up faces or detailed individual characters
- Keep human figures small and as part of the background/environment
- This is a BACKGROUND scene - main character will be composited separately

NO TEXT, NO KOREAN CHARACTERS, NO CAPTIONS anywhere in the image."""
        
        full_prompt = f"{COMMON_STYLE} {prompt}. {style_consistency}"
        print(f"[*] 🎨 고정 스타일 가이드 + 배경 인물만 허용 + NO TEXT")
    else:
        full_prompt = prompt

    print(f"[*] Generating background image with Gemini Image: {full_prompt[:100]}...")

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[full_prompt],
            config=types.GenerateContentConfig(
                response_modalities=['Image'],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",
                )
            )
        )

        for part in response.parts:
            if part.text is not None:
                print(f"[*] Gemini response text: {part.text}")
            elif part.inline_data is not None:
                image = part.as_image()
                # 디렉토리 생성
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                image.save(output_path)
                print(f"[+] Background image saved: {output_path}")
                return output_path

        raise Exception("No image generated")

    except Exception as e:
        print(f"[-] Gemini Image API error: {e}")
        print(f"[!] Creating placeholder image")
        # 디렉토리 생성
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img = Image.new('RGB', (1024, 576), color=(200, 220, 240))
        img.save(output_path)
        return output_path

