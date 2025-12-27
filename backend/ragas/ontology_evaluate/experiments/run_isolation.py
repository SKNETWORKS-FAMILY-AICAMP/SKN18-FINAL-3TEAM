"""
Isolation Baseline Study 실행 (1개만 활성화)

각 컴포넌트의 단독 기여도를 파악하기 위해 1개씩만 활성화하여 실험합니다.

Usage:
    # 전체 실행 (12가지 설정 × 20개 질문 = 240회)
    python -m backend.ragas.ontology_evaluate.experiments.run_isolation --group all --limit 20

    # 특정 그룹만 실행
    python -m backend.ragas.ontology_evaluate.experiments.run_isolation --group semantic_expander --limit 20
    python -m backend.ragas.ontology_evaluate.experiments.run_isolation --group thread --limit 20
    python -m backend.ragas.ontology_evaluate.experiments.run_isolation --group entity_boost --limit 20
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict

from backend.ragas.ontology_evaluate.baseline_ablation import AblationRunner, AblationConfig
from backend.ragas.ontology_evaluate.evaluators import (
    TBoxConsistencyEvaluator,
    IntentPreservationEvaluator,
    RelationCoherenceEvaluator,
    PropertyGroupSelectionEvaluator,
    TerminalTripleValidityEvaluator,
    EvidenceDiversityEvaluator,
    ConvergenceUtilizationEvaluator,
    AnswerQualityEvaluator
)
from backend.ragas.ontology_evaluate.evaluators.intent_aware_evaluator import IntentAwareEvaluator
from backend.ragas.ontology_evaluate.utils.llm_judge import LLMJudge

# LangGraph import
from backend.langgraph_fuseki.graph import create_graph_flow


# =====================================================
# Isolation 실험 설정 생성기
# =====================================================

class IsolationExperimentGenerator:
    """1개만 활성화하는 Isolation 실험 설정 생성"""

    @staticmethod
    def generate_semantic_expander_isolation() -> List[AblationConfig]:
        """Semantic Expander Isolation: 3개 중 1개만 ON"""
        configs = []

        # 1. temporal만 ON
        configs.append(AblationConfig(
            semantic_expander={
                "temporal": True,
                "causal_chain": False,
                "pgvector": False
            },
            experiment_name="iso_semantic_temporal_only",
            description="Semantic Expander: temporal만 활성화"
        ))

        # 2. causal_chain만 ON
        configs.append(AblationConfig(
            semantic_expander={
                "temporal": False,
                "causal_chain": True,
                "pgvector": False
            },
            experiment_name="iso_semantic_causal_only",
            description="Semantic Expander: causal_chain만 활성화"
        ))

        # 3. pgvector만 ON
        configs.append(AblationConfig(
            semantic_expander={
                "temporal": False,
                "causal_chain": False,
                "pgvector": True
            },
            experiment_name="iso_semantic_pgvector_only",
            description="Semantic Expander: pgvector만 활성화"
        ))

        return configs

    @staticmethod
    def generate_thread_isolation() -> List[AblationConfig]:
        """Thread Isolation: 5개 중 1개만 ON"""
        thread_types = [
            "outgoing_relations",
            "incoming_relations",
            "connected_entities",
            "entity_properties",
            "type_and_summary"
        ]

        configs = []

        for thread_type in thread_types:
            # 기본값: 모두 False
            base_threads = {t: False for t in thread_types}
            # 해당 thread만 True
            base_threads[thread_type] = True

            configs.append(AblationConfig(
                aggregator_threads=base_threads,
                experiment_name=f"iso_thread_{thread_type}_only",
                description=f"Thread: {thread_type}만 활성화"
            ))

        return configs

    @staticmethod
    def generate_entity_boost_isolation() -> List[AblationConfig]:
        """Entity Boost Isolation: 4개 boost 모드"""
        boost_modes = [
            ("exact", "정확 매칭 부스트"),
            ("partial", "부분 매칭 부스트"),
            ("normalized", "정규화 매칭 부스트"),
            ("none", "부스트 없음")
        ]

        configs = []

        for mode, desc in boost_modes:
            configs.append(AblationConfig(
                entity_boost_mode=mode,
                experiment_name=f"iso_boost_{mode}",
                description=f"Entity Boost: {desc}"
            ))

        return configs

    @classmethod
    def generate_all_isolation_experiments(cls) -> Dict[str, List[AblationConfig]]:
        """모든 Isolation 실험 설정 생성"""
        return {
            "semantic_expander": cls.generate_semantic_expander_isolation(),
            "thread": cls.generate_thread_isolation(),
            "entity_boost": cls.generate_entity_boost_isolation()
        }


# =====================================================
# 평가 및 저장 함수 (run_baseline.py와 동일)
# =====================================================

def _save_experiment_results(results: list, output_dir: str, group_name: str, queries_data: list):
    """실험 결과를 2개 파일로 저장: Full + Summary"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Full 결과 저장
    full_file = output_path / f"{group_name}_isolation_full.json"
    with open(full_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  → Full 결과: {full_file}")

    # 2. Summary 결과 생성
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

                # LLM Judge 품질 평가
                summary_item["llm_judge_quality"] = metrics.get("llm_judge_quality")
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
    summary_file = output_path / f"{group_name}_isolation_summary.json"
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
    answer_quality_evaluator: AnswerQualityEvaluator,
    query: str = None,
    query_type: str = None,
    expected_property_groups: List[str] = None,
    use_intent_aware: bool = True
) -> dict:
    """GraphState에 대해 모든 평가 메트릭 실행"""
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

    # LLM Judge 답변 품질 평가
    llm_judge_quality = None
    if query and answer_quality_evaluator:
        final_answer = state_output.get("final_answer", "")
        llm_judge_quality = answer_quality_evaluator.evaluate(
            query=query,
            query_type=query_type or "unknown",
            answer=final_answer
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
        "intent_aware": intent_aware_result,
        "llm_judge_quality": llm_judge_quality
    }


