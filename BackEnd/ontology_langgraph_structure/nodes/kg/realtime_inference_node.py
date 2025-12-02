"""
Realtime Inference Node

Jena Reasoner API를 호출하여 실시간 추론 수행
- What-if: 가상 트리플 + 기존 데이터 → 추론
- 일반: 기존 데이터만 → 추론
"""

import os
import sys
import requests
from pathlib import Path

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from state import GraphState

API_URL = os.getenv("INFERENCE_API_URL", "http://localhost:8001")


def realtime_inference_node(state: GraphState) -> GraphState:
    """Jena Reasoner API 호출"""

    query_type = state.get("query_type", "causal")
    hypothetical_triples = state.get("hypothetical_triples", [])
    sparql_query = state.get("sparql_query", "")

    # 추론 요청 payload
    if query_type == "what_if" and hypothetical_triples:
        # What-if: 가상 트리플 포함
        payload = {
            "base_ontology": "korean_history.owl",
            "base_instances": [],  # 빈 리스트면 자동으로 모든 .ttl 파일 사용
            "rules": "all_rules.rules",
            "hypothetical_triples": hypothetical_triples,
            "query": sparql_query or "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 100"
        }
        endpoint = f"{API_URL}/what-if"
        print(f"🔮 What-if 추론 실행 (가상 트리플 {len(hypothetical_triples)}개)")

    else:
        # 일반 추론
        payload = {
            "ontology": "korean_history.owl",
            "instances": [],  # 빈 리스트면 자동으로 모든 .ttl 파일 사용
            "rules": "all_rules.rules"
        }
        endpoint = f"{API_URL}/infer"
        print(f"📊 일반 추론 실행")

    try:
        response = requests.post(endpoint, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        print(f"✅ 추론 완료: {result.get('status')}")

        # 결과 정규화
        inference_results = {
            "status": result.get("status"),
            "fuseki_endpoint": result.get("fuseki_endpoint"),
            "raw_results": result.get("results", {})
        }

        # SPARQL 결과 추출
        if "results" in result:
            bindings = result.get("results", {}).get("results", {}).get("bindings", [])
            inference_results["bindings"] = bindings
            print(f"   - 추론된 트리플 수: {len(bindings)}")

    except requests.exceptions.Timeout:
        print(f"⚠️ 추론 시간 초과 (60초)")
        inference_results = {"status": "timeout", "bindings": []}

    except Exception as e:
        print(f"❌ 추론 API 호출 실패: {e}")
        inference_results = {"status": "error", "error": str(e), "bindings": []}

    return {
        **state,
        "inference_results": inference_results,
        "executed_nodes": state.get("executed_nodes", []) + ["realtime_inference"]
    }
