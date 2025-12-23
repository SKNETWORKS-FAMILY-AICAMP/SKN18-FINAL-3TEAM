# Intent-Aware Evaluation 사용 가이드

## 개요

Intent-Aware Evaluation은 query_type(factual, causal, comparative, deep_analysis)에 따라 평가 메트릭에 다른 가중치를 적용하는 평가 시스템입니다.

**핵심 아이디어**:
- Factual 쿼리: 단순 사실 확인 → 수렴 노드 중요도 낮음
- Causal 쿼리: 인과관계 추론 → 수렴 노드 중요도 높음
- Comparative 쿼리: 2개 엔티티 비교 → 수렴 노드 중요도 매우 높음
- Deep Analysis 쿼리: 심층 분석 → Intent 보존과 관계 일관성 중요

---

## 설치 및 설정

### 1. 파일 구조

```
backend/ragas/ontology_evaluate/
├── evaluators/
│   ├── __init__.py
│   ├── intent_aware_evaluator.py       # Intent-aware 평가자 (NEW)
│   ├── l1_schema_compliance.py
│   ├── l2_path_quality.py
│   └── l3_terminal_knowledge.py
├── experiments/
│   └── run_baseline.py                 # 업데이트됨 (intent-aware 지원)
├── data/
│   └── test_queries.json               # 40개 query_type 포함 쿼리
├── INTENT_AWARE_USAGE.md               # 이 파일
└── INTENT_AWARE_QUERY_VALIDATION.md    # 쿼리 검증 보고서
```

### 2. 의존성

```python
# 기존 evaluators 의존성과 동일
from ragas.ontology_evaluate.evaluators.intent_aware_evaluator import IntentAwareEvaluator
```

---

## 사용 방법

### 방법 1: 커맨드라인 실행 (가장 간단)

```bash
# Intent-aware 평가 활성화 (기본값)
python experiments/run_baseline.py \
    --group semantic_expander \
    --queries data/test_queries.json

# Intent-aware 평가 비활성화
python experiments/run_baseline.py \
    --group semantic_expander \
    --queries data/test_queries.json \
    --no-intent-aware

# 디버깅용 (쿼리 10개만)
python experiments/run_baseline.py \
    --group semantic_expander \
    --queries data/test_queries.json \
    --limit 10
```

**출력 예시**:
```
======================================================================
Baseline Ablation Study 실행
======================================================================
실험 그룹: semantic_expander
질문 파일: data/test_queries.json
결과 저장: data/results
Intent-aware 평가: 활성화
======================================================================
테스트 질문 개수: 40
Query Type 분포: {'factual': 10, 'causal': 10, 'comparative': 10, 'deep_analysis': 10}

...

======================================================================
Intent-Aware 평가 요약
======================================================================
  causal         : 0.847 (n=10)
  comparative    : 0.901 (n=10)
  deep_analysis  : 0.823 (n=10)
  factual        : 0.756 (n=10)
======================================================================
```

### 방법 2: Python 코드에서 직접 사용

```python
from ragas.ontology_evaluate.evaluators.intent_aware_evaluator import IntentAwareEvaluator

# 1. Evaluator 생성
evaluator = IntentAwareEvaluator()

# 2. 각 evaluator의 원점수 준비
raw_metrics = {
    "tbox_consistency": 0.90,
    "intent_preservation": 0.85,
    "relation_coherence": 0.88,
    "triple_validity": 0.82,
    "evidence_diversity": 0.75,
    "convergence_utilization": 0.80
}

# 3. Intent-aware 평가 실행
result = evaluator.evaluate(
    query_type="causal",  # factual, causal, comparative, deep_analysis
    raw_metrics=raw_metrics
)

# 4. 결과 확인
print(f"Query Type: {result['query_type']}")
print(f"Final Score: {result['final_score']:.3f}")
print(f"Weights: {result['weights']}")
print(f"Weighted Metrics: {result['weighted_metrics']}")
```

### 방법 3: 커스텀 가중치 사용

```python
from ragas.ontology_evaluate.evaluators.intent_aware_evaluator import (
    IntentAwareEvaluator,
    IntentWeightConfig
)

# 커스텀 가중치 정의
custom_weights = {
    "my_custom_intent": IntentWeightConfig(
        tbox_consistency_weight=2.0,      # 매우 중요
        intent_preservation_weight=1.5,
        relation_coherence_weight=1.0,
        triple_validity_weight=1.0,
        evidence_diversity_weight=0.5,
        convergence_utilization_weight=0.3  # 덜 중요
    )
}

# Evaluator 생성
evaluator = IntentAwareEvaluator(custom_weights=custom_weights)

# 평가 실행
result = evaluator.evaluate("my_custom_intent", raw_metrics)
```

