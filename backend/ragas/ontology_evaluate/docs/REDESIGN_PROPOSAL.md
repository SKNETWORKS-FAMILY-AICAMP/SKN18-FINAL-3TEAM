# 향후 계획 및 개선 제안

> **상태**: ✅ Phase 1 완료 - Intent-aware 평가 구현 완료 (2025-12-24)

## 완료된 항목

### ✅ Intent-Aware 평가 시스템

- Query type별 가중치 프리셋 구현
- `IntentAwareEvaluator` 클래스 구현
- `run_baseline.py`에 통합
- 40개 테스트 쿼리 검증 완료
- 사용 가이드 작성 (GUIDE.md에 통합됨)

자세한 내용은 [GUIDE.md](./GUIDE.md)의 "Step 7: Intent-Aware 평가 실행" 섹션을 참고하세요.

---

## 향후 계획

### 🔜 Phase 2: Thinking Trace 구현

**목표**: 노드별 추론 과정을 기록하여 향후 "thinking 모드" UI에 표시

**필요 작업**:
1. `GraphState`에 `thinking_trace` 필드 추가
2. `test_config`에 `enable_thinking_trace` 옵션 추가
3. 각 노드에 `@trace_thinking_process` 데코레이터 적용
4. Frontend에서 thinking trace 시각화

**예상 작업량**: 2~3일

**우선순위**: Medium (Intent-aware 평가 완료 후)

**구현 예시**:

```python
# backend/langgraph_fuseki/utils/thinking_trace.py

from typing import Dict, Any, Callable
import time
from functools import wraps

def trace_thinking_process(node_name: str):
    """
    노드 실행 과정을 thinking_trace에 기록하는 데코레이터
    
    Usage:
        @trace_thinking_process("semantic_expander")
        def semantic_expander_node(state: GraphState) -> GraphState:
            ...
    """
    def decorator(node_func: Callable):
        @wraps(node_func)
        def wrapper(state: GraphState) -> GraphState:
            test_config = state.get("test_config", {})
            enable_trace = test_config.get("enable_thinking_trace", False)
            
            if not enable_trace:
                return node_func(state)
            
            # Thinking 모드 ON: 추론 과정 기록
            step_start = time.time()
            input_snapshot = {...}
            output_state = node_func(state)
            output_snapshot = {...}
            
            trace_entry = {
                "step": len(state.get("thinking_trace", [])) + 1,
                "node": node_name,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "execution_time": time.time() - step_start,
                "input": input_snapshot,
                "output": output_snapshot,
                "reasoning": generate_reasoning(node_name, input_snapshot, output_snapshot),
                "metrics": calculate_node_metrics(node_name, output_state)
            }
            
            thinking_trace = state.get("thinking_trace", [])
            thinking_trace.append(trace_entry)
            output_state["thinking_trace"] = thinking_trace
            
            return output_state
        return wrapper
    return decorator
```

**GraphState 확장**:

```python
class GraphState(TypedDict):
    # ... 기존 필드
    
    # ========== Thinking 모드 (추론 과정 기록) ==========
    thinking_trace: NotRequired[List[Dict[str, Any]]]
    # [
    #     {
    #         "step": 1,
    #         "node": "classify_node",
    #         "timestamp": "2025-12-24T10:30:00",
    #         "input": {"query": "임진왜란의 원인은?"},
    #         "output": {"query_type": "causal", "query_intent": "원인 파악"},
    #         "reasoning": "질문에 '원인'이라는 키워드가 있어 causal로 분류",
    #         "metrics": {"confidence": 0.95}
    #     },
    #     ...
    # ]
```

---

### 🔜 Phase 3: Thinking 모드 UI

**목표**: 사용자가 추론 과정을 시각적으로 확인할 수 있는 UI 구현

**필요 작업**:
1. thinking_trace를 프론트엔드에 전달
2. 단계별 시각화 컴포넌트 구현
3. 실시간 추론 과정 스트리밍

**예상 작업량**: 1개월

**우선순위**: Low (Thinking Trace 구현 후)

---

### 🔜 Phase 4: Thinking Trace 기반 평가

**목표**: 추론 과정의 품질을 평가하는 새로운 메트릭 추가

**새로운 평가 메트릭**:
- **Reasoning Coherence**: 각 단계가 이전 단계와 논리적으로 연결되는가?
- **Step Necessity**: 각 단계가 최종 답변에 기여하는가?
- **Intent Alignment**: 전체 과정이 초기 intent를 유지하는가?

**예상 작업량**: 1주

**우선순위**: Low (Thinking Trace 구현 후)

---

## 구현 우선순위

### Phase 1: Intent-aware 평가 ✅ 완료
- ✅ test_config에 intent_weights 추가
- ✅ evaluator에서 query_type 반영
- ✅ Ablation Study에 intent별 분석 추가

### Phase 2: Thinking Trace 구현 ⏳ 예정
- ⏳ GraphState에 thinking_trace 추가
- ⏳ trace_thinking_process 데코레이터 구현
- ⏳ 주요 노드에 데코레이터 적용

### Phase 3: Thinking 모드 UI ⏳ 예정
- ⏳ thinking_trace를 프론트엔드에 전달
- ⏳ 단계별 시각화 컴포넌트 구현
- ⏳ 실시간 추론 과정 스트리밍

---

## 참고 문서

- [GUIDE.md](./GUIDE.md): 전체 evaluation 프레임워크 가이드
- [WEIGHT_CALCULATION_GUIDE.md](./WEIGHT_CALCULATION_GUIDE.md): 가중치 계산 방법론
- [README.md](./README.md): Ontology evaluation 개요
