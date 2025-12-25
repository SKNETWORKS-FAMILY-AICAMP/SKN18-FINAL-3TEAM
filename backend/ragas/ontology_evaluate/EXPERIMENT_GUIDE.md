# Ontology Evaluate 실험 가이드

## 📌 실험 개요

이 가이드는 **3가지 핵심 컴포넌트**의 가중치를 최적화하여 Ontology 시스템의 성능을 평가하는 전체 실험 프로세스를 설명합니다.

### 최적화 대상 컴포넌트

1. **Semantic Expander** (의미 확장)
   - `temporal_weight`: 시간적 확장 가중치
   - `causal_weight`: 인과관계 확장 가중치
   - `vector_weight`: 벡터 유사도 확장 가중치
   - 제약: `temporal + causal + vector = 1.0`

2. **Thread Weights** (지식 검색 가중치)
   - `outgoing_relations`: 나가는 관계
   - `incoming_relations`: 들어오는 관계
   - `entity_properties`: 엔티티 속성
   - `connected_entities`: 연결된 엔티티
   - `type_and_summary`: 타입 및 요약

3. **Entity Boost** (엔티티 매칭 부스트)
   - `exact_match`: 정확한 매칭 배율
   - `partial_match`: 부분 매칭 배율

---

## 🎯 실험 전체 Flow

```
Step 1: Baseline Ablation Study
  └─ 각 컴포넌트의 기본 성능 측정
     ├─ semantic_expander (필수)
     ├─ thread (선택)
     └─ entity_boost (선택)

Step 2: 전체 데이터셋 가중치 최적화 (빠른 확인)
  └─ 모든 query_type을 섞어서 기본 최적 가중치 찾기

Step 3: Query Type별 가중치 최적화 (핵심)
  └─ factual / causal / comparative / deep_analysis별로 최적화
     ├─ semantic_expander (필수)
     ├─ thread (선택, 시간 소요 큼)
     └─ entity_boost (선택)

Step 4: config.yaml 업데이트
  └─ 실험 결과를 config.yaml에 반영

Step 5: 최종 평가
  └─ 확정된 가중치로 전체 시스템 평가 (200개 샘플)
```

---

## ⚙️ 실험 실행 명령어

### Step 1: Baseline Ablation Study

**목적**: 각 컴포넌트의 기본 성능 파악

```bash
# 1-1. Semantic Expander Baseline
python -m backend.ragas.ontology_evaluate.experiments.run_baseline \
    --group semantic_expander \
    --limit 10 \
    --queries backend/ragas/ontology_evaluate/data/test_queries.json \
    --output backend/ragas/ontology_evaluate/data/results

# 결과 파일:
# - semantic_expander_ablation_full.json (전체 state)
# - semantic_expander_ablation_summary.json (점수, 수치만) ✨
```

```bash
# 1-2. Thread Baseline (선택)
python -m backend.ragas.ontology_evaluate.experiments.run_baseline \
    --group thread \
    --limit 10

# 1-3. Entity Boost Baseline (선택)
python -m backend.ragas.ontology_evaluate.experiments.run_baseline \
    --group entity_boost \
    --limit 10
```

**결과 확인**:
```bash
# Summary 파일로 빠른 확인
cat backend/ragas/ontology_evaluate/data/results/semantic_expander_ablation_summary.json | jq '.[0] | {
  query: .query,
  query_type: .query_type,
  score: .intent_aware_score,
  entities: .num_extracted_entities,
  evidences: .num_evidences
}'
```

---

### Step 2: 전체 데이터셋 가중치 최적화

**목적**: 전체 질문에 대한 기본 최적 가중치 찾기 (빠른 확인용)

```bash
# 2-1. Semantic Expander 최적화 (50개 샘플)
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander \
    --method grid_search \
    --limit 50 \
    --output backend/ragas/ontology_evaluate/data/results

# 결과 파일:
# - semantic_expander_weights_all_full.json
# - semantic_expander_weights_all_summary.json ✨
```

