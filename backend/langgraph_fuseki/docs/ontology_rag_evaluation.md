# HistoK Ontology-based RAG 평가 프레임워크

## 1. 문제 재정의

### 1.1 기존 RAGAS의 한계

**RAGAS Faithfulness의 전제 붕괴**:
- RAGAS Faithfulness는 **retrieved context**(닫힌 전제)를 가정
- Ontology-driven inference는 **inferred context**를 생성
- 추론된 관계는 retrieved document에 없으므로 Faithfulness 평가 전제가 붕괴됨

**RAGAS Relevancy의 오해**:
- 질문 표면(surface form)과의 직접 관련성만 측정
- 의미 확장 시 낮은 점수 → 온톨로지 시스템의 핵심 가치를 반영하지 못함

### 1.2 HistoK의 핵심 과제

> "질문 표면(surface form)과는 멀어지지만, **질문 의도(intent)와의 정합성**은 유지되어야 한다"

문제는 **Intent Drift(의도 이탈)**이지, 방향 전환 자체가 아님.

### 1.3 평가 목표

> **"정답(answer)을 평가하지 않고, 추론 행위(reasoning behavior)를 평가한다"**

이것이 Ground Truth 없이도 평가 가능한 이론적 근거.

---

## 2. 실패 유형 분류 (Failure Taxonomy)

| 실패 유형 | 설명 | HistoK 예시 |
|----------|------|-------------|
| **Intent Drift** | 질문 의도에서 이탈 | "임진왜란의 원인" → 이순신의 식습관으로 확장 |
| **Relation Misuse** | 관계 의미 오용 | `participatesIn` 대신 `contemporaryWith` 사용 |
| **Over-expansion** | 필요 이상 확장 | Semantic Expander에서 75개 → 200개로 과도 확장 |
| **Semantic Shortcut** | 논리적 근거 없는 점프 | A→B→C 경로 무시하고 A→C 직접 연결 |
| **Schema Violation** | TBox 위반 | `Person → birthPlace → Event` (타입 오류) |
| **Thread Imbalance** | Thread별 정보 불균형 | 5개 Thread 중 1개만 95%의 evidences 제공 |
| **Low Diversity** | 경로 다양성 부족 | 15개 evidences가 모두 같은 expansion_method 출처 |

---

## 3. 평가 레벨 분리 (4-Level Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│  L4: Answer Utility (Optional)       ← 기존 RAGAS 영역      │
│      - 답변 자연스러움, 완결성                               │
├─────────────────────────────────────────────────────────────┤
│  L3: Terminal Knowledge Contribution  ← HistoK 핵심 (1)      │
│      - Terminal Triple Validity                             │
│      - Evidence Diversity                                   │
│      - Convergence Node Utilization (query_type별 차등)     │
├─────────────────────────────────────────────────────────────┤
│  L2: Expansion Path Quality          ← HistoK 핵심 (2)      │
│      - Intent Preservation Score                            │
│      - Relation Semantic Coherence                          │
│      - Path Necessity (Counterfactual)                      │
├─────────────────────────────────────────────────────────────┤
│  L1: Ontology Schema Compliance                             │
│      - TBox Consistency                                     │
│      - Type Constraint Validation                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. HistoK 평가 메트릭

### 📊 L1: Ontology Schema Compliance

#### 4.1.1 TBox Consistency Score

**목적**: 확장 경로가 온톨로지 스키마(TBox)를 위반하지 않는지 검증

**평가 대상**: Stage 3 (Semantic Expander), Stage 4 (Parallel Knowledge Retrieval)

**검증 항목**:
- 각 triple의 domain/range 타입 일치
- 허용되지 않은 relation 사용 여부

**계산 방식**:
```
TBox_Consistency = 1.0 - (violations_count / total_triples)
```

**예시**:
```
✓ Person -[participatesIn]-> Event (domain: Person, range: Event)
✗ Person -[birthPlace]-> Event (domain: Person, range: Place - 타입 불일치)
```

---

### 📊 L2: Expansion Path Quality

#### 4.2.1 Intent Preservation Score 🆕

**목적**: 각 hop에서 질문 의도가 유지/강화/이탈되는지 추적

**평가 대상**: Stage 3 (Semantic Expander의 3가지 확장 방법: Temporal, Causal Chain, Pgvector)

