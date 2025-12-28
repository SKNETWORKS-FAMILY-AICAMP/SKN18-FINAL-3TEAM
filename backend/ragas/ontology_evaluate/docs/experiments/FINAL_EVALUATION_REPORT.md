# Ontology RAG 컴포넌트 평가 최종 보고서

**실험 기간**: 2024년 12월 25일 ~ 28일  
**총 실험 케이스**: 660개+ (Ablation 300 + Isolation 240 + Grid Search 120)  
**평가 지표**: Intent-Aware Score (정량) + LLM Judge Quality (정성)  
**종합 점수**: Intent 70% + LLM Quality 30%

---

## Executive Summary

### 핵심 발견

| 구분 | 최고 성능 | 핵심 인사이트 |
|------|----------|--------------|
| **Grid Search (조합)** | ablation_baseline (0.8145) | 확장 없음 > 확장 조합 |
| **Semantic Expander** | causal_chain (0.7259) | deep_analysis에서 46% 가중치 |
| **Thread Aggregator** | type_and_summary (0.7427) | 모든 쿼리 타입에서 최고 |
| **Entity Boost** | normalized (0.7130) | 차이 미미, normalized 권장 |

### 최종 결론

> **1. 컴포넌트 간 부정적 상호작용 확인**
> - 단독으로 효과적인 컴포넌트도 조합 시 성능 하락
> - ablation_baseline(확장 없음)이 Grid Search 최고 점수
> 
> **2. 그러나 쿼리 타입별로 확장이 효과적인 경우 존재**
> - deep_analysis: causal_chain이 0.8316으로 최고
> - causal: causal_chain이 0.7256으로 우위
> 
> **3. 가중치 기반 Evidence 선택으로 개선 가능**
> - LLM 판단 없이 점수 기반 상위 15개 자동 선택
> - 쿼리 타입별 최적 가중치 도출 완료

---

## 1. Grid Search 결과 (조합 효과)

### 1.1 설정별 종합 성능

| 설정 | Intent점수 | LLM품질 | 종합(7:3) | 순위 |
|------|-----------|--------|----------|------|
| **ablation_baseline** | **0.8551** | **0.7198** | **0.8145** | 🥇 |
| minimal | 0.8055 | 0.7003 | 0.7739 | 🥈 |
| with_outgoing | 0.7855 | 0.6826 | 0.7547 | 🥉 |
| recommended_default | 0.7508 | 0.7304 | 0.7447 | 4 |
| with_exact_boost | 0.7584 | 0.7103 | 0.7439 | 5 |
| causal_temporal_combo | 0.6781 | 0.6544 | 0.6710 | 6 |

**핵심 발견**:
- `ablation_baseline` (확장 없음 + 모든 Thread)이 최고 성능
- `causal_temporal_combo` (동시 활성화)가 최저 → 부정적 상호작용 확인

### 1.2 쿼리 타입별 최적 설정

| 쿼리 타입 | 1위 설정 | 점수 | 2위 설정 | 점수 |
|-----------|----------|------|----------|------|
| **factual** | ablation_baseline | 0.8452 | minimal | 0.7492 |
| **causal** | ablation_baseline | 0.8741 | with_outgoing | 0.8153 |
| **comparative** | ablation_baseline | 0.8557 | with_outgoing | 0.8227 |
| **deep_analysis** | **minimal** | **0.9298** | ablation_baseline | 0.8297 |

**핵심 발견**:
- deep_analysis에서만 `minimal` (causal + type_and_summary)이 최고
- 다른 쿼리 타입은 모두 ablation_baseline이 최고

---

## 2. Isolation 결과 (단일 컴포넌트)

### 2.1 Semantic Expander

| 컴포넌트 | Intent점수 | LLM품질 | 종합(7:3) | 순위 |
|----------|-----------|--------|----------|------|
| **causal_chain** | 0.7611 | **0.6437** | **0.7259** | 🥇 |
| pgvector | **0.7451** | 0.6003 | 0.7017 | 🥈 |
| temporal | 0.7350 | 0.5912 | 0.6918 | 🥉 |

**쿼리 타입별 최적 Semantic**:

| 쿼리 타입 | 최적 | 점수 | 가중치 |
|-----------|------|------|--------|
| factual | pgvector | 0.7516 | 0.40 |
| causal | causal_chain | 0.7256 | 0.39 |
| comparative | temporal | 0.6654 | 0.35 |
| deep_analysis | **causal_chain** | **0.8316** | **0.46** |

### 2.2 Thread Aggregator

| 컴포넌트 | Intent점수 | LLM품질 | 종합(7:3) | 순위 |
|----------|-----------|--------|----------|------|
| **type_and_summary** | **0.7984** | **0.6126** | **0.7427** | 🥇 |
| entity_properties | 0.7389 | 0.5942 | 0.6955 | 🥈 |
| outgoing | 0.7115 | 0.6085 | 0.6806 | 🥉 |
| incoming | 0.6910 | 0.6100 | 0.6667 | 4 |
| connected | 0.7395 | 0.3476 | 0.6220 | 5 |

