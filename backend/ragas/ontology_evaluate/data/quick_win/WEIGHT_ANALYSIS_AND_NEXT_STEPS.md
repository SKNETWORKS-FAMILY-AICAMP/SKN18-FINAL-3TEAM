# Ontology RAG 가중치 실험 종합 분석 및 다음 단계

**실험일**: 2024년 12월 26일  
**데이터**: 총 300개 케이스 (Semantic Expander 100 + Thread 120 + Entity Boost 80)

---

## Executive Summary

### 핵심 발견

| 발견 | 내용 | 영향도 |
|------|------|--------|
| 가중치가 최적 설정을 결정 | Intent 가중치 변경 시 Thread 최적 설정이 역전 | ★★★ |
| Intent vs Triple 트레이드오프 | Entity Boost에서 두 메트릭 간 상충 관계 발견 | ★★★ |
| Semantic Expander가 가장 민감 | 설정 간 Gap 0.2004로 가장 큼 | ★★☆ |

---

## 1. 가중치 변경에 따른 최적 설정 역전 현상

### 1.1 Thread Ablation: Outgoing vs Incoming

#### Raw Metrics 비교

| 메트릭 | Outgoing 제거 | Incoming 제거 | 유리한 쪽 |
|--------|--------------|--------------|----------|
| tbox_consistency | **1.0000** | 0.9727 | Outgoing |
| **intent_preservation** | 0.5209 | **0.5615** | **Incoming (+0.04)** |
| triple_validity | **0.9371** | 0.9236 | Outgoing |

#### 가중치별 승자 변화

| 가중치 설정 | Outgoing 제거 | Incoming 제거 | Winner |
|------------|--------------|--------------|--------|
| Equal (모두 1.0) | **0.6478** | 0.6476 | **Outgoing** |
| Aggressive (intent=5) | 0.6400 | **0.6570** | **Incoming** |

#### 역전 원인

```
Equal Weights:
  → tbox(1.0) + triple(0.94) 합산 → Outgoing 승

Aggressive Intent:
  → intent × 5배 반영 → 0.5615 × 5 = 2.81 vs 0.5209 × 5 = 2.60
  → Intent 차이(+0.04)가 5배로 증폭 → Incoming 역전승!
```

**결론**: Intent를 중시하면 Incoming 제거, 전통적 메트릭(tbox/triple)을 중시하면 Outgoing 제거

---

### 1.2 Entity Boost: Partial vs Normalized

#### Raw Metrics 비교

| 메트릭 | Partial | Normalized | 차이 |
|--------|---------|------------|------|
| **intent_preservation** | **0.5831** | 0.5356 | Partial +0.048 |
| **triple_validity** | 0.6900 | **1.0000** | Normalized +0.31 ★ |
| evidence_diversity | 0.1569 | 0.0000 | Partial +0.16 |

#### Intent:Triple 비율별 승자

| Intent:Triple | Partial | Normalized | Winner |
|---------------|---------|------------|--------|
| 1:1 | 0.6988 | 0.7337 | **Normalized** |
| 2:1 | 0.6810 | 0.7033 | **Normalized** |
| 3:1 | 0.6679 | 0.6809 | **Normalized** |
| **5:1** | 0.6501 | 0.6503 | **동점** |
| 3:3 | 0.6726 | 0.7481 | **Normalized** |

#### 트레이드오프 분석

```
Partial의 강점:
  - Intent Preservation: 0.5831 (높음)
  - Evidence Diversity: 0.1569 (있음)
  - 유연한 매칭으로 더 많은 관련 정보 수집

Normalized의 강점:
  - Triple Validity: 1.0000 (완벽!)
  - TBox Consistency: 1.0000 (완벽!)
  - 정확한 매칭으로 노이즈 없음
```

**결론**: 
- Intent만 극단적으로 높이면 (5:1) → 동점
- Intent와 Triple 둘 다 중요하면 → Normalized 우세
- Intent를 압도적으로 중시하면 → Partial 우세

---

## 2. 실험별 민감도 분석

### Gap 비교 (Best - Worst)

```
Semantic Expander:  ████████████████████████████████████████  0.2004 (가장 민감)
Entity Boost:       ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0.0298
Thread Ablation:    ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0.0287
```

### 해석

| 실험 | Gap | 의미 |
|------|-----|------|
| Semantic Expander | 0.2004 | 설정 선택이 성능에 **결정적** 영향 |
| Thread Ablation | 0.0287 | 설정 간 차이 작음, **미세 튜닝** 영역 |
| Entity Boost | 0.0298 | 설정 간 차이 작음, **미세 튜닝** 영역 |

**우선순위**: Semantic Expander OFF가 가장 중요한 설정

---

## 3. 현재 권장 설정

### 확정 설정

```python
CONFIRMED_CONFIG = {
    # Semantic Expander - 확정 (모든 가중치에서 baseline 최적)
    "semantic_expander": {
        "temporal": False,
        "causal_chain": False,
        "pgvector": False,
    },
}
```

### 가중치 의존 설정

| 가중치 전략 | Thread | Entity Boost |
|------------|--------|--------------|
| Intent 중시 (5:1) | without_incoming | Partial ≈ Normalized |
| 균형 (3:3) | without_outgoing | Normalized |
| Triple 중시 (1:3) | without_outgoing | Normalized |

