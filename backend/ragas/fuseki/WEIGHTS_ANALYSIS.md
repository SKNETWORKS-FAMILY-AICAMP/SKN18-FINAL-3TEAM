# 통합 테스트 가중치 분석 및 근거

## 개요

이 문서는 `integrated_test_runner.py`에서 사용하는 커스텀 가중치의 결정 근거를 설명합니다.
모든 기능(4개 Semantic Expanders + 5개 Aggregator Threads)을 동시에 활성화할 때,
각 구성 요소의 상대적 중요도를 반영한 가중치를 적용합니다.

## 분석 기반

### 데이터 출처
- 기존 80가지 조합 테스트 결과 (`ragas_results_10combos_20251216_215508_worker*.json`)
- outgoing_relations vs entity_properties 상세 비교 분석
- 컨텍스트 품질 및 RAGAS 메트릭 분석

### 주요 발견 사항
1. **outgoing_relations**: nv_context_relevance **0.50**, faithfulness **0.572** (최고)
2. **entity_properties**: nv_context_relevance **0.4625**, faithfulness **0.478**
3. 서술적 풍부함(narrative richness)이 RAGAS 점수에 결정적 영향

---

## 1. Semantic Expanders 가중치

```python
"semantic_expanders": {
    "temporal": 1.3,      # 시간 정보는 역사 질문에 매우 중요
    "category": 1.2,      # 카테고리 분류는 정확도 향상
    "causal_chain": 1.4,  # 인과관계는 역사 이해의 핵심 (가장 높음)
    "pgvector": 1.0       # 벡터 검색은 기본 가중치
}
```

### 근거

#### causal_chain: 1.4 (최고 가중치)
**이유**: 역사적 사건의 핵심은 인과관계
- "세조 즉위" → "계유정난" → "단종 복위 모의" 같은 인과 사슬이 역사 이해의 핵심
- 단순 사실 나열보다 **원인-결과** 구조가 질문 답변에 결정적
- 예시: "삼도수군통제사의 역할은 무엇이었나요?" → 임진왜란 → 수군 통제 필요성 → 직제 정비
- 한국사 데이터의 특성: 사건 간 연관성이 풍부하게 기록됨

#### temporal: 1.3 (두 번째로 높음)
**이유**: 시간 정보는 역사 질문의 필수 요소
- 대부분의 역사 질문이 특정 시대/년도와 연관됨
- "1455년", "세조 재위 기간" 같은 시간 정보가 컨텍스트 정확도에 직접 기여
- property_groups.json의 "연도" 그룹이 가장 많이 사용됨 (Year, BirthYear, DeathYear, StartYear, EndYear 등)

#### category: 1.2
**이유**: 카테고리 분류는 정확도 향상에 기여
- 엔티티 타입 분류 (인물, 사건, 제도, 문서 등)가 검색 정확도 향상
- property_groups.json의 32개 그룹 분류 활용
- 예시: "세조" → [인물/군주] 카테고리로 관련 속성 우선 검색

#### pgvector: 1.0 (기본 가중치)
**이유**: 보조적 역할, 시맨틱 유사도 기반 검색
- 벡터 유사도는 전통적 검색 방식의 보완재
- 한국사 도메인에서는 명시적 관계(temporal, causal)가 더 효과적
- 기본 가중치를 유지하되, 다른 expander가 놓칠 수 있는 유사 엔티티 발견에 기여

---

## 2. Aggregator Threads 가중치

```python
"aggregator_threads": {
    "outgoing_relations": 1.3,    # 서술적 풍부함으로 가장 높은 점수
    "incoming_relations": 1.1,    # outgoing보다는 낮지만 관계 정보 중요
    "entity_properties": 1.2,     # 단편적이지만 정확한 정보 제공
    "connected_entities": 1.0,    # 2-hop 관계, 보조적 역할
    "type_and_summary": 1.15      # 타입/요약 정보는 컨텍스트 이해에 도움
}
```

### 근거

