# 전체 가중치 민감도 실험 결과

**실험일**: 2024년 12월 26일  
**데이터**: Semantic Expander 100개 + Thread Ablation 120개 + Entity Boost 80개 = **총 300개 케이스**

---

## Executive Summary

### 핵심 발견

| 실험 | 기존 최적 | 신규 최적 (aggressive_intent) | 변화 |
|------|----------|------------------------------|------|
| Semantic Expander | baseline | baseline | 유지 ✓ |
| Thread Ablation | without_outgoing | **without_incoming** | **변경!** |
| Entity Boost | normalized_match | normalized_match | 유지 ✓ |

### 실험별 민감도

```
Best-Worst Gap (설정 간 성능 차이):

Semantic Expander:  ████████████████████████████████████████  0.2004 (가장 민감)
Thread Ablation:    ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0.0287
Entity Boost:       ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0.0298
```

→ **Semantic Expander 설정이 성능에 가장 큰 영향**

---

## 1. Thread Ablation 결과

### 가중치별 최적 설정 변화

| 가중치 설정 | 1위 | Score | 2위 | Score |
|------------|-----|-------|-----|-------|
| baseline_equal | without_connected_entities | 0.6521 | without_outgoing_relations | 0.6478 |
| intent_x2 | **without_incoming_relations** | 0.6368 | without_connected_entities | 0.6363 |
| intent_x3 | **without_incoming_relations** | 0.6285 | without_connected_entities | 0.6240 |
| aggressive_intent | **without_incoming_relations** | 0.6570 | without_entity_properties | 0.6506 |
| core_metrics_only | **without_incoming_relations** | 0.7424 | without_connected_entities | 0.7408 |

**핵심 발견**: Intent 가중치를 높이면 `without_incoming_relations`가 1위로 부상!

### aggressive_intent 적용 시 상세

| 설정 | Original | New Score | 변화 |
|------|----------|-----------|------|
| baseline | 0.6075 | 0.6283 | +0.0208 |
| without_outgoing_relations | 0.6487 | 0.6400 | **-0.0088** |
| **without_incoming_relations** | 0.6325 | **0.6570** | **+0.0245** |
| without_entity_properties | 0.6449 | 0.6506 | +0.0057 |
| without_connected_entities | 0.6376 | 0.6441 | +0.0066 |
| without_type_and_summary | 0.6392 | 0.6297 | -0.0095 |

**해석**: 
- `without_outgoing`은 기존에 1위였으나 새 가중치에서 점수 하락
- `without_incoming`은 Intent 보존이 좋아 새 가중치에서 상승

---

## 2. Entity Boost 결과

### 가중치별 최적 설정 변화

| 가중치 설정 | 1위 | Score | 2위 | Score |
|------------|-----|-------|-----|-------|
| baseline_equal | normalized_match | 0.6479 | exact_match | 0.6455 |
| intent_x2 | normalized_match | 0.6339 | exact_match | 0.6317 |
| intent_x3 | normalized_match | 0.6230 | exact_match | 0.6209 |
| aggressive_intent | normalized_match | 0.6503 | **partial_match** | 0.6501 |
| core_metrics_only | normalized_match | 0.7481 | exact_match | 0.7221 |

**핵심 발견**: `normalized_match`가 일관되게 1위, but `partial_match`가 거의 동점으로 2위 부상!

### aggressive_intent 적용 시 상세

| 설정 | Original | New Score | 변화 |
|------|----------|-----------|------|
| exact_match | 0.6214 | 0.6375 | +0.0161 |
| **normalized_match** | 0.6329 | **0.6503** | +0.0174 |
| partial_match | 0.6391 | 0.6501 | +0.0109 |
| penalty_match | 0.6159 | 0.6205 | +0.0046 |

---

## 3. Semantic Expander 결과 (재확인)

### aggressive_intent 적용 시

| 설정 | Score | 순위 |
|------|-------|------|
| **baseline** | **0.8287** | **1위** |
| temporal_only | 0.7274 | 2위 |
| causal_chain_only | 0.6850 | 4위 |
| pgvector_only | 0.6283 | 5위 |
| full | 0.6913 | 3위 |

**Gap**: 0.2004 (baseline - pgvector_only)

→ 모든 가중치 설정에서 **baseline이 일관되게 1위**

---

## 4. 통합 권장 설정

### 최종 권장 Config

```python
RECOMMENDED_CONFIG = {
    # 가중치 (aggressive_intent)
    "weights": {
        "intent_preservation": 5.0,      # ★ 핵심
        "tbox_consistency": 1.0,
        "relation_coherence": 1.0,
        "triple_validity": 1.0,
        "evidence_diversity": 0.5,       # 하향
        "convergence_utilization": 0.5,  # 하향
        "property_group_selection": 0.5, # 하향
    },
    
    # Semantic Expander (가장 중요!)
    "semantic_expander": {
        "temporal": False,
        "causal_chain": False,
        "pgvector": False,
    },
    
    # Thread Ablation (★ 새 발견!)
    "aggregator_threads": {
        "outgoing_relations": True,
        "incoming_relations": False,     # ★ 제거 권장 (신규)
        "entity_properties": True,
        "connected_entities": True,
        "type_and_summary": True,
    },
    
    # Entity Boost
    "entity_boost_mode": "normalized_match",
}
```

### 기존 권장 vs 신규 권장

| 항목 | 기존 (equal weights) | 신규 (aggressive_intent) |
|------|---------------------|-------------------------|
| **가중치** | 모두 1.0 | intent=5.0, evidence/conv/prop=0.5 |
| **Semantic Expander** | baseline (off) | baseline (off) ✓ |
| **Thread 제거** | outgoing_relations | **incoming_relations** ★ |
| **Entity Boost** | partial_match | normalized_match |

---

## 5. 우선순위 권장

### 성능 영향도 순위

1. **Semantic Expander OFF** (Gap: 0.2004) - 가장 중요!
2. **Intent 가중치 5.0** (Gap 증가: +147%)
3. **incoming_relations 제거** (Gap: 0.0287)
4. **normalized_match 사용** (Gap: 0.0298)

### 즉시 적용 권장

```python
# 최소 변경으로 최대 효과
QUICK_APPLY = {
    "semantic_expander": {"temporal": False, "causal_chain": False, "pgvector": False},
    "weights": {"intent_preservation": 5.0},  # 나머지는 1.0
}
```

---

## 부록: 실행 스크립트

```bash
# 전체 실험 실행
python3 /home/claude/weight_experiment_all.py

# 결과 파일
/home/claude/all_experiments_weight_results.json
```
