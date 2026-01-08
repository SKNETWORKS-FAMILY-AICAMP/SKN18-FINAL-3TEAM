# Stage 1 최적화 분석: 재질문에 필요한 최소 데이터

> **핵심 발견**: Stage 1.5는 Stage 1의 **일부 결과만** 필요하며, 나머지는 백그라운드에서 처리 가능

---

## 1. Stage 1.5가 실제로 사용하는 데이터

### user_intent_clarification_node.py 분석

```python
# user_intent_clarification_node.py에서 실제 사용하는 데이터
state.get("needs_clarification", False)      # ✅ 단순 boolean
state.get("clarification_question", "")       # ✅ 문자열
state.get("expansion_directions", [])         # ✅ 리스트
state.get("test_config")                      # ✅ 테스트 설정

# 사용자 선택 완료 후 저장
selected_direction["direction_id"]            # ✅ 문자열만 저장
```

### generate_clarification_question() 필요 데이터

```python
def generate_clarification_question(
    strategy: str,              # ✅ 문자열 (예: "time-based", "depth-based")
    directions: List[Dict],     # ✅ 방향 리스트만 필요
    query: str                  # ✅ 원본 질문
) -> str:
```

### generate_expansion_directions() 필요 데이터

```python
def generate_expansion_directions(
    query_type: str,            # ✅ "causal", "factual", etc.
    query: str,                 # ✅ 원본 질문
    keywords: List[str]         # ✅ 상위 5개 키워드만
) -> tuple[str, List[Dict]]:
```

---

## 2. Stage 1에서 생성되는 모든 데이터 (현재)

### classify_node.py 출력 전체

```python
# Thread 1: 의도 분석 (LLM 호출)
{
    "query_type": "causal",                    # ✅ 재질문에 필요
    "query_intent": "궁궐을 건설한 왕 찾기",  # ❌ 재질문에 불필요
    "selected_property_groups": ["건설", "설립", "통치"],  # ❌ 재질문에 불필요
}

# Thread 2: 키워드 확장 (LLM 호출)
{
    "expanded_keywords_dict": {                # ❌ 재질문에 불필요 (전체)
        "궁궐": ["경복궁", "창덕궁"],
        "왕": ["태조", "세종"]
    }
}

# 후처리 1: 프로퍼티 변환 (로컬 처리)
{
    "selected_properties": [                   # ❌ 재질문에 불필요
        "built", "builtBy", "constructed", ...
    ]
}

# 후처리 2: 키워드 리스트 변환 (로컬 처리)
{
    "expanded_keywords": [                     # ✅ 재질문에 필요 (상위 5개만)
        "경복궁", "창덕궁", "태조", "세종"
    ]
}

# 후처리 3: 방향 생성 (LLM 호출 또는 로컬)
{
    "classification_strategy": "time-based",   # ✅ 재질문에 필요
    "expansion_directions": [...]              # ✅ 재질문에 필요
}

# 메타 데이터
{
    "needs_clarification": True,               # ✅ 재질문에 필요
    "clarification_question": "..."            # ✅ 재질문에 필요
}
```

---

## 3. 핵심 발견: 재질문에 필요한 데이터는 최소한!

### ✅ 재질문(Stage 1.5)에 필요한 데이터

```python
{
    "query_type": "causal",                    # ✅ 필수
    "expanded_keywords": ["경복궁", "창덕궁", "태조", "세종"][:5],  # ✅ 상위 5개만
    "classification_strategy": "time-based",   # ✅ 필수
    "expansion_directions": [...],             # ✅ 필수
    "clarification_question": "...",           # ✅ 필수
    "needs_clarification": True                # ✅ 필수
}
```

### ❌ 재질문에 불필요하지만 현재 Stage 1에서 생성 중인 데이터

```python
{
    "query_intent": "궁궐을 건설한 왕 찾기",              # ❌ Stage 2 이후 사용
    "selected_property_groups": ["건설", "설립", "통치"],  # ❌ Stage 2 이후 사용
    "selected_properties": ["built", "builtBy", ...],     # ❌ Stage 4에서 사용
    "expanded_keywords_dict": {...}                       # ❌ Stage 2에서 사용
}
```

