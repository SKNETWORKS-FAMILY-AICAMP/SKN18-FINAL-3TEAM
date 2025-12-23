"""
Baseline Ablation Study 실행

Usage:
    python experiments/run_baseline.py --group semantic_expander --queries data/test_queries.json
"""

import sys
import argparse
import json
from pathlib import Path

# 상위 디렉토리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ragas.ontology_evaluate.baseline_ablation import AblationRunner, AblationExperimentGenerator
from ragas.ontology_evaluate.evaluators import (
    TBoxConsistencyEvaluator,
    IntentPreservationEvaluator,
    RelationCoherenceEvaluator,
    TerminalTripleValidityEvaluator,
    EvidenceDiversityEvaluator,
    ConvergenceUtilizationEvaluator
)
from ragas.ontology_evaluate.evaluators.intent_aware_evaluator import IntentAwareEvaluator
from ragas.ontology_evaluate.utils import LLMJudge

# LangGraph import (실제 경로에 맞게 수정 필요)
# from langgraph_fuseki.graph import create_graph


def load_queries(queries_file: str):
    """테스트 질문 로드"""
    with open(queries_file, "r", encoding="utf-8") as f:
        queries_data = json.load(f)

    # 전체 query 데이터 반환 (query_type 정보 포함)
    return queries_data


def evaluate_state(
    state_output: dict,
    llm_judge: LLMJudge,
    ontology_schema: dict,
    query_type: str = None,
    use_intent_aware: bool = True
) -> dict:
    """GraphState에 대해 모든 평가 메트릭 실행

    Args:
        state_output: LangGraph 실행 결과
        llm_judge: LLM Judge 인스턴스
        ontology_schema: 온톨로지 스키마
        query_type: 쿼리 타입 (factual, causal, comparative, deep_analysis)
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

    # Intent-aware 평가
    intent_aware_result = None
    if use_intent_aware and query_type:
        intent_aware_evaluator = IntentAwareEvaluator()
        intent_aware_result = intent_aware_evaluator.evaluate(query_type, raw_metrics)

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
        default="data/test_queries.json",
        help="테스트 질문 JSON 파일 경로"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/results",
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
    llm_judge = LLMJudge(model="gpt-4o")

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
    # TODO: 실제 LangGraph 초기화 구현
    # graph = create_graph()

    def mock_graph_invoke(state):
        """Mock LangGraph invoke (실제 구현 필요)"""
        # TODO: 실제 graph.invoke() 호출 구현
        # query_type을 state에서 가져오거나 기본값 사용
        query_type = state.get("query_type", "factual")
        return {
            "query": state["query"],
            "query_intent": "테스트 의도",
            "query_type": query_type,
            "extracted_entities": [],
            "evidences": [],
            "convergence_nodes": [],
            "final_answer": "테스트 답변"
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
                graph_invoke_func=mock_graph_invoke,
                group_name=group_name
            )

            # 각 결과에 평가 메트릭 추가
            for idx, result in enumerate(results):
                if result["success"]:
                    state_output = result["state_output"]
                    # 해당 쿼리의 query_type 가져오기
                    query_idx = idx % len(queries_data)
                    query_type = queries_data[query_idx].get("query_type", "factual")
                    result["metrics"] = evaluate_state(
                        state_output,
                        llm_judge,
                        ontology_schema,
                        query_type=query_type,
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
            graph_invoke_func=mock_graph_invoke,
            group_name=args.group
        )

        # 각 결과에 평가 메트릭 추가
        for idx, result in enumerate(results):
            if result["success"]:
                state_output = result["state_output"]
                # 해당 쿼리의 query_type 가져오기
                query_idx = idx % len(queries_data)
                query_type = queries_data[query_idx].get("query_type", "factual")
                result["metrics"] = evaluate_state(
                    state_output,
                    llm_judge,
                    ontology_schema,
                    query_type=query_type,
                    use_intent_aware=args.intent_aware
                )

        # 결과 재저장 (메트릭 포함)
        output_file = Path(args.output) / f"{args.group}_ablation.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 평가 완료: {output_file}")

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
