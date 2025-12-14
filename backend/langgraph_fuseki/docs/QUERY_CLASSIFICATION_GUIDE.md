# Query Classification 가이드

## 🎯 질문 유형별 처리 차이점

Query Classifier가 분류한 결과(`causal`, `what_if`, `deep_analysis`)에 따라 **4가지 측면**에서 처리가 달라집니다.

---

## 📊 질문 유형별 차이 비교표

| 구분                      | `causal` (인과관계) | `what_if` (가상 시나리오)     | `deep_analysis` (심화 분석)   |
| ------------------------- | ------------------- | ----------------------------- | ----------------------------- |
| **1. 가상 Triple 생성**   | ❌ 없음             | ✅ **생성함**                 | ❌ 없음                       |
| **2. 병렬 실행 Thread**   | 5개 (기본)          | 5개 + **가상 데이터**         | **5개 (강화)**                |
| **3. Thread별 가중치**    | 균등 (20% 각)       | **인과관계 40%** + 나머지 15% | **동기분석 40%** + 나머지 15% |
| **4. SPARQL 쿼리 복잡도** | 기본 (1-2 hop)      | 기본 + 가상 조건              | **복잡 (3+ hop)**             |
| **5. Story 생성 스타일**  | 시간순 인과 설명    | "만약~했다면" 대체 역사       | "진짜 이유는" 심층 분석       |

---

## 🔍 세부 차이점

### **1. 가상 Triple 생성 여부**

#### **`causal` / `deep_analysis`**

```python
# 가상 Triple 생성하지 않음
hypothetical_triples = []
```

#### **`what_if`**

```python
# Hypothetical Triple Node 실행
hypothetical_triples = [
    "hist:Wongyun hist:wonBattle hist:GadeokdoSea .",
    "hist:GadeokdoSea hist:outcome 'victory' ."
]

# 모든 Thread에 가상 데이터 포함하여 추론
```

---

### **2. 병렬 실행 Thread 구성**

모든 유형에서 **5개 Thread를 병렬 실행**하지만, **가중치와 우선순위가 다름**

#### **`causal` (인과관계)**

```python
parallel_threads = {
    "causal": {
        "weight": 0.30,  # 30% - 가장 중요
        "sparql": "SELECT ?a ?b WHERE {?a hist:leadsTo ?b}",
        "rules": "causal_inference.rules"
    },
    "person": {
        "weight": 0.20,  # 20%
        "sparql": "SELECT ?p WHERE {?p hist:participatedIn ?event}",
        "rules": "person_relation.rules"
    },
    "temporal": {
        "weight": 0.20,  # 20%
        "sparql": "SELECT ?event ?year WHERE {?event hist:year ?year}",
        "rules": "temporal_context.rules"
    },
    "pattern": {
        "weight": 0.15,  # 15%
        "sparql": "SELECT ?e1 ?e2 WHERE {?e1 hist:similarPattern ?e2}",
        "rules": "pattern_detection.rules"
    },
    "motive": {
        "weight": 0.15,  # 15%
        "sparql": "SELECT ?person ?motive WHERE {?person hist:motivation ?motive}",
        "rules": "motive_analysis.rules"
    }
}

# 최종 근거 가중치 계산 시 causal 체인을 가장 우선
```

**결과 예시:**

```
근거 1: [인과관계 30%] 명량해전 → 수군보존 → 해상권장악
근거 2: [인물관계 20%] 이순신 리더십
근거 3: [시대배경 20%] 1597년 정유재란
근거 4: [패턴 15%] 한산도 vs 명량해전
근거 5: [동기 15%] 전략적 판단
```

---

#### **`what_if` (가상 시나리오)**