```bash
# 2-2. Thread 최적화 (선택, 시간 소요 매우 큼)
# 주의: 4^5 = 1024개 조합, 실행 시간 예상 3-5시간
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component thread \
    --method grid_search \
    --limit 20 \
    --output backend/ragas/ontology_evaluate/data/results

# 2-3. Entity Boost 최적화 (선택)
# 5×5 = 25개 조합
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component entity_boost \
    --method grid_search \
    --limit 50 \
    --output backend/ragas/ontology_evaluate/data/results
```

**결과 확인**:
```bash
# Best weights 확인
cat backend/ragas/ontology_evaluate/data/results/semantic_expander_weights_all_summary.json | jq '.best_result'

# 출력 예시:
# {
#   "trial_id": 42,
#   "weights": {
#     "temporal_weight": 0.3,
#     "causal_weight": 0.5,
#     "vector_weight": 0.2
#   },
#   "score": 0.847
# }
```

---

### Step 3: Query Type별 가중치 최적화 (핵심!)

**목적**: 각 질문 유형에 최적화된 가중치 찾기

#### 3-1. Semantic Expander (필수)

```bash
# Factual 질문
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander \
    --query_type factual \
    --method grid_search \
    --limit 50

# Causal 질문
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander \
    --query_type causal \
    --method grid_search \
    --limit 50

# Comparative 질문
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander \
    --query_type comparative \
    --method grid_search \
    --limit 50

# Deep Analysis 질문
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander \
    --query_type deep_analysis \
    --method grid_search \
    --limit 50
```

#### 3-2. Thread (선택, 시간 소요 큼)

```bash
# 주의: 각 query_type당 1024 trials × N개 질문
# 실행 시간: query_type당 1-2시간 예상

# Factual 질문
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component thread \
    --query_type factual \
    --method grid_search \
    --limit 20

# 나머지 query_type도 동일하게 실행
```

#### 3-3. Entity Boost (선택)

```bash
# Factual 질문
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component entity_boost \
    --query_type factual \
    --method grid_search \
    --limit 50

# 나머지 query_type도 동일하게 실행
```

**결과 확인**:
```bash
# 모든 query_type의 best weights 확인
for qtype in factual causal comparative deep_analysis; do
  echo "=== Semantic Expander: $qtype ==="
  cat backend/ragas/ontology_evaluate/data/results/semantic_expander_weights_${qtype}_summary.json | jq '.best_result.weights'
done

# Thread weights 확인
for qtype in factual causal comparative deep_analysis; do
  echo "=== Thread: $qtype ==="
  cat backend/ragas/ontology_evaluate/data/results/thread_weights_${qtype}_summary.json | jq '.best_result.weights'
done

# Entity Boost 확인
for qtype in factual causal comparative deep_analysis; do
  echo "=== Entity Boost: $qtype ==="
  cat backend/ragas/ontology_evaluate/data/results/entity_boost_weights_${qtype}_summary.json | jq '.best_result.weights'
done
```

---

### Step 4: config.yaml 업데이트

**목적**: Step 3에서 찾은 최적 가중치를 config.yaml에 반영

#### 4-1. 결과 확인

```bash
# Factual 질문의 Semantic Expander best weights
cat backend/ragas/ontology_evaluate/data/results/semantic_expander_weights_factual_summary.json | jq '.best_result.weights'

# 출력 예시:
# {
#   "temporal_weight": 0.5,
#   "causal_weight": 0.2,
#   "vector_weight": 0.3
# }
```

#### 4-2. config.yaml 수정

[backend/ragas/ontology_evaluate/config/config.yaml](backend/ragas/ontology_evaluate/config/config.yaml) 파일을 열고 업데이트:

