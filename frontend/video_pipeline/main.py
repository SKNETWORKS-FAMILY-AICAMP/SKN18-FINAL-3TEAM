#!/usr/bin/env python3
"""
배경 이미지 영상 생성 메인 실행 파일
프롬프트 입력으로 배경 이미지 생성 후 영상 만들기
"""

from pathlib import Path
from services import (
    parse_scenes,
    separate_scene_and_camera,
    enhance_scene_with_era_details,
    generate_image_with_gemini,
    create_video_from_image_fal
)

# Directory setup
OUTPUT_DIR = Path("output")
VIDEO_DIR = OUTPUT_DIR / "videos"
IMAGES_DIR = OUTPUT_DIR / "images"

# Create directories
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def main():
    """Main execution function - 프롬프트 입력으로 자동 처리"""
    print("="*60)
    print("🎬 배경 이미지 생성 → 영상 생성 (자동 처리)")
    print("="*60)
    
    print("\n✨ 기능:")
    print("  ✅ sin1:, sin2: 형식 프롬프트 자동 파싱")
    print("  ✅ 장면 설명과 카메라 움직임 자동 구분")
    print("  ✅ 배경 이미지 자동 생성")
    print("  ✅ 각 배경 이미지로 영상 자동 생성")
    print("  ✅ 캐릭터 제약 없음 - 배경 이미지에 최적화된 설정")
    
    print("\n📌 프롬프트 입력 형식:")
    print("  sin1: 임진왜란 발발. 도요토미 히데요시가 조선 침략을 명령하고 일본군이 출정하는 장면. 대규모 병력을 보여주는 Wide shot.")
    print("  sin2: 부산진 함락. 일본군의 거센 공격과 조선군의 방어가 충돌하는 순간. 조선 수군과 일본군이 격렬하게 맞붙는 Dynamic action shot.")
    print("  sin3: 옥포 해전 승리. 이순신 장군이 지휘하는 거북선과 조선 수군이 바다 위에서 일본 함대를 격파하는 Wide shot.")
    print("  sin4: 행주대첩. 권율 장군이 조선군과 함께 산성을 지키며 반격하는 장면. 병사들의 결의와 긴장감을 강조한 Close-up mix.")
    print("\n💡 각 씬에서 장면 설명과 카메라 움직임을 자동으로 구분합니다!")
    print("-"*60)
    
    # 프롬프트 입력
    all_lines = []
    print("\n프롬프트 입력 (빈 줄 입력 시 종료):")
    while True:
        line = input()
        if line.strip() == "":
            break
        all_lines.append(line)
    
    user_input = "\n".join(all_lines)
    
    if not user_input.strip():
        print("\n⚠️  프롬프트가 비어있습니다. 종료합니다.")
        return
    
    # sin1:, sin2: 형식으로 장면 파싱
    parsed_scenes = parse_scenes(user_input)
    
    if not parsed_scenes:
        print("\n❌ sin1:, sin2: 형식의 프롬프트를 찾을 수 없습니다.")
        print("예시:")
        print("  sin1: 장면 설명. 카메라 움직임.")
        print("  sin2: 장면 설명. 카메라 움직임.")
        return
    
    print(f"\n✅ {len(parsed_scenes)}개의 장면 감지됨!")
    
    # 각 장면에서 장면 설명과 카메라 움직임 자동 구분
    print(f"\n{'='*60}")
    print("🔍 장면 분석 중...")
    print("="*60)
    
    scenes = []
    for scene_info in parsed_scenes:
        scene_text = scene_info['text']
        scene_description, camera_movement = separate_scene_and_camera(scene_text)
        
        print(f"\n[sin{scene_info['number']}]")
        print(f"  📝 장면 설명: {scene_description[:80]}...")
        print(f"  🎥 카메라 움직임: {camera_movement[:80]}...")
        
        # 배경 이미지 생성용 프롬프트 (캐릭터 없음)
        image_prompt = scene_description
        if "no characters" not in image_prompt.lower():
            image_prompt += ", historical background scene, no main characters in foreground"
        
        scenes.append({
            "number": scene_info['number'],
            "image_prompt": image_prompt,
            "video_prompt": f"{scene_description}, {camera_movement}" if scene_description else camera_movement
        })
    
    print(f"\n✅ 총 {len(scenes)}개 장면 분석 완료!")
    
    # 1단계: 배경 이미지 생성
    print(f"\n{'='*60}")
    print("🖼️ 배경 이미지 생성 중...")
    print("="*60)
    
    generated_images = []
    failed_scenes = []
    
    for i, scene in enumerate(scenes):
        print(f"\n{'='*60}")
        print(f"🎨 Scene {i+1}/{len(scenes)} - 배경 이미지 생성")
        print(f"{'='*60}")
        
        try:
            # 1. 장면 강화
            enhanced_prompt = enhance_scene_with_era_details(scene["image_prompt"], use_gemini_analysis=False)
            
            # 3. 배경 이미지 생성
            bg_path = IMAGES_DIR / f"background_{scene['number']}.png"
            generate_image_with_gemini(enhanced_prompt, str(bg_path))
            
            if Path(bg_path).exists():
                generated_images.append((scene['number'], str(bg_path), scene['video_prompt']))
                print(f"✅ Scene {i+1} 배경 이미지 생성 완료!")
            else:
                failed_scenes.append((scene['number'], "이미지 생성 실패"))
                print(f"❌ Scene {i+1} 배경 이미지 생성 실패")
                
        except Exception as e:
            failed_scenes.append((scene['number'], str(e)))
            print(f"❌ Scene {i+1} 처리 중 오류: {e}")
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
    
    for scene_num, img_path, video_prompt in generated_images:
        print(f"\n{'='*60}")
        print(f"🎥 Scene {scene_num} - 영상 생성")
        print(f"{'='*60}")
        
        if not Path(img_path).exists():
            print(f"❌ [오류] 이미지 파일이 없습니다: {img_path}")
            failed_videos.append((scene_num, img_path))
            continue
        
        print(f"[*] 배경 이미지: {Path(img_path).name}")
        print(f"[*] 영상 프롬프트: {video_prompt[:80]}...")
        
        video_path = VIDEO_DIR / f"background_scene_{scene_num}_video.mp4"
        
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
                individual_videos.append(result)
                print(f"✅ Scene {scene_num} 영상 생성 성공!")
            else:
                failed_videos.append((scene_num, img_path))
                print(f"❌ Scene {scene_num} 영상 생성 실패")
                
        except Exception as e:
            failed_videos.append((scene_num, img_path))
            print(f"❌ Scene {scene_num} 처리 중 오류: {e}")
            import traceback
            print(f"    상세 오류:\n{traceback.format_exc()}")
    
    # 결과 요약
    print(f"\n{'='*60}")
    print(f"📊 최종 결과 요약")
    print(f"{'='*60}")
    print(f"✅ 배경 이미지: {len(generated_images)}개")
    print(f"✅ 영상: {len(individual_videos)}개")
    if failed_scenes:
        print(f"❌ 실패한 장면: {len(failed_scenes)}개")
        for num, reason in failed_scenes:
            print(f"   - sin{num}: {reason}")
    if failed_videos:
        print(f"❌ 실패한 영상: {len(failed_videos)}개")
        for num, path in failed_videos:
            print(f"   - sin{num}: {Path(path).name}")
    print(f"{'='*60}")
    
    if not individual_videos:
        print("\n❌ 생성된 영상이 없습니다.")
        return
    
    # 생성된 개별 영상 출력
    print(f"\n🎉 완료! 생성된 영상들:")
    print(f"   저장 위치: {VIDEO_DIR}")
    for video in individual_videos:
        if Path(video).exists():
            size = Path(video).stat().st_size / (1024 * 1024)
            print(f"   ✅ {Path(video).name} ({size:.2f} MB)")
        else:
            print(f"   ⚠️  {Path(video).name} (파일 없음)")
    
    print("="*60)


if __name__ == "__main__":
    main()

