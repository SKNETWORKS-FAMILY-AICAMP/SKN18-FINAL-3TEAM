#!/usr/bin/env python3
"""
배경 이미지 영상 생성 메인 실행 파일 (JSON 형식)
JSON 프롬프트 입력으로 배경 이미지 생성 후 영상 만들기
"""

import json
from pathlib import Path
from services import (
    enhance_scene_with_era_details,
    generate_image_with_gemini,
    create_video_from_image_fal
)

# Directory setup
OUTPUT_DIR = Path(__file__).parent / "output"
VIDEO_DIR = OUTPUT_DIR / "videos"
IMAGES_DIR = OUTPUT_DIR / "images"

# Create directories
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def parse_json_prompt(json_data: dict) -> list:
    """
    JSON 형식의 프롬프트를 파싱하여 장면 목록 반환
    image_prompt와 camera_prompt를 직접 사용
    
    Args:
        json_data: JSON 딕셔너리
        
    Returns:
        장면 정보 리스트
    """
    scenes = []
    
    if "scenes" not in json_data:
        return scenes
    
    for scene in json_data["scenes"]:
        scene_id = scene.get("scene_id", 0)
        image_prompt = scene.get("image_prompt", "")
        camera_prompt = scene.get("camera_prompt", "")
        
        # 디버깅: 장면 정보 출력
        print(f"[DEBUG] Scene {scene_id} 파싱 중...")
        print(f"  - image_prompt 존재: {bool(image_prompt)}")
        print(f"  - camera_prompt 존재: {bool(camera_prompt)}")
        if image_prompt:
            print(f"  - image_prompt 길이: {len(image_prompt)}")
        if camera_prompt:
            print(f"  - camera_prompt 길이: {len(camera_prompt)}")
        
        # image_prompt와 camera_prompt가 필수
        if not image_prompt:
            print(f"⚠️  Scene {scene_id}: image_prompt가 없습니다. 건너뜁니다.")
            print(f"    사용 가능한 키: {list(scene.keys())}")
            continue
        
        if not camera_prompt:
            # camera_prompt가 없으면 기본값 사용
            camera_prompt = "smooth camera movement, cinematic, gentle motion"
            print(f"⚠️  Scene {scene_id}: camera_prompt가 없습니다. 기본값 사용.")
        
        scenes.append({
            "scene_id": scene_id,
            "image_prompt": image_prompt,
            "video_prompt": camera_prompt
        })
        print(f"✅ Scene {scene_id} 파싱 완료")
    
    return scenes