```yaml
semantic_expander:
  query_type_weights:
    factual:
      temporal_weight: 0.5  # ← Step 3-1 결과 반영
      causal_weight: 0.2
      vector_weight: 0.3

    causal:
      temporal_weight: 0.2  # ← Step 3-1 결과 반영
      causal_weight: 0.6
      vector_weight: 0.2

    # ... 나머지도 동일하게

aggregator_threads:
  query_type_weights:
    factual:
      outgoing_relations: 1.0  # ← Step 3-2 결과 반영
      incoming_relations: 0.8
      entity_properties: 1.2
      connected_entities: 0.8
      type_and_summary: 1.0

    # ... 나머지도 동일하게

entity_boost:
  query_type_multipliers:
    factual:
      exact_match: 2.5  # ← Step 3-3 결과 반영
      partial_match: 1.3

    # ... 나머지도 동일하게
```

---

### Step 5: 최종 평가

**목적**: 최적화된 가중치로 전체 시스템 성능 평가

```bash
# 5-1. 최종 평가 실행 (200개 샘플)
python -m backend.ragas.ontology_evaluate.experiments.run_baseline \
    --group semantic_expander \
    --limit 200 \
    --queries backend/ragas/ontology_evaluate/data/test_queries.json \
    --output backend/ragas/ontology_evaluate/data/results \
    --intent-aware

# 결과 파일:
# - semantic_expander_ablation_full.json
# - semantic_expander_ablation_summary.json ✨
```

**최종 결과 분석**:
```bash
# Query Type별 평균 점수 계산
cat backend/ragas/ontology_evaluate/data/results/semantic_expander_ablation_summary.json | \
  jq 'group_by(.query_type) | map({
    query_type: .[0].query_type,
    count: length,
    avg_score: (map(.intent_aware_score) | add / length),
    avg_entities: (map(.num_extracted_entities) | add / length),
    avg_evidences: (map(.num_evidences) | add / length),
    avg_time: (map(.execution_time) | add / length)
  })'

# 출력 예시:
# [
#   {
#     "query_type": "factual",
#     "count": 80,
#     "avg_score": 0.847,
#     "avg_entities": 25.3,
#     "avg_evidences": 12.5,
#     "avg_time": 2.1
#   },
#   ...
# ]
```

---

## 📊 실험 우선순위 (시간 제약이 있는 경우)

### 필수 실험 (최소 구성)

```bash
# 1. Semantic Expander만 Query Type별 최적화
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander --query_type factual --limit 50

python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander --query_type causal --limit 50

python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander --query_type comparative --limit 50

python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander --query_type deep_analysis --limit 50

# 2. config.yaml 업데이트 (semantic_expander만)

# 3. 최종 평가
python -m backend.ragas.ontology_evaluate.experiments.run_baseline \
    --group semantic_expander --limit 200 --intent-aware
```

**예상 실행 시간**: 약 2-3시간

### 권장 실험 (중간 구성)

필수 실험 + Entity Boost 최적화

**예상 실행 시간**: 약 4-5시간

### 완전 실험 (전체 구성)

필수 + Entity Boost + Thread 최적화

**예상 실행 시간**: 약 10-15시간 (Thread가 시간 소요 큼)

---

## 📁 결과 파일 구조

```
backend/ragas/ontology_evaluate/data/results/
├── # Step 1: Baseline Ablation
├── semantic_expander_ablation_full.json
├── semantic_expander_ablation_summary.json ✨
├── thread_ablation_full.json
├── thread_ablation_summary.json ✨
├── entity_boost_ablation_full.json
├── entity_boost_ablation_summary.json ✨
│
├── # Step 2: 전체 가중치 최적화
├── semantic_expander_weights_all_full.json
├── semantic_expander_weights_all_summary.json ✨
├── thread_weights_all_full.json
├── thread_weights_all_summary.json ✨
├── entity_boost_weights_all_full.json
├── entity_boost_weights_all_summary.json ✨
│
├── # Step 3: Query Type별 가중치 최적화
├── semantic_expander_weights_factual_full.json
├── semantic_expander_weights_factual_summary.json ✨
├── semantic_expander_weights_causal_full.json
├── semantic_expander_weights_causal_summary.json ✨
├── semantic_expander_weights_comparative_full.json
├── semantic_expander_weights_comparative_summary.json ✨
├── semantic_expander_weights_deep_analysis_full.json
├── semantic_expander_weights_deep_analysis_summary.json ✨
│
├── thread_weights_factual_full.json
├── thread_weights_factual_summary.json ✨
├── ... (causal, comparative, deep_analysis)
│
├── entity_boost_weights_factual_full.json
├── entity_boost_weights_factual_summary.json ✨
└── ... (causal, comparative, deep_analysis)
```

