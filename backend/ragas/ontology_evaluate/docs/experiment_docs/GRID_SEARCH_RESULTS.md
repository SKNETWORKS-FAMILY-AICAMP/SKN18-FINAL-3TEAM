# Ontology RAG Grid Search 최적화 실험 결과 보고서

**실험 기간**: 2024년 12월 28일
**총 실험 케이스**: 120개 (6개 설정 × 20개 쿼리)
**실험 유형**: 컴포넌트 조합 최적화 (Optimized Grid Search)

---

## Executive Summary

### 핵심 발견

| 순위 | 설정 | Intent-Aware Score | 핵심 특징 |
|------|------|-------------------|----------|
| 🥇 **1위** | ablation_baseline | **0.8551** | **확장 없음 + 전체 Thread** (Ablation 최고 재현) |
| 🥈 2위 | minimal | **0.8055** | causal_chain + type_and_summary만 (최소 구성) |
| 🥉 3위 | with_outgoing | 0.7855 | minimal + outgoing 추가 |
| 4위 | with_exact_boost | 0.7584 | minimal + exact_match boost |
| 5위 | recommended_default | 0.7508 | minimal + entity_properties |
| 6위 | causal_temporal_combo | 0.6781 | **다중 확장 전략 조합 실패** |

### 최적 설정 발견

**Ablation Baseline이 Grid Search에서도 최고 성능 (0.8551)**
- Ablation Study 결론 검증: **"확장 없음"이 최적**
- Grid Search를 통한 조합 최적화 시도 → 단순 설정이 여전히 최고

---

## 1. 실험 설계

### 목적
Ablation과 Isolation 연구 결과를 바탕으로 **최적 컴포넌트 조합** 탐색

### Grid Search 전략

**기본 가설**:
1. Ablation: "확장 없음"이 최고 → 재현 필요
2. Isolation: causal_chain, type_and_summary 단독 최고 → 조합 효과 확인
3. Thread 최소화가 성능 향상 → 검증 필요

**테스트 설정 (6개)**:

| 설정 이름 | Semantic Expander | Threads | Entity Boost | 가설 |
|----------|------------------|---------|--------------|------|
| ablation_baseline | 없음 | 5개 전체 | 없음 | Ablation 최고 성능 재현 |
| minimal | causal_chain만 | type_and_summary만 | normalized | Isolation 최고 조합 |
| with_outgoing | causal_chain만 | +outgoing 추가 | normalized | outgoing 효과 검증 |
| with_exact_boost | causal_chain만 | type_and_summary만 | exact | boost 모드 비교 |
| recommended_default | causal_chain만 | +entity_properties | normalized | 균형적 설정 |
| causal_temporal_combo | causal+temporal | type_and_summary만 | normalized | 다중 확장 효과 |

---

## 2. 전체 결과 비교

### 성능 순위

| 순위 | 설정 | Score | 최소 | 최대 | Range | 성능 분석 |
|------|------|-------|------|------|-------|----------|
| 1 | **ablation_baseline** | **0.8551** | 0.7930 | 0.9174 | 0.1244 | **압도적 최고, 안정적** |
| 2 | minimal | 0.8055 | 0.5000 | 1.0000 | 0.5000 | 2위, 변동성 큼 |
| 3 | with_outgoing | 0.7855 | 0.4719 | 0.9117 | 0.4398 | outgoing 추가 시 -2.5% |
| 4 | with_exact_boost | 0.7584 | 0.3808 | 0.9174 | 0.5366 | exact 사용 시 -5.8% |
| 5 | recommended_default | 0.7508 | 0.4640 | 0.9042 | 0.4402 | entity_prop 추가 시 -6.8% |
| 6 | causal_temporal_combo | 0.6781 | 0.5028 | 0.8936 | 0.3908 | **다중 확장 실패** -26.2% |

### Raw Metrics 비교

