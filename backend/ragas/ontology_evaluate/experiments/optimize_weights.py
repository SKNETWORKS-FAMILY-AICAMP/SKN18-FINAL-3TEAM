"""
Query Type별 가중치 최적화 실험

Usage:
    # 전체 데이터셋으로 최적화
    python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
        --component semantic_expander --method grid_search --limit 50

    # Factual 질문만 사용하여 최적화
    python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
        --component semantic_expander --query_type factual --method grid_search --limit 50
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from itertools import product
import time

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


def load_queries(queries_file: str, query_type: Optional[str] = None, limit: Optional[int] = None):
    """테스트 질문 로드 (query_type 필터링 지원)

    Args:
        queries_file: 질문 JSON 파일 경로
        query_type: 필터링할 query_type (None이면 전체)
        limit: 최대 질문 개수

    Returns:
        질문 데이터 리스트
    """
    queries_path = Path(queries_file)

    with open(queries_path, "r", encoding="utf-8") as f:
        queries_data = json.load(f)

    # query_type 필터링
    if query_type:
        queries_data = [q for q in queries_data if q.get("query_type") == query_type]
        print(f"[INFO] query_type='{query_type}' 필터링: {len(queries_data)}개 질문")

    # limit 적용
    if limit:
        queries_data = queries_data[:limit]

    return queries_data


def evaluate_state(
    state_output: dict,
    llm_judge: LLMJudge,
    ontology_schema: dict,
    query_type: str = None,
    expected_property_groups: List[str] = None
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

    # L2: Property Group Selection
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

    if property_group_result:
        raw_metrics["property_group_selection"] = property_group_result["score"]

    # Intent-aware 평가
    intent_aware_result = None
    if query_type:
        intent_aware_evaluator = IntentAwareEvaluator()
        user_selected_direction = state_output.get("user_selected_direction")
        intent_aware_result = intent_aware_evaluator.evaluate(
            query_type,
            raw_metrics,
            user_selected_direction
        )

    return {
        "raw_metrics": raw_metrics,
        "intent_aware": intent_aware_result,
        "detailed_results": {
            "tbox_consistency": tbox_result,
            "intent_preservation": intent_result,
            "relation_coherence": relation_result,
            "triple_validity": triple_result,
            "evidence_diversity": diversity_result,
            "convergence_utilization": convergence_result
        }
    }


class WeightOptimizer:
    """가중치 최적화 실행기"""

    def __init__(self, component: str, method: str = "grid_search"):
        """
        Args:
            component: 최적화할 컴포넌트 (semantic_expander, entity_extractor 등)
            method: 최적화 방법 (grid_search, bayesian)
        """
        self.component = component
        self.method = method

    def generate_weight_grid(self, component: str) -> List[Dict[str, float]]:
        """가중치 그리드 생성

        Args:
            component: 컴포넌트 이름

        Returns:
            가중치 조합 리스트
        """
        if component == "semantic_expander":
            # Temporal, Causal, Vector 가중치 (합=1.0 제약)
            weight_options = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

            grid = []
            for temporal in weight_options:
                for causal in weight_options:
                    vector = round(1.0 - temporal - causal, 1)
                    if 0.0 <= vector <= 1.0:  # 유효한 조합만
                        grid.append({
                            "temporal_weight": temporal,
                            "causal_weight": causal,
                            "vector_weight": vector
                        })

            print(f"[INFO] Semantic Expander Grid: {len(grid)}개 조합")
            return grid

        elif component == "thread":
            # Thread 가중치 (5개 thread 타입)
            # 간단한 Grid: [0.5, 1.0, 1.5, 2.0] 4개 옵션
            weight_options = [0.5, 1.0, 1.5, 2.0]

            grid = []
            from itertools import product

            # 5개 thread의 모든 조합: 4^5 = 1024개
            for combo in product(weight_options, repeat=5):
                grid.append({
                    "outgoing_relations": combo[0],
                    "incoming_relations": combo[1],
                    "entity_properties": combo[2],
                    "connected_entities": combo[3],
                    "type_and_summary": combo[4]
                })

            print(f"[INFO] Thread Grid: {len(grid)}개 조합 (4^5)")
            print(f"[WARN] Thread 최적화는 실행 시간이 매우 깁니다 (1024 trials)")
            return grid

        elif component == "entity_boost":
            # Entity Boost 배율 (exact_match, partial_match)
            exact_options = [1.0, 1.5, 2.0, 2.5, 3.0]
            partial_options = [1.0, 1.2, 1.5, 1.8, 2.0]

            grid = []
            for exact in exact_options:
                for partial in partial_options:
                    grid.append({
                        "exact_match": exact,
                        "partial_match": partial
                    })

            print(f"[INFO] Entity Boost Grid: {len(grid)}개 조합 (5×5)")
            return grid

        elif component == "entity_extractor":
            # Similarity threshold 최적화
            thresholds = [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]
            grid = [{"similarity_threshold": t} for t in thresholds]
            print(f"[INFO] Entity Extractor Grid: {len(grid)}개 조합")
            return grid

        else:
            raise ValueError(f"Unknown component: {component}")

    def run_optimization(
        self,
        queries_data: List[Dict],
        graph_invoke_func,
        output_dir: str,
        query_type_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """가중치 최적화 실행

        Args:
            queries_data: 질문 데이터 리스트
            graph_invoke_func: LangGraph invoke 함수
            output_dir: 결과 저장 디렉토리
            query_type_filter: query_type 필터 (None이면 전체)

        Returns:
            최적화 결과 (best_weights, best_score 등)
        """
        weight_grid = self.generate_weight_grid(self.component)

        print("\n" + "=" * 70)
        print(f"가중치 최적화: {self.component}")
        if query_type_filter:
            print(f"Query Type: {query_type_filter}")
        print(f"총 {len(weight_grid)}개 가중치 조합 × {len(queries_data)}개 질문")
        print(f"예상 실행 횟수: {len(weight_grid) * len(queries_data)}")
        print("=" * 70)

        # LLM Judge & Schema
        llm_judge = LLMJudge(model="gpt-5-mini")
        ontology_schema = {
            "classes": ["Person", "Event", "Place", "Organization"],
            "properties": {
                "participatesIn": {"domain": "Person", "range": "Event"},
                "built": {"domain": "Person", "range": "Place"},
                "causedBy": {"domain": "Event", "range": "Event"},
            }
        }

        best_weights = None
        best_score = -1.0
        best_trial_id = -1
        all_trials = []

        start_time = time.time()

        for trial_id, weights in enumerate(weight_grid, 1):
            print(f"\n[Trial {trial_id}/{len(weight_grid)}] Weights: {weights}")

            trial_scores = []
            trial_details = []

            for query_data in queries_data:
                query = query_data["query"]
                qtype = query_data.get("query_type", "factual")
                expected_property_groups = query_data.get("expected_property_groups", [])

                # State 초기화 (가중치 주입)
                state = {
                    "query": query,
                    "query_type": qtype,
                    "test_config": {
                        "skip_clarification": True,
                        "weights": weights  # 가중치 주입
                    }
                }

                try:
                    # LangGraph 실행
                    result_state = graph_invoke_func(state)

                    # 평가
                    metrics = evaluate_state(
                        result_state,
                        llm_judge,
                        ontology_schema,
                        query_type=qtype,
                        expected_property_groups=expected_property_groups
                    )

                    # Intent-aware final score 사용
                    if metrics.get("intent_aware"):
                        final_score = metrics["intent_aware"]["final_score"]
                    else:
                        # Fallback: raw metrics 평균
                        raw_scores = list(metrics["raw_metrics"].values())
                        final_score = sum(raw_scores) / len(raw_scores) if raw_scores else 0.0

                    trial_scores.append(final_score)
                    trial_details.append({
                        "query": query,
                        "query_type": qtype,
                        "final_score": final_score,
                        "raw_metrics": metrics["raw_metrics"]
                    })

                except Exception as e:
                    print(f"[ERROR] Query 실행 실패: {query[:30]}... - {e}")
                    trial_scores.append(0.0)
                    trial_details.append({
                        "query": query,
                        "query_type": qtype,
                        "error": str(e),
                        "final_score": 0.0
                    })

            # Trial 평균 점수
            avg_score = sum(trial_scores) / len(trial_scores) if trial_scores else 0.0

            trial_result = {
                "trial_id": trial_id,
                "weights": weights,
                "avg_score": avg_score,
                "num_queries": len(queries_data),
                "query_type_filter": query_type_filter,
                "details": trial_details
            }

            all_trials.append(trial_result)

            print(f"  → Avg Score: {avg_score:.4f}")

            # 최고 점수 업데이트
            if avg_score > best_score:
                best_score = avg_score
                best_weights = weights
                best_trial_id = trial_id
                print(f"  ✨ NEW BEST! (Trial {trial_id})")

        elapsed_time = time.time() - start_time

        # 결과 정리
        optimization_result = {
            "component": self.component,
            "method": self.method,
            "query_type_filter": query_type_filter,
            "num_queries": len(queries_data),
            "num_trials": len(weight_grid),
            "best_trial_id": best_trial_id,
            "best_weights": best_weights,
            "best_score": best_score,
            "elapsed_time": elapsed_time,
            "all_trials": all_trials
        }

        # 2개 파일 저장: Full + Summary
        self._save_results(optimization_result, output_dir, query_type_filter)

        return optimization_result

    def _save_results(self, result: Dict, output_dir: str, query_type_filter: Optional[str]):
        """결과를 2개 파일로 저장: Full + Summary"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 파일명 생성
        if query_type_filter:
            filename_base = f"{self.component}_weights_{query_type_filter}"
        else:
            filename_base = f"{self.component}_weights_all"

        # 1. Full 결과 (모든 trial 상세 데이터)
        full_file = output_path / f"{filename_base}_full.json"
        with open(full_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Full 결과 저장: {full_file}")

        # 2. Summary 결과 (점수, 수치만)
        summary = self._create_summary(result)
        summary_file = output_path / f"{filename_base}_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"✅ Summary 저장: {summary_file}")

    def _create_summary(self, result: Dict) -> Dict:
        """Summary 데이터 생성 (수치만)"""
        # Trial별 점수 요약
        trial_summaries = []
        for trial in result["all_trials"]:
            trial_summaries.append({
                "trial_id": trial["trial_id"],
                "weights": trial["weights"],
                "avg_score": trial["avg_score"],
                "num_queries": trial["num_queries"]
            })

        # Top 5 trials
        sorted_trials = sorted(trial_summaries, key=lambda x: x["avg_score"], reverse=True)
        top5_trials = sorted_trials[:5]

        summary = {
            "component": result["component"],
            "method": result["method"],
            "query_type_filter": result["query_type_filter"],
            "total_trials": result["num_trials"],
            "total_queries": result["num_queries"],
            "elapsed_time_seconds": round(result["elapsed_time"], 2),
            "best_result": {
                "trial_id": result["best_trial_id"],
                "weights": result["best_weights"],
                "score": result["best_score"]
            },
            "top5_trials": top5_trials,
            "score_distribution": {
                "min": min(t["avg_score"] for t in trial_summaries),
                "max": max(t["avg_score"] for t in trial_summaries),
                "mean": sum(t["avg_score"] for t in trial_summaries) / len(trial_summaries),
                "median": sorted([t["avg_score"] for t in trial_summaries])[len(trial_summaries) // 2]
            }
        }

        return summary


def main():
    parser = argparse.ArgumentParser(description="Query Type별 가중치 최적화")
    parser.add_argument(
        "--component",
        type=str,
        choices=["semantic_expander", "thread", "entity_boost", "entity_extractor"],
        required=True,
        help="최적화할 컴포넌트"
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["grid_search", "bayesian"],
        default="grid_search",
        help="최적화 방법"
    )
    parser.add_argument(
        "--query_type",
        type=str,
        choices=["factual", "causal", "comparative", "deep_analysis"],
        default=None,
        help="특정 query_type만 사용 (None이면 전체)"
    )
    parser.add_argument(
        "--queries",
        type=str,
        default="backend/ragas/ontology_evaluate/data/test_queries.json",
        help="테스트 질문 JSON 파일"
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
        help="테스트 질문 개수 제한"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("가중치 최적화 실험")
    print("=" * 70)
    print(f"컴포넌트: {args.component}")
    print(f"최적화 방법: {args.method}")
    print(f"Query Type 필터: {args.query_type or '전체'}")
    print(f"질문 파일: {args.queries}")
    print("=" * 70)

    # 1. 질문 로드 (query_type 필터링)
    queries_data = load_queries(args.queries, query_type=args.query_type, limit=args.limit)
    print(f"테스트 질문 개수: {len(queries_data)}")

    # 2. LangGraph 초기화
    print("\n[INFO] LangGraph 초기화 중...")
    try:
        graph = create_graph_flow()
        print("[INFO] LangGraph 초기화 완료!")
    except Exception as e:
        print(f"[ERROR] LangGraph 초기화 실패: {e}")
        graph = None

    def graph_invoke_func(state):
        """LangGraph 실행"""
        if graph is None:
            # Mock fallback
            return {
                "query": state["query"],
                "query_type": state.get("query_type", "factual"),
                "extracted_entities": [],
                "evidences": [],
                "final_answer": "Mock answer"
            }

        try:
            return graph.invoke(state)
        except Exception as e:
            print(f"[ERROR] Graph invoke 실패: {e}")
            return {
                "query": state["query"],
                "query_type": state.get("query_type", "factual"),
                "extracted_entities": [],
                "evidences": [],
                "final_answer": f"Error: {e}"
            }

    # 3. 가중치 최적화 실행
    optimizer = WeightOptimizer(component=args.component, method=args.method)
    result = optimizer.run_optimization(
        queries_data=queries_data,
        graph_invoke_func=graph_invoke_func,
        output_dir=args.output,
        query_type_filter=args.query_type
    )

    # 4. 결과 출력
    print("\n" + "=" * 70)
    print("최적화 완료!")
    print("=" * 70)
    print(f"Best Weights: {result['best_weights']}")
    print(f"Best Score: {result['best_score']:.4f}")
    print(f"Best Trial ID: {result['best_trial_id']}")
    print(f"실행 시간: {result['elapsed_time']:.1f}초")
    print("=" * 70)


if __name__ == "__main__":
    main()
