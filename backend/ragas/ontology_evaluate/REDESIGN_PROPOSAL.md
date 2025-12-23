# test_config 및 평가 프레임워크 재설계 제안

> **상태**: ✅ Phase 1 완료 - Intent-aware 평가 구현 완료 (2025-12-24)

## 구현 완료 항목

### ✅ Intent-Aware 평가 시스템 (완료)

**구현 파일**: `evaluators/intent_aware_evaluator.py`

**구현 내용**:
1. Query type별 가중치 프리셋 (factual, causal, comparative, deep_analysis)
2. `IntentAwareEvaluator` 클래스 구현
3. `run_baseline.py`에 통합 (--intent-aware / --no-intent-aware 옵션)
4. 40개 테스트 쿼리 검증 완료 ([INTENT_AWARE_QUERY_VALIDATION.md](./INTENT_AWARE_QUERY_VALIDATION.md))
5. 사용 가이드 작성 ([INTENT_AWARE_USAGE.md](./INTENT_AWARE_USAGE.md))

**사용 방법**:
```bash
# Intent-aware 평가 활성화 (기본값)
python experiments/run_baseline.py --group semantic_expander

# Intent-aware 평가 비활성화
python experiments/run_baseline.py --group semantic_expander --no-intent-aware
```

**평가 결과 구조**:
```python
{
    "raw_metrics": {...},           # 6개 원점수
    "detailed_results": {...},      # 각 evaluator의 상세 결과
    "intent_aware": {               # Intent-aware 평가 (NEW)
        "query_type": "causal",
        "final_score": 0.847,
        "weights": {...},
        "weighted_metrics": {...}
    }
}
```

---

## 문제 인식 (Original)

### 1. 현재 test_config의 한계

**기존 RAGAS test_config (80가지 조합)**:
```python
{
    "semantic_expander": {"temporal": True, "category": False, ...},  # 1개만 True
    "aggregator_threads": {"outgoing_relations": True, ...},  # 1개만 True
    "entity_boost_mode": "exact_match"
}
```

**문제점**:
- ❌ **intent router와 무관**: query_type(causal, factual, comparative, deep_analysis)에 따른 가중치 변화를 반영하지 못함
- ❌ **중간 과정 추적 불가**: 노드별 사고 과정(thinking process)을 기록하지 않음
- ❌ **향후 thinking 모드 부적합**: 추론 단계별 시각화 데이터가 없음

### 2. Intent Router 기반 LangGraph의 특징

현재 시스템 (`state.py:12`):
```python
query_type: Literal["causal", "factual", "deep_analysis", "comparative"]
thread_weights: Dict[str, float]  # query_type별 다른 가중치
```

**Intent에 따른 동작 변화**:
- **Causal**: 인과관계 Thread 가중치 높음, 수렴 노드 중요도 1.5
- **Factual**: 단순 정보 검색, 수렴 노드 중요도 1.0
- **Comparative**: 비교 분석, 수렴 노드 중요도 1.2
- **Deep Analysis**: 심층 분석, 수렴 노드 중요도 1.3

### 3. 향후 Thinking 모드 요구사항

사용자가 보는 화면:
```
🤔 추론 과정 (Thinking Process)

1단계: 질문 분석
  └─ 질문 유형: causal (인과관계)
  └─ 핵심 의도: 임진왜란의 원인 파악

2단계: 엔티티 추출
  └─ 추출된 엔티티: 임진왜란 (Event), 조선 (Organization)

3단계: 의미론적 확장
  └─ Temporal: 정유재란 (7년 차이) → 관련도 0.85
  └─ Causal Chain: 명나라 요청 → 도요토미 히데요시 → 관련도 0.92

4단계: 지식 검색 (5개 Thread)
  └─ outgoing_relations: 15개 경로 (가중치: 1.5)
  └─ incoming_relations: 8개 경로 (가중치: 1.2)
  └─ ...

5단계: 근거 통합
  └─ 수렴 노드 감지: 명나라, 일본 (2개)
  └─ 최종 선택: 15개 근거 (Intent Preservation: 0.92)

6단계: 답변 생성
  └─ 최종 답변: "임진왜란은 도요토미 히데요시의..."
```

