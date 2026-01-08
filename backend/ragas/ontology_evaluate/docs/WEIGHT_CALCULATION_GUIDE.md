# 가중치 계산 시스템 설계 가이드

## 개요

본 문서는 온톨로지 기반 RAG 평가 시스템의 **Intent-Aware 가중치 계산 방식**을 설명합니다. 코드 구현보다는 **실험 설계를 통해 최적 가중치를 선택하는 방법론**에 초점을 맞춥니다.

---

## 1. 핵심 개념: Intent-Aware 평가

### 1.1 기본 원리

모든 평가 메트릭이 모든 질문 유형에 동일하게 중요한 것은 아닙니다.

**예시:**
- **Factual 질문** ("세종대왕이 훈민정음을 창제한 시기는?"): 수렴 노드(convergence)가 덜 중요
- **Comparative 질문** ("임진왜란과 병자호란의 공통점은?"): 수렴 노드가 매우 중요 (두 엔티티의 교차점 필요)

### 1.2 평가 메트릭 계층

시스템은 6가지 평가 메트릭을 사용합니다:

```
L1 (Schema 레벨):
  └─ TBox Consistency: 온톨로지 스키마 준수 여부

L2 (Path 레벨):
  ├─ Intent Preservation: 확장 경로가 질문 의도를 유지하는지
  └─ Relation Coherence: 관계의 일관성과 연결성

L3 (Triple 레벨):
  ├─ Triple Validity: 최종 Triple의 유효성
  ├─ Evidence Diversity: 증거의 다양성
  └─ Convergence Utilization: 수렴 노드 활용도
```

---

## 2. 질문 유형별 가중치 전략

### 2.1 Factual (사실 확인)

**특징:**
- 단순 사실 확인 (언제, 누가, 어디서)
- 직선적 경로 (A → B)
- 수렴 노드 불필요

**가중치 전략:**
```
높음 ↑
  ├─ TBox Consistency (1.5)      # 스키마 준수 최우선
  ├─ Intent Preservation (1.3)   # 의도 유지 중요
  └─ Triple Validity (1.2)       # Triple 정확성

보통 =
  └─ Relation Coherence (1.0)

낮음 ↓
  ├─ Evidence Diversity (0.8)
  └─ Convergence Utilization (0.5)  # 가장 낮음
```

**실험 가설:**
> "Factual 질문에서는 수렴 노드 가중치를 낮춰도 final_score가 높게 나올 것"

### 2.2 Causal (인과관계)

**특징:**
- 원인과 결과 추론
- 인과 체인 필요 (A → B → C)
- 수렴 노드 중요 (원인 ↔ 결과 연결)

**가중치 전략:**
```
높음 ↑
  ├─ Convergence Utilization (1.5)    # 인과 체인 연결
  ├─ Intent Preservation (1.4)
  ├─ Relation Coherence (1.3)         # 인과 일관성
  └─ Evidence Diversity (1.2)

보통 =
  ├─ Triple Validity (1.2)
  └─ TBox Consistency (1.0)
```

**실험 가설:**
> "인과관계 질문에서는 수렴 노드와 관계 일관성 가중치를 높여야 성능 향상"

### 2.3 Comparative (비교)

**특징:**
- 2개 이상 엔티티 비교
- 교차점 발견 필수
- 수렴 노드 최고 중요도

**가중치 전략:**
```
매우 높음 ↑↑
  └─ Convergence Utilization (1.6)    # 가장 중요!

높음 ↑
  ├─ Evidence Diversity (1.4)         # 양쪽 증거 필요
  ├─ Intent Preservation (1.3)
  ├─ Relation Coherence (1.2)
  └─ Triple Validity (1.2)

보통 =
  └─ TBox Consistency (1.0)
```

**실험 가설:**
> "비교 질문에서는 수렴 노드 가중치가 final_score에 가장 큰 영향"

### 2.4 Deep Analysis (심층 분석)

**특징:**
- 복합적 분석 (원인 + 결과 + 영향)
- 다양한 경로 탐색
- 균형 잡힌 가중치

**가중치 전략:**
```
높음 ↑
  ├─ Intent Preservation (1.5)        # 의도 유지 최우선
  ├─ Relation Coherence (1.4)
  ├─ Convergence Utilization (1.3)
  ├─ Triple Validity (1.3)
  └─ Evidence Diversity (1.3)

보통 =
  └─ TBox Consistency (1.0)
```

**실험 가설:**
> "심층 분석은 모든 메트릭이 고르게 중요하며, Intent Preservation이 최우선"

---

## 3. 실험 설계: 가중치 선택 방법론

### 3.1 Ablation Study (소거 연구)

**목표:** 각 메트릭의 기여도 측정

