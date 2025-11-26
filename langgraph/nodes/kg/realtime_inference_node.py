"""
Realtime Inference Node

What-if 시나리오 실시간 추론
1. 자연어 → 가상 트리플 생성
2. 실시간 추론 API 호출
"""

import os
import requests
from langgraph.state import GraphState

API_URL = os.getenv("INFERENCE_API_URL", "http://localhost:8001")


def realtime_inference_node(state: GraphState) -> GraphState:
    """실시간 SWRL 추론"""

    query = state.get("query", "").lower()

    # 1. 가상 트리플 생성 (베이스라인: 하드코딩)
    hypothetical = _generate_hypothetical(query)

    # 2. API 호출
    payload = {
        "base_ontology": "test_basic.owl",
        "base_instances": ["test_scenario_all.ttl"],
        "rules": "test_inference.rules",
        "hypothetical_triples": hypothetical,
        "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 50"
    }

    try:
        endpoint = f"{API_URL}/what-if" if hypothetical else f"{API_URL}/infer"
        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        # 3. 결과 정규화
        kg_results = []
        if "results" in result:
            bindings = result.get("results", {}).get("results", {}).get("bindings", [])
            kg_results = [
                {k: v.get("value") for k, v in row.items()}
                for row in bindings
            ]

        return {
            **state,
            "kg_results": kg_results,
            "executor": "realtime"
        }

    except Exception as e:
        raise RuntimeError(f"실시간 추론 API 실패: {e}")


def _generate_hypothetical(query: str) -> list[str]:
    """자연어 → 가상 트리플 (베이스라인: 하드코딩)"""

    if "이순신" in query and "없었다면" in query:
        return [
            "test:YiSunSin test:died test:EarlyDeath .",
            "test:ImjinWar test:outcome \"defeat\" ."
        ]

    return []  # 기본: 일반 추론