**필요 데이터**:
- 노드별 실행 결과 (extracted_entities, expanded_entities, evidences 등)
- 각 단계의 점수 (relevance_score, weight, intent_preservation 등)
- 중간 결정 근거 (왜 이 엔티티를 선택했는지, 왜 이 Thread가 중요한지)

---

## 향후 계획 (Phase 2)

### 🔜 Thinking Trace 구현

**목표**: 노드별 추론 과정을 기록하여 향후 "thinking 모드" UI에 표시

**필요 작업**:
1. `GraphState`에 `thinking_trace` 필드 추가
2. `test_config`에 `enable_thinking_trace` 옵션 추가
3. 각 노드에 `@trace_thinking_process` 데코레이터 적용
4. Frontend에서 thinking trace 시각화

**예상 작업량**: 2~3일

**우선순위**: Medium (Intent-aware 평가 완료 후)

---

## 재설계 방안 (Original)

### 1. test_config 확장: intent-aware config

**기존**:
```python
{
    "semantic_expander": {"temporal": True, ...},
    "aggregator_threads": {"outgoing_relations": True, ...}
}
```

**개선안**:
```python
{
    # Ablation Study 설정 (기존 유지)
    "semantic_expander": {"temporal": True, "category": False, ...},
    "aggregator_threads": {"outgoing_relations": True, ...},
    "entity_boost_mode": "exact_match",

    # Intent-aware 가중치 오버라이드 (신규)
    "intent_weights": {
        "causal": {
            "convergence_importance": 1.5,
            "thread_weights": {
                "outgoing_relations": 1.5,
                "incoming_relations": 1.2,
                ...
            }
        },
        "factual": {
            "convergence_importance": 1.0,
            "thread_weights": {
                "outgoing_relations": 1.0,
                ...
            }
        }
    },

    # Thinking 모드 설정 (신규)
    "enable_thinking_trace": True,  # 중간 과정 기록 여부
    "thinking_detail_level": "full"  # "minimal", "medium", "full"
}
```

### 2. GraphState에 thinking_trace 추가

**state.py 수정**:
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
    #     {
    #         "step": 3,
    #         "node": "semantic_expander",
    #         "timestamp": "2025-12-24T10:30:05",
    #         "input": {"extracted_entities": [...]},
    #         "output": {"expanded_entities": [...], "expansion_count": 25},
    #         "reasoning": "Temporal 확장으로 정유재란 추가 (7년 차이)",
    #         "metrics": {
    #             "temporal": {"count": 5, "avg_relevance": 0.85},
    #             "causal_chain": {"count": 8, "avg_relevance": 0.92}
    #         }
    #     },
    #     {
    #         "step": 5,
    #         "node": "path_evidence_aggregator",
    #         "timestamp": "2025-12-24T10:30:10",
    #         "input": {"parallel_results": {...}},
    #         "output": {
    #             "evidences": [...],
    #             "convergence_nodes": [{"label": "명나라", ...}]
    #         },
    #         "reasoning": "수렴 노드 '명나라'가 임진왜란과 조선을 연결",
    #         "metrics": {
    #             "intent_preservation": 0.92,
    #             "convergence_utilization": 0.8,
    #             "evidence_diversity": 0.75
    #         }
    #     }
    # ]