**실험 설계:**
```python
# 1단계: Baseline (모든 가중치 1.0)
baseline_weights = {
    "tbox": 1.0,
    "intent": 1.0,
    "coherence": 1.0,
    "validity": 1.0,
    "diversity": 1.0,
    "convergence": 1.0
}

# 2단계: Leave-One-Out (각 메트릭 제거)
for metric in metrics:
    test_weights = baseline_weights.copy()
    test_weights[metric] = 0.0  # 해당 메트릭 제거

    # 실험 실행 및 성능 측정
    score = run_experiment(test_weights, test_queries)

    # 성능 하락폭 = 메트릭 중요도
    contribution = baseline_score - score
```

**분석 방법:**
- 성능 하락이 큰 메트릭 = 중요도 높음 → 가중치 ↑
- 성능 하락이 작은 메트릭 = 중요도 낮음 → 가중치 ↓

### 3.2 Grid Search (격자 탐색)

**목표:** 최적 가중치 조합 탐색

**실험 설계:**
```python
# 가중치 후보 범위 정의
weight_candidates = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]

# 질문 유형별 Grid Search
for query_type in ["factual", "causal", "comparative", "deep_analysis"]:
    best_score = 0
    best_weights = None

    # 주요 메트릭 2-3개에 대해 조합 탐색
    for convergence_w in weight_candidates:
        for intent_w in weight_candidates:
            for diversity_w in weight_candidates:
                weights = create_custom_weights(
                    convergence=convergence_w,
                    intent=intent_w,
                    diversity=diversity_w
                )

                score = evaluate_on_test_set(query_type, weights)

                if score > best_score:
                    best_score = score
                    best_weights = weights
```

**분석 방법:**
- 질문 유형별로 최고 성능을 낸 가중치 조합 선택
- Trade-off 분석: 한 메트릭을 올리면 다른 메트릭은?

### 3.3 Intent-Direction Matrix 실험

**목표:** `query_type` + `user_selected_direction` 조합별 최적 가중치

**실험 설계:**
```python
# Causal 질문 예시
causal_directions = ["time_cause", "time_consequence", "class_person"]

for direction in causal_directions:
    test_queries = load_queries(query_type="causal", preferred_direction=direction)

    # 방향별 가중치 테스트
    if direction.startswith("time_"):
        # 시간축 방향 → Relation Coherence 가중치 상향
        weights = custom_weights(coherence=1.5)
    elif direction.startswith("class_"):
        # 클래스 방향 → Evidence Diversity 가중치 상향
        weights = custom_weights(diversity=1.5)

    score = evaluate(test_queries, weights)
```

**분석 방법:**
- 각 방향별로 어떤 메트릭이 성능에 가장 큰 영향을 미치는지 분석
- 방향별 맞춤형 가중치 프리셋 생성 가능

---

## 4. 실험 실행 프로세스

### 4.1 준비 단계

1. **테스트 질문 준비:**
   ```bash
   python -m backend.ragas.ontology_evaluate.build_queries_persona
   ```
   - `data/test_queries.json` 생성 (40개 질문)
   - 질문 유형별 10개씩 (factual, causal, comparative, deep_analysis)

2. **Baseline 실험 실행:**
   ```bash
   python -m backend.ragas.ontology_evaluate.experiments.run_baseline
   ```
   - 모든 가중치 1.0으로 기준선 성능 측정

### 4.2 Ablation 실험

```bash
# 1. Semantic Expander Ablation
python -m backend.ragas.ontology_evaluate.experiments.run_grid_search \
  --experiment semantic_expander

# 2. Thread Ablation
python -m backend.ragas.ontology_evaluate.experiments.run_grid_search \
  --experiment thread

# 3. 결과 분석
python -m backend.ragas.ontology_evaluate.utils.result_analyzer \
  --input data/results/semantic_expander_ablation.json \
  --output data/results/ablation_analysis.md
```

### 4.3 Grid Search 실험

```python
# experiments/run_grid_search.py 사용 예시

from ragas.ontology_evaluate.evaluators.intent_aware_evaluator import (
    IntentAwareEvaluator,
    create_custom_weights
)

# Factual 질문에 대한 Grid Search
factual_queries = load_queries(query_type="factual")

weight_ranges = {
    "convergence": [0.3, 0.5, 0.8, 1.0],
    "intent": [1.0, 1.2, 1.5, 1.8],
    "tbox": [1.2, 1.5, 1.8, 2.0]
}

results = grid_search(
    queries=factual_queries,
    weight_ranges=weight_ranges,
    output_path="data/results/factual_grid_search.json"
)
```

### 4.4 결과 분석 및 가중치 선택