**Intent 상태 분류**:
| 상태 | 점수 | 의미 |
|------|------|------|
| Preserve | 1.0 | 의도 유지 |
| Enrich | 1.2 | 의도 심화 (보너스) |
| Drift | 0.5 | 의도 전환 (페널티) |
| Hallucinated | 0.0 | 의도 무관 (실패) |

**계산 방식**:
```
Intent_Preservation = Σ(hop_score) / hop_count

# 질문 의도 키워드 추출 (LLM)
질문: "임진왜란의 원인"
의도 키워드: ["원인", "배경", "발생", "이유"]

# 각 hop 평가
hop 1: "임진왜란" → "명나라 요청" (Enrich: 1.2)
hop 2: "명나라 요청" → "이순신의 식습관" (Hallucinated: 0.0)
→ Intent_Preservation = (1.2 + 0.0) / 2 = 0.6
```

**HistoK 적용**:
- Stage 1의 `query_intent` 사용
- Temporal 확장: "임진왜란" → "정유재란" (Enrich ✓)
- Temporal 확장: "임진왜란" → "인조반정" (Drift ✗)

---

#### 4.2.2 Relation Semantic Coherence 🆕

**목적**: 각 relation이 질문 의도와 의미론적으로 일관되는지 평가

**평가 대상**: Stage 4 (Parallel Knowledge Retrieval의 5개 Thread)

**Intent별 Valid Relations**:
| 질문 의도 | Valid Relations |
|-----------|----------------|
| 원인 | `caused`, `causes`, `leadsTo`, `ledTo` |
| 업적 | `built`, `established`, `achieved`, `founded` |
| 결과 | `leadsTo`, `causes`, `affects` |
| 관계 | `participatesIn`, `involvesPerson`, `relatedTo` |

**계산 방식**:
```
Relation_Coherence = coherent_relations / total_relations

# 예시: "세종의 업적" 질문
Thread 1: [built, established, founded] → 3/3 = 1.0 ✓
Thread 2: [diedIn, marriedTo, contemporaryWith] → 0/3 = 0.0 ✗
```

---

#### 4.2.3 Counterfactual Sufficiency Test

**목적**: 확장이 실제로 필요했는지 counterfactual 방식으로 검증

**평가 질문**:
1. Answer' (확장 X)가 minimal answer 조건을 충족하는가?
2. Answer - Answer' = 확장의 기여도 측정
3. 추가 정보가 legitimate sub-question에 답하는가?

**계산 방식**:
```python
# Baseline 비교
Answer_full = generate(with_expansion=True)
Answer_baseline = generate(with_expansion=False)

# LLM-as-Judge
evaluation = {
    "minimal_satisfied": bool,  # Answer_baseline이 최소 요구사항 충족?
    "expansion_contribution": float,  # 0~1
    "legitimacy": bool  # 추가 정보가 합법적인 sub-question에 답하는가?
}

Expansion_Necessity = (
    0.0 if minimal_satisfied else 0.5
) + expansion_contribution * 0.5
```

**HistoK 적용**:
- Semantic Expander ON/OFF 비교
- Thread별 Ablation Study (각 Thread를 하나씩 제거)

---

### 📊 L3: Terminal Knowledge Contribution

#### 4.3.1 Terminal Triple Validity 🆕

**목적**: 최종 도달한 (Subject, Relation, Object) triple이 질문에 기여하는지 평가

**평가 대상**: Stage 5 (Path Evidence Aggregator의 top 15 evidences)

**평가 기준**:
- Before: Node만 평가 → 부정확
- After: **Node + Relation + Context** 전체 평가

**예시**:
```
질문: "세종대왕의 업적"

Triple 1: (세종대왕) -[built]-> (경복궁)
평가: 기여함 (1.0) ✓

Triple 2: (세종대왕) -[contemporaryWith]-> (성삼문)
평가: 간접 기여 (0.5)

Triple 3: (세종대왕) -[marriedTo]-> (소헌왕후)
평가: 무관함 (0.0) ✗
```

**계산 방식**:
```
Terminal_Triple_Validity = Σ(triple_score) / evidence_count
```

**LLM-as-Judge 프롬프트**:
```
질문: {question}
질문 의도: {query_intent}

Triple: ({subject}) -[{relation}]-> ({object})

이 triple이 질문에 답하는 데 기여하는가?
1. 기여함 (1.0)
2. 간접 기여 (0.5)
3. 무관함 (0.0)
```

---

#### 4.3.2 Evidence Diversity Score

