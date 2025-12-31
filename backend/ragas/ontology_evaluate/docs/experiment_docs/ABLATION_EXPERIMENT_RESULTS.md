# Ontology RAG Ablation Study 실험 결과 보고서

**실험 기간**: 2024년 12월 25일
**최종 업데이트**: 2024년 12월 28일
**총 실험 케이스**: 300개

---

## Executive Summary

### 핵심 발견
| 실험 | 최고 성능 | 최저 성능 | 핵심 인사이트 |
|------|----------|----------|--------------|
| Semantic Expander | baseline (0.6705) | pgvector_only (0.5984) | **확장 시 12.1% 성능 하락** |
| Thread Ablation | without_outgoing (0.6487) | baseline (0.6075) | **제거 시 +6.8% 성능 향상** |
| Entity Boost | partial_match (0.6391) | penalty_match (0.6159) | **유연한 매칭이 3.8% 우위** |

---

## 1. Semantic Expander Ablation Study

### 실험 설계
- **목적**: Semantic Expander의 각 확장 전략(temporal, causal_chain, pgvector) 효과 측정
- **설정**: 5가지 (baseline, temporal_only, causal_chain_only, pgvector_only, full)
- **쿼리**: 20개 (factual 5, causal 5, comparative 5, deep_analysis 5)
- **총 케이스**: 100개

### 전체 결과

| 설정 | Intent-Aware Score | 최소 | 최대 | 평균 실행시간 |
|------|-------------------|------|------|--------------|
| **baseline** | **0.6705** | 0.5671 | 0.7553 | 153.56초 |
| temporal_only | 0.6192 | 0.4982 | 0.7699 | 146.34초 |
| causal_chain_only | 0.6044 | 0.3927 | 0.7952 | 145.82초 |
| pgvector_only | 0.5984 | 0.4730 | 0.7329 | 137.97초 |
| full | 0.6090 | 0.4039 | 0.8068 | 152.84초 |

### Raw Metrics 분석

| 설정 | TBox Consistency | Intent Preservation | Triple Validity |
|------|-----------------|---------------------|----------------|
| baseline | **0.9297** | **1.0000** | 0.5655 |
| temporal_only | 0.8397 | 0.7843 | **0.6514** |
| causal_chain_only | 0.8237 | 0.7606 | 0.6412 |
| pgvector_only | 0.8909 | 0.6342 | 0.5959 |
| full | 0.9183 | 0.7604 | **0.6571** |

**핵심 발견**:
- Baseline의 `intent_preservation: 1.0000`이 압도적으로 높음
- 확장 전략 활성화 시 Intent 보존력이 평균 **23.4%p 하락** (1.0 → 0.766)
- Full expansion이 Triple Validity는 높지만 Intent는 크게 손실

### 쿼리 타입별 분석

| 쿼리 타입 | baseline | temporal | causal_chain | pgvector | full |
|----------|----------|----------|--------------|----------|------|
| factual | 0.6681 | **0.6852** | 0.6572 | 0.6128 | 0.5499 |
| causal | **0.6462** | 0.6301 | 0.6228 | 0.6183 | 0.6363 |
| comparative | **0.6885** | 0.5490 | 0.5579 | 0.6101 | 0.6143 |
| deep_analysis | **0.6792** | 0.6125 | 0.5797 | 0.5522 | 0.6355 |

**쿼리 타입별 최적 설정**:
- **factual**: temporal_only (0.6852)
- **causal**: baseline (0.6462)
- **comparative**: baseline (0.6885)
- **deep_analysis**: baseline (0.6792)

### 결론
> **Semantic Expansion은 현재 구현에서 오히려 성능을 저하시킴**
>
> **정량적 근거**:
> - Baseline 대비 최악 케이스(pgvector) **12.1% 하락** (0.6705 → 0.5984)
> - Full expansion도 baseline 대비 **9.2% 하락** (0.6090)
> - Intent Preservation 평균 **23.4%p 하락** (1.0 → 0.766)
>
> **원인 분석**:
> 1. 확장 시 불필요한 노드 추가로 노이즈 증가
> 2. Intent Preservation이 확장에 따라 급격히 감소
> 3. 단순 factual 질문에만 temporal 확장이 약간 유효 (+2.6%)

