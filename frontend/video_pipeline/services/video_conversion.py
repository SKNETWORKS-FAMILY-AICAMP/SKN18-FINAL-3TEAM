# services/video_conversion.py

import os
import time
from pathlib import Path
from dotenv import load_dotenv
import fal_client
import requests

load_dotenv()
FAL_KEY = os.getenv("FAL_KEY")
if FAL_KEY:
    os.environ['FAL_KEY'] = FAL_KEY

def create_video_from_image_fal(image_path: str, output_path: str, prompt: str = None, resolution: str = "1080p", duration: int = 5) -> str:
    if not FAL_KEY:
        print(f"❌ [오류] FAL_KEY 없음")
        return None

    # 노드에서 이미 "majestic palace..." 처럼 구체적인 프롬프트가 넘어옴
    if prompt is None:
        prompt = "cinematic atmosphere, gentle motion"

    print(f"[*] Video Generation: {Path(image_path).name}")
    
    try:
        # 1. 이미지 업로드
        if not Path(image_path).exists(): return None
        image_url = fal_client.upload_file(image_path)
        
        # 2. 모드 결정 (이분법: 전투 vs 비전투)
        # 노드에서 보낸 프롬프트에 'battle', 'war' 등이 있으면 전투 모드로 작동
        safe_prompt = prompt.lower()
        war_keywords = ['battle', 'war', 'attack', 'explosion', 'fire', 'combat']
        is_war_mode = any(k in safe_prompt for k in war_keywords)
        
        if is_war_mode:
            # [전투 모드] 역동성 추가
            # 노드의 프롬프트(prompt)를 앞에 두고, 효과를 뒤에 덧붙임
            final_prompt = (
                f"{prompt}, "
                "dynamic motion, sparks, smoke, debris, "
                "cinematic war atmosphere"
            )
            print(f"    ⚔️ Mode: [WAR] - 역동적 움직임 적용")
        else:
            # [안정 모드] Tension, Royal, Nature 모두 여기 포함
            # 핵심: 구체적인 묘사는 노드의 프롬프트(prompt)를 100% 신뢰하고,
            # 여기서는 '흔들림 방지'와 '인물 억제'만 담당함.
            final_prompt = (
                f"{prompt}, "
                "static camera, slow and smooth motion, "
                "highly detailed, atmospheric, "
                "NO HUMANS, NO CHARACTERS" # 안전장치
            )
            print(f"    🛡️ Mode: [STABLE] - 분위기 유지, 움직임 안정화")

        # 네거티브 프롬프트 (공통)
        negative_prompt = (
            "distortion, morphing, people flying, "
            "modern elements, text, subtitles, watermark, "
            "glitch, low quality, messy"
        )
        
        # 3. API 호출
        arguments = {
            "prompt": final_prompt,
            "image_url": image_url,
            "resolution": resolution,
            "duration": str(duration),
            "negative_prompt": negative_prompt,
            "enable_prompt_expansion": False, # 중요: AI가 멋대로 덧붙이는 것 방지
            "seed": 42
        }
        
        # ... (이하 API 호출 및 다운로드 로직 기존과 동일) ...
        handler = fal_client.submit("fal-ai/wan-25-preview/image-to-video", arguments=arguments)
        
        # (대기 및 다운로드 코드 생략 - 기존과 동일하게 사용하세요)
        # ...
        
        # 전체 코드가 필요하면 이전에 드린 코드의 뒷부분을 그대로 붙이시면 됩니다.
        
        # 편의를 위해 뒷부분(대기/다운로드) 요약:
        start_time = time.time()
        while True:
            status = handler.status()
            if "COMPLETED" in str(status).upper(): break
            if "FAILED" in str(status).upper(): return None
            time.sleep(3)
            
        result = handler.get()
        video_url = result['video']['url']
        response = requests.get(video_url)
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        return output_path

    except Exception as e:
        print(f"❌ Error: {e}")
        return None