---

## 평가 결과 구조

### 1. 전체 평가 결과

```json
{
  "raw_metrics": {
    "tbox_consistency": 0.90,
    "intent_preservation": 0.85,
    "relation_coherence": 0.88,
    "triple_validity": 0.82,
    "evidence_diversity": 0.75,
    "convergence_utilization": 0.80
  },
  "detailed_results": {
    "tbox_consistency": {
      "score": 0.90,
      "violations": [],
      "total_triples": 120
    },
    "intent_preservation": {
      "score": 0.85,
      "state": "Enrich",
      "reasoning": "..."
    },
    ...
  },
  "intent_aware": {
    "query_type": "causal",
    "raw_metrics": {...},
    "weights": {
      "tbox_consistency": 0.156,
      "intent_preservation": 0.218,
      "relation_coherence": 0.203,
      "triple_validity": 0.187,
      "evidence_diversity": 0.187,
      "convergence_utilization": 0.234
    },
    "weighted_metrics": {
      "tbox_consistency": 0.140,
      "intent_preservation": 0.185,
      "relation_coherence": 0.178,
      "triple_validity": 0.153,
      "evidence_diversity": 0.140,
      "convergence_utilization": 0.187
    },
    "final_score": 0.847,
    "breakdown": "..."
  }
}
```

### 2. Intent-aware 결과만 추출

```python
intent_result = result["metrics"]["intent_aware"]

print(f"Query Type: {intent_result['query_type']}")
print(f"Final Score: {intent_result['final_score']:.3f}")

# 가장 영향력 있는 메트릭 확인
weighted = intent_result['weighted_metrics']
top_metrics = sorted(weighted.items(), key=lambda x: x[1], reverse=True)[:3]

print("\nTop 3 Contributing Metrics:")
for metric, score in top_metrics:
    weight = intent_result['weights'][metric]
    raw = intent_result['raw_metrics'][metric]
    print(f"  {metric}: {score:.3f} (raw={raw:.3f}, weight={weight:.3f})")
```

---

## Query Type별 가중치 분석

### Factual (단순 사실 확인)

```python
FACTUAL_WEIGHTS = {
    "tbox_consistency": 0.224,        # 가장 높음 (Schema 준수)
    "intent_preservation": 0.194,     # 높음
    "triple_validity": 0.179,         # 높음
    "relation_coherence": 0.149,      # 중간
    "evidence_diversity": 0.119,      # 낮음
    "convergence_utilization": 0.075  # 가장 낮음 (수렴 노드 불필요)
}
```

**특징**:
- Schema 준수와 Intent 보존이 가장 중요
- 수렴 노드는 거의 불필요 (가중치 0.075)
- 단순 1-hop 조회에 최적화

### Causal (인과관계 추론)

```python
CAUSAL_WEIGHTS = {
    "convergence_utilization": 0.234,  # 가장 높음 (인과 체인 연결)
    "intent_preservation": 0.218,      # 매우 높음
    "relation_coherence": 0.203,       # 높음 (인과 체인)
    "evidence_diversity": 0.187,       # 높음
    "triple_validity": 0.187,          # 높음
    "tbox_consistency": 0.156          # 중간
}
```

**특징**:
- 수렴 노드가 가장 중요 (가중치 0.234)
- 관계 일관성도 중요 (인과 체인 연결)
- 증거 다양성 중요 (다각적 인과 분석)

### Comparative (비교 분석)

```python
COMPARATIVE_WEIGHTS = {
    "convergence_utilization": 0.253,  # 가장 높음 (2개 엔티티 비교점)
    "evidence_diversity": 0.221,       # 매우 높음 (양쪽 증거)
    "intent_preservation": 0.205,      # 높음
    "triple_validity": 0.189,          # 높음
    "relation_coherence": 0.189,       # 높음
    "tbox_consistency": 0.158          # 중간
}
```

**특징**:
- 수렴 노드가 가장 중요 (가중치 0.253)
- 증거 다양성도 매우 중요 (양쪽 엔티티의 증거 필요)
- 2개 엔티티 비교에 최적화

### Deep Analysis (심층 분석)