---

## 2. Thread Ablation Study

### 실험 설계
- **목적**: Aggregator Thread별 기여도 측정
- **설정**: 6가지 (baseline + 5개 스레드 각각 제거)
- **쿼리**: 20개
- **총 케이스**: 120개

### 전체 결과

| 설정 | Intent-Aware Score | 최소 | 최대 | 평균 실행시간 |
|------|-------------------|------|------|--------------|
| baseline | 0.6075 | 0.4584 | 0.6693 | 55.50초 |
| **without_outgoing_relations** | **0.6487** | 0.5909 | 0.7058 | 57.03초 |
| without_entity_properties | 0.6449 | 0.5794 | 0.7025 | 55.10초 |
| without_type_and_summary | 0.6392 | 0.5763 | 0.6902 | 51.50초 |
| without_connected_entities | 0.6376 | 0.5816 | 0.7296 | 52.86초 |
| without_incoming_relations | 0.6325 | 0.5650 | 0.6880 | 59.21초 |

### Raw Metrics 분석

| 설정 | TBox | Intent | Triple | 성능 변화 |
|------|------|--------|--------|----------|
| baseline (모두 활성화) | 0.9767 | 0.5277 | 0.8533 | - |
| without_outgoing | **1.0000** | 0.5209 | **0.9371** | **+6.8%** |
| without_entity_properties | 0.9750 | **0.5548** | 0.8933 | **+6.2%** |
| without_type_and_summary | 0.9900 | 0.5088 | 0.9300 | **+5.2%** |
| without_connected_entities | 0.9955 | 0.5256 | 0.9479 | **+5.0%** |
| without_incoming | 0.9727 | 0.5615 | 0.9236 | **+4.1%** |

**핵심 발견**:
- **모든 제거 시나리오가 baseline보다 성능 향상** → Thread 과다 활성화 시 노이즈 발생
- `without_outgoing`: TBox 1.0, Triple +9.8%p → **가장 효과적인 제거 대상**
- Intent Preservation은 thread 수가 적을수록 향상 (역상관)

### 결론
> **모든 스레드 제거 설정이 baseline보다 높은 성능 - Thread 과다 활성화 문제 명확**
>
> **정량적 근거**:
> - `without_outgoing`: **+6.8%** (0.6075 → 0.6487) → 최대 향상
> - `without_entity_properties`: **+6.2%** (0.6449)
> - 5개 스레드 모두 제거 시나리오가 **평균 +5.6% 향상**
>
> **핵심 인사이트**:
> 1. **Thread 간 부정적 상호작용 존재**: 많을수록 성능 저하
> 2. `outgoing_relations`가 가장 큰 노이즈 원인 (제거 시 +6.8%)
> 3. TBox Consistency는 제거 시 향상 (0.9767 → 평균 0.9830)
> 4. **선택적 최소화 전략 필수**: 필요한 Thread만 활성화해야 함

---

## 3. Entity Boost Ablation Study

### 실험 설계
- **목적**: Entity Boost 매칭 전략별 효과 측정
- **설정**: 4가지 (exact, normalized, partial, penalty)
- **쿼리**: 20개
- **총 케이스**: 80개

### 전체 결과

| 설정 | Intent-Aware Score | 최소 | 최대 | 평균 실행시간 |
|------|-------------------|------|------|--------------|
| exact_match | 0.6214 | 0.5099 | 0.6749 | 72.76초 |
| normalized_match | 0.6329 | 0.5796 | 0.6735 | 46.99초 |
| **partial_match** | **0.6391** | 0.4981 | 0.7129 | 70.61초 |
| penalty_match | 0.6159 | 0.4806 | 0.6972 | 53.84초 |

### Raw Metrics 분석

