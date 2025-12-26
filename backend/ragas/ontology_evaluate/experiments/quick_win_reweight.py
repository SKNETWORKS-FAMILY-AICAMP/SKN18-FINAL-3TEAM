"""
Quick Win: Intent Preservation 가중치 최적화

기존 실험 결과를 다양한 intent_preservation 가중치로 재계산하여
Full이 Baseline을 초과하는 최적 가중치를 찾습니다.

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.quick_win_reweight \
        --results backend/ragas/ontology_evaluate/data/baseline_results \
        --output backend/ragas/ontology_evaluate/data/quick_win \
        --weights 1.0 1.5 2.0 2.5 3.0
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


def load_full_results(results_dir: Path, group: str) -> List[Dict[str, Any]]:
    """Full 결과 파일 로드"""
    full_file = results_dir / f"{group}_ablation_full.json"
    if not full_file.exists():
        raise FileNotFoundError(f"Full 결과 파일이 없습니다: {full_file}")

    with open(full_file, "r", encoding="utf-8") as f:
        return json.load(f)


def recalculate_weighted_score(
    metrics: Dict[str, float],
    intent_weight: float
) -> float:
    """
    Intent preservation 가중치를 조정하여 최종 점수 재계산

    기본 가중치:
    - tbox_consistency: 1.0
    - intent_preservation: intent_weight (조정 가능)
    - relation_coherence: 1.0
    - property_group_selection: 1.0
    - triple_validity: 1.0
    - evidence_diversity: 1.0
    - convergence_utilization: 1.0
    """
    if not metrics:
        return 0.0

    weights = {
        "tbox_consistency": 1.0,
        "intent_preservation": intent_weight,
        "relation_coherence": 1.0,
        "property_group_selection": 1.0,
        "triple_validity": 1.0,
        "evidence_diversity": 1.0,
        "convergence_utilization": 1.0
    }

    weighted_sum = 0.0
    total_weight = 0.0

    for metric_name, weight in weights.items():
        if metric_name in metrics:
            weighted_sum += metrics[metric_name] * weight
            total_weight += weight

    return weighted_sum / total_weight if total_weight > 0 else 0.0


def analyze_experiments_by_weight(
    results: List[Dict[str, Any]],
    intent_weight: float
) -> Dict[str, Any]:
    """특정 가중치로 실험 결과 재분석"""

    # 실험별로 그룹화
    experiments = defaultdict(list)

    for result in results:
        if not result.get("success"):
            continue

        exp_name = result.get("experiment_name", "unknown")
        metrics = result.get("metrics", {})

        # 가중치 적용하여 점수 재계산
        new_score = recalculate_weighted_score(metrics, intent_weight)

        experiments[exp_name].append({
            "query": result.get("query", ""),
            "original_score": result.get("metrics", {}).get("weighted_average", 0.0),
            "new_score": new_score,
            "metrics": metrics
        })

    # 실험별 평균 계산
    summary = {}
    for exp_name, exp_results in experiments.items():
        scores = [r["new_score"] for r in exp_results]
        summary[exp_name] = {
            "mean": sum(scores) / len(scores) if scores else 0.0,
            "count": len(scores),
            "scores": scores
        }

    return summary


def find_best_weight(
    results: List[Dict[str, Any]],
    weights: List[float],
    baseline_name: str = "baseline",
    full_name: str = "full"
) -> Dict[str, Any]:
    """최적 가중치 찾기"""

    print("\n" + "=" * 70)
    print("Intent Preservation 가중치별 성능 분석")
    print("=" * 70)

    weight_analysis = []

    for weight in weights:
        summary = analyze_experiments_by_weight(results, weight)

        baseline_score = summary.get(baseline_name, {}).get("mean", 0.0)
        full_score = summary.get(full_name, {}).get("mean", 0.0)
        improvement = ((full_score - baseline_score) / baseline_score * 100) if baseline_score > 0 else 0.0

        weight_analysis.append({
            "intent_weight": weight,
            "baseline_score": baseline_score,
            "full_score": full_score,
            "improvement": improvement,
            "full_beats_baseline": full_score > baseline_score,
            "all_experiments": summary
        })

        print(f"\nIntent Weight: {weight:.1f}")
        print(f"  Baseline: {baseline_score:.4f}")
        print(f"  Full:     {full_score:.4f}")
        print(f"  Improvement: {improvement:+.2f}%")
        print(f"  Full > Baseline: {'✅ YES' if full_score > baseline_score else '❌ NO'}")

    # 최적 가중치 찾기 (Full이 Baseline을 가장 많이 초과하는 가중치)
    best = max(weight_analysis, key=lambda x: x["improvement"])

    print("\n" + "=" * 70)
    print("최적 가중치 분석")
    print("=" * 70)
    print(f"최적 Intent Weight: {best['intent_weight']:.1f}")
    print(f"  Baseline: {best['baseline_score']:.4f}")
    print(f"  Full:     {best['full_score']:.4f}")
    print(f"  Improvement: {best['improvement']:+.2f}%")

    return {
        "best_weight": best["intent_weight"],
        "best_improvement": best["improvement"],
        "weight_analysis": weight_analysis
    }


def save_results(output_path: Path, group: str, analysis: Dict[str, Any]):
    """결과 저장"""
    output_path.mkdir(parents=True, exist_ok=True)

    # 전체 분석 결과 저장
    output_file = output_path / f"{group}_quick_win_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {output_file}")

    # 요약 테이블 생성
    summary_file = output_path / f"{group}_quick_win_summary.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("# Quick Win: Intent Preservation 가중치 최적화 결과\n\n")
        f.write("## 가중치별 성능 비교\n\n")
        f.write("| Intent Weight | Baseline | Full | Improvement | Full > Baseline |\n")
        f.write("|---------------|----------|------|-------------|------------------|\n")

        for wa in analysis["weight_analysis"]:
            status = "✅" if wa["full_beats_baseline"] else "❌"
            f.write(f"| {wa['intent_weight']:.1f} | {wa['baseline_score']:.4f} | "
                   f"{wa['full_score']:.4f} | {wa['improvement']:+.2f}% | {status} |\n")

        f.write(f"\n## 최적 가중치\n\n")
        f.write(f"**Intent Preservation Weight: {analysis['best_weight']:.1f}**\n\n")
        f.write(f"- Baseline: {analysis['weight_analysis'][int(analysis['best_weight']/0.5)]['baseline_score']:.4f}\n")
        f.write(f"- Full: {analysis['weight_analysis'][int(analysis['best_weight']/0.5)]['full_score']:.4f}\n")
        f.write(f"- Improvement: {analysis['best_improvement']:+.2f}%\n")

    print(f"요약 저장: {summary_file}")


def main():
    parser = argparse.ArgumentParser(description="Quick Win: Intent 가중치 최적화")
    parser.add_argument(
        "--results",
        type=str,
        default="backend/ragas/ontology_evaluate/data/results_rerun",
        help="실험 결과 디렉토리"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="backend/ragas/ontology_evaluate/data/quick_win",
        help="출력 디렉토리"
    )
    parser.add_argument(
        "--group",
        type=str,
        default="semantic_expander",
        choices=["semantic_expander", "thread", "entity_boost"],
        help="실험 그룹"
    )
    parser.add_argument(
        "--weights",
        type=float,
        nargs="+",
        default=[1.0, 1.5, 2.0, 2.5, 3.0],
        help="테스트할 Intent 가중치 목록"
    )
    parser.add_argument(
        "--baseline",
        type=str,
        default="baseline",
        help="Baseline 실험 이름"
    )
    parser.add_argument(
        "--full",
        type=str,
        default="full",
        help="Full 실험 이름"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Quick Win: Intent Preservation 가중치 최적화")
    print("=" * 70)
    print(f"실험 그룹: {args.group}")
    print(f"결과 디렉토리: {args.results}")
    print(f"테스트 가중치: {args.weights}")
    print("=" * 70)

    # 1. Full 결과 로드
    print("\n[1/3] Full 결과 로드 중...")
    results_dir = Path(args.results)
    results = load_full_results(results_dir, args.group)
    print(f"  → {len(results)}개 결과 로드 완료")

    # 2. 최적 가중치 찾기
    print("\n[2/3] 최적 가중치 찾기...")
    analysis = find_best_weight(
        results,
        args.weights,
        baseline_name=args.baseline,
        full_name=args.full
    )

    # 3. 결과 저장
    print("\n[3/3] 결과 저장 중...")
    output_path = Path(args.output)
    save_results(output_path, args.group, analysis)

    print("\n" + "=" * 70)
    print("✅ Quick Win 분석 완료!")
    print("=" * 70)

    # 권장 사항 출력
    best_analysis = analysis["weight_analysis"][
        [i for i, wa in enumerate(analysis["weight_analysis"])
         if wa["intent_weight"] == analysis["best_weight"]][0]
    ]

    if best_analysis["full_beats_baseline"]:
        print("\n🎉 성공! Full이 Baseline을 초과했습니다.")
        print(f"   → 권장 Intent Weight: {analysis['best_weight']:.1f}")
        print(f"   → Step 2 (Bayesian Optimization) 건너뛰고 다음 단계로 진행 가능")
    else:
        print("\n⚠️  Full이 여전히 Baseline보다 낮습니다.")
        print(f"   → 최선의 Intent Weight: {analysis['best_weight']:.1f} (Improvement: {analysis['best_improvement']:+.2f}%)")
        print(f"   → Step 2 (Bayesian Optimization)로 전체 가중치 최적화 필요")


if __name__ == "__main__":
    main()
