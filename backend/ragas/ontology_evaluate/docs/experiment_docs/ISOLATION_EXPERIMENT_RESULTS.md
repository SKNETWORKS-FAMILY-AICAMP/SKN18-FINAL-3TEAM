# Ontology RAG Isolation Study 실험 결과 보고서

**실험 기간**: 2024년 12월 27일  
**총 실험 케이스**: 240개 (Semantic 60 + Entity Boost 80 + Thread 100)  
**실험 유형**: 컴포넌트 단독 활성화 테스트 (Isolation Study)

---

## Executive Summary

### 핵심 발견
| 실험 | 최고 성능 | 최저 성능 | 핵심 인사이트 |
|------|----------|----------|--------------|
| Semantic Expander | **causal_chain (0.7450)** | pgvector (0.6552) | **causal_chain이 13.7% 우위** |
| Entity Boost | **normalized (0.7159)** | partial (0.7015) | **차이 미미 (2.1%)** |
| Thread Aggregator | **type_and_summary (0.7556)** | incoming (0.6763) | **type_and_summary 11.7% 우위** |

### Ablation Study vs Isolation Study 비교

| 관점 | Ablation (제거 테스트) | Isolation (단독 테스트) |
|------|----------------------|----------------------|
| Semantic Expander | baseline(확장없음) 최고 | causal_chain 단독 최고 |
| Thread | 제거 시 성능 향상 | type_and_summary 단독 최고 |
| Entity Boost | partial_match 최고 | normalized 최고 |

**결론**: 컴포넌트 간 **부정적 상호작용** 존재. 단독 시 효과적인 컴포넌트도 조합 시 노이즈 발생.

---

## 1. Semantic Expander Isolation Study

### 실험 설계
- **목적**: 각 확장 전략을 **단독으로** 활성화했을 때의 순수 효과 측정
- **설정**: 3가지 (temporal_only, causal_chain_only, pgvector_only)
- **쿼리**: 20개 (factual 5, causal 5, comparative 5, deep_analysis 5)
- **총 케이스**: 60개

### 전체 결과

| 설정 | Intent-Aware Score | 최소 | 최대 | Evidence有 | 평균 실행시간 |
|------|-------------------|------|------|-----------|--------------|
| **causal_chain_only** | **0.7450** | 0.5471 | 1.0139 | 19/20 | 154.12초 |
| temporal_only | 0.6717 | 0.5166 | 0.8873 | 20/20 | 149.52초 |
| pgvector_only | 0.6552 | 0.5208 | 0.8548 | 19/20 | 158.56초 |

### Raw Metrics 분석

| 설정 | TBox Consistency | Intent Preservation | Relation Coherence | Triple Validity | Evidence Diversity |
|------|-----------------|---------------------|-------------------|----------------|-------------------|
| **causal_chain_only** | 0.9117 | **0.7832** | 1.0000 | **0.5317** | 0.4362 |
| temporal_only | 0.9285 | 0.6558 | 1.0000 | 0.4688 | 0.4107 |
| pgvector_only | **0.9552** | 0.6137 | 1.0000 | 0.4784 | **0.4445** |

**핵심 발견**: 
- `causal_chain`이 **Intent Preservation (0.7832)**에서 압도적 우위
- `pgvector`는 TBox Consistency가 높지만 Intent 보존력 낮음

### 쿼리 타입별 분석

| 쿼리 타입 | temporal | causal_chain | pgvector | 최적 설정 | 차이(Δ) |
|----------|----------|--------------|----------|----------|---------|
| factual | 0.7007 | **0.7392** | 0.6402 | **causal_chain** | +5.5% |
| causal | **0.6994** | 0.6862 | 0.6789 | **temporal** | +1.9% |
| comparative | 0.6100 | **0.9104** | 0.6456 | **causal_chain** | +49.2% |
| deep_analysis | **0.6768** | 0.6442 | 0.6560 | **temporal** | +5.1% |

**쿼리 타입별 권장**:
- **comparative (비교 질문)**: causal_chain 필수 (+49.2% 향상)
- **factual (사실 질문)**: causal_chain 권장
- **causal/deep_analysis**: temporal 약간 우위

### 결론
> **causal_chain이 단독으로 가장 효과적 (0.7450)**
> 
> 핵심 인사이트:
> 1. Intent Preservation에서 causal_chain이 19.6%p 높음 (0.7832 vs 0.6137)
> 2. 비교 질문에서 causal_chain이 49.2% 향상
> 3. Ablation에서 "확장 없음"이 최고였던 이유: **조합 시 노이즈 발생**

---

## 2. Entity Boost Isolation Study