**목적**: 5개 Thread에서 고르게 evidences가 선택되었는지 평가

**문제 상황**:
```
Thread 1 (outgoing_relations): 14개
Thread 2 (incoming_relations): 1개
Thread 3 (entity_properties): 0개
Thread 4 (connected_entities): 0개
Thread 5 (type_and_summary): 0개
→ 매우 불균형 (Thread Imbalance 실패)
```

**계산 방식** (Shannon Entropy):
```python
import math

def evidence_diversity_score(evidences):
    thread_distribution = {}
    for ev in evidences:
        thread_type = ev["type"]
        thread_distribution[thread_type] = thread_distribution.get(thread_type, 0) + 1

    total = len(evidences)
    entropy = 0
    for count in thread_distribution.values():
        p = count / total
        entropy -= p * math.log2(p) if p > 0 else 0

    # 5개 Thread 기준 최대 entropy = log2(5) ≈ 2.32
    max_entropy = math.log2(5)
    diversity_score = entropy / max_entropy

    return diversity_score

# 예시
evidences = [
    {"type": "outgoing_relations"},  # 7개
    {"type": "incoming_relations"},  # 4개
    {"type": "entity_properties"},   # 2개
    {"type": "connected_entities"},  # 1개
    {"type": "type_and_summary"}     # 1개
]
diversity = evidence_diversity_score(evidences)  # ≈ 0.85 (양호)
```

**목표**:
- 5개 Thread에서 최소 1개씩은 선택
- 다양성 점수 0.7 이상 권장

---

#### 4.3.3 Convergence Node Utilization Score 🆕

**목적**: 수렴 노드가 답변에 실제로 활용되었는지, query_type에 맞게 활용되었는지 평가

**중요**: 수렴 노드는 평가 요소 중 **하나**일 뿐. 2개 이상의 관계를 묻는 질문(예: A와 B의 공통점)에서만 높은 가중치 부여

**query_type별 중요도**:
| query_type | 가중치 | 이유 |
|------------|--------|------|
| causal | 1.5 | 인과관계 질문에서 수렴 노드는 핵심 |
| deep_analysis | 1.3 | 심층 분석 시 연결점 중요 |
| comparative | 1.2 | 비교 질문 시 공통점 찾기 유용 |
| factual | 1.0 | 사실 질문에서는 수렴 노드 덜 중요 |

**계산 방식**:
```python
def convergence_node_utilization_score(convergence_nodes, final_answer, query_type):
    if not convergence_nodes:
        return 1.0  # 수렴 노드가 없으면 중립

    # query_type별 가중치
    importance_weight = {
        "causal": 1.5,
        "deep_analysis": 1.3,
        "comparative": 1.2,
        "factual": 1.0
    }.get(query_type, 1.0)

    # 각 수렴 노드가 답변에 언급되었는지 확인
    mentioned_count = 0
    for node in convergence_nodes:
        node_label = node["label"]
        if node_label in final_answer:
            mentioned_count += 1

    utilization_rate = mentioned_count / len(convergence_nodes)
    final_score = utilization_rate * importance_weight

    return min(final_score, 1.0)  # 1.0 상한
```

**HistoK 적용**:
- Stage 5에서 `convergence_nodes` 추출
- Stage 6에서 최종 답변에 언급 여부 확인

---

## 5. 통합 평가 파이프라인

```
┌──────────────────────────────────────────────────────────┐
│  Phase 1: Automatic Structural Validation                │
│  ├─ TBox Consistency (L1)                                │
│  ├─ Path Length Outlier Detection                        │
│  └─ Relation Type Distribution                           │
├──────────────────────────────────────────────────────────┤
│  Phase 2: LLM-as-Judge Evaluation                        │
│  ├─ Intent Preservation Score (L2)                       │
│  ├─ Relation Semantic Coherence (L2)                     │
│  ├─ Terminal Triple Validity (L3)                        │
│  └─ Convergence Node Utilization (L3, query_type별)     │
├──────────────────────────────────────────────────────────┤
│  Phase 3: Counterfactual Testing                         │
│  ├─ Expansion Necessity (baseline 비교)                  │
│  └─ Thread Contribution (ablation study)                 │
├──────────────────────────────────────────────────────────┤
│  Phase 4: Sample-based Human Evaluation (Optional)       │
│  ├─ Clustering & Sampling                                │
│  ├─ Human Annotation                                     │
│  └─ Cluster-wide Score Generalization                    │
└──────────────────────────────────────────────────────────┘
```

