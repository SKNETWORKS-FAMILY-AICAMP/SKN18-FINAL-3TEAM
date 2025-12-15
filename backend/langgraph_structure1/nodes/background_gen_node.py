import os
import json
from datetime import datetime
from django.conf import settings
from backend.langgraph_structure1.state import GraphState
from frontend.video_pipeline.services import (
    process_scene_prompt,
    generate_image_with_gemini 
)
# 동영상 생성도 필요하면 import create_video_from_image_fal 추가

def background_gen_node(state: GraphState) -> GraphState:
    """
    배경 이미지 생성 노드
    1. scene_script의 image_prompt를 읽음
    2. services 모듈로 이미지 생성 및 media 폴더에 저장
    3. 로컬 파일 경로를 HTTP URL로 변환하여 location 필드에 입력
    """
    print("🎨 [Background Node] 배경 이미지 생성 시작...")
    
    script_json = state.get("scene_script", {})
    scenes = script_json.get("scenes", [])
    
    # 저장할 기본 경로 (Django media/backgrounds)
    save_dir = os.path.join(settings.MEDIA_ROOT, "backgrounds")
    os.makedirs(save_dir, exist_ok=True)
    
    for i, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", i)
        image_prompt = scene.get("image_prompt", "")
        
        if not image_prompt:
            print(f"⚠️ Scene {scene_id}: image_prompt 없음. 스킵.")
            continue
            
        # 1. 파일명 및 경로 설정
        # 겹치지 않게 유니크한 이름 추천 (여기선 간단히 scene_id 사용)
        file_name = f"bg_{state.get('query_type', 'gen')}_{scene_id}.png"
        full_path = os.path.join(save_dir, file_name)
        
        # 2. 프롬프트 강화 (팀원 코드 활용)
        # (True는 이미지용이라는 뜻)
        enhanced_prompt, _ = process_scene_prompt(image_prompt, is_image=True)
        
        print(f"   Generating Scene {scene_id}...")
        
        try:
            # 3. 이미지 생성 (팀원 코드 활용)
            # 파일이 이미 있으면 덮어쓸지 로직 추가 가능
            generate_image_with_gemini(enhanced_prompt, full_path)
            
            # 4. URL 변환 (http://127.0.0.1:8000/media/backgrounds/파일명)
            # settings.MY_SERVER_URL + settings.MEDIA_URL + 'backgrounds/' + file_name
            # URL 조합 시 슬래시(/) 처리에 주의
            
            base_url = settings.MY_SERVER_URL.rstrip('/')
            media_url = settings.MEDIA_URL.strip('/')
            
            final_url = f"{base_url}/{media_url}/backgrounds/{file_name}"
            
            # 5. JSON 업데이트 (location 필드에 URL 넣기)
            scene["location"] = final_url
            print(f"   ✅ URL 적용 완료: {final_url}")
            
        except Exception as e:
            print(f"   ❌ Scene {scene_id} 생성 실패: {e}")
            # 실패 시 기본값이라도 넣어주기 (선택사항)
            # scene["location"] = "Point_Center" 
    
    #대본 저장 로직.
    #
    try:
        # 1. 저장할 폴더 만들기 (프로젝트 루트/debug_scripts)
        # settings.BASE_DIR이 없으면 현재 폴더 기준으로 생성
        base_dir = getattr(settings, 'BASE_DIR', os.getcwd())
        log_dir = os.path.join(base_dir, "Created_Acts")
        os.makedirs(log_dir, exist_ok=True)

        # 2. 파일명 생성 (날짜_시간_질문타입.json)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        q_type = state.get("query_type", "unknown")
        filename = f"script_{timestamp}_{q_type}.json"
        filepath = os.path.join(log_dir, filename)

        # 3. 예쁘게 저장 (한글 깨짐 방지: ensure_ascii=False)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(script_json, f, indent=4, ensure_ascii=False)
            
        print(f"📂 [DEBUG] 대본 파일 저장됨: {filepath}")
        
    except Exception as e:
        print(f"⚠️ 대본 저장 중 에러 발생: {e}")

    return {
        **state,
        "scene_script": script_json, # 업데이트된 JSON 반환
    }