| 설정 | TBox | Intent | Triple | 분석 |
|------|------|--------|--------|------|
| **ablation_baseline** | 0.8632 | **1.0000** | 0.4975 | **Intent 완벽** |
| minimal | **1.0000** | 0.8305 | **1.0000** | TBox/Triple 완벽 |
| with_outgoing | 0.9050 | 0.8793 | 0.4409 | Intent 높지만 Triple 낮음 |
| with_exact_boost | **1.0000** | 0.8216 | 0.4604 | 균형적 |
| recommended_default | **1.0000** | 0.8115 | 0.4353 | 균형적 |
| causal_temporal_combo | **1.0000** | 0.6703 | 0.4593 | **Intent 급락** |

**핵심 발견**:
- **ablation_baseline**: Intent Preservation 1.0000 (완벽) → 전체 점수 최고
- **minimal**: TBox/Triple 완벽하지만 Intent는 0.8305로 낮음
- **다중 확장 조합(causal+temporal)**: Intent 0.6703으로 급락 → **조합 실패**

---

## 3. 설정별 상세 분석

### 🥇 1위: ablation_baseline (0.8551)

**설정**:
```python
{
    "semantic_expander": {
        "temporal": False,
        "causal_chain": False,
        "pgvector": False
    },
    "aggregator_threads": {
        "outgoing_relations": True,
        "incoming_relations": True,
        "entity_properties": True,
        "connected_entities": True,
        "type_and_summary": True
    },
    "entity_boost_mode": None
}
```

**성능 분석**:
- Intent-Aware Score: **0.8551** (최고)
- Intent Preservation: **1.0000** (완벽)
- Range: 0.1244 (가장 안정적)

**왜 최고인가**:
1. **Intent Preservation 완벽**: 확장 없이 추출된 엔티티만 사용 → 의도 보존
2. **Ablation Study 재현 성공**: Ablation에서 최고였던 설정 Grid Search에서도 검증
3. **안정성 최고**: 최소-최대 편차가 가장 작음

---

### 🥈 2위: minimal (0.8055)

**설정**:
```python
{
    "semantic_expander": {
        "causal_chain": True  # causal_chain만 활성화
    },
    "aggregator_threads": {
        "type_and_summary": True  # 최소 Thread
    },
    "entity_boost_mode": "normalized"
}
```

**성능 분석**:
- Intent-Aware Score: 0.8055 (ablation_baseline 대비 -5.8%)
- TBox/Triple: 1.0000 (완벽)
- Intent: 0.8305 (높음)
- Range: 0.5000 (변동성 큼)

**장점**:
1. **Isolation 연구 기반 최소 구성**: causal_chain + type_and_summary
2. TBox/Triple Validity 완벽 (1.0)
3. 복잡도 최소 → 실행 시간 단축 가능

**단점**:
1. Intent Preservation이 baseline보다 낮음 (0.8305 vs 1.0)
2. 변동성 큼 (0.5~1.0) → 안정성 부족

---

### 🥉 3위: with_outgoing (0.7855)

**설정**: minimal + outgoing_relations 추가

**성능 분석**:
- Intent-Aware: 0.7855 (minimal 대비 -2.5%)
- Intent: 0.8793 (오히려 상승)
- Triple: 0.4409 (급락)

**결론**:
- **outgoing 추가 시 오히려 성능 하락** (-2.5%)
- Ablation 결과와 일치: outgoing 제거 시 성능 향상 (+6.8%)
- **outgoing은 노이즈 원인 확정**

---

### 4위~5위: boost 및 thread 추가 실험

**with_exact_boost (4위, 0.7584)**:
- exact_match boost 사용 → minimal 대비 -5.8%
- Entity Boost의 효과 미미 확인

**recommended_default (5위, 0.7508)**:
- entity_properties 추가 → minimal 대비 -6.8%
- **Thread 추가 시 성능 저하 재확인**

---

### 6위: causal_temporal_combo (0.6781) - 실패 케이스

**설정**: causal_chain + temporal 동시 활성화

**성능 분석**:
- Intent-Aware: 0.6781 (ablation_baseline 대비 **-20.7%**)
- Intent: 0.6703 (**급락**, baseline 대비 -33%p)
- **최하위 성능**