---

## 6. HistoK 시스템 적용 가이드

### 6.1 평가 실행 순서

1. **Phase 1 (자동 검증)** - 즉시 실행 가능
   - TBox Consistency: TTL 스키마와 대조
   - Evidence Diversity: Shannon Entropy 계산
   - Path Length 분포 확인

2. **Phase 2 (LLM Judge)** - GPT-4를 Judge로 사용
   - Intent Preservation: Stage 3 각 expansion_method별 평가
   - Relation Coherence: Stage 4 각 Thread별 평가
   - Terminal Triple Validity: Stage 5 top 15 evidences 평가

3. **Phase 3 (Counterfactual)** - Ablation Study
   - Semantic Expander ON/OFF 비교
   - Thread별 기여도 측정 (각 Thread 제거)

4. **Phase 4 (Human Eval)** - Optional
   - 질문 클러스터링 (query_type, 복잡도, 도메인)
   - 각 클러스터에서 3개씩 샘플링 (총 15개)
   - Human annotation → 클러스터 전체 점수 일반화

### 6.2 평가 지표 요약

| Level | 메트릭 | 적용 Stage | 자동/수동 | 중요도 |
|-------|--------|-----------|----------|--------|
| L1 | TBox Consistency | Stage 3, 4 | 자동 | 필수 |
| L2 | Intent Preservation | Stage 3 | LLM Judge | 핵심 |
| L2 | Relation Coherence | Stage 4 | LLM Judge | 핵심 |
| L2 | Expansion Necessity | Stage 3 | Counterfactual | 중요 |
| L3 | Terminal Triple Validity | Stage 5 | LLM Judge | 핵심 |
| L3 | Evidence Diversity | Stage 5 | 자동 | 중요 |
| L3 | Convergence Utilization | Stage 5, 6 | 반자동 | 선택 (query_type별) |

---

## 7. 기존 RAGAS vs HistoK 평가

| 항목 | 기존 RAGAS | HistoK 평가 |
|------|-----------|-------------|
| **평가 대상** | 답변 품질 | 추론 행위 |
| **전제** | Closed context (retrieved docs) | Open context (inferred knowledge) |
| **핵심 메트릭** | Faithfulness, Relevancy | Intent Preservation, Relation Coherence |
| **Ground Truth** | 필수 | 불필요 (counterfactual 방식) |
| **수렴 노드** | 평가 안 함 | query_type별 차별화 평가 |
| **확장 필요성** | 평가 안 함 | Counterfactual Sufficiency Test |
| **경로 다양성** | 평가 안 함 | Evidence Diversity Score |

---

## 8. 향후 실험 방향

### 8.1 Phase 1: Baseline 설정 (필수)
- [ ] Semantic Expander 없이 직접 검색만 (baseline)
- [ ] Semantic Expander 3가지 방법 개별 평가 (Temporal, Causal Chain 1-3 hop, Pgvector)
- [ ] Thread별 기여도 측정 (각 Thread 제거 실험)

### 8.2 Phase 2: 가중치 튜닝
- [ ] `FIXED_SCORE_*` 값 실험 (temporal, causal_chain, pgvector)
- [ ] Causal Chain hop별 가중치 최적화 (1-hop vs 2-hop vs 3-hop 기여도)
- [ ] `THREAD_WEIGHT_*` 값 실험 (5개 Thread별 가중치)
- [ ] `QUERY_ENTITY_MATCH_BOOST_*` 값 실험

### 8.3 Phase 3: 수렴 노드 최적화
- [ ] query_type별 convergence 가중치 최적화
- [ ] 수렴 노드 감지 threshold 실험 (현재: 2개 이상 연결)

### 8.4 Phase 4: 테스트 세트 구축
- [ ] query_type별 대표 질문 50개 선정
- [ ] Clustering 기반 샘플링 (15개)
- [ ] Human evaluation 수행

---

## 9. 참고 자료

### 9.1 관련 문서
- `scoring_methodology.md`: 점수 계산 방법론 상세
- `conversational_intent_clarification.md`: 의도 확인 전략
- `README.md`: 전체 시스템 아키텍처

### 9.2 핵심 원칙

> "우리는 정답(answer)을 평가하지 않고, 추론 행위(reasoning behavior)를 평가한다."

이 한 문장이 Ground Truth 없는 평가의 이론적 근거.