```

### 3. 노드별 thinking_trace 기록 래퍼

**새로운 유틸리티**:
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
                # Thinking 모드 OFF: 기존 방식 그대로
                return node_func(state)

            # Thinking 모드 ON: 추론 과정 기록
            step_start = time.time()

            # 입력 상태 스냅샷
            input_snapshot = {
                "query": state.get("query"),
                "query_type": state.get("query_type"),
                "extracted_entities": len(state.get("extracted_entities", []))
            }

            # 노드 실행
            output_state = node_func(state)

            # 출력 상태 스냅샷
            output_snapshot = extract_output_snapshot(node_name, output_state)

            # reasoning 생성 (노드별 커스터마이징 필요)
            reasoning = generate_reasoning(node_name, input_snapshot, output_snapshot)

            # metrics 계산
            metrics = calculate_node_metrics(node_name, output_state)

            # thinking_trace에 추가
            trace_entry = {
                "step": len(state.get("thinking_trace", [])) + 1,
                "node": node_name,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "execution_time": time.time() - step_start,
                "input": input_snapshot,
                "output": output_snapshot,
                "reasoning": reasoning,
                "metrics": metrics
            }

            thinking_trace = state.get("thinking_trace", [])
            thinking_trace.append(trace_entry)
            output_state["thinking_trace"] = thinking_trace

            return output_state

        return wrapper
    return decorator


def generate_reasoning(node_name: str, input_snap: Dict, output_snap: Dict) -> str:
    """노드별 추론 근거 생성"""

    if node_name == "classify_node":
        query_type = output_snap.get("query_type")
        return f"질문 패턴 분석 결과 '{query_type}' 유형으로 분류"

    elif node_name == "semantic_expander":
        expansion_count = output_snap.get("expansion_count", 0)
        methods = output_snap.get("expansion_methods", [])
        return f"{', '.join(methods)} 확장으로 {expansion_count}개 엔티티 추가"

    elif node_name == "path_evidence_aggregator":
        convergence_count = len(output_snap.get("convergence_nodes", []))
        if convergence_count > 0:
            nodes = ", ".join([n["label"] for n in output_snap.get("convergence_nodes", [])[:3]])
            return f"수렴 노드 {convergence_count}개 감지: {nodes}"
        return "근거 통합 완료"

    return f"{node_name} 실행 완료"


def calculate_node_metrics(node_name: str, state: GraphState) -> Dict[str, Any]:
    """노드별 평가 메트릭 계산"""

    if node_name == "semantic_expander":
        # Intent Preservation 계산 (간단 버전)
        extracted_count = len(state.get("extracted_entities", []))
        # 실제로는 LLM Judge 사용
        return {
            "expansion_rate": extracted_count / max(1, len(state.get("extracted_entities", [])[:10])),
            "intent_preservation": 0.85  # 실제로는 evaluator 사용
        }

    elif node_name == "path_evidence_aggregator":
        # Convergence Utilization 계산
        convergence_nodes = state.get("convergence_nodes", [])
        final_answer = state.get("final_answer", "")

        mentioned_count = sum(
            1 for node in convergence_nodes
            if node.get("label", "") in final_answer
        )

        return {
            "convergence_utilization": mentioned_count / max(1, len(convergence_nodes)),
            "evidence_diversity": 0.75,  # 실제로는 evaluator 사용
            "total_evidences": len(state.get("evidences", []))
        }

    return {}
```

### 4. 노드 코드 수정 예시

**semantic_expander_node.py**:
```python
from backend.langgraph_fuseki.utils.thinking_trace import trace_thinking_process

@trace_thinking_process("semantic_expander")
def semantic_expander_node(state: GraphState) -> GraphState:
    """
    의미론적 엔티티 확장 노드

    thinking_trace가 활성화되면 자동으로 추론 과정 기록
    """
    # 기존 코드 그대로
    query = state.get("query", "")
    extracted_entities = state.get("extracted_entities", [])
    test_config = state.get("test_config", {})
    semantic_config = test_config.get("semantic_expander", {})

    # 확장 실행
    if semantic_config.get("temporal", True):
        temporal_expanded = expand_by_temporal_context(...)

    # ... (기존 로직)

    return {**state, "extracted_entities": all_expanded}
```

**효과**:
- 코드 변경 최소화 (데코레이터만 추가)
- Thinking 모드 ON/OFF 자동 전환
- 중간 과정 자동 기록

---

## 평가 프레임워크 개선

### 1. Intent-aware 평가

**기존**:
```python
# 모든 질문에 동일한 가중치
metrics = {
    "intent_preservation": 0.85,
    "convergence_utilization": 0.7
}
```

