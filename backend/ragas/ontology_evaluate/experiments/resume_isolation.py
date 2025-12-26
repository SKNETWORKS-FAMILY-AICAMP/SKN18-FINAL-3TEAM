"""
Isolation 실험 재개 스크립트

임시 파일에서 중단된 실험을 재개하고, summary를 생성합니다.

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.resume_isolation \
        --group entity_boost \
        --output backend/ragas/ontology_evaluate/data/results_isolation
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple

from backend.ragas.ontology_evaluate.baseline_ablation import AblationRunner
from backend.ragas.ontology_evaluate.experiments.run_isolation import (
    IsolationExperimentGenerator,
    load_queries,
    evaluate_state,
    _save_experiment_results
)
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


def find_errors_in_state(state_output: Dict[str, Any], path: str = "") -> List[Dict[str, Any]]:
    """재귀적으로 state_output 내부의 모든 에러 찾기"""
    errors = []
    
    if isinstance(state_output, dict):
        # 직접 error 필드가 있는 경우
        if 'error' in state_output:
            error_msg = state_output.get('error', '')
            if '500' in str(error_msg) or 'Maximum lock' in str(error_msg) or 'SPARQL' in str(error_msg):
                errors.append({
                    'path': path,
                    'error': error_msg.strip(),
                })
        
        # 재귀적으로 탐색
        for key, value in state_output.items():
            if key != 'error':  # 이미 처리한 error는 제외
                new_path = f"{path}.{key}" if path else key
                errors.extend(find_errors_in_state(value, new_path))
    
    elif isinstance(state_output, list):
        for i, item in enumerate(state_output):
            new_path = f"{path}[{i}]" if path else f"[{i}]"
            errors.extend(find_errors_in_state(item, new_path))
    
    return errors


def get_failed_experiments(
    results: List[Dict[str, Any]],
    queries: List[str],
    configs: List
) -> List[Tuple[str, Any]]:
    """실패한 실험 목록 반환 (HTTP 500, SPARQL 에러 등)"""
    failed = []
    
    for result in results:
        query = result.get("query", "")
        exp_name = result.get("experiment_name", "")
        success = result.get("success", True)
        top_level_error = result.get("error", "")
        state_output = result.get("state_output", {})
        
        # 최상위 레벨 에러 확인
        has_top_error = ('500' in str(top_level_error) or 
                        'Maximum lock' in str(top_level_error) or 
                        'SPARQL' in str(top_level_error))
        
        # state_output 내부 에러 찾기
        state_errors = find_errors_in_state(state_output) if state_output else []
        
        # 실패한 실험인 경우
        if not success or has_top_error or state_errors:
            # 해당 config 찾기
            config = None
            for c in configs:
                if c.experiment_name == exp_name:
                    config = c
                    break
            
            if config and query in queries:
                failed.append((query, config))
    
    return failed


def main():
    parser = argparse.ArgumentParser(description="Isolation 실험 재개 및 Summary 생성")
    parser.add_argument(
        "--group",
        type=str,
        choices=["semantic_expander", "thread", "entity_boost"],
        required=True,
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
        default="backend/ragas/ontology_evaluate/data/results_isolation",
        help="결과 저장 디렉토리"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="테스트 질문 개수 제한"
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
        "--retry-failed",
        action="store_true",
        help="실패한 실험 (HTTP 500, SPARQL 에러 등)도 재실행"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Isolation 실험 재개 및 Summary 생성")
    print("=" * 70)
    print(f"실험 그룹: {args.group}")
    print(f"질문 파일: {args.queries}")
    print(f"질문 개수 제한: {args.limit}개")
    print(f"결과 저장: {args.output}")
    print(f"Intent-aware 평가: {'활성화' if args.intent_aware else '비활성화'}")
    print(f"재개 실행: {'아니오' if args.skip_resume else '예'}")
    print(f"실패한 실험 재실행: {'예' if args.retry_failed else '아니오'}")
    print("=" * 70)

    # 1. 결과 파일 확인 (temp 파일 우선 사용, ablation은 무시)
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    temp_file = output_path / f"{args.group}_temp.json"
    full_file = output_path / f"{args.group}_isolation_full.json"
    ablation_file = output_path / f"{args.group}_ablation.json"
    
    # temp 파일 우선 사용 (ablation은 무시)
    source_file = None
    source_name = None
    
    if temp_file.exists():
        source_file = temp_file
        source_name = "temp"
    elif full_file.exists():
        source_file = full_file
        source_name = "full"
    else:
        print(f"[ERROR] 결과 파일이 없습니다:")
        print(f"  - {temp_file}")
        print(f"  - {full_file}")
        if ablation_file.exists():
            print(f"  - [무시됨] {ablation_file} (ablation 파일은 미완성이므로 무시합니다)")
        print(f"  → 실험을 처음부터 시작하세요.")
        return
    
    # ablation 파일이 있으면 경고만 출력 (사용하지 않음)
    if ablation_file.exists():
        print(f"\n[INFO] ablation 파일이 있지만 무시합니다: {ablation_file}")
        print(f"  → temp 파일을 기준으로 재실험을 진행합니다.")

    print(f"\n[1/6] 결과 파일 로드 중...")
    existing_results = load_temp_results(source_file)
    print(f"  → 기존 결과: {len(existing_results)}개")
    print(f"  → 소스 파일: {source_file} ({source_name})")

    # 2. 질문 및 설정 로드
    print(f"\n[2/6] 질문 및 설정 로드 중...")
    queries_data = load_queries(args.queries)
    if args.limit:
        queries_data = queries_data[:args.limit]
    queries = [q["query"] for q in queries_data]
    print(f"  → 질문 개수: {len(queries)}")

    all_experiments = IsolationExperimentGenerator.generate_all_isolation_experiments()
    configs = all_experiments[args.group]
    print(f"  → 설정 개수: {len(configs)}")

    # 3. 완료된 실험 확인
    print(f"\n[3/6] 완료된 실험 확인 중...")
    completed = get_completed_experiments(existing_results)
    print(f"  → 완료된 실험: {len(completed)}개")
    print(f"  → 예상 총 실험: {len(queries) * len(configs)}개")
    
    # 실패한 실험 확인
    if args.retry_failed:
        print(f"\n[3.5/6] 실패한 실험 확인 중...")
        failed_experiments = get_failed_experiments(existing_results, queries, configs)
        print(f"  → 실패한 실험: {len(failed_experiments)}개")
        
        if failed_experiments:
            # 질문별 통계
            failed_queries = {}
            for query, config in failed_experiments:
                if query not in failed_queries:
                    failed_queries[query] = []
                failed_queries[query].append(config.experiment_name)
            
            print(f"  → 실패한 질문: {len(failed_queries)}개")
            for query, exps in list(failed_queries.items())[:5]:
                print(f"    - {query[:50]}... ({len(exps)}개 실험)")

    # 4. 남은 실험 확인 및 재개
    remaining = get_remaining_experiments(queries, configs, completed)
    
    # 실패한 실험도 재실행하는 경우 추가
    if args.retry_failed:
        failed_experiments = get_failed_experiments(existing_results, queries, configs)
        # 기존 결과에서 실패한 실험 제거 (재실행을 위해)
        failed_keys = {(q, c.experiment_name) for q, c in failed_experiments}
        results = [r for r in existing_results 
                  if (r.get("query", ""), r.get("experiment_name", "")) not in failed_keys]
        # 남은 실험에 실패한 실험 추가
        remaining.extend(failed_experiments)
        print(f"\n[4/6] 남은 실험 확인...")
        print(f"  → 미완료 실험: {len(get_remaining_experiments(queries, configs, completed))}개")
        print(f"  → 실패한 실험 (재실행): {len(failed_experiments)}개")
        print(f"  → 총 재실행: {len(remaining)}개")
    else:
        results = existing_results.copy()
        print(f"\n[4/6] 남은 실험 확인...")
        print(f"  → 남은 실험: {len(remaining)}개")

    if not args.skip_resume and len(remaining) > 0:
        print(f"\n[4/6] 남은 실험 재개 중...")
        
        # LLM Judge 초기화
        llm_judge = LLMJudge(model="gpt-4o-mini")
        
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
        from backend.ragas.ontology_evaluate.baseline_ablation import AblationRunner
        runner = AblationRunner(output_dir=str(output_path))

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
                query_data = queries_data[query_idx]
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

            # 매 5개 실험마다 임시 저장
            if len(results) % 5 == 0:
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"  → 임시 저장: {temp_file} ({len(results)}개 실험)")

        print(f"\n  → 재개 완료! 총 {len(results)}개 실험")
    else:
        if args.skip_resume:
            print(f"\n[4/6] 재개 건너뛰기 (summary만 생성)")
        else:
            print(f"\n[4/6] 모든 실험이 완료되었습니다!")

    # 5. 평가 메트릭이 없는 결과에 대해 평가 추가
    print(f"\n[5/6] 평가 메트릭 추가 중...")
    
    # LLM Judge 초기화 (아직 안 했다면)
    if not args.skip_resume or len(remaining) == 0:
        llm_judge = LLMJudge(model="gpt-4o-mini")
        ontology_schema = {
            "classes": ["Person", "Event", "Place", "Organization"],
            "properties": {
                "participatesIn": {"domain": "Person", "range": "Event"},
                "built": {"domain": "Person", "range": "Place"},
                "causedBy": {"domain": "Event", "range": "Event"},
            }
        }

    missing_metrics = 0
    for idx, result in enumerate(results):
        if result.get("success") and (not result.get("metrics") or result.get("metrics") == {}):
            state_output = result.get("state_output", {})
            if state_output:
                # 해당 쿼리의 query_type 가져오기
                query = result.get("query", "")
                if query in queries:
                    query_idx = queries.index(query)
                    query_data = queries_data[query_idx]
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
                    missing_metrics += 1

    print(f"  → 평가 메트릭 추가: {missing_metrics}개")

    # 6. 최종 결과 저장 (Full + Summary)
    print(f"\n[6/6] 최종 결과 저장 중...")

    # Full 결과 저장
    with open(full_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  → Full 결과: {full_file}")

    # Summary 생성 및 저장
    _save_experiment_results(results, str(output_path), args.group, queries_data)
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