### 실험 설계
- **목적**: Entity Boost 매칭 전략별 순수 효과 측정
- **설정**: 4가지 (exact, partial, normalized, none)
- **쿼리**: 20개
- **총 케이스**: 80개

### 전체 결과

| 설정 | Intent-Aware Score | 최소 | 최대 | Evidence有 | 평균 실행시간 |
|------|-------------------|------|------|-----------|--------------|
| **normalized_match** | **0.7159** | 0.5308 | 0.9988 | 16/20 | 132.27초 |
| exact_match | 0.7074 | 0.4700 | 0.9663 | 16/20 | 130.06초 |
| none | 0.7056 | 0.5577 | 0.9860 | 16/20 | 131.78초 |
| partial_match | 0.7015 | 0.5659 | 0.9606 | 16/20 | 130.38초 |

### Raw Metrics 분석

| 설정 | TBox Consistency | Intent Preservation | Triple Validity | Evidence Diversity |
|------|-----------------|---------------------|----------------|-------------------|
| **none** | **0.9823** | 0.7032 | 0.5850 | 0.2396 |
| partial_match | 0.9689 | 0.7046 | 0.5366 | 0.2711 |
| normalized_match | 0.9650 | 0.7074 | **0.6429** | 0.3116 |
| exact_match | 0.9527 | **0.7130** | 0.5439 | **0.3179** |

### 질문별 최적 모드 분포

| 모드 | 최적인 질문 수 | 비율 |
|------|--------------|------|
| **exact_match** | 7/20 | 35% |
| **normalized_match** | 6/20 | 30% |
| none | 2/20 | 10% |
| partial_match | 0/20 | 0% |

### 결론
> **normalized_match가 전체 평균 최고, exact_match가 개별 질문에서 더 자주 최적**
> 
> 핵심 인사이트:
> 1. 모드 간 차이가 **2.1%로 미미** (0.7015 ~ 0.7159)
> 2. **partial_match는 단 한 번도 최적이 아님** → 사용 비권장
> 3. Ablation에서 partial이 최고였던 이유: 다른 컴포넌트와의 조합 효과

---

## 3. Thread Aggregator Isolation Study

### 실험 설계
- **목적**: 각 Thread를 **단독으로** 활성화했을 때의 순수 효과 측정
- **설정**: 5가지 (각 Thread 단독)
- **쿼리**: 20개
- **총 케이스**: 100개

### 전체 결과

| 설정 | Intent-Aware Score | 최소 | 최대 | Evidence有 | 평균 실행시간 |
|------|-------------------|------|------|-----------|--------------|
| **type_and_summary_only** | **0.7556** | 0.6316 | 1.0000 | 15/20 | 109.80초 |
| connected_entities_only | 0.7381 | 0.6316 | 0.9737 | **3/20** ⚠️ | 71.99초 |
| entity_properties_only | 0.7189 | 0.5509 | 0.9965 | 15/20 | 114.13초 |
| outgoing_relations_only | 0.7161 | 0.4842 | 0.9509 | 16/20 | 112.03초 |
| incoming_relations_only | 0.6763 | 0.5263 | 0.8561 | 16/20 | 110.16초 |

### 성능 차이 분석

| 비교 | 차이 | 해석 |
|------|------|------|
| type_and_summary vs incoming | +11.7% | **가장 큰 차이** |
| type_and_summary vs outgoing | +5.5% | 유의미한 차이 |
| connected_entities 문제점 | Evidence 15%만 | 점수는 높지만 신뢰도 낮음 |

### 결론
> **type_and_summary가 가장 안정적이고 효과적**
> 
> 핵심 인사이트:
> 1. `type_and_summary`: 점수 최고 + Evidence 생성률 우수 (75%)
> 2. `connected_entities`: 점수는 높지만 **Evidence 15%만 생성** → 신뢰도 문제
> 3. `incoming_relations`: 일관되게 낮은 성능 → **비활성화 권장**
> 4. Ablation에서 "outgoing 제거 시 성능 향상"의 의미: 단독으로는 괜찮지만 조합 시 노이즈

---

## 4. Ablation vs Isolation 종합 비교

### 상충되는 결과 분석

| 컴포넌트 | Ablation 결론 | Isolation 결론 | 해석 |
|----------|--------------|---------------|------|
| Semantic Expander | 확장 없음이 최고 | causal_chain 단독 최고 | **조합 시 상호 간섭** |
| outgoing_relations | 제거 시 +6.8% | 단독 시 0.7161 (양호) | **다른 Thread와 충돌** |
| Entity Boost | partial_match 최고 | normalized 최고 | **환경 의존적** |

