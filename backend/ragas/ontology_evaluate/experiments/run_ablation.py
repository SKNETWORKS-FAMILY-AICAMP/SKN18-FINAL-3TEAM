"""
Baseline Ablation Study 실행

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.run_ablation --group semantic_expander
"""

import argparse
import json
from pathlib import Path
from typing import List

from backend.ragas.ontology_evaluate.baseline_ablation import AblationRunner, AblationExperimentGenerator
from backend.ragas.ontology_evaluate.evaluators import (
    TBoxConsistencyEvaluator,
    IntentPreservationEvaluator,
    RelationCoherenceEvaluator,
    PropertyGroupSelectionEvaluator,
    TerminalTripleValidityEvaluator,
    EvidenceDiversityEvaluator,
    ConvergenceUtilizationEvaluator
)
from backend.ragas.ontology_evaluate.evaluators.intent_aware_evaluator import IntentAwareEvaluator
from backend.ragas.ontology_evaluate.utils.llm_judge import LLMJudge

# LangGraph import
from backend.langgraph_fuseki.graph import create_graph_flow


def _save_experiment_results(results: list, output_dir: str, group_name: str, queries_data: list):
    """실험 결과를 2개 파일로 저장: Full + Summary

    Args:
        results: 실험 결과 리스트
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


def load_queries(queries_file: str):
    """테스트 질문 로드"""
    queries_path = Path(queries_file)
    
    with open(queries_path, "r", encoding="utf-8") as f:
        queries_data = json.load(f)

    return queries_data


def evaluate_state(
    state_output: dict,
    llm_judge: LLMJudge,
    ontology_schema: dict,
    query_type: str = None,
    expected_property_groups: List[str] = None,
    use_intent_aware: bool = True
) -> dict:
    """GraphState에 대해 모든 평가 메트릭 실행

    Args:
        state_output: LangGraph 실행 결과
        llm_judge: LLM Judge 인스턴스
        ontology_schema: 온톨로지 스키마
        query_type: 쿼리 타입 (factual, causal, comparative, deep_analysis)
        expected_property_groups: 예상되는 property group 목록
        use_intent_aware: Intent-aware 평가 사용 여부

    Returns:
        모든 평가 메트릭 결과
    """
    # L1: TBox Consistency
    tbox_evaluator = TBoxConsistencyEvaluator(ontology_schema)
    tbox_result = tbox_evaluator.evaluate(state_output)

    # L2: Intent Preservation
    intent_evaluator = IntentPreservationEvaluator(llm_judge)
    intent_result = intent_evaluator.evaluate(state_output)

    # L2: Relation Coherence
    relation_evaluator = RelationCoherenceEvaluator()
    relation_result = relation_evaluator.evaluate(state_output)

    # L2: Property Group Selection (NEW)
    property_group_result = None
    if expected_property_groups:
        property_group_evaluator = PropertyGroupSelectionEvaluator()
        property_group_result = property_group_evaluator.evaluate(state_output, expected_property_groups)

    # L3: Terminal Triple Validity
    triple_evaluator = TerminalTripleValidityEvaluator(llm_judge)
    triple_result = triple_evaluator.evaluate(state_output)

    # L3: Evidence Diversity
    diversity_evaluator = EvidenceDiversityEvaluator()
    diversity_result = diversity_evaluator.evaluate(state_output)

    # L3: Convergence Utilization
    convergence_evaluator = ConvergenceUtilizationEvaluator()
    convergence_result = convergence_evaluator.evaluate(state_output)

    # Raw metrics
    raw_metrics = {
        "tbox_consistency": tbox_result["score"],
        "intent_preservation": intent_result["score"],
        "relation_coherence": relation_result["score"],
        "triple_validity": triple_result["score"],
        "evidence_diversity": diversity_result["score"],
        "convergence_utilization": convergence_result["score"]
    }
    
    # Property Group Selection 점수 추가 (있는 경우)
    if property_group_result:
        raw_metrics["property_group_selection"] = property_group_result["score"]

    # Intent-aware 평가
    intent_aware_result = None
    if use_intent_aware and query_type:
        intent_aware_evaluator = IntentAwareEvaluator()
        user_selected_direction = state_output.get("user_selected_direction")
        intent_aware_result = intent_aware_evaluator.evaluate(
            query_type,
            raw_metrics,
            user_selected_direction
        )

    return {
        "raw_metrics": raw_metrics,
        "detailed_results": {
            "tbox_consistency": tbox_result,
            "intent_preservation": intent_result,
            "relation_coherence": relation_result,
            "triple_validity": triple_result,
            "evidence_diversity": diversity_result,
            "convergence_utilization": convergence_result
        },
        "intent_aware": intent_aware_result
    }


def main():
    parser = argparse.ArgumentParser(description="Baseline Ablation Study 실행")
    parser.add_argument(
        "--group",
        type=str,
        choices=["semantic_expander", "thread", "entity_boost", "all"],
        default="semantic_expander",
        help="실험 그룹 선택"
    )
    parser.add_argument(
        "--queries",
        type=str,
        default="backend/ragas/ontology_evaluate/data/test_queries.json",
        help="테스트 질문 JSON 파일 경로"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="backend/ragas/ontology_evaluate/data/results",
        help="결과 저장 디렉토리"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="테스트 질문 개수 제한 (디버깅용)"
    )
    parser.add_argument(
        "--intent-aware",
        action="store_true",
        default=True,
        help="Intent-aware 평가 사용 (기본값: True)"
    )
    parser.add_argument(
        "--no-intent-aware",
        dest="intent_aware",
        action="store_false",
        help="Intent-aware 평가 비활성화"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Baseline Ablation Study 실행")
    print("=" * 70)
    print(f"실험 그룹: {args.group}")
    print(f"질문 파일: {args.queries}")
    print(f"결과 저장: {args.output}")
    print(f"Intent-aware 평가: {'활성화' if args.intent_aware else '비활성화'}")
    print("=" * 70)

    # 1. 테스트 질문 로드
    queries_data = load_queries(args.queries)
    if args.limit:
        queries_data = queries_data[:args.limit]
    print(f"테스트 질문 개수: {len(queries_data)}")

    # Query type 분포 출력
    if args.intent_aware:
        query_type_counts = {}
        for q in queries_data:
            qtype = q.get("query_type", "unknown")
            query_type_counts[qtype] = query_type_counts.get(qtype, 0) + 1
        print(f"Query Type 분포: {query_type_counts}")

    # 2. LLM Judge 초기화
    llm_judge = LLMJudge(model="gpt-5-mini")

    # 3. 온톨로지 스키마 로드 (실제 스키마 파일에서 로드 필요)
    # TODO: 실제 온톨로지 스키마 로드 구현
    ontology_schema = {
        "classes": ["Person", "Event", "Place", "Organization"],
        "properties": {
            "participatesIn": {"domain": "Person", "range": "Event"},
            "built": {"domain": "Person", "range": "Place"},
            "causedBy": {"domain": "Event", "range": "Event"},
        }
    }

    # 4. LangGraph 초기화
    print("\n[INFO] LangGraph 초기화 중...")
    try:
        graph = create_graph_flow()
        print("[INFO] LangGraph 초기화 완료!")
    except Exception as e:
        print(f"[ERROR] LangGraph 초기화 실패: {e}")
        print("[INFO] Mock 모드로 전환합니다.")
        graph = None

    def real_graph_invoke(state):
        """실제 LangGraph 실행"""
        # test_config에 skip_clarification 추가 (평가 모드)
        if "test_config" not in state:
            state["test_config"] = {}
        state["test_config"]["skip_clarification"] = True

        if graph is None:
            # Fallback: Mock 모드
            query_type = state.get("query_type", "factual")
            return {
                "query": state["query"],
                "query_intent": "테스트 의도",
                "query_type": query_type,
                "extracted_entities": [],
                "evidences": [],
                "convergence_nodes": [],
                "final_answer": "테스트 답변 (Mock)"
            }

        # 실제 LangGraph 실행
        try:
            result = graph.invoke(state)
            return result
        except Exception as e:
            print(f"[ERROR] LangGraph 실행 실패: {e}")
            # Fallback: Mock 데이터 반환
            query_type = state.get("query_type", "factual")
            return {
                "query": state["query"],
                "query_intent": "에러 발생",
                "query_type": query_type,
                "extracted_entities": [],
                "evidences": [],
                "convergence_nodes": [],
                "final_answer": f"에러 발생: {str(e)}"
            }

    # 5. Ablation Runner 초기화
    runner = AblationRunner(output_dir=args.output)

    # 6. 실험 실행
    if args.group == "all":
        # 모든 실험 그룹 실행
        all_experiments = AblationExperimentGenerator.generate_all_experiments()

        for group_name, configs in all_experiments.items():
            print(f"\n{'='*70}")
            print(f"실험 그룹: {group_name}")
            print(f"{'='*70}")

            # queries를 query 문자열 리스트로 변환
            queries = [q["query"] for q in queries_data]

            results = runner.run_experiment_group(
                queries=queries,
                configs=configs,
                graph_invoke_func=real_graph_invoke,
                group_name=group_name
            )

            # 각 결과에 평가 메트릭 추가
            for idx, result in enumerate(results):
                if result["success"]:
                    state_output = result["state_output"]
                    # 해당 쿼리의 query_type 가져오기
                    query_idx = idx % len(queries_data)
                    query_data = queries_data[query_idx]
                    query_type = query_data.get("query_type", "factual")
                    expected_property_groups = query_data.get("expected_property_groups", [])
                    
                    result["metrics"] = evaluate_state(
                        state_output,
                        llm_judge,
                        ontology_schema,
                        query_type=query_type,
                        expected_property_groups=expected_property_groups,
                        use_intent_aware=args.intent_aware
                    )
    else:
        # 특정 실험 그룹만 실행
        all_experiments = AblationExperimentGenerator.generate_all_experiments()
        configs = all_experiments[args.group]

        # queries를 query 문자열 리스트로 변환
        queries = [q["query"] for q in queries_data]

        results = runner.run_experiment_group(
            queries=queries,
            configs=configs,
            graph_invoke_func=real_graph_invoke,
            group_name=args.group
        )

        # 각 결과에 평가 메트릭 추가
        for idx, result in enumerate(results):
            if result["success"]:
                state_output = result["state_output"]
                # 해당 쿼리의 query_type 가져오기
                query_idx = idx % len(queries_data)
                query_data = queries_data[query_idx]
                query_type = query_data.get("query_type", "factual")
                expected_property_groups = query_data.get("expected_property_groups", [])

                result["metrics"] = evaluate_state(
                    state_output,
                    llm_judge,
                    ontology_schema,
                    query_type=query_type,
                    expected_property_groups=expected_property_groups,
                    use_intent_aware=args.intent_aware
                )

        # 2개 파일 저장: Full + Summary
        _save_experiment_results(results, args.output, args.group, queries_data)

        print(f"\n✅ 평가 완료!")

        # Intent-aware 평가 요약 출력
        if args.intent_aware:
            print("\n" + "=" * 70)
            print("Intent-Aware 평가 요약")
            print("=" * 70)

            # Query type별 평균 점수 계산
            intent_scores = {}
            for result in results:
                if result["success"] and result.get("metrics", {}).get("intent_aware"):
                    ia_result = result["metrics"]["intent_aware"]
                    qtype = ia_result["query_type"]
                    final_score = ia_result["final_score"]

                    if qtype not in intent_scores:
                        intent_scores[qtype] = []
                    intent_scores[qtype].append(final_score)

            # 평균 출력
            for qtype in sorted(intent_scores.keys()):
                scores = intent_scores[qtype]
                avg_score = sum(scores) / len(scores) if scores else 0.0
                print(f"  {qtype:15s}: {avg_score:.3f} (n={len(scores)})")

            print("=" * 70)

    print("\n" + "=" * 70)
    print("실험 완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()