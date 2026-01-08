# 최적 설정 적용 가이드

**Quick Win 실험 결과 기반 최적 설정**

## 📊 실험 근거

- 데이터: 300개 케이스 (Semantic Expander 100 + Thread 120 + Entity Boost 80)
- 가중치: aggressive_intent (intent_preservation=5.0)
- 결과: 전체 성능 +0.82% 개선

---

## 🎯 핵심 정리

### 이 설정의 활용 방법

| 구분 | 설명 |
|------|------|
| ✅ | **config.py에 이미 반영됨** |
| ✅ | 쿼리 타입별 동적 설정 지원 |
| ✅ | 별도 설정 없이 바로 사용 가능 |

### 설정 적용 방식

```
기본 설정 (전역):
  - incoming_relations: 0.0 (Intent 강화)
  - Semantic Expander: 모두 OFF
  - Entity Boost: normalized + partial 강화

쿼리 타입별 동적 설정:
  - factual → 정확성 최우선
  - causal → 인과관계 확장
  - comparative → 관계 구조 유지
  - deep_analysis → 폭넓은 확장
```

---

## 🔧 적용 방법

### 1. 기본 설정 (자동 적용)

**✅ `backend/langgraph_fuseki/config.py`에 이미 최적 설정이 반영되어 있습니다!**

#### 전역 기본값 (Quick Win 결과)

```python
# Thread: incoming_relations 비활성화 (Intent 강화)
THREAD_WEIGHT_INCOMING_RELATIONS = 0.0

# Entity Boost: Normalized + Partial 강화 (Intent와 Accuracy 균형)
QUERY_ENTITY_MATCH_BOOST_PARTIAL = 1.5
QUERY_ENTITY_MATCH_BOOST_NORMALIZED = 1.5

# Semantic Expander: 모두 비활성화 (baseline 최적)
FIXED_SCORE_CAUSAL_CHAIN = 0.0
FIXED_SCORE_TEMPORAL = 0.0
FIXED_SCORE_PGVECTOR = 0.0
```

#### 쿼리 타입별 동적 설정

```python
from backend.langgraph_fuseki.config import get_config_for_query_type

# 사용 예시
config = get_config_for_query_type("causal")
# {
#   "semantic_expander": {"temporal": False, "causal_chain": True, "pgvector": False},
#   "thread_weights": {"incoming_relations": 0.0, ...},
#   "entity_boost": "partial"
# }
```

---

## 📋 변경 사항 요약

### 전역 기본 설정

| 항목 | 기존 | 최적 | 근거 |
|------|-----|------|------|
| **Thread incoming_relations** | 1.0 | **0.0** | Intent 강화 (11승 4패, +1.7%p) |
| **Entity Boost normalized** | 1.0 | **1.5** | Triple 정확도 강화 |
| **Entity Boost partial** | 1.0 | **1.5** | Intent 보존 강화 |
| **Semantic Expander ALL** | 1.0 | **0.0** | Baseline 최적 (Gap: 0.2004) |

### 쿼리 타입별 설정

| 쿼리 타입 | SE temporal | SE causal | Thread 제거 | Entity Boost | 핵심 목표 |
|----------|-------------|-----------|-------------|--------------|----------|
| **factual** | ❌ | ❌ | outgoing | normalized | 정확성 |
| **causal** | ❌ | ✅ | incoming | partial | 인과관계 |
| **comparative** | ❌ | ❌ | outgoing | normalized | 관계유지 |
| **deep_analysis** | ✅ | ✅ | incoming | partial | 지식확장 |

---

## 🎯 쿼리 타입별 상세 설명

### 1. FACTUAL (사실 확인형)

**예시**: "광해군의 재위 기간은?", "훈민정음 창제 시기는?"

**특징**:
- 확장 시 Intent 손실 최대 (-0.41)
- 정확한 단답형 필요

**설정**:
```python
"factual": {
    "semantic_expander": {"temporal": False, "causal_chain": False, "pgvector": False},
    "thread_weights": {"outgoing_relations": 0.0},  # 불필요한 관계 제거
    "entity_boost": "normalized"  # 완벽한 정확성
}
```

### 2. CAUSAL (인과관계형)

**예시**: "임진왜란이 발생한 원인은?", "병자호란의 결과는?"

**특징**:
- 확장 시 relation 증가 (+0.23)
- 원인-결과 관계 중요

**설정**:
```python
"causal": {
    "semantic_expander": {"causal_chain": True},  # 인과관계만 확장
    "thread_weights": {"incoming_relations": 0.0},  # Intent 보존
    "entity_boost": "partial"  # 다양한 관계 허용
}
```

### 3. COMPARATIVE (비교형)

