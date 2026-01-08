# LangGraph Thinking Mode를 위한 동적 RAG 설정 가이드

**목적**: 쿼리 타입에 따라 최적의 RAG 파이프라인 설정을 동적으로 선택

---

## 핵심 정리

### 이 실험 결과의 활용 방법

| 구분 | 설명 |
|------|------|
| ❌ | 점수 계산 방식 조정이 아님 |
| ✅ | **쿼리 타입별 시스템 설정 결정에 사용** |

### LangGraph에서의 활용

```
Step 1: 쿼리 분석 → 쿼리 타입 분류 (factual/causal/comparative/deep_analysis)
Step 2: 쿼리 타입에 맞는 설정 선택
Step 3: 해당 설정으로 RAG 파이프라인 실행
```

---

## 쿼리 타입별 특성 (실험 데이터 기반)

### Raw Metrics 비교

| 쿼리 타입 | intent | tbox | triple | relation | evidence |
|----------|--------|------|--------|----------|----------|
| **factual** | 1.00 | 1.00 | 0.56 | 0.43 | 0.36 |
| **causal** | 1.00 | 1.00 | 0.50 | 0.31 | 0.34 |
| **comparative** | 1.00 | 0.86 | 0.54 | **1.00** | 0.42 |
| **deep_analysis** | 1.00 | 0.86 | **0.67** | 0.60 | **0.45** |

### 확장 시 손실 (Baseline → Full)

| 쿼리 타입 | Δintent | Δtbox | Δtriple | Δrelation | Δevidence |
|----------|---------|-------|---------|-----------|-----------|
| **factual** | **-0.41** ★ | -0.12 | +0.10 | -0.23 | +0.02 |
| **causal** | -0.20 | -0.17 | +0.13 | **+0.23** | +0.00 |
| **comparative** | -0.24 | +0.12 | +0.08 | **-0.38** | -0.11 |
| **deep_analysis** | **-0.11** | +0.13 | +0.06 | -0.20 | -0.16 |

---

## 쿼리 타입별 권장 설정

### 1. FACTUAL (사실 확인형)

**예시 질문**: "광해군의 재위 기간은?", "훈민정음 창제 시기는?"

**특징**:
- 확장 시 Intent 손실 최대 (-0.41)
- 정확한 단답형 답변 필요

**권장 설정**:
```python
{
    "semantic_expander": {"temporal": False, "causal_chain": False, "pgvector": False},
    "thread": {"exclude": ["outgoing_relations"]},
    "entity_boost": "normalized",
}
```

**근거**:
- Semantic Expander OFF → Intent 손실 방지
- outgoing 제거 → 불필요한 관계 정보 제거, 정확성 향상
- normalized → triple_validity 1.0 (완벽한 정확성)

---

### 2. CAUSAL (인과관계형)

**예시 질문**: "임진왜란이 발생한 원인은?", "병자호란의 결과는?"

**특징**:
- 확장 시 relation 증가 (+0.23)
- Intent 중간 손실 (-0.20)
- 원인-결과 관계 정보 중요

**권장 설정**:
```python
{
    "semantic_expander": {"temporal": False, "causal_chain": True, "pgvector": False},
    "thread": {"exclude": ["incoming_relations"]},
    "entity_boost": "partial",
}
```

**근거**:
- causal_chain만 ON → 인과관계 정보 확장
- incoming 제거 → Intent 보존 향상 (+0.04)
- partial → 다양한 관계 정보 허용

---

### 3. COMPARATIVE (비교형)

**예시 질문**: "세종대왕과 정조의 업적 비교", "임진왜란과 병자호란 공통점"

**특징**:
- Baseline에서 relation = 1.0 (완벽)
- 확장 시 relation 손실 (-0.38)
- 두 대상 간 관계 구조 유지 중요

**권장 설정**:
```python
{
    "semantic_expander": {"temporal": False, "causal_chain": False, "pgvector": False},
    "thread": {"exclude": ["outgoing_relations"]},
    "entity_boost": "normalized",
}
```

**근거**:
- Semantic Expander OFF → 관계 구조 손실 방지
- outgoing 제거 → 비교 대상 간 관계에 집중
- normalized → 정확한 엔티티 매칭

---

### 4. DEEP_ANALYSIS (심층분석형)

**예시 질문**: "임진왜란이 조선 사회에 끼친 장기적 영향", "당쟁의 전개 과정과 영향"

**특징**:
- 확장해도 Intent 손실 적음 (-0.11)
- evidence 다양성 가장 높음 (0.45)
- 폭넓은 맥락과 다양한 관점 필요

**권장 설정**:
```python
{
    "semantic_expander": {"temporal": True, "causal_chain": True, "pgvector": False},
    "thread": {"exclude": ["incoming_relations"]},
    "entity_boost": "partial",
}
```

