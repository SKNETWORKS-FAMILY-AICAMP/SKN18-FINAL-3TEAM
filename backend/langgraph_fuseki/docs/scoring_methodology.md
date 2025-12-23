# 점수 계산 방법론 (Scoring Methodology)

> 한국사 RAG 시스템의 엔티티 관련성 정량화 체계

---

## 📋 목차

1. [개요](#개요)
2. [전체 파이프라인에서의 점수 계산](#전체-파이프라인에서의-점수-계산)
3. [3단계 가중치 시스템](#3단계-가중치-시스템)
4. [Semantic Expansion 점수 계산](#semantic-expansion-점수-계산)
5. [Path Evidence Aggregation 점수 계산](#path-evidence-aggregation-점수-계산)
6. [베이스라인 테스트](#베이스라인-테스트)
7. [향후 실험 계획](#향후-실험-계획)

---

## 개요

### 점수 계산의 목적

온톨로지 그래프에서 추출된 근거(evidence)들의 **관련성(relevance)**을 평가하여, 질문에 가장 적합한 근거를 선별합니다.

### 핵심 원칙

1. **다층 가중치 구조**: Semantic Expansion → Thread Type → Entity Boost
2. **설정 기반 점수**: 모든 가중치는 환경변수로 제어 가능
3. **SPARQL 연결 분석**: 키워드가 연결된 노드에 있으면 추가 점수
4. **수렴 노드 감지**: 여러 엔티티를 연결하는 노드에 보너스

---

## 전체 파이프라인에서의 점수 계산

### 점수 계산이 발생하는 단계

```
[Stage 0/6] History Check
   └─ 점수 계산 없음

[Stage 1/6] Query Classification
   └─ 점수 계산 없음

[Stage 1.5/6] User Intent Clarification
   └─ 점수 계산 없음

[Stage 2/6] Entity Extraction
   ├─ base_score: TTL 매칭 점수 (1.0 / 0.7 / 0.3)
   ├─ name_match_boost: 키워드별 +0.5
   └─ sparql_connected_bonus: 연결 노드 분석 (+0.1/match, 최대 +0.3)
   📊 출력: query_entities (각 엔티티에 base_score 포함)

[Stage 3/6] Semantic Expansion ⭐ 1차 점수 계산
   ├─ 4가지 확장 방법 (causal_chain, temporal, category, pgvector)
   ├─ 각 방법별 relevance_score 계산
   ├─ sparql_connected_bonus 추가
   └─ semantic_weight 적용 (FIXED_SCORE_*)
   📊 출력: expanded_entities (각 엔티티에 relevance_score 포함)

[Stage 4/6] Parallel Knowledge Retrieval
   └─ 점수 계산 없음 (5개 스레드에서 SPARQL 쿼리만 실행)
   📊 출력: thread_results (각 스레드별 raw triples)

[Stage 5/6] Path Evidence Aggregation ⭐ 2차 점수 계산 (최종)
   ├─ base_weight: Thread Type Weight 적용
   ├─ relevance_score: 트리플 관련성 평가
   ├─ entity_boost: 질문 엔티티 매칭 품질 반영
   ├─ convergence_bonus: 수렴 노드 감지 (×1.1)
   └─ final_weight = base_weight × relevance_score × entity_boost × convergence
   📊 출력: all_paths (각 근거에 weight 포함, 상위 15개 선택)

[Stage 6/6] Story Generator
   └─ 점수 계산 없음 (상위 15개 근거로 LLM 답변 생성)
```

---

## 3단계 가중치 시스템

### Level 1: Semantic Expansion Weights

**목적**: 의미론적 확장 방법의 중요도 반영

**4가지 방법**:
- `causal_chain`: 인과관계 체인 (예: leadsTo, causedBy)
- `temporal`: 시간적 맥락 (±10년 범위)
- `category`: 카테고리 분류 (동일 주제/유형)
- `pgvector`: 벡터 유사도 (임베딩 검색)

**설정 위치**: `config.py` → `FIXED_SCORE_*`

**현재 값**: 모두 **1.0** (베이스라인 테스트)

---

### Level 2: Thread Type Weights

**목적**: 5개 병렬 검색 스레드의 상대적 중요도 반영

**5가지 스레드**:
- `outgoing_relations`: A → B (나가는 관계)
- `incoming_relations`: B → A (들어오는 관계)
- `entity_properties`: A → "literal" (속성 값)
- `connected_entities`: A → B → C (2-hop 연결)
- `type_and_summary`: rdf:type, Summary (타입 및 요약)

**설정 위치**: `config.py` → `THREAD_WEIGHT_*`

**현재 값**: 모두 **1.0** (베이스라인 테스트)

---

### Level 3: Entity Boost

**목적**: 질문 엔티티와의 매칭 품질 반영

**3가지 모드**:
- `exact_match`: 정확히 일치
- `partial_match`: 부분 일치
- `normalized_match`: 정규화 일치

**설정 위치**: `config.py` → `QUERY_ENTITY_MATCH_BOOST_*`

**현재 값**: 모두 **1.0** (베이스라인 테스트)

---

## Semantic Expansion 점수 계산

### 계산 흐름

```
원본 엔티티 (예: "세조 즉위")
   ↓
4가지 확장 방법 병렬 실행
   ↓
각 확장된 엔티티마다 relevance_score 계산
   ↓
SPARQL 연결 분석으로 보너스 추가
   ↓
semantic_weight 적용
   ↓
최종 relevance_score
```

### 방법별 점수 계산 로직

#### 1. Causal Chain (인과관계 체인)

**SPARQL 쿼리**: `leadsTo`, `causedBy`, `triggeredBy` 관계 추적

**점수 계산**:
```
relevance_score = 1.0 (기본값)
+ SPARQL 연결 분석 보너스 (최대 +0.3)
× FIXED_SCORE_CAUSAL_CHAIN (현재 1.0)
```

**예시**:
- 질문: "세조 즉위의 원인은?"
- 확장: "계유정난" (causedBy 관계)
- 점수: 1.0 + 0.2 (SPARQL 연결) × 1.0 = **1.2**

---

#### 2. Temporal (시간적 맥락)

**SPARQL 쿼리**: ±10년 범위 내 엔티티 검색 (`hasYear` 속성 활용)

**점수 계산**:
```
relevance_score = 1.0 (기본값)
+ SPARQL 연결 분석 보너스 (최대 +0.3)
× FIXED_SCORE_TEMPORAL (현재 1.0)
```

**예시**:
- 질문: "임진왜란의 영향은?" (1592년)
- 확장: "광해군 즉위" (1608년, +16년)
- 점수: 1.0 + 0.1 × 1.0 = **1.1**

---

#### 3. Category (카테고리)

**SPARQL 쿼리**: `hasCategory` 속성으로 동일 유형 검색

**점수 계산**:
```
relevance_score = 1.0 (기본값)
+ SPARQL 연결 분석 보너스 (최대 +0.3)
× FIXED_SCORE_CATEGORY (현재 1.0)
```

**예시**:
- 질문: "강화도 조약의 배경은?" (카테고리: 조약)
- 확장: "병자수호조약" (동일 카테고리)
- 점수: 1.0 × 1.0 = **1.0**

---

#### 4. Pgvector (벡터 유사도)

**pgvector 쿼리**: 코사인 거리 기반 유사 엔티티 검색

**점수 계산** (하이브리드):
```
relevance_score = 고정 점수 × α + 코사인 유사도 × (1 - α)
                = 0.65 × 0.6 + similarity × 0.4
                = 0.39 + similarity × 0.4
```

**예시**:
- 질문: "을미사변의 원인은?"
- 확장: "명성황후 시해" (코사인 유사도 0.880)
- 점수: 0.39 + (0.880 × 0.4) = **0.742**

### 코사인 거리 vs 유사도

| Cosine Distance | Cosine Similarity | 해석           |
| --------------- | ----------------- | -------------- |
| 0.0             | 1.000             | 완전히 동일    |
| 0.1             | 0.900             | 매우 유사      |
| 0.2             | 0.800             | 유사           |
| 0.5             | 0.500             | 보통           |
| 1.0             | 0.000             | 무관           |

**변환 공식**: `Cosine Similarity = 1 - Cosine Distance`

---

### SPARQL 연결 분석 보너스

모든 확장 방법에 공통으로 적용되는 추가 점수입니다.

**로직**:
```
1. 확장된 엔티티의 연결 노드 조회 (SPARQL)
2. 각 연결 노드에 질문 키워드가 포함되어 있는지 확인
3. 포함될 때마다 +0.1 (최대 +0.3)
```

**예시**:
```
확장 엔티티: "계유정난"
연결 노드:
  - "계유정난" --involves--> "세조" (키워드 "세조" 포함) → +0.1
  - "계유정난" --involves--> "단종" (키워드 "세조" 미포함) → +0.0
  - "계유정난" --Summary--> "세조가 단종을 폐위..." (키워드 "세조" 포함) → +0.1

총 보너스: +0.2
```

---

## Path Evidence Aggregation 점수 계산

### 계산 흐름

```
5개 Thread 결과 (triples)
   ↓
각 트리플마다 개별 점수 계산
   ↓
base_weight (Thread Type)
   ↓
relevance_score (트리플 관련성)
   ↓
entity_boost (엔티티 매칭 품질)
   ↓
convergence_bonus (수렴 노드 감지)
   ↓
final_weight = base × relevance × boost × convergence
   ↓
상위 15개 선택
```

### 단계별 점수 계산

#### 1. Base Weight (Thread Type)

**목적**: 스레드 유형별 기본 가중치

**계산**:
```
base_weight = thread_weights.get(thread_type, 1.0)
```

**현재 값** (모두 1.0):
- `outgoing_relations`: 1.0
- `incoming_relations`: 1.0
- `entity_properties`: 1.0
- `connected_entities`: 1.0
- `type_and_summary`: 1.0

---

#### 2. Relevance Score (트리플 관련성)

**목적**: 트리플 (subject, predicate, object)과 질문의 관련성 평가

**3가지 평가 기준**:

**A. 엔티티 매칭** (×1.5)
```
subject 또는 object가 질문 엔티티에 포함되면 ×1.5
```

**B. 키워드 포함** (×1.3)
```
subject, predicate, object 중 하나라도 질문 키워드 포함 시 ×1.3
```

**C. Property Groups 매칭** (×1.2)
```
predicate가 선택된 property_groups에 속하면 ×1.2
```

**계산 순서**:
```
1. 기본 점수 = 1.0
2. 엔티티 매칭 체크 → 1.0 × 1.5 = 1.5
3. 키워드 포함 체크 → 1.5 × 1.3 = 1.95
4. Property Groups 매칭 → 1.95 × 1.2 = 2.34

최종 relevance_score = 2.34
```

**예시**:
```
질문: "세조의 재위 기간은?"
키워드: ["세조", "재위", "기간"]
질문 엔티티: ["세조"]

트리플: ("세조", "hasReignStart", "1455")

1. 엔티티 매칭: "세조" in query_entities → ×1.5
2. 키워드 포함: "재위" not in triple → ×1.0
3. Property Groups: "hasReignStart" in "재위" 그룹 → ×1.2

relevance_score = 1.0 × 1.5 × 1.0 × 1.2 = 1.8
```

---

#### 3. Entity Boost (엔티티 매칭 품질)

**목적**: 질문 엔티티와의 매칭 품질 반영

**계산**:
```
if subject in query_entities or object in query_entities:
    entity_boost = QUERY_ENTITY_MATCH_BOOST_EXACT  # 현재 1.0
else:
    entity_boost = 1.0
```

**현재**: 모든 boost 값이 1.0이므로 실질적 영향 없음 (베이스라인)

---

#### 4. Convergence Bonus (수렴 노드 감지)

**목적**: 여러 질문 엔티티를 연결하는 중요 노드 발견

**로직**:
```
1. 모든 트리플에서 노드별 연결 엔티티 수 계산
2. 2개 이상의 질문 엔티티와 연결된 노드 → 수렴 노드
3. 수렴 노드가 포함된 트리플 → ×1.1
```

**예시**:
```
질문: "세조와 단종의 관계는?"
질문 엔티티: ["세조", "단종"]

트리플 분석:
  - ("계유정난", "involves", "세조")
  - ("계유정난", "involves", "단종")

수렴 노드: "계유정난" (2개 엔티티 모두와 연결)

트리플: ("계유정난", "Summary", "1453년 수양대군이...")
convergence_bonus = 1.1
```

---

### 최종 Weight 계산

```
final_weight = base_weight × relevance_score × entity_boost × convergence_bonus
```

**전체 예시**:
```
트리플: ("세조", "hasReignStart", "1455")

base_weight = 1.0 (outgoing_relations)
relevance_score = 1.8 (엔티티 매칭 + Property Groups)
entity_boost = 1.0 (현재 baseline)
convergence_bonus = 1.0 (수렴 노드 아님)

final_weight = 1.0 × 1.8 × 1.0 × 1.0 = 1.8
```

---

## 베이스라인 테스트

### 현재 설정 (모든 가중치 = 1.0)

```
# Semantic Expansion Weights
FIXED_SCORE_CAUSAL_CHAIN = 1.0
FIXED_SCORE_TEMPORAL = 1.0
FIXED_SCORE_CATEGORY = 1.0
FIXED_SCORE_PGVECTOR = 1.0

# Thread Type Weights
THREAD_WEIGHT_OUTGOING_RELATIONS = 1.0
THREAD_WEIGHT_INCOMING_RELATIONS = 1.0
THREAD_WEIGHT_ENTITY_PROPERTIES = 1.0
THREAD_WEIGHT_CONNECTED_ENTITIES = 1.0
THREAD_WEIGHT_TYPE_AND_SUMMARY = 1.0

# Entity Boost
QUERY_ENTITY_MATCH_BOOST_EXACT = 1.0
QUERY_ENTITY_MATCH_BOOST_PARTIAL = 1.0
QUERY_ENTITY_MATCH_BOOST_NORMALIZED = 1.0
```

### 베이스라인 목적

**가중치 없이 순수한 성능 측정**하여, 향후 가중치 튜닝의 기준점(baseline) 확보

**측정 항목**:
- RAGAS nv_context_relevance (불필요한 컨텍스트 비율)
- RAGAS answer_relevancy (답변 관련성)
- RAGAS faithfulness (근거 충실도)

**베이스라인 후 진행**:
1. RAGAS 평가 결과 분석
2. 80가지 조합 실험 (4 × 5 × 4)
3. 최적 가중치 조합 도출
4. 질문 유형별 가중치 설정

---

## 향후 실험 계획

### Phase 1: 베이스라인 측정 (현재)

**목표**: 가중치 없는 순수 성능 측정

**설정**: 모든 가중치 = 1.0

**평가**:
- 40개 질문 (외국인 20개 + 아이들 20개)
- RAGAS 3가지 메트릭
- 실행 시간 측정

---

### Phase 2: 단일 변수 실험

**목표**: 각 가중치 레벨의 영향도 개별 측정

**실험 1: Semantic Expansion Weights**
```
causal_chain: [1.0, 1.2, 1.4, 1.6]
temporal, category, pgvector: 1.0 (고정)

→ 4가지 조합 테스트
```

**실험 2: Thread Type Weights**
```
outgoing_relations: [1.0, 1.2, 1.4, 1.6]
나머지: 1.0 (고정)

→ 5개 스레드 × 4가지 값 = 20가지 조합
```

**실험 3: Entity Boost**
```
exact_match: [1.0, 1.2, 1.5, 2.0]
나머지: 1.0 (고정)

→ 4가지 조합
```

---

### Phase 3: 조합 실험

**목표**: 최적 가중치 조합 발견

**실험 설계**:
```
4 (semantic) × 5 (thread) × 4 (boost) = 80가지 조합
```

**병렬 실행**:
```bash
# 8개 워커로 병렬 실행
./backend/ragas/fuseki/run_parallel.sh 0 10
```

**평가 기준**:
1. nv_context_relevance 최대화 (불필요한 컨텍스트 최소화)
2. answer_relevancy 유지/향상
3. faithfulness 유지/향상
4. 실행 시간 ≤ 30초

---

### Phase 4: 질문 유형별 가중치

**목표**: 질문 유형에 따라 동적으로 가중치 조정

**질문 유형**:
- `causal`: 인과관계 중심
- `factual`: 사실 확인 중심
- `deep_analysis`: 심층 분석 중심
- `comparative`: 비교 분석 중심

**가중치 전략 예시**:
```
causal 질문:
  - FIXED_SCORE_CAUSAL_CHAIN = 1.5 (강화)
  - THREAD_WEIGHT_INCOMING_RELATIONS = 1.3 (원인 추적)

factual 질문:
  - THREAD_WEIGHT_ENTITY_PROPERTIES = 1.4 (속성 중요)
  - THREAD_WEIGHT_TYPE_AND_SUMMARY = 1.3 (기본 정보)

deep_analysis 질문:
  - THREAD_WEIGHT_CONNECTED_ENTITIES = 1.5 (연결 관계 중요)
  - QUERY_ENTITY_MATCH_BOOST_EXACT = 1.3 (정확한 매칭)
```

---

### Phase 5: 실시간 튜닝

**목표**: 사용자 피드백 기반 가중치 자동 조정

**방법**:
1. 사용자 만족도 수집 (👍/👎)
2. 불만족 케이스 분석
3. 가중치 미세 조정 (±0.1)
4. A/B 테스트로 검증

---

## 요약

### 점수 계산 핵심 흐름

```
[Stage 3] Semantic Expansion
   ↓ relevance_score (4가지 방법)
   ↓ + SPARQL 연결 분석 보너스
   ↓ × semantic_weight
   ↓
[Stage 5] Path Evidence Aggregation
   ↓ base_weight (Thread Type)
   ↓ × relevance_score (트리플 관련성)
   ↓ × entity_boost (매칭 품질)
   ↓ × convergence_bonus (수렴 노드)
   ↓
final_weight → 상위 15개 선택
```

### 현재 상태

- **모든 가중치 = 1.0** (베이스라인 테스트)
- **실질적 차별화 요소**: SPARQL 연결 분석, 트리플 관련성 평가, 수렴 노드 감지
- **다음 단계**: RAGAS 평가 → 80가지 조합 실험 → 최적 가중치 도출

### 문서 참고

- [conversational_intent_clarification.md](./conversational_intent_clarification.md) - 대화형 의도 확인 시스템
- [README.md](./README.md) - 전체 시스템 아키텍처
- [WEIGHTS_ANALYSIS.md](../../ragas/fuseki/WEIGHTS_ANALYSIS.md) - 가중치 실험 결과 (실험 후 작성 예정)

---

**최종 업데이트**: 2025-12-23
**현재 버전**: Phase 1 (베이스라인 테스트)