**개선안**:
```python
# query_type에 따라 다른 기준
def evaluate_with_intent(state: GraphState, metrics: Dict) -> Dict:
    query_type = state.get("query_type", "factual")

    # Intent별 가중치
    intent_weights = {
        "causal": {
            "intent_preservation": 1.5,  # 인과관계에서 매우 중요
            "convergence_utilization": 1.5,
            "evidence_diversity": 1.0
        },
        "factual": {
            "intent_preservation": 1.0,
            "convergence_utilization": 0.5,  # 덜 중요
            "evidence_diversity": 0.8
        },
        "comparative": {
            "intent_preservation": 1.2,
            "convergence_utilization": 1.8,  # 매우 중요
            "evidence_diversity": 1.3
        },
        "deep_analysis": {
            "intent_preservation": 1.3,
            "convergence_utilization": 1.3,
            "evidence_diversity": 1.5
        }
    }

    weights = intent_weights.get(query_type, {})

    # 가중 평균 계산
    weighted_score = sum(
        metrics[metric] * weights.get(metric, 1.0)
        for metric in metrics
    ) / sum(weights.values())

    return {
        "query_type": query_type,
        "raw_metrics": metrics,
        "intent_weights": weights,
        "weighted_score": weighted_score
    }
```

### 2. Thinking Trace 기반 평가

**새로운 평가 메트릭**:
```python
# evaluators/thinking_quality.py

class ThinkingQualityEvaluator:
    """Thinking 과정 품질 평가"""

    def evaluate(self, thinking_trace: List[Dict]) -> Dict:
        """
        추론 과정의 논리성, 일관성 평가

        Returns:
            {
                "reasoning_coherence": 0.9,  # 추론 일관성
                "step_necessity": 0.85,      # 각 단계 필요성
                "intent_alignment": 0.92     # 의도와의 정합성
            }
        """
        if not thinking_trace:
            return {"score": 0.0}

        # 1. 추론 일관성: 각 단계가 이전 단계와 논리적으로 연결되는가?
        coherence_scores = []
        for i in range(1, len(thinking_trace)):
            prev_step = thinking_trace[i-1]
            curr_step = thinking_trace[i]

            # 이전 단계의 output이 현재 단계의 input과 일치하는지
            coherence = self._check_step_coherence(prev_step, curr_step)
            coherence_scores.append(coherence)

        reasoning_coherence = sum(coherence_scores) / max(1, len(coherence_scores))

        # 2. 단계 필요성: 각 단계가 최종 답변에 기여하는가?
        necessity_scores = []
        for step in thinking_trace:
            metrics = step.get("metrics", {})
            # 점수가 높으면 필요한 단계
            avg_metric = sum(metrics.values()) / max(1, len(metrics))
            necessity_scores.append(avg_metric)

        step_necessity = sum(necessity_scores) / max(1, len(necessity_scores))

        # 3. Intent 정합성: 전체 과정이 초기 intent를 유지하는가?
        intent_alignment = self._check_intent_alignment(thinking_trace)

        return {
            "reasoning_coherence": reasoning_coherence,
            "step_necessity": step_necessity,
            "intent_alignment": intent_alignment,
            "overall_score": (reasoning_coherence + step_necessity + intent_alignment) / 3
        }
```

---

## 구현 우선순위

### Phase 1: Intent-aware 평가 (즉시)
1. ✅ test_config에 intent_weights 추가
2. ✅ evaluator에서 query_type 반영
3. ✅ Ablation Study에 intent별 분석 추가

### Phase 2: Thinking Trace 기반 (2주 내)
1. ⏳ GraphState에 thinking_trace 추가
2. ⏳ trace_thinking_process 데코레이터 구현
3. ⏳ 주요 노드에 데코레이터 적용

### Phase 3: Thinking 모드 UI (1개월 내)
1. ⏳ thinking_trace를 프론트엔드에 전달
2. ⏳ 단계별 시각화 컴포넌트 구현
3. ⏳ 실시간 추론 과정 스트리밍

---

## 결론

### 현재 test_config의 문제
- ❌ Intent router와 무관
- ❌ 중간 과정 추적 불가
- ❌ Thinking 모드 부적합

### 개선 후
- ✅ Intent별 가중치 반영
- ✅ 노드별 thinking_trace 자동 기록
- ✅ Thinking 모드 UI 데이터 제공

### 다음 작업
1. test_config에 intent_weights 추가 (30분)
2. evaluator에 query_type 기반 가중치 적용 (1시간)
3. thinking_trace 유틸리티 구현 (2시간)
4. semantic_expander_node에 데코레이터 적용 (30분)

**질문**: 이 재설계 방향이 적합한지, 그리고 어떤 Phase부터 시작할지 결정 부탁드립니다.
