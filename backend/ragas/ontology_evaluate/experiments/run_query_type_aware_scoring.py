"""
Query-Type Aware Scoring System v4.0 실험

v4.0 설정으로만 실험 실행 (Baseline 실행하지 않음)

Usage:
    # 전체 80개 질문 실행
    python -m backend.ragas.ontology_evaluate.experiments.run_query_type_aware_scoring

    # 특정 개수만 테스트
    python -m backend.ragas.ontology_evaluate.experiments.run_query_type_aware_scoring --limit 20

    # 로그 저장
    python -m backend.ragas.ontology_evaluate.experiments.run_query_type_aware_scoring > logs/v4_experiment.log 2>&1
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 공통 평가 모듈
from backend.ragas.ontology_evaluate.evaluators import AnswerQualityEvaluator
from backend.ragas.ontology_evaluate.utils.llm_judge import LLMJudge
from backend.ragas.ontology_evaluate.utils.experiment_utils import (
    run_single_query,
    load_queries,
    initialize_evaluators
)

# LangGraph import
from backend.langgraph_fuseki.graph import create_graph_flow


# =====================================================
# 실험 설정
# =====================================================

class ExperimentConfig:
    """실험 설정 관리"""

    @staticmethod
    def get_baseline_config() -> Dict[str, Any]:
        """
        Baseline: Quick Win 설정 (기존 최적 설정)

        출처: backend/ragas/ontology_evaluate/data/quick_win/ALL_WEIGHT_EXPERIMENT_RESULTS.md
        - Thread incoming 제거: +1.7%p 개선
        - Normalized + Partial 강화: intent와 accuracy 균형
        - Semantic Expander 비활성화: +20%p 개선
        """
        return {
            "name": "baseline_quick_win",
            "description": "Quick Win 최적 설정 (Baseline)",
            # 주의: config.py의 기본값이 Quick Win이므로 추가 설정 불필요
            # 실제로는 기본 config.py 설정을 그대로 사용
        }

    @staticmethod
    def get_v3_config() -> Dict[str, Any]:
        """
        v3.0: Query-Type Aware Scoring System

        모든 Component가 쿼리 타입별로 다른 점수를 받음:
        - Semantic Expander: 쿼리 타입별 점수 (기존)
        - Thread Aggregator: 쿼리 타입별 점수 (NEW)
        - Entity Boost: 쿼리 타입별 점수 (NEW)

        출처: backend/langgraph_fuseki/utils/evidence_scoring.py
        - SEMANTIC_EXPANDER_BY_QUERY_TYPE
        - THREAD_AGGREGATOR_BY_QUERY_TYPE
        - ENTITY_BOOST_BY_QUERY_TYPE
        """
        return {
            "name": "v3_query_type_aware",
            "description": "Query-Type Aware Scoring v3.0 (모든 Component 쿼리 타입별 점수)",
            # 주의: evidence_scoring.py가 자동으로 쿼리 타입별 점수 적용
            # config.py 수정 불필요 (scoring 로직만 변경)
        }

    @staticmethod
    def get_v4_config() -> Dict[str, Any]:
        """
        v4.0: Query-Type Aware Scoring System v4.0

        v4.0는 그래프 구조 자체를 변경한 버전입니다.
        컴포넌트 on/off 설정이 아닌 그래프 자체의 변경이므로
        기본 설정을 사용합니다.
        """
        return {
            "name": "v4_query_type_aware",
            "description": "Query-Type Aware Scoring v4.0 (그래프 구조 변경)",
            # 주의: 그래프 구조 자체가 변경되었으므로 컴포넌트 설정 불필요
            # build_test_config가 experiment_name에서 "query_type_aware"를 감지하여
            # use_query_type_aware=True로 자동 설정됨
        }


# =====================================================
# 실험 실행 함수
# =====================================================


def run_experiment(
    config: Dict[str, Any],
    queries: List[Dict],
    graph,
    llm_judge: LLMJudge,
    ontology_schema: dict,
    answer_quality_evaluator: AnswerQualityEvaluator
) -> List[Dict[str, Any]]:
    """
    단일 설정으로 모든 질문 실행

    Args:
        config: 실험 설정
        queries: 질문 리스트
        graph: LangGraph 인스턴스
        llm_judge: LLM Judge
        ontology_schema: 온톨로지 스키마
        answer_quality_evaluator: 답변 품질 평가자

    Returns:
        실험 결과 리스트
    """
    results = []
    total_queries = len(queries)

    print(f"\n{'='*80}")
    print(f"실험 시작: {config['name']}")
    print(f"설명: {config['description']}")
    print(f"질문 수: {total_queries}개")
    print(f"{'='*80}")

    for idx, query_data in enumerate(queries, 1):
        result = run_single_query(
            query_data=query_data,
            graph=graph,
            config=config,
            llm_judge=llm_judge,
            ontology_schema=ontology_schema,
            answer_quality_evaluator=answer_quality_evaluator,
            query_idx=idx,
            total_queries=total_queries,
            verbose=True
        )
        results.append(result)

        # 중간 저장 (10개마다)
        if idx % 10 == 0:
            print(f"\n  [체크포인트] {idx}/{total_queries} 완료")

    print(f"\n{'='*80}")
    print(f"실험 완료: {config['name']}")
    print(f"성공: {len([r for r in results if 'error' not in r])}/{total_queries}")
    print(f"{'='*80}")

    return results


# =====================================================
# 결과 비교 및 분석
# =====================================================
# compare_experiment_results와 print_comparison_summary는
# utils.experiment_utils에서 import하여 사용


# =====================================================
# Main 실행
# =====================================================

def main():
    parser = argparse.ArgumentParser(description="Query-Type Aware Scoring v4.0 실험")
    parser.add_argument("--limit", type=int, default=None, help="실행할 질문 수 제한 (기본: 전체 80개)")
    parser.add_argument("--output-dir", type=str, default=None, help="결과 저장 디렉토리")
    args = parser.parse_args()

    # 경로 설정
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
    BACKEND_DIR = PROJECT_ROOT / "backend"
    EVAL_DIR = BACKEND_DIR / "ragas" / "ontology_evaluate"
    DATA_DIR = EVAL_DIR / "data"

    # 결과 디렉토리
    if args.output_dir:
        RESULTS_DIR = Path(args.output_dir)
    else:
        RESULTS_DIR = DATA_DIR / "results_v4"

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 타임스탬프
    TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. 테스트 질문 로드
    TEST_QUERIES_PATH = DATA_DIR / "test_queries.json"
    queries = load_queries(str(TEST_QUERIES_PATH))

    if args.limit:
        queries = queries[:args.limit]

    print(f"총 {len(queries)}개 질문 로드 완료")

    # 2. 평가 도구 초기화
    llm_judge, answer_quality_evaluator, ontology_schema = initialize_evaluators()

    # 3. LangGraph 생성
    graph = create_graph_flow()

    # 4. 실험 설정
    v4_config = ExperimentConfig.get_v4_config()

    # 5. v4.0 실험 실행
    print(f"\n{'#'*80}")
    print("# v4.0 (Query-Type Aware) 실험")
    print(f"{'#'*80}")

    v4_results = run_experiment(
        config=v4_config,
        queries=queries,
        graph=graph,
        llm_judge=llm_judge,
        ontology_schema=ontology_schema,
        answer_quality_evaluator=answer_quality_evaluator
    )

    # v4.0 결과 저장
    v4_output = RESULTS_DIR / f"v4_query_type_aware_{TIMESTAMP}.json"
    with open(v4_output, "w", encoding="utf-8") as f:
        json.dump(v4_results, f, ensure_ascii=False, indent=2)
    print(f"\nv4.0 결과 저장: {v4_output}")

    print(f"\n{'#'*80}")
    print("# 실험 완료!")
    print(f"{'#'*80}")
    print(f"\n결과 파일:")
    print(f"  - v4.0: {v4_output}")
    print(f"\n저장 위치: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