**예시**: "세종대왕과 정조 비교", "임진왜란과 병자호란 공통점"

**특징**:
- Baseline에서 relation = 1.0 (완벽)
- 확장 시 relation 손실 (-0.38)

**설정**:
```python
"comparative": {
    "semantic_expander": {"temporal": False, "causal_chain": False, "pgvector": False},
    "thread_weights": {"outgoing_relations": 0.0},  # 관계 구조 손실 방지
    "entity_boost": "normalized"  # 정확한 매칭
}
```

### 4. DEEP_ANALYSIS (심층분석형)

**예시**: "임진왜란의 장기적 영향", "당쟁의 전개 과정과 영향"

**특징**:
- Intent 손실 최소 (-0.11)
- 폭넓은 맥락 필요

**설정**:
```python
"deep_analysis": {
    "semantic_expander": {"temporal": True, "causal_chain": True},  # 시간적/인과적 확장
    "thread_weights": {"incoming_relations": 0.0},  # Intent 보존
    "entity_boost": "partial"  # 다양한 근거
}
```

---

## 🔄 사용 방법

### LangGraph Node에서 활용

```python
from backend.langgraph_fuseki.config import get_config_for_query_type

def configure_rag_pipeline(state):
    """쿼리 타입에 따라 RAG 파이프라인 설정"""
    query_type = state.get("query_type", "deep_analysis")
    config = get_config_for_query_type(query_type)

    # Semantic Expander 설정
    state["semantic_expander_config"] = config["semantic_expander"]

    # Thread 가중치 설정
    state["thread_weights"] = config["thread_weights"]

    # Entity Boost 모드 설정
    state["entity_boost_mode"] = config["entity_boost"]

    return state
```

### 커스텀 설정 (선택)

환경별로 다른 설정이 필요한 경우 `.env` 파일에서 오버라이드:

```bash
# 예시: 테스트 환경에서 incoming_relations 활성화
THREAD_WEIGHT_INCOMING_RELATIONS=1.0

# 예시: Semantic Expander causal_chain 활성화
FIXED_SCORE_CAUSAL_CHAIN=1.0
```

---

## 📈 기대 성능

### 전역 기본 설정 적용 시

```
기존 설정 (Equal Weights):  0.7062
최적 설정 (Aggressive Intent): 0.7120
───────────────────────────────────
개선율: +0.82%
```

### 쿼리 타입별 개선 효과

- **factual**: Intent 손실 방지 (+0.41p)
- **causal**: 인과관계 정보 증가 (+0.23p)
- **comparative**: 관계 구조 유지 (+0.38p)
- **deep_analysis**: 다양한 맥락 확장 (+0.16p)

---

## 🔄 롤백 방법

문제 발생 시 기본값으로 복원:

```bash
# .env 파일에서 설정
THREAD_WEIGHT_INCOMING_RELATIONS=1.0
QUERY_ENTITY_MATCH_BOOST_NORMALIZED=1.0
QUERY_ENTITY_MATCH_BOOST_PARTIAL=1.0
FIXED_SCORE_CAUSAL_CHAIN=1.0
FIXED_SCORE_TEMPORAL=1.0
FIXED_SCORE_PGVECTOR=1.0
```

---

## 📝 핵심 인사이트

**1. Incoming 제거 = Intent 중심 추론**
- 형식적 정확성(tbox, triple)보다 의도 보존 우선
- 11승 4패, +1.7%p 개선

**2. Normalized + Partial 강화 = 균형**
- Normalized: Triple 정확도 1.0 (완벽)
- Partial: Intent 보존 0.58 (최고)
- 상호 보완 효과

**3. Semantic Expander OFF = 노이즈 제거**
- Baseline이 Full보다 +20%p 우수
- 불필요한 확장이 오히려 성능 저하

**4. 쿼리 타입별 동적 설정 = 최적화**
- factual: 정확성 최우선
- causal: 선택적 확장 (causal_chain만)
- comparative: 최소 확장 (관계 구조 유지)
- deep_analysis: 폭넓은 확장

---

## 📚 추가 참고 자료

- 실험 결과: [backend/ragas/ontology_evaluate/data/quick_win/ALL_WEIGHT_EXPERIMENT_RESULTS.md](../data/quick_win/ALL_WEIGHT_EXPERIMENT_RESULTS.md)
- 쿼리 타입별 가이드: [LANGGRAPH_DYNAMIC_CONFIG_GUIDE.md](LANGGRAPH_DYNAMIC_CONFIG_GUIDE.md)
- 상세 데이터: [backend/ragas/ontology_evaluate/data/quick_win/all_experiments_weight_results.json](../data/quick_win/all_experiments_weight_results.json)
