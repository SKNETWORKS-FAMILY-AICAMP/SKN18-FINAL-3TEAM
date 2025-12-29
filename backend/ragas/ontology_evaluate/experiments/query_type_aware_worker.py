"""
Query-Type Aware Scoring Worker 스크립트

개별 배치의 질문들을 Baseline과 v3.0 설정으로 실행하여 평가 결과 생성

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.query_type_aware_worker \
        --batch-file data/query_type_aware_results/batch_1.json \
        --output data/query_type_aware_results/batch_1_results_20241229_120000.json \
        --batch-num 1 \
        --timestamp 20241229_120000
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

# 공통 평가 모듈 import
from backend.ragas.ontology_evaluate.utils.experiment_utils import (
    run_single_query,
    initialize_evaluators
)

# 실험 설정
from backend.ragas.ontology_evaluate.experiments.run_query_type_aware_scoring import ExperimentConfig


def run_batch_experiment(
    queries: List[Dict],
    graph,
    llm_judge,
    ontology_schema: dict,
    answer_quality_evaluator,
    batch_num: int,
    timestamp: str
) -> List[Dict[str, Any]]:
    """
    배치 질문들을 Baseline과 v3.0 설정으로 실행

    Args:
        queries: 질문 리스트
        graph: LangGraph 인스턴스
        llm_judge: LLM Judge
        ontology_schema: 온톨로지 스키마
        answer_quality_evaluator: 답변 품질 평가자
        batch_num: 배치 번호
        timestamp: 타임스탬프

    Returns:
        실험 결과 리스트 (Baseline + v3.0)
    """
    all_results = []
    
    # 실험 설정
    baseline_config = ExperimentConfig.get_baseline_config()
    v3_config = ExperimentConfig.get_v3_config()
    
    configs = [baseline_config, v3_config]
    
    for config_idx, config in enumerate(configs):
        config_name = config["name"]
        print(f"\n{'='*70}")
        print(f"[Batch {batch_num}] 설정 {config_idx+1}/{len(configs)}: {config_name}")
        print(f"{'='*70}")
        
        config_start = time.time()
        
        for q_idx, query_data in enumerate(queries, 1):
            query = query_data.get("query", "")
            print(f"\n  [{q_idx}/{len(queries)}] {query[:50]}...")
            
            try:
                result = run_single_query(
                    query_data=query_data,
                    graph=graph,
                    config=config,
                    llm_judge=llm_judge,
                    ontology_schema=ontology_schema,
                    answer_quality_evaluator=answer_quality_evaluator,
                    query_idx=q_idx,
                    total_queries=len(queries),
                    verbose=False  # 배치 실행 시 상세 출력 최소화
                )
                
                # intent_aware_score 추출
                intent_score = 0.0
                if result.get("metrics") and result["metrics"].get("intent_aware"):
                    intent_score = result["metrics"]["intent_aware"].get("final_score", 0.0)
                
                print(f"    ✓ Score: {intent_score:.4f}")
                all_results.append(result)
                
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:50]}")
                error_result = {
                    "experiment_name": config_name,
                    "description": config.get("description", ""),
                    "query": query,
                    "success": False,
                    "error": str(e),
                    "execution_time": 0.0,
                    "metrics": None
                }
                all_results.append(error_result)
        
        config_elapsed = time.time() - config_start
        success_count = sum(1 for r in all_results if r.get("experiment_name") == config_name and r.get("success", False))
        print(f"\n  Summary: {config_name} - success={success_count}/{len(queries)}, time={config_elapsed:.1f}s")
    
    return all_results


def main():
    parser = argparse.ArgumentParser(description="Query-Type Aware Scoring Worker")
    parser.add_argument("--batch-file", type=str, required=True, help="배치 질문 파일 경로")
    parser.add_argument("--output", type=str, required=True, help="결과 저장 경로")
    parser.add_argument("--batch-num", type=int, required=True, help="배치 번호")
    parser.add_argument("--timestamp", type=str, required=True, help="타임스탬프")
    args = parser.parse_args()

    batch_file = Path(args.batch_file)
    output_file = Path(args.output)
    batch_num = args.batch_num
    timestamp = args.timestamp

    print("=" * 80)
    print(f"Query-Type Aware Scoring Worker - Batch {batch_num}")
    print("=" * 80)
    print(f"배치 파일: {batch_file}")
    print(f"출력 파일: {output_file}")
    print(f"시작 시간: {datetime.now()}")
    
    # 배치 질문 로드
    if not batch_file.exists():
        print(f"✗ 배치 파일이 없습니다: {batch_file}")
        return
    
    with open(batch_file, "r", encoding="utf-8") as f:
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
    
    # 평가 도구 초기화
    print("✓ 평가 도구 초기화 중...")
    try:
        llm_judge, answer_quality_evaluator, ontology_schema = initialize_evaluators()
        print("✓ 평가 도구 초기화 완료")
    except Exception as e:
        print(f"✗ 평가 도구 초기화 실패: {e}")
        return
    
    # 배치 실험 실행
    batch_start = time.time()
    all_results = run_batch_experiment(
        queries=queries,
        graph=graph,
        llm_judge=llm_judge,
        ontology_schema=ontology_schema,
        answer_quality_evaluator=answer_quality_evaluator,
        batch_num=batch_num,
        timestamp=timestamp
    )
    batch_elapsed = time.time() - batch_start
    
    # 결과 저장
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    # 배치 요약
    print("\n" + "=" * 80)
    print(f"Batch {batch_num} 완료")
    print("=" * 80)
    print(f"총 질문: {len(queries)}개")
    print(f"총 결과: {len(all_results)}개 (Baseline {len(queries)}개 + v3.0 {len(queries)}개)")
    print(f"총 시간: {batch_elapsed:.1f}초 ({batch_elapsed/60:.1f}분)")
    
    # 설정별 평균 점수 출력
    config_scores = {}
    for result in all_results:
        if result.get("success") and result.get("metrics") and result["metrics"].get("intent_aware"):
            config_name = result.get("experiment_name", "unknown")
            if config_name not in config_scores:
                config_scores[config_name] = []
            score = result["metrics"]["intent_aware"].get("final_score", 0.0)
            config_scores[config_name].append(score)
    
    print(f"\n설정별 평균 점수:")
    for config_name, scores in sorted(config_scores.items(), key=lambda x: sum(x[1])/len(x[1]) if x[1] else 0, reverse=True):
        mean_score = sum(scores) / len(scores) if scores else 0
        print(f"  - {config_name}: {mean_score:.4f} ({len(scores)}개)")
    
    print(f"\n결과 저장: {output_file}")
    print(f"종료 시간: {datetime.now()}")


if __name__ == "__main__":
    main()