### 핵심 발견: 부정적 상호작용 (Negative Interaction)

```
단독 성능:  causal_chain (0.7450) > temporal (0.6717) > pgvector (0.6552)
조합 성능:  baseline (확장없음, 0.6705) > full (모두활성화, 0.6090)

⚠️ 단독으로 좋은 컴포넌트도 조합하면 성능 하락
```

---

## 5. 권장 설정

### A. 단순 최적 설정 (Isolation 기반)

```python
SIMPLE_OPTIMAL = {
    "semantic_expander": {
        "temporal": False,
        "causal_chain": True,   # ⭐ 단독 최고 성능
        "pgvector": False
    },
    "aggregator_threads": {
        "outgoing_relations": True,
        "incoming_relations": False,  # ❌ 일관되게 낮음
        "entity_properties": True,
        "connected_entities": False,  # ⚠️ Evidence 생성 문제
        "type_and_summary": True      # ⭐ 최고 성능
    },
    "entity_boost_mode": "normalized"  # 또는 "exact"
}
```

### B. 쿼리 타입별 동적 설정 (권장)

```python
def get_optimal_config(query_type: str):
    base_config = {
        "aggregator_threads": {
            "type_and_summary": True,
            "entity_properties": True,
            "outgoing_relations": True,
            "incoming_relations": False,
            "connected_entities": False
        },
        "entity_boost_mode": "normalized"
    }
    
    if query_type == "comparative":
        # 비교 질문: causal_chain 49.2% 향상
        base_config["semantic_expander"] = {
            "causal_chain": True,
            "temporal": False,
            "pgvector": False
        }
    elif query_type in ["factual", "causal"]:
        # 사실/인과 질문: causal 또는 temporal
        base_config["semantic_expander"] = {
            "causal_chain": True,
            "temporal": True,
            "pgvector": False
        }
    else:
        # deep_analysis: temporal 약간 우위
        base_config["semantic_expander"] = {
            "temporal": True,
            "causal_chain": False,
            "pgvector": False
        }
    
    return base_config
```

---

## 6. Grid Search 필요성 분석

### 이미 확인된 사항 ✅
1. **단독 컴포넌트 효과**: causal_chain, type_and_summary가 최고
2. **비효과적 컴포넌트**: incoming_relations, partial_match
3. **쿼리 타입별 경향**: comparative에서 causal_chain 압도적

### Grid Search로 확인 필요한 사항 🔍
1. **최적 조합 탐색**: causal_chain + temporal 조합 효과?
2. **Thread 조합**: type_and_summary + entity_properties만 활성화 시?
3. **정밀 튜닝**: 2~3개 컴포넌트 조합의 상호작용

### 권장 Grid Search 범위

```python
# 축소된 Grid (8개 조합)
GRID_CONFIGS = [
    # 1. Isolation 기반 최적
    {"causal": True, "threads": ["type_and_summary", "entity_properties"]},
    
    # 2. causal + temporal 조합
    {"causal": True, "temporal": True, "threads": ["type_and_summary"]},
    
    # 3. 모든 semantic + 최소 thread
    {"causal": True, "temporal": True, "pgvector": True, "threads": ["type_and_summary"]},
    
    # 4-8. Entity Boost 변형...
]
```

---

## 7. 데이터 출처

| 파일 | 케이스 수 | 성공률 | Evidence有 비율 |
|------|----------|--------|----------------|
| `semantic_expander_isolation_summary.json` | 60 | 100% | 96.7% |
| `entity_boost_isolation_summary.json` | 80 | 100% | 80% |
| `thread_temp.json` | 100 | 100% | 65% |

---

## 8. 결론 및 Next Steps

### 핵심 결론

1. **Semantic Expander**: `causal_chain` 단독이 가장 효과적 (0.7450)
2. **Thread Aggregator**: `type_and_summary` 최우선, `incoming_relations` 비활성화
3. **Entity Boost**: `normalized` 또는 `exact` (차이 미미)
4. **조합 주의**: 단독으로 좋은 컴포넌트도 조합 시 성능 하락 가능

### 즉시 적용 가능 사항

- `incoming_relations` 비활성화 → 즉시 적용
- `connected_entities` 비활성화 → Evidence 신뢰도 개선
- `causal_chain` 우선 활성화 → comparative 질문 49% 향상

### Next Steps

1. **축소된 Grid Search** (8개 조합) → 최적 조합 확정
2. **쿼리 타입별 동적 설정** 구현
3. **프로덕션 A/B 테스트** 진행

---

*이 보고서는 240개 실제 실험 케이스를 기반으로 작성되었습니다.*
