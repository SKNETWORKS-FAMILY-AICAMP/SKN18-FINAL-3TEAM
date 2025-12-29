"""
실험 실행 및 결과 분석 공통 유틸리티

모든 실험 스크립트에서 재사용 가능한 함수들
"""

import time
import subprocess
import sys
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

from backend.ragas.ontology_evaluate.common_eval import evaluate_state, get_ontology_schema
from backend.ragas.ontology_evaluate.evaluators import AnswerQualityEvaluator
from backend.ragas.ontology_evaluate.utils.llm_judge import LLMJudge


def run_single_query(
    query_data: Dict,
    graph,
    config: Dict[str, Any],
    llm_judge: LLMJudge,
    ontology_schema: dict,
    answer_quality_evaluator: AnswerQualityEvaluator,
    query_idx: int = None,
    total_queries: int = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    단일 질문 실행 및 평가 (공통 함수)

    Args:
        query_data: 질문 데이터 (test_queries.json 형식)
        graph: LangGraph 인스턴스
        config: 실험 설정 (name, description 포함)
        llm_judge: LLM Judge
        ontology_schema: 온톨로지 스키마
        answer_quality_evaluator: 답변 품질 평가자
        query_idx: 질문 인덱스 (1-based, 선택사항)
        total_queries: 전체 질문 수 (선택사항)
        verbose: 상세 출력 여부

    Returns:
        평가 결과 딕셔너리
    """
    query = query_data.get("query", query_data.get("user_query", ""))
    query_type = query_data.get("query_type", "factual")
    ground_truth = query_data.get("ground_truth", "")
    expected_entities = query_data.get("expected_entities", [])
    expected_property_groups = query_data.get("expected_property_groups", [])

    if verbose and query_idx is not None and total_queries is not None:
        print(f"\n{'='*80}")
        print(f"[{query_idx}/{total_queries}] Query: {query}")
        print(f"  - Type: {query_type}")
        if expected_entities:
            print(f"  - Expected Entities: {expected_entities}")
        if config.get("name"):
            print(f"  - Config: {config['name']}")
        print(f"{'='*80}")

    try:
        # LangGraph 실행
        start_time = time.time()

        # state 형식은 graph에 따라 다를 수 있음
        initial_state = {
            "query": query,
            "query_type": query_type,
            "entities": expected_entities,
            "executed_nodes": []
        }

        # test_config가 있으면 추가
        if "test_config" in config:
            initial_state["test_config"] = config["test_config"]
        elif any(key in config for key in ["semantic_expander", "aggregator_threads", "entity_boost_mode"]):
            from backend.ragas.ontology_evaluate.common_eval import build_test_config
            initial_state["test_config"] = build_test_config(config)

        state_output = graph.invoke(initial_state)
        execution_time = time.time() - start_time

        if verbose:
            print(f"  ✓ LangGraph 실행 완료 ({execution_time:.2f}s)")
            answer = state_output.get("answer", state_output.get("final_answer", "N/A"))
            print(f"  - Answer: {str(answer)[:100]}...")

        # 평가 실행
        eval_start = time.time()
        evaluation_result = evaluate_state(
            state_output=state_output,
            llm_judge=llm_judge,
            ontology_schema=ontology_schema,
            answer_quality_evaluator=answer_quality_evaluator,
            query=query,
            query_type=query_type,
            expected_property_groups=expected_property_groups,
            use_intent_aware=True
        )
        eval_time = time.time() - eval_start

        if verbose:
            print(f"  ✓ 평가 완료 ({eval_time:.2f}s)")
            if evaluation_result.get("intent_aware"):
                intent_score = evaluation_result["intent_aware"].get("intent_aware_score") or evaluation_result["intent_aware"].get("final_score", 0)
                print(f"  - Intent-Aware Score: {intent_score:.4f}")

        # 결과 구성
        result = {
            "query": query,
            "query_type": query_type,
            "experiment_name": config.get("name", "unknown"),
            "experiment_description": config.get("description", ""),
            "ground_truth": ground_truth,
            "expected_entities": expected_entities,
            "expected_property_groups": expected_property_groups,
            "answer": state_output.get("answer", state_output.get("final_answer", "")),
            "evidences": state_output.get("evidences", []),
            "execution_time": execution_time,
            "evaluation_time": eval_time,
            "raw_metrics": evaluation_result.get("raw_metrics", {}),
            "intent_aware": evaluation_result.get("intent_aware"),
            "llm_judge_quality": evaluation_result.get("llm_judge_quality"),
            "timestamp": datetime.now().isoformat()
        }

        return result

    except Exception as e:
        if verbose:
            print(f"  ✗ 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()

        return {
            "query": query,
            "query_type": query_type,
            "experiment_name": config.get("name", "unknown"),
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def calculate_metric_averages(results: List[Dict]) -> Dict[str, float]:
    """
    실험 결과 리스트에서 메트릭 평균 계산

    Args:
        results: 실험 결과 리스트

    Returns:
        메트릭별 평균 점수 딕셔너리
    """
    metrics = {
        "intent_aware_score": [],
        "tbox_consistency": [],
        "intent_preservation": [],
        "relation_coherence": [],
        "triple_validity": [],
        "evidence_diversity": [],
        "convergence_utilization": []
    }

    for result in results:
        if "error" in result:
            continue

        # Intent-Aware Score
        if result.get("intent_aware"):
            intent_score = result["intent_aware"].get("intent_aware_score") or result["intent_aware"].get("final_score")
            if intent_score is not None:
                metrics["intent_aware_score"].append(intent_score)

        # Raw Metrics
        raw = result.get("raw_metrics", {})
        if raw:
            metrics["tbox_consistency"].append(raw.get("tbox_consistency", 0))
            metrics["intent_preservation"].append(raw.get("intent_preservation", 0))
            metrics["relation_coherence"].append(raw.get("relation_coherence", 0))
            metrics["triple_validity"].append(raw.get("triple_validity", 0))
            metrics["evidence_diversity"].append(raw.get("evidence_diversity", 0))
            metrics["convergence_utilization"].append(raw.get("convergence_utilization", 0))

    # 평균 계산
    averages = {
        metric: sum(values) / len(values) if values else 0.0
        for metric, values in metrics.items()
    }

    return averages


def compare_experiment_results(
    baseline_results: List[Dict],
    experiment_results: List[Dict],
    baseline_name: str = "baseline",
    experiment_name: str = "experiment"
) -> Dict[str, Any]:
    """
    두 실험 결과 비교 분석

    Args:
        baseline_results: Baseline 실험 결과
        experiment_results: 비교할 실험 결과
        baseline_name: Baseline 이름 (출력용)
        experiment_name: 실험 이름 (출력용)

    Returns:
        비교 분석 결과
    """
    baseline_avg = calculate_metric_averages(baseline_results)
    experiment_avg = calculate_metric_averages(experiment_results)

    # 차이 계산 (experiment - baseline)
    differences = {
        metric: experiment_avg[metric] - baseline_avg[metric]
        for metric in baseline_avg.keys()
    }

    # 승/패/무 계산 (질문별)
    wins = 0
    losses = 0
    ties = 0

    # 결과를 query로 매칭
    baseline_dict = {r.get("query", ""): r for r in baseline_results}
    experiment_dict = {r.get("query", ""): r for r in experiment_results}

    for query in set(baseline_dict.keys()) & set(experiment_dict.keys()):
        baseline = baseline_dict[query]
        experiment = experiment_dict[query]

        if "error" in baseline or "error" in experiment:
            continue

        baseline_score = 0
        if baseline.get("intent_aware"):
            baseline_score = baseline["intent_aware"].get("intent_aware_score") or baseline["intent_aware"].get("final_score", 0)

        experiment_score = 0
        if experiment.get("intent_aware"):
            experiment_score = experiment["intent_aware"].get("intent_aware_score") or experiment["intent_aware"].get("final_score", 0)

        if experiment_score > baseline_score:
            wins += 1
        elif experiment_score < baseline_score:
            losses += 1
        else:
            ties += 1

    return {
        "baseline_name": baseline_name,
        "experiment_name": experiment_name,
        "baseline_averages": baseline_avg,
        "experiment_averages": experiment_avg,
        "differences": differences,
        "win_loss_tie": {
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "total": wins + losses + ties
        }
    }


def print_comparison_summary(comparison: Dict[str, Any]):
    """
    비교 결과 요약 출력

    Args:
        comparison: compare_experiment_results()의 반환값
    """
    baseline_name = comparison.get("baseline_name", "Baseline")
    experiment_name = comparison.get("experiment_name", "Experiment")
    
    print(f"\n{'='*80}")
    print(f"실험 결과 비교: {baseline_name} vs {experiment_name}")
    print(f"{'='*80}")

    print("\n[평균 점수]")
    print(f"{'메트릭':<30} {baseline_name:>15} {experiment_name:>15} {'차이(Δ)':>12}")
    print("-" * 80)

    baseline_avg = comparison["baseline_averages"]
    experiment_avg = comparison["experiment_averages"]
    diff = comparison["differences"]

    for metric in baseline_avg.keys():
        delta_str = f"{diff[metric]:+.4f}"
        print(f"{metric:<30} {baseline_avg[metric]:>15.4f} {experiment_avg[metric]:>15.4f} {delta_str:>12}")

    print("\n[질문별 승/패/무]")
    wlt = comparison["win_loss_tie"]
    print(f"  - 승 ({experiment_name} 우수): {wlt['wins']}개")
    print(f"  - 패 ({baseline_name} 우수): {wlt['losses']}개")
    print(f"  - 무승부: {wlt['ties']}개")
    print(f"  - 총 질문: {wlt['total']}개")

    if wlt['total'] > 0:
        win_rate = wlt['wins'] / wlt['total'] * 100
        print(f"  - {experiment_name} 승률: {win_rate:.1f}%")

    print(f"\n{'='*80}")


# =====================================================
# 병렬 실행 유틸리티
# =====================================================

def split_queries_into_batches(
    queries: List[Dict],
    batch_size: int = 20,
    num_batches: int = None
) -> List[List[Dict]]:
    """
    질문 리스트를 배치로 분할

    Args:
        queries: 질문 리스트
        batch_size: 배치 크기
        num_batches: 배치 개수 (None이면 batch_size로 자동 계산)

    Returns:
        배치 리스트
    """
    if num_batches is None:
        num_batches = (len(queries) + batch_size - 1) // batch_size

    batches = []
    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(queries))
        batch = queries[start_idx:end_idx]
        if batch:  # 빈 배치 제외
            batches.append(batch)

    return batches


def save_batch_files(
    batches: List[List[Dict]],
    output_dir: Path,
    prefix: str = "batch"
) -> List[Path]:
    """
    배치별 질문 파일 저장

    Args:
        batches: 배치 리스트
        output_dir: 출력 디렉토리
        prefix: 파일명 prefix

    Returns:
        저장된 파일 경로 리스트
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_files = []

    for i, batch in enumerate(batches, 1):
        batch_file = output_dir / f"{prefix}_{i}_queries.json"
        with open(batch_file, "w", encoding="utf-8") as f:
            import json
            json.dump(batch, f, ensure_ascii=False, indent=2)
        batch_files.append(batch_file)

    return batch_files


def launch_parallel_workers(
    batch_files: List[Path],
    worker_module: str,
    results_dir: Path,
    timestamp: str,
    project_root: Path,
    extra_args: List[str] = None
) -> Tuple[List[subprocess.Popen], List[Path]]:
    """
    병렬 worker 프로세스 실행

    Args:
        batch_files: 배치 파일 경로 리스트
        worker_module: worker 모듈 경로 (예: "backend.ragas.ontology_evaluate.experiments.worker")
        results_dir: 결과 저장 디렉토리
        timestamp: 타임스탬프
        project_root: 프로젝트 루트 경로
        extra_args: 추가 명령행 인자

    Returns:
        (프로세스 리스트, 로그 파일 리스트)
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    processes = []
    log_files = []

    for i, batch_file in enumerate(batch_files, 1):
        output_file = results_dir / f"batch_{i}_results_{timestamp}.json"
        log_file = results_dir / f"batch_{i}_log_{timestamp}.txt"

        log_files.append(log_file)

        cmd = [
            "nohup",
            sys.executable,
            "-m", worker_module,
            "--batch-file", str(batch_file),
            "--output", str(output_file),
            "--batch-num", str(i),
            "--timestamp", timestamp
        ]

        if extra_args:
            cmd.extend(extra_args)

        with open(log_file, "w") as log_f:
            process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                cwd=str(project_root)
            )

        processes.append(process)

    return processes, log_files


def print_parallel_execution_summary(
    processes: List[subprocess.Popen],
    log_files: List[Path],
    results_dir: Path,
    timestamp: str = None,
    merge_command: str = None
):
    """
    병렬 실행 요약 출력

    Args:
        processes: 프로세스 리스트
        log_files: 로그 파일 리스트
        results_dir: 결과 디렉토리
        timestamp: 타임스탬프
        merge_command: 결과 통합 명령어
    """
    print(f"{'='*80}")
    print("모든 프로세스 실행 완료!")
    print(f"{'='*80}\n")

    print("진행 상황 모니터링:")
    for i, log_file in enumerate(log_files, 1):
        print(f"  Batch {i}: tail -f {log_file}")

    print(f"\n프로세스 상태 확인:")
    for i, process in enumerate(processes, 1):
        print(f"  Batch {i} PID: {process.pid}")

    print(f"\n결과 파일 위치: {results_dir}")

    if merge_command:
        print(f"\n모든 프로세스가 완료되면 다음 명령어로 결과를 통합하세요:")
        print(f"  {merge_command}")


# =====================================================
# 고수준 병렬 실행 유틸리티
# =====================================================

def prepare_parallel_batches(
    items: List[Any],
    batch_size: int = 20,
    num_batches: int = None,
    output_dir: Path = None,
    prefix: str = "batch"
) -> Tuple[List[List[Any]], List[Path]]:
    """
    병렬 실행을 위한 배치 준비 (분할 + 파일 저장)

    Args:
        items: 분할할 아이템 리스트 (queries, configs 등)
        batch_size: 배치 크기
        num_batches: 배치 개수 (None이면 batch_size로 자동 계산)
        output_dir: 배치 파일 저장 디렉토리
        prefix: 파일명 prefix

    Returns:
        (배치 리스트, 배치 파일 경로 리스트)
    """
    batches = split_queries_into_batches(items, batch_size=batch_size, num_batches=num_batches)
    
    batch_files = []
    if output_dir:
        batch_files = save_batch_files(batches, output_dir, prefix=prefix)
    
    return batches, batch_files


def wait_for_processes(
    processes: List[subprocess.Popen],
    timeout: float = None,
    check_interval: float = 5.0
) -> Dict[int, bool]:
    """
    병렬 프로세스 완료 대기

    Args:
        processes: 프로세스 리스트
        timeout: 최대 대기 시간 (초, None이면 무한 대기)
        check_interval: 상태 확인 간격 (초)

    Returns:
        {PID: 성공 여부} 딕셔너리
    """
    import time
    
    start_time = time.time()
    results = {}
    
    while processes:
        if timeout and (time.time() - start_time) > timeout:
            print(f"⚠️  타임아웃 ({timeout}초) - 남은 프로세스 강제 종료")
            for process in processes:
                process.terminate()
            break
        
        for process in list(processes):
            if process.poll() is not None:  # 프로세스 종료됨
                results[process.pid] = process.returncode == 0
                processes.remove(process)
        
        if processes:
            time.sleep(check_interval)
    
    return results


def run_parallel_experiment(
    items: List[Any],
    worker_module: str,
    results_dir: Path,
    project_root: Path,
    batch_size: int = 20,
    num_batches: int = None,
    timestamp: str = None,
    extra_args: List[str] = None,
    batch_prefix: str = "batch",
    wait_for_completion: bool = False,
    merge_command: str = None,
    verbose: bool = True
) -> Tuple[List[subprocess.Popen], List[Path], List[List[Any]]]:
    """
    병렬 실험 실행 (고수준 함수)

    배치 분할, 파일 저장, 프로세스 실행, 요약 출력을 한 번에 처리

    Args:
        items: 실험할 아이템 리스트 (queries, configs 등)
        worker_module: worker 모듈 경로
        results_dir: 결과 저장 디렉토리
        project_root: 프로젝트 루트 경로
        batch_size: 배치 크기
        num_batches: 배치 개수 (None이면 batch_size로 자동 계산)
        timestamp: 타임스탬프 (None이면 자동 생성)
        extra_args: 추가 명령행 인자
        batch_prefix: 배치 파일 prefix
        wait_for_completion: 프로세스 완료 대기 여부
        merge_command: 결과 통합 명령어
        verbose: 상세 출력 여부

    Returns:
        (프로세스 리스트, 로그 파일 리스트, 배치 리스트)
    """
    from datetime import datetime
    
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if verbose:
        print(f"\n{'='*80}")
        print("병렬 실험 실행")
        print(f"{'='*80}")
        print(f"아이템 수: {len(items)}개")
        print(f"배치 크기: {batch_size}")
        print(f"Worker: {worker_module}")
        print(f"결과 디렉토리: {results_dir}")
        print(f"{'='*80}\n")
    
    # 배치 준비
    if verbose:
        print("📦 배치 준비 중...")
    
    batches, batch_files = prepare_parallel_batches(
        items=items,
        batch_size=batch_size,
        num_batches=num_batches,
        output_dir=results_dir.parent if results_dir else None,
        prefix=batch_prefix
    )
    
    if verbose:
        for i, batch in enumerate(batches, 1):
            print(f"  Batch {i}: {len(batch)}개 아이템")
    
    # 병렬 프로세스 실행
    if verbose:
        print(f"\n🚀 병렬 프로세스 실행 중... ({len(batches)}개)")
    
    processes, log_files = launch_parallel_workers(
        batch_files=batch_files,
        worker_module=worker_module,
        results_dir=results_dir,
        timestamp=timestamp,
        project_root=project_root,
        extra_args=extra_args
    )
    
    if verbose:
        for i, (process, batch_file) in enumerate(zip(processes, batch_files), 1):
            print(f"  ✓ Batch {i} 시작 (PID: {process.pid})")
            print(f"    입력: {batch_file.name}")
            print(f"    로그: {log_files[i-1].name}")
    
    # 프로세스 완료 대기
    if wait_for_completion:
        if verbose:
            print(f"\n⏳ 프로세스 완료 대기 중...")
        results = wait_for_processes(processes)
        if verbose:
            success_count = sum(1 for success in results.values() if success)
            print(f"  완료: {success_count}/{len(results)}개 성공")
    
    # 요약 출력
    if verbose:
        print_parallel_execution_summary(
            processes=processes,
            log_files=log_files,
            results_dir=results_dir,
            timestamp=timestamp,
            merge_command=merge_command
        )
    
    return processes, log_files, batches


# =====================================================
# 데이터 로드 및 초기화 유틸리티
# =====================================================

def load_queries(queries_path: str) -> List[Dict[str, Any]]:
    """
    질문 데이터 로드 (공통 함수)

    Args:
        queries_path: 질문 파일 경로

    Returns:
        질문 데이터 리스트
    """
    with open(queries_path, "r", encoding="utf-8") as f:
        import json
        return json.load(f)


def initialize_evaluators():
    """
    평가자 초기화 (공통 함수)

    Returns:
        (llm_judge, answer_quality_evaluator, ontology_schema) 튜플
    """
    llm_judge = LLMJudge()
    answer_quality_evaluator = AnswerQualityEvaluator(llm_judge)
    ontology_schema = get_ontology_schema()
    return llm_judge, answer_quality_evaluator, ontology_schema


# =====================================================
# 결과 저장 유틸리티
# =====================================================

def create_summary_from_results(
    results: List[Dict],
    queries_data: List[Dict] = None
) -> List[Dict]:
    """
    실험 결과에서 Summary 형식 생성 (공통 함수)

    Args:
        results: 실험 결과 리스트
        queries_data: 질문 데이터 (선택사항, query_type 찾기용)

    Returns:
        Summary 형식 결과 리스트
    """
    summary_results = []
    query_map = {q.get("query", ""): q for q in (queries_data or [])}

    for idx, result in enumerate(results):
        # query_type 찾기
        query = result.get("query", "")
        query_type = result.get("query_type", "")
        if not query_type and query in query_map:
            query_type = query_map[query].get("query_type", "unknown")
        elif not query_type and queries_data:
            query_idx = idx % len(queries_data)
            query_type = queries_data[query_idx].get("query_type", "unknown")

        summary_item = {
            "experiment_name": result.get("experiment_name", ""),
            "description": result.get("description", ""),
            "query": query,
            "query_type": query_type,
            "success": result.get("success", False),
            "execution_time": result.get("execution_time", 0.0),
            "config": result.get("config", {}),
        }

        if result.get("success") and result.get("state_output"):
            state = result.get("state_output", {})
            metrics = result.get("metrics", {})

            # 기본 정보
            summary_item["final_answer"] = state.get("final_answer", state.get("answer", ""))

            # 엔티티 개수
            summary_item["num_extracted_entities"] = len(state.get("extracted_entities", []))
            summary_item["num_expanded_entities"] = len(state.get("expanded_entities", []))

            # Evidence 개수
            summary_item["num_evidences"] = len(state.get("evidences", []))

            # Convergence nodes 개수
            convergence_tree = state.get("convergence_triple_tree", {})
            if isinstance(convergence_tree, dict):
                summary_item["num_convergence_nodes"] = len(convergence_tree.get("nodes", []))
            else:
                summary_item["num_convergence_nodes"] = len(state.get("convergence_nodes", []))

            # 메트릭 점수
            if metrics:
                summary_item["raw_metrics"] = metrics.get("raw_metrics", {})

                # Intent-aware final score
                intent_aware = metrics.get("intent_aware", {})
                if intent_aware:
                    summary_item["intent_aware_score"] = intent_aware.get("final_score", intent_aware.get("intent_aware_score", 0.0))
                    summary_item["weighted_metrics"] = intent_aware.get("weighted_metrics", {})
                else:
                    # Fallback: raw metrics 평균
                    raw_scores = list(metrics.get("raw_metrics", {}).values())
                    summary_item["intent_aware_score"] = sum(raw_scores) / len(raw_scores) if raw_scores else 0.0
                    summary_item["weighted_metrics"] = {}

                # LLM Judge 품질 점수
                summary_item["llm_judge_quality"] = result.get("llm_judge_quality") or metrics.get("llm_judge_quality")
            else:
                summary_item["raw_metrics"] = {}
                summary_item["intent_aware_score"] = 0.0
                summary_item["weighted_metrics"] = {}
        else:
            # 실패한 경우
            summary_item["error"] = result.get("error", "Unknown error")
            summary_item["final_answer"] = ""
            summary_item["num_extracted_entities"] = 0
            summary_item["num_expanded_entities"] = 0
            summary_item["num_evidences"] = 0
            summary_item["num_convergence_nodes"] = 0
            summary_item["raw_metrics"] = {}
            summary_item["intent_aware_score"] = 0.0
            summary_item["weighted_metrics"] = {}

        summary_results.append(summary_item)

    return summary_results


def save_experiment_results(
    results: List[Dict],
    output_dir: Path,
    group_name: str,
    experiment_type: str = "experiment",
    queries_data: List[Dict] = None
):
    """
    실험 결과를 Full + Summary 형식으로 저장 (공통 함수)

    Args:
        results: 실험 결과 리스트
        output_dir: 출력 디렉토리
        group_name: 실험 그룹명
        experiment_type: 실험 타입 (예: "isolation", "ablation", "grid_search")
        queries_data: 질문 데이터 (Summary 생성용, 선택사항)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Full 결과 저장
    full_file = output_dir / f"{group_name}_{experiment_type}_full.json"
    with open(full_file, "w", encoding="utf-8") as f:
        import json
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Full 결과: {full_file}")

    # 2. Summary 결과 생성 및 저장
    summary_results = create_summary_from_results(results, queries_data)
    summary_file = output_dir / f"{group_name}_{experiment_type}_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        import json
        json.dump(summary_results, f, ensure_ascii=False, indent=2)
    print(f"✓ Summary: {summary_file}")


def run_single_config_experiment(
    config: Dict[str, Any],
    queries: List[Dict],
    graph,
    llm_judge: LLMJudge,
    ontology_schema: dict,
    answer_quality_evaluator: AnswerQualityEvaluator,
    config_idx: int = 0,
    total_configs: int = 1,
    group_name: str = "",
    verbose: bool = True,
    state_key: str = "query"
) -> List[Dict[str, Any]]:
    """
    단일 설정으로 모든 질문 실행 및 평가 (통합 함수)

    Args:
        config: 실험 설정
        queries: 질문 리스트
        graph: LangGraph 인스턴스
        llm_judge: LLM Judge
        ontology_schema: 온톨로지 스키마
        answer_quality_evaluator: 답변 품질 평가자
        config_idx: 설정 인덱스
        total_configs: 전체 설정 개수
        group_name: 그룹 이름 (출력용)
        verbose: 상세 출력 여부
        state_key: state의 query 키 ("query" 또는 "user_query")

    Returns:
        실험 결과 리스트
    """
    from backend.ragas.ontology_evaluate.common_eval import build_test_config, evaluate_state
    import time

    config_name = config.get("name", f"config_{config_idx}")
    config_description = config.get("description", "")
    test_config = build_test_config(config)

    if verbose:
        print(f"\n{'='*70}")
        if group_name:
            print(f"[{group_name}] 설정 {config_idx+1}/{total_configs}: {config_name}")
        else:
            print(f"설정 {config_idx+1}/{total_configs}: {config_name}")
        print(f"{'='*70}")

        # 설정 정보 출력
        se_config = config.get('semantic_expander', {})
        if se_config:
            print(f"  SE: temporal={se_config.get('temporal')}, "
                  f"causal={se_config.get('causal_chain')}, "
                  f"pgvector={se_config.get('pgvector')}")

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
        query = query_data.get("query", query_data.get("user_query", ""))
        query_type = query_data.get("query_type", "factual")
        expected_property_groups = query_data.get("expected_property_groups", [])

        if verbose:
            print(f"\n  [{q_idx+1}/{len(queries)}] {query[:50]}...")

        q_start = time.time()

        try:
            # LangGraph 실행
            state = {
                state_key: query,
                "test_config": test_config
            }
            state_output = graph.invoke(state)

            # 평가
            if verbose:
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

            final_score = metrics["intent_aware"].get("final_score", 0.0) if metrics.get("intent_aware") else 0.0
            llm_judge_quality = metrics.get("llm_judge_quality")
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
                    "raw_metrics": metrics.get("raw_metrics", {}),
                    "intent_aware": metrics.get("intent_aware"),
                    "final_score": final_score
                },
                "llm_judge_quality": llm_judge_quality
            }

            if verbose:
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
            if verbose:
                print(f"    ✗ Error: {str(e)[:100]}")

        flat_results.append(result)

    config_elapsed = time.time() - config_start

    # 통계 출력
    if verbose:
        success_count = sum(1 for r in flat_results if r.get("success"))
        if success_count > 0:
            scores = [r["metrics"]["final_score"] for r in flat_results if r.get("success") and r.get("metrics")]
            mean_score = sum(scores) / len(scores) if scores else 0.0
            print(f"\n  Summary: mean={mean_score:.4f}, success={success_count}/{len(queries)}, time={config_elapsed:.1f}s")

    return flat_results