---

## 4. 최적화 방안: Stage 1 분할

### 방안 A: Stage 1을 두 단계로 분할 (권장)

#### Stage 1-A: 조기 응답 (재질문 준비)

```python
def query_classifier_early_response(state: GraphState) -> GraphState:
    """
    재질문에 필요한 최소 데이터만 생성 (조기 응답)

    처리 시간: ~1-2초 (LLM 1회만)
    """

    # 1. LLM 1회 호출: query_type 분류만
    query_type = classify_query_type_only(query)  # "causal", "factual", etc.

    # 2. 키워드 추출 (kiwipiepy, 빠름)
    keywords = extract_keywords_with_kiwi(query)[:5]

    # 3. 방향 생성 (로컬 또는 LLM, 선택)
    classification_strategy, expansion_directions = generate_expansion_directions(
        query_type=query_type,
        query=query,
        keywords=keywords
    )

    # 4. 질문 텍스트 생성 (로컬, 빠름)
    clarification_question = generate_clarification_question(
        strategy=classification_strategy,
        directions=expansion_directions,
        query=query
    )

    return {
        **state,
        "query_type": query_type,
        "classification_strategy": classification_strategy,
        "expansion_directions": expansion_directions,
        "clarification_question": clarification_question,
        "needs_clarification": True
    }
```

**처리 시간**:
- LLM 1회 호출 (query_type 분류): ~0.5-1초
- kiwipiepy 키워드 추출: ~0.01초
- 방향 생성: ~0.5초 (로컬) 또는 ~1초 (LLM)
- **총 처리 시간: 1-2초** (현재 2.5초 대비 40-60% 단축!)

#### Stage 1-B: 백그라운드 상세 분석

```python
def query_classifier_detailed_analysis(state: GraphState) -> GraphState:
    """
    Stage 2 이후에 필요한 상세 데이터 생성 (백그라운드)

    사용자가 선택하는 동안 백그라운드에서 실행
    """

    # 병렬 실행
    executor = ThreadPoolExecutor(max_workers=2)

    # Thread 1: 의도 분석 + 프로퍼티 그룹 선택
    def analyze_intent_and_properties():
        # LLM 호출
        result = {
            "query_intent": "...",
            "selected_property_groups": [...]
        }
        return result

    # Thread 2: 키워드 확장 (전체)
    def expand_keywords():
        # LLM 호출
        result = {
            "expanded_keywords_dict": {...}
        }
        return result

    future1 = executor.submit(analyze_intent_and_properties)
    future2 = executor.submit(expand_keywords)

    result1 = future1.result()
    result2 = future2.result()

    # 프로퍼티 변환
    selected_properties = convert_groups_to_properties(
        result1["selected_property_groups"]
    )

    executor.shutdown(wait=True)

    return {
        **state,
        "query_intent": result1["query_intent"],
        "selected_property_groups": result1["selected_property_groups"],
        "selected_properties": selected_properties,
        "expanded_keywords_dict": result2["expanded_keywords_dict"],
        "expanded_keywords": flatten_keywords(result2["expanded_keywords_dict"])
    }
```

---

### 방안 B: 더 공격적인 최적화 (query_type도 로컬 분류)

```python
def query_classifier_minimal(state: GraphState) -> GraphState:
    """
    LLM 없이 재질문 준비 (초고속)

    처리 시간: ~0.1-0.2초
    """

    # 1. 규칙 기반 query_type 분류 (LLM 없이)
    query_type = classify_query_type_by_rules(query)

    # 2. 키워드 추출 (kiwipiepy)
    keywords = extract_keywords_with_kiwi(query)[:5]

    # 3. 고정 매핑 방향 생성 (LLM 없이)
    classification_strategy, expansion_directions = generate_fixed_expansion_directions(
        query_type=query_type,
        keywords=keywords
    )

    # 4. 질문 텍스트 생성
    clarification_question = generate_clarification_question(
        strategy=classification_strategy,
        directions=expansion_directions,
        query=query
    )

    return {
        **state,
        "query_type": query_type,
        "classification_strategy": classification_strategy,
        "expansion_directions": expansion_directions,
        "clarification_question": clarification_question,
        "needs_clarification": True
    }
```