# =====================================================
# Main 함수
# =====================================================

def main():
    parser = argparse.ArgumentParser(description="Isolation Baseline Study 실행")
    parser.add_argument(
        "--group",
        type=str,
        choices=["semantic_expander", "thread", "entity_boost", "all"],
        default="all",
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
        default="backend/ragas/ontology_evaluate/data/results_isolation",
        help="결과 저장 디렉토리"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="실행할 질문 개수 제한 (--start-query 이후부터 카운트, 기본값: None=무제한)"
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
    parser.add_argument(
        "--start-query",
        type=int,
        default=0,
        help="시작할 질문 인덱스 (0부터 시작, 기본값: 0)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Isolation Baseline Study 실행")
    print("=" * 70)
    print(f"실험 그룹: {args.group}")
    print(f"질문 파일: {args.queries}")
    print(f"질문 개수 제한: {args.limit}개")
    print(f"결과 저장: {args.output}")
    print(f"Intent-aware 평가: {'활성화' if args.intent_aware else '비활성화'}")
    print("=" * 70)

    # 1. 테스트 질문 로드
    queries_data = load_queries(args.queries)
    print(f"전체 질문 개수: {len(queries_data)}")

    # Query type 분포 출력
    if args.intent_aware:
        query_type_counts = {}
        for q in queries_data:
            qtype = q.get("query_type", "unknown")
            query_type_counts[qtype] = query_type_counts.get(qtype, 0) + 1
        print(f"Query Type 분포: {query_type_counts}")

    # 2. LLM Judge 초기화
    llm_judge = LLMJudge(model="gpt-5-mini")

    # 2-1. Answer Quality Evaluator 초기화
    answer_quality_evaluator = AnswerQualityEvaluator()
    print("LLM Judge Answer Quality Evaluator 초기화 완료")

    # 3. 온톨로지 스키마 로드
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
    all_experiments = IsolationExperimentGenerator.generate_all_isolation_experiments()

    if args.group == "all":
        # 모든 실험 그룹 실행
        total_configs = sum(len(configs) for configs in all_experiments.values())
        print(f"\n전체 실험 설정 개수: {total_configs}개")
        print(f"총 실행 횟수: {total_configs} × {len(queries_data)} = {total_configs * len(queries_data)}회\n")

        if args.start_query > 0 or args.limit:
            print(f"⚠️  --start-query와 --limit 옵션은 단일 그룹 실행 시에만 사용 가능합니다.")
            print(f"   전체 실행(--group all)에서는 무시됩니다.\n")

        for group_name, configs in all_experiments.items():
            print(f"\n{'='*70}")
            print(f"실험 그룹: {group_name} ({len(configs)}개 설정)")
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
                    query = result.get("query", "")
                    query_type = query_data.get("query_type", "factual")
                    expected_property_groups = query_data.get("expected_property_groups", [])

                    result["metrics"] = evaluate_state(
                        state_output,
                        llm_judge,
                        ontology_schema,
                        answer_quality_evaluator,
                        query=query,
                        query_type=query_type,
                        expected_property_groups=expected_property_groups,
                        use_intent_aware=args.intent_aware
                    )

            # 결과 저장
            _save_experiment_results(results, args.output, group_name, queries_data)

    else:
        # 특정 실험 그룹만 실행
        configs = all_experiments[args.group]

        # start_query와 limit 필터링
        if args.start_query > 0:
            if args.start_query >= len(queries_data):
                print(f"❌ 오류: --start-query {args.start_query}는 질문 개수({len(queries_data)})를 초과합니다.")
                return

            queries_data = queries_data[args.start_query:]
            print(f"\n⚠️  질문 인덱스 {args.start_query}부터 시작합니다.")
            print(f"   건너뛴 질문: {args.start_query}개")

        if args.limit:
            queries_data = queries_data[:args.limit]
            print(f"   실행 제한: {args.limit}개")

        print(f"   최종 실행할 질문: {len(queries_data)}개\n")

        print(f"\n실험 설정 개수: {len(configs)}개")
        print(f"총 실행 횟수: {len(configs)} × {len(queries_data)} = {len(configs) * len(queries_data)}회\n")

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
                query = result.get("query", "")
                query_type = query_data.get("query_type", "factual")
                expected_property_groups = query_data.get("expected_property_groups", [])

                result["metrics"] = evaluate_state(
                    state_output,
                    llm_judge,
                    ontology_schema,
                    answer_quality_evaluator,
                    query=query,
                    query_type=query_type,
                    expected_property_groups=expected_property_groups,
                    use_intent_aware=args.intent_aware
                )

        # 결과 저장
        _save_experiment_results(results, args.output, args.group, queries_data)

    print(f"\n✅ 평가 완료!")

    # Intent-aware 평가 요약 출력
    if args.intent_aware:
        print("\n" + "=" * 70)
        print("Intent-Aware 평가 요약")
        print("=" * 70)

        # 전체 결과에서 Query type별 평균 점수 계산
        if args.group == "all":
            for group_name in all_experiments.keys():
                summary_file = Path(args.output) / f"{group_name}_isolation_summary.json"
                if summary_file.exists():
                    with open(summary_file, "r", encoding="utf-8") as f:
                        summary_data = json.load(f)

                    print(f"\n[{group_name}]")
                    intent_scores = {}
                    for item in summary_data:
                        if item.get("success") and item.get("intent_aware_score") is not None:
                            qtype = item["query_type"]
                            score = item["intent_aware_score"]

                            if qtype not in intent_scores:
                                intent_scores[qtype] = []
                            intent_scores[qtype].append(score)

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
