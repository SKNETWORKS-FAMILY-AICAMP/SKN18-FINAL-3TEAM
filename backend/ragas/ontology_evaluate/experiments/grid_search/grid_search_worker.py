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
    ConvergenceUtilizationEvaluator
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
    """
    se_config = config.get("semantic_expander", {})
    thread_config = config.get("thread_weights", {})
    boost_config = config.get("entity_boost", {})
    
    # Thread weights → aggregator_threads (활성/비활성)
    # 가중치가 0.0이면 비활성화
    aggregator_threads = {
        "outgoing_relations": thread_config.get("outgoing_relations", 1.0) > 0,
        "incoming_relations": thread_config.get("incoming_relations", 1.0) > 0,
        "connected_entities": thread_config.get("connected_entities", 1.0) > 0,
        "entity_properties": thread_config.get("entity_properties", 1.0) > 0,
        "type_and_summary": thread_config.get("type_and_summary", 1.0) > 0,
    }
    
    # Entity boost mode 결정
    normalized = boost_config.get("normalized", 1.0)
    partial = boost_config.get("partial", 1.0)
    
    if normalized > partial:
        entity_boost_mode = "normalized_match"
    elif partial > normalized:
        entity_boost_mode = "partial_match"
    else:
        entity_boost_mode = "exact_match"  # 같으면 exact
    
    return {
        "skip_clarification": True,
        "semantic_expander": se_config,
        "aggregator_threads": aggregator_threads,
        "entity_boost_mode": entity_boost_mode,
        # 실제 가중치 값도 저장 (노드에서 사용)
        "thread_weights_values": thread_config,
        "entity_boost_values": boost_config,
    }


def run_single_config(
    config: Dict[str, Any],
    queries: List[Dict],
    graph,
    llm_judge: LLMJudge,
    ontology_schema: dict,
    batch_num: int,
    config_idx: int,
    total_configs: int
) -> Dict[str, Any]:
    """
    단일 설정으로 모든 질문 실행 및 평가
    """
    config_name = config.get("name", f"config_{config_idx}")
    test_config = build_test_config(config)
    
    print(f"\n{'='*70}")
    print(f"[Batch {batch_num}] 설정 {config_idx+1}/{total_configs}: {config_name}")
    print(f"{'='*70}")
    print(f"  SE: temporal={config['semantic_expander'].get('temporal')}, "
          f"causal={config['semantic_expander'].get('causal_chain')}")
    print(f"  Thread: in={config['thread_weights'].get('incoming_relations')}, "
          f"out={config['thread_weights'].get('outgoing_relations')}")
    print(f"  Boost: norm={config['entity_boost'].get('normalized')}, "
          f"partial={config['entity_boost'].get('partial')}")
    
    config_results = []
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
            
            q_elapsed = time.time() - q_start
            
            result = {
                "query": query,
                "query_type": query_type,
                "raw_metrics": metrics["raw_metrics"],
                "final_score": metrics["intent_aware"]["final_score"] if metrics["intent_aware"] else 0.0,
                "elapsed_time": q_elapsed,
                "status": "success"
            }
            
            print(f"    ✓ Score: {result['final_score']:.4f} ({q_elapsed:.1f}s)")
            
        except Exception as e:
            q_elapsed = time.time() - q_start
            result = {
                "query": query,
                "query_type": query_type,
                "error": str(e),
                "elapsed_time": q_elapsed,
                "status": "error"
            }
            print(f"    ✗ Error: {str(e)[:50]}")
        
        config_results.append(result)
    
    config_elapsed = time.time() - config_start
    
    # 설정별 통계 계산
    success_results = [r for r in config_results if r["status"] == "success"]
    scores = [r["final_score"] for r in success_results]
    
    config_summary = {
        "config_name": config_name,
        "config": config,
        "total_queries": len(queries),
        "success_count": len(success_results),
        "error_count": len(queries) - len(success_results),
        "mean_score": sum(scores) / len(scores) if scores else 0.0,
        "min_score": min(scores) if scores else 0.0,
        "max_score": max(scores) if scores else 0.0,
        "total_time": config_elapsed,
        "results": config_results
    }
    
    print(f"\n  Summary: mean={config_summary['mean_score']:.4f}, "
          f"success={config_summary['success_count']}/{len(queries)}, "
          f"time={config_elapsed:.1f}s")
    
    return config_summary


def main():
    parser = argparse.ArgumentParser(description="Grid Search Worker")
    parser.add_argument("--config-file", type=str, required=True, help="설정 파일 경로")
    parser.add_argument("--queries-file", type=str, required=True, help="질문 파일 경로")
    parser.add_argument("--output", type=str, required=True, help="결과 저장 경로")
    parser.add_argument("--batch-num", type=int, required=True, help="배치 번호")
    args = parser.parse_args()
    
    config_file = Path(args.config_file)
    queries_file = Path(args.queries_file)
    output_file = Path(args.output)
    batch_num = args.batch_num
    
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
    llm_judge = LLMJudge(model="gpt-4o-mini")
    print("✓ LLM Judge 초기화 완료")
    
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
    
    # 모든 설정 실행
    all_results = []
    batch_start = time.time()
    
    for config_idx, config in enumerate(configs):
        result = run_single_config(
            config=config,
            queries=queries,
            graph=graph,
            llm_judge=llm_judge,
            ontology_schema=ontology_schema,
            batch_num=batch_num,
            config_idx=config_idx,
            total_configs=len(configs)
        )
        all_results.append(result)
        
        # 중간 저장 (5개마다)
        if (config_idx + 1) % 5 == 0:
            temp_data = {
                "batch_num": batch_num,
                "total_configs": len(configs),
                "completed_configs": config_idx + 1,
                "results": all_results
            }
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(temp_data, f, ensure_ascii=False, indent=2)
            print(f"\n[중간 저장] {config_idx + 1}/{len(configs)} 설정 완료")
    
    batch_elapsed = time.time() - batch_start
    
    # 최종 저장
    output_data = {
        "batch_num": batch_num,
        "total_configs": len(configs),
        "total_queries": len(queries),
        "total_runs": len(configs) * len(queries),
        "total_time": batch_elapsed,
        "start_time": datetime.now().isoformat(),
        "results": all_results
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # 배치 요약
    print("\n" + "=" * 80)
    print(f"Batch {batch_num} 완료")
    print("=" * 80)
    print(f"총 설정: {len(configs)}개")
    print(f"총 질문: {len(queries)}개")
    print(f"총 실행: {len(configs) * len(queries)}회")
    print(f"총 시간: {batch_elapsed:.1f}초 ({batch_elapsed/60:.1f}분)")
    
    # 상위 5개 설정 출력
    sorted_results = sorted(all_results, key=lambda x: x["mean_score"], reverse=True)
    print(f"\n상위 5개 설정:")
    for i, r in enumerate(sorted_results[:5], 1):
        print(f"  {i}. {r['config_name']}: {r['mean_score']:.4f}")
    
    print(f"\n결과 저장: {output_file}")
    print(f"종료 시간: {datetime.now()}")


if __name__ == "__main__":
    main()