**규칙 기반 query_type 분류**:

```python
def classify_query_type_by_rules(query: str) -> str:
    """빠른 규칙 기반 분류"""

    # Factual 패턴
    if any(pattern in query for pattern in ["언제", "시기", "연도", "년도", "몇년"]):
        return "factual"

    # Causal 패턴
    elif any(pattern in query for pattern in ["왜", "이유", "원인", "때문", "배경"]):
        return "causal"

    # Comparative 패턴
    elif any(pattern in query for pattern in ["비교", "차이", "다른점", "같은점", "vs"]):
        return "comparative"

    # Deep analysis (기본값)
    else:
        return "deep_analysis"
```

**처리 시간**:
- 규칙 기반 분류: ~0.001초
- kiwipiepy 키워드 추출: ~0.01초
- 고정 매핑 방향 생성: ~0.1초
- **총 처리 시간: 0.1-0.2초** (현재 2.5초 대비 92% 단축!!)

---

## 5. 추천 구현 방안

### Phase 1: 규칙 기반 조기 응답 (즉시 적용 가능)

**목표**: Stage 1.5 진입을 2.5초 → 0.2초로 단축

**구현**:

```python
# classify_node.py 수정

def query_classifier_node(state: GraphState) -> GraphState:
    """
    개선된 Query Classifier: 조기 응답 + 백그라운드 상세 분석
    """

    # ========== Phase 1: 조기 응답 (재질문 준비) ==========
    # 규칙 기반 빠른 분류
    query_type = classify_query_type_by_rules(query)

    # 키워드 추출 (kiwipiepy)
    keywords = extract_keywords_with_kiwi(query)[:5]

    # 고정 매핑 방향 생성 (로컬)
    classification_strategy, expansion_directions = generate_fixed_expansion_directions(
        query_type=query_type,
        keywords=keywords
    )

    # 질문 텍스트 생성
    clarification_question = generate_clarification_question(
        strategy=classification_strategy,
        directions=expansion_directions,
        query=query
    )

    # ========== 조기 응답 데이터 반환 (Stage 1.5로 진행 가능) ==========
    state.update({
        "query_type_initial": query_type,  # 초기 예측 (백그라운드에서 정밀 분석)
        "classification_strategy": classification_strategy,
        "expansion_directions": expansion_directions,
        "clarification_question": clarification_question,
        "needs_clarification": True
    })

    # ========== Phase 2: 백그라운드 상세 분석 시작 ==========
    # 사용자가 선택하는 동안 백그라운드에서 실행
    background_data = start_detailed_analysis_background(state, query, keywords)
    state["background_detailed_analysis"] = background_data

    return state
```

### Phase 2: 백그라운드 상세 분석 통합

```python
# entity_expander_node.py 진입 시

def entity_expander_node(state: GraphState) -> GraphState:
    """
    Entity Expander: 백그라운드 분석 결과 통합 후 실행
    """

    # 백그라운드 상세 분석 완료 대기
    background_data = state.get("background_detailed_analysis")
    if background_data:
        detailed_results = wait_for_detailed_analysis(background_data, timeout=5.0)

        # 상세 분석 결과 통합
        state.update({
            "query_type": detailed_results.get("query_type", state["query_type_initial"]),
            "query_intent": detailed_results["query_intent"],
            "selected_property_groups": detailed_results["selected_property_groups"],
            "selected_properties": detailed_results["selected_properties"],
            "expanded_keywords_dict": detailed_results["expanded_keywords_dict"],
            "expanded_keywords": detailed_results["expanded_keywords"]
        })

    # 이제 Entity Expander 실행
    ...
```

---

## 6. 예상 성능 개선

### 시나리오: "임진왜란이 조선에 미친 영향은?"

