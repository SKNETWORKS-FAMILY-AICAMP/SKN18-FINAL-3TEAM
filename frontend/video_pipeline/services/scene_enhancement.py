"""
장면 강화 서비스 모듈
- 시대에 맞는 배경 요소 자동 추가
- 역사적 배경 세부사항 강화
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API for Text Generation
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_text_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_text_model = None


def enhance_scene_with_era_details(scene_text: str, use_gemini_analysis: bool = False) -> str:
    """
    Add era-appropriate details to scene description (배경만, 캐릭터 없음)
    
    Args:
        scene_text: 원본 장면 텍스트
        use_gemini_analysis: Gemini를 사용한 상세 분석 여부
    
    Returns:
        강화된 장면 텍스트
    """
    if use_gemini_analysis and gemini_text_model:
        try:
            print(f"[*] Gemini로 시대 분석 중...")
            analysis_prompt = f"""다음은 역사적 장면 묘사입니다. 이 장면의 시대와 상황을 분석하여 적절한 배경 요소, 건축물, 환경을 추가해주세요.

장면: {scene_text}

다음 형식으로 답변해주세요:
- 시대: [시대명]
- 건축물: [구체적인 건축물 설명]
- 환경: [환경 요소들]
- 배경: [배경 요소들]
- 분위기: [전체적인 분위기]"""

            response = gemini_text_model.generate_content(analysis_prompt)
            analysis = response.text.strip()
            print(f"[+] Gemini 분석 완료")
            enhanced = f"{scene_text}. Historical background details: {analysis}"
            return enhanced
        except Exception as e:
            print(f"[!] Gemini 분석 실패: {e}, 원본 사용")
            return scene_text

    # Simple enhancement
    enhanced = f"{scene_text}. Historical Joseon Dynasty period setting with authentic architecture and environment."
    print(f"[+] 장면 자동 강화 완료 (배경만)")
    return enhanced

