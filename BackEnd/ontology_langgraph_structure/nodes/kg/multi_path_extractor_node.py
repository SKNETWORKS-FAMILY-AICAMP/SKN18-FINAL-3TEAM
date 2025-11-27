"""
Multi-Path Extractor Node

5개 Thread의 추론 결과에서 각각 경로 추출
- Thread별로 서로 다른 경로 추출 로직 적용
- 각 Thread의 가중치 반영
"""

from state import GraphState


def multi_path_extractor_node(state: GraphState) -> GraphState:
    """5개 Thread별 추론 경로 추출"""

    parallel_results = state.get("parallel_inference_results", {})
    thread_weights = state.get("thread_weights", {})

    print(f"\n🔍 다중 경로 추출 중... ({len(parallel_results)}개 Thread)")

    inference_paths = {}

    for thread_type, result in parallel_results.items():
        bindings = result.get("bindings", [])

        if not bindings:
            print(f"   ⚠️ {thread_type}: 결과 없음")
            inference_paths[thread_type] = []
            continue

        # Thread별 경로 추출
        if thread_type == "causal":
            paths = extract_causal_paths(bindings, thread_weights.get(thread_type, 0.2))
        elif thread_type == "person":
            paths = extract_person_paths(bindings, thread_weights.get(thread_type, 0.2))
        elif thread_type == "temporal":
            paths = extract_temporal_paths(bindings, thread_weights.get(thread_type, 0.2))
        elif thread_type == "pattern":
            paths = extract_pattern_paths(bindings, thread_weights.get(thread_type, 0.2))
        elif thread_type == "motive":
            paths = extract_motive_paths(bindings, thread_weights.get(thread_type, 0.2))
        elif thread_type == "comparison":
            paths = extract_comparison_paths(bindings, thread_weights.get(thread_type, 0.2))
        else:
            paths = []

        inference_paths[thread_type] = paths

        print(f"   ✅ {thread_type}: {len(paths)}개 경로 추출 (가중치: {thread_weights.get(thread_type, 0):.0%})")

    return {
        **state,
        "inference_paths": inference_paths,
        "executed_nodes": state.get("executed_nodes", []) + ["multi_path_extractor"]
    }


def extract_causal_paths(bindings: list, base_weight: float) -> list:
    """인과관계 체인 추출"""
    paths = []

    # leadsTo 관계 수집
    for binding in bindings:
        cause = binding.get("cause", {}).get("value", "").split("#")[-1]
        effect = binding.get("effect", {}).get("value", "").split("#")[-1]

        if cause and effect:
            paths.append({
                "type": "causal",
                "chain": [cause, effect],
                "weight": base_weight,
                "description": f"{cause} → {effect}"
            })

    return paths[:10]  # 상위 10개


def extract_person_paths(bindings: list, base_weight: float) -> list:
    """인물 관계 추출"""
    paths = []

    for binding in bindings:
        person = binding.get("person", {}).get("value", "").split("#")[-1]
        event = binding.get("event", {}).get("value", "").split("#")[-1]
        role = binding.get("role", {}).get("value", "")

        if person and event:
            paths.append({
                "type": "person",
                "person": person,
                "event": event,
                "role": role,
                "weight": base_weight,
                "description": f"{person} - {event}" + (f" ({role})" if role else "")
            })

    return paths[:10]


def extract_temporal_paths(bindings: list, base_weight: float) -> list:
    """시대 배경 추출"""
    paths = []

    for binding in bindings:
        event = binding.get("event", {}).get("value", "").split("#")[-1]
        year = binding.get("year", {}).get("value", "")
        context = binding.get("context", {}).get("value", "")

        if event and year:
            paths.append({
                "type": "temporal",
                "event": event,
                "year": year,
                "context": context,
                "weight": base_weight,
                "description": f"{year}년: {event}" + (f" ({context})" if context else "")
            })

    return paths[:10]


def extract_pattern_paths(bindings: list, base_weight: float) -> list:
    """패턴 추출"""
    paths = []

    for binding in bindings:
        e1 = binding.get("e1", {}).get("value", "").split("#")[-1]
        e2 = binding.get("e2", {}).get("value", "").split("#")[-1]
        pattern = binding.get("pattern", {}).get("value", "")

        if e1 and e2:
            paths.append({
                "type": "pattern",
                "events": [e1, e2],
                "pattern": pattern,
                "weight": base_weight,
                "description": f"{e1} ↔ {e2}" + (f" ({pattern})" if pattern else "")
            })

    return paths[:10]


def extract_motive_paths(bindings: list, base_weight: float) -> list:
    """동기 분석 추출"""
    paths = []

    for binding in bindings:
        person = binding.get("person", {}).get("value", "").split("#")[-1]
        motive = binding.get("motive", {}).get("value", "")
        action = binding.get("action", {}).get("value", "").split("#")[-1]

        if person and motive:
            paths.append({
                "type": "motive",
                "person": person,
                "motive": motive,
                "action": action,
                "weight": base_weight,
                "description": f"{person}: {motive}" + (f" → {action}" if action else "")
            })

    return paths[:10]


def extract_comparison_paths(bindings: list, base_weight: float) -> list:
    """실제 vs 가상 비교 추출 (What-if용)"""
    paths = []

    for binding in bindings:
        event = binding.get("event", {}).get("value", "").split("#")[-1]
        actual = binding.get("actual", {}).get("value", "")
        hypothetical = binding.get("hypothetical", {}).get("value", "")

        if event and (actual or hypothetical):
            paths.append({
                "type": "comparison",
                "event": event,
                "actual": actual,
                "hypothetical": hypothetical,
                "weight": base_weight,
                "description": f"{event}: 실제({actual}) vs 가상({hypothetical})"
            })

    return paths[:10]
