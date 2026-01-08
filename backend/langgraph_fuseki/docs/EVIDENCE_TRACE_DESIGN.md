# Evidence 확장 근거 추적 기능 설계

## 1. 목표

프론트엔드에서 그래프 DB UI 형식으로 Evidence의 확장 경로를 시각화

```
예시: "조선 궁궐 건축한 왕이 누구야?"

[질문] → [키워드: 궁궐, 건축, 왕]
              ↓
    [Entity: 경복궁] ─── hasBuilder ───→ [Entity: 태조]
              │                              │
              ├── type_and_summary           ├── entity_properties
              │   └── "조선의 정궁"              └── "재위: 1392-1398"
              │
              └── outgoing_relations
                  └── builtBy → 태조 이성계
```

---

## 2. 현재 저장되는 정보

### ✅ 이미 있는 것

| 정보 | 위치 | 예시 |
|------|------|------|
| Entity 이름 | `extracted_entities[].name` | "훈민정음" |
| Entity 타입 | `extracted_entities[].type` | "Document" |
| 매칭 방식 | `extracted_entities[].match_method` | "exact", "partial" |
| 매칭 키워드 | `extracted_entities[].matched_keyword` | "훈민정음" |
| 확장 방식 | `extracted_entities[].expansion_method` | "temporal", "causal_chain" |
| 확장 출처 | `extracted_entities[].expansion_source` | "훈민정음 창제" |
| Thread 타입 | `evidences[].type` | "entity_properties" |
| Predicate | `evidences[].raw_data.predicate` | "hasCreationYear" |
| Value | `evidences[].raw_data.value` | "1443" |

### ❌ 없는 것

| 정보 | 필요 이유 |
|------|----------|
| Kiwi 초기 추출 단어 | 시작점 표시 |
| Evidence → Entity 연결 | 역추적 |
| 확장 경로 체인 | A → B → C 시각화 |

---

## 3. 설계 옵션

### Option A: 모든 Evidence에 경로 저장

```python
evidence = {
    "type": "entity_properties",
    "description": "훈민정음의 CreationYear: 1443",
    # 기존 필드...
    
    # 새로 추가
    "trace": {
        "kiwi_keywords": ["훈민정음", "창제", "시기"],
        "source_entity": {
            "name": "훈민정음",
            "type": "Document",
            "uri": "hist:Document_6f5a09a0"
        },
        "expansion_path": [
            # 확장이 있으면 체인 표시
            # {"from": "훈민정음 창제", "to": "세종", "method": "causal_chain"}
        ],
        "thread": "entity_properties",
        "predicate": "hasCreationYear",
        "edge_label": "CreationYear"
    }
}
```

**장점**: 
- 프론트엔드에서 바로 사용 가능
- 딜레이 없음

**단점**:
- 메모리 증가 (~20% 예상)
- 모든 Evidence에 중복 정보

---

### Option B: Entity 기준으로 저장 + Evidence에 참조만

```python
# Entity에 상세 경로 저장
entity = {
    "name": "훈민정음",
    "trace": {
        "kiwi_keywords": ["훈민정음"],
        "match_method": "exact",
        "expansion_chain": []  # 확장 없으면 빈 배열
    }
}

# Evidence에는 참조만
evidence = {
    "type": "entity_properties",
    "source_entity_name": "훈민정음",  # 참조
    "thread": "entity_properties",
    "predicate": "hasCreationYear"
}
```

**장점**:
- 메모리 효율적
- Entity 중심 관리

**단점**:
- 프론트에서 조인 필요

---

### Option C: 요청 시 경로 계산 (지연 로딩)

```python
# 기본 응답
response = {
    "answer": "...",
    "evidences": [...]  # 기존대로
}

# 사용자가 "근거 보기" 클릭 시 별도 API 호출
GET /api/evidence/{evidence_id}/trace

# 응답
{
    "kiwi_keywords": ["훈민정음", "창제"],
    "expansion_path": [...],
    "graph_data": {
        "nodes": [...],
        "edges": [...]
    }
}
```

**장점**:
- 초기 응답 빠름
- 필요할 때만 계산

**단점**:
- UX 딜레이 (클릭 후 로딩)
- 추가 API 구현 필요

---

## 4. 권장: Option A (모든 Evidence에 경로 저장)

### 이유

1. **UX 최우선**: 사용자가 바로 경로 확인 가능
2. **메모리 증가 미미**: Evidence 15개 × 경로 정보 ~1KB = ~15KB 추가
3. **구현 단순**: 기존 파이프라인에 필드 추가만

