"""
Isolation Baseline Study 실행 (grid_search 패턴 기반)

각 컴포넌트의 단독 기여도를 파악하기 위해 1개씩만 활성화하여 실험합니다.

Usage:
    # 전체 실행
    python -m backend.ragas.ontology_evaluate.experiments.run_isolation --group all --limit 20

    # 특정 그룹만 실행
    python -m backend.ragas.ontology_evaluate.experiments.run_isolation --group semantic_expander --limit 20
    python -m backend.ragas.ontology_evaluate.experiments.run_isolation --group thread --limit 20
    python -m backend.ragas.ontology_evaluate.experiments.run_isolation --group entity_boost --limit 20

    # 중간부터 재시작
    python -m backend.ragas.ontology_evaluate.experiments.run_isolation --group semantic_expander --start-query 10 --limit 20
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 공통 평가 모듈
from backend.ragas.ontology_evaluate.common_eval import get_ontology_schema
from backend.ragas.ontology_evaluate.utils.llm_judge import LLMJudge
from backend.ragas.ontology_evaluate.utils.experiment_utils import (
    initialize_evaluators,
    run_single_config_experiment,
    save_experiment_results
)

# LangGraph import
from backend.langgraph_fuseki.graph import create_graph_flow


# =====================================================
# Isolation 실험 설정 생성기
# =====================================================

class IsolationExperimentGenerator:
    """1개만 활성화하는 Isolation 실험 설정 생성 (grid_search 패턴)"""

    @staticmethod
    def generate_semantic_expander_isolation() -> List[Dict[str, Any]]:
        """Semantic Expander Isolation: 3개 중 1개만 ON"""
        return [
            {
                "name": "iso_semantic_temporal_only",
                "description": "Semantic Expander: temporal만 활성화",
                "semantic_expander": {"temporal": True, "causal_chain": False, "pgvector": False},
                "aggregator_threads": {},
                "entity_boost_mode": None
            },
            {
                "name": "iso_semantic_causal_only",
                "description": "Semantic Expander: causal_chain만 활성화",
                "semantic_expander": {"temporal": False, "causal_chain": True, "pgvector": False},
                "aggregator_threads": {},
                "entity_boost_mode": None
            },
            {
                "name": "iso_semantic_pgvector_only",
                "description": "Semantic Expander: pgvector만 활성화",
                "semantic_expander": {"temporal": False, "causal_chain": False, "pgvector": True},
                "aggregator_threads": {},
                "entity_boost_mode": None
            }
        ]

    @staticmethod
    def generate_thread_isolation() -> List[Dict[str, Any]]:
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
            base_threads = {t: False for t in thread_types}
            base_threads[thread_type] = True

            configs.append({
                "name": f"iso_thread_{thread_type}_only",
                "description": f"Thread: {thread_type}만 활성화",
                "semantic_expander": {},
                "aggregator_threads": base_threads,
                "entity_boost_mode": None
            })

        return configs

    @staticmethod
    def generate_entity_boost_isolation() -> List[Dict[str, Any]]:
        """Entity Boost Isolation: 4개 boost 모드"""
        boost_modes = [
            ("exact", "정확 매칭 부스트"),
            ("partial", "부분 매칭 부스트"),
            ("normalized", "정규화 매칭 부스트"),
            ("none", "부스트 없음")
        ]

        configs = []
        for mode, desc in boost_modes:
            configs.append({
                "name": f"iso_boost_{mode}",
                "description": f"Entity Boost: {desc}",
                "semantic_expander": {},
                "aggregator_threads": {},
                "entity_boost_mode": mode if mode != "none" else None
            })

        return configs

    @classmethod
    def generate_all_isolation_experiments(cls) -> Dict[str, List[Dict[str, Any]]]:
        """모든 Isolation 실험 설정 생성"""
        return {
            "semantic_expander": cls.generate_semantic_expander_isolation(),
            "thread": cls.generate_thread_isolation(),
            "entity_boost": cls.generate_entity_boost_isolation()
        }


# =====================================================
# 실험 실행 함수 (utils 함수 사용)
# =====================================================


def main():
    parser = argparse.ArgumentParser(description="Isolation Baseline Study (grid_search 패턴)")
    parser.add_argument("--group", type=str, required=True,
                        choices=["all", "semantic_expander", "thread", "entity_boost"],
                        help="실험 그룹")
    parser.add_argument("--queries-file", type=str,
                        default="backend/ragas/ontology_evaluate/data/test_queries_20.json",
                        help="테스트 질문 파일")
    parser.add_argument("--output", type=str,
                        default="backend/ragas/ontology_evaluate/data/results_isolation",
                        help="결과 저장 디렉토리")
    parser.add_argument("--start-query", type=int, default=0,
                        help="시작 질문 인덱스 (0부터)")
    parser.add_argument("--limit", type=int, default=None,
                        help="실행할 질문 개수 제한")
    args = parser.parse_args()

    print("=" * 80)
    print("Isolation Baseline Study (grid_search 패턴)")
    print("=" * 80)

    # 질문 로드
    with open(args.queries_file, "r", encoding="utf-8") as f:
        queries_data = json.load(f)

    # start_query와 limit 필터링
    if args.start_query > 0:
        if args.start_query >= len(queries_data):
            print(f"❌ 오류: --start-query {args.start_query}는 질문 개수({len(queries_data)})를 초과합니다.")
            return
        queries_data = queries_data[args.start_query:]
        print(f"\n⚠️  질문 인덱스 {args.start_query}부터 시작합니다.")

    if args.limit:
        queries_data = queries_data[:args.limit]
        print(f"   실행 제한: {args.limit}개")

    print(f"   최종 실행할 질문: {len(queries_data)}개\n")

    # LangGraph 초기화
    print("✓ LangGraph 초기화 중...")
    graph = create_graph_flow()
    print("✓ LangGraph 초기화 완료")

    # 평가자 초기화
    print("✓ 평가자 초기화 중...")
    llm_judge, answer_quality_evaluator, ontology_schema = initialize_evaluators()
    print("✓ 평가자 초기화 완료")

    # 실험 설정 생성
    generator = IsolationExperimentGenerator()
    all_experiments = generator.generate_all_isolation_experiments()

    # 실험 실행
    if args.group == "all":
        # 모든 그룹 실행
        for group_name, configs in all_experiments.items():
            print(f"\n{'='*80}")
            print(f"실험 그룹: {group_name}")
            print(f"{'='*80}")
            print(f"설정 개수: {len(configs)}개")
            print(f"총 실행 횟수: {len(configs)} × {len(queries_data)} = {len(configs) * len(queries_data)}회\n")

            all_results = []
            for config_idx, config in enumerate(configs):
                results = run_single_config_experiment(
                    config=config,
                    queries=queries_data,
                    graph=graph,
                    llm_judge=llm_judge,
                    ontology_schema=ontology_schema,
                    answer_quality_evaluator=answer_quality_evaluator,
                    config_idx=config_idx,
                    total_configs=len(configs),
                    group_name=group_name,
                    state_key="user_query"
                )
                all_results.extend(results)

            # 결과 저장
            save_experiment_results(
                results=all_results,
                output_dir=Path(args.output),
                group_name=group_name,
                experiment_type="isolation"
            )

    else:
        # 특정 그룹만 실행
        configs = all_experiments[args.group]
        print(f"\n{'='*80}")
        print(f"실험 그룹: {args.group}")
        print(f"{'='*80}")
        print(f"설정 개수: {len(configs)}개")
        print(f"총 실행 횟수: {len(configs)} × {len(queries_data)} = {len(configs) * len(queries_data)}회\n")

        all_results = []
        for config_idx, config in enumerate(configs):
            results = run_single_config_experiment(
                config=config,
                queries=queries_data,
                graph=graph,
                llm_judge=llm_judge,
                ontology_schema=ontology_schema,
                answer_quality_evaluator=answer_quality_evaluator,
                config_idx=config_idx,
                total_configs=len(configs),
                group_name=args.group,
                state_key="user_query"
            )
            all_results.extend(results)

        # 결과 저장
        save_experiment_results(
            results=all_results,
            output_dir=Path(args.output),
            group_name=args.group,
            experiment_type="isolation"
        )

    print(f"\n✅ 평가 완료!")
    print(f"종료 시간: {datetime.now()}")


if __name__ == "__main__":
    main()
