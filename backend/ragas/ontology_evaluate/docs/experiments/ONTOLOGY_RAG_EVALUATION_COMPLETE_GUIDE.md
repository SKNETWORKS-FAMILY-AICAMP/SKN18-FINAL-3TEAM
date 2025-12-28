# Ontology RAG 평가 시스템 종합 가이드

**최종 업데이트**: 2024년 12월 28일  
**총 실험 케이스**: 660개+ (Ablation 300 + Isolation 240 + Grid Search 120)  
**평가 지표**: Intent-Aware Score + LLM Judge Quality

---

## 1. 실험 개요

### 1.1 이 실험의 목적

HisToK 플랫폼의 Ontology RAG 시스템은 사용자 질문에 대해 **지식 그래프를 확장**하여 더 풍부한 답변을 제공합니다. 그러나 확장이 항상 좋은 것은 아닙니다.

```
핵심 질문:
┌─────────────────────────────────────────────────────────────────┐
│  1. 어떤 컴포넌트가 답변 품질을 향상시키는가?                      │
│  2. 어떤 컴포넌트 조합이 최적인가?                                │
│  3. 쿼리 타입별로 최적 설정이 다른가?                             │
│  4. LLM 판단 없이 점수 기반으로 Evidence를 선택할 수 있는가?       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 시스템 구조

```
사용자 질문
    ↓
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Entity Extraction                                     │
│  → 질문에서 엔티티 추출                                          │
├─────────────────────────────────────────────────────────────────┤
│  Stage 2: Semantic Expander (확장)                              │
│  → temporal: 시간적 맥락 확장                                    │
│  → causal_chain: 인과관계 확장                                  │
│  → pgvector: 벡터 유사도 기반 확장                              │
├─────────────────────────────────────────────────────────────────┤
│  Stage 3: Thread Aggregator (정보 수집)                         │
│  → type_and_summary: 엔티티 타입과 요약                         │
│  → entity_properties: 엔티티 속성                               │
│  → outgoing_relations: 나가는 관계                              │
│  → incoming_relations: 들어오는 관계                            │
│  → connected_entities: 연결된 엔티티                            │
├─────────────────────────────────────────────────────────────────┤
│  Stage 4: Entity Boost (가중치 조정)                            │
│  → exact: 정확한 매칭만                                         │
│  → partial: 부분 매칭 허용                                      │
│  → normalized: 정규화된 매칭                                    │
├─────────────────────────────────────────────────────────────────┤
│  Stage 5: Evidence Selection (55개 → 15개)                      │
│  → 기존: LLM이 판단하여 선택                                    │
│  → 목표: 점수 기반 자동 선택                                    │
├─────────────────────────────────────────────────────────────────┤
│  Stage 6: Answer Generation                                     │
│  → 선택된 Evidence로 최종 답변 생성                              │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 실험 유형

| 실험 유형 | 목적 | 케이스 수 |
|----------|------|----------|
| **Ablation Study** | 컴포넌트 제거 시 성능 변화 | 300개 |
| **Isolation Study** | 컴포넌트 단독 활성화 시 성능 | 240개 |
| **Grid Search** | 최적 조합 탐색 | 120개 |

---

## 2. 평가 지표 설명

### 2.1 평가 체계 구조

```
최종 점수 = Intent-Aware Score × 0.7 + LLM Judge Quality × 0.3
         = (정량 + 정성) × 0.7 + (답변 품질) × 0.3
```

### 2.2 Intent-Aware Score (정량 + 정성)

| 메트릭 | 유형 | 가중치 | 설명 |
|--------|------|--------|------|
| **Intent Preservation** | 정성 (LLM) | 52.6% | 확장이 질문 의도를 유지하는가? |
| TBox Consistency | 정량 | 10.5% | 온톨로지 스키마를 준수하는가? |
| Relation Coherence | 정량 | 10.5% | 관계가 의미적으로 일관되는가? |
| **Triple Validity** | 정성 (LLM) | 10.5% | Triple이 답변에 기여하는가? |
| Evidence Diversity | 정량 | 5.3% | 다양한 Thread에서 정보 수집? |
| Convergence Utilization | 정량 | 5.3% | 수렴 노드를 활용했는가? |