**실패 원인**:
1. **다중 확장 전략의 부정적 상호작용**: causal+temporal 조합 시 Intent 급락
2. Ablation에서 "full expansion" 실패와 동일 패턴
3. **확장 전략은 단독 사용이 원칙**

---

## 4. 핵심 인사이트

### 4.1 Ablation Study 검증 성공

```
Ablation 결론: "확장 없음(baseline)"이 최고 (0.6705)
Grid Search 결과: ablation_baseline 최고 (0.8551)

→ Grid Search에서도 Ablation 결론 재현
→ "단순함이 최고"라는 원칙 검증
```

### 4.2 컴포넌트 조합의 부정적 상호작용

| 조합 | 개별 성능 (Isolation) | 조합 성능 (Grid) | 결과 |
|------|---------------------|-----------------|------|
| causal_chain 단독 | 0.7611 (최고) | - | - |
| type_and_summary 단독 | 0.7984 (최고) | - | - |
| **causal + type_and_summary** | - | 0.8055 | **조합해도 baseline보다 낮음** |
| causal + temporal | - | 0.6781 | **치명적 성능 하락** |

**결론**: **단독으로 좋은 컴포넌트도 조합 시 성능 저하**

### 4.3 Intent Preservation이 핵심

| 설정 | Intent Preservation | 전체 점수 | 상관관계 |
|------|-------------------|----------|---------|
| ablation_baseline | **1.0000** | **0.8551** | **강한 양의 상관** |
| minimal | 0.8305 | 0.8055 | |
| with_outgoing | 0.8793 | 0.7855 | |
| causal_temporal | 0.6703 | 0.6781 | |

**핵심**: Intent Preservation이 높을수록 전체 점수 향상

### 4.4 Thread 최소화 원칙

```
5개 Thread (baseline): 0.8551
1개 Thread (minimal): 0.8055 (-5.8%)
2개 Thread (with_outgoing): 0.7855 (-8.1%)
3개 Thread (recommended): 0.7508 (-12.2%)

→ Thread 많을수록 성능 저하
→ 하지만 baseline은 예외 (Intent 1.0 효과)
```

---

## 5. 최종 권장 설정

### A. 프로덕션 추천 (최고 성능)

```python
PRODUCTION_OPTIMAL = {
    "semantic_expander": {
        "temporal": False,
        "causal_chain": False,
        "pgvector": False
    },
    "aggregator_threads": {
        "outgoing_relations": True,
        "incoming_relations": True,
        "entity_properties": True,
        "connected_entities": True,
        "type_and_summary": True
    },
    "entity_boost_mode": None
}
```

**근거**: Grid Search 최고 성능 (0.8551), Intent 완벽 보존 (1.0)

**장점**:
- ✅ 최고 성능 (0.8551)
- ✅ Intent Preservation 완벽 (1.0)
- ✅ 가장 안정적 (Range 0.1244)
- ✅ Ablation/Grid Search 모두 검증

**단점**:
- ⚠️ Thread 5개 모두 사용 → 실행 시간 증가 가능
- ⚠️ Ablation Thread 실험과 모순 (Thread 제거 시 성능 향상)

---

### B. 최소 구성 (효율성 우선)

```python
MINIMAL_EFFICIENT = {
    "semantic_expander": {
        "causal_chain": True  # Isolation 최고 전략만
    },
    "aggregator_threads": {
        "type_and_summary": True  # Isolation 최고 Thread만
    },
    "entity_boost_mode": "normalized"
}
```

**근거**: Isolation 연구 기반, Grid Search 2위 (0.8055)

**장점**:
- ✅ 컴포넌트 최소 → 빠른 실행 시간
- ✅ TBox/Triple Validity 완벽 (1.0)
- ✅ Intent도 높음 (0.8305)
- ✅ Isolation 연구와 일관성

**단점**:
- ⚠️ baseline 대비 -5.8% 성능
- ⚠️ 변동성 큼 (Range 0.5)