**근거**:
- temporal + causal ON → 시간적/인과적 맥락 확장
- incoming 제거 → Intent 보존
- partial → evidence_diversity 0.16 (다양한 근거 허용)

---

## LangGraph 구현 코드

```python
# 쿼리 타입별 설정
QUERY_TYPE_CONFIGS = {
    "factual": {
        "semantic_expander": {
            "temporal": False, 
            "causal_chain": False, 
            "pgvector": False
        },
        "thread": {"exclude": ["outgoing_relations"]},
        "entity_boost": "normalized",
        "description": "정확한 단답형, Intent 최우선"
    },
    "causal": {
        "semantic_expander": {
            "temporal": False, 
            "causal_chain": True,  # 인과관계만 확장
            "pgvector": False
        },
        "thread": {"exclude": ["incoming_relations"]},
        "entity_boost": "partial",
        "description": "원인-결과 관계, 선택적 확장"
    },
    "comparative": {
        "semantic_expander": {
            "temporal": False, 
            "causal_chain": False, 
            "pgvector": False
        },
        "thread": {"exclude": ["outgoing_relations"]},
        "entity_boost": "normalized",
        "description": "비교 대상 간 관계 구조 유지"
    },
    "deep_analysis": {
        "semantic_expander": {
            "temporal": True,   # 시간적 맥락 확장
            "causal_chain": True,  # 인과적 맥락 확장
            "pgvector": False
        },
        "thread": {"exclude": ["incoming_relations"]},
        "entity_boost": "partial",
        "description": "폭넓은 맥락, 다양한 관점"
    },
}


# LangGraph Node: 쿼리 타입 분류
def classify_query_type(state):
    """
    쿼리를 분석하여 타입 분류
    """
    query = state["query"]
    
    # 규칙 기반 분류 (또는 LLM 사용)
    if any(kw in query for kw in ["기간", "시기", "언제", "누가", "무엇"]):
        query_type = "factual"
    elif any(kw in query for kw in ["원인", "이유", "왜", "결과", "영향"]):
        if any(kw in query for kw in ["장기적", "전반", "사회"]):
            query_type = "deep_analysis"
        else:
            query_type = "causal"
    elif any(kw in query for kw in ["비교", "차이", "공통점", "vs"]):
        query_type = "comparative"
    else:
        query_type = "deep_analysis"  # 기본값
    
    state["query_type"] = query_type
    return state


# LangGraph Node: RAG 설정 적용
def configure_rag_pipeline(state):
    """
    쿼리 타입에 따라 RAG 파이프라인 설정
    """
    query_type = state["query_type"]
    config = QUERY_TYPE_CONFIGS[query_type]
    
    state["semantic_expander_config"] = config["semantic_expander"]
    state["thread_config"] = config["thread"]
    state["entity_boost_mode"] = config["entity_boost"]
    
    # Thinking mode 로그
    state["thinking_log"] = f"""
    [RAG 설정 결정]
    쿼리 타입: {query_type}
    설명: {config['description']}
    
    Semantic Expander: {config['semantic_expander']}
    Thread 제외: {config['thread']['exclude']}
    Entity Boost: {config['entity_boost']}
    """
    
    return state
```

---

## 설정 결정 플로우차트

```
                    ┌─────────────────┐
                    │   쿼리 입력      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  쿼리 타입 분류   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐         ┌─────▼─────┐        ┌─────▼─────┐
   │ factual │         │  causal   │        │comparative│
   │   또는   │         │           │        │           │
   └────┬────┘         └─────┬─────┘        └─────┬─────┘
        │                    │                    │
        │              ┌─────▼─────┐              │
        │              │deep_analysis│            │
        │              │ 여부 확인   │             │
        │              └─────┬─────┘              │
        │                    │                    │
   ┌────▼────┐         ┌─────▼─────┐        ┌─────▼─────┐
   │ 정확성   │         │  균형/확장  │        │ 관계유지  │
   │ 최우선   │         │           │        │          │
   └────┬────┘         └─────┬─────┘        └─────┬─────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  설정 적용 후    │
                    │  RAG 실행       │
                    └─────────────────┘
```

---

## 요약 테이블

| 쿼리 타입 | SE temporal | SE causal | Thread 제외 | Entity Boost | 핵심 목표 |
|----------|-------------|-----------|-------------|--------------|----------|
| **factual** | ❌ | ❌ | outgoing | normalized | 정확성 |
| **causal** | ❌ | ✅ | incoming | partial | 인과관계 |
| **comparative** | ❌ | ❌ | outgoing | normalized | 관계유지 |
| **deep_analysis** | ✅ | ✅ | incoming | partial | 지식확장 |

---

*이 가이드는 300개 실험 케이스 분석 결과를 기반으로 작성되었습니다.*
