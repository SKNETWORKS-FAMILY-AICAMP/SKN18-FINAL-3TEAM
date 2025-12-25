# Step 1-B: 재실험 계획서

**목적**: Step 1 실패 원인 제거 후 재실험
**일자**: 2025-12-25

---

## Step 1 실패 원인 요약

### 원인 1: SPARQL 타임아웃 (Critical)

**증상**:

```
HTTPConnectionPool(host='localhost', port=3030): Read timed out
```

**영향**:

- 인과관계 체인 검색 실패
- 시간적 확장 검색 실패

**해결**:

```bash
# .env 파일에 추가됨
FUSEKI_URL=""
```

**검증**:

```bash
# 확인
tail -1 /Users/jina/Documents/Documents\ -\ Jina\ MacBook\ Air/GitHub/SKN18-FINAL-3TEAM/.env
# 출력: FUSEKI_URL=""
```

### 원인 2: TTL 데이터 누락

**실패 쿼리**: "불국사는 어느 시대에 건립되었는가?"

**확인 결과**:

```bash
grep -i "불국사" korean_history_normalized.ttl
# 출력: (없음)

grep -i "bulguk" korean_history_normalized.ttl
# 출력: (없음)
```

**결론**: TTL 데이터에 "불국사" 엔티티 없음

**해결**:

- 옵션 1: 실패 쿼리 제외하고 재실험
- 옵션 2: TTL 데이터 추가 (시간 소요)
- **선택**: 옵션 1 (실패 쿼리 제외)

---

## 재실험 설정

### 변경 사항

| 항목       | Step 1 (원본)  | Step 1-B (재실험) |
| ---------- | -------------- | ----------------- |
| FUSEKI_URL | localhost:3030 | "" (비활성화)     |
| 샘플 수    | 10개           | 10개              |
| 실패 쿼리  | 포함           | 제외              |
| Query Type | factual만      | factual만         |
| 가중치     | 1.0 (default)  | 1.0 (default)     |
| LLM Judge  | gpt-4o         | gpt-5-mini        |

### 실행 명령어

```bash
# 1. 환경변수 확인
tail -1 .env
# 출력: FUSEKI_URL=""

# 2. 재실험 실행
```

---

## 예상 결과

### 목표 메트릭

| 메트릭             | Step 1 (원본) | Step 1-B (목표) |
| ------------------ | ------------- | --------------- |
| Failure Rate       | 10% (1/10)    | 0% (0/20)       |
| Baseline Avg Score | 0.656         | 0.65 ~ 0.70     |
| Std Dev            | 0.101         | < 0.10          |
| Avg Entities       | 7.7           | > 8.0           |
| Avg Time           | 106s          | < 100s          |

### 검증 기준

**재실험 성공 조건**:

1. ✅ Failure rate = 0%
2. ✅ Baseline score ≥ 0.65
3. ✅ SPARQL 타임아웃 없음
4. ✅ N ≥ 20

**재실험 실패 시**:

- TTL 데이터 추가 필요
- 샘플 수 추가 증가
- 다른 Query Type 테스트

---

## 재실험 후 분석 계획

### 분석 1: Baseline 안정성 확인

```bash
cat results_rerun/semantic_expander_ablation_summary.json | jq '
[.[] | select(.experiment_name == "semantic_expander_baseline")] |
{
  count: length,
  avg_score: (map(.intent_aware_score) | add / length),
  std_dev: (map(.intent_aware_score) as $s | ($s | add / length) as $m | ($s | map(pow(. - $m; 2)) | add / length | sqrt)),
  min: (map(.intent_aware_score) | min),
  max: (map(.intent_aware_score) | max),
  failures: (map(select(.num_extracted_entities == 0)) | length)
}
'
```

### 분석 2: Semantic Expander 효과 재검증

```bash
cat results_rerun/semantic_expander_ablation_summary.json | jq '
group_by(.experiment_name) |
map({
  experiment: .[0].experiment_name,
  avg_score: (map(.intent_aware_score) | add / length),
  vs_baseline: ((map(.intent_aware_score) | add / length) - BASELINE_SCORE)
})
'
```

### 분석 3: 실패 케이스 확인

```bash
cat results_rerun/semantic_expander_ablation_summary.json | jq '
[.[] | select(.num_extracted_entities == 0 or .num_evidences == 0)]
'
# 출력: [] (빈 배열이어야 함)
```

---

## 다음 단계 (재실험 성공 시)

### Step 2: Query Type별 Semantic Expander 가중치 최적화

**실행 순서**:

```bash
# 2-1. Factual 가중치 최적화
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander \
    --query_type factual \
    --limit 50

# 2-2. Causal 가중치 최적화
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander \
    --query_type causal \
    --limit 50

# 2-3. Comparative 가중치 최적화
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander \
    --query_type comparative \
    --limit 50

# 2-4. Deep Analysis 가중치 최적화
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander \
    --query_type deep_analysis \
    --limit 50
```

**예상 실행 시간**: 각 2-3시간 (총 8-12시간)

---

## 체크리스트

### 재실험 전 준비

- [x] FUSEKI_URL="" 설정 완료
- [x] test_queries.json 확인 (20개 이상 factual 질문)
- [x] 실패 쿼리("불국사") 제외 또는 데이터 추가
- [ ] results_rerun 디렉토리 생성
- [x] LLM API 키 확인

### 재실험 실행

- [ ] run_baseline 실행
- [ ] 실행 중 에러 모니터링
- [ ] 결과 파일 생성 확인

### 재실험 후 검증

- [ ] Failure rate = 0% 확인
- [ ] Baseline score ≥ 0.65 확인
- [ ] Summary 파일 분석
- [ ] EXPERIMENT_RESULTS.md 업데이트

---

**작성일**: 2025-12-25
**상태**: 준비 완료
**실행 대기 중**