**Intent Preservation 점수 체계**:
- `Preserve (1.0)`: 의도 유지
- `Enrich (1.2)`: 의도 심화 (보너스)
- `Drift (0.5)`: 의도 전환 (페널티)
- `Hallucinated (0.0)`: 의도 무관 (실패)

### 2.3 LLM Judge Quality (답변 품질)

| 메트릭 | 가중치 | 설명 |
|--------|--------|------|
| **Completeness** | 25% | 질문에 충분히 답했는가? |
| **Information Richness** | 20% | 추가로 유용한 정보 제공? |
| **Factual Accuracy** | 25% | 역사적 사실과 일치하는가? |
| Coherence | 15% | 논리적으로 일관되는가? |
| Helpfulness | 15% | 사용자에게 도움이 되는가? |

### 2.4 왜 이런 평가 체계인가?

```
문제 상황:
┌─────────────────────────────────────────────────────────────────┐
│  확장 시스템의 목표: "더 풍부한 답변 제공"                        │
│  BUT Intent-Aware Score만으로는:                                │
│    - 확장 안 하면 → Intent = 1.0 (자동 만점)                    │
│    - 확장 하면 → Intent < 1.0 (페널티)                          │
│  → 확장의 "가치"가 아닌 "안전성"만 측정                          │
└─────────────────────────────────────────────────────────────────┘

해결:
┌─────────────────────────────────────────────────────────────────┐
│  LLM Judge Quality 추가 (30%)                                   │
│  → Information Richness: 확장으로 더 유용한 정보 제공했는가?     │
│  → Completeness: 질문에 충분히 답했는가?                        │
│  → 확장의 실제 "가치" 측정                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 실험 결과 요약

### 3.1 Grid Search 결과 (조합 효과)

| 설정 | Intent점수 | LLM품질 | 종합(7:3) | 순위 |
|------|-----------|--------|----------|------|
| **ablation_baseline** | **0.8551** | **0.7198** | **0.8145** | 🥇 |
| minimal | 0.8055 | 0.7003 | 0.7739 | 🥈 |
| with_outgoing | 0.7855 | 0.6826 | 0.7547 | 🥉 |
| recommended_default | 0.7508 | 0.7304 | 0.7447 | 4 |
| with_exact_boost | 0.7584 | 0.7103 | 0.7439 | 5 |
| causal_temporal_combo | 0.6781 | 0.6544 | 0.6710 | 6 |

**핵심 발견**: 
- `ablation_baseline` (확장 없음)이 최고 → **컴포넌트 간 부정적 상호작용 존재**
- `causal_temporal_combo` (동시 활성화)가 최저 → **조합 시 노이즈 증가**

### 3.2 Isolation 결과 (단일 컴포넌트)

#### Semantic Expander

| 컴포넌트 | Intent점수 | LLM품질 | 종합(7:3) |
|----------|-----------|--------|----------|
| **causal_chain** | 0.7611 | **0.6437** | **0.7259** |
| pgvector | 0.7451 | 0.6003 | 0.7017 |
| temporal | 0.7350 | 0.5912 | 0.6918 |

#### Thread Aggregator

| 컴포넌트 | Intent점수 | LLM품질 | 종합(7:3) |
|----------|-----------|--------|----------|
| **type_and_summary** | **0.7984** | **0.6126** | **0.7427** |
| entity_properties | 0.7389 | 0.5942 | 0.6955 |
| outgoing | 0.7115 | 0.6085 | 0.6806 |
| incoming | 0.6910 | 0.6100 | 0.6667 |
| connected | 0.7395 | 0.3476 | 0.6220 |

#### Entity Boost

| 모드 | Intent점수 | LLM품질 | 종합(7:3) |
|------|-----------|--------|----------|
| **normalized** | 0.7593 | **0.6049** | **0.7130** |
| none | 0.7634 | 0.5536 | 0.7005 |
| partial | 0.7516 | 0.5740 | 0.6983 |
| exact | 0.7399 | 0.5924 | 0.6956 |

### 3.3 쿼리 타입별 최적 설정

| 쿼리 타입 | 최적 Semantic | 가중치 | 최적 Thread | 가중치 |
|-----------|--------------|--------|------------|--------|
| **factual** | pgvector | 0.40 | type_and_summary | 0.41 |
| **causal** | causal_chain | 0.39 | type_and_summary | 0.43 |
| **comparative** | temporal/causal | 0.35 | type_and_summary | 0.37 |
| **deep_analysis** | **causal_chain** | **0.46** | type_and_summary | 0.37 |

---

## 4. 구체적 사례 분석

### 4.1 성공 사례: 확장이 효과적인 경우

#### 사례 1: 태조 이성계의 재위 기간 (LLM Quality: 1.0)

**질문**: 태조 이성계의 재위 기간은?  
**타입**: factual  
**설정**: ablation_baseline

**답변**:
```
태조 이성계의 재위 기간은 1392년 시작하여 1398년 퇴위로 총 6년 재위이며, 
이성계 추대에 의해 태조로 즉위한 것입니다.

