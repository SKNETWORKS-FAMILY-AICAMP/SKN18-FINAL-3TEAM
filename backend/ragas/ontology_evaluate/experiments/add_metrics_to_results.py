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
from backend.ragas.ontology_evaluate.common_eval import evaluate_state, get_ontology_schema
from backend.ragas.ontology_evaluate.evaluators import AnswerQualityEvaluator
from backend.ragas.ontology_evaluate.utils.llm_judge import LLMJudge


def load_queries(queries_path: str) -> List[Dict[str, Any]]:
    """질문 데이터 로드"""
    with open(queries_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_experiment_results(results: list, output_dir: str, group_name: str, queries_data: list):
    """실험 결과를 2개 파일로 저장: Full + Summary

    run_ablation.py의 _save_experiment_results 함수와 동일한 로직

    Args:
        results: 실험 결과 리스트 (metrics 포함)
        output_dir: 출력 디렉토리
        group_name: 실험 그룹명
        queries_data: 원본 질문 데이터
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Full 결과 저장 (기존 방식, 모든 state 포함)
    full_file = output_path / f"{group_name}_ablation_full.json"
    with open(full_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  → Full 결과: {full_file}")

    # 2. Summary 결과 생성 (점수, 수치만)
    summary_results = []
    for idx, result in enumerate(results):
        query_idx = idx % len(queries_data)
        query_data = queries_data[query_idx]

        summary_item = {
            "experiment_name": result.get("experiment_name", ""),
            "description": result.get("description", ""),
            "query": result.get("query", ""),
            "query_type": query_data.get("query_type", "unknown"),
            "success": result.get("success", False),
            "execution_time": result.get("execution_time", 0.0),
            "config": result.get("config", {}),
        }

        if result.get("success") and result.get("state_output"):
            state = result["state_output"]

            # 답변 추가
            summary_item["final_answer"] = state.get("final_answer", "")

            # 엔티티 개수
            extracted_entities = state.get("extracted_entities", [])
            expanded_entities = state.get("expanded_entities", [])
            summary_item["num_extracted_entities"] = len(extracted_entities)
            summary_item["num_expanded_entities"] = len(expanded_entities)

            # Evidence 개수
            evidences = state.get("evidences", [])
            summary_item["num_evidences"] = len(evidences)

            # Convergence nodes 개수
            convergence_nodes = state.get("convergence_nodes", [])
            summary_item["num_convergence_nodes"] = len(convergence_nodes)

            # 메트릭 점수
            if result.get("metrics"):
                metrics = result["metrics"]

                # Raw metrics
                summary_item["raw_metrics"] = metrics.get("raw_metrics", {})

                # Intent-aware final score
                if metrics.get("intent_aware"):
                    ia = metrics["intent_aware"]
                    summary_item["intent_aware_score"] = ia.get("final_score", 0.0)
                    summary_item["weighted_metrics"] = ia.get("weighted_metrics", {})
                else:
                    # Fallback: raw metrics 평균
                    raw_scores = list(metrics.get("raw_metrics", {}).values())
                    summary_item["intent_aware_score"] = sum(raw_scores) / len(raw_scores) if raw_scores else 0.0

                # LLM Judge 답변 품질 점수 추가
                if metrics.get("llm_judge_quality"):
                    summary_item["llm_judge_quality"] = metrics["llm_judge_quality"]
        else:
            # 실패한 경우
            summary_item["error"] = result.get("error", "Unknown error")
            summary_item["final_answer"] = ""
            summary_item["num_extracted_entities"] = 0
            summary_item["num_expanded_entities"] = 0
            summary_item["num_evidences"] = 0
            summary_item["num_convergence_nodes"] = 0
            summary_item["raw_metrics"] = {}
            summary_item["intent_aware_score"] = 0.0

        summary_results.append(summary_item)

    # Summary 파일 저장
    summary_file = output_path / f"{group_name}_ablation_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, ensure_ascii=False, indent=2)
    print(f"  → Summary: {summary_file}")


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
    _save_experiment_results(results, output_dir, group_name, queries_data)

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
    ontology_schema = get_ontology_schema()
    print(f"  ✓ 질문 데이터: {len(queries_data)}개")
    print(f"  ✓ 온톨로지 스키마 로드 완료")

    # 2. 평가자 초기화
    print("\n🔧 평가자 초기화 중...")
    llm_judge = LLMJudge()
    answer_quality_evaluator = AnswerQualityEvaluator()
    print("  ✓ LLM Judge 초기화 완료")
    print("  ✓ Answer Quality Evaluator 초기화 완료")

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
