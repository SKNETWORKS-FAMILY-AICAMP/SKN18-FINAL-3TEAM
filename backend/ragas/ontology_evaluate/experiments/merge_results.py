"""
배치 결과 통합 스크립트

4개 배치의 평가 결과를 하나의 파일로 통합하고 통계를 계산합니다.

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.merge_results --timestamp 20241226_153000
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "backend" / "ragas" / "ontology_evaluate" / "data"
RESULTS_DIR = DATA_DIR / "full_evaluation_results"


def calculate_statistics(results: list) -> dict:
    """
    전체 결과 통계 계산

    Args:
        results: 전체 결과 리스트

    Returns:
        통계 딕셔너리
    """
    # 쿼리 타입별 분류
    by_query_type = defaultdict(list)
    by_difficulty = defaultdict(list)

    for result in results:
        if result["status"] != "success":
            continue

        query_type = result["query_type"]
        difficulty = result["query_data"].get("difficulty", "unknown")
        final_score = result["evaluation"]["final_score"]

        by_query_type[query_type].append(final_score)
        by_difficulty[difficulty].append(final_score)

    # 전체 통계
    all_scores = [r["evaluation"]["final_score"] for r in results if r["status"] == "success"]

    stats = {
        "total_queries": len(results),
        "success_count": sum(1 for r in results if r["status"] == "success"),
        "error_count": sum(1 for r in results if r["status"] == "error"),
        "overall": {
            "mean": sum(all_scores) / len(all_scores) if all_scores else 0,
            "min": min(all_scores) if all_scores else 0,
            "max": max(all_scores) if all_scores else 0,
            "count": len(all_scores)
        },
        "by_query_type": {},
        "by_difficulty": {}
    }

    # 쿼리 타입별 통계
    for query_type, scores in by_query_type.items():
        stats["by_query_type"][query_type] = {
            "mean": sum(scores) / len(scores),
            "min": min(scores),
            "max": max(scores),
            "count": len(scores)
        }

    # 난이도별 통계
    for difficulty, scores in by_difficulty.items():
        stats["by_difficulty"][difficulty] = {
            "mean": sum(scores) / len(scores),
            "min": min(scores),
            "max": max(scores),
            "count": len(scores)
        }

    return stats


def print_statistics(stats: dict):
    """통계 출력"""
    print("\n" + "="*80)
    print("전체 평가 통계")
    print("="*80)

    print(f"\n총 질문: {stats['total_queries']}개")
    print(f"성공: {stats['success_count']}개")
    print(f"실패: {stats['error_count']}개")

    print(f"\n전체 평균 점수: {stats['overall']['mean']:.4f}")
    print(f"최저 점수: {stats['overall']['min']:.4f}")
    print(f"최고 점수: {stats['overall']['max']:.4f}")

    print("\n쿼리 타입별 평균 점수:")
    for query_type in ["factual", "causal", "comparative", "deep_analysis"]:
        if query_type in stats["by_query_type"]:
            qtype_stats = stats["by_query_type"][query_type]
            print(f"  {query_type:15s}: {qtype_stats['mean']:.4f} ({qtype_stats['count']}개)")

    print("\n난이도별 평균 점수:")
    for difficulty in ["easy", "medium", "hard"]:
        if difficulty in stats["by_difficulty"]:
            diff_stats = stats["by_difficulty"][difficulty]
            print(f"  {difficulty:10s}: {diff_stats['mean']:.4f} ({diff_stats['count']}개)")


def main():
    parser = argparse.ArgumentParser(description="배치 결과 통합")
    parser.add_argument("--timestamp", type=str, required=True, help="실행 타임스탬프")
    args = parser.parse_args()

    timestamp = args.timestamp

    print("="*80)
    print("배치 결과 통합 시작")
    print("="*80)
    print(f"타임스탬프: {timestamp}")

    # 4개 배치 결과 로드
    all_results = []
    batch_summaries = []

    for batch_num in range(1, 5):
        batch_file = RESULTS_DIR / f"batch_{batch_num}_results_{timestamp}.json"

        if not batch_file.exists():
            print(f"\n⚠️  Batch {batch_num} 결과 파일 없음: {batch_file}")
            continue

        with open(batch_file, "r", encoding="utf-8") as f:
            batch_data = json.load(f)

        batch_results = batch_data.get("results", [])
        all_results.extend(batch_results)

        batch_summary = {
            "batch_num": batch_num,
            "total": batch_data.get("total_queries", 0),
            "success": batch_data.get("success_count", 0),
            "error": batch_data.get("error_count", 0)
        }
        batch_summaries.append(batch_summary)

        print(f"\n✓ Batch {batch_num} 로드 완료: {len(batch_results)}개 결과")

    print(f"\n총 {len(all_results)}개 결과 로드 완료")

    # 통계 계산
    stats = calculate_statistics(all_results)

    # 통합 결과 저장
    merged_file = RESULTS_DIR / f"full_evaluation_results_{timestamp}.json"
    merged_data = {
        "timestamp": timestamp,
        "total_queries": len(all_results),
        "batch_summaries": batch_summaries,
        "statistics": stats,
        "results": all_results,
        "config": {
            "rag_pipeline": "Quick Win (incoming=0.0, normalized/partial=1.5, semantic_expander=0.0)",
            "eval_weights": "aggressive_intent (intent_preservation=5.0, others=1.0/0.5)"
        }
    }

    with open(merged_file, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 통합 결과 저장: {merged_file}")

    # 통계 출력
    print_statistics(stats)

    # 요약 리포트 생성
    report_file = RESULTS_DIR / f"evaluation_report_{timestamp}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# 전체 평가 리포트\n\n")
        f.write(f"**실행 시간**: {timestamp}\n\n")
        f.write(f"**설정**:\n")
        f.write(f"- RAG 파이프라인: Quick Win (incoming=0.0, normalized/partial=1.5, semantic_expander=0.0)\n")
        f.write(f"- 평가 가중치: aggressive_intent (intent_preservation=5.0)\n\n")

        f.write(f"## 전체 통계\n\n")
        f.write(f"| 항목 | 값 |\n")
        f.write(f"|------|----|\n")
        f.write(f"| 총 질문 | {stats['total_queries']}개 |\n")
        f.write(f"| 성공 | {stats['success_count']}개 |\n")
        f.write(f"| 실패 | {stats['error_count']}개 |\n")
        f.write(f"| 평균 점수 | {stats['overall']['mean']:.4f} |\n")
        f.write(f"| 최저 점수 | {stats['overall']['min']:.4f} |\n")
        f.write(f"| 최고 점수 | {stats['overall']['max']:.4f} |\n\n")

        f.write(f"## 쿼리 타입별 성능\n\n")
        f.write(f"| 쿼리 타입 | 평균 점수 | 질문 수 |\n")
        f.write(f"|----------|----------|--------|\n")
        for query_type in ["factual", "causal", "comparative", "deep_analysis"]:
            if query_type in stats["by_query_type"]:
                qtype_stats = stats["by_query_type"][query_type]
                f.write(f"| {query_type} | {qtype_stats['mean']:.4f} | {qtype_stats['count']} |\n")

        f.write(f"\n## 난이도별 성능\n\n")
        f.write(f"| 난이도 | 평균 점수 | 질문 수 |\n")
        f.write(f"|--------|----------|--------|\n")
        for difficulty in ["easy", "medium", "hard"]:
            if difficulty in stats["by_difficulty"]:
                diff_stats = stats["by_difficulty"][difficulty]
                f.write(f"| {difficulty} | {diff_stats['mean']:.4f} | {diff_stats['count']} |\n")

    print(f"\n✓ 리포트 저장: {report_file}")

    print("\n" + "="*80)
    print("배치 결과 통합 완료!")
    print("="*80)


if __name__ == "__main__":
    main()