**✨ = 평가에 적합한 Summary 파일** (점수, 수치만 포함)

---

## 🔍 Summary 파일 구조

```json
{
  "experiment_name": "semantic_expander_baseline",
  "description": "모든 Semantic Expander 비활성화",
  "query": "세종대왕이 훈민정음을 창제한 시기는 언제인가?",
  "query_type": "factual",
  "success": true,
  "execution_time": 2.3,
  "config": {
    "semantic_expander": {
      "temporal": false,
      "causal_chain": false,
      "pgvector": false
    }
  },
  "final_answer": "1443년 세종대왕이 훈민정음을 창제했습니다...",
  "num_extracted_entities": 25,
  "num_expanded_entities": 42,
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
  "intent_aware_score": 0.847,
  "weighted_metrics": {
    "tbox_consistency": 0.1275,
    "intent_preservation": 0.164,
    ...
  }
}
```

---

## 📈 예상 성능 개선

| 컴포넌트             | 기본값 성능 | 최적화 후 성능 | 개선율  |
| -------------------- | ----------- | -------------- | ------- |
| Semantic Expander    | 0.788       | 0.860          | +9.1%   |
| Thread               | 0.795       | 0.835          | +5.0%   |
| Entity Boost         | 0.800       | 0.825          | +3.1%   |
| **전체 시스템**      | **0.788**   | **0.890**      | **+12.9%** |

---

## ⚠️ 주의사항

1. **Thread 최적화는 시간 소요가 매우 큼** (4^5 = 1024 trials)
   - 꼭 필요한 경우에만 실행
   - `--limit` 값을 작게 설정 (10-20개)

2. **GPU/메모리 부족 시**
   - `--limit` 값을 줄이기 (10-20개)
   - Grid Search 대신 Bayesian Optimization 사용 (`--method bayesian`)

3. **결과 검증**
   - Summary 파일로 빠르게 확인
   - 이상치(outlier)가 있으면 해당 trial 재실행

4. **config.yaml 백업**
   - 실험 전에 백업본 생성
   - `cp config.yaml config.yaml.backup`

---

## 🚀 빠른 시작 (Quick Start)

```bash
# 1. 필수 실험만 실행 (Semantic Expander만)
cd /Users/jina/Documents/Documents\ -\ Jina\ MacBook\ Air/GitHub/SKN18-FINAL-3TEAM

# Factual
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander --query_type factual --limit 50

# Causal
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander --query_type causal --limit 50

# Comparative
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander --query_type comparative --limit 50

# Deep Analysis
python -m backend.ragas.ontology_evaluate.experiments.optimize_weights \
    --component semantic_expander --query_type deep_analysis --limit 50

# 2. 결과 확인 및 config.yaml 업데이트
for qtype in factual causal comparative deep_analysis; do
  echo "=== $qtype ==="
  cat backend/ragas/ontology_evaluate/data/results/semantic_expander_weights_${qtype}_summary.json | jq '.best_result.weights'
done

# 3. 최종 평가
python -m backend.ragas.ontology_evaluate.experiments.run_baseline \
    --group semantic_expander --limit 200 --intent-aware
```

---

**작성일**: 2025-12-25
**버전**: 1.0
**문의**: 실험 중 문제 발생 시 이슈 등록
