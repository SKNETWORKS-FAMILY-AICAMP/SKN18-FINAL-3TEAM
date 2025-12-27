"""
Grid Search Worker 스크립트

개별 배치의 설정들을 순차적으로 처리하여 평가 결과 생성

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.grid_search.grid_search_worker \
        --config-file data/grid_search_results/batch_1_configs.json \
        --queries-file data/grid_search_results/grid_search_queries.json \
        --output data/grid_search_results/batch_1_results.json \
        --batch-num 1
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# LangGraph import
from backend.langgraph_fuseki.graph import create_graph_flow

# 평가자 import
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

    # Property Group Selection 점수 추가
    if property_group_result:
        raw_metrics["property_group_selection"] = property_group_result["score"]
    else:
        raw_metrics["property_group_selection"] = 0.5  # 기본값

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
        "intent_aware": intent_aware_result
    }


def build_test_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grid Search 설정을 LangGraph test_config 형식으로 변환

    형식:
        - semantic_expander: {temporal: bool, causal_chain: bool, pgvector: bool}
        - aggregator_threads: {thread_name: bool}
        - entity_boost_mode: "normalized" | "exact" | None
    """
    return {
        "skip_clarification": True,
        "semantic_expander": config.get("semantic_expander", {}),
        "aggregator_threads": config.get("aggregator_threads", {}),
        "entity_boost_mode": config.get("entity_boost_mode"),
    }