```python
# 실험 결과 비교
from ragas.ontology_evaluate.utils.result_analyzer import ResultAnalyzer

analyzer = ResultAnalyzer()

# 1. 질문 유형별 최적 가중치 찾기
best_weights = analyzer.find_best_weights_per_query_type(
    results_dir="data/results"
)

# 2. 성능 Trade-off 분석
analyzer.plot_weight_impact(
    metric="convergence_utilization",
    query_type="comparative"
)

# 3. 최종 가중치 프리셋 업데이트
analyzer.export_optimal_weights(
    output_path="evaluators/intent_aware_evaluator.py",
    preset_name="INTENT_WEIGHT_PRESETS"
)
```

---

## 5. 가중치 해석 가이드

### 5.1 정규화 방식

모든 가중치는 합이 1.0이 되도록 정규화됩니다:

```python
# 입력 가중치 (raw)
raw_weights = {
    "tbox": 1.5,
    "intent": 1.3,
    "coherence": 1.0,
    "validity": 1.2,
    "diversity": 0.8,
    "convergence": 0.5
}

# 정규화 (합 = 1.0)
total = sum(raw_weights.values())  # 6.3
normalized = {k: v / total for k, v in raw_weights.items()}

# 결과
# tbox: 0.238 (23.8%)
# intent: 0.206 (20.6%)
# convergence: 0.079 (7.9%)  ← 가장 낮음
```

### 5.2 가중치 값의 의미

- **0.5 이하**: 거의 무시 (5-8% 비중)
- **0.8 ~ 1.0**: 낮은 중요도 (12-16% 비중)
- **1.2 ~ 1.5**: 높은 중요도 (18-23% 비중)
- **1.6 이상**: 최고 중요도 (24%+ 비중)

### 5.3 실제 점수 계산 예시

**Causal 질문, 모든 raw_metrics = 0.80 가정:**

```python
# Raw Metrics (evaluator 출력)
raw = {
    "tbox": 0.80,
    "intent": 0.80,
    "coherence": 0.80,
    "validity": 0.80,
    "diversity": 0.80,
    "convergence": 0.80
}

# Causal 가중치 (정규화됨)
weights = {
    "tbox": 0.132,           # 1.0 / 7.6
    "intent": 0.184,         # 1.4 / 7.6
    "coherence": 0.171,      # 1.3 / 7.6
    "validity": 0.158,       # 1.2 / 7.6
    "diversity": 0.158,      # 1.2 / 7.6
    "convergence": 0.197     # 1.5 / 7.6 ← 가장 높음
}

# 가중치 적용
weighted = {k: raw[k] * weights[k] for k in raw}

# 최종 점수
final_score = sum(weighted.values())  # 0.80
```

**만약 convergence만 0.50이면?**

```python
raw["convergence"] = 0.50  # 수렴 노드 성능 하락

# 가중치 적용
weighted["convergence"] = 0.50 * 0.197 = 0.099

# 최종 점수
final_score = 0.741  # ← 0.059 하락 (convergence 가중치가 높아서 큰 영향)
```

---

## 6. 실전 가이드: 가중치 튜닝 시나리오

### 시나리오 1: Factual 질문 성능이 낮을 때

**증상:**
```
Factual 질문 평균 점수: 0.65
다른 유형: 0.80+
```

**진단 절차:**
1. Factual 질문의 raw_metrics 확인
2. 어떤 메트릭이 낮은지 파악

**가능한 원인과 해결책:**

| 낮은 메트릭 | 원인 | 가중치 조정 |
|-----------|------|------------|
| TBox Consistency | 스키마 위반 많음 | TBox 가중치 ↑ (1.5 → 2.0) |
| Intent Preservation | 의도 이탈 많음 | Intent 가중치 ↑ (1.3 → 1.8) |
| Convergence | 불필요한 수렴 노드 | Convergence 가중치 ↓ (0.5 → 0.3) |

### 시나리오 2: Comparative 질문에서 교차점을 못 찾을 때

**증상:**
```
Convergence Utilization: 0.40 (너무 낮음)
Final Score: 0.60
```

**해결책:**
```python
# Convergence 가중치 대폭 상향
comparative_weights = create_custom_weights(
    query_type="comparative",
    convergence=2.0,  # 1.6 → 2.0
    diversity=1.6     # 양쪽 증거 필요
)
```

**기대 효과:**
- Convergence가 낮으면 final_score에 큰 페널티
- 시스템이 수렴 노드를 더 적극적으로 찾도록 유도

### 시나리오 3: 새로운 방향(Direction) 추가 시

**상황:**
사용자가 선택한 방향이 `"scope_international"` (국제적 영향)일 때