#### 현재 (순차 실행)

```
Stage 1: Classify (LLM 2회 병렬 + 방향 생성)  : 2.5초
  - Thread 1 (의도 분석): 1.5초
  - Thread 2 (키워드 확장): 1.5초
  - 방향 생성: 0.5초 (병렬 후)

→ Stage 1.5 진입: 2.5초 후
→ 사용자 선택 대기: 10초

Stage 2: Entity Expander                      : 3.5초
```

#### 개선 후 (조기 응답 + 백그라운드)

```
Stage 1-A: 조기 응답 (재질문 준비)            : 0.2초 ✅
  - 규칙 기반 분류: 0.001초
  - 키워드 추출: 0.01초
  - 고정 매핑 방향 생성: 0.1초
  - 질문 텍스트 생성: 0.05초

→ Stage 1.5 진입: 0.2초 후 ✅ (2.3초 단축!)
→ 사용자 선택 대기: 10초

  백그라운드 실행 (사용자 선택 중):
  - Thread 1 (의도 분석): 1.5초
  - Thread 2 (키워드 확장): 1.5초
  - TTL 로드: 0.5초
  - 기본 엔티티 매칭: 1.0초
  → 10초 내 완료 ✅

Stage 2: Entity Expander (통합만)             : 1.0초 ✅
  - 백그라운드 결과 통합: 0.5초
  - SPARQL 스코어링만: 0.5초
```

**개선율**:
- Stage 1.5 진입 시간: 2.5초 → 0.2초 (**92% 단축**)
- 사용자 체감 시간: 2.5초 + 10초 + 3.5초 = 16초 → 0.2초 + 10초 + 1.0초 = 11.2초 (**30% 단축**)

---

## 7. 구현 우선순위

| 작업 | 난이도 | 효과 | 우선순위 |
|------|--------|------|----------|
| 1. 규칙 기반 `query_type` 분류 추가 | 낮음 | 높음 | **1순위** ⭐⭐⭐ |
| 2. 고정 매핑 `expansion_directions` 생성 | 낮음 | 높음 | **1순위** ⭐⭐⭐ |
| 3. `classify_node.py` 분할 (조기 응답 + 백그라운드) | 중간 | 높음 | **2순위** ⭐⭐ |
| 4. 백그라운드 분석 결과 통합 | 중간 | 중간 | 3순위 ⭐ |

---

## 8. 리스크 및 대응 방안

### 리스크 1: 규칙 기반 분류 정확도

**대응**:
- 백그라운드에서 LLM 기반 정밀 분류 실행
- 사용자 선택 완료 후 정밀 분류 결과 적용
- 규칙 분류가 틀려도 백그라운드에서 수정됨

### 리스크 2: 고정 매핑 방향이 부자연스러울 수 있음

**대응**:
- 초기에는 고정 매핑 사용 (빠른 응답)
- 향후 LLM 기반 동적 생성으로 점진적 개선
- A/B 테스트로 사용자 선호도 측정

### 리스크 3: 백그라운드 작업 실패 시 데이터 누락

**대응**:
- 백그라운드 실패 시 조기 응답 데이터로 폴백
- 필수 데이터는 조기 응답에 포함
- 상세 분석은 선택적(optional) 처리

---

## 9. 다음 단계

### 즉시 적용 가능 (Phase 1)

1. ✅ `classify_query_type_by_rules()` 함수 추가
2. ✅ `generate_fixed_expansion_directions()` 함수 추가
3. ✅ `query_classifier_node()` 수정 (조기 응답 로직)
4. ✅ 테스트 및 성능 측정

### 중기 계획 (Phase 2)

1. 백그라운드 상세 분석 인프라 구축
2. `entity_expander_node()` 백그라운드 결과 통합
3. 통합 테스트

---

**작성일**: 2025-12-25
**목적**: Stage 1 최적화를 통한 재질문 진입 시간 단축 (2.5초 → 0.2초)
**핵심**: Stage 1.5는 전체 Stage 1 결과가 **필요 없음** - 최소 데이터만으로 충분!