def run_single_config(
    config: Dict[str, Any],
    queries: List[Dict],
    graph,
    llm_judge: LLMJudge,
    ontology_schema: dict,
    answer_quality_evaluator: AnswerQualityEvaluator,
    batch_num: int,
    config_idx: int,
    total_configs: int
) -> List[Dict[str, Any]]:
    """
    단일 설정으로 모든 질문 실행 및 평가
    Ablation 형식으로 flat list 반환
    """
    config_name = config.get("name", f"config_{config_idx}")
    config_description = config.get("description", "")
    test_config = build_test_config(config)

    print(f"\n{'='*70}")
    print(f"[Batch {batch_num}] 설정 {config_idx+1}/{total_configs}: {config_name}")
    print(f"{'='*70}")

    # 설정 정보 출력
    se_config = config.get('semantic_expander', {})
    print(f"  SE: temporal={se_config.get('temporal')}, "
          f"causal={se_config.get('causal_chain')}, "
          f"pgvector={se_config.get('pgvector')}")

    threads = config.get('aggregator_threads', {})
    print(f"  Thread: entity_prop={threads.get('entity_properties')}, "
          f"type_summary={threads.get('type_and_summary')}, "
          f"outgoing={threads.get('outgoing_relations')}, "
          f"incoming={threads.get('incoming_relations')}, "
          f"connected={threads.get('connected_entities')}")
    print(f"  Boost: {config.get('entity_boost_mode')}")
    
    flat_results = []  # Ablation 형식: flat list
    config_start = time.time()

    for q_idx, query_data in enumerate(queries):
        query = query_data["query"]
        query_type = query_data.get("query_type", "deep_analysis")
        expected_property_groups = query_data.get("expected_property_groups", [])

        print(f"\n  [{q_idx+1}/{len(queries)}] {query[:40]}...")

        q_start = time.time()

        try:
            # LangGraph 실행
            state = {
                "query": query,
                "test_config": test_config
            }
            state_output = graph.invoke(state)

            # 평가
            metrics = evaluate_state(
                state_output,
                llm_judge,
                ontology_schema,
                query_type=query_type,
                expected_property_groups=expected_property_groups
            )

            final_answer = state_output.get("final_answer", "")
            final_score = metrics["intent_aware"]["final_score"] if metrics["intent_aware"] else 0.0

            # LLM Judge 품질 평가
            print(f"    → LLM Judge 평가 중...")
            llm_judge_quality = answer_quality_evaluator.evaluate(query, query_type, final_answer)

            q_elapsed = time.time() - q_start

            # Ablation 형식으로 저장 (full.json용)
            result = {
                "experiment_name": config_name,
                "description": config_description,
                "query": query,
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

            print(f"    ✓ Score: {final_score:.4f} | LLM Judge: {llm_judge_quality.get('overall_score', 0):.4f} ({q_elapsed:.1f}s)")

        except Exception as e:
            q_elapsed = time.time() - q_start
            result = {
                "experiment_name": config_name,
                "description": config_description,
                "query": query,
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
            print(f"    ✗ Error: {str(e)[:50]}")

        flat_results.append(result)

    config_elapsed = time.time() - config_start

    # 통계 출력
    success_count = sum(1 for r in flat_results if "metrics" in r)
    if success_count > 0:
        scores = [r["metrics"]["final_score"] for r in flat_results if "metrics" in r]
        mean_score = sum(scores) / len(scores) if scores else 0.0
        print(f"\n  Summary: mean={mean_score:.4f}, success={success_count}/{len(queries)}, time={config_elapsed:.1f}s")

    return flat_results


def main():
    parser = argparse.ArgumentParser(description="Grid Search Worker")
    parser.add_argument("--config-file", type=str, required=True, help="설정 파일 경로")
    parser.add_argument("--queries-file", type=str, required=True, help="질문 파일 경로")
    parser.add_argument("--output", type=str, required=True, help="결과 저장 경로 (기본 파일)")
    parser.add_argument("--batch-num", type=int, required=True, help="배치 번호")
    args = parser.parse_args()

    config_file = Path(args.config_file)
    queries_file = Path(args.queries_file)
    output_base = Path(args.output).stem  # 확장자 제거
    output_dir = Path(args.output).parent
    batch_num = args.batch_num

    # 4가지 출력 파일 경로
    output_file = output_dir / f"{output_base}.json"
    output_full_file = output_dir / f"{output_base}_full.json"
    output_summary_file = output_dir / f"{output_base}_summary.json"
    output_temp_file = output_dir / f"{output_base}_temp.json"  # 중간 저장용
    
    print("=" * 80)
    print(f"Grid Search Worker - Batch {batch_num}")
    print("=" * 80)
    print(f"설정 파일: {config_file}")
    print(f"질문 파일: {queries_file}")
    print(f"출력 파일: {output_file}")
    print(f"시작 시간: {datetime.now()}")
    
    # 설정 로드
    with open(config_file, "r", encoding="utf-8") as f:
        configs = json.load(f)
    print(f"\n총 {len(configs)}개 설정 로드")
    
    # 질문 로드
    with open(queries_file, "r", encoding="utf-8") as f:
        queries = json.load(f)
    print(f"총 {len(queries)}개 질문 로드")
    
    # LangGraph 초기화
    print("\n✓ LangGraph 초기화 중...")
    try:
        graph = create_graph_flow()
        print("✓ LangGraph 초기화 완료")
    except Exception as e:
        print(f"✗ LangGraph 초기화 실패: {e}")
        return
    
    # LLM Judge 초기화
    print("✓ LLM Judge 초기화 중...")
    llm_judge = LLMJudge(model="gpt-5-mini")
    print("✓ LLM Judge 초기화 완료")

    # Answer Quality Evaluator 초기화
    print("✓ Answer Quality Evaluator 초기화 중...")
    answer_quality_evaluator = AnswerQualityEvaluator()
    print("✓ Answer Quality Evaluator 초기화 완료")

    # 온톨로지 스키마 (간략화)
    ontology_schema = {
        "classes": ["Person", "Event", "Place", "Organization", "Battle", "Dynasty"],
        "properties": {
            "participatesIn": {"domain": "Person", "range": "Event"},
            "built": {"domain": "Person", "range": "Place"},
            "causedBy": {"domain": "Event", "range": "Event"},
            "leadsTo": {"domain": "Event", "range": "Event"},
        }
    }

    # 모든 설정 실행 (flat list로 수집)
    all_flat_results = []  # Ablation 형식
    batch_start = time.time()

    for config_idx, config in enumerate(configs):
        config_results = run_single_config(
            config=config,
            queries=queries,
            graph=graph,
            llm_judge=llm_judge,
            ontology_schema=ontology_schema,
            answer_quality_evaluator=answer_quality_evaluator,
            batch_num=batch_num,
            config_idx=config_idx,
            total_configs=len(configs)
        )
        all_flat_results.extend(config_results)  # flat list에 추가

        # 중간 저장 (설정마다) - temp.json만
        with open(output_temp_file, "w", encoding="utf-8") as f:
            json.dump(all_flat_results, f, ensure_ascii=False, indent=2)
        print(f"\n[중간 저장] {config_idx + 1}/{len(configs)} 설정 완료, 총 {len(all_flat_results)}개 결과 → {output_temp_file.name}")

    batch_elapsed = time.time() - batch_start

    # 3가지 형식으로 저장
    # 1. 기본 파일 (state_output 제외)
    basic_results = []
    for r in all_flat_results:
        basic = {k: v for k, v in r.items() if k != "llm_judge_quality"}
        basic_results.append(basic)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(basic_results, f, ensure_ascii=False, indent=2)

    # 2. Full 파일 (모든 내용 포함 + LLM Judge)
    with open(output_full_file, "w", encoding="utf-8") as f:
        json.dump(all_flat_results, f, ensure_ascii=False, indent=2)

    # 3. Summary 파일 (state_output 제외, final_answer 포함)
    summary_results = []
    for r in all_flat_results:
        if r.get("success"):
            state = r.get("state_output", {})
            metrics = r.get("metrics", {})
            raw = metrics.get("raw_metrics", {}) if metrics else {}
            intent_aware = metrics.get("intent_aware", {}) if metrics else {}

            summary = {
                "experiment_name": r.get("experiment_name"),
                "description": r.get("description"),
                "query": r.get("query"),
                "query_type": state.get("query_type", "unknown"),
                "success": True,
                "execution_time": r.get("execution_time"),
                "config": r.get("config"),
                "final_answer": state.get("final_answer", ""),
                "num_extracted_entities": len(state.get("extracted_entities", [])),
                "num_expanded_entities": len(state.get("expanded_entities", [])),
                "num_evidences": len(state.get("evidences", [])),
                "num_convergence_nodes": len(state.get("convergence_triple_tree", {}).get("nodes", [])),
                "raw_metrics": raw,
                "intent_aware_score": intent_aware.get("final_score", 0) if intent_aware else 0,
                "weighted_metrics": intent_aware.get("weighted_metrics", {}) if intent_aware else {},
                "llm_judge_quality": r.get("llm_judge_quality")
            }
        else:
            summary = {
                "experiment_name": r.get("experiment_name"),
                "description": r.get("description"),
                "query": r.get("query"),
                "query_type": "unknown",
                "success": False,
                "execution_time": r.get("execution_time"),
                "config": r.get("config"),
                "error": r.get("error")
            }
        summary_results.append(summary)

    with open(output_summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, ensure_ascii=False, indent=2)

    # 배치 요약
    print("\n" + "=" * 80)
    print(f"Batch {batch_num} 완료")
    print("=" * 80)
    print(f"총 설정: {len(configs)}개")
    print(f"총 질문: {len(queries)}개")
    print(f"총 결과: {len(all_flat_results)}개")
    print(f"총 시간: {batch_elapsed:.1f}초 ({batch_elapsed/60:.1f}분)")

    # 설정별 평균 점수 출력
    config_scores = {}
    for result in all_flat_results:
        if "metrics" in result:
            config_name = result["experiment_name"]
            if config_name not in config_scores:
                config_scores[config_name] = []
            config_scores[config_name].append(result["metrics"]["final_score"])

    print(f"\n설정별 평균 점수:")
    for config_name, scores in sorted(config_scores.items(), key=lambda x: sum(x[1])/len(x[1]) if x[1] else 0, reverse=True):
        mean_score = sum(scores) / len(scores) if scores else 0
        print(f"  - {config_name}: {mean_score:.4f} ({len(scores)}개)")

    # temp 파일 삭제
    if output_temp_file.exists():
        output_temp_file.unlink()
        print(f"\n✓ 중간 파일 삭제: {output_temp_file.name}")

    print(f"\n결과 저장:")
    print(f"  - {output_file.name}")
    print(f"  - {output_full_file.name}")
    print(f"  - {output_summary_file.name}")
    print(f"종료 시간: {datetime.now()}")


if __name__ == "__main__":
    main()