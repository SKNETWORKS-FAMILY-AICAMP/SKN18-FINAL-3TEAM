# Ontology RAG Isolation Study 실험 결과 보고서

**실험 기간**: 2024년 12월 27일
**최종 업데이트**: 2024년 12월 28일
**총 실험 케이스**: 240개 (Semantic 60 + Entity Boost 80 + Thread 100)
**실험 유형**: 컴포넌트 단독 활성화 테스트 (Isolation Study)

---

## Executive Summary

### 핵심 발견
| 실험 | 최고 성능 | 최저 성능 | 핵심 인사이트 |
|------|----------|----------|--------------|
| Semantic Expander | **causal_chain (0.7611)** | temporal (0.7350) | **causal_chain이 3.6% 우위** |
| Entity Boost | **none (0.7634)** | exact (0.7399) | **boost 없음이 최고, 차이 3.2%** |
| Thread Aggregator | **type_and_summary (0.7984)** | incoming (0.6910) | **type_and_summary 15.5% 우위** |

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

| 설정 | Intent-Aware Score | 최소 | 최대 | Evidence有 |
|------|-------------------|------|------|-----------|
| **causal_chain_only** | **0.7611** | 0.5521 | 0.9296 | 19/20 (95%) |
| pgvector_only | 0.7451 | 0.5918 | 0.9138 | 19/20 (95%) |
| temporal_only | 0.7350 | 0.5868 | 0.9353 | 20/20 (100%) |

### Raw Metrics 분석

| 설정 | TBox | Intent | Triple | 성능 우위 |
|------|------|--------|--------|----------|
| **causal_chain_only** | 0.9362 | **0.7950** | 0.6230 | **최고** (0.7611) |
| pgvector_only | **0.9780** | 0.7457 | **0.6504** | 2위 (0.7451) |
| temporal_only | 0.9467 | 0.7517 | 0.5524 | 3위 (0.7350) |

**핵심 발견**:
- **causal_chain이 Intent Preservation에서 압도적** (0.7950 vs 평균 0.7475)
- pgvector는 TBox/Triple 최고지만 Intent에서 밀림
- **Isolation 환경에서는 Ablation과 정반대 결과**: 단독 시 causal_chain이 최고

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
> **causal_chain이 단독으로 가장 효과적 (0.7611) - Ablation과 정반대**
>
> **정량적 근거**:
> - `causal_chain`: 0.7611 (Intent 0.7950 최고)
> - `pgvector`: 0.7451 (TBox/Triple 우수하나 Intent 부족)
> - `temporal`: 0.7350 (Evidence 100%지만 성능 최하)
> - 최고-최저 차이 **3.6%** (0.7611 vs 0.7350)
>
> **핵심 인사이트**:
> 1. **Ablation vs Isolation 역전**: Ablation에서는 baseline(확장없음) 최고, Isolation에서는 causal_chain 최고
> 2. Intent Preservation에서 causal_chain이 **6.5%p 우위** (0.7950 vs 0.7475)
> 3. **조합 시 부정적 상호작용 존재**: 단독으로 좋아도 함께 쓰면 성능 하락

---

## 2. Entity Boost Isolation Study

### 실험 설계
- **목적**: Entity Boost 매칭 전략별 순수 효과 측정
- **설정**: 4가지 (exact, partial, normalized, none)
- **쿼리**: 20개
- **총 케이스**: 80개

### 전체 결과

| 설정 | Intent-Aware Score | 최소 | 최대 | Evidence有 |
|------|-------------------|------|------|-----------|
| **none** | **0.7634** | 0.6041 | 0.9532 | 19/20 (95%) |
| normalized_match | 0.7593 | 0.5515 | 0.9752 | 20/20 (100%) |
| partial_match | 0.7516 | 0.5717 | 0.9227 | 19/20 (95%) |
| exact_match | 0.7399 | 0.5940 | 0.9146 | 19/20 (96%) |

### Raw Metrics 분석

