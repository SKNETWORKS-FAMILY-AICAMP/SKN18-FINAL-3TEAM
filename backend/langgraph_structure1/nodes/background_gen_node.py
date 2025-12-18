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

def background_gen_node(state: GraphState) -> GraphState:
    """
    배경 이미지 및 영상 생성 노드
    """
    print("🎨 [Background Node] 배경 이미지 및 영상 생성 시작...")
    
    script_json = state.get("scene_script", {})
    scenes = script_json.get("scenes", [])
    
    # [수정 1] 타임스탬프를 루프 돌기 '전'에 미리 만들어둡니다. (파일 이름에 붙이기 위해)
    # 예: 20251218_103055
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
            
        # [수정 2] 파일 이름에 시간(current_time_str)을 추가해서 절대 안 겹치게 만듦!
        # 결과 예: bg_gen_0_20251218_103055.png
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
            video_prompt = enhanced_prompt + ", slow camera movement, cinematic atmosphere"
            
            print(f"      👉 영상 변환 시작 (Fal.ai)...")
            result_video = create_video_from_image_fal(
                image_path=image_full_path,
                output_path=video_full_path,
                prompt=video_prompt,
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
    
    # 대본 저장 로직 (이미 위에서 타임스탬프를 만들었으니 재활용)
    try:
        base_dir = getattr(settings, 'BASE_DIR', os.getcwd())
        log_dir = os.path.join(base_dir, "Created_Acts")
        os.makedirs(log_dir, exist_ok=True)

        # 위에서 만든 시간 값 사용
        q_type = state.get("query_type", "unknown")
        filename = f"script_{current_time_str}_{q_type}.json"
        filepath = os.path.join(log_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(script_json, f, indent=4, ensure_ascii=False)
            
        print(f"📂 [DEBUG] 대본 파일 저장됨: {filepath}")
        
    except Exception as e:
        print(f"⚠️ 대본 저장 중 에러 발생: {e}")

    return {
        **state,
        "scene_script": script_json, 
    }