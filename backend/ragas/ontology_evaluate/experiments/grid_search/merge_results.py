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


def merge_batch_results(output_dir: Path):
    """
    배치 결과 파일들을 하나로 병합

    Args:
        output_dir: 결과 파일이 있는 디렉토리
    """
    print("\n" + "="*70)
    print("Grid Search 결과 병합")
    print("="*70)
    print()

    # 배치 결과 파일 찾기
    batch_files = sorted(output_dir.glob("batch_*_results.json"))

    if not batch_files:
        print("❌ 배치 결과 파일을 찾을 수 없습니다!")
        print(f"   경로: {output_dir}")
        return

    print(f"📂 발견된 배치 파일: {len(batch_files)}개")
    for batch_file in batch_files:
        print(f"  - {batch_file.name}")
    print()

    # 모든 결과 병합
    merged_results = {
        "metadata": {
            "experiment_name": "optimized_grid_search",
            "merged_at": datetime.now().isoformat(),
            "num_batches": len(batch_files),
            "batch_files": [f.name for f in batch_files]
        },
        "results": []
    }

    total_experiments = 0
    for batch_file in batch_files:
        print(f"📥 {batch_file.name} 로드 중...")

        with open(batch_file, 'r', encoding='utf-8') as f:
            batch_data = json.load(f)

        batch_results = batch_data.get("results", [])
        merged_results["results"].extend(batch_results)
        total_experiments += len(batch_results)

        print(f"  → {len(batch_results)}개 실험 추가")

    print()
    print(f"✅ 총 {total_experiments}개 실험 결과 병합 완료")
    print()

    # 통계 출력
    config_counts = {}
    for result in merged_results["results"]:
        config_name = result.get("config_name", "unknown")
        config_counts[config_name] = config_counts.get(config_name, 0) + 1

    print("📊 설정별 실험 수:")
    for config_name, count in sorted(config_counts.items()):
        print(f"  - {config_name}: {count}개")
    print()

    # 병합 결과 저장
    output_file = output_dir / "grid_results_merged.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_results, f, indent=2, ensure_ascii=False)

    print(f"💾 병합 결과 저장: {output_file}")
    print()

    # 요약 통계 저장
    summary = {
        "merged_at": datetime.now().isoformat(),
        "total_experiments": total_experiments,
        "num_configs": len(config_counts),
        "config_distribution": config_counts
    }

    summary_file = output_dir / "merge_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"📝 요약 정보 저장: {summary_file}")
    print()

    print("="*70)
    print("✅ 병합 완료!")
    print("="*70)
    print()
    print("다음 단계: 결과 분석")
    print("  python -m backend.ragas.ontology_evaluate.experiments.grid_search.analyze_grid_results \\")
    print(f"      --results {output_file}")
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