def main():
    """Main execution function - JSON 프롬프트 입력으로 자동 처리"""
    print("="*60)
    print("🎬 배경 이미지 생성 → 영상 생성 (JSON 형식)")
    print("="*60)
    
    print("\n✨ 기능:")
    print("  ✅ JSON 형식 프롬프트 자동 파싱")
    print("  ✅ image_prompt와 camera_prompt 직접 사용")
    print("  ✅ 각 배경 이미지로 영상 자동 생성")
    print("  ✅ 캐릭터 제약 없음 - 배경 이미지에 최적화된 설정")
    
    print("\n📌 JSON 프롬프트 입력 형식:")
    print("  {")
    print('    "title": "타이틀"')
    print('    "scenes": [')
    print('      {')
    print('        "scene_id": 1,')
    print('        "image_prompt": "장면 설명...",')
    print('        "camera_prompt": "카메라 움직임..."')
    print('      }')
    print('    ]')
    print("  }")
    print("-"*60)
    
    # JSON 프롬프트 입력
    import sys
    json_input = ""
    
    # 명령줄 인자로 파일 경로가 제공되면 파일에서 읽기
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_input = f.read()
            print(f"\n📄 파일에서 JSON 읽기: {file_path}")
        except FileNotFoundError:
            print(f"\n❌ 파일을 찾을 수 없습니다: {file_path}")
            return
        except Exception as e:
            print(f"\n❌ 파일 읽기 오류: {e}")
            return
    else:
        # 직접 입력 - JSON 파싱이 성공할 때까지 입력받기
        all_lines = []
        print("\nJSON 프롬프트 입력:")
        print("  (여러 줄 입력 가능, 빈 줄은 무시됩니다)")
        print("  (입력 완료 후 Ctrl+Z (Windows) 또는 Ctrl+D (Linux/Mac)로 종료)")
        print("  또는 JSON 입력이 완료되면 빈 줄 두 번 입력")
        print("-" * 60)
        
        while True:
            try:
                line = input()
                all_lines.append(line)
                
                # 현재까지 입력된 내용으로 JSON 파싱 시도
                current_input = "\n".join(all_lines)
                try:
                    test_data = json.loads(current_input)
                    # 파싱 성공하면 입력 완료
                    print("\n✅ JSON 입력 완료!")
                    break
                except json.JSONDecodeError:
                    # 아직 완성되지 않았으면 계속 입력
                    pass
            except EOFError:
                # Ctrl+Z 또는 Ctrl+D 입력
                break
        
        json_input = "\n".join(all_lines)
    
    if not json_input.strip():
        print("\n⚠️  프롬프트가 비어있습니다. 종료합니다.")
        return
    
    # JSON 파싱
    try:
        json_data = json.loads(json_input)
        print(f"[DEBUG] JSON 파싱 성공")
        print(f"[DEBUG] JSON 키: {list(json_data.keys())}")
        if "scenes" in json_data:
            print(f"[DEBUG] scenes 개수: {len(json_data['scenes'])}")
            if json_data["scenes"]:
                print(f"[DEBUG] 첫 번째 scene 키: {list(json_data['scenes'][0].keys())}")
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 파싱 오류: {e}")
        print(f"오류 위치: 라인 {e.lineno}, 컬럼 {e.colno}")
        print("\n입력된 JSON (처음 500자):")
        print(json_input[:500])
        print("\n💡 팁: JSON 파일로 저장 후 다음 명령으로 실행하세요:")
        print("   python main2.py your_file.json")
        print("올바른 JSON 형식으로 입력해주세요.")
        return
    
    # JSON에서 장면 파싱
    scenes = parse_json_prompt(json_data)
    
    if not scenes:
        print("\n❌ 장면 정보를 찾을 수 없습니다.")
        print("JSON에 'scenes' 배열이 포함되어 있는지 확인해주세요.")
        return
    
    title = json_data.get("title", "Untitled")
    print(f"\n📽️  제목: {title}")
    print(f"✅ {len(scenes)}개의 장면 감지됨!")
    
    # 장면 정보 출력
    print(f"\n{'='*60}")
    print("🔍 장면 분석 중...")
    print("="*60)
    
    for scene in scenes:
        print(f"\n[Scene {scene['scene_id']}]")
        print(f"  📝 이미지 프롬프트: {scene['image_prompt'][:80]}...")
        print(f"  🎬 카메라 프롬프트: {scene['video_prompt'][:80]}...")
    
    print(f"\n✅ 총 {len(scenes)}개 장면 분석 완료!")
    
    # 1단계: 배경 이미지 생성
    print(f"\n{'='*60}")
    print("🖼️ 배경 이미지 생성 중...")
    print("="*60)
    
    generated_images = []
    failed_scenes = []
    
    for i, scene in enumerate(scenes):
        print(f"\n{'='*60}")
        print(f"🎨 Scene {i+1}/{len(scenes)} (ID: {scene['scene_id']}) - 배경 이미지 생성")
        print(f"{'='*60}")
        
        try:
            # 1. 장면 강화
            enhanced_prompt = enhance_scene_with_era_details(scene["image_prompt"], use_gemini_analysis=False)
            
            # 3. 배경 이미지 생성
            bg_path = IMAGES_DIR / f"background_scene_{scene['scene_id']}.png"
            generate_image_with_gemini(enhanced_prompt, str(bg_path))
            
            if Path(bg_path).exists():
                generated_images.append((
                    scene['scene_id'],
                    str(bg_path),
                    scene['video_prompt']
                ))
                print(f"✅ Scene {i+1} (ID: {scene['scene_id']}) 배경 이미지 생성 완료!")
            else:
                failed_scenes.append((scene['scene_id'], "이미지 생성 실패"))
                print(f"❌ Scene {i+1} (ID: {scene['scene_id']}) 배경 이미지 생성 실패")
                
        except Exception as e:
            failed_scenes.append((scene['scene_id'], str(e)))
            print(f"❌ Scene {i+1} (ID: {scene['scene_id']}) 처리 중 오류: {e}")
            import traceback
            print(f"    상세 오류:\n{traceback.format_exc()}")
    
    if not generated_images:
        print("\n❌ 생성된 배경 이미지가 없습니다.")
        return
    
    # 2단계: 각 배경 이미지로 영상 생성
    print(f"\n{'='*60}")
    print("🎥 영상 생성 중...")
    print("="*60)
    
    individual_videos = []
    failed_videos = []
    
    for scene_id, img_path, video_prompt in generated_images:
        print(f"\n{'='*60}")
        print(f"🎥 Scene {scene_id} - 영상 생성")
        print(f"{'='*60}")
        
        if not Path(img_path).exists():
            print(f"❌ [오류] 이미지 파일이 없습니다: {img_path}")
            failed_videos.append((scene_id, img_path))
            continue
        
        print(f"[*] 배경 이미지: {Path(img_path).name}")
        print(f"[*] 영상 프롬프트: {video_prompt[:80]}...")
        
        video_path = VIDEO_DIR / f"background_scene_{scene_id}_video.mp4"
        
        try:
            # 영상 생성
            result = create_video_from_image_fal(
                img_path,
                str(video_path),
                video_prompt,
                resolution="1080p",
                duration=5
            )
            
            if result:
                individual_videos.append((scene_id, result))
                print(f"✅ Scene {scene_id} 영상 생성 성공!")
            else:
                failed_videos.append((scene_id, img_path))
                print(f"❌ Scene {scene_id} 영상 생성 실패")
                
        except Exception as e:
            failed_videos.append((scene_id, img_path))
            print(f"❌ Scene {scene_id} 처리 중 오류: {e}")
            import traceback
            print(f"    상세 오류:\n{traceback.format_exc()}")
    
    # 결과 요약
    print(f"\n{'='*60}")
    print(f"📊 최종 결과 요약")
    print(f"{'='*60}")
    print(f"📽️  제목: {title}")
    print(f"✅ 배경 이미지: {len(generated_images)}개")
    print(f"✅ 영상: {len(individual_videos)}개")
    if failed_scenes:
        print(f"❌ 실패한 장면: {len(failed_scenes)}개")
        for scene_id, reason in failed_scenes:
            print(f"   - Scene {scene_id}: {reason}")
    if failed_videos:
        print(f"❌ 실패한 영상: {len(failed_videos)}개")
        for scene_id, path in failed_videos:
            print(f"   - Scene {scene_id}: {Path(path).name}")
    print(f"{'='*60}")
    
    if not individual_videos:
        print("\n❌ 생성된 영상이 없습니다.")
        return
    
    # 생성된 개별 영상 출력
    print(f"\n🎉 완료! 생성된 영상들:")
    print(f"   저장 위치: {VIDEO_DIR}")
    for scene_id, video in individual_videos:
        if Path(video).exists():
            size = Path(video).stat().st_size / (1024 * 1024)
            print(f"   ✅ Scene {scene_id}: {Path(video).name} ({size:.2f} MB)")
        else:
            print(f"   ⚠️  Scene {scene_id}: {Path(video).name} (파일 없음)")
    
    print("="*60)


if __name__ == "__main__":
    main()