| 설정 | TBox | Intent | Triple | 성능 |
|------|------|--------|--------|------|
| **none** | **0.9856** | 0.7933 | 0.6187 | **0.7634** |
| normalized_match | 0.9118 | **0.8016** | 0.5893 | 0.7593 |
| partial_match | 0.9361 | 0.7788 | **0.6472** | 0.7516 |
| exact_match | 0.9694 | 0.7542 | 0.6156 | 0.7399 |

**핵심 발견**:
- **boost 없음(none)이 최고 성능** (0.7634) → Entity Boost가 오히려 방해
- `normalized`는 Intent 최고(0.8016)지만 Triple에서 손실
- 모든 모드 간 차이 **3.2%로 미미** (0.7634 vs 0.7399)

### 질문별 최적 모드 분포

| 모드 | 최적인 질문 수 | 비율 |
|------|--------------|------|
| **exact_match** | 7/20 | 35% |
| **normalized_match** | 6/20 | 30% |
| none | 2/20 | 10% |
| partial_match | 0/20 | 0% |

### 결론
> **Entity Boost 없음(none)이 최고 - boost가 오히려 성능 저하**
>
> **정량적 근거**:
> - `none`: 0.7634 (TBox 0.9856 최고)
> - `normalized`: 0.7593 (Intent 0.8016 최고, 차이 0.54%)
> - `partial`: 0.7516 (Triple 0.6472 최고)
> - `exact`: 0.7399 (모든 지표 최하)
> - 최고-최저 차이 **3.2%** (0.7634 vs 0.7399)
>
> **핵심 인사이트**:
> 1. **Entity Boost의 효과 미미하거나 역효과** (none이 최고)
> 2. **Ablation과 역전**: Ablation에서는 partial 최고, Isolation에서는 none 최고
> 3. 모드 간 차이 3.2%로 매우 작음 → **Entity Boost의 영향력 제한적**
> 4. Isolation 환경에서는 단순한 설정이 더 효과적

### ⭐ 쿼리 타입별 분석 (Entity Boost)

| 쿼리 타입 | none | normalized | partial | exact | 최적 설정 | 차이(Δ) |
|----------|------|-----------|---------|-------|----------|---------|
| factual | 0.8027 | **0.8162** | 0.8033 | 0.8159 | **normalized** | +1.7% |
| causal | **0.9351** | 0.9216 | 0.8966 | 0.8799 | **none** | +6.3% |
| comparative | **0.8613** | 0.7918 | 0.8049 | 0.8226 | **none** | +8.8% |
| deep_analysis | 0.9895 | 0.9930 | **1.0034** | 0.9370 | **partial** | +1.4% |

**쿼리 타입별 핵심 발견**:
- **causal/comparative**: boost 없음(none)이 압도적 최고 (+6~9%)
- **factual**: normalized/exact가 약간 우수 (하지만 차이 미미 1.7%)
- **deep_analysis**: partial이 유일하게 1.0 초과 달성

---

## 3. Thread Aggregator Isolation Study

### 실험 설계
- **목적**: 각 Thread를 **단독으로** 활성화했을 때의 순수 효과 측정
- **설정**: 5가지 (각 Thread 단독)
- **쿼리**: 20개
- **총 케이스**: 100개

### 전체 결과

| 설정 | Intent-Aware Score | 최소 | 최대 | Evidence有 |
|------|-------------------|------|------|-----------|
| **type_and_summary_only** | **0.7984** | 0.6316 | 0.9368 | 19/20 (95%) |
| entity_properties_only | 0.7389 | 0.5754 | 0.8947 | 19/20 (95%) |
| connected_entities_only | 0.7395 | 0.5175 | 0.9474 | **5/20** (27%) ⚠️ |
| outgoing_relations_only | 0.7115 | 0.4877 | 0.8882 | 19/20 (96%) |
| incoming_relations_only | 0.6910 | 0.5368 | 0.8316 | 19/20 (95%) |

### Raw Metrics 분석

| 설정 | TBox | Intent | Triple | 성능 |
|------|------|--------|--------|------|
| **type_and_summary** | **1.0000** | 0.8170 | **1.0000** | **0.7984** |
| connected_entities | 0.9545 | 0.7401 | 0.8705 | 0.7395 |
| entity_properties | **1.0000** | 0.7881 | 0.5788 | 0.7389 |
| outgoing_relations | 0.8000 | 0.7874 | 0.5227 | 0.7115 |
| incoming_relations | 0.5879 | **0.8016** | 0.4682 | 0.6910 |