#### outgoing_relations: 1.3 (최고 가중치)
**이유**: **서술적 풍부함**으로 RAGAS 점수 최고
- **nv_context_relevance: 0.50** (entity_properties 0.4625보다 높음)
- **faithfulness: 0.572** (entity_properties 0.478보다 16.4% 높음)

**컨텍스트 예시**:
```
✓ 좋은 예 (outgoing_relations):
"세조 즉위 → [Summary] → 수양대군이 단종을 몰아내고 스스로 세조로 즉위한 사건(계유정난과 연관)."
→ 주어 + 관계 + 서술적 설명 = 완전한 문장 구조

✗ 단편적 (entity_properties):
"세조의 ReignStart: 1455"
→ 키-값 쌍, 문맥 추론 필요
```

**장점**:
- 관계 + 설명이 결합되어 LLM이 관련성 판단 용이
- 문맥적 서술(narrative context)이 RAGAS 메트릭에서 선호됨

**단점**:
- 중복 정보가 많을 수 있음 (예: "수군통제사", "통제사", "삼도수군통제사" 등)
- → 0점 필터링으로 노이즈 제거 완료

#### entity_properties: 1.2 (두 번째)
**이유**: **정보의 다양성과 정확성**
- 단편적이지만 Year, Location, Title, Summary 등 **다양한 측면** 제공
- outgoing_relations의 중복 문제가 적음
- 정확한 사실 정보 (연도, 위치 등) 제공

**컨텍스트 예시**:
```
"세조의 ReignStart: 1455"
"세조의 ReignEnd: 1468"
"세조의 Title: 왕"
"세조의 Achievement: 일시적 규장각 설치(양성지의 건의로)"
→ 다양한 속성, 중복 없음
```

**장점**:
- 정보 다양성 우수
- 리터럴 값으로 정확도 높음

**단점**:
- 서술적 풍부함 부족 → RAGAS 점수 낮음
- 문맥 추론 필요

**가중치 결정**:
- 서술성은 낮지만 정확성과 다양성을 반영하여 **1.2**
- outgoing보다는 낮지만, 보조적 스레드들보다는 높게 설정

#### type_and_summary: 1.15
**이유**: **엔티티 개요 제공**으로 컨텍스트 이해 향상
- 엔티티 타입 + 요약 문장 제공
- entity_properties보다 서술적, outgoing보다는 간결

**예시**:
```
"[사건] 세조 즉위 (1455년): 수양대군이 단종을 폐위시키고 왕위에 오른 사건"
→ 타입 + 시간 + 요약이 결합된 구조
```

**가중치 결정**:
- entity_properties와 outgoing의 중간 특성
- 서술적 요약이 있어 **1.15**

#### incoming_relations: 1.1
**이유**: outgoing과 대칭적이지만 **질문 패턴상 활용도 낮음**
- "X는 누구인가?" → outgoing 정보가 더 유용
- "X로 인해 발생한 사건은?" → incoming이 필요
- 한국사 질문의 특성상 outgoing이 더 자주 활용됨

**가중치 결정**:
- outgoing보다 낮게 설정 (**1.1**)
- 하지만 관계 정보이므로 기본값(1.0)보다는 높게

#### connected_entities: 1.0 (기본 가중치)
**이유**: **2-hop 관계**로 보조적 역할
- 직접 관계가 아닌 간접 연결
- 노이즈 가능성이 높음
- 기본 가중치 유지

---

## 3. Entity Boost Mode

```python
"entity_boost_mode": "exact_match"
```

### 근거
- **exact_match**: 정확히 일치하는 엔티티에만 높은 relevance_score 부여
- 역사 데이터의 특성: 엔티티 이름이 명확하고 중의성이 낮음
- 예: "세조", "삼도수군통제사", "영릉" 등 고유 명사
- partial_match는 "세조실록", "세조 즉위" 등 파생 엔티티를 과도하게 포함할 위험

---

## 4. Evidence Selection

```python
"evidence_selection": {
    "top_k": 30,  # 상위 30개 근거 선택 (기본 15개에서 증가)
    "diversity_bonus": 0.1  # 다양한 스레드에서 온 근거에 보너스
}
```

### 근거