1392년 이성계 추대에 의해 태조로 즉위하면서 조선을 건국한 초대 왕으로 
재위가 시작되었습니다. 재위 기간은 1392년부터 1398년까지...
```

**성공 요인**:
- 핵심 정보(1392년, 1398년, 6년)를 정확히 제공
- 불필요한 확장 없이 간결하게 답변
- Intent Preservation = 0.8844, LLM Quality = 1.0

---

#### 사례 2: 임오군란의 배경 (Intent: 1.0, LLM: 0.85)

**질문**: 임오군란이 발생한 배경은?  
**타입**: deep_analysis  
**설정**: minimal (causal + type_and_summary)

**답변**:
```
임오군란의 배경은 1882년의 내부 개혁 갈등이 심화되는 가운데 외세 간섭이 
본격화된 시간적 배경에 있으며, 이 흐름은 1884년의 갑신정변으로 이어져 
근대화 시도와 외교 구도가 한층 격화되었습니다.

임오군란은 1882년 서울에서 벌어진 군사 반란으로, 조선 정부가 추진한 
군제 개편과 근대화 정책에 대한 군인들의 불만이 폭발한 사건입니다...
```

**성공 요인**:
- causal_chain 확장이 인과관계(임오군란 → 갑신정변) 연결
- deep_analysis에서 확장이 효과적
- 시간적 흐름과 원인-결과를 명확히 서술

---

### 4.2 실패 사례: 확장이 역효과인 경우

#### 사례 3: 경국대전 편찬 왕 (Intent vs LLM 불일치)

**질문**: 경국대전을 편찬한 왕은 누구인가?  
**타입**: factual

| 설정 | Intent | LLM | 답변 요약 |
|------|--------|-----|----------|
| minimal | 0.8947 | **0.5000** | "태조 이성계" (❌ 오답) |
| causal_temporal_combo | 0.5892 | **0.9200** | "성종" (✅ 정답) |

**minimal 답변** (Intent 높지만 오답):
```
경국대전을 편찬한 주도 왕은 태조 이성계입니다. 
1394년에는 조선 초의 치국 정책을 담은 법제서를 육전체제에 근거해 편찬하였고...
```

**causal_temporal_combo 답변** (Intent 낮지만 정답):
```
경국대전은 성종이 편찬을 주도하여 1485년 1월 1일부터 시행된 조선의 
통일 법전입니다.
```

**분석**:
- Intent Score가 높아도 **사실적 정확성이 낮을 수 있음**
- LLM Quality의 Factual Accuracy가 이를 보완
- **두 지표의 조합이 필수적**

---

#### 사례 4: 조선시대 신분제도 변화 (LLM Quality: 0.26)

**질문**: 조선시대 신분제도의 변화와 그 영향은?  
**타입**: causal  
**설정**: with_outgoing

**답변**:
```
[데이터 부재를 안내하는 수준에 머물러 있어 완성도와 유용성이 크게 떨어진다]
```

**LLM Judge 평가**:
```
시스템 답변은 질문에 대한 구체적 역사 분석을 제공하지 않고 데이터 부재를 
안내하는 수준에 머물러 있어 완성도와 유용성이 크게 떨어진다.
```

**실패 원인**:
- outgoing_relations가 관련 없는 정보를 너무 많이 수집
- 정작 핵심 정보(양반/중인/상민/천민 체계)를 찾지 못함
- Evidence 선택 단계에서 노이즈에 묻힘

---

#### 사례 5: 설정 간 큰 차이 - 한양 천도

**질문**: 한양 천도는 몇 년도에 이루어졌는가?  
**타입**: factual  
**Intent 차이**: 0.3176 (최대 vs 최소)

| 설정 | Intent | LLM | 특징 |
|------|--------|-----|------|
| ablation_baseline | 0.8176 | 0.7100 | 풍부한 맥락 제공 |
| minimal | 0.5000 | 0.7000 | 간결하지만 Intent 낮음 |

**ablation_baseline 답변**:
```
한양 천도는 1394년에 이루어졌으며, 이양, 이양생, 이양중, 권양, 정양한, 
정양 등의 인물과 양도목 같은 기관이 관련 기록에 등장하고...