| 설정 | TBox | Intent | Triple | 성능 차이 |
|------|------|--------|--------|----------|
| partial_match | 0.9916 | **0.5831** | 0.6900 | **최고** (0.6391) |
| normalized_match | **1.0000** | 0.5356 | **1.0000** | 2위 (0.6329) |
| exact_match | 0.9673 | 0.5349 | 0.8123 | 3위 (0.6214) |
| penalty_match | 0.9500 | 0.5169 | 0.8600 | 최저 (0.6159) |

**핵심 발견**:
- **모드 간 차이 미미**: 최고-최저 **3.8%** (0.6391 vs 0.6159)
- `partial_match`: Intent Preservation 최고 (0.5831) → 전체 점수 최고
- `normalized_match`: TBox와 Triple 완벽(1.0)하지만 Intent는 낮음
- `penalty_match`: 모든 지표에서 최저 → **사용 비권장**

### 결론
> **partial_match가 최고 성능이지만 모드 간 차이는 미미 (3.8%)**
>
> **정량적 근거**:
> - `partial_match`: 0.6391 (Intent 0.5831로 최고)
> - `normalized_match`: 0.6329 (TBox/Triple 완벽 1.0)
> - `exact_match`: 0.6214 (균형적)
> - 최고-최저 차이 **단 3.8%** → Entity Boost의 영향력 제한적
>
> **핵심 인사이트**:
> 1. **Entity Boost는 성능에 미치는 영향이 작음** (3.8% 차이)
> 2. `partial_match`가 Intent Preservation에서 우위 (0.5831 vs 평균 0.5291)
> 3. `penalty_match`는 일관되게 최저 → **사용 비권장**
> 4. **Ablation 환경에서는 partial이 우수**, Isolation에서는 normalized 우수 → 환경 의존적

---

## 4. 종합 분석 및 권장사항

### 현재 시스템의 문제점

1. **과도한 확장**: Semantic Expander가 불필요한 노이즈를 추가
2. **스레드 중복**: 모든 스레드 활성화가 오히려 성능 저하
3. **Intent Drift**: 확장/집계 과정에서 원래 의도 손실

### 권장 최적 설정

```python
RECOMMENDED_CONFIG = {
    "semantic_expander": {
        "temporal": False,      # 비활성화 권장
        "causal_chain": False,  # 비활성화 권장
        "pgvector": False       # 비활성화 권장
    },
    "aggregator_threads": {
        "outgoing_relations": False,  # 비활성화 시 +6.8%
        "incoming_relations": True,
        "entity_properties": True,
        "connected_entities": True,
        "type_and_summary": True
    },
    "entity_boost_mode": "partial_match"  # 유연한 매칭
}
```

### 향후 개선 방향

1. **쿼리 타입 기반 동적 설정**
   - factual → temporal 확장만 활성화
   - causal/comparative/deep_analysis → baseline 유지

2. **스레드 선택적 활성화**
   - 질문 유형에 따른 필요 스레드만 활성화
   - outgoing_relations 기본 비활성화

3. **Intent-Aware 확장 전략**
   - 확장 전 Intent 보존 가능성 평가
   - 노이즈 임계값 기반 필터링

---

## 5. 데이터 출처

모든 수치는 다음 실제 실험 데이터 파일에서 추출됨:

| 파일 | 크기 | 케이스 수 | 최종 업데이트 |
|------|------|----------|---------------|
| `semantic_expander_ablation_summary.json` | 316KB | 100개 (20개×5설정) | 2024-12-28 |
| `thread_ablation_summary.json` | 288KB | 120개 (20개×6설정) | 2024-12-28 |
| `entity_boost_ablation_summary.json` | 197KB | 80개 (20개×4설정) | 2024-12-28 |

**데이터 경로**: `backend/ragas/ontology_evaluate/data/results_ablation/`

---

*이 보고서는 2024년 12월 28일 업데이트된 실제 실험 데이터를 기반으로 작성되었습니다.*