#### top_k: 30
**이유**: 모든 스레드 활성화 시 충분한 근거 필요
- 5개 스레드 × 평균 6개 = 30개
- 각 스레드의 대표적인 근거를 골고루 포함
- 너무 많으면 LLM 컨텍스트 창 압박, 너무 적으면 정보 부족

#### diversity_bonus: 0.1
**이유**: 스레드 다양성 장려
- 한 스레드에서만 근거가 집중되는 것을 방지
- 예: outgoing_relations만 20개 선택 → 다양성 부족
- 보너스로 각 스레드의 특징적인 정보가 고르게 포함되도록 유도

---

## 5. 가중치 적용 방식

### GraphState에 가중치 전달
```python
initial_state: GraphState = {
    "query": question,
    "thread_weights": {
        "outgoing_relations": 1.3,
        "incoming_relations": 1.1,
        "entity_properties": 1.2,
        "connected_entities": 1.0,
        "type_and_summary": 1.15
    },
    "test_config": {
        "semantic_expander": {"temporal": True, "category": True, ...},
        "aggregator_threads": {"outgoing_relations": True, ...},
        "entity_boost_mode": "exact_match",
        "custom_weights": OPTIMIZED_WEIGHTS
    }
}
```

### path_evidence_aggregator_node에서 활용
```python
# 각 스레드의 base_weight에 가중치 곱하기
base_weight = thread_weights.get(thread_type, 1.0)
relevance_score = calculate_improved_relevance_score(...)
final_weight = base_weight * relevance_score

# 최종 근거 정렬 시 weight 사용
top_evidences = sorted(all_paths, key=lambda x: x["weight"], reverse=True)[:top_k]
```

---

## 6. 예상 효과

### Before (단일 스레드 테스트)
- outgoing_relations 단독: **nv_context_relevance 0.50**
- entity_properties 단독: **nv_context_relevance 0.4625**

### After (통합 + 가중치)
**예상 점수**: **nv_context_relevance 0.55~0.60**

**근거**:
1. **시너지 효과**: 서술적 풍부함(outgoing) + 정확한 정보(entity_properties)
2. **다양성**: 5개 스레드가 서로 다른 측면 제공
3. **가중치 최적화**: 중요한 스레드에 더 높은 가중치
4. **노이즈 제거**: 0점 필터링으로 관련 없는 정보 제거

**기대 효과**:
- **Faithfulness**: 0.60+ (다양한 근거로 답변 신뢰도 향상)
- **Answer Relevancy**: 0.75+ (풍부한 컨텍스트로 답변 품질 향상)
- **nv_response_groundedness**: 0.95+ (근거 기반 답변)

---

## 7. 향후 개선 방향

### 7.1 동적 가중치 조정
현재는 고정 가중치이지만, 향후에는 질문 타입에 따라 동적 조정 가능:

```python
# 시간 관련 질문 → temporal 가중치 증가
if "언제" in question or "년도" in question:
    weights["temporal"] = 1.5

# 인과 관련 질문 → causal_chain 가중치 증가
if "왜" in question or "이유" in question:
    weights["causal_chain"] = 1.6
```

### 7.2 학습 기반 가중치
- RAGAS 점수 피드백을 통해 가중치 자동 튜닝
- Bayesian Optimization 또는 Reinforcement Learning 적용

### 7.3 페르소나별 가중치
- 외국인: temporal + category 높게 (기본 지식 부족)
- 아이들: entity_properties + type_and_summary 높게 (쉬운 설명 필요)

---

## 결론

이 가중치는 **데이터 기반 분석**과 **도메인 지식**을 결합하여 설정되었습니다:

1. **RAGAS 점수 분석**: outgoing_relations이 가장 높은 점수
2. **컨텍스트 품질 분석**: 서술적 풍부함이 핵심
3. **정보 다양성**: entity_properties의 강점 반영
4. **역사 도메인 특성**: 인과관계와 시간 정보의 중요성

이 가중치로 **통합 테스트**를 실행하면, 단일 스레드보다 **15-20% 향상된 RAGAS 점수**를 기대할 수 있습니다.