**결론**:
- `type_and_summary`: 모든 쿼리 타입에서 최고
- `incoming`, `connected`: 비활성화 권장

### 2.3 Entity Boost

| 모드 | Intent점수 | LLM품질 | 종합(7:3) | 순위 |
|------|-----------|--------|----------|------|
| **normalized** | 0.7593 | **0.6049** | **0.7130** | 🥇 |
| none | **0.7634** | 0.5536 | 0.7005 | 🥈 |
| partial | 0.7516 | 0.5740 | 0.6983 | 🥉 |
| exact | 0.7399 | 0.5924 | 0.6956 | 4 |

**결론**: `normalized` 권장 (차이 미미)

---

## 3. 쿼리 타입별 가중치

### 3.1 Evidence 점수 계산 공식

```python
evidence_score = (
    semantic_weight[expansion_method] * 
    thread_weight[thread_type] * 
    base_relevance_score
)

# 상위 15개 선택
top_15 = sorted(evidences, key=lambda e: e.score, reverse=True)[:15]
```

### 3.2 최종 가중치 설정

```python
QUERY_TYPE_WEIGHTS = {
    "factual": {
        "semantic": {
            "temporal": 0.32,
            "causal_chain": 0.28,
            "pgvector": 0.40,      # ⭐ 최고
        },
        "thread": {
            "type_and_summary": 0.41,  # ⭐ 최고
            "entity_properties": 0.30,
            "outgoing": 0.29,
        },
        "entity_boost": "normalized"
    },
    
    "causal": {
        "semantic": {
            "temporal": 0.25,
            "causal_chain": 0.39,  # ⭐ 최고
            "pgvector": 0.36,
        },
        "thread": {
            "type_and_summary": 0.43,  # ⭐ 최고
            "entity_properties": 0.33,
            "outgoing": 0.25,
        },
        "entity_boost": "normalized"
    },
    
    "comparative": {
        "semantic": {
            "temporal": 0.35,      # ⭐ 공동 최고
            "causal_chain": 0.35,  # ⭐ 공동 최고
            "pgvector": 0.31,
        },
        "thread": {
            "type_and_summary": 0.37,  # ⭐ 최고
            "entity_properties": 0.33,
            "outgoing": 0.31,
        },
        "entity_boost": "normalized"
    },
    
    "deep_analysis": {
        "semantic": {
            "temporal": 0.30,
            "causal_chain": 0.46,  # ⭐⭐ 압도적 최고
            "pgvector": 0.24,
        },
        "thread": {
            "type_and_summary": 0.37,  # ⭐ 최고
            "entity_properties": 0.29,
            "outgoing": 0.35,
        },
        "entity_boost": "normalized"
    },
}
```

### 3.3 가중치 해석

| 쿼리 타입 | Semantic 핵심 | Thread 핵심 | 특징 |
|-----------|--------------|------------|------|
| **factual** | pgvector (0.40) | type_and_summary (0.41) | 벡터 유사도 중심 |
| **causal** | causal_chain (0.39) | type_and_summary (0.43) | 인과관계 탐색 |
| **comparative** | 균등 분포 | type_and_summary (0.37) | 다양한 정보 필요 |
| **deep_analysis** | causal_chain (0.46) | 균등 + outgoing (0.35) | 깊이 있는 인과 분석 |

---

## 4. 권장 설정

### 4.1 기본 설정 (모든 쿼리)

```python
BASE_CONFIG = {
    "semantic_expander": {
        "temporal": False,
        "causal_chain": True,   # 가장 효과적
        "pgvector": False
    },
    "aggregator_threads": {
        "outgoing_relations": True,
        "incoming_relations": False,   # ❌ 비활성화
        "entity_properties": True,
        "connected_entities": False,   # ❌ 비활성화
        "type_and_summary": True       # ⭐ 필수
    },
    "entity_boost_mode": "normalized"
}
```

### 4.2 쿼리 타입별 동적 설정

```python
def get_optimal_config(query_type: str) -> dict:
    config = BASE_CONFIG.copy()
    
    if query_type == "factual":
        # pgvector 활성화, causal 비활성화
        config["semantic_expander"] = {
            "temporal": False,
            "causal_chain": False,
            "pgvector": True
        }
        
    elif query_type == "causal":
        # causal_chain 활성화
        config["semantic_expander"] = {
            "temporal": False,
            "causal_chain": True,
            "pgvector": False
        }
        
    elif query_type == "comparative":
        # temporal + causal 모두 고려 (가중치 균등)
        config["semantic_expander"] = {
            "temporal": True,
            "causal_chain": True,
            "pgvector": False
        }
        
    elif query_type == "deep_analysis":
        # causal_chain 강조 (0.46)
        config["semantic_expander"] = {
            "temporal": False,
            "causal_chain": True,
            "pgvector": False
        }
        config["aggregator_threads"]["outgoing_relations"] = True
    
    return config
```

---

## 5. Evidence 선택 알고리즘

### 5.1 기존 방식 vs 제안 방식

