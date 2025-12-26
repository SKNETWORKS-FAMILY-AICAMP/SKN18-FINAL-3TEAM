"""
평가 Worker 스크립트

개별 배치의 질문들을 처리하여 평가 결과를 생성합니다.

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.evaluation_worker \
        --batch-file backend/ragas/ontology_evaluate/data/batch_1_queries.json \
        --output backend/ragas/ontology_evaluate/data/full_evaluation_results/batch_1_results.json \
        --batch-num 1
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
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
from backend.langgraph_fuseki.config import get_config_for_query_type

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

    # Property Group Selection 점수 추가 (있는 경우)
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
        "intent_aware": intent_aware_result
    }


def process_query(
    query_data: dict,
    graph,
    llm_judge: LLMJudge,
    ontology_schema: dict,
    batch_num: int,
    query_idx: int
) -> dict:
    """
    단일 질문을 처리하여 평가 결과 생성

    Args:
        query_data: 질문 데이터
        graph: LangGraph 인스턴스
        llm_judge: LLM Judge 인스턴스
        ontology_schema: 온톨로지 스키마
        batch_num: 배치 번호
        query_idx: 질문 인덱스

    Returns:
        평가 결과 딕셔너리
    """
    query = query_data["query"]
    query_type = query_data.get("query_type", "deep_analysis")
    expected_property_groups = query_data.get("expected_property_groups", [])

    print(f"\n[Batch {batch_num}][{query_idx+1}] 처리 시작: {query}")
    print(f"  Query Type: {query_type}")

    start_time = time.time()
    rag_config = get_config_for_query_type(query_type)

    try:
        state = {
            "query": query,
            "query_type": query_type,  # 쿼리 타입 전달
            "test_config": {
                "skip_clarification": True,
                "semantic_expander": rag_config["semantic_expander"],
                "aggregator_threads": {
                    k: v > 0 for k, v in rag_config["thread_weights"].items()
                },
                "entity_boost_mode": rag_config["entity_boost"]
            }
        }

        print(f"  [LangGraph 실행 중...]")
        state_output = graph.invoke(state)

        # 평가 메트릭 계산
        print(f"  [평가 메트릭 계산 중...]")
        metrics = evaluate_state(
            state_output,
            llm_judge,
            ontology_schema,
            query_type=query_type,
            expected_property_groups=expected_property_groups
        )

        elapsed_time = time.time() - start_time

        # 결과 구성
        result = {
            "query": query,
            "query_type": query_type,
            "query_data": query_data,
            "raw_metrics": metrics["raw_metrics"],
            "evaluation": metrics["intent_aware"],
            "final_answer": state_output.get("final_answer", ""),
            "num_extracted_entities": len(state_output.get("extracted_entities", [])),
            "num_expanded_entities": len(state_output.get("expanded_entities", [])),
            "num_evidences": len(state_output.get("evidences", [])),
            "num_convergence_nodes": len(state_output.get("convergence_nodes", [])),
            "elapsed_time": elapsed_time,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }

        final_score = metrics["intent_aware"]["final_score"] if metrics["intent_aware"] else 0.0
        print(f"  ✓ 완료 (소요 시간: {elapsed_time:.2f}초)")
        print(f"  Final Score: {final_score:.4f}")

        return result

    except Exception as e:
        elapsed_time = time.time() - start_time

        result = {
            "query": query,
            "query_type": query_type,
            "query_data": query_data,
            "error": str(e),
            "elapsed_time": elapsed_time,
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }

        print(f"  ✗ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

        return result


def main():
    parser = argparse.ArgumentParser(description="배치 평가 Worker")
    parser.add_argument("--batch-file", type=str, required=True, help="배치 질문 파일 경로")
    parser.add_argument("--output", type=str, required=True, help="결과 저장 경로")
    parser.add_argument("--batch-num", type=int, required=True, help="배치 번호")
    args = parser.parse_args()

    batch_file = Path(args.batch_file)
    output_file = Path(args.output)
    batch_num = args.batch_num

    print("="*80)
    print(f"Batch {batch_num} Worker 시작")
    print("="*80)
    print(f"입력 파일: {batch_file}")
    print(f"출력 파일: {output_file}")
    print(f"시작 시간: {datetime.now()}")

    # 배치 질문 로드
    with open(batch_file, "r", encoding="utf-8") as f:
        queries = json.load(f)

    print(f"\n총 {len(queries)}개 질문 로드 완료")

    # LangGraph 초기화
    print("✓ LangGraph 초기화 중...")
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

    # 온톨로지 스키마 (임시)
    ontology_schema = {
        "classes": ["Person", "Event", "Place", "Organization"],
        "properties": {
            "participatesIn": {"domain": "Person", "range": "Event"},
            "built": {"domain": "Person", "range": "Place"},
            "causedBy": {"domain": "Event", "range": "Event"},
        }
    }

    # 질문 처리
    results = []
    success_count = 0
    error_count = 0

    for idx, query_data in enumerate(queries):
        result = process_query(query_data, graph, llm_judge, ontology_schema, batch_num, idx)
        results.append(result)

        if result["status"] == "success":
            success_count += 1
        else:
            error_count += 1

        # 중간 저장 (10개마다)
        if (idx + 1) % 10 == 0:
            temp_data = {
                "batch_num": batch_num,
                "total_queries": len(queries),
                "success_count": success_count,
                "error_count": error_count,
                "results": results
            }
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(temp_data, f, ensure_ascii=False, indent=2)
            print(f"\n[중간 저장] {idx + 1}/{len(queries)} 완료")

    # 최종 저장
    output_data = {
        "batch_num": batch_num,
        "total_queries": len(queries),
        "success_count": success_count,
        "error_count": error_count,
        "start_time": datetime.now().isoformat(),
        "results": results
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print("\n" + "="*80)
    print(f"Batch {batch_num} Worker 완료")
    print("="*80)
    print(f"총 질문: {len(queries)}개")
    print(f"성공: {success_count}개")
    print(f"실패: {error_count}개")
    print(f"결과 저장: {output_file}")
    print(f"종료 시간: {datetime.now()}")


if __name__ == "__main__":
    main()
