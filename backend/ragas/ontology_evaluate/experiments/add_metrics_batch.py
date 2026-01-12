"""
배치 병렬 평가 메트릭 추가 스크립트

큰 결과 파일을 작은 배치로 나눠서 병렬로 평가 메트릭을 추가합니다.

사용법:
    # 특정 그룹의 배치 처리
    python -m backend.ragas.ontology_evaluate.experiments.add_metrics_batch \
        --group semantic_expander --batch-size 10 --batch-num 0

    # 전체 그룹 병렬 실행 (별도 터미널에서)
    ./run_parallel_add_metrics.sh
"""

import json
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any

# 공통 평가 모듈
from backend.ragas.ontology_evaluate.common_eval import evaluate_state
from backend.ragas.ontology_evaluate.evaluators import AnswerQualityEvaluator
from backend.ragas.ontology_evaluate.utils.llm_judge import LLMJudge
from backend.ragas.ontology_evaluate.utils.experiment_utils import (
    load_queries,
    initialize_evaluators
)


def process_batch(
    results: List[Dict],
    queries_data: List[Dict],
    llm_judge: LLMJudge,
    ontology_schema: dict,
    answer_quality_evaluator: AnswerQualityEvaluator,
    batch_num: int,
    total_batches: int
) -> List[Dict]:
    """배치 단위로 평가 메트릭 추가"""

    print(f"\n{'='*70}")
    print(f"배치 {batch_num + 1}/{total_batches} 처리 중 ({len(results)}개 결과)")
    print(f"{'='*70}")

    # query를 빠르게 찾기 위한 dict
    query_map = {q["query"]: q for q in queries_data}

    evaluated_results = []

    for idx, result in enumerate(results):
        if not result.get("success", False):
            # 실패한 결과는 그대로 유지
            evaluated_results.append(result)
            continue

        query = result.get("query", "")
        state_output = result.get("state_output", {})

        # 해당 쿼리 정보 찾기
        query_data = query_map.get(query, {})
        query_type = query_data.get("query_type", "factual")
        expected_property_groups = query_data.get("expected_property_groups", [])

        print(f"  [{idx+1}/{len(results)}] {query[:50]}...")

        try:
            # 평가 메트릭 추가
            metrics = evaluate_state(
                state_output,
                llm_judge,
                ontology_schema,
                answer_quality_evaluator,
                query=query,
                query_type=query_type,
                expected_property_groups=expected_property_groups,
                use_intent_aware=True
            )

            # 결과에 metrics 추가
            result["metrics"] = {
                "raw_metrics": metrics["raw_metrics"],
                "intent_aware": metrics["intent_aware"],
                "final_score": metrics["intent_aware"]["final_score"] if metrics["intent_aware"] else 0.0
            }
            result["llm_judge_quality"] = metrics["llm_judge_quality"]
            result["query_type"] = query_type

            score = result["metrics"]["final_score"]
            judge_score = metrics["llm_judge_quality"].get("overall_score", 0) if metrics["llm_judge_quality"] else 0
            print(f"    ✓ Score: {score:.4f} | Judge: {judge_score:.4f}")

        except Exception as e:
            print(f"    ✗ Error: {str(e)[:100]}")
            result["metrics"] = None
            result["error"] = str(e)

        evaluated_results.append(result)

    return evaluated_results


def main():
    parser = argparse.ArgumentParser(description="배치 병렬 평가 메트릭 추가")
    parser.add_argument("--group", type=str, required=True,
                        choices=["semantic_expander", "thread", "entity_boost"],
                        help="실험 그룹")
    parser.add_argument("--batch-size", type=int, default=20,
                        help="배치 크기 (기본: 20)")
    parser.add_argument("--batch-num", type=int, required=True,
                        help="배치 번호 (0부터 시작)")
    parser.add_argument("--queries", type=str,
                        default="backend/ragas/ontology_evaluate/data/test_queries.json",
                        help="질문 파일 경로")
    parser.add_argument("--input-dir", type=str,
                        default="backend/ragas/ontology_evaluate/data/results_isolation",
                        help="입력 디렉토리")
    parser.add_argument("--output-dir", type=str,
                        default="backend/ragas/ontology_evaluate/data/results_isolation/batches",
                        help="배치 결과 출력 디렉토리")

    args = parser.parse_args()

    print("=" * 80)
    print(f"배치 병렬 평가 메트릭 추가 - {args.group} (Batch {args.batch_num})")
    print("=" * 80)

    # 1. 입력 파일 로드
    input_file = Path(args.input_dir) / f"{args.group}_ablation.json"
    print(f"\n📂 입력 파일 로드: {input_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        all_results = json.load(f)

    print(f"  ✓ 전체 결과: {len(all_results)}개")

    # 2. 배치 분할
    start_idx = args.batch_num * args.batch_size
    end_idx = min(start_idx + args.batch_size, len(all_results))

    if start_idx >= len(all_results):
        print(f"\n❌ 오류: 배치 {args.batch_num}는 범위를 벗어났습니다.")
        print(f"   전체 결과: {len(all_results)}개, 배치 크기: {args.batch_size}")
        print(f"   최대 배치 번호: {(len(all_results) - 1) // args.batch_size}")
        return

    batch_results = all_results[start_idx:end_idx]
    total_batches = (len(all_results) + args.batch_size - 1) // args.batch_size

    print(f"  ✓ 배치 범위: [{start_idx}:{end_idx}] ({len(batch_results)}개)")
    print(f"  ✓ 전체 배치: {total_batches}개")

    # 3. 질문 데이터 로드
    queries_data = load_queries(args.queries)
    print(f"  ✓ 질문 데이터: {len(queries_data)}개")

    # 4. 평가자 초기화
    print("\n🔧 평가자 초기화 중...")
    llm_judge, answer_quality_evaluator, ontology_schema = initialize_evaluators()
    print("  ✓ 초기화 완료")

    # 5. 배치 평가
    start_time = time.time()

    evaluated_results = process_batch(
        batch_results,
        queries_data,
        llm_judge,
        ontology_schema,
        answer_quality_evaluator,
        args.batch_num,
        total_batches
    )

    elapsed = time.time() - start_time

    # 6. 배치 결과 저장
    output_dir = Path(args.output_dir) / args.group
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"batch_{args.batch_num:03d}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(evaluated_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print(f"✅ 배치 {args.batch_num} 완료!")
    print(f"{'='*70}")
    print(f"  처리 결과: {len(evaluated_results)}개")
    print(f"  소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    print(f"  평균 시간: {elapsed/len(evaluated_results):.1f}초/개")
    print(f"  저장 위치: {output_file}")

    # 성공/실패 통계
    success_count = sum(1 for r in evaluated_results if r.get("metrics"))
    print(f"\n  성공: {success_count}/{len(evaluated_results)}개")

    if success_count > 0:
        scores = [r["metrics"]["final_score"] for r in evaluated_results if r.get("metrics")]
        avg_score = sum(scores) / len(scores)
        print(f"  평균 점수: {avg_score:.4f}")


if __name__ == "__main__":
    main()