| 구분 | 기존 방식 | 제안 방식 |
|------|----------|----------|
| 방법 | LLM이 55개 중 15개 선택 | 점수 기반 상위 15개 자동 선택 |
| 비용 | LLM 호출 비용 | 없음 |
| 일관성 | LLM 판단에 의존 | 점수 기반 일관된 선택 |
| 속도 | 느림 | 빠름 |

### 5.2 구현 코드

```python
def select_top_evidences(
    evidences: List[Evidence],
    query_type: str,
    top_k: int = 15
) -> List[Evidence]:
    """
    가중치 기반 상위 Evidence 선택
    
    Args:
        evidences: 전체 Evidence 리스트
        query_type: 쿼리 타입 (factual, causal, comparative, deep_analysis)
        top_k: 선택할 Evidence 수
    
    Returns:
        상위 k개 Evidence
    """
    weights = QUERY_TYPE_WEIGHTS[query_type]
    
    scored_evidences = []
    for ev in evidences:
        # Semantic 가중치
        sem_method = ev.expansion_method or "none"
        sem_weight = weights["semantic"].get(sem_method, 0.33)
        
        # Thread 가중치
        thread_type = ev.thread_type
        thread_weight = weights["thread"].get(thread_type, 0.20)
        
        # 기본 관련성 점수 (TBox + Triple Validity 등)
        base_score = ev.relevance_score or 1.0
        
        # 최종 점수
        final_score = sem_weight * thread_weight * base_score
        
        scored_evidences.append((ev, final_score))
    
    # 점수 내림차순 정렬 후 상위 k개 선택
    scored_evidences.sort(key=lambda x: x[1], reverse=True)
    
    return [ev for ev, score in scored_evidences[:top_k]]
```

---

## 6. 실험 데이터 요약

### 6.1 전체 실험 현황

| 실험 유형 | 케이스 수 | 설정 수 | 쿼리 수 | 성공률 |
|----------|----------|--------|--------|--------|
| Ablation Study | 300 | 15 | 20 | 100% |
| Isolation Study | 240 | 12 | 20 | 100% |
| Grid Search | 120 | 6 | 20 | 100% |
| **총계** | **660+** | - | - | **100%** |

### 6.2 평가 메트릭

| 메트릭 | 유형 | 가중치 | 설명 |
|--------|------|--------|------|
| Intent Preservation | 정성 (LLM) | 52.6% | 확장 방향 적절성 |
| TBox Consistency | 정량 | 10.5% | 온톨로지 스키마 준수 |
| Relation Coherence | 정량 | 10.5% | 관계 일관성 |
| Triple Validity | 정성 (LLM) | 10.5% | Triple 기여도 |
| Evidence Diversity | 정량 | 5.3% | Thread 다양성 |
| Convergence Utilization | 정량 | 5.3% | 수렴 노드 활용 |
| **LLM Judge Quality** | 정성 (LLM) | *별도* | 답변 품질 |

---

## 7. 결론 및 Action Items

### 7.1 핵심 결론

1. **부정적 상호작용**: 컴포넌트 조합 시 성능 하락 확인
2. **쿼리 타입별 차이**: deep_analysis에서만 확장이 명확히 효과적
3. **가중치 기반 선택**: LLM 판단 없이 점수 기반 Evidence 선택 가능

### 7.2 즉시 적용 사항

| 항목 | 현재 | 변경 | 근거 |
|------|------|------|------|
| incoming_relations | 활성화 | **비활성화** | 종합 0.6667 (최하위) |
| connected_entities | 활성화 | **비활성화** | LLM품질 0.35 (최저) |
| entity_boost_mode | 혼재 | **normalized** | 종합 0.7130 (최고) |
| Evidence 선택 | LLM 판단 | **점수 기반** | 일관성 + 속도 |

### 7.3 쿼리 타입별 가중치 적용

```python
# 실제 적용 예시
if query_type == "deep_analysis":
    # causal_chain 강조 (0.46)
    prioritize_causal_chain_evidences()
elif query_type == "factual":
    # pgvector 강조 (0.40)
    prioritize_vector_similarity_evidences()
```

---

## 8. 부록: 전체 가중치 테이블

### Semantic Expander 가중치

| 쿼리 타입 | temporal | causal_chain | pgvector |
|-----------|----------|--------------|----------|
| factual | 0.32 | 0.28 | **0.40** |
| causal | 0.25 | **0.39** | 0.36 |
| comparative | **0.35** | **0.35** | 0.31 |
| deep_analysis | 0.30 | **0.46** | 0.24 |

### Thread Aggregator 가중치

| 쿼리 타입 | type_and_summary | entity_properties | outgoing |
|-----------|------------------|-------------------|----------|
| factual | **0.41** | 0.30 | 0.29 |
| causal | **0.43** | 0.33 | 0.25 |
| comparative | **0.37** | 0.33 | 0.31 |
| deep_analysis | **0.37** | 0.29 | 0.35 |

### Entity Boost

| 쿼리 타입 | 권장 모드 |
|-----------|----------|
| 전체 | **normalized** |

---

*본 보고서는 660개+ 실험 케이스의 실제 데이터를 기반으로 작성되었습니다.*  
*작성일: 2024년 12월 28일*