---

## 4. 미해결 질문

1. **최적 가중치는 무엇인가?**
   - Intent:Triple 비율을 어떻게 설정해야 하는가?
   - Human Evaluation 없이 객관적 기준이 있는가?

2. **쿼리 타입별 가중치가 달라야 하는가?**
   - factual: Triple 중시?
   - causal/deep_analysis: Intent 중시?

3. **메트릭 간 상관관계는?**
   - Intent↑ → Triple↓ 인가?
   - 두 메트릭을 동시에 높일 수 있는가?

---

## 5. 다음 실험 제안

### 실험 A: Human Evaluation 기반 가중치 검증 ⭐ 권장

**목적**: 실제 답변 품질과 메트릭 간 상관관계 파악

```
방법:
1. 50개 대표 케이스 선정 (점수 분포 다양하게)
2. 각 답변에 Human Score (1-5점) 부여
3. 회귀 분석으로 최적 가중치 도출

Human_Score = w1×intent + w2×triple + w3×tbox + ...

예상 소요: 4-5시간
기대 효과: 객관적 가중치 결정
```

### 실험 B: 쿼리 타입별 최적 가중치 탐색

**목적**: 질문 유형에 따른 맞춤 가중치 발견

```
방법:
1. 쿼리 타입별로 분리 (factual, causal, comparative, deep_analysis)
2. 각 타입에서 가중치 Grid Search
3. 타입별 최적 가중치 도출

실험 설계:
- factual (10개): Intent vs Triple 비율 테스트
- causal (10개): Intent vs Triple 비율 테스트
- ...

예상 소요: 2시간 (자동화)
기대 효과: 쿼리 라우팅 전략 수립
```

### 실험 C: 복합 설정 최적화

**목적**: Thread + Entity Boost 조합 최적화

```
방법:
1. Thread 6가지 × Entity Boost 4가지 = 24개 조합
2. 각 조합에서 aggressive_intent 가중치로 평가
3. 최적 조합 발견

현재 데이터로 시뮬레이션 가능 (실제 실험 불필요)

예상 소요: 30분
기대 효과: 최적 조합 확인
```

### 실험 D: Intent-Triple 동시 최적화 가능성 탐색

**목적**: 두 메트릭을 동시에 높일 수 있는 설정 탐색

```
방법:
1. 모든 설정에서 Intent × Triple 곱 계산
2. 곱이 최대인 설정 탐색
3. 파레토 최적 설정 도출

가설: 현재 설정들은 Intent-Triple 트레이드오프 관계
검증: 둘 다 높은 "황금 설정"이 존재하는가?
```

---

## 6. 권장 실험 순서

| 순서 | 실험 | 소요 시간 | 기대 가치 |
|------|------|----------|----------|
| 1 | **실험 C**: 복합 설정 최적화 | 30분 | 빠른 확인 |
| 2 | **실험 B**: 쿼리 타입별 가중치 | 2시간 | 실용적 인사이트 |
| 3 | **실험 D**: Intent-Triple 동시 최적화 | 1시간 | 이론적 한계 파악 |
| 4 | **실험 A**: Human Evaluation | 4-5시간 | 최종 검증 |

---

## 7. 즉시 실행 가능한 코드

### 실험 C: 복합 설정 시뮬레이션

```python
# Thread × Entity Boost 조합 시뮬레이션
THREAD_OPTIONS = ['baseline', 'without_outgoing', 'without_incoming', ...]
ENTITY_OPTIONS = ['exact', 'normalized', 'partial', 'penalty']

for thread in THREAD_OPTIONS:
    for entity in ENTITY_OPTIONS:
        score = simulate_combined(thread, entity, weights)
        print(f"{thread} + {entity}: {score}")
```

### 실험 B: 쿼리 타입별 분석

```python
# 쿼리 타입별 최적 가중치 탐색
QUERY_TYPES = ['factual', 'causal', 'comparative', 'deep_analysis']
WEIGHT_RATIOS = [(1,1), (2,1), (3,1), (1,2), (1,3), (2,2), (3,3)]

for qt in QUERY_TYPES:
    for int_w, tri_w in WEIGHT_RATIOS:
        score = evaluate_query_type(qt, int_w, tri_w)
        print(f"{qt} @ {int_w}:{tri_w}: {score}")
```

---

## 부록: 핵심 수치 요약

### Thread Ablation (aggressive_intent 기준)

| 설정 | Score | Intent | Triple |
|------|-------|--------|--------|
| without_incoming | **0.6570** | **0.5615** | 0.9236 |
| without_outgoing | 0.6400 | 0.5209 | **0.9371** |
| baseline | 0.6283 | 0.5277 | 0.8533 |

### Entity Boost (aggressive_intent 기준)

| 설정 | Score | Intent | Triple |
|------|-------|--------|--------|
| normalized | **0.6503** | 0.5356 | **1.0000** |
| partial | 0.6501 | **0.5831** | 0.6900 |
| exact | 0.6375 | 0.5349 | 0.8123 |
| penalty | 0.6205 | 0.5169 | 0.8600 |

---

*이 문서는 300개 실험 케이스의 가중치 민감도 분석을 기반으로 작성되었습니다.*