```python
DEEP_ANALYSIS_WEIGHTS = {
    "intent_preservation": 0.227,      # 가장 높음 (의도 유지)
    "relation_coherence": 0.212,       # 매우 높음
    "convergence_utilization": 0.197,  # 높음
    "evidence_diversity": 0.197,       # 높음
    "triple_validity": 0.197,          # 높음
    "tbox_consistency": 0.152          # 중간
}
```

**특징**:
- Intent 보존이 가장 중요 (복합 분석)
- 관계 일관성도 매우 중요
- 균형잡힌 가중치 분포

---

## 실험 시나리오

### 시나리오 1: Query Type별 성능 비교

**목표**: 각 query_type에서 어떤 설정이 가장 효과적인지 발견

```bash
# Semantic expander 실험
python experiments/run_baseline.py \
    --group semantic_expander \
    --queries data/test_queries.json

# 결과 분석
python -c "
import json
with open('data/results/semantic_expander_ablation.json') as f:
    results = json.load(f)

# Query type별 최고 점수 설정 찾기
best_configs = {}
for result in results:
    if result['success']:
        ia = result['metrics']['intent_aware']
        qtype = ia['query_type']
        score = ia['final_score']
        config = result['config']

        if qtype not in best_configs or score > best_configs[qtype]['score']:
            best_configs[qtype] = {'score': score, 'config': config}

for qtype, data in best_configs.items():
    print(f'{qtype}: {data[\"score\"]:.3f} - {data[\"config\"]}')"
```

### 시나리오 2: 수렴 노드 중요도 검증

**목표**: 수렴 노드가 comparative/causal에서 정말 중요한지 검증

```bash
# Thread 실험
python experiments/run_baseline.py \
    --group thread \
    --queries data/test_queries.json

# 결과 분석: convergence_utilization 메트릭과 final_score의 상관관계
python -c "
import json
with open('data/results/thread_ablation.json') as f:
    results = json.load(f)

# Query type별 convergence 영향 분석
for qtype in ['factual', 'causal', 'comparative', 'deep_analysis']:
    qtype_results = [r for r in results if r['success'] and r['metrics']['intent_aware']['query_type'] == qtype]

    conv_scores = [r['metrics']['raw_metrics']['convergence_utilization'] for r in qtype_results]
    final_scores = [r['metrics']['intent_aware']['final_score'] for r in qtype_results]

    # 간단한 상관관계 계산
    import numpy as np
    corr = np.corrcoef(conv_scores, final_scores)[0, 1]
    print(f'{qtype}: correlation = {corr:.3f}')"
```

**기대 결과**:
- Factual: 낮은 상관관계 (convergence 중요하지 않음)
- Causal: 높은 상관관계 (convergence 중요)
- Comparative: 매우 높은 상관관계 (convergence 매우 중요)
- Deep Analysis: 중간 상관관계

### 시나리오 3: Intent-aware vs Raw 평가 비교

**목표**: Intent-aware 평가가 정말 query_type에 따라 다르게 평가하는지 확인

```bash
# Intent-aware 활성화
python experiments/run_baseline.py \
    --group semantic_expander \
    --queries data/test_queries.json \
    --output data/results_intent_aware

# Intent-aware 비활성화
python experiments/run_baseline.py \
    --group semantic_expander \
    --queries data/test_queries.json \
    --output data/results_raw \
    --no-intent-aware

# 결과 비교
python -c "
import json
import numpy as np

with open('data/results_intent_aware/semantic_expander_ablation.json') as f:
    results_ia = json.load(f)

with open('data/results_raw/semantic_expander_ablation.json') as f:
    results_raw = json.load(f)

# Query type별 점수 분산 비교
for qtype in ['factual', 'causal', 'comparative', 'deep_analysis']:
    ia_scores = [r['metrics']['intent_aware']['final_score'] for r in results_ia if r['success'] and r['metrics']['intent_aware']['query_type'] == qtype]

    # Raw는 단순 평균으로 계산
    raw_scores = [np.mean(list(r['metrics']['raw_metrics'].values())) for r in results_raw if r['success']]

    print(f'{qtype}:')
    print(f'  Intent-aware mean: {np.mean(ia_scores):.3f}')
    print(f'  Raw mean: {np.mean(raw_scores):.3f}')
    print(f'  Difference: {np.mean(ia_scores) - np.mean(raw_scores):.3f}')"
```

**기대 결과**:
- Factual: Intent-aware 점수가 낮음 (수렴 노드 패널티)
- Comparative: Intent-aware 점수가 높음 (수렴 노드 보너스)

---

## 결과 해석 가이드

### 1. Final Score 해석

