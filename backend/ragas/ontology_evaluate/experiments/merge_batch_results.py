"""
배치 결과 병합 스크립트

여러 배치로 나눠서 처리한 결과를 하나로 병합하고 Full + Summary 파일 생성

사용법:
    python -m backend.ragas.ontology_evaluate.experiments.merge_batch_results \
        --group semantic_expander
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

from backend.ragas.ontology_evaluate.utils.experiment_utils import save_experiment_results


def merge_and_save_results(
    batch_dir: Path,
    output_dir: Path,
    group_name: str
):
    """배치 결과를 병합하고 Full + Summary 파일 생성"""

    print(f"\n{'='*70}")
    print(f"배치 결과 병합: {group_name}")
    print(f"{'='*70}")

    # 1. 모든 배치 파일 찾기
    batch_files = sorted(batch_dir.glob("batch_*.json"))

    if not batch_files:
        print(f"❌ 오류: {batch_dir}에 배치 파일이 없습니다.")
        return

    print(f"\n📂 배치 파일: {len(batch_files)}개")
    for bf in batch_files:
        print(f"  - {bf.name}")

    # 2. 모든 배치 결과 로드 및 병합
    all_results = []
    for batch_file in batch_files:
        with open(batch_file, "r", encoding="utf-8") as f:
            batch_results = json.load(f)
            all_results.extend(batch_results)
            print(f"  ✓ {batch_file.name}: {len(batch_results)}개")

    print(f"\n  총 결과: {len(all_results)}개")

    # 3. Full + Summary 결과 저장
    save_experiment_results(
        results=all_results,
        output_dir=output_dir,
        group_name=group_name,
        experiment_type="isolation"
    )

    # 5. 통계 출력
    success_count = sum(1 for r in all_results if r.get("metrics"))
    print(f"\n{'='*70}")
    print(f"병합 완료 통계")
    print(f"{'='*70}")
    print(f"  전체 결과: {len(all_results)}개")
    print(f"  성공: {success_count}개")
    print(f"  실패: {len(all_results) - success_count}개")

    if success_count > 0:
        scores = [r["metrics"]["final_score"] for r in all_results if r.get("metrics")]
        avg_score = sum(scores) / len(scores)
        print(f"  평균 점수: {avg_score:.4f}")


def main():
    parser = argparse.ArgumentParser(description="배치 결과 병합")
    parser.add_argument("--group", type=str, required=True,
                        choices=["semantic_expander", "thread", "entity_boost", "all"],
                        help="실험 그룹")
    parser.add_argument("--batch-dir", type=str,
                        default="backend/ragas/ontology_evaluate/data/results_isolation/batches",
                        help="배치 결과 디렉토리")
    parser.add_argument("--output-dir", type=str,
                        default="backend/ragas/ontology_evaluate/data/results_isolation",
                        help="최종 결과 출력 디렉토리")

    args = parser.parse_args()

    batch_base_dir = Path(args.batch_dir)
    output_dir = Path(args.output_dir)

    if args.group == "all":
        # 모든 그룹 처리
        for group in ["semantic_expander", "thread", "entity_boost"]:
            batch_dir = batch_base_dir / group
            if batch_dir.exists():
                merge_and_save_results(batch_dir, output_dir, group)
            else:
                print(f"⚠️  경고: {batch_dir} 디렉토리가 없습니다. 건너뜁니다.")
    else:
        # 특정 그룹만 처리
        batch_dir = batch_base_dir / args.group
        if not batch_dir.exists():
            print(f"❌ 오류: {batch_dir} 디렉토리가 없습니다.")
            return

        merge_and_save_results(batch_dir, output_dir, args.group)


if __name__ == "__main__":
    main()
