"""
Grid Search: 가중치 최적화 실험

Phase 1 (Baseline Ablation) 결과를 바탕으로 가중치 최적화

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.run_grid_search --baseline-results backend/ragas/ontology_evaluate/data/results/semantic_expander_ablation.json
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any
from itertools import product


class GridSearchConfig:
    """Grid Search 설정"""

    # Semantic Expander 가중치 범위 (FIXED_SCORE_*)
    SEMANTIC_WEIGHTS = {
        "temporal": [0.5, 1.0, 1.5, 2.0],
        "category": [0.5, 1.0, 1.5, 2.0],
        "causal_chain": [0.5, 1.0, 1.5, 2.0],
        "pgvector": [0.5, 1.0, 1.5, 2.0]
    }

    # Thread 가중치 범위 (THREAD_WEIGHT_*)
    THREAD_WEIGHTS = {
        "outgoing_relations": [0.5, 1.0, 1.5, 2.0],
        "incoming_relations": [0.5, 1.0, 1.5, 2.0],
        "entity_properties": [0.5, 1.0, 1.5, 2.0],
        "connected_entities": [0.5, 1.0, 1.5, 2.0],
        "type_and_summary": [0.5, 1.0, 1.5, 2.0]
    }

    # Entity Boost 배율 범위
    ENTITY_BOOST_MULTIPLIERS = {
        "exact_match": [1.0, 1.5, 2.0, 2.5],
        "partial_match": [1.0, 1.2, 1.5, 1.8]
    }


class GridSearchRunner:
    """Grid Search 실행기"""

    def __init__(self, baseline_results_file: str):
        """
        Args:
            baseline_results_file: Phase 1 결과 파일
        """
        self.baseline_results = self._load_baseline(baseline_results_file)

    def _load_baseline(self, results_file: str) -> List[Dict[str, Any]]:
        """Baseline 결과 로드"""
        with open(results_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_semantic_weight_grid(self) -> List[Dict[str, float]]:
        """Semantic Expander 가중치 그리드 생성

        Returns:
            가중치 조합 리스트 (예: 4^4 = 256개)
        """
        # 모든 조합 생성
        keys = list(GridSearchConfig.SEMANTIC_WEIGHTS.keys())
        values = [GridSearchConfig.SEMANTIC_WEIGHTS[k] for k in keys]

        weight_combinations = []
        for combo in product(*values):
            weight_dict = dict(zip(keys, combo))
            weight_combinations.append(weight_dict)

        return weight_combinations

    def generate_thread_weight_grid(self) -> List[Dict[str, float]]:
        """Thread 가중치 그리드 생성

        Returns:
            가중치 조합 리스트 (예: 4^5 = 1024개)
        """
        keys = list(GridSearchConfig.THREAD_WEIGHTS.keys())
        values = [GridSearchConfig.THREAD_WEIGHTS[k] for k in keys]

        weight_combinations = []
        for combo in product(*values):
            weight_dict = dict(zip(keys, combo))
            weight_combinations.append(weight_dict)

        return weight_combinations

    def run_semantic_weight_search(
        self,
        queries: List[str],
        graph_invoke_func,
        output_dir: str
    ):
        """Semantic Expander 가중치 Grid Search

        Args:
            queries: 테스트 질문 리스트
            graph_invoke_func: LangGraph invoke 함수
            output_dir: 결과 저장 디렉토리
        """
        weight_grid = self.generate_semantic_weight_grid()

        print(f"Semantic Expander Grid Search")
        print(f"총 {len(weight_grid)}개 가중치 조합 테스트")

        results = []

        for i, weights in enumerate(weight_grid, 1):
            print(f"\n진행률: [{i}/{len(weight_grid)}]")
            print(f"가중치: {weights}")

            # TODO: 각 가중치 조합에 대해 LangGraph 실행 및 평가
            # 이 부분은 실제 LangGraph state에 가중치를 주입하는 방식으로 구현 필요

            result = {
                "weights": weights,
                "metrics": {},  # 평가 메트릭
                "queries": queries
            }

            results.append(result)

        # 결과 저장
        output_file = Path(output_dir) / "semantic_weight_grid_search.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Grid Search 완료: {output_file}")

    def run_thread_weight_search(
        self,
        queries: List[str],
        graph_invoke_func,
        output_dir: str
    ):
        """Thread 가중치 Grid Search

        Args:
            queries: 테스트 질문 리스트
            graph_invoke_func: LangGraph invoke 함수
            output_dir: 결과 저장 디렉토리
        """
        weight_grid = self.generate_thread_weight_grid()

        print(f"Thread Grid Search")
        print(f"총 {len(weight_grid)}개 가중치 조합 테스트")

        results = []

        for i, weights in enumerate(weight_grid, 1):
            print(f"\n진행률: [{i}/{len(weight_grid)}]")
            print(f"가중치: {weights}")

            # TODO: 각 가중치 조합에 대해 LangGraph 실행 및 평가

            result = {
                "weights": weights,
                "metrics": {},  # 평가 메트릭
                "queries": queries
            }

            results.append(result)

        # 결과 저장
        output_file = Path(output_dir) / "thread_weight_grid_search.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Grid Search 완료: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Grid Search 가중치 최적화")
    parser.add_argument(
        "--baseline-results",
        type=str,
        required=True,
        help="Phase 1 결과 파일 경로"
    )
    parser.add_argument(
        "--search-type",
        type=str,
        choices=["semantic", "thread", "all"],
        default="semantic",
        help="Grid Search 타입"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/results",
        help="결과 저장 디렉토리"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Grid Search 가중치 최적화")
    print("=" * 70)
    print(f"Baseline 결과: {args.baseline_results}")
    print(f"Search 타입: {args.search_type}")
    print("=" * 70)

    # Grid Search Runner 초기화
    runner = GridSearchRunner(args.baseline_results)

    # TODO: 실제 LangGraph 및 질문 로드
    queries = ["테스트 질문 1", "테스트 질문 2"]

    def mock_graph_invoke(state):
        return state

    # Grid Search 실행
    if args.search_type == "semantic" or args.search_type == "all":
        runner.run_semantic_weight_search(queries, mock_graph_invoke, args.output)

    if args.search_type == "thread" or args.search_type == "all":
        runner.run_thread_weight_search(queries, mock_graph_invoke, args.output)

    print("\n" + "=" * 70)
    print("Grid Search 완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()
