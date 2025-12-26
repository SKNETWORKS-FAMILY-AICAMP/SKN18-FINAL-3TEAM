# Ontology RAG Ablation Study 실험 결과 보고서

**실험 기간**: 2024년 12월 25일  
**데이터 검증일**: 2024년 12월 26일  
**총 실험 케이스**: 300개

---

## Executive Summary

### 핵심 발견
| 실험 | 최고 성능 | 최저 성능 | 핵심 인사이트 |
|------|----------|----------|--------------|
| Semantic Expander | baseline (0.6705) | pgvector_only (0.5984) | **확장 시 9.2% 성능 하락** |
| Thread Ablation | without_outgoing (0.6487) | baseline (0.6075) | **제거 시 성능 향상** |
| Entity Boost | partial_match (0.6391) | penalty_match (0.6159) | **유연한 매칭이 효과적** |

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

| 설정 | TBox Consistency | Intent Preservation | Relation Coherence | Triple Validity |
|------|-----------------|---------------------|-------------------|----------------|
| baseline | 0.9297 | **1.0000** | 0.5838 | 0.5655 |
| temporal_only | 0.8397 | 0.7843 | 0.4971 | 0.6514 |
| causal_chain_only | 0.8237 | 0.7606 | 0.4842 | 0.6412 |
| pgvector_only | 0.8909 | 0.6342 | 0.5304 | 0.5959 |
| full | 0.9183 | 0.7604 | 0.4375 | 0.6571 |

**핵심 발견**: Baseline의 `intent_preservation: 1.0000`이 가장 높음. 확장 시 의도 보존력 저하.

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
> **Semantic Expansion은 현재 구현에서 오히려 성능을 저하시킴 (9.2% 하락)**
> 
> 원인 분석:
> 1. 확장 시 불필요한 노드 추가로 노이즈 증가
> 2. Intent Preservation이 확장에 따라 급격히 감소
> 3. 단순 factual 질문에만 temporal 확장이 유효

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

| 설정 | TBox | Intent | Relation | Triple | Evidence |
|------|------|--------|----------|--------|----------|
| baseline | 0.9767 | 0.5277 | 1.0000 | 0.8533 | 0.0000 |
| without_outgoing | **1.0000** | 0.5209 | 1.0000 | 0.9371 | 0.0765 |
| without_entity_properties | 0.9750 | **0.5548** | 1.0000 | 0.8933 | 0.0757 |
| without_incoming | 0.9727 | 0.5615 | 1.0000 | 0.9236 | 0.0754 |

### 결론
> **모든 스레드 제거 설정이 baseline보다 높은 성능**
> 
> 핵심 인사이트:
> 1. Outgoing relations 제거 시 최고 성능 (+6.8%)
> 2. 스레드가 많을수록 노이즈 증가 가능성
> 3. 스레드 선택적 활성화 전략 필요

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

| 설정 | TBox | Intent | Triple | Evidence |
|------|------|--------|--------|----------|
| exact_match | 0.9673 | 0.5349 | 0.8123 | 0.2043 |
| normalized_match | **1.0000** | 0.5356 | **1.0000** | 0.0000 |
| partial_match | 0.9916 | **0.5831** | 0.6900 | 0.1569 |
| penalty_match | 0.9500 | 0.5169 | 0.8600 | 0.0000 |

### 결론
> **partial_match가 최고 성능, 유연한 매칭이 효과적**
> 
> 핵심 인사이트:
> 1. Partial match가 Intent Preservation에서 우위
> 2. Normalized match는 안정적이나 evidence diversity 부족
> 3. Penalty match는 과도한 제약으로 성능 저하

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

모든 수치는 다음 실제 실험 데이터 파일에서 검증됨:

| 파일 | 크기 | 케이스 수 |
|------|------|----------|
| `semantic_expander_ablation_summary.json` | 323KB | 100개 |
| `thread_ablation_summary.json` | 295KB | 120개 |
| `entity_boost_ablation_summary.json` | 201KB | 80개 |

---

*이 보고서는 실제 실험 데이터를 기반으로 검증되었습니다.*
