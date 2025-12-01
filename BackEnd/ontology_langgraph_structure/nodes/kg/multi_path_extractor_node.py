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

    # leadsTo 관계 수집 (다양한 변수명 지원)
    for binding in bindings:
        # 원인 추출 (cause, subject, s 등 다양한 변수명 지원)
        cause_binding = (
            binding.get("cause") or 
            binding.get("subject") or 
            binding.get("s") or 
            binding.get("entity") or
            {}
        )
        cause = cause_binding.get("value", "").split("#")[-1] if cause_binding else ""
        
        # 라벨이 있으면 사용
        cause_label = (
            binding.get("causeLabel") or 
            binding.get("subjectLabel") or 
            binding.get("sLabel") or
            {}
        )
        cause_name = cause_label.get("value", cause) if cause_label else cause
        
        # 결과 추출 (effect, object, o 등 다양한 변수명 지원)
        effect_binding = (
            binding.get("effect") or 
            binding.get("object") or 
            binding.get("o") or
            {}
        )
        effect = effect_binding.get("value", "").split("#")[-1] if effect_binding else ""
        
        # 라벨이 있으면 사용
        effect_label = (
            binding.get("effectLabel") or 
            binding.get("objectLabel") or 
            binding.get("oLabel") or
            {}
        )
        effect_name = effect_label.get("value", effect) if effect_label else effect

        if cause and effect:
            paths.append({
                "type": "causal",
                "chain": [cause_name, effect_name],
                "weight": base_weight,
                "description": f"{cause_name} → {effect_name}"
            })

    return paths[:10]  # 상위 10개


def extract_person_paths(bindings: list, base_weight: float) -> list:
    """인물 관계 추출"""
    paths = []

    for binding in bindings:
        # 인물 추출 (다양한 변수명 지원)
        person_binding = (
            binding.get("person") or 
            binding.get("entity") or 
            binding.get("s") or
            {}
        )
        person = person_binding.get("value", "").split("#")[-1] if person_binding else ""
        
        # 라벨
        person_label = (
            binding.get("personLabel") or 
            binding.get("entityLabel") or 
            binding.get("sLabel") or
            {}
        )
        person_name = person_label.get("value", person) if person_label else person
        
        # 이벤트/값 추출
        event_binding = (
            binding.get("event") or 
            binding.get("value") or 
            binding.get("o") or
            {}
        )
        event = event_binding.get("value", "").split("#")[-1] if event_binding else ""
        
        # 역할
        role_binding = binding.get("role") or binding.get("property") or {}
        role = role_binding.get("value", "") if role_binding else ""

        if person and event:
            paths.append({
                "type": "person",
                "person": person_name,
                "event": event,
                "role": role,
                "weight": base_weight,
                "description": f"{person_name} - {event}" + (f" ({role})" if role else "")
            })

    return paths[:10]


def extract_temporal_paths(bindings: list, base_weight: float) -> list:
    """시대 배경 추출"""
    paths = []

    for binding in bindings:
        # 이벤트/엔티티 추출 (다양한 변수명 지원)
        event_binding = (
            binding.get("event") or 
            binding.get("entity") or 
            binding.get("s") or
            {}
        )
        event = event_binding.get("value", "").split("#")[-1] if event_binding else ""
        
        # 라벨
        event_label = (
            binding.get("eventLabel") or 
            binding.get("entityLabel") or 
            binding.get("sLabel") or
            {}
        )
        event_name = event_label.get("value", event) if event_label else event
        
        # 연도
        year_binding = binding.get("year") or binding.get("date") or {}
        year = year_binding.get("value", "") if year_binding else ""
        
        # 컨텍스트
        context_binding = binding.get("context") or binding.get("description") or {}
        context = context_binding.get("value", "") if context_binding else ""

        if event and year:
            paths.append({
                "type": "temporal",
                "event": event_name,
                "year": year,
                "context": context,
                "weight": base_weight,
                "description": f"{year}년: {event_name}" + (f" ({context})" if context else "")
            })

    return paths[:10]


def extract_pattern_paths(bindings: list, base_weight: float) -> list:
    """패턴 추출"""
    paths = []

    for binding in bindings:
        # 엔티티 추출 (다양한 변수명 지원)
        e1_binding = (
            binding.get("e1") or 
            binding.get("entity") or 
            binding.get("s") or
            {}
        )
        e1 = e1_binding.get("value", "").split("#")[-1] if e1_binding else ""
        
        e1_label = (
            binding.get("e1Label") or 
            binding.get("entityLabel") or 
            binding.get("sLabel") or
            {}
        )
        e1_name = e1_label.get("value", e1) if e1_label else e1
        
        e2_binding = binding.get("e2") or binding.get("o") or {}
        e2 = e2_binding.get("value", "").split("#")[-1] if e2_binding else ""
        
        # 패턴
        pattern_binding = binding.get("pattern") or binding.get("p") or {}
        pattern = pattern_binding.get("value", "") if pattern_binding else ""

        if e1:
            paths.append({
                "type": "pattern",
                "events": [e1_name, e2] if e2 else [e1_name],
                "pattern": pattern,
                "weight": base_weight,
                "description": f"{e1_name} ↔ {e2}" + (f" ({pattern})" if pattern else "") if e2 else e1_name
            })

    return paths[:10]


def extract_motive_paths(bindings: list, base_weight: float) -> list:
    """동기 분석 추출"""
    paths = []

    for binding in bindings:
        # 인물/엔티티 추출
        person_binding = (
            binding.get("person") or 
            binding.get("entity") or 
            binding.get("s") or
            {}
        )
        person = person_binding.get("value", "").split("#")[-1] if person_binding else ""
        
        person_label = (
            binding.get("personLabel") or 
            binding.get("entityLabel") or 
            binding.get("sLabel") or
            {}
        )
        person_name = person_label.get("value", person) if person_label else person
        
        # 동기
        motive_binding = (
            binding.get("motive") or 
            binding.get("value") or 
            binding.get("o") or
            {}
        )
        motive = motive_binding.get("value", "") if motive_binding else ""
        
        # 행동
        action_binding = binding.get("action") or {}
        action = action_binding.get("value", "").split("#")[-1] if action_binding else ""

        if person and motive:
            paths.append({
                "type": "motive",
                "person": person_name,
                "motive": motive,
                "action": action,
                "weight": base_weight,
                "description": f"{person_name}: {motive}" + (f" → {action}" if action else "")
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
