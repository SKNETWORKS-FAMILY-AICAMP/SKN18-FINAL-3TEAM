import os
import json
from datetime import datetime
from django.conf import settings
from backend.langgraph_structure1.state import GraphState
from frontend.video_pipeline.services import (
    process_scene_prompt,
    generate_image_with_gemini,
    create_video_from_image_fal 
)

# 영상 생성 시 대본 전체를 주면 사람이 배경에 튀어 나오므로 대본이 아니라 분위기만 주기 위한 다중 if문 함수
def get_video_style_prompt(scene_text: str) -> str:
    """
    대본 텍스트를 분석하여 4가지 분위기 중 하나에 맞는 '영상 전용 프롬프트'를 반환
    * 핵심 전략: 인물 묘사를 싹 빼고, '배경의 움직임(Motion)'만 지시함.
    """
    text = scene_text.lower()
    
    # 1. 🔥 WAR (전쟁/전투) - 확실한 전투 키워드가 있을 때만
    war_keywords = [
        'battlefield', 'fighting', 'war zone', 'combat', 
        'soldiers charging', 'invasion', 'killing', 'bloody', 
        'army clash', '전쟁', '전투', '침략'
    ]
    if any(k in text for k in war_keywords):
        print("      👉 분위기 감지: [WAR/BATTLE]")
        return (
            "historical battlefield, chaotic atmosphere, thick smoke rising, "
            "fire sparks flying in the air, embers, debris, fast moving smoke, "
            "dramatic lighting, cinematic, NO HUMANS"
        )

    # 2. 😨 TENSION (긴장/위기/밤/잠입) - 전투는 아니지만 분위기가 무거울 때
    tension_keywords = ['crisis', 'spy', 'secret', 'night', 'dark', 'fear', 'danger', 'storm', 'rain', 'thunder', 'fog', 'mist', 'urgency', '위기', '밀정', '암살', '밤']
    if any(k in text for k in tension_keywords):
        print("      👉 분위기 감지: [TENSION/DARK]")
        return (
            "dark and tense atmosphere, heavy fog flowing, fast moving dark clouds, "
            "gloomy lighting, cinematic wind, mysterious, "
            "ominous mood, storm approaching, NO HUMANS"
        )

    # 3. 👑 ROYAL (궁궐/엄숙/회의/세종대왕) - 웅장하고 정적인 상황
    royal_keywords = ['king', 'queen', 'palace', 'throne', 'decree', 'meeting', 'discussion', 'scholar', 'study', 'book', 'science', 'royal', '왕', '세종', '궁궐', '회의']
    if any(k in text for k in royal_keywords):
        print("      👉 분위기 감지: [ROYAL/SOLEMN]")
        return (
            "majestic historical palace atmosphere, golden light rays (god rays) shining through, "
            "floating dust particles, very slow cinematic camera movement, "
            "peaceful but grand, holy atmosphere, static composition, NO HUMANS"
        )

    # 4. 🍃 NATURE (평화/기본) - 위 3가지가 아니면 기본 자연 풍경
    print("      👉 분위기 감지: [PEACE/NATURE]")
    return (
        "peaceful historical scenery, gentle wind blowing, "
        "leaves shaking softly, slow moving white clouds, "
        "bright and airy atmosphere, serenity, warm sunlight, "
        "static background, NO HUMANS"
    )

def background_gen_node(state: GraphState) -> GraphState:
    """
    배경 이미지 및 영상 생성 노드
    """
    print("🎨 [Background Node] 배경 이미지 및 영상 생성 시작...")
    
    script_json = state.get("scene_script", {})
    scenes = script_json.get("scenes", [])
    
    # 타임스탬프 (배경 파일 이름용)
    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 저장할 기본 경로 (Django media/backgrounds)
    save_dir = os.path.join(settings.MEDIA_ROOT, "backgrounds")
    os.makedirs(save_dir, exist_ok=True)
    
    for i, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", i)
        image_prompt = scene.get("image_prompt", "")
        
        if not image_prompt:
            print(f"⚠️ Scene {scene_id}: image_prompt 없음. 스킵.")
            continue
            
        # 파일 이름 생성 (중복 방지)
        query_type = state.get('query_type', 'gen')
        
        image_file_name = f"bg_{query_type}_{scene_id}_{current_time_str}.png"
        image_full_path = os.path.join(save_dir, image_file_name)
        
        video_file_name = f"bg_{query_type}_{scene_id}_{current_time_str}.mp4"
        video_full_path = os.path.join(save_dir, video_file_name)
        
        # 3. 프롬프트 강화
        enhanced_prompt, _ = process_scene_prompt(image_prompt, is_image=True)
        
        print(f"   🎬 Processing Scene {scene_id}...")
        
        try:
            # ---------------------------------------------------------
            # [단계 1] 이미지 생성
            # ---------------------------------------------------------
            generate_image_with_gemini(enhanced_prompt, image_full_path)
            print(f"      👉 이미지 생성 완료: {image_file_name}")
            
            # ---------------------------------------------------------
            # [단계 2] 영상 생성 (이미지 -> 영상)
            # ---------------------------------------------------------
            video_style_prompt = get_video_style_prompt(enhanced_prompt)
            
            print(f"      👉 영상 변환 시작 (Fal.ai)...")
            result_video = create_video_from_image_fal(
                image_path=image_full_path,
                output_path=video_full_path,
                prompt=video_style_prompt,
                resolution="1080p", 
                duration=5
            )

            # ---------------------------------------------------------
            # [단계 3] URL 등록
            # ---------------------------------------------------------
            base_url = settings.MY_SERVER_URL.rstrip('/')
            media_url = settings.MEDIA_URL.strip('/')
            
            if result_video and os.path.exists(result_video):
                # 영상 성공 시
                final_url = f"{base_url}/{media_url}/backgrounds/{video_file_name}"
                print(f"      ✅ 영상 URL 적용: {final_url}")
            else:
                # 영상 실패 시
                final_url = f"{base_url}/{media_url}/backgrounds/{image_file_name}"
                print(f"      ⚠️ 영상 실패, 이미지 URL 적용: {final_url}")

            # JSON 업데이트
            scene["location"] = final_url
            
        except Exception as e:
            print(f"   ❌ Scene {scene_id} 생성 실패: {e}")
            import traceback
            print(traceback.format_exc())
    
    # [삭제됨] 로컬에 대본 저장하는 코드는 제거했습니다. (views.py가 담당)

    # 병렬 실행 시 LangGraph 오류 방지: 업데이트하는 키만 반환
    return {
        "scene_script": script_json,
    }