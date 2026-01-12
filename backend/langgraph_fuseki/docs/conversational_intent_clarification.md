# 대화형 의도 확인 시스템 (Conversational Intent Clarification System)

## 📋 목차

1. [개요](#개요)
2. [문제 정의](#문제-정의)
3. [해결 방안](#해결-방안)
4. [하이브리드 분류 전략](#하이브리드-분류-전략)
5. [대화 흐름](#대화-흐름)
6. [구현 가이드](#구현-가이드)
7. [예시](#예시)

---

## 개요

### 목적
LLM이 키워드를 확장할 때 사용자가 원하지 않는 방향으로 확장되는 문제를 해결하기 위해, **사용자에게 확장 방향을 선택하게 하는 대화형 피드백 시스템**을 도입합니다.

### 핵심 아이디어
1. LLM이 질문을 분석하여 **가능한 확장 방향**을 제시
2. 사용자가 2-4개 옵션 중 원하는 방향을 선택
3. 선택된 방향으로 키워드 재확장 및 검색 진행
4. 질문 유형 분류도 사용자 피드백으로 확정

### 질문 유형 (Query Types)
- **causal**: 인과관계 중심 질문 (왜, 원인, 결과)
- **factual**: 사실 확인 질문 (누구, 언제, 어디서, 무엇)
- **deep_analysis**: 심층 분석 질문 (영향, 의미, 평가)
- **comparative**: 비교 분석 질문 (차이점, 공통점)

---

## 문제 정의

### 현재 문제점

**예시 질문**: "명성황후 시해사건으로 발발된 사건들은?"

**사용자 의도**: 을미사변 직후 발생한 사건들 (아관파천, 단발령 반대 운동 등)

**LLM의 잘못된 확장**:
- 시해사건의 **원인**까지 확장 → 청일전쟁, 갑오개혁
- 장기적 **영향**까지 확장 → 독립협회 설립, 러일전쟁
- 관련 **인물**까지 확장 → 이토 히로부미, 고종

**결과**: 사용자가 원하지 않는 정보까지 검색되어 **답변의 관련성(relevance)** 저하

### 근본 원인
1. LLM이 키워드 확장 방향을 **독단적**으로 결정
2. 사용자의 **구체적 의도**를 파악하지 못함
3. "발발된 사건들"이 **시간적 선후관계**인지, **인과관계**인지, **영향**인지 불분명

---

## 해결 방안

### 2단계 프로세스

#### 1단계: 확장 방향 제시 및 선택
```
LLM 분석 → 확장 방향 2-4개 제시 → 사용자 선택 → 방향 확정
```

#### 2단계: 질문 유형 확정
```
LLM 초기 분류 → 사용자 선택에 따라 재분류 → 최종 유형 확정
```

### 시스템 흐름

```
[Stage 1/6] Query Classification (Initial)
   ├─ LLM 분석: 질문 의도, 가능한 확장 방향 추론
   ├─ 분류 전략 선택 (Hybrid Strategy Selection)
   └─ 초기 질문 유형: query_type_initial

[Stage 1.5/6] User Intent Clarification (NEW)
   ├─ 확장 방향 2-4개 옵션 생성
   ├─ 사용자에게 질문 제시
   ├─ 사용자 선택 수신
   └─ 선택 방향 저장: user_selected_direction

[Stage 2/6] Entity Extraction (Refined)
   ├─ user_selected_direction 반영하여 키워드 재확장
   ├─ 질문 유형 재확정: query_type (final)
   └─ 이후 Stage 3-6 진행...
```

---

## 분류 전략 선택 방식

시스템이 질문에 대한 확장 방향을 제시하는 방식은 3가지가 있습니다.

### 방식 비교

| 방식 | 전략 선택 | 유연성 | 일관성 | 구현 복잡도 | 추천 단계 |
|------|----------|--------|--------|------------|----------|
| **고정 매핑** | 쿼리 타입 1:1 매핑 | 낮음 | 높음 | 낮음 | Phase 1 ⭐ |
| **Hybrid** | 기본 전략 + LLM 대안 | 중간 | 중간 | 중간 | Phase 2 |
| **자유 조합** | LLM 완전 자유 생성 | 높음 | 낮음 | 높음 | Phase 3 |

---

## 방식 1: 고정 매핑 (Fixed Mapping) ⭐ Phase 1

### 개요
쿼리 타입에 따라 **고정된 1:1 매핑**으로 분류 전략을 선택합니다.

### 전략 매핑 테이블

| 쿼리 타입 | 분류 전략 | 이유 |
|-----------|----------|------|
| `causal` | `time-based` | 인과관계는 시간 순서가 핵심 |
| `factual` | `class-based` | 사실 확인은 엔티티 클래스가 중요 |
| `deep_analysis` | `scope-based` | 심층 분석은 영향 범위가 핵심 |
| `comparative` | `depth-based` | 비교는 분석 깊이가 중요 |

### 동작 흐름

```
질문: "명성황후 시해사건으로 발발된 사건들은?"
   ↓
초기 분류: query_type = "causal"
   ↓
전략 선택: strategy = "time-based" (고정)
   ↓
방향 제시: [원인, 직후 사건, 장기 영향]  (모두 시간축 기준)
   ↓
사용자 선택: 2. 직후 사건
   ↓
최종 방향: time_direction = "forward", time_scope = "short_term"
```

### 장점
- ✅ 예측 가능하고 일관성 있음
- ✅ 디버깅 용이
- ✅ 빠른 응답 (LLM 추가 호출 불필요)
- ✅ 구현 간단

### 단점
- ❌ 유연성 부족
- ❌ 질문에 따라 다른 전략이 더 적합할 수 있음

### 사용 시나리오
- 프로토타입 개발
- 빠른 응답이 중요한 경우
- 일관성이 최우선인 경우

---

## 방식 2: Hybrid (기본 전략 + LLM 대안) - Phase 2

### 개요
**고정 매핑으로 기본 전략**을 선택하고, **LLM이 대안 전략**을 제안합니다.

### 동작 흐름

```
질문: "임진왜란이 조선에 미친 영향은?"
   ↓
초기 분류: query_type = "deep_analysis"
   ↓
기본 전략: strategy = "scope-based" (고정)
   ↓
LLM 분석: 대안 전략 제안
   - primary: "scope-based" (기본 전략 유지)
   - alternatives: ["time-based", "depth-based"]
   ↓
사용자에게 제시:
   A. 영향 범위별 (추천) ⭐
      1️⃣ 인적 피해
      2️⃣ 제도적 변화
      3️⃣ 경제/문화적 충격
      4️⃣ 국제 관계 변화

   B. 시간 순서별
      5️⃣ 전쟁 중 영향
      6️⃣ 전쟁 직후 영향
      7️⃣ 장기적 영향

   C. 분석 깊이별
      8️⃣ 기본 정보
      9️⃣ 인과 분석
      🔟 역사적 평가
   ↓
사용자 선택: 5. 전쟁 중 영향
   ↓
최종 전략 변경: "scope-based" → "time-based"
```

### 장점
- ✅ 기본적으로 일관성 유지
- ✅ 필요 시 유연하게 대안 제공
- ✅ 사용자에게 더 많은 선택권
- ✅ 고정 매핑의 안정성 + LLM의 유연성

### 단점
- ❌ LLM 호출 1회 추가 (응답 시간 증가)
- ❌ 구현 복잡도 증가
- ❌ 대안 전략 품질이 LLM 성능에 의존

### 사용 시나리오
- Phase 1 테스트 완료 후
- 사용자 피드백이 "선택지가 부족하다"는 경우
- 복잡한 질문이 자주 발생하는 경우

---

## 방식 3: 자유 조합 (LLM-Driven Free Composition) - Phase 3

### 개요
전략을 미리 고정하지 않고, **LLM이 질문을 분석하여 자유롭게 2-4가지 방향을 생성**합니다.
각 방향마다 **서로 다른 분류 전략 조합**을 사용할 수 있습니다.

### 동작 흐름

```
질문: "명성황후 시해사건으로 발발된 사건들은?"
   ↓
초기 분류: query_type = "causal"
   ↓
LLM 자유 분석: 전략 선택 없이 방향 생성
   ↓
LLM 생성 결과:
   [
      {
         "direction": "직접 원인 (왜 죽였나?)",
         "classification": "causal + before",      ← time-based 전략
         "keywords": ["청일전쟁", "일본 세력 확대", ...],
         "property_groups": ["인과관계", "외교", "통치"]
      },
      {
         "direction": "직후 사건 (그 다음 무슨 일이?)",
         "classification": "consequence + Event",  ← class-based 전략
         "keywords": ["을미사변", "아관파천", ...],
         "property_groups": ["인과관계", "사건", "연도"]
      },
      {
         "direction": "장기 영향 (조선에 어떤 영향?)",
         "classification": "consequence + national", ← scope-based 전략
         "keywords": ["을사조약", "한일병합", ...],
         "property_groups": ["외교", "통치", "조약"]
      },
      {
         "direction": "관련 인물 (누가 관여했나?)",
         "classification": "relational + Person",  ← class-based 전략
         "keywords": ["이범진", "고종", "미우라 고로", ...],
         "property_groups": ["참여", "인물", "직위"]
      }
   ]
   ↓
사용자에게 제시: (위 4가지 방향)
   ↓
사용자 선택: 2. 직후 사건 (그 다음 무슨 일이?)
   ↓
최종 분류 확정:
   - classification: "consequence + Event"
   - strategy_type: "class-based" (자동 추론)
   - target_class: "Event"
   - temporal_filter: "after 1895"
```

### Classification 조합 예시

LLM이 자유롭게 조합할 수 있는 분류 요소:

#### 시간 차원
- `before`, `after`, `contemporary`
- `short-term`, `long-term`

#### 클래스 차원
- `Person`, `Event`, `Institution`, `Policy`, `Document`, `Culture`

#### 범위 차원
- `individual`, `institutional`, `national`, `international`

#### 깊이 차원
- `basic`, `relational`, `causal`, `evaluative`

#### 관계 차원
- `causal`, `consequence`, `relational`, `comparative`

### 조합 예시

| Classification | 의미 | 전략 유형 |
|----------------|------|----------|
| `causal + before` | 인과관계의 원인 (이전 사건) | time-based |
| `consequence + Event` | 결과로 발생한 사건들 | class-based |
| `consequence + national` | 국가적 영향 | scope-based |
| `relational + Person` | 관련 인물들 | class-based |
| `comparative + depth` | 깊이별 비교 | depth-based |

### 장점
- ✅ 최고의 유연성
- ✅ 사용자 관점에서 가장 직관적인 선택지
- ✅ 질문마다 최적화된 방향 제시
- ✅ 전략 제약 없이 자유로운 조합

### 단점
- ❌ LLM 의존도 높음 (품질이 LLM 성능에 좌우)
- ❌ 일관성 부족 (같은 질문이라도 매번 다른 결과 가능)
- ❌ 검증 어려움 (방향들이 정말 상호 배타적인지 확인 어려움)
- ❌ 구현 복잡도 최고
- ❌ 각 방향마다 다른 로직 실행 → 디버깅 어려움

### 사용 시나리오
- Phase 2 테스트 완료 후
- 사용자 피드백이 "더 다양한 관점이 필요하다"는 경우
- 복잡한 질문 유형이 많은 도메인
- LLM 성능이 충분히 검증된 후

---

## 하이브리드 분류 전략 (Phase 1 기준)

### 전략 개요
질문 유형에 따라 **가장 적합한 분류 기준**을 선택하는 방식입니다.

**중요**: Phase 1에서는 **질문당 1개의 고정된 전략**을 선택합니다.

### 전략 1: 시간축 기반 (Time-based)
**적용 대상**: `causal` 질문

**분류 기준**:
- **원인/이전 사건** (cause/before): 해당 사건 이전의 원인, 배경
- **직후 사건** (immediate consequence): 사건 직후 발생한 즉각적 결과
- **장기 영향** (long-term impact): 수년~수십년 후의 간접적 영향

**property_groups.json 활용**:
- `"인과관계"` 그룹: `caused`, `causes`, `hasMotive`, `hasPurpose`, `leadsTo`, `ledTo`
- `"시기"` 그룹: `began`, `period`, `usedSince`
- `"연도"` 그룹: `hasStartYear`, `hasEndYear`, `occurredInYear`

**예시 질문**:
- "명성황후 시해사건으로 발발된 사건들은?"
- "임진왜란의 원인은 무엇인가요?"
- "세종의 한글 창제가 미친 영향은?"

---

### 전략 2: 온톨로지 클래스 기반 (Class-based)
**적용 대상**: `factual` 질문

**분류 기준** (온톨로지 상위 클래스):
- **인물** (Person): 왕, 신하, 학자, 군인
- **사건** (Event): 전쟁, 개혁, 반란, 외교
- **제도** (Institution): 관직, 법률, 기구, 교육
- **문화/문서** (Culture/Document): 서적, 유물, 풍속

**property_groups.json 활용**:
- `"직위"` 그룹: `hasTitle`, `heldOffice`, `hasRank`
- `"문서"` 그룹: `documents`, `documentsEvent`, `hasSummary`
- `"설립"` 그룹: `establishedBy`, `founded`, `reformed`

**예시 질문**:
- "세조는 누구였나요?"
- "삼도수군통제사의 역할은 무엇이었나요?"
- "조선왕조실록이란 무엇인가요?"

---

### 전략 3: 분석 깊이 기반 (Depth-based)
**적용 대상**: `deep_analysis`, `comparative` 질문

**분류 기준**:
- **기본 정보** (basic): 정의, 개요, 기본 사실
- **관계형 정보** (relational): 관련 인물/사건/제도
- **인과형 정보** (causal): 원인, 결과, 영향
- **평가형 정보** (evaluative): 의의, 한계, 평가

**property_groups.json 활용**:
- `"속성"` 그룹: 기본 정보
- `"연결관계"` 그룹: 관계형 정보
- `"인과관계"` 그룹: 인과형 정보
- `"문서"` 그룹 중 `hasSummary`, `hasNote`: 평가형 정보

**예시 질문**:
- "임진왜란이 조선에 미친 영향은?"
- "갑신정변과 갑오개혁의 차이는?"

---

### 전략 4: 영향 범위 기반 (Scope-based)
**적용 대상**: `deep_analysis` 질문 (특히 영향/의미 분석)

**분류 기준**:
- **개인적** (individual): 특정 인물에 미친 영향
- **제도적** (institutional): 관직, 법률, 기구 변화
- **국가적** (national): 국내 정치/경제/사회 변화
- **국제적** (international): 외교, 주변국 관계

**property_groups.json 활용**:
- `"참여"` 그룹: 개인적 영향
- `"변경"` 그룹: 제도적 영향
- `"외교"` 그룹: 국제적 영향

**예시 질문**:
- "임진왜란이 조선에 미친 영향은?"
- "갑오개혁의 의미는 무엇인가요?"

---

## 대화 흐름

### 공통 템플릿

```
시스템:
"[질문 주제]"는 여러 방향으로 답변할 수 있어요.

어떤 [부분/측면/관점]이 더 궁금하신가요?

1️⃣ [방향 1 제목] ([부가 설명])
   → [구체적 예시 키워드들]

2️⃣ [방향 2 제목] ([부가 설명])
   → [구체적 예시 키워드들]

3️⃣ [방향 3 제목] ([부가 설명])
   → [구체적 예시 키워드들]

번호로 선택해주세요 (1, 2, 3)
```

### 옵션 설계 원칙

1. **2-4개 옵션**: 너무 많으면 혼란, 너무 적으면 제약
2. **상호 배타적**: 옵션 간 명확한 구분
3. **구체적 예시 제시**: 키워드 미리보기로 방향 이해 도움
4. **부가 설명**: 각 옵션이 무엇을 의미하는지 1줄 설명

---

## 구현 가이드

### 1. GraphState 수정 (state.py)

```python
class GraphState(TypedDict):
    # ... 기존 필드들 ...

    # 대화형 의도 확인 필드 (NEW)
    needs_clarification: bool  # 의도 확인 필요 여부
    expansion_directions: List[Dict[str, Any]]  # LLM이 제시하는 확장 방향 옵션
    user_selected_direction: Optional[str]  # 사용자가 선택한 방향 (예: "immediate_consequence")
    clarification_question: Optional[str]  # 사용자에게 보여줄 질문 텍스트
    query_type_initial: Optional[str]  # LLM의 초기 질문 유형 예측
    # query_type: str  # 이미 존재, 사용자 피드백 반영한 최종 유형
```

### 2. Query Classification 수정 (classify_node.py)

**기존**: LLM이 질문 유형을 바로 결정
**변경 후**: LLM이 초기 예측 + 확장 방향 옵션 생성

```python
def query_classifier_node(state: GraphState) -> GraphState:
    """
    Stage 1/6: Query Classification (Initial)
    - LLM이 질문을 분석하여 초기 유형 예측
    - 가능한 확장 방향 2-4개 생성
    - needs_clarification = True 설정
    """
    query = state["query"]

    # LLM 분석 프롬프트
    prompt = f"""
질문: "{query}"

1. 이 질문의 유형을 예측하세요 (causal/factual/deep_analysis/comparative)
2. 이 질문에 적합한 분류 전략을 선택하세요 (time-based/class-based/depth-based/scope-based)
3. 선택한 전략에 따라 2-4개의 확장 방향을 제시하세요.

각 방향은 다음 형식으로:
- direction_id: 방향 식별자 (예: "immediate_consequence")
- title: 방향 제목 (예: "직후 사건")
- description: 1줄 설명
- example_keywords: 예시 키워드 리스트 (최대 5개)
"""

    response = llm.invoke(prompt)

    return {
        **state,
        "query_type_initial": response["query_type"],
        "expansion_directions": response["directions"],
        "needs_clarification": True,
        "clarification_question": generate_clarification_question(response["directions"])
    }
```

### 3. 새 노드: User Intent Clarification (NEW)

```python
def user_intent_clarification_node(state: GraphState) -> GraphState:
    """
    Stage 1.5/6: User Intent Clarification (NEW)
    - 사용자에게 확장 방향 질문 제시
    - 사용자 응답 대기 (1, 2, 3, 4)
    - 선택된 방향 저장
    """
    if not state.get("needs_clarification", False):
        # 의도 확인 필요 없으면 스킵
        return state

    # 질문 출력
    print(f"\n{'='*70}")
    print(f"[Stage 1.5/6] 사용자 의도 확인 (User Intent Clarification)")
    print(f"{'='*70}")
    print(state["clarification_question"])

    # 사용자 입력 대기
    user_choice = input("\n선택 (번호 입력): ").strip()

    # 선택 검증
    try:
        choice_idx = int(user_choice) - 1
        selected_direction = state["expansion_directions"][choice_idx]
    except (ValueError, IndexError):
        print("❌ 잘못된 선택입니다. 기본값(1번)으로 진행합니다.")
        selected_direction = state["expansion_directions"][0]

    print(f"\n✅ 선택됨: {selected_direction['title']}")

    return {
        **state,
        "user_selected_direction": selected_direction["direction_id"],
        "needs_clarification": False
    }
```

### 4. Entity Extraction 수정 (entity_expander_node.py)

**기존**: 질문에서 바로 키워드 추출
**변경 후**: `user_selected_direction` 반영하여 재확장

```python
def entity_expander_node(state: GraphState) -> GraphState:
    """
    Stage 2/6: Entity Extraction (Refined)
    - user_selected_direction을 반영하여 키워드 재확장
    - 질문 유형 최종 확정 (query_type)
    """
    query = state["query"]
    selected_direction = state.get("user_selected_direction")

    # 방향 반영한 프롬프트
    if selected_direction:
        prompt = f"""
질문: "{query}"
사용자가 선택한 방향: {selected_direction}

이 방향에 맞게 질문에서 핵심 키워드를 추출하세요.
예를 들어:
- "immediate_consequence" → 사건 직후 발생한 엔티티만
- "cause" → 사건 이전의 원인 엔티티만
- "long_term_impact" → 수년 후 영향받은 엔티티만
"""
    else:
        # 기존 로직 (방향 없이 추출)
        prompt = f"질문: '{query}'\n핵심 키워드를 추출하세요."

    # ... 키워드 추출 로직 ...

    # 질문 유형 최종 확정
    final_query_type = determine_final_query_type(
        state["query_type_initial"],
        selected_direction
    )

    return {
        **state,
        "query_type": final_query_type,
        "query_entities": extracted_entities,
        # ...
    }
```

### 5. 그래프 플로우 수정 (graph.py)

```python
def create_graph_flow():
    workflow = StateGraph(GraphState)

    # 노드 등록
    workflow.add_node("history_check", history_check_node)
    workflow.add_node("query_classifier", query_classifier_node)
    workflow.add_node("user_intent_clarification", user_intent_clarification_node)  # NEW
    workflow.add_node("entity_expander", entity_expander_node)
    # ... 나머지 노드들 ...

    # 플로우 정의
    workflow.set_entry_point("history_check")
    workflow.add_edge("history_check", "query_classifier")
    workflow.add_edge("query_classifier", "user_intent_clarification")  # NEW
    workflow.add_edge("user_intent_clarification", "entity_expander")  # NEW
    workflow.add_edge("entity_expander", "semantic_expander")
    # ... 나머지 엣지들 ...

    return workflow.compile()
```

---

## 예시

### 예시 1: 시간축 기반 (Time-based)

**질문**: "명성황후 시해사건으로 발발된 사건들은?"

**LLM 분석**:
- 초기 유형: `causal`
- 선택 전략: `time-based`

**시스템 질문**:
```
"명성황후 시해사건으로 발발된 사건들"은 여러 시간 관점에서 답변할 수 있어요.

어떤 시기의 사건들이 더 궁금하신가요?

1️⃣ 시해사건의 원인 (사건 이전에 발생한 배경)
   → [청일전쟁, 갑오개혁, 민비파와 대원군파 대립, 일본의 조선 장악]

2️⃣ 직후 발생한 사건들 (시해사건 직후 몇 개월 내)
   → [을미사변, 아관파천, 단발령 반대 운동, 의병 봉기]

3️⃣ 장기적 영향 (수년 후 파급 효과)
   → [독립협회 설립, 러일전쟁, 을사늑약, 항일운동]

번호로 선택해주세요 (1, 2, 3)
```

**사용자 선택**: `2`

**결과**:
- `user_selected_direction = "immediate_consequence"`
- `query_type = "causal"`
- Entity Extraction: [을미사변, 아관파천, 단발령, 의병] 중심으로 확장

---

### 예시 2: 온톨로지 클래스 기반 (Class-based)

**질문**: "세종의 업적은?"

**LLM 분석**:
- 초기 유형: `factual`
- 선택 전략: `class-based`

**시스템 질문**:
```
"세종의 업적"은 여러 분야로 나눌 수 있어요.

어떤 분야의 업적이 더 궁금하신가요?

1️⃣ 문화·과학 업적
   → [한글 창제, 측우기, 해시계, 칠정산, 집현전]

2️⃣ 정치·군사 업적
   → [4군6진 개척, 의정부 서사제, 왜구 토벌, 집현전 설치]

3️⃣ 민생·복지 업적
   → [공법 실시, 호패법, 진휼 정책, 농사직설 편찬]

번호로 선택해주세요 (1, 2, 3)
```

**사용자 선택**: `1`

**결과**:
- `user_selected_direction = "culture_science"`
- `query_type = "factual"`
- Property Groups 우선: `["문서", "저술", "속성"]` (문화/과학 관련)

---

### 예시 3: 영향 범위 기반 (Scope-based)

**질문**: "임진왜란이 조선에 미친 영향은?"

**LLM 분석**:
- 초기 유형: `deep_analysis`
- 선택 전략: `scope-based`

**시스템 질문**:
```
"임진왜란의 영향"은 여러 범위로 분석할 수 있어요.

어떤 범위의 영향이 더 궁금하신가요?

1️⃣ 인적 피해 (사상자, 인구 감소, 노비 문제)
   → [사상자 수, 인구 감소, 노비 문서 소실, 신분제 동요]

2️⃣ 제도적 변화 (정치·군사 제도 개혁)
   → [훈련도감 설치, 비변사 강화, 속오군 편성, 광해군 중립외교]

3️⃣ 경제·문화적 충격 (토지, 세금, 문화재)
   → [토지 황폐화, 조세 수입 감소, 경복궁 소실, 문화재 약탈]

4️⃣ 국제 관계 변화 (명·청 교체, 일본)
   → [명나라 쇠퇴, 후금(청) 부상, 정묘·병자호란 배경, 조일 국교 단절]

번호로 선택해주세요 (1, 2, 3, 4)
```

**사용자 선택**: `2`

**결과**:
- `user_selected_direction = "institutional_change"`
- `query_type = "deep_analysis"`
- Property Groups 우선: `["설립", "변경", "지휘", "직위"]`

---

### 예시 4: 분석 깊이 기반 (Depth-based)

**질문**: "갑신정변과 갑오개혁의 차이는?"

**LLM 분석**:
- 초기 유형: `comparative`
- 선택 전략: `depth-based`

**시스템 질문**:
```
"갑신정변과 갑오개혁의 차이"는 여러 깊이로 비교할 수 있어요.

어떤 측면을 중심으로 비교하고 싶으신가요?

1️⃣ 기본 정보 비교 (시기, 주도 세력, 개요)
   → [발생 연도, 주도 인물, 배경, 간단한 개요]

2️⃣ 개혁 내용 비교 (구체적 개혁안, 정강)
   → [갑신정변 14개조, 갑오개혁 홍범14조, 세부 개혁 항목]

3️⃣ 성공/실패 원인 비교 (왜 실패/성공했나)
   → [외세 개입, 내부 반발, 추진 방식, 청일전쟁 영향]

번호로 선택해주세요 (1, 2, 3)
```

**사용자 선택**: `3`

**결과**:
- `user_selected_direction = "success_failure_analysis"`
- `query_type = "comparative"`
- Property Groups 우선: `["인과관계", "반대", "외교", "법률"]`

---

## 구현 로드맵

### Phase 1: 고정 매핑 방식 (현재 단계)

**목표**: 프로토타입 완성 및 기본 기능 검증

**구현 범위**:
- GraphState에 대화형 필드 추가
- Query Classification에서 고정 매핑으로 전략 선택
- User Intent Clarification 노드 추가 (사용자 선택 처리)
- Entity Extraction에서 선택 방향 반영
- 4가지 전략별 방향 생성 템플릿 작성

**검증 방법**:
- 각 쿼리 타입별로 3-5개 테스트 질문 실행
- 사용자 선택이 Entity Extraction에 올바르게 반영되는지 확인
- RAGAS 평가로 베이스라인 점수 측정

---

### Phase 2: Hybrid 방식

**전제 조건**: Phase 1 완료 및 베이스라인 RAGAS 점수 확보

**구현 범위**:
- LLM 대안 전략 제안 로직 추가
- 복수 전략 옵션 UI 개선 (A, B, C 그룹)
- 전략 변경 시 필터링 로직 동적 조정

**검증 방법**:
- Phase 1 대비 RAGAS 점수 비교
- 사용자 선택 분포 분석 (어떤 대안이 많이 선택되는지)
- 일관성 테스트 (같은 질문 10회 반복)

---

### Phase 3: 자유 조합 방식

**전제 조건**: Phase 2 완료 및 LLM 성능 검증

**구현 범위**:
- LLM 자유 방향 생성 프롬프트 작성
- Classification 자동 파싱 및 전략 추론 로직
- 각 방향별 독립적인 필터링 로직 실행

**검증 방법**:
- Phase 2 대비 RAGAS 점수 비교
- LLM 생성 방향의 품질 검증 (상호 배타성, 관련성)
- 에러 핸들링 테스트 (LLM이 이상한 조합 생성 시)

---

## 요약

### 핵심 변경 사항
1. ✅ **대화형 피드백 루프 추가**: Stage 1.5/6에서 사용자 의도 확인
2. ✅ **2단계 질문 유형 분류**: `query_type_initial` (예측) → `query_type` (확정)
3. ✅ **3가지 전략 선택 방식**: 고정 매핑 (Phase 1) → Hybrid (Phase 2) → 자유 조합 (Phase 3)
4. ✅ **키워드 재확장**: 사용자 선택 방향 반영

### 기대 효과
- **RAGAS nv_context_relevance 향상**: 불필요한 컨텍스트 제거
- **RAGAS answer_relevancy 향상**: 사용자 의도에 맞는 답변 생성
- **사용자 만족도 향상**: 원하는 정보만 얻음

### 현재 구현 단계
**Phase 1: 고정 매핑 방식** (진행 중)

다음 단계: GraphState 수정 및 기본 대화 흐름 구현