- **0.9 ~ 1.0**: 매우 우수 - 해당 query_type에 최적화된 성능
- **0.8 ~ 0.9**: 우수 - 대부분의 메트릭이 높은 점수
- **0.7 ~ 0.8**: 양호 - 일부 메트릭 개선 필요
- **0.6 ~ 0.7**: 보통 - 여러 메트릭 개선 필요
- **< 0.6**: 미흡 - 전반적인 개선 필요

### 2. Query Type별 기대 점수 범위

| Query Type | 기대 점수 범위 | 이유 |
|------------|----------------|------|
| Factual | 0.70 ~ 0.85 | 단순 조회는 높은 점수 쉽게 달성 가능 |
| Causal | 0.75 ~ 0.90 | 인과 체인 구축 시 높은 점수 |
| Comparative | 0.80 ~ 0.95 | 수렴 노드 발견 시 매우 높은 점수 |
| Deep Analysis | 0.75 ~ 0.90 | 복합 분석 성공 시 높은 점수 |

### 3. 메트릭별 기여도 분석

```python
# 특정 결과의 메트릭 기여도 확인
result = results[0]
ia = result['metrics']['intent_aware']

print("Metric Contributions:")
for metric in ia['weighted_metrics']:
    weight = ia['weights'][metric]
    raw = ia['raw_metrics'][metric]
    weighted = ia['weighted_metrics'][metric]
    contribution_pct = (weighted / ia['final_score']) * 100

    print(f"  {metric:30s}: {contribution_pct:5.1f}% (raw={raw:.3f}, weight={weight:.3f})")
```

---

## FAQ

### Q1: Intent-aware 평가를 비활성화하려면?

```bash
python experiments/run_baseline.py --no-intent-aware
```

### Q2: 새로운 query_type을 추가하려면?

`intent_aware_evaluator.py`의 `INTENT_WEIGHT_PRESETS`에 추가:

```python
INTENT_WEIGHT_PRESETS = {
    # ... 기존 설정 ...
    "my_new_type": IntentWeightConfig(
        tbox_consistency_weight=1.0,
        intent_preservation_weight=1.0,
        relation_coherence_weight=1.0,
        triple_validity_weight=1.0,
        evidence_diversity_weight=1.0,
        convergence_utilization_weight=1.0
    )
}
```

### Q3: 가중치를 동적으로 조정하려면?

커스텀 가중치 사용:

```python
custom_weights = {
    "causal": IntentWeightConfig(
        convergence_utilization_weight=2.0,  # 더 높게 설정
        # ... 나머지 ...
    )
}

evaluator = IntentAwareEvaluator(custom_weights=custom_weights)
```

### Q4: Raw metrics와 Intent-aware 점수가 크게 차이나는 이유?

Intent-aware 평가는 query_type에 따라 가중치를 다르게 적용합니다:
- Factual: 수렴 노드 낮은 가중치 → raw 평균보다 낮을 수 있음
- Comparative: 수렴 노드 높은 가중치 → raw 평균보다 높을 수 있음

이는 정상적인 동작이며, query_type에 적합한 평가를 위한 것입니다.

### Q5: 실제 LangGraph와 통합하려면?

`run_baseline.py`의 `mock_graph_invoke`를 실제 graph로 교체:

```python
# Mock 대신 실제 graph 사용
from langgraph_fuseki.graph import create_graph

graph = create_graph()

def real_graph_invoke(state):
    return graph.invoke(state)

# runner에 전달
results = runner.run_experiment_group(
    queries=queries,
    configs=configs,
    graph_invoke_func=real_graph_invoke,  # Mock 대신 실제 함수
    group_name=args.group
)
```

---

## 다음 단계

1. **Baseline 실험 실행**: 40개 쿼리로 기본 성능 측정
2. **Ablation Study**: 각 컴포넌트의 기여도 측정
3. **최적 설정 발견**: Query type별 최고 성능 설정 찾기
4. **Thinking Trace 추가**: 중간 추론 과정 기록 (향후 작업)
5. **실시간 평가**: LangGraph 실행 중 실시간 평가 (향후 작업)

---

## 관련 문서

- [INTENT_AWARE_QUERY_VALIDATION.md](./INTENT_AWARE_QUERY_VALIDATION.md): 40개 테스트 쿼리 검증 보고서
- [REDESIGN_PROPOSAL.md](./REDESIGN_PROPOSAL.md): Test config와 intent router 호환성 분석
- [GUIDE.md](./GUIDE.md): 전체 evaluation 프레임워크 가이드
- [README.md](./README.md): Ontology evaluation 개요