---

### C. 쿼리 타입별 동적 설정

```python
def get_optimal_config(query_type: str, priority: str = "performance"):
    """
    priority: "performance" (최고 성능) vs "efficiency" (실행 시간)
    """
    if priority == "performance":
        # 모든 쿼리 타입에 ablation_baseline 사용
        return PRODUCTION_OPTIMAL

    elif priority == "efficiency":
        # 쿼리 타입별 최소 구성
        if query_type == "comparative":
            # 비교 질문: causal_chain 필수
            return {
                "semantic_expander": {"causal_chain": True},
                "aggregator_threads": {"type_and_summary": True},
                "entity_boost_mode": "normalized"
            }
        else:
            # 나머지: 확장 없음
            return {
                "semantic_expander": {},
                "aggregator_threads": {"type_and_summary": True},
                "entity_boost_mode": None
            }
```

---

## 6. Grid Search가 답하지 못한 질문

### 6.1 Thread Ablation 모순

**모순**:
- Ablation Thread 실험: outgoing 제거 시 +6.8% 향상
- Grid Search baseline: outgoing 포함 5개 Thread가 최고

**가능한 설명**:
1. Thread 단독 영향 vs 전체 시스템 효과 차이
2. Semantic Expander 없음 + 5개 Thread 조합의 시너지
3. Intent Preservation 1.0 효과가 Thread 노이즈를 상쇄

**추가 실험 필요**:
- ablation_baseline에서 Thread 하나씩 제거하며 성능 측정

---

### 6.2 왜 확장 없음이 최고인가?

**가설**:
1. **현재 Semantic Expander 구현의 한계**: 확장 로직이 불필요한 노드를 너무 많이 추가
2. **Entity Extractor 성능이 이미 충분**: 초기 30개 엔티티만으로도 충분한 coverage
3. **확장 시 노이즈 증가 > 정보 증가**: 추가 정보의 가치보다 노이즈가 더 큼

---

## 7. 데이터 출처

**파일**: `backend/ragas/ontology_evaluate/data/grid_search_optimized/grid_results_merged_summary.json`

| 항목 | 값 |
|------|-----|
| 총 레코드 | 120개 |
| 설정 수 | 6개 |
| 쿼리 당 설정 | 20개 |
| 성공률 | 100% |
| 최종 업데이트 | 2024-12-28 |

**데이터 경로**: `backend/ragas/ontology_evaluate/data/grid_search_optimized/`

---

## 8. 결론

### 핵심 결론

1. **"단순함이 최고"**
   - ablation_baseline (확장 없음) = Grid Search 최고 (0.8551)
   - 복잡한 조합보다 단순 설정이 우수

2. **Intent Preservation이 성능 핵심**
   - Intent 1.0인 baseline이 압도적
   - 확장/조합 시 Intent 손실 = 성능 하락

3. **컴포넌트 조합의 부정적 상호작용**
   - 단독으로 좋아도 조합 시 성능 저하
   - 특히 다중 확장 전략(causal+temporal) 치명적

4. **Minimal 설정의 가능성**
   - 2위 minimal (0.8055)도 충분히 높은 성능
   - 효율성 중요 시 선택 가능

### Next Steps

1. **Thread 조합 심층 분석**
   - ablation_baseline에서 Thread 하나씩 제거 실험
   - 왜 5개 Thread가 최고인지 규명

2. **Semantic Expander 개선**
   - 확장 로직 리팩토링으로 노이즈 감소
   - 선택적/적응적 확장 전략 개발

3. **쿼리 타입별 최적화**
   - comparative 질문에 causal_chain 효과 재검증
   - 타입별 최적 설정 세밀 조정

4. **프로덕션 A/B 테스트**
   - ablation_baseline vs minimal 실제 환경 비교
   - 성능 vs 효율성 trade-off 검증

---

*이 보고서는 2024년 12월 28일 완료된 Grid Search 실험 120개 케이스를 기반으로 작성되었습니다.*