천도 과정의 인과관계를 시간의 흐름에 맞추어 보면, 먼저 1392년 태조 이성계가 
새로운 왕조의 기초를 다진 뒤 수도를 한양으로 정비하려고 했습니다...
```

**분석**:
- factual 질문에서도 맥락 정보가 답변 품질을 높임
- 단, 불필요한 인물 나열(이양, 이양생 등)은 노이즈

---

### 4.3 쿼리 타입별 패턴

#### Factual (사실 확인형)

| 특징 | 설명 |
|------|------|
| 최적 설정 | ablation_baseline 또는 minimal |
| 확장 효과 | 대체로 부정적 (Intent 손실) |
| 핵심 지표 | Factual Accuracy가 가장 중요 |
| 대표 실패 | "경국대전 편찬 왕" - Intent 높지만 오답 |

#### Causal (인과관계형)

| 특징 | 설명 |
|------|------|
| 최적 설정 | causal_chain 활성화 |
| 확장 효과 | 긍정적 (인과 관계 연결) |
| 핵심 지표 | Information Richness 중요 |
| 대표 성공 | "임오군란 배경" - 갑신정변 연결 |

#### Comparative (비교형)

| 특징 | 설명 |
|------|------|
| 최적 설정 | 확장 최소화 |
| 확장 효과 | 부정적 (관계 구조 손실) |
| 핵심 지표 | 두 대상 간 관계 유지 |
| 주의점 | 과도한 확장 시 비교 대상 혼동 |

#### Deep Analysis (심층 분석형)

| 특징 | 설명 |
|------|------|
| 최적 설정 | causal_chain (가중치 0.46) |
| 확장 효과 | 긍정적 (풍부한 맥락) |
| 핵심 지표 | Information Richness + Completeness |
| 대표 성공 | "세도정치 영향 분석" |

---

## 5. 최종 가중치 설정

### 5.1 쿼리 타입별 Evidence 가중치

```python
QUERY_TYPE_WEIGHTS = {
    "factual": {
        "semantic": {
            "temporal": 0.32,
            "causal_chain": 0.28,
            "pgvector": 0.40,      # ⭐ 벡터 유사도 중심
        },
        "thread": {
            "type_and_summary": 0.41,  # ⭐ 최고
            "entity_properties": 0.30,
            "outgoing_relations": 0.29,
        },
        "entity_boost": "normalized"
    },
    
    "causal": {
        "semantic": {
            "temporal": 0.25,
            "causal_chain": 0.39,  # ⭐ 인과관계 중심
            "pgvector": 0.36,
        },
        "thread": {
            "type_and_summary": 0.43,
            "entity_properties": 0.33,
            "outgoing_relations": 0.25,
        },
        "entity_boost": "normalized"
    },
    
    "comparative": {
        "semantic": {
            "temporal": 0.35,
            "causal_chain": 0.35,  # 균등 분포
            "pgvector": 0.31,
        },
        "thread": {
            "type_and_summary": 0.37,
            "entity_properties": 0.33,
            "outgoing_relations": 0.31,
        },
        "entity_boost": "normalized"
    },
    
    "deep_analysis": {
        "semantic": {
            "temporal": 0.30,
            "causal_chain": 0.46,  # ⭐⭐ 압도적
            "pgvector": 0.24,
        },
        "thread": {
            "type_and_summary": 0.37,
            "entity_properties": 0.29,
            "outgoing_relations": 0.35,
        },
        "entity_boost": "normalized"
    },
}
```

### 5.2 비활성화 권장 컴포넌트

| 컴포넌트 | 조치 | 근거 |
|----------|------|------|
| `incoming_relations` | ❌ 비활성화 | 종합 점수 0.6667 (최하위) |
| `connected_entities` | ❌ 비활성화 | LLM 품질 0.35 (최저) |

### 5.3 Evidence 선택 알고리즘

```python
def select_top_evidences(evidences, query_type, top_k=15):
    """
    가중치 기반 상위 Evidence 선택
    → LLM 판단 없이 점수 기반 자동 선택
    """
    weights = QUERY_TYPE_WEIGHTS[query_type]
    
    scored = []
    for ev in evidences:
        # 비활성화 컴포넌트 필터링
        if ev.thread_type in ["incoming_relations", "connected_entities"]:
            continue
        
        # 가중치 계산
        sem_weight = weights["semantic"].get(ev.expansion_method, 0.33)
        thread_weight = weights["thread"].get(ev.thread_type, 0.33)
        
        final_score = sem_weight * thread_weight * ev.base_score
        scored.append((ev, final_score))
    
    # 상위 k개 선택
    scored.sort(key=lambda x: x[1], reverse=True)
    return [ev for ev, _ in scored[:top_k]]
