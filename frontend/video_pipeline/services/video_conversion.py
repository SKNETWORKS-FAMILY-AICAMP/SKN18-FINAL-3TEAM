"""
비디오 변환 서비스 모듈
- 이미지를 영상으로 변환 (fal.ai Wan 2.5 사용)
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
import fal_client
import requests

# Load environment variables
load_dotenv()

# API Keys
FAL_KEY = os.getenv("FAL_KEY")

# Configure fal.ai API
if FAL_KEY:
    os.environ['FAL_KEY'] = FAL_KEY


def create_video_from_image_fal(image_path: str, output_path: str, prompt: str = None, resolution: str = "1080p", duration: int = 5) -> str:
    """
    Wan 2.5로 이미지를 영상으로 변환 (배경 이미지용 - 캐릭터 관련 제약 없음)
    
    Args:
        image_path: 입력 이미지 경로
        output_path: 출력 영상 경로
        prompt: 영상 모션 설명 (최대 800자)
        resolution: 해상도 ("480p", "720p", "1080p")
        duration: 영상 길이 (5 또는 10초)
    
    Returns:
        생성된 영상 경로
    """
    if not FAL_KEY:
        print(f"❌ [오류] FAL_KEY가 설정되지 않았습니다.")
        return None
    
    if prompt is None:
        prompt = "smooth camera movement, cinematic, gentle motion, dramatic atmosphere"

    print(f"[*] Creating video from image: {Path(image_path).name}")
    print(f"    Video prompt: {prompt[:80]}...")
    print(f"    Settings: {resolution}, {duration}초")

    try:
        # STEP 1: 이미지 파일 확인
        if not Path(image_path).exists():
            print(f"❌ [오류] 이미지 파일이 없습니다: {image_path}")
            return None
        
        print(f"    [1/5] 이미지 파일 확인 완료: {Path(image_path).name}")
        
        # STEP 2: 이미지 업로드 (Wan 2.5 방식)
        print(f"    [2/5] 선택한 이미지 파일 업로드 중...")
        print(f"    이미지 경로: {image_path}")
        try:
            image_url = fal_client.upload_file(image_path)
            print(f"    [2/5] 이미지 업로드 완료: {image_url[:60]}...")
        except Exception as upload_error:
            print(f"❌ [오류] 이미지 업로드 실패: {upload_error}")
            print(f"    오류 타입: {type(upload_error).__name__}")
            import traceback
            print(f"    상세 오류:\n{traceback.format_exc()}")
            return None
        
        # STEP 3: Wan 2.5 API 호출
        print(f"    [3/5] fal.ai API 호출 중...")
        print(f"    모델: fal-ai/wan-25-preview/image-to-video")
        print(f"    모션 프롬프트: {prompt[:100]}...")
        
        # Unity 배경용: 자연스러운 움직임 + 전투 효과 허용
        
        # 전투/액션 효과 키워드 감지
        action_keywords = ['battle', 'fight', 'attack', 'war', 'arrow', 'fire', 'explosion', 'cannon', 'combat', 'charge', 'shoot', 'strike', 'clash', 'siege', 'gun', 'blast', 'shell', '전투', '공격', '화살', '포탄', '폭발', '발사', '총', '사격']
        has_action = any(keyword in prompt.lower() for keyword in action_keywords)
        
        # 액션 장면: 전투 효과 최우선! (맨 앞에 배치)
        if has_action:
            # 전투 효과를 가장 먼저 명시 (AI가 최우선으로 처리)
            battle_effects_priority = f"{prompt}, PRIORITY EFFECTS: dramatic battle scene with visible combat effects, MANY arrows flying through the air in multiple directions, large explosions with fire and smoke, cannon fire with dramatic smoke trails, gunfire smoke clouds, weapon sparks from clashing, debris flying from impacts, dust clouds from combat, fire effects from explosions"
            
            # 전투 동작
            combat_actions = ", soldiers in dynamic combat: actively shooting arrows, swinging swords in battle, charging with spears, engaged in fighting, running in battle formation, all on ground"
            
            # 기본 제약 (맨 뒤로)
            base_constraints = ", Joseon Dynasty 16th century Korea setting, static camera, people keep feet on ground, NO new people appearing, maintain composition"
            
            enhanced_prompt = battle_effects_priority + combat_actions + base_constraints
            print(f"    💥 전투 장면: 전투 효과 최우선 (화살, 폭발, 연기 강조)")
        else:
            # 일반 장면
            base_settings = f"{prompt}, Joseon Dynasty 16th century Korea, static camera, peaceful background movements: soldiers walking, standing guard, talking, environmental motion (flags, smoke, wind), people on ground, NO new people, maintain composition"
            enhanced_prompt = base_settings
            print(f"    🎬 일반 장면: 평화로운 배경")
        
        # 사람만 날아다니는 것 차단 (화살, 폭발 효과는 허용!)
        enhanced_negative_prompt = "PEOPLE FLYING, PEOPLE FLOATING, SOLDIERS FLYING, SOLDIERS FLOATING, HUMAN LEVITATION, person in air, person in sky, person hovering, person jumping unrealistically high, human rising up, soldier not touching ground, camera movement, camera pan, camera zoom, modern soldiers, modern military, contemporary uniforms, modern equipment, 20th/21st century, NEW PERSON APPEARING, new character entering, hero emerging from nowhere, extra people, low resolution, error, worst quality, low quality, defects, distortion, blurry"
        
        arguments = {
            "prompt": enhanced_prompt,
            "image_url": image_url,
            "resolution": resolution,
            "duration": str(duration),
            "negative_prompt": enhanced_negative_prompt,
            "enable_prompt_expansion": False,  # 프롬프트 확장 비활성화
            "enable_safety_checker": False,  # 콘텐츠 필터 비활성화
            "strength": 0.42  # 전투 효과 역동적 생성 허용 (58% 원본, 42% 변화)
        }
        
        try:
            handler = fal_client.submit(
                "fal-ai/wan-25-preview/image-to-video",
                arguments=arguments
            )
            print(f"    [3/5] API 작업 제출 완료")
        except Exception as submit_error:
            print(f"❌ [오류] API 작업 제출 실패: {submit_error}")
            print(f"    오류 타입: {type(submit_error).__name__}")
            import traceback
            print(f"    상세 오류:\n{traceback.format_exc()}")
            return None
        
        # STEP 4: 진행 상태 모니터링
        print(f"    [4/5] 영상 생성 대기 중... (약 1-3분 소요)")
        start_time = time.time()
        while True:
            try:
                status = handler.status()
                elapsed = int(time.time() - start_time)
                status_str = str(status).upper()
                
                if "COMPLETED" in status_str or "OK" in status_str:
                    print(f"    [4/5] 작업 완료! (소요 시간: {elapsed}초)")
                    break
                if "FAILED" in status_str or "ERROR" in status_str:
                    print(f"❌ [오류] 영상 생성 실패! 상태: {status}")
                    return None
                
                print(f"    [{elapsed}초] 상태: {status}...")
                time.sleep(5)
            except Exception as status_error:
                print(f"❌ [오류] 상태 확인 실패: {status_error}")
                import traceback
                print(f"    상세 오류:\n{traceback.format_exc()}")
                return None
        
        # STEP 5: 결과 가져오기 및 다운로드
        print(f"    [5/5] 영상 다운로드 준비 중...")
        try:
            result = handler.get()
            
            if result is None:
                print(f"❌ [오류] API가 None을 반환했습니다.")
                return None
            
            if not isinstance(result, dict):
                print(f"❌ [오류] 예상치 못한 응답 타입: {type(result)}")
                return None
            
            if 'video' not in result:
                print(f"❌ [오류] 응답에 'video' 키가 없습니다. 사용 가능한 키: {list(result.keys())}")
                return None
            
            if 'url' not in result['video']:
                print(f"❌ [오류] video에 'url' 키가 없습니다. 사용 가능한 키: {list(result['video'].keys())}")
                return None
            
            video_url = result['video']['url']
            print(f"    [5/5] 비디오 URL 획득: {video_url[:60]}...")
            
        except Exception as get_error:
            print(f"❌ [오류] API 결과 가져오기 실패: {get_error}")
            print(f"    오류 타입: {type(get_error).__name__}")
            import traceback
            print(f"    상세 오류:\n{traceback.format_exc()}")
            return None
        
        # 비디오 다운로드
        print(f"    [5/5] 비디오 다운로드 중...")
        try:
            response = requests.get(video_url, timeout=120)
            response.raise_for_status()
            
            # 파일 저장
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            # 파일 확인
            if Path(output_path).exists():
                saved_size = Path(output_path).stat().st_size / (1024 * 1024)
                print(f"[+] ✅ 영상 저장 완료: {output_path}")
                print(f"    파일 크기: {saved_size:.2f} MB")
                if 'seed' in result:
                    print(f"    시드: {result.get('seed')}")
                if 'actual_prompt' in result and result['actual_prompt']:
                    print(f"    실제 프롬프트: {result['actual_prompt'][:100]}...")
                return output_path
            else:
                print(f"❌ [오류] 파일 저장 후 확인 실패: {output_path}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"❌ [오류] 비디오 다운로드 타임아웃 (120초 초과)")
            print(f"    💡 팁: 네트워크 연결을 확인하거나 더 큰 타임아웃을 설정하세요.")
            return None
        except requests.exceptions.RequestException as download_error:
            print(f"❌ [오류] 비디오 다운로드 실패: {download_error}")
            import traceback
            print(f"    상세 오류:\n{traceback.format_exc()}")
            return None

    except FileNotFoundError as e:
        print(f"❌ [오류] 파일을 찾을 수 없습니다: {e}")
        return None
    except PermissionError as e:
        print(f"❌ [오류] 파일 접근 권한이 없습니다: {e}")
        return None
    except Exception as e:
        print(f"❌ [오류] 예상치 못한 오류 발생: {e}")
        print(f"    오류 타입: {type(e).__name__}")
        import traceback
        print(f"    상세 오류:\n{traceback.format_exc()}")
        return None

