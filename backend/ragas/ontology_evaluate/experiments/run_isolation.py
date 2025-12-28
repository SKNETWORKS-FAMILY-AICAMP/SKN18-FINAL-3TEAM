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
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 공통 평가 모듈
from backend.ragas.ontology_evaluate.common_eval import evaluate_state, build_test_config, get_ontology_schema
from backend.ragas.ontology_evaluate.evaluators import AnswerQualityEvaluator
from backend.ragas.ontology_evaluate.utils.llm_judge import LLMJudge

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
# 실험 실행 함수 (grid_search 패턴)
# =====================================================

def run_single_config(
    config: Dict[str, Any],
    queries: List[Dict],
    graph,
    llm_judge: LLMJudge,
    ontology_schema: dict,
    answer_quality_evaluator: AnswerQualityEvaluator,
    group_name: str,
    config_idx: int,
    total_configs: int
) -> List[Dict[str, Any]]:
    """
    단일 설정으로 모든 질문 실행 및 평가
    grid_search_worker 패턴 사용
    """
    config_name = config.get("name", f"config_{config_idx}")
    config_description = config.get("description", "")
    test_config = build_test_config(config)

    print(f"\n{'='*70}")
    print(f"[{group_name}] 설정 {config_idx+1}/{total_configs}: {config_name}")
    print(f"{'='*70}")

    # 설정 정보 출력
    se_config = config.get('semantic_expander', {})
    if se_config:
        print(f"  SE: {se_config}")

    threads = config.get('aggregator_threads', {})
    if threads:
        active_threads = [k for k, v in threads.items() if v]
        print(f"  Thread: {active_threads}")

    boost_mode = config.get('entity_boost_mode')
    if boost_mode:
        print(f"  Boost: {boost_mode}")

    flat_results = []
    config_start = time.time()

    for q_idx, query_data in enumerate(queries):
        query = query_data.get("query", "")
        query_type = query_data.get("query_type", "factual")
        expected_property_groups = query_data.get("expected_property_groups", [])

        print(f"\n  [{q_idx+1}/{len(queries)}] {query[:50]}...")
        q_start = time.time()

        try:
            # LangGraph 실행
            state = {
                "user_query": query,
                "test_config": test_config
            }
            state_output = graph.invoke(state)

            # 평가
            print(f"    → 평가 중...")
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

            final_score = metrics["intent_aware"]["final_score"] if metrics["intent_aware"] else 0.0
            llm_judge_quality = metrics["llm_judge_quality"]

            q_elapsed = time.time() - q_start

            # 결과 저장
            result = {
                "experiment_name": config_name,
                "description": config_description,
                "query": query,
                "query_type": query_type,
                "config": {
                    "semantic_expander": config.get("semantic_expander", {}),
                    "aggregator_threads": config.get("aggregator_threads", {}),
                    "entity_boost_mode": config.get("entity_boost_mode")
                },
                "state_output": state_output,
                "execution_time": q_elapsed,
                "success": True,
                "error": None,
                "metrics": {
                    "raw_metrics": metrics["raw_metrics"],
                    "intent_aware": metrics["intent_aware"],
                    "final_score": final_score
                },
                "llm_judge_quality": llm_judge_quality
            }

            judge_score = llm_judge_quality.get('overall_score', 0) if llm_judge_quality else 0
            print(f"    ✓ Score: {final_score:.4f} | LLM Judge: {judge_score:.4f} ({q_elapsed:.1f}s)")

        except Exception as e:
            q_elapsed = time.time() - q_start
            result = {
                "experiment_name": config_name,
                "description": config_description,
                "query": query,
                "query_type": query_type,
                "config": {
                    "semantic_expander": config.get("semantic_expander", {}),
                    "aggregator_threads": config.get("aggregator_threads", {}),
                    "entity_boost_mode": config.get("entity_boost_mode")
                },
                "state_output": {},
                "execution_time": q_elapsed,
                "success": False,
                "error": str(e),
                "metrics": None
            }
            print(f"    ✗ Error: {str(e)[:100]}")

        flat_results.append(result)

    config_elapsed = time.time() - config_start

    # 통계 출력
    success_count = sum(1 for r in flat_results if r["success"])
    if success_count > 0:
        scores = [r["metrics"]["final_score"] for r in flat_results if r["success"] and r["metrics"]]
        mean_score = sum(scores) / len(scores) if scores else 0.0
        print(f"\n  Summary: mean={mean_score:.4f}, success={success_count}/{len(queries)}, time={config_elapsed:.1f}s")

    return flat_results


def save_experiment_results(results: list, output_dir: str, group_name: str):
    """실험 결과를 2개 파일로 저장: Full + Summary (grid_search 패턴)"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Full 결과 저장
    full_file = output_path / f"{group_name}_isolation_full.json"
    with open(full_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Full 결과: {full_file}")

    # 2. Summary 결과 생성
    summary_results = []
    for result in results:
        if result["success"] and result["metrics"]:
            state = result.get("state_output", {})
            metrics = result["metrics"]
            ia = metrics.get("intent_aware", {})

            summary_item = {
                "experiment_name": result.get("experiment_name", ""),
                "query": result.get("query", ""),
                "query_type": result.get("query_type", ""),
                "final_answer": state.get("final_answer", ""),
                "num_extracted_entities": len(state.get("extracted_entities", [])),
                "num_expanded_entities": len(state.get("expanded_entities", [])),
                "num_evidences": len(state.get("evidences", [])),
                "num_convergence_nodes": len(state.get("convergence_triple_tree", {}).get("nodes", [])),
                "raw_metrics": metrics.get("raw_metrics", {}),
                "intent_aware_score": ia.get("final_score", 0.0),
                "weighted_metrics": ia.get("weighted_metrics", {}),
                "llm_judge_quality": result.get("llm_judge_quality")
            }
        else:
            summary_item = {
                "experiment_name": result.get("experiment_name", ""),
                "query": result.get("query", ""),
                "query_type": result.get("query_type", ""),
                "success": False,
                "error": result.get("error")
            }
        summary_results.append(summary_item)

    summary_file = output_path / f"{group_name}_isolation_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, ensure_ascii=False, indent=2)
    print(f"✓ Summary: {summary_file}")


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

    # LLM Judge 초기화
    print("✓ LLM Judge 초기화 중...")
    llm_judge = LLMJudge()
    print("✓ LLM Judge 초기화 완료")

    # Answer Quality Evaluator 초기화
    print("✓ Answer Quality Evaluator 초기화 중...")
    answer_quality_evaluator = AnswerQualityEvaluator()
    print("✓ Answer Quality Evaluator 초기화 완료")

    # 온톨로지 스키마
    ontology_schema = get_ontology_schema()

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
                results = run_single_config(
                    config,
                    queries_data,
                    graph,
                    llm_judge,
                    ontology_schema,
                    answer_quality_evaluator,
                    group_name,
                    config_idx,
                    len(configs)
                )
                all_results.extend(results)

            # 결과 저장
            save_experiment_results(all_results, args.output, group_name)

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
            results = run_single_config(
                config,
                queries_data,
                graph,
                llm_judge,
                ontology_schema,
                answer_quality_evaluator,
                args.group,
                config_idx,
                len(configs)
            )
            all_results.extend(results)

        # 결과 저장
        save_experiment_results(all_results, args.output, args.group)

    print(f"\n✅ 평가 완료!")
    print(f"종료 시간: {datetime.now()}")


if __name__ == "__main__":
    main()