```python
parallel_threads = {
    "causal": {
        "weight": 0.40,  # 40% - 가상 시나리오의 핵심은 인과 변화
        "sparql": "SELECT ?a ?b WHERE {?a hist:leadsTo ?b}",
        "rules": "causal_inference.rules",
        "hypothetical": hypothetical_triples  # ✅ 가상 데이터 포함
    },
    "person": {
        "weight": 0.20,  # 20%
        "sparql": "SELECT ?p WHERE {?p hist:participatedIn ?event}",
        "rules": "person_relation.rules",
        "hypothetical": hypothetical_triples  # ✅ 가상 데이터 포함
    },
    "temporal": {
        "weight": 0.15,  # 15%
        "sparql": "SELECT ?event ?year WHERE {?event hist:year ?year}",
        "rules": "temporal_context.rules",
        "hypothetical": hypothetical_triples  # ✅ 가상 데이터 포함
    },
    "pattern": {
        "weight": 0.15,  # 15%
        "sparql": "SELECT ?e1 ?e2 WHERE {?e1 hist:similarPattern ?e2}",
        "rules": "pattern_detection.rules"
    },
    "comparison": {  # ✅ 실제 vs 가상 비교
        "weight": 0.10,  # 10%
        "sparql": "SELECT ?actual ?hypothetical WHERE {...}",
        "rules": "comparison.rules"
    }
}

# 가상 인과 체인에 가장 높은 가중치
```

**결과 예시:**

```
근거 1: [가상 인과 40%] 가덕도승리 → 일본약화 → 조기종료
근거 2: [인물변화 20%] 원균 통제사 유지, 이순신 복직 불필요
근거 3: [시대변화 15%] 1597년 전황 변화
근거 4: [비교분석 10%] 실제 vs 가상 비교
근거 5: [패턴 15%] 승리 패턴 분석
```

---

#### **`deep_analysis` (심화 분석)**

```python
parallel_threads = {
    "motive": {
        "weight": 0.35,  # 35% - 심화 분석의 핵심은 동기
        "sparql": """
            SELECT ?person ?motive ?action ?result WHERE {
                ?person hist:motivation ?motive .
                ?person hist:performedAction ?action .
                ?action hist:resultedIn ?result .
            }
        """,  # ✅ 복잡한 3-hop 쿼리
        "rules": "motive_analysis.rules"
    },
    "causal": {
        "weight": 0.25,  # 25%
        "sparql": "SELECT ?a ?b ?c WHERE {?a hist:leadsTo ?b . ?b hist:leadsTo ?c}",
        "rules": "causal_inference.rules"
    },
    "person": {
        "weight": 0.20,  # 20%
        "sparql": """
            SELECT ?p1 ?p2 ?relation WHERE {
                ?p1 ?relation ?p2 .
                FILTER(?relation IN (hist:betrayed, hist:allied, hist:opposed))
            }
        """,  # ✅ 복잡한 관계 분석
        "rules": "person_relation.rules"
    },
    "pattern": {
        "weight": 0.10,  # 10%
        "sparql": "SELECT ?pattern WHERE {?event hist:hasPattern ?pattern}",
        "rules": "pattern_detection.rules"
    },
    "temporal": {
        "weight": 0.10,  # 10%
        "sparql": "SELECT ?event ?context WHERE {?event hist:historicalContext ?context}",
        "rules": "temporal_context.rules"
    }
}

# 동기 분석에 가장 높은 가중치
```

**결과 예시:**

```
근거 1: [동기분석 35%] 독자세력화 욕심 + 후금 밀통
근거 2: [인과관계 25%] 약탈 → 조선불신 → 명나라통제불능 → 살해
근거 3: [인물관계 20%] 모문룡 vs 조선 vs 명나라
근거 4: [패턴 10%] 외국 장수 주둔의 반복 패턴
근거 5: [시대배경 10%] 1621-1629년 동아시아 정세
```

---

### **3. SPARQL 쿼리 복잡도**

#### **`causal` - 기본 쿼리 (1-2 hop)**

