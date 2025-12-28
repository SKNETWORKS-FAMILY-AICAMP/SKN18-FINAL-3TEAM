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

    # 3. Full 결과 저장
    full_file = output_dir / f"{group_name}_isolation_full.json"
    with open(full_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Full 결과 저장: {full_file}")

    # 4. Summary 결과 생성
    summary_results = []
    for result in all_results:
        if result.get("success") and result.get("metrics"):
            state = result.get("state_output", {})
            metrics = result["metrics"]
            ia = metrics.get("intent_aware", {})

            summary_item = {
                "experiment_name": result.get("experiment_name", ""),
                "query": result.get("query", ""),
                "query_type": result.get("query_type", ""),
                "final_answer": state.get("final_answer", ""),
                "num_extracted_entities": len(state.get("extracted_entities", [])),
                "num_expanded_entities": len(state.get("expanded_entities", [])),
                "num_evidences": len(state.get("evidences", [])),
                "num_convergence_nodes": len(state.get("convergence_triple_tree", {}).get("nodes", [])),
                "raw_metrics": metrics.get("raw_metrics", {}),
                "intent_aware_score": ia.get("final_score", 0.0) if ia else 0.0,
                "weighted_metrics": ia.get("weighted_metrics", {}) if ia else {},
                "llm_judge_quality": result.get("llm_judge_quality")
            }
        else:
            summary_item = {
                "experiment_name": result.get("experiment_name", ""),
                "query": result.get("query", ""),
                "query_type": result.get("query_type", ""),
                "success": False,
                "error": result.get("error")
            }
        summary_results.append(summary_item)

    summary_file = output_dir / f"{group_name}_isolation_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, ensure_ascii=False, indent=2)
    print(f"✓ Summary 결과 저장: {summary_file}")

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
