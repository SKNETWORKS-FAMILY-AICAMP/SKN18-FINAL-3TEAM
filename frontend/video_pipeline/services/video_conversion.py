# services/video_conversion.py

import os
import time
from pathlib import Path
from dotenv import load_dotenv
import fal_client
import requests
import traceback

load_dotenv()
FAL_KEY = os.getenv("FAL_KEY")
if FAL_KEY:
    os.environ['FAL_KEY'] = FAL_KEY

def create_video_from_image_fal(image_path: str, output_path: str, prompt: str = None, resolution: str = "1080p", duration: int = 5) -> str:
    if not FAL_KEY:
        print(f"❌ [오류] FAL_KEY 없음")
        return None

    # 기본 프롬프트 설정
    if prompt is None:
        prompt = "cinematic atmosphere, gentle motion"

    print(f"[*] Video Generation Start: {Path(image_path).name}")
    
    try:
        # [DEV 기능 흡수] 1. 안전한 이미지 업로드 (상세 에러 로그)
        if not Path(image_path).exists(): 
            print(f"❌ 파일 없음: {image_path}")
            return None
            
        try:
            print(f"    [1/4] 이미지 업로드 중...")
            image_url = fal_client.upload_file(image_path)
            print(f"    ✅ 업로드 완료: {image_url[:50]}...")
        except Exception as upload_error:
            print(f"❌ [오류] 이미지 업로드 실패: {upload_error}")
            return None
        
        # [DEV 기능 흡수] 2. 정교한 키워드 분석 (전투 vs 평화)
        # 영어 및 한국어 전투 키워드
        action_keywords = [
            'battle', 'fight', 'attack', 'war', 'combat', 'charge', 'strike', 'clash',
            'siege', 'invasion', 'assault', 'defense', 'warfare',
            'arrow', 'explosion', 'cannon', 'shoot', 'gunfire', 'blast',
            '전투', '전쟁', '공격', '방어', '침략', '격전', '화살', '포탄', '폭발', '발사'
        ]

        # 평화 키워드 (전투 효과 억제용)
        peace_keywords = ['peaceful', 'serene', 'calm', 'tranquil', '평화', '평온', '고요', 'palace']
        
        safe_prompt = prompt.lower()
        has_peace = any(k in safe_prompt for k in peace_keywords)
        has_action = any(k in safe_prompt for k in action_keywords)

        # 평화 키워드가 있으면 전투 효과 강제 비활성화
        if has_peace:
            has_action = False
        
        # 3. 프롬프트 조합 (하이브리드 전략)
        if has_action:
            # [전투 모드] -> DEV 팀원의 디테일한 프롬프트 사용 (화려한 효과)
            battle_effects = (
                "PRIORITY EFFECTS: dramatic battle scene, "
                "MANY arrows flying through the air, "
                "large explosions with fire and smoke, "
                "cannon fire trails, weapon sparks, debris flying, "
                "soldiers in dynamic combat action"
            )
            # 기본 제약 (배경 유지)
            constraints = "Joseon Dynasty 16th century Korea setting, maintain composition"
            
            final_prompt = f"{prompt}, {battle_effects}, {constraints}"
            print(f"    ⚔️ Mode: [WAR] - 강력한 전투 효과 적용 (DEV Logic)")
            
        else:
            # [일반 모드] -> HEAD 작성자님의 안정성 로직 사용 (NO HUMANS 필수)
            # 유니티 배경으로 쓸 때 사람이 둥둥 떠다니면 안 되므로 이 로직이 필수적임
            final_prompt = (
                f"{prompt}, "
                "static camera, slow and smooth motion, "
                "highly detailed, atmospheric, "
                "NO HUMANS, NO CHARACTERS, empty scenery" # 사람이 배경에 박제되는 것 방지
            )
            print(f"    🛡️ Mode: [STABLE] - 인물 제거 및 안정화 (HEAD Logic)")

        # 4. 공통 네거티브 프롬프트
        negative_prompt = (
            "distortion, morphing, people flying, "
            "modern elements, text, subtitles, watermark, "
            "glitch, low quality, messy, ugly, "
            "modern buildings, cars, power lines"
        )
        
        # 5. API 호출 (Wan 2.5 모델)
        arguments = {
            "prompt": final_prompt,
            "image_url": image_url,
            "resolution": resolution,
            "duration": str(duration),
            "negative_prompt": negative_prompt,
            "enable_prompt_expansion": False, # 우리가 만든 프롬프트를 그대로 쓰기 위해 False
            "seed": 42
        }
        
        print(f"    [3/4] 영상 생성 요청 중... (모델: Wan 2.5)")
        handler = fal_client.submit("fal-ai/wan-25-preview/image-to-video", arguments=arguments)
        
        # 6. 대기 및 다운로드
        start_time = time.time()
        while True:
            status = handler.status()
            if hasattr(status, 'status'): # status 객체 처리
                 status_str = status.status
            else:
                 status_str = str(status)

            if "COMPLETED" in status_str.upper():
                break
            if "FAILED" in status_str.upper():
                print(f"❌ 영상 생성 실패: {status}")
                return None
            
            elapsed = time.time() - start_time
            if elapsed > 300: # 5분 타임아웃
                print("❌ 시간 초과")
                return None
                
            time.sleep(2)
            
        result = handler.get()
        video_url = result['video']['url']
        
        print(f"    [4/4] 다운로드 중...")
        response = requests.get(video_url)
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        print(f"    ✅ 저장 완료: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ Error in video generation: {e}")
        traceback.print_exc() # 상세 에러 출력
        return None