### 구현 방안

```python
# 1. Kiwi 추출 단계에서 저장
def extract_keywords(query):
    keywords = kiwi.analyze(query)
    state["kiwi_keywords"] = keywords  # 저장
    return keywords

# 2. Entity 추출 시 trace 정보 추가
def extract_entities(state):
    for entity in entities:
        entity["trace"] = {
            "matched_keyword": find_matched_keyword(entity, state["kiwi_keywords"]),
            "match_method": entity["match_method"]
        }

# 3. Semantic 확장 시 경로 기록
def expand_entities(state):
    for expanded in expanded_entities:
        expanded["trace"] = {
            "expansion_method": method,
            "expansion_source": source_entity["name"],
            "expansion_reason": "causal_chain: caused_by relation"
        }

# 4. Evidence 생성 시 trace 통합
def create_evidence(entity, thread_result):
    return {
        "type": thread_result["type"],
        "description": thread_result["description"],
        # ... 기존 필드
        
        "trace": {
            "kiwi_keywords": state["kiwi_keywords"],
            "source_entity": {
                "name": entity["name"],
                "type": entity["type"],
                "uri": entity["uri"]
            },
            "expansion_path": entity.get("trace", {}).get("expansion_chain", []),
            "thread": thread_result["type"],
            "predicate": thread_result.get("predicate"),
            "edge_label": thread_result.get("predicate_display")
        }
    }
```

---

## 5. 프론트엔드 데이터 구조

```json
{
  "answer": "경복궁은 태조 이성계가 1395년에 건축했습니다.",
  "evidences": [
    {
      "rank": 1,
      "description": "경복궁의 Builder: 태조",
      "contribution": "기여함",
      "trace": {
        "kiwi_keywords": ["궁궐", "건축", "왕"],
        "source_entity": {
          "name": "경복궁",
          "type": "Building",
          "uri": "hist:Building_xxx"
        },
        "expansion_path": [],
        "thread": "entity_properties",
        "predicate": "hasBuilder",
        "edge_label": "Builder"
      }
    },
    {
      "rank": 2,
      "description": "태조의 Achievement: 조선 건국",
      "contribution": "간접 기여",
      "trace": {
        "kiwi_keywords": ["궁궐", "건축", "왕"],
        "source_entity": {
          "name": "태조",
          "type": "Person",
          "uri": "hist:Person_xxx"
        },
        "expansion_path": [
          {
            "from": "경복궁",
            "to": "태조",
            "method": "outgoing_relations",
            "edge": "hasBuilder"
          }
        ],
        "thread": "entity_properties",
        "predicate": "hasAchievement",
        "edge_label": "Achievement"
      }
    }
  ],
  "graph_visualization": {
    "nodes": [
      {"id": "kw_궁궐", "type": "keyword", "label": "궁궐"},
      {"id": "ent_경복궁", "type": "entity", "label": "경복궁", "entity_type": "Building"},
      {"id": "ent_태조", "type": "entity", "label": "태조", "entity_type": "Person"},
      {"id": "ev_1", "type": "evidence", "label": "Builder: 태조"}
    ],
    "edges": [
      {"from": "kw_궁궐", "to": "ent_경복궁", "label": "matched"},
      {"from": "ent_경복궁", "to": "ent_태조", "label": "hasBuilder"},
      {"from": "ent_경복궁", "to": "ev_1", "label": "entity_properties"}
    ]
  }
}
```

---

## 6. 구현 우선순위

| 순서 | 작업 | 난이도 | 효과 |
|------|------|--------|------|
| 1 | Kiwi 키워드 저장 | 낮음 | 시작점 표시 |
| 2 | Entity trace 필드 추가 | 중간 | 매칭 정보 |
| 3 | Evidence trace 통합 | 중간 | 전체 경로 |
| 4 | graph_visualization 생성 | 높음 | 시각화 데이터 |

---

## 7. 예상 영향

| 항목 | 현재 | 변경 후 |
|------|------|---------|
| Evidence 크기 | ~500B | ~1KB |
| 응답 크기 (15개) | ~7.5KB | ~15KB |
| 처리 시간 | 기준 | +5% 예상 |
| 메모리 | 기준 | +10% 예상 |

→ **영향 미미, UX 개선 효과 큼**

---

*이 설계를 기반으로 LangGraph 파이프라인 수정이 필요합니다.*
