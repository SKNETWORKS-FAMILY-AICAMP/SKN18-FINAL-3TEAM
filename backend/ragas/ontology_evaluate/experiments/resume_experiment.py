"""
실험 재개 스크립트

임시 파일에서 중단된 실험을 재개하고, summary를 생성합니다.

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.resume_experiment \
        --temp-file backend/ragas/ontology_evaluate/data/results_rerun/semantic_expander_temp.json \
        --group semantic_expander \
        --output backend/ragas/ontology_evaluate/data/results_rerun
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple

from backend.ragas.ontology_evaluate.baseline_ablation import AblationRunner, AblationExperimentGenerator
from backend.ragas.ontology_evaluate.experiments.run_baseline import (
    load_queries,
    evaluate_state,
    _save_experiment_results
)
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
from backend.langgraph_fuseki.graph import create_graph_flow


def load_temp_results(temp_file: Path) -> List[Dict[str, Any]]:
    """임시 파일에서 결과 로드"""
    with open(temp_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_completed_experiments(results: List[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    """완료된 실험 목록 반환 (query, experiment_name)"""
    completed = set()
    for result in results:
        query = result.get("query", "")
        exp_name = result.get("experiment_name", "")
        if query and exp_name:
            completed.add((query, exp_name))
    return completed


def get_remaining_experiments(
    queries: List[str],
    configs: List,
    completed: Set[Tuple[str, str]]
) -> List[Tuple[str, Any]]:
    """남은 실험 목록 반환"""
    remaining = []
    for query in queries:
        for config in configs:
            key = (query, config.experiment_name)
            if key not in completed:
                remaining.append((query, config))
    return remaining


def main():
    parser = argparse.ArgumentParser(description="실험 재개 및 Summary 생성")
    parser.add_argument(
        "--temp-file",
        type=str,
        required=True,
        help="임시 결과 파일 경로"
    )
    parser.add_argument(
        "--group",
        type=str,
        choices=["semantic_expander", "thread", "entity_boost"],
        default="semantic_expander",
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
        default="backend/ragas/ontology_evaluate/data/results_rerun",
        help="결과 저장 디렉토리"
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
        "--skip-resume",
        action="store_true",
        help="재개 없이 summary만 생성"
    )
    parser.add_argument(
        "--start-query",
        type=int,
        default=None,
        help="시작 질문 번호 (1-based, 예: 16)"
    )
    parser.add_argument(
        "--end-query",
        type=int,
        default=None,
        help="끝 질문 번호 (1-based, 예: 20, 포함)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("실험 재개 및 Summary 생성")
    print("=" * 70)
    print(f"임시 파일: {args.temp_file}")
    print(f"실험 그룹: {args.group}")
    print(f"결과 저장: {args.output}")
    print(f"Intent-aware 평가: {'활성화' if args.intent_aware else '비활성화'}")
    print(f"재개 실행: {'아니오' if args.skip_resume else '예'}")
    print("=" * 70)

    # 1. 임시 파일 로드
    temp_file = Path(args.temp_file)
    if not temp_file.exists():
        print(f"[ERROR] 임시 파일이 없습니다: {temp_file}")
        return

    print(f"\n[1/5] 임시 파일 로드 중...")
    existing_results = load_temp_results(temp_file)
    print(f"  → 기존 결과: {len(existing_results)}개")
    print(f"  → 임시 파일 경로: {temp_file}")
    print(f"  → (새로운 결과는 이 파일에 append되어 저장됩니다)")

    # 2. 질문 및 설정 로드
    print(f"\n[2/5] 질문 및 설정 로드 중...")
    all_queries_data = load_queries(args.queries)  # 전체 질문 데이터 (summary 생성용)
    all_queries = [q["query"] for q in all_queries_data]
    
    # 질문 범위 필터링 (실행할 질문만)
    if args.start_query is not None or args.end_query is not None:
        start_idx = (args.start_query - 1) if args.start_query else 0
        end_idx = args.end_query if args.end_query else len(all_queries)
        queries = all_queries[start_idx:end_idx]
        filtered_queries_data = all_queries_data[start_idx:end_idx]  # 실행할 질문 데이터만
        print(f"  → 전체 질문 개수: {len(all_queries)}")
        print(f"  → 필터링된 질문 범위: {start_idx + 1}-{end_idx}번 ({len(queries)}개)")
    else:
        queries = all_queries
        filtered_queries_data = all_queries_data
        print(f"  → 질문 개수: {len(queries)}")
    
    # summary 생성 시에는 전체 질문 데이터 사용
    queries_data_for_summary = all_queries_data

    all_experiments = AblationExperimentGenerator.generate_all_experiments()
    configs = all_experiments[args.group]
    print(f"  → 설정 개수: {len(configs)}")

    # 3. 완료된 실험 확인
    print(f"\n[3/5] 완료된 실험 확인 중...")
    completed = get_completed_experiments(existing_results)
    print(f"  → 완료된 실험: {len(completed)}개")
    print(f"  → 예상 총 실험: {len(queries) * len(configs)}개")

    # 4. 남은 실험 확인 및 재개
    remaining = get_remaining_experiments(queries, configs, completed)
    print(f"\n[4/5] 남은 실험 확인...")
    print(f"  → 남은 실험: {len(remaining)}개")

    results = existing_results.copy()

    if not args.skip_resume and len(remaining) > 0:
        print(f"\n[4/5] 남은 실험 재개 중...")
        
        # LLM Judge 초기화
        llm_judge = LLMJudge(model="gpt-5-mini")
        
        # 온톨로지 스키마 로드
        ontology_schema = {
            "classes": ["Person", "Event", "Place", "Organization"],
            "properties": {
                "participatesIn": {"domain": "Person", "range": "Event"},
                "built": {"domain": "Person", "range": "Place"},
                "causedBy": {"domain": "Event", "range": "Event"},
            }
        }
        
        # LangGraph 초기화
        print("  → LangGraph 초기화 중...")
        try:
            graph = create_graph_flow()
            print("  → LangGraph 초기화 완료!")
        except Exception as e:
            print(f"  → [ERROR] LangGraph 초기화 실패: {e}")
            print("  → Mock 모드로 전환합니다.")
            graph = None

        def real_graph_invoke(state):
            """실제 LangGraph 실행"""
            if "test_config" not in state:
                state["test_config"] = {}
            state["test_config"]["skip_clarification"] = True

            if graph is None:
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

            try:
                result = graph.invoke(state)
                return result
            except Exception as e:
                print(f"  → [ERROR] LangGraph 실행 실패: {e}")
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

        # Ablation Runner 초기화
        runner = AblationRunner(output_dir=args.output)

        # 남은 실험 실행
        for idx, (query, config) in enumerate(remaining, 1):
            print(f"\n  진행률: [{idx}/{len(remaining)}]")
            print(f"  질문: {query[:50]}...")
            print(f"  설정: {config.experiment_name}")

            result = runner.run_single_experiment(query, config, real_graph_invoke)
            
            # 평가 메트릭 추가
            if result["success"]:
                state_output = result["state_output"]
                # 해당 쿼리의 query_type 가져오기
                query_idx = queries.index(query)
                query_data = filtered_queries_data[query_idx]
                query_type = query_data.get("query_type", "factual")
                expected_property_groups = query_data.get("expected_property_groups", [])

                result["metrics"] = evaluate_state(
                    state_output,
                    llm_judge,
                    ontology_schema,
                    query_type=query_type,
                    expected_property_groups=expected_property_groups,
                    use_intent_aware=args.intent_aware
                )

            results.append(result)

            # 매 5개 실험마다 임시 저장 (기존 temp 파일에 덮어쓰기)
            if len(results) % 5 == 0:
                # 기존 temp 파일에 저장 (기존 + 새로운 결과 모두 포함)
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"  → 임시 저장: {temp_file} ({len(results)}개 실험)")

        print(f"\n  → 재개 완료! 총 {len(results)}개 실험")
    else:
        if args.skip_resume:
            print(f"\n[4/5] 재개 건너뛰기 (summary만 생성)")
        else:
            print(f"\n[4/5] 모든 실험이 완료되었습니다!")

    # 5. 평가 메트릭이 없는 결과에 대해 평가 추가
    print(f"\n[5/5] 평가 메트릭 추가 중...")

    # LLM Judge 초기화 (항상 필요)
    llm_judge = LLMJudge(model="gpt-5-mini")
    ontology_schema = {
        "classes": ["Person", "Event", "Place", "Organization"],
        "properties": {
            "participatesIn": {"domain": "Person", "range": "Event"},
            "built": {"domain": "Person", "range": "Place"},
            "causedBy": {"domain": "Event", "range": "Event"},
        }
    }

    # 평가 대상 개수 확인
    total_missing = sum(1 for r in results if r.get("success") and (not r.get("metrics") or r.get("metrics") == {}))
    print(f"  → 평가 필요한 결과: {total_missing}개")

    missing_metrics = 0
    for idx, result in enumerate(results):
        if result.get("success") and (not result.get("metrics") or result.get("metrics") == {}):
            state_output = result.get("state_output", {})
            if state_output:
                # 해당 쿼리의 query_type 가져오기
                query = result.get("query", "")
                # 전체 질문 목록에서 찾기
                all_query_strings = [q["query"] for q in all_queries_data]
                if query in all_query_strings:
                    query_idx = all_query_strings.index(query)
                    query_data = all_queries_data[query_idx]
                    query_type = query_data.get("query_type", "factual")
                    expected_property_groups = query_data.get("expected_property_groups", [])

                    # 진행 상황 로그 추가
                    print(f"  [{missing_metrics + 1}/{total_missing}] 평가 중: {query[:50]}... (실험: {result.get('experiment_name', 'N/A')})")

                    result["metrics"] = evaluate_state(
                        state_output,
                        llm_judge,
                        ontology_schema,
                        query_type=query_type,
                        expected_property_groups=expected_property_groups,
                        use_intent_aware=args.intent_aware
                    )
                    missing_metrics += 1

    print(f"\n  → 평가 메트릭 추가 완료: {missing_metrics}개")

    # 6. 최종 결과 저장 (Full + Summary)
    print(f"\n[6/6] 최종 결과 저장 중...")
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    # Full 결과 저장
    full_file = output_path / f"{args.group}_ablation_full.json"
    with open(full_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  → Full 결과: {full_file}")

    # Summary 생성 및 저장 (전체 질문 데이터 사용)
    _save_experiment_results(results, str(output_path), args.group, queries_data_for_summary)
    print(f"  → Summary 생성 완료!")

    print("\n" + "=" * 70)
    print("✅ 완료!")
    print("=" * 70)
    print(f"총 실험: {len(results)}개")
    print(f"성공: {sum(1 for r in results if r.get('success'))}개")
    print(f"실패: {sum(1 for r in results if not r.get('success'))}개")
    print(f"평가 메트릭 있음: {sum(1 for r in results if r.get('metrics') and r.get('metrics') != {})}개")


if __name__ == "__main__":
    main()