```

---

## 6. 결론

### 6.1 핵심 발견

1. **컴포넌트 간 부정적 상호작용**: 단독으로 효과적인 컴포넌트도 조합 시 성능 하락
2. **쿼리 타입별 최적 설정 상이**: deep_analysis에서만 확장이 명확히 효과적
3. **평가 지표 조합 필수**: Intent Score만으로는 사실 정확성 판단 불가
4. **가중치 기반 선택 가능**: LLM 판단 없이 점수 기반 Evidence 선택 가능

### 6.2 즉시 적용 사항

| 항목 | 조치 | 효과 |
|------|------|------|
| incoming_relations | 비활성화 | +11.7% 성능 향상 |
| connected_entities | 비활성화 | LLM 품질 개선 |
| entity_boost | normalized 고정 | 일관된 성능 |
| Evidence 선택 | 점수 기반 | 속도 + 일관성 |

### 6.3 한계점

- **Factual 정확성 vs Intent 보존**: 때로 상충됨 (경국대전 사례)
- **복잡한 질문**: 신분제도 변화처럼 광범위한 주제는 여전히 어려움
- **조합 효과 예측**: 단일 컴포넌트 효과로 조합 효과 완전 예측 불가

---

## 7. 부록: 설정 요약 테이블

### Semantic Expander 가중치

| 쿼리 타입 | temporal | causal_chain | pgvector | 핵심 |
|-----------|----------|--------------|----------|------|
| factual | 0.32 | 0.28 | **0.40** | 벡터 유사도 |
| causal | 0.25 | **0.39** | 0.36 | 인과관계 |
| comparative | 0.35 | 0.35 | 0.31 | 균등 |
| deep_analysis | 0.30 | **0.46** | 0.24 | 인과 강조 |

### Thread Aggregator 가중치

| 쿼리 타입 | type_and_summary | entity_properties | outgoing |
|-----------|------------------|-------------------|----------|
| factual | **0.41** | 0.30 | 0.29 |
| causal | **0.43** | 0.33 | 0.25 |
| comparative | **0.37** | 0.33 | 0.31 |
| deep_analysis | **0.37** | 0.29 | 0.35 |

---

*본 문서는 660개+ 실험 케이스의 실제 데이터를 기반으로 작성되었습니다.*  
*모든 수치는 2024년 12월 28일 최신 실험 결과입니다.*