**실험:**
```python
# 국제 관계는 Evidence Diversity가 중요할 것으로 가정
test_weights = create_custom_weights(
    query_type="causal",
    diversity=1.8,     # 여러 국가 증거 필요
    convergence=1.6    # 국가 간 교차점
)

# 실험 실행
results = evaluate_with_direction(
    query_type="causal",
    preferred_direction="scope_international",
    weights=test_weights
)

# 결과 비교
if results["final_score"] > baseline:
    # 가중치 프리셋에 추가
    DIRECTION_SPECIFIC_WEIGHTS["scope_international"] = test_weights
```

---

## 7. 체크리스트: 가중치 설정 검증

### 7.1 실험 전 체크리스트

- [ ] 테스트 질문이 질문 유형별로 10개 이상 있는가?
- [ ] Baseline 실험을 먼저 실행했는가?
- [ ] 각 질문에 `preferred_direction`이 명시되어 있는가?
- [ ] LLM Judge가 정상 작동하는가? (API 키 확인)

### 7.2 실험 중 체크리스트

- [ ] 각 실험 결과가 JSON 파일로 저장되는가?
- [ ] 실행 시간이 너무 길지 않은가? (timeout 설정)
- [ ] 에러가 발생한 질문을 로그에 기록하는가?

### 7.3 실험 후 체크리스트

- [ ] 가중치 변화에 따라 final_score가 변하는가?
- [ ] 질문 유형별로 최적 가중치가 다른가?
- [ ] Trade-off를 시각화했는가? (그래프/표)
- [ ] 새 가중치로 검증 세트에서 테스트했는가?

---

## 8. 참고: 현재 가중치 설정 요약

### 현재 프리셋 (INTENT_WEIGHT_PRESETS)

| Query Type | TBox | Intent | Coherence | Validity | Diversity | Convergence |
|-----------|------|--------|-----------|----------|-----------|-------------|
| **Factual** | 1.5 ↑ | 1.3 ↑ | 1.0 = | 1.2 ↑ | 0.8 ↓ | **0.5 ↓↓** |
| **Causal** | 1.0 = | 1.4 ↑ | 1.3 ↑ | 1.2 ↑ | 1.2 ↑ | **1.5 ↑↑** |
| **Comparative** | 1.0 = | 1.3 ↑ | 1.2 ↑ | 1.2 ↑ | 1.4 ↑↑ | **1.6 ↑↑↑** |
| **Deep Analysis** | 1.0 = | **1.5 ↑↑** | 1.4 ↑ | 1.3 ↑ | 1.3 ↑ | 1.3 ↑ |

**범례:**
- ↑↑↑ = 최고 중요도 (해당 타입에서 가장 높음)
- ↑↑ = 매우 높음
- ↑ = 높음
- = = 기준 (1.0)
- ↓ = 낮음
- ↓↓ = 매우 낮음

---

## 9. 마무리: 가중치 선택 철학

### 핵심 원칙

1. **질문 의도를 반영하라**
   - Factual ≠ Comparative: 가중치도 달라야 함

2. **실험으로 검증하라**
   - 직관이 아닌 데이터로 결정

3. **Trade-off를 이해하라**
   - 한 메트릭을 올리면 다른 메트릭은 상대적으로 낮아짐

4. **지속적으로 개선하라**
   - 새로운 질문 유형이 추가되면 재실험

### 최종 가이드라인

> **"좋은 가중치란 시스템이 인간 평가자처럼 판단하게 만드는 가중치다."**

- 인간 평가자가 중요하게 여기는 메트릭에 높은 가중치
- 실험 결과와 인간 직관이 일치하는지 확인
- 가중치는 고정이 아닌 **실험을 통해 발견하는 것**

---

## 부록: 실험 결과 템플릿

### A. Ablation Study 결과 예시

```markdown
## Factual 질문 Ablation 결과

| 제거한 메트릭 | Final Score | 하락폭 | 중요도 |
|------------|------------|-------|--------|
| Baseline (제거 없음) | 0.850 | - | - |
| TBox | 0.720 | -0.130 | ⭐⭐⭐ |
| Intent | 0.750 | -0.100 | ⭐⭐⭐ |
| Convergence | 0.840 | -0.010 | ⭐ |

**결론:** Factual 질문에서는 TBox와 Intent가 중요, Convergence는 거의 영향 없음
```

### B. Grid Search 결과 예시

```markdown
## Comparative 질문 Grid Search 결과

| Convergence | Diversity | Final Score |
|------------|-----------|------------|
| 1.0 | 1.0 | 0.750 |
| 1.5 | 1.2 | 0.820 |
| **2.0** | **1.5** | **0.890** ← 최고 |
| 2.5 | 1.8 | 0.870 (과적합) |

**선택:** Convergence=2.0, Diversity=1.5
```

---

**작성일:** 2025-12-24
**버전:** 1.0
**유지보수:** 새로운 질문 유형이나 평가 메트릭 추가 시 업데이트 필요
