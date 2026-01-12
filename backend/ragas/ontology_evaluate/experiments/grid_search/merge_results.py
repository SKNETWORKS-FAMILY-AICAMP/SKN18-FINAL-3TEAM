"""
Grid Search 병렬 실행 결과 병합 스크립트

4개 배치로 나눠서 실행한 결과를 하나로 병합합니다.

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.grid_search.merge_results \
        --output-dir backend/ragas/ontology_evaluate/data/grid_search_optimized
"""

import argparse
import json
from pathlib import Path
from datetime import datetime


def merge_files_by_type(output_dir: Path, file_pattern: str, output_name: str) -> int:
    """
    특정 패턴의 파일들을 flat list로 병합

    Args:
        output_dir: 결과 파일이 있는 디렉토리
        file_pattern: 파일 패턴 (예: "batch_*_full.json")
        output_name: 출력 파일명 (예: "grid_results_merged_full.json")

    Returns:
        병합된 항목 수
    """
    batch_files = sorted(output_dir.glob(file_pattern))

    if not batch_files:
        print(f"⚠️  {file_pattern} 파일을 찾을 수 없습니다.")
        return 0

    print(f"\n📂 {file_pattern}: {len(batch_files)}개 파일 발견")
    for batch_file in batch_files:
        print(f"  - {batch_file.name}")

    # Flat list로 병합
    merged_list = []

    for batch_file in batch_files:
        print(f"📥 {batch_file.name} 로드 중...")

        with open(batch_file, 'r', encoding='utf-8') as f:
            batch_data = json.load(f)

        # Flat list 형태로 병합
        if isinstance(batch_data, list):
            merged_list.extend(batch_data)
        else:
            # 혹시 nested 형태면 results 추출
            batch_results = batch_data.get("results", [])
            merged_list.extend(batch_results)

        print(f"  → {len(batch_data) if isinstance(batch_data, list) else len(batch_results)}개 항목 추가")

    total_items = len(merged_list)
    print(f"✅ 총 {total_items}개 항목 병합 완료")

    # Flat list로 저장
    output_file = output_dir / output_name
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_list, f, indent=2, ensure_ascii=False)

    print(f"💾 병합 결과 저장: {output_file.name}")

    return total_items


def merge_batch_results(output_dir: Path):
    """
    배치 결과 파일들을 하나로 병합
    - batch_*.json → grid_results_merged.json (flat list)
    - batch_*_full.json → grid_results_merged_full.json (flat list)
    - batch_*_summary.json → grid_results_merged_summary.json (flat list)

    Args:
        output_dir: 결과 파일이 있는 디렉토리
    """
    print("\n" + "="*70)
    print("Grid Search 결과 병합")
    print("="*70)
    print()

    # 1. Base 파일 병합 (batch_*.json - 이름에 _가 포함되지 않은 것)
    print("🔹 Base 파일 병합 (batch_*.json)")
    # batch_N.json 패턴 찾기 (batch_1.json, batch_2.json 등)
    base_files = [f for f in sorted(output_dir.glob("batch_*.json"))
                  if "_full" not in f.name and "_summary" not in f.name and "_temp" not in f.name]

    if base_files:
        print(f"\n📂 batch_*.json: {len(base_files)}개 파일 발견")
        for batch_file in base_files:
            print(f"  - {batch_file.name}")

        merged_list = []
        for batch_file in base_files:
            print(f"📥 {batch_file.name} 로드 중...")
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)

            if isinstance(batch_data, list):
                merged_list.extend(batch_data)
                print(f"  → {len(batch_data)}개 항목 추가")
            else:
                batch_results = batch_data.get("results", [])
                merged_list.extend(batch_results)
                print(f"  → {len(batch_results)}개 항목 추가")

        total_base = len(merged_list)
        print(f"✅ 총 {total_base}개 항목 병합 완료")

        output_file = output_dir / "grid_results_merged.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_list, f, indent=2, ensure_ascii=False)
        print(f"💾 병합 결과 저장: {output_file.name}")
    else:
        print("⚠️  batch_*.json 파일을 찾을 수 없습니다.")
        total_base = 0

    # 2. Full 파일 병합
    print("\n🔹 Full 파일 병합 (batch_*_full.json)")
    total_full = merge_files_by_type(output_dir, "batch_*_full.json", "grid_results_merged_full.json")

    # 3. Summary 파일 병합
    print("\n🔹 Summary 파일 병합 (batch_*_summary.json)")
    total_summary = merge_files_by_type(output_dir, "batch_*_summary.json", "grid_results_merged_summary.json")

    # 통계 출력
    print("\n" + "="*70)
    print("📊 병합 요약")
    print("="*70)
    print(f"  Base 파일:    {total_base}개 항목")
    print(f"  Full 파일:    {total_full}개 항목")
    print(f"  Summary 파일: {total_summary}개 항목")
    print()

    # 설정별 통계 (Full 파일 기준)
    full_file = output_dir / "grid_results_merged_full.json"
    if full_file.exists():
        with open(full_file, 'r', encoding='utf-8') as f:
            full_data = json.load(f)

        config_counts = {}
        for result in full_data:
            config_name = result.get("experiment_name", "unknown")
            config_counts[config_name] = config_counts.get(config_name, 0) + 1

        print("📈 설정별 실험 수 (Full 기준):")
        for config_name, count in sorted(config_counts.items()):
            print(f"  - {config_name}: {count}개")
        print()

    print("="*70)
    print("✅ 모든 병합 완료!")
    print("="*70)
    print()


def main():
    parser = argparse.ArgumentParser(description="Grid Search 병렬 실행 결과 병합")
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="결과 파일이 있는 디렉토리 경로"
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    if not output_dir.exists():
        print(f"❌ 디렉토리가 존재하지 않습니다: {output_dir}")
        return

    merge_batch_results(output_dir)


if __name__ == "__main__":
    main()
