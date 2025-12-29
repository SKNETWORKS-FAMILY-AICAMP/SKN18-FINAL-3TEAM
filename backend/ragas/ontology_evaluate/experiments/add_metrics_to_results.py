"""
완료된 실험 결과에 평가 메트릭을 추가하고 Full + Summary 파일 생성

run_ablation.py의 evaluate_state와 _save_experiment_results 로직을 재사용합니다.

사용법:
    # 단일 파일 처리
    python -m backend.ragas.ontology_evaluate.experiments.add_metrics_to_results \
        --input backend/ragas/ontology_evaluate/data/results_isolation/semantic_expander_ablation.json \
        --group semantic_expander

    # 전체 그룹 처리
    python -m backend.ragas.ontology_evaluate.experiments.add_metrics_to_results \
        --group all
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
import sys

# 공통 평가 모듈
from backend.ragas.ontology_evaluate.common_eval import evaluate_state
from backend.ragas.ontology_evaluate.utils.experiment_utils import (
    load_queries,
    save_experiment_results,
    initialize_evaluators
)


def process_single_file(
    input_file: str,
    output_dir: str,
    group_name: str,
    queries_data: list,
    llm_judge: LLMJudge,
    answer_quality_evaluator: AnswerQualityEvaluator,
    ontology_schema: dict,
    use_intent_aware: bool
) -> int:
    """단일 ablation.json 파일 처리"""
    print(f"\n{'='*70}")
    print(f"파일 처리: {input_file}")
    print(f"{'='*70}\n")

    # 1. 파일 로드
    print("📂 데이터 로드 중...")
    with open(input_file, "r", encoding="utf-8") as f:
        results = json.load(f)
    print(f"  ✓ 실험 결과: {len(results)}개")

    # 2. 각 결과에 metrics 추가
    print(f"\n📊 평가 메트릭 추가 중... (총 {len(results)}개)")
    metrics_added = 0

    for idx, result in enumerate(results):
        if not result.get("success"):
            continue

        # 해당 쿼리의 query_type 가져오기
        query_idx = idx % len(queries_data)
        query_data = queries_data[query_idx]
        query = result.get("query", "")
        query_type = query_data.get("query_type", "factual")
        expected_property_groups = query_data.get("expected_property_groups", [])

        # state_output 확인
        state_output = result.get("state_output")
        if not state_output:
            continue

        # 평가 실행
        try:
            metrics = evaluate_state(
                state_output,
                llm_judge,
                ontology_schema,
                answer_quality_evaluator,
                query=query,
                query_type=query_type,
                expected_property_groups=expected_property_groups,
                use_intent_aware=use_intent_aware
            )
            result["metrics"] = metrics
            metrics_added += 1

            # 진행상황 출력 (10개마다)
            if (idx + 1) % 10 == 0:
                print(f"  ✓ [{idx+1}/{len(results)}] 평가 완료")

        except Exception as e:
            print(f"  ✗ [{idx+1}/{len(results)}] 평가 실패: {e}")
            result["metrics"] = {}

    # 3. Full + Summary 파일 저장
    print(f"\n💾 결과 저장 중...")
    save_experiment_results(
        results=results,
        output_dir=Path(output_dir),
        group_name=group_name,
        experiment_type="ablation",
        queries_data=queries_data
    )

    print(f"\n✅ 완료! Metrics 추가: {metrics_added}/{len(results)}개")
    return metrics_added


def main():
    parser = argparse.ArgumentParser(description="완료된 실험 결과에 평가 메트릭 추가 및 Full+Summary 생성")
    parser.add_argument(
        "--group",
        type=str,
        choices=["semantic_expander", "thread", "entity_boost", "all"],
        required=True,
        help="실험 그룹 선택"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="backend/ragas/ontology_evaluate/data/results_isolation",
        help="입력 디렉토리 (ablation.json 파일이 있는 곳)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="출력 디렉토리 (기본값: input-dir과 동일)"
    )
    parser.add_argument(
        "--queries",
        type=str,
        default="backend/ragas/ontology_evaluate/data/test_queries.json",
        help="질문 데이터 파일 경로"
    )
    parser.add_argument(
        "--intent-aware",
        action="store_true",
        default=True,
        help="Intent-aware 평가 사용"
    )
    parser.add_argument(
        "--no-intent-aware",
        dest="intent_aware",
        action="store_false",
        help="Intent-aware 평가 비활성화"
    )

    args = parser.parse_args()

    # 출력 디렉토리 기본값 설정
    output_dir = args.output_dir or args.input_dir

    print(f"입력 디렉토리: {args.input_dir}")
    print(f"출력 디렉토리: {output_dir}")
    print(f"질문 데이터: {args.queries}")
    print(f"Intent-aware: {'활성화' if args.intent_aware else '비활성화'}")
    print(f"그룹: {args.group}")
    print(f"{'='*70}\n")

    # 1. 공통 데이터 로드
    print("📂 공통 데이터 로드 중...")
    queries_data = load_queries(args.queries)
    print(f"  ✓ 질문 데이터: {len(queries_data)}개")

    # 2. 평가자 초기화
    print("\n🔧 평가자 초기화 중...")
    llm_judge, answer_quality_evaluator, ontology_schema = initialize_evaluators()
    print("  ✓ 평가자 초기화 완료")

    # 3. 처리할 그룹 결정
    if args.group == "all":
        groups = ["semantic_expander", "thread", "entity_boost"]
    else:
        groups = [args.group]

    # 4. 각 그룹 처리
    input_dir_path = Path(args.input_dir)
    total_added = 0

    for group in groups:
        input_file = input_dir_path / f"{group}_ablation.json"

        # 파일 존재 확인
        if not input_file.exists():
            print(f"\n⚠️  {input_file} 파일이 없습니다. 건너뛰기...")
            continue

        # 파일 처리
        metrics_added = process_single_file(
            str(input_file),
            output_dir,
            group,
            queries_data,
            llm_judge,
            answer_quality_evaluator,
            ontology_schema,
            args.intent_aware
        )
        total_added += metrics_added

    # 5. 최종 요약
    print(f"\n{'='*70}")
    print(f"✅ 전체 작업 완료!")
    print(f"{'='*70}")
    print(f"처리한 그룹: {len(groups)}개")
    print(f"총 Metrics 추가: {total_added}개")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
