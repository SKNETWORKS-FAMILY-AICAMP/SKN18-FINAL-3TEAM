"""
썸네일 생성 테스트 스크립트
제목만 전달하여 썸네일 이미지가 잘 생성되는지 테스트합니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Django 설정을 모킹하여 설정 없이 실행 가능하도록
class MockSettings:
    BASE_DIR = project_root / "backend" / "django"
    MEDIA_ROOT = project_root / "backend" / "django" / "media"
    MY_SERVER_URL = "http://127.0.0.1:8000"
    MEDIA_URL = "/media/"

# django.conf.settings를 모킹 (import 전에 모킹해야 함)
import sys
from unittest.mock import MagicMock

# django 모듈들을 모킹
mock_django = MagicMock()
mock_django_conf = MagicMock()
mock_django_conf.settings = MockSettings()
mock_django.conf = mock_django_conf

sys.modules['django'] = mock_django
sys.modules['django.conf'] = mock_django_conf
sys.modules['django.conf.settings'] = MockSettings()

from backend.langgraph_structure1.nodes.thumbnail_gen_node import (
    generate_thumbnail_prompt,
    generate_thumbnail_with_nanobanana
)


def test_thumbnail_generation(title: str = "The Magic of Hangeul"):
    """
    썸네일 생성 테스트
    
    Args:
        title: 테스트할 영상 제목
    """
    print("=" * 70)
    print(f"🧪 썸네일 생성 테스트 시작")
    print("=" * 70)
    print(f"📝 제목: {title}")
    print()
    
    # 1. 프롬프트 생성
    print("1️⃣ 프롬프트 생성 중...")
    prompt = generate_thumbnail_prompt(title)
    print(f"   ✅ 프롬프트 생성 완료")
    print(f"   📄 프롬프트 (처음 200자):\n   {prompt[:200]}...")
    print()
    
    # 2. 출력 경로 설정
    output_dir = project_root / "backend" / "django" / "media" / "thumbnails"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"test_thumbnail_{title.replace(' ', '_')[:30]}.png"
    
    print("2️⃣ 썸네일 이미지 생성 중...")
    print(f"   📂 출력 경로: {output_path}")
    print()
    
    # 3. 썸네일 생성
    try:
        result_path = generate_thumbnail_with_nanobanana(prompt, str(output_path))
        
        if result_path and Path(result_path).exists():
            print()
            print("=" * 70)
            print("✅ 테스트 성공!")
            print("=" * 70)
            print(f"📁 생성된 이미지: {result_path}")
            print(f"📏 파일 크기: {Path(result_path).stat().st_size / 1024:.2f} KB")
            print()
            print("💡 이미지를 확인하려면:")
            print(f"   open {result_path}")
        else:
            print()
            print("=" * 70)
            print("❌ 테스트 실패: 이미지가 생성되지 않았습니다")
            print("=" * 70)
            
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ 테스트 실패: 오류 발생")
        print("=" * 70)
        print(f"오류 내용: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 명령줄 인자로 제목 전달 가능
    if len(sys.argv) > 1:
        title = " ".join(sys.argv[1:])
    else:
        # 기본 제목 사용
        title = "The Magic of Hangeul"
    
    test_thumbnail_generation(title)

