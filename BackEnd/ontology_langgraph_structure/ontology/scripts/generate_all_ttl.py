"""
전체 CSV 데이터를 TTL로 변환 (limit 없이 전체 처리)
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from llm_ttl_generator import LLMTTLGenerator

# .env 파일 로드
load_dotenv()


def main():
    """전체 데이터 TTL 생성"""

    # 경로 설정
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent.parent
    csv_path = project_root / "backend/db_pipeline/data/encykorea_cleaned6.csv"
    output_dir = script_dir.parent / "instances"

    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)

    # 생성기 초기화
    generator = LLMTTLGenerator(str(csv_path), str(output_dir))

    print("=" * 60)
    print("🚀 전체 CSV 데이터 → TTL 변환 시작")
    print("=" * 60)
    print(f"📂 입력: {csv_path}")
    print(f"📂 출력: {output_dir}/korean_history_instances.ttl")
    print("")
    print("⚠️  주의: 전체 데이터 처리는 시간이 오래 걸릴 수 있습니다")
    print("   (예상 시간: CSV 행 수 × 2~3초)")
    print("   (예상 비용: 약 $3-4) ← 프롬프트 최적화로 절감")
    print("")

    # TTL 생성 (limit=None → 전체)
    generator.generate_ttl_file(limit=None)

    print("")
    print("=" * 60)
    print("✅ 전체 TTL 변환 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