```sparql
PREFIX hist: <http://www.semanticweb.org/ontologies/korean-history#>

# 인과관계 (1-hop)
SELECT ?cause ?effect WHERE {
    ?cause hist:leadsTo ?effect .
}

# 간접 원인 (2-hop, 추론 결과)
SELECT ?root ?final WHERE {
    ?final hist:indirectlyCausedBy ?root .
}
```

---

#### **`what_if` - 가상 조건 포함 (2-hop + 비교)**

```sparql
PREFIX hist: <http://www.semanticweb.org/ontologies/korean-history#>

# 가상 인과관계
SELECT ?cause ?effect WHERE {
    ?cause hist:leadsTo ?effect .
    # 가상 Triple이 추론 결과에 반영됨
}

# 실제 vs 가상 비교
SELECT ?event ?actualOutcome ?hypotheticalOutcome WHERE {
    ?event hist:actualOutcome ?actualOutcome .
    ?event hist:hypotheticalOutcome ?hypotheticalOutcome .
}
```

---

#### **`deep_analysis` - 복잡한 쿼리 (3+ hop)**

```sparql
PREFIX hist: <http://www.semanticweb.org/ontologies/korean-history#>

# 동기 → 행동 → 결과 체인 (3-hop)
SELECT ?person ?motive ?action ?result WHERE {
    ?person hist:motivation ?motive .
    ?person hist:performedAction ?action .
    ?action hist:resultedIn ?result .

    # 추가 조건: 배신/동맹 관계
    OPTIONAL {
        ?person hist:betrayed ?victim .
    }
}

# 복잡한 인과 네트워크 (4-hop)
SELECT ?root ?intermediate1 ?intermediate2 ?final WHERE {
    ?root hist:leadsTo ?intermediate1 .
    ?intermediate1 hist:leadsTo ?intermediate2 .
    ?intermediate2 hist:leadsTo ?final .
}
```

---

### **4. Story Generator 스타일**

#### **`causal` - 시간순 인과 설명**

```python
story_prompt = f"""
질문: {query}
근거: {evidences}

시간 순서대로 인과관계를 설명하세요:
- "~로 인해", "~때문에" 표현 사용
- 각 단계의 영향 설명
- [근거 N] 번호로 출처 명시
"""
```

**생성 예시:**

```
명량해전은 조선 역사의 결정적 전환점이었습니다.

1597년 가덕도해전 패배로 조선 수군이 거의 전멸한 상황에서
[근거 3] 이순신이 12척으로 133척을 격파했습니다 [근거 1].

이 승리로 인해 [근거 1] 조선 수군이 보존되었고, 해상권을
장악하여 일본 보급로를 차단할 수 있었습니다.

📌 핵심: 명량해전은 수군 보존 → 해상권 장악 → 왜란 종료로
이어진 결정적 전환점이었습니다.
```

---

#### **`what_if` - "만약~했다면" 대체 역사**

```python
story_prompt = f"""
질문: {query}
실제 근거: {actual_evidences}
가상 근거: {hypothetical_evidences}

대체 역사 스토리를 작성하세요:
- "만약 ~했다면" 형식
- 실제 역사와 가상 시나리오 비교
- 차이점 강조
- [가상 근거 N], [실제 근거 N]으로 출처 구분
"""
```

**생성 예시:**

```
만약 원균이 가덕도해전에서 승리했다면, 조선의 역사는
크게 달라졌을 것입니다.

가덕도 승리로 [가상 근거 1] 일본 수군이 약화되어 명량해협까지
진격하지 못했을 것입니다. 실제 역사에서는 가덕도 패배 →
이순신 복직 → 명량 승리의 흐름이었지만 [실제 근거 3],
가상에서는 이 과정이 생략됩니다 [가상 근거 2].

역설적이게도 [가상 근거 4] 명량해전이라는 "12척으로 133척을
물리친" 기적이 없었다면, 이순신의 명성도 존재하지 않았을 것입니다.

📌 핵심: 원균의 승리는 전쟁을 조기 종료시켰겠지만,
역설적으로 명량해전이라는 역사적 순간은 탄생하지 못했을 것입니다.
```