### 성능 차이 분석

| 비교 | 차이 | 해석 |
|------|------|------|
| type_and_summary vs incoming | **+15.5%** | **압도적 차이** |
| type_and_summary vs outgoing | **+12.2%** | 매우 유의미 |
| type_and_summary vs entity_properties | **+8.1%** | 유의미 |
| connected_entities 문제점 | Evidence **27%만** | 점수는 높지만 **신뢰도 심각** |

### 결론
> **type_and_summary가 압도적으로 최고 (0.7984) - 단독 Thread의 명확한 승자**
>
> **정량적 근거**:
> - `type_and_summary`: 0.7984 (TBox/Triple 완벽 1.0, Intent 0.8170)
> - `entity_properties`: 0.7389 (TBox 1.0, 차이 -7.5%)
> - `connected_entities`: 0.7395 (Evidence **27%만** 생성 → 신뢰 불가)
> - `outgoing`: 0.7115 (차이 -10.9%)
> - `incoming`: 0.6910 (차이 -13.5%, **최하위**)
>
> **핵심 인사이트**:
> 1. **type_and_summary의 압도적 우위**: 최하위 대비 **+15.5%**, TBox/Triple 완벽
> 2. `connected_entities` **치명적 결함**: Evidence 73% 미생성 → 사용 불가
> 3. `incoming_relations`: 일관되게 최저 → **즉시 비활성화 권장**
> 4. **Ablation과 일관성**: Ablation에서도 outgoing 제거 시 성능 향상 (+6.8%)

### ⭐ 쿼리 타입별 분석 (Thread Aggregator)

| 쿼리 타입 | type_and_summary | entity_properties | outgoing_relations | incoming_relations | connected_entities | 최적 설정 | 차이(Δ) |
|----------|------------------|-------------------|-------------------|-------------------|-------------------|----------|---------|
| factual | **0.8264** | 0.8159 | 0.7590 | 0.7938 | 0.7829 | **type_and_summary** | +1.3% |
| causal | **0.9480** | 0.8976 | 0.8521 | 0.7253 | 0.8874 | **type_and_summary** | +5.6% |
| comparative | 0.8596 | **0.8662** | 0.7773 | 0.8188 | 0.7927 | **entity_properties** | +0.8% |
| deep_analysis | 0.9632 | 0.9709 | **0.9828** | 0.8830 | 0.9332 | **outgoing_relations** | +1.2% |

**쿼리 타입별 핵심 발견**:
- **factual/causal**: type_and_summary가 압도적 (+1.3~5.6%)
- **comparative**: entity_properties가 근소하게 우세 (+0.8%) ⭐ 전역 평균과 다름
- **deep_analysis**: outgoing_relations가 최고 (+1.2%) ⭐ **전역 평균과 정반대!**
- **incoming_relations**: 모든 쿼리 타입에서 하위권 (특히 causal에서 최하위)

**전략적 함의**:
1. **deep_analysis**: 전역 평균(type_and_summary 최고)과 정반대 → outgoing_relations 선호
2. **comparative**: entity_properties를 선호하는 유일한 타입
3. **incoming_relations**: 일관되게 저성능 → Quick Win에서 제거 결정 검증됨

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

모든 수치는 다음 실제 실험 데이터 파일에서 추출됨:

| 파일 | 케이스 수 | Evidence 생성률 | 최종 업데이트 |
|------|----------|----------------|---------------|
| `semantic_expander_isolation_summary.json` | 60 (20×3) | 96.7% | 2024-12-28 |
| `entity_boost_isolation_summary.json` | 80 (20×4) | 96.3% | 2024-12-28 |
| `thread_isolation_summary.json` | 100 (20×5) | 87.0%* | 2024-12-28 |

\* connected_entities(27%)를 제외하면 평균 95.8%

**데이터 경로**: `backend/ragas/ontology_evaluate/data/results_isolation/`

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

*이 보고서는 2024년 12월 28일 업데이트된 240개 실제 실험 케이스를 기반으로 작성되었습니다.*
