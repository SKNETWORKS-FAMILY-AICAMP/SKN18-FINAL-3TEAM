"""
Parallel Inference Executor Node

5개의 추론 Thread를 병렬로 실행하여 다양한 관점의 근거 수집
- ThreadPoolExecutor로 병렬 처리
- 각 Thread마다 독립적인 Jena Reasoner API 호출
- 추론 결과를 TTL 형식으로 저장
"""

import os
import time
import requests
import concurrent.futures
from datetime import datetime
from pathlib import Path
from state import GraphState
from utils.inference_triple_generator import InferenceTripleGenerator


API_URL = os.getenv("INFERENCE_API_URL", "http://localhost:8001")
SAVE_INFERENCE_TRIPLES = os.getenv("SAVE_INFERENCE_TRIPLES", "true").lower() == "true"
INFERENCE_OUTPUT_DIR = os.getenv("INFERENCE_OUTPUT_DIR", "./inference_results")


def parallel_inference_executor_node(state: GraphState) -> GraphState:
    """5개 Thread 병렬 추론 실행"""

    multi_queries = state.get("multi_queries", {})
    hypothetical_triples = state.get("hypothetical_triples", [])
    query_type = state.get("query_type", "causal")

    print(f"\n⚡ 병렬 추론 시작 ({len(multi_queries)}개 Thread)")
    start_time = time.time()

    # ThreadPoolExecutor로 병렬 실행
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # 각 Thread별 Future 생성
        futures = {
            executor.submit(
                execute_inference_thread,
                thread_type=thread_type,
                sparql=sparql,
                hypothetical=hypothetical_triples,
                query_type=query_type
            ): thread_type
            for thread_type, sparql in multi_queries.items()
        }

        # 결과 수집
        results = {}
        for future in concurrent.futures.as_completed(futures):
            thread_type = futures[future]
            try:
                result = future.result(timeout=30)
                results[thread_type] = result
                print(f"   ✅ {thread_type}: {result['status']} ({len(result.get('bindings', []))}개 결과)")
            except concurrent.futures.TimeoutError:
                print(f"   ⏱️ {thread_type}: 시간 초과 (30초)")
                results[thread_type] = {"status": "timeout", "bindings": []}
            except Exception as e:
                print(f"   ❌ {thread_type}: 실패 - {e}")
                results[thread_type] = {"status": "error", "bindings": [], "error": str(e)}

    elapsed = time.time() - start_time
    print(f"⚡ 병렬 추론 완료 ({elapsed:.1f}초)")

    # 총 결과 통계
    total_bindings = sum(len(r.get("bindings", [])) for r in results.values())
    print(f"   - 총 추론 결과: {total_bindings}개")

    # 추론 결과를 TTL로 저장 (옵션)
    inference_ttl_path = None
    if SAVE_INFERENCE_TRIPLES and total_bindings > 0:
        try:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            inference_ttl_path = save_inference_results_as_ttl(
                results=results,
                query=state.get("query", ""),
                session_id=session_id,
                execution_time=elapsed
            )
            print(f"   💾 추론 결과 저장: {inference_ttl_path}")
        except Exception as e:
            print(f"   ⚠️ 추론 결과 저장 실패: {e}")

    return {
        **state,
        "parallel_inference_results": results,
        "execution_time": elapsed,
        "inference_ttl_path": inference_ttl_path,
        "executed_nodes": state.get("executed_nodes", []) + ["parallel_inference_executor"]
    }


def save_inference_results_as_ttl(
    results: dict,
    query: str,
    session_id: str,
    execution_time: float
) -> str:
    """
    추론 결과를 TTL 파일로 저장

    Args:
        results: 병렬 추론 결과
        query: 사용자 질문
        session_id: 세션 ID
        execution_time: 실행 시간

    Returns:
        저장된 파일 경로
    """
    # 출력 디렉토리 생성
    output_dir = Path(INFERENCE_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 생성
    output_path = output_dir / f"inference_{session_id}.ttl"

    # Triple 생성기 초기화
    generator = InferenceTripleGenerator()

    # TTL 생성 및 저장
    generator.save_triples_to_file(
        inference_results=results,
        output_path=str(output_path),
        session_id=session_id
    )

    # 메타데이터 추가
    metadata_ttl = generator.generate_inference_metadata(
        inference_results=results,
        session_id=session_id,
        query=query,
        execution_time=execution_time
    )

    # 메타데이터를 파일에 추가
    with open(output_path, "a", encoding="utf-8") as f:
        f.write("\n\n")
        f.write(metadata_ttl)

    return str(output_path)


def execute_inference_thread(thread_type: str, sparql: str, hypothetical: list, query_type: str) -> dict:
    """개별 Thread에서 Jena Reasoner API 호출"""

    # What-if인 경우 가상 트리플 포함
    use_hypothetical = (query_type == "what_if" and thread_type in ["causal", "person", "temporal"])

    # Rules 파일 선택
    rules_file = f"{thread_type}_inference.rules"

    # API 요청 payload
    if use_hypothetical and hypothetical:
        # What-if API 엔드포인트
        payload = {
            "base_ontology": "korean_history.owl",
            "base_instances": [],  # 빈 리스트 → 모든 .ttl 파일 자동 로드
            "rules": rules_file,
            "hypothetical_triples": hypothetical,
            "query": sparql
        }
        endpoint = f"{API_URL}/what-if"
    else:
        # 일반 추론 API 엔드포인트
        payload = {
            "ontology": "korean_history.owl",
            "instances": [],  # 빈 리스트 → 모든 .ttl 파일 자동 로드
            "rules": rules_file
        }
        endpoint = f"{API_URL}/infer"

    try:
        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        # SPARQL 결과 추출
        if "results" in result:
            bindings = result.get("results", {}).get("results", {}).get("bindings", [])
        else:
            bindings = []

        return {
            "status": "success",
            "bindings": bindings,
            "fuseki_endpoint": result.get("fuseki_endpoint"),
            "thread_type": thread_type
        }

    except requests.exceptions.Timeout:
        return {"status": "timeout", "bindings": [], "thread_type": thread_type}
    except Exception as e:
        return {"status": "error", "bindings": [], "error": str(e), "thread_type": thread_type}
