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
from ragas.ontology_evaluate.utils import LLMJudge

# LangGraph import (실제 경로에 맞게 수정 필요)
# from langgraph_fuseki.graph import create_graph


def load_queries(queries_file: str):
    """테스트 질문 로드"""
    with open(queries_file, "r", encoding="utf-8") as f:
        queries_data = json.load(f)

    # query 문자열만 추출
    queries = [q["query"] for q in queries_data]
    return queries


def evaluate_state(state_output: dict, llm_judge: LLMJudge, ontology_schema: dict) -> dict:
    """GraphState에 대해 모든 평가 메트릭 실행

    Args:
        state_output: LangGraph 실행 결과
        llm_judge: LLM Judge 인스턴스
        ontology_schema: 온톨로지 스키마

    Returns:
        모든 평가 메트릭 결과
    """
    metrics = {}

    # L1: TBox Consistency
    tbox_evaluator = TBoxConsistencyEvaluator(ontology_schema)
    metrics["tbox_consistency"] = tbox_evaluator.evaluate(state_output)

    # L2: Intent Preservation
    intent_evaluator = IntentPreservationEvaluator(llm_judge)
    metrics["intent_preservation"] = intent_evaluator.evaluate(state_output)

    # L2: Relation Coherence
    relation_evaluator = RelationCoherenceEvaluator()
    metrics["relation_coherence"] = relation_evaluator.evaluate(state_output)

    # L3: Terminal Triple Validity
    triple_evaluator = TerminalTripleValidityEvaluator(llm_judge)
    metrics["terminal_triple_validity"] = triple_evaluator.evaluate(state_output)

    # L3: Evidence Diversity
    diversity_evaluator = EvidenceDiversityEvaluator()
    metrics["evidence_diversity"] = diversity_evaluator.evaluate(state_output)

    # L3: Convergence Utilization
    convergence_evaluator = ConvergenceUtilizationEvaluator()
    metrics["convergence_utilization"] = convergence_evaluator.evaluate(state_output)

    return metrics


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

    args = parser.parse_args()

    print("=" * 70)
    print("Baseline Ablation Study 실행")
    print("=" * 70)
    print(f"실험 그룹: {args.group}")
    print(f"질문 파일: {args.queries}")
    print(f"결과 저장: {args.output}")
    print("=" * 70)

    # 1. 테스트 질문 로드
    queries = load_queries(args.queries)
    if args.limit:
        queries = queries[:args.limit]
    print(f"테스트 질문 개수: {len(queries)}")

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
        return {
            "query": state["query"],
            "query_intent": "테스트 의도",
            "query_type": "factual",
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

            results = runner.run_experiment_group(
                queries=queries,
                configs=configs,
                graph_invoke_func=mock_graph_invoke,
                group_name=group_name
            )

            # 각 결과에 평가 메트릭 추가
            for result in results:
                if result["success"]:
                    state_output = result["state_output"]
                    result["metrics"] = evaluate_state(state_output, llm_judge, ontology_schema)
    else:
        # 특정 실험 그룹만 실행
        all_experiments = AblationExperimentGenerator.generate_all_experiments()
        configs = all_experiments[args.group]

        results = runner.run_experiment_group(
            queries=queries,
            configs=configs,
            graph_invoke_func=mock_graph_invoke,
            group_name=args.group
        )

        # 각 결과에 평가 메트릭 추가
        for result in results:
            if result["success"]:
                state_output = result["state_output"]
                result["metrics"] = evaluate_state(state_output, llm_judge, ontology_schema)

        # 결과 재저장 (메트릭 포함)
        output_file = Path(args.output) / f"{args.group}_ablation.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 평가 완료: {output_file}")

    print("\n" + "=" * 70)
    print("실험 완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()