---

#### **`deep_analysis` - "진짜 이유는" 심층 분석**

```python
story_prompt = f"""
질문: {query}
근거: {evidences}

심층 분석 스토리를 작성하세요:
- "진짜 이유는", "이면에는" 표현 사용
- 표면적 이유 vs 숨은 동기 구분
- 여러 근거를 종합하여 깊이 있는 분석
- 당시 상황과 맥락 설명
"""
```

**생성 예시:**

```
모문룡의 살해는 단순한 개인 비리가 아닌, 복잡한 국제 정세와
권력 욕심이 얽힌 필연적 결과였습니다.

표면적으로는 [근거 3] 전공 과장, 과도한 군량 요청이 명분이었지만,
진짜 이유는 [근거 1] 독자 세력 구축과 후금과의 밀통이었습니다.

더 깊은 배경을 보면 [근거 4] "외국 장수 주둔 → 협력 → 갈등 →
제거"라는 패턴이 반복되었으며, 모문룡도 이 패턴을 벗어나지
못했습니다.

결국 [근거 5] 명나라 원숭환의 정치적 결단으로 살해되었는데,
이는 조선-명 양국의 이중 부담을 해소하려는 [근거 2] 시도였습니다.

📌 핵심: 개인의 탐욕 + 독자세력화 + 조선-명 이중 부담이
결합된 필연적 결과이며, 역사적 패턴의 반복이었습니다.
```

---

## 💡 구현 코드 예시

### **병렬 실행 가중치 적용**

```python
def parallel_knowledge_retrieval_node(state: GraphState) -> GraphState:
    """질문 유형에 따라 다른 가중치로 병렬 실행"""

    query_type = state.get("query_type", "causal")

    # 질문 유형별 Thread 가중치
    if query_type == "causal":
        thread_weights = {
            "causal": 0.30,
            "person": 0.20,
            "temporal": 0.20,
            "pattern": 0.15,
            "motive": 0.15
        }
    elif query_type == "what_if":
        thread_weights = {
            "causal": 0.40,      # ✅ 가상 인과 중요
            "person": 0.20,
            "temporal": 0.15,
            "comparison": 0.15,  # ✅ 실제 vs 가상 비교
            "pattern": 0.10
        }
    else:  # deep_analysis
        thread_weights = {
            "motive": 0.35,      # ✅ 동기 분석 중요
            "causal": 0.25,
            "person": 0.20,
            "pattern": 0.10,
            "temporal": 0.10
        }

    # 병렬 실행 (모든 유형에서 5개 Thread)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                execute_inference_thread,
                thread_type=ttype,
                weight=weight,
                hypothetical=state.get("hypothetical_triples", [])
            ): ttype
            for ttype, weight in thread_weights.items()
        }

        results = {}
        for future in concurrent.futures.as_completed(futures):
            ttype = futures[future]
            results[ttype] = future.result()

    return {**state, "parallel_inference_results": results}
```

---

## 📊 최종 요약

| 측면              | `causal`       | `what_if`       | `deep_analysis` |
| ----------------- | -------------- | --------------- | --------------- |
| **가상 Triple**   | ❌             | ✅ 생성         | ❌              |
| **Thread 개수**   | 5개            | 5개             | 5개             |
| **최우선 Thread** | 인과관계 (30%) | 가상 인과 (40%) | 동기분석 (35%)  |
| **SPARQL 복잡도** | 1-2 hop        | 2 hop + 비교    | 3+ hop          |
| **스토리 스타일** | 시간순 인과    | 대체 역사       | 심층 분석       |

**핵심:** 모든 유형에서 **5개 Thread를 병렬 실행**하지만, **가중치와 우선순위**가 달라져서 **근거의 중요도**와 **최종 스토리 방향**이 바뀝니다.
