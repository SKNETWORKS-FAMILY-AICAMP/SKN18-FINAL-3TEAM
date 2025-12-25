# Ontology Evaluate 실험 결과

**실험 일자**: 2025-12-25
**실험자**: Jina
**목적**: 가중치 최적화를 위한 Baseline 성능 측정

---

## Step 1: Baseline Ablation Study

### 실험 설정

- **데이터셋**: test_queries.json
- **샘플 수**: 10개 (factual 질문)
- **실험 그룹**: semantic_expander
- **가중치**: 모든 가중치 1.0 (default)
- **LLM Judge**: gpt-5-nano

### 실험 결과 (수치)

| Experiment               | N   | Avg Score | Std Dev | Min   | Max   | Avg Entities | Avg Evidences | Avg Time (s) | Failures |
| ------------------------ | --- | --------- | ------- | ----- | ----- | ------------ | ------------- | ------------ | -------- |
| baseline (모든 확장 OFF) | 10  | 0.656     | 0.101   | 0.508 | 0.800 | 7.7          | 13.5          | 106.2        | 1        |
| full (모든 확장 ON)      | 10  | 0.555     | 0.109   | 0.390 | 0.714 | 9.0          | 13.5          | 111.1        | 1        |
| causal_chain_only        | 10  | 0.521     | 0.125   | 0.328 | 0.714 | 9.0          | 13.5          | 116.8        | 1        |
| temporal_only            | 10  | 0.491     | 0.091   | 0.405 | 0.714 | 9.0          | 13.5          | 115.3        | 1        |
| pgvector_only            | 10  | 0.485     | 0.160   | 0.241 | 0.714 | 9.0          | 13.5          | 114.8        | 1        |

### 성능 비교 (Baseline 대비)

| Experiment        | Score 차이 | 변화율 |
| ----------------- | ---------- | ------ |
| full              | -0.101     | -15.4% |
| causal_chain_only | -0.135     | -20.6% |
| temporal_only     | -0.165     | -25.2% |
| pgvector_only     | -0.171     | -26.1% |

---

## 핵심 발견

### 발견 1: Semantic Expander가 성능을 하락시킴

- Baseline (확장 없음): **0.656**
- Full (모든 확장): **0.555** (-15.4%)
- 모든 단일 확장 방법도 Baseline보다 낮음

### 발견 2: 실패 케이스 발생

**실패 쿼리**: "불국사는 어느 시대에 건립되었는가?"

- 모든 실험에서 동일하게 실패
- `num_extracted_entities = 0`
- `num_evidences = 0`
- 원인: TTL 데이터에 "불국사" 엔티티 없음 또는 매칭 실패

### 발견 3: 실행 시간

- Baseline: 106.2초
- Full: 111.1초 (+4.9초, +4.6%)
- Semantic Expander 활성화 시 평균 5-10초 증가

### 발견 4: 표준편차 분석

- pgvector_only: std_dev = 0.160 (가장 불안정)
- temporal_only: std_dev = 0.091 (가장 안정)
- Baseline: std_dev = 0.101 (중간)

---

## 실패 원인 분석

### 원인 1: SPARQL 타임아웃

**증상**:

```
HTTPConnectionPool(host='localhost', port=3030): Read timed out
```

**영향**:

- 인과관계 체인 검색 실패
- 시간적 확장 검색 실패
- 일부 엔티티 확장 불가

**해결 방법**:

1. FUSEKI_URL="" 설정 (SPARQL 비활성화)
2. SPARQL_TIMEOUT 증가 (3초 → 10초)

### 원인 2: TTL 데이터 누락

**증상**:

- "불국사" 쿼리에서 entities = 0

**확인 필요**:

- TTL 파일에 "불국사" 엔티티 존재 여부
- 키워드 추출 실패 여부
- 매칭 threshold 문제 여부

### 원인 3: 노이즈 엔티티 확장

**증상**:

- 확장 활성화 시 오히려 점수 하락

**가설**:

- 확장된 엔티티가 질문과 무관
- 가중치 1.0이 부적절
- Factual 질문에는 확장이 불필요

---

## 통계적 분석

### 가중치 영향 (현재 모든 가중치 = 1.0)

**Semantic Expander 가중치**:

```python
FIXED_SCORES = {
    "temporal": 1.0,
    "causal_chain": 1.0,
    "pgvector": 1.0
}
```

**결과**:

- temporal만: 0.491 (baseline 대비 -25.2%)
- causal만: 0.521 (baseline 대비 -20.6%)
- pgvector만: 0.485 (baseline 대비 -26.1%)
- 셋 다: 0.555 (baseline 대비 -15.4%)

**해석**:

- 현재 가중치로는 어떤 조합도 Baseline을 이기지 못함
- 가중치 최적화 필수

### Score 분포

| Score Range | baseline | full | causal | temporal | pgvector |
| ----------- | -------- | ---- | ------ | -------- | -------- |
| 0.0 - 0.3   | 0        | 0    | 1      | 0        | 1        |
| 0.3 - 0.5   | 1        | 2    | 2      | 4        | 4        |
| 0.5 - 0.7   | 6        | 7    | 6      | 5        | 4        |
| 0.7 - 1.0   | 3        | 1    | 1      | 1        | 1        |

---

## 다음 실험 계획

### Step 1-B: 재실험 (Failure 원인 제거)

**수정 사항**:

1. FUSEKI_URL="" 설정
2. "불국사" 쿼리 제외 또는 TTL 데이터 확인
3. 샘플 수 증가 (10개 → 20개)

**목표**:

- Failure rate 0%
- 안정적인 baseline 확보

### Step 2: Query Type별 데이터 수집

**필요 데이터**:

- factual: 20개
- causal: 20개
- comparative: 20개
- deep_analysis: 20개

### Step 3: Semantic Expander 가중치 최적화

**실험 설계**:

- Component: semantic_expander
- Grid: temporal × causal × vector (합=1.0 제약)
- Grid 크기: 66개 조합
- Query Type별 실험

**예상 결과**:

- factual: temporal=0.1, causal=0.1, vector=0.8
- causal: temporal=0.2, causal=0.6, vector=0.2

---

## Raw Data 파일

### 생성된 파일

```
backend/ragas/ontology_evaluate/data/results/
├── semantic_expander_ablation_full.json      (1.9MB)
├── semantic_expander_ablation_summary.json   (53KB)
```

### Summary JSON 구조

```json
{
  "experiment_name": "semantic_expander_baseline",
  "query": "세종대왕이 훈민정음을 창제한 시기는 언제인가?",
  "query_type": "factual",
  "success": true,
  "execution_time": 106.2,
  "final_answer": "...",
  "num_extracted_entities": 10,
  "num_expanded_entities": 0,
  "num_evidences": 15,
  "num_convergence_nodes": 3,
  "raw_metrics": {
    "tbox_consistency": 0.85,
    "intent_preservation": 0.82,
    "relation_coherence": 0.79,
    "triple_validity": 0.88,
    "evidence_diversity": 0.75,
    "convergence_utilization": 0.81
  },
  "intent_aware_score": 0.656
}
```

---

## 결론

### 실험 1차 결과

1. **Baseline > Full**: 확장이 오히려 성능 하락 (-15.4%)
2. **실패율**: 10% (1/10 케이스)
3. **SPARQL 타임아웃**: 인과관계 체인 검색 실패
4. **표준편차**: 0.091 ~ 0.160 (불안정)

### 재실험 필요성

- FUSEKI 비활성화 필요
- 실패 케이스 제거 필요
- 샘플 수 증가 필요

### 다음 단계

1. ✅ Step 1-B 재실험 (수정 적용)
2. ⏳ Step 2 가중치 최적화
3. ⏳ Step 3 최종 평가

---

**작성일**: 2025-12-25
**문서 버전**: 1.0
**상태**: Step 1 완료, Step 1-B 준비 중
