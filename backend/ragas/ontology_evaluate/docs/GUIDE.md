# HistoK 평가 프레임워크 구현 가이드

## 1. LangGraph 연동 방식

### 연동 방법: **테스트 실행 방식 (코드 삽입 없음)**

**중요**: 평가 코드는 **기존 LangGraph 노드 코드에 삽입되지 않습니다**. 대신 별도의 테스트 스크립트에서 LangGraph를 실행하고 결과를 평가합니다.

```
┌─────────────────────────────────────────────────────────────┐
│  기존 LangGraph (변경 없음)                                    │
│  ├─ Stage 1: Intent Router                                   │
│  ├─ Stage 2: Entity Extractor                                │
│  ├─ Stage 3: Semantic Expander                               │
│  ├─ Stage 4: Parallel Knowledge Retrieval                    │
│  ├─ Stage 5: Path Evidence Aggregator                        │
│  └─ Stage 6: Generate Answer                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
                  graph.invoke(state)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  평가 프레임워크 (ontology_evaluate/)                          │
│  ├─ Evaluators: state_output을 받아서 평가                    │
│  ├─ LLM Judge: GPT-5-nano로 Intent/Triple 평가                    │
│  └─ Result Analyzer: 실험 결과 분석                           │
└─────────────────────────────────────────────────────────────┘
```

### 연동 흐름

```python
# experiments/run_baseline.py

# 1. LangGraph 초기화 (기존 코드 그대로)
from langgraph_fuseki.graph import create_graph_flow
graph = create_graph_flow()

# 2. 테스트 질문으로 실행
initial_state = {
    "query": "세종대왕의 업적은?",
    "test_config": {  # Ablation 설정 주입
        "semantic_expander": {
            "temporal": True,
            "causal_chain": True,
            "pgvector": True,
            ...
        }
    }
}

# 3. LangGraph 실행 (기존 방식 그대로)
state_output = graph.invoke(initial_state)

# 4. 평가 (새로운 코드)
from ragas.ontology_evaluate.evaluators import IntentPreservationEvaluator
evaluator = IntentPreservationEvaluator(llm_judge)
metrics = evaluator.evaluate(state_output)  # GraphState를 분석

# 5. 결과 저장
save_results(metrics)
```

### test_config 활용 방법

**기존 노드 코드 수정 (최소한의 변경)**:

각 노드에서 `test_config`가 있으면 해당 설정을 따르도록 조건문 추가:

```python
# nodes/kg/semantic_expander_node.py

def semantic_expander_node(state: GraphState) -> GraphState:
    # 기존 코드
    extracted_entities = state["extracted_entities"]

    # 테스트 설정 확인 (평가 시에만 사용)
    test_config = state.get("test_config", {})
    semantic_config = test_config.get("semantic_expander", {})

    # Temporal 확장
    if semantic_config.get("temporal", True):  # 기본 True
        temporal_entities = expand_temporal(extracted_entities)
        extracted_entities.extend(temporal_entities)

    # Causal Chain 확장
    if semantic_config.get("causal_chain", True):
        causal_entities = expand_by_causal_chain(extracted_entities)
        extracted_entities.extend(causal_entities)

    # Pgvector 확장
    if semantic_config.get("pgvector", True):
        pgvector_entities = expand_by_pgvector(extracted_entities)
        extracted_entities.extend(pgvector_entities)

    # ... (나머지 확장 방법)

    state["extracted_entities"] = extracted_entities
    return state
```

**변경 최소화**: `test_config`가 없으면 기존 방식 그대로 동작 (기본값 True)

---

## 2. 다음 스텝 (순서대로)

### Step 1: LangGraph에 test_config 지원 추가 ✅ 필수

**작업 내용**: 각 노드가 `test_config`를 인식하도록 최소한의 코드 추가

**수정 파일**:
- `nodes/kg/semantic_expander_node.py`
- `nodes/kg/path_evidence_aggregator_node.py`
- (필요시) `state.py`에 `test_config` 필드 추가

**예상 작업량**: 30분 ~ 1시간

---

### Step 2: 온톨로지 스키마 로드 구현 ✅ 필수

**작업 내용**: TTL 파일에서 온톨로지 스키마(classes, properties) 추출

**파일 생성**:

```python
# backend/ragas/ontology_evaluate/utils/schema_loader.py

def load_ontology_schema(ttl_path: str) -> dict:
    """TTL 파일에서 스키마 로드

    Returns:
        {
            "classes": ["Person", "Event", "Place", ...],
            "properties": {
                "participatesIn": {
                    "domain": "Person",
                    "range": "Event"
                },
                ...
            }
        }
    """
    # rdflib 사용하여 TTL 파싱
    pass
```

**예상 작업량**: 1시간

---

### Step 3: 첫 Ablation 실험 실행 ✅ 핵심

**실행 명령**:

```bash
# 방법 1: 직접 모듈 실행
python -m backend.ragas.ontology_evaluate.experiments.run_baseline \
    --group semantic_expander \
    --limit 5

# 방법 2: 패키지 실행
python -m backend.ragas.ontology_evaluate.experiments \
    --group semantic_expander \
    --limit 5

# 결과 확인
cat backend/ragas/ontology_evaluate/data/results/semantic_expander_ablation.json
```

**예상 결과**:

```json
[
  {
    "experiment_name": "semantic_expander_baseline",
    "query": "세종대왕이 훈민정음을 창제한 시기는?",
    "metrics": {
      "intent_preservation": {"score": 0.85},
      "terminal_triple_validity": {"score": 0.92},
      ...
    }
  },
  ...
]
```

**예상 작업량**: 2~3시간 (디버깅 포함)

---

### Step 5: 결과 분석 및 인사이트 도출 📊

**실행 명령**:

```bash
python -c "
from utils.result_analyzer import ResultAnalyzer
analyzer = ResultAnalyzer('data/results/semantic_expander_ablation.json')
analyzer.generate_report('data/results/analysis_report.txt')
"
```

**분석 내용**:

1. Baseline 대비 각 확장 방법의 기여도
2. 어떤 확장 방법이 Intent Preservation에 기여하는가?
3. Thread별 Evidence Diversity 비교

**예상 작업량**: 1시간

---

### Step 6: Grid Search 실행 (선택적) 🔍

Phase 1 결과를 바탕으로 가중치 최적화:

```bash
python experiments/run_grid_search.py \
    --baseline-results data/results/semantic_expander_ablation.json \
    --search-type semantic
```

**주의**: Grid Search는 많은 시간 소요 (4^4 = 256개 조합)

**예상 작업량**: 4~8시간 (GPU 사용 시)

---

### Step 7: Intent-Aware 평가 실행 ✅ NEW

**작업 내용**: Query type에 따라 메트릭에 다른 가중치를 적용하는 평가 실행

#### Intent-Aware 평가 개요

Intent-Aware Evaluation은 query_type(factual, causal, comparative, deep_analysis)에 따라 평가 메트릭에 다른 가중치를 적용하는 평가 시스템입니다.

**핵심 아이디어**:

- Factual 쿼리: 단순 사실 확인 → 수렴 노드 중요도 낮음
- Causal 쿼리: 인과관계 추론 → 수렴 노드 중요도 높음
- Comparative 쿼리: 2개 엔티티 비교 → 수렴 노드 중요도 매우 높음
- Deep Analysis 쿼리: 심층 분석 → Intent 보존과 관계 일관성 중요

#### 실행 방법

**커맨드라인 실행 (가장 간단)**:

```bash
cd backend/ragas/ontology_evaluate

# Intent-aware 평가 활성화 (기본값)
python -m backend.ragas.ontology_evaluate.experiments.run_baseline \
    --group semantic_expander

# Intent-aware 평가 비활성화 (비교용)
python -m backend.ragas.ontology_evaluate.experiments.run_baseline \
    --group semantic_expander \
    --no-intent-aware

# 디버깅용 (쿼리 10개만)
python -m backend.ragas.ontology_evaluate.experiments.run_baseline \
    --group semantic_expander \
    --limit 10
```

**Python 코드에서 직접 사용**:

```python
from ragas.ontology_evaluate.evaluators.intent_aware_evaluator import IntentAwareEvaluator

# 1. Evaluator 생성
evaluator = IntentAwareEvaluator()

# 2. 각 evaluator의 원점수 준비
raw_metrics = {
    "tbox_consistency": 0.90,
    "intent_preservation": 0.85,
    "relation_coherence": 0.88,
    "triple_validity": 0.82,
    "evidence_diversity": 0.75,
    "convergence_utilization": 0.80
}

# 3. Intent-aware 평가 실행
result = evaluator.evaluate(
    query_type="causal",  # factual, causal, comparative, deep_analysis
    raw_metrics=raw_metrics
)

# 4. 결과 확인
print(f"Query Type: {result['query_type']}")
print(f"Final Score: {result['final_score']:.3f}")
print(f"Weights: {result['weights']}")
print(f"Weighted Metrics: {result['weighted_metrics']}")
```

**출력 예시**:

```
======================================================================
Baseline Ablation Study 실행
======================================================================
실험 그룹: semantic_expander
질문 파일: data/test_queries.json
결과 저장: data/results
Intent-aware 평가: 활성화
======================================================================
테스트 질문 개수: 40
Query Type 분포: {'factual': 10, 'causal': 10, 'comparative': 10, 'deep_analysis': 10}

...

======================================================================
Intent-Aware 평가 요약
======================================================================
  causal         : 0.847 (n=10)
  comparative    : 0.901 (n=10)
  deep_analysis  : 0.823 (n=10)
  factual        : 0.756 (n=10)
======================================================================
```

#### Query Type별 가중치 분석

**Factual (단순 사실 확인)**:

- Schema 준수와 Intent 보존이 가장 중요
- 수렴 노드는 거의 불필요 (가중치 0.075)
- 단순 1-hop 조회에 최적화

**Causal (인과관계 추론)**:

- 수렴 노드가 가장 중요 (가중치 0.234)
- 관계 일관성도 중요 (인과 체인 연결)
- 증거 다양성 중요 (다각적 인과 분석)

**Comparative (비교 분석)**:

- 수렴 노드가 가장 중요 (가중치 0.253)
- 증거 다양성도 매우 중요 (양쪽 엔티티의 증거 필요)
- 2개 엔티티 비교에 최적화

**Deep Analysis (심층 분석)**:

- Intent 보존이 가장 중요 (복합 분석)
- 관계 일관성도 매우 중요
- 균형잡힌 가중치 분포

#### 결과 해석 가이드

**Final Score 해석**:

- **0.9 ~ 1.0**: 매우 우수 - 해당 query_type에 최적화된 성능
- **0.8 ~ 0.9**: 우수 - 대부분의 메트릭이 높은 점수
- **0.7 ~ 0.8**: 양호 - 일부 메트릭 개선 필요
- **0.6 ~ 0.7**: 보통 - 여러 메트릭 개선 필요
- **< 0.6**: 미흡 - 전반적인 개선 필요

**Query Type별 기대 점수 범위**:

| Query Type    | 기대 점수 범위 | 이유                                 |
| ------------- | -------------- | ------------------------------------ |
| Factual       | 0.70 ~ 0.85    | 단순 조회는 높은 점수 쉽게 달성 가능 |
| Causal        | 0.75 ~ 0.90    | 인과 체인 구축 시 높은 점수          |
| Comparative   | 0.80 ~ 0.95    | 수렴 노드 발견 시 매우 높은 점수     |
| Deep Analysis | 0.75 ~ 0.90    | 복합 분석 성공 시 높은 점수          |

#### FAQ

**Q1: Intent-aware 평가를 비활성화하려면?**

```bash
python -m backend.ragas.ontology_evaluate.experiments.run_baseline --no-intent-aware
```

**Q2: 새로운 query_type을 추가하려면?**
`intent_aware_evaluator.py`의 `INTENT_WEIGHT_PRESETS`에 추가

**Q3: 가중치를 동적으로 조정하려면?**
커스텀 가중치 사용 (자세한 내용은 [WEIGHT_CALCULATION_GUIDE.md](./WEIGHT_CALCULATION_GUIDE.md) 참고)

**Q4: Raw metrics와 Intent-aware 점수가 크게 차이나는 이유?**
Intent-aware 평가는 query_type에 따라 가중치를 다르게 적용합니다:

- Factual: 수렴 노드 낮은 가중치 → raw 평균보다 낮을 수 있음
- Comparative: 수렴 노드 높은 가중치 → raw 평균보다 높을 수 있음

이는 정상적인 동작이며, query_type에 적합한 평가를 위한 것입니다.

**예상 작업량**: 30분 (Step 4 완료 후)

---

## 3. ontology_evaluate/ 코드 설명

### 📁 디렉토리별 역할

```
ontology_evaluate/
├── baseline_ablation.py        # Ablation 실험 설정 생성기
├── build_queries_persona.py    # Intent별 테스트 질문 생성
├── evaluators/                 # 평가 메트릭 구현
│   ├── intent_aware_evaluator.py  # NEW: Intent-aware 평가자
│   ├── l1_schema_compliance.py
│   ├── l2_path_quality.py
│   └── l3_terminal_knowledge.py
├── utils/                      # 유틸리티
├── experiments/                # 실험 실행 스크립트
└── data/                       # 데이터
```

---

### 1️⃣ `baseline_ablation.py` - Ablation 실험 설정 생성기

**역할**: Ablation Study의 실험 설정을 자동 생성

**주요 클래스**:

#### `AblationConfig`

```python
@dataclass
class AblationConfig:
    semantic_expander: Dict[str, bool]  # 어떤 확장 방법을 활성화할지
    aggregator_threads: Dict[str, bool]  # 어떤 Thread를 활성화할지
    experiment_name: str                 # 실험 이름
```

**예시**:

```python
# Temporal 확장만 활성화
config = AblationConfig(
    semantic_expander={
        "temporal": True,
        "causal_chain": False,
        "pgvector": False
    },
    experiment_name="semantic_expander_temporal_only"
)
```

#### `AblationExperimentGenerator`

**메서드**:

- `generate_semantic_expander_experiments()`: 5개 Semantic Expander 실험 생성

  - Baseline (모두 비활성화)
  - Temporal Only (±10년 시간적 확장)
  - Causal Chain Only (1-3 hop 인과관계 체인)
  - Pgvector Only (벡터 유사도)
  - Full (모두 활성화)

- `generate_thread_experiments()`: 6개 Thread 실험 생성

  - Baseline (1개만)
  - Leave-One-Out (각 Thread 하나씩 제거)

**사용 예시**:

```python
experiments = AblationExperimentGenerator.generate_semantic_expander_experiments()
# → [AblationConfig(...), AblationConfig(...), ...] 6개 설정 반환
```

#### `AblationRunner`

**역할**: 실험 실행 및 결과 저장

**메서드**:

- `run_single_experiment()`: 1개 질문 × 1개 설정 실행
- `run_experiment_group()`: 여러 질문 × 여러 설정 실행
- `run_all_experiments()`: 모든 실험 실행

**사용 예시**:

```python
runner = AblationRunner(output_dir="data/results")

runner.run_experiment_group(
    queries=["질문1", "질문2", ...],
    configs=[config1, config2, ...],
    graph_invoke_func=graph.invoke,
    group_name="semantic_expander"
)
# → data/results/semantic_expander_ablation.json 생성
```

---

### 2️⃣ `build_queries_persona.py` - 테스트 질문 생성

**역할**: Intent별로 적합한 테스트 질문 40개 생성

**주요 클래스**:

#### `TestQuery`

```python
@dataclass
class TestQuery:
    query: str                      # 질문
    query_type: str                 # factual, causal, comparative, deep_analysis
    intent_keywords: List[str]      # property_groups 그룹명 (예: ["인과관계", "설립"])
    expected_entities: List[str]    # 예상 엔티티 (예: ["임진왜란"])
    expected_property_groups: List[str]  # 예상 property groups
    difficulty: str                 # easy, medium, hard
```

**property_groups.json 기반 구조**:

```json
{
  "query": "세종대왕이 훈민정음을 창제한 시기는 언제인가?",
  "query_type": "factual",
  "intent_keywords": ["연도", "시기", "설립"], // property_groups 그룹명
  "expected_entities": ["세종", "훈민정음"],
  "expected_property_groups": ["연도", "시기", "설립"], // 평가용
  "difficulty": "easy",
  "description": "단순 사실 확인 - 시간 정보"
}
```

#### `PersonaQueryBuilder`

**메서드**:

- `build_factual_queries()`: 10개 사실 확인 질문
- `build_causal_queries()`: 10개 인과관계 질문 (수렴 노드 중요)
- `build_comparative_queries()`: 10개 비교 질문 (수렴 노드 매우 중요)
- `build_deep_analysis_queries()`: 10개 심층 분석 질문

**생성 규칙**:

- **Factual**: 단순 정보 조회 (예: "세종대왕이 훈민정음을 창제한 시기는?")
- **Causal**: 원인/결과 분석 (예: "임진왜란이 발생한 원인은?")
- **Comparative**: 2개 엔티티 비교 (예: "임진왜란과 병자호란의 공통점은?")
- **Deep Analysis**: 심층 분석 (예: "세종대왕의 업적이 조선 사회에 미친 영향은?")

**사용 예시**:

```python
PersonaQueryBuilder.save_to_json("data/test_queries.json")
# → 40개 질문이 담긴 JSON 파일 생성
```

#### **Property Groups 매핑 가이드**

**32개 사용 가능한 그룹**:

- "속성", "문서", "연결관계", "연도", "소속", "인과관계", "장소", "참여", "부분", "포함", "직위", "기간중", "시기", "재위", "법률", "시행", "지휘", "변경", "역할", "조사", "위치", "세금", "협력", "저술", "시대", "반대", "설립", "날짜", "복원", "승진", "외교", "교육"

**Query Type별 매핑 전략**:

| Query Type        | 주요 그룹                    | 예시                                                                            |
| ----------------- | ---------------------------- | ------------------------------------------------------------------------------- |
| **Factual**       | 연도, 시기, 장소, 직위, 재위 | "세종대왕이 훈민정음을 창제한 시기는?" → ["연도", "시기", "설립"]               |
| **Causal**        | 인과관계 + 도메인 그룹       | "임진왜란이 발생한 원인은?" → ["인과관계"]                                      |
| **Comparative**   | 연결관계 + 비교 대상 그룹    | "임진왜란과 병자호란의 공통점은?" → ["연결관계", "지휘"]                        |
| **Deep Analysis** | 복합 그룹 조합               | "세종대왕의 업적이 조선 사회에 미친 영향은?" → ["속성", "인과관계", "연결관계"] |

**매핑 원칙**:

1. **핵심 그룹 우선**: 각 query_type의 특성을 반영하는 핵심 그룹 선택
2. **도메인 그룹 추가**: 질문 내용에 맞는 도메인별 그룹 추가
3. **2-3개 그룹 권장**: 너무 많으면 평가가 모호해짐

#### 테스트 쿼리 검증 결과

**검증 완료**: 40개 쿼리 모두 Intent-aware 평가에 적합

**Query Type별 분포**:

- Factual: 10개 (단순 사실 확인, 수렴 노드 불필요)
- Causal: 10개 (인과관계 추론, 수렴 노드 중요)
- Comparative: 10개 (2개 엔티티 비교, 수렴 노드 매우 중요)
- Deep Analysis: 10개 (심층 분석, Intent 보존 중요)

**검증 포인트**:

- ✅ Query Type별 분포 균형 (각 10개씩)
- ✅ Intent 키워드 명확성 (각 타입별 특성 반영)
- ✅ 수렴 노드 중요도 분포 적절 (query_type별 차별화)
- ✅ 엔티티 다양성 (인물, 사건, 장소, 개념)
- ✅ 2-Entity 비교 충분 (Comparative 쿼리 10개 모두 2개 이상 엔티티 비교)

**전체 평가: ⭐⭐⭐⭐⭐ (5/5)** - Intent-Aware 평가에 매우 적합

---

### 3️⃣ `evaluators/` - 평가 메트릭 구현

#### `intent_aware_evaluator.py`

**역할**: Query type에 따라 메트릭에 다른 가중치를 적용하는 평가자

#### `PropertyGroupSelectionEvaluator`

**역할**: LangGraph가 선택한 property groups와 예상 그룹의 일치도 평가

**사용 예시**:

```python
from ragas.ontology_evaluate.evaluators import PropertyGroupSelectionEvaluator

evaluator = PropertyGroupSelectionEvaluator()

# LangGraph 실행 결과
state_output = {
    "selected_property_groups": ["연도", "설립", "참여"]
}

# 예상 그룹 (test_queries.json에서)
expected_groups = ["연도", "시기", "설립"]

result = evaluator.evaluate(state_output, expected_groups)
print(f"Property Group Selection Score: {result['score']:.3f}")  # 0.667
print(f"Matched: {result['matched_groups']}")     # ["연도", "설립"]
print(f"Missing: {result['missing_groups']}")     # ["시기"]
print(f"Extra: {result['extra_groups']}")         # ["참여"]
```

**점수 계산**: Jaccard Index = `교집합 / 합집합`

- 교집합: ["연도", "설립"] = 2개
- 합집합: ["연도", "시기", "설립", "참여"] = 4개
- 점수: 2/4 = 0.5

#### `IntentWeightConfig`

```python
@dataclass
class IntentWeightConfig:
    tbox_consistency_weight: float
    intent_preservation_weight: float
    relation_coherence_weight: float
    triple_validity_weight: float
    evidence_diversity_weight: float
    convergence_utilization_weight: float
```

##### `IntentAwareEvaluator`

**메서드**:

- `evaluate(query_type, raw_metrics)`: Query type에 따라 가중치 적용 후 최종 점수 계산

**가중치 프리셋**:

```python
INTENT_WEIGHT_PRESETS = {
    "factual": IntentWeightConfig(
        convergence_utilization_weight=0.5,  # 낮음
        tbox_consistency_weight=1.5,         # 높음
        ...
    ),
    "causal": IntentWeightConfig(
        convergence_utilization_weight=1.5,  # 매우 높음
        relation_coherence_weight=1.3,       # 높음
        ...
    ),
    "comparative": IntentWeightConfig(
        convergence_utilization_weight=1.6,  # 가장 높음
        evidence_diversity_weight=1.4,       # 매우 높음
        ...
    ),
    "deep_analysis": IntentWeightConfig(
        intent_preservation_weight=1.5,      # 가장 높음
        relation_coherence_weight=1.4,       # 높음
        ...
    )
}
```

**출력**:

```python
{
    "query_type": "causal",
    "raw_metrics": {...},
    "weights": {
        "convergence_utilization": 0.234,  # 정규화된 가중치
        "intent_preservation": 0.218,
        ...
    },
    "weighted_metrics": {
        "convergence_utilization": 0.187,  # raw × weight
        "intent_preservation": 0.185,
        ...
    },
    "final_score": 0.847  # sum(weighted_metrics)
}
```

**사용 예시**:

```python
from ragas.ontology_evaluate.evaluators.intent_aware_evaluator import IntentAwareEvaluator

evaluator = IntentAwareEvaluator()

raw_metrics = {
    "tbox_consistency": 0.90,
    "intent_preservation": 0.85,
    "relation_coherence": 0.88,
    "triple_validity": 0.82,
    "evidence_diversity": 0.75,
    "convergence_utilization": 0.80
}

result = evaluator.evaluate("causal", raw_metrics)
print(f"Final Score: {result['final_score']:.3f}")  # 0.847
```

---

#### `l1_schema_compliance.py`

**클래스**: `TBoxConsistencyEvaluator`

**역할**: 온톨로지 스키마(TBox) 위반 검증

**평가 대상**:

- Stage 3 (Semantic Expander)에서 생성된 확장 경로
- Stage 5 (Path Evidence Aggregator)에서 추출된 triple

**검증 항목**:

```python
# 예: (Person) -[participatesIn]-> (Event)
# domain: Person, range: Event 일치해야 함

# 위반 예시:
(Person) -[birthPlace]-> (Event)  # ✗ range는 Place여야 함
```

**출력**:

```python
{
    "score": 0.95,  # 1.0 - (violations / total_triples)
    "violations": [
        {
            "subject": "Person",
            "predicate": "birthPlace",
            "object": "Event",
            "violation_type": "range_mismatch",
            "expected": "Place",
            "actual": "Event"
        }
    ],
    "total_triples": 20,
    "violation_count": 1
}
```

---

#### `l2_path_quality.py`

**클래스 1**: `IntentPreservationEvaluator`

**역할**: 각 확장 hop에서 질문 의도가 유지되는지 평가 (LLM Judge 사용)

**평가 대상**: Stage 3의 각 expansion hop

**Intent 상태**:

- **Preserve (1.0)**: 의도 유지
- **Enrich (1.2)**: 의도 심화 (보너스)
- **Drift (0.5)**: 의도 전환 (페널티)
- **Hallucinated (0.0)**: 의도 무관 (실패)

**예시**:

```python
# 질문: "임진왜란의 원인은?"
# Hop 1: "임진왜란" → "명나라 요청" (Enrich: 1.2)
# Hop 2: "임진왜란" → "이순신의 식습관" (Hallucinated: 0.0)
# → 평균: (1.2 + 0.0) / 2 = 0.6
```

**출력**:

```python
{
    "score": 0.6,
    "hops": [
        {
            "source_entity": "임진왜란",
            "target_entity": "명나라 요청",
            "expansion_method": "causal_chain",
            "intent_state": "Enrich",
            "score": 1.2
        },
        ...
    ]
}
```

---

**클래스 2**: `RelationCoherenceEvaluator`

**역할**: 사용된 relation이 질문 의도와 의미적으로 일관되는지 평가

**평가 대상**: Stage 4의 5개 Thread에서 사용된 relation

**Valid Relations 예시**:

```python
VALID_RELATIONS_BY_INTENT = {
    "원인": ["causedBy", "leadsTo", "influences"],
    "업적": ["built", "established", "achieved", "founded"],
    "결과": ["leadsTo", "causes", "affects"]
}
```

**예시**:

```python
# 질문: "세종의 업적"
# Thread 1: [built, established, founded] → 3/3 = 1.0 ✓
# Thread 2: [diedIn, marriedTo] → 0/2 = 0.0 ✗
```

**출력**:

```python
{
    "score": 0.6,  # coherent_relations / total_relations
    "coherent_relations": 3,
    "total_relations": 5,
    "incoherent_relations": [
        {
            "predicate": "marriedTo",
            "entity": "세종대왕",
            "value": "소헌왕후",
            "thread_type": "outgoing_relations"
        }
    ]
}
```

---

#### `l3_terminal_knowledge.py`

**클래스 1**: `TerminalTripleValidityEvaluator`

**역할**: 최종 도달한 triple이 질문에 기여하는지 평가 (LLM Judge 사용)

**평가 대상**: Stage 5의 top 15 evidences

**Triple 기여도**:

- **기여함 (1.0)**: 질문에 직접 답함
- **간접 기여 (0.5)**: 배경 정보 제공
- **무관함 (0.0)**: 답변에 도움 안 됨

**예시**:

```python
# 질문: "세종대왕의 업적"
# Triple 1: (세종대왕) -[built]-> (경복궁) → 기여함 (1.0) ✓
# Triple 2: (세종대왕) -[marriedTo]-> (소헌왕후) → 무관함 (0.0) ✗
```

**출력**:

```python
{
    "score": 0.67,  # (1.0 + 0.5 + 0.0) / 3
    "triple_evaluations": [
        {
            "subject": "세종대왕",
            "predicate": "built",
            "object": "경복궁",
            "contribution": "기여함",
            "score": 1.0
        },
        ...
    ]
}
```

---

**클래스 2**: `EvidenceDiversityEvaluator`

**역할**: 5개 Thread에서 고르게 evidences가 선택되었는지 평가 (Shannon Entropy 사용)

**평가 대상**: Stage 5의 evidences 분포

**Shannon Entropy 계산**:

```python
# Thread 분포: [7, 4, 2, 1, 1] (총 15개)
# Entropy = -Σ(p * log2(p))
# Diversity Score = Entropy / log2(5)  # 정규화
```

**문제 상황**:

```python
# 불균형 예시:
Thread 1 (outgoing_relations): 14개
Thread 2 (incoming_relations): 1개
Thread 3~5: 0개
→ Diversity Score ≈ 0.3 (낮음)

# 균형 예시:
Thread 1: 3개, Thread 2: 3개, Thread 3: 3개, Thread 4: 3개, Thread 5: 3개
→ Diversity Score = 1.0 (최고)
```

**출력**:

```python
{
    "score": 0.85,
    "thread_distribution": {
        "outgoing_relations": 7,
        "incoming_relations": 4,
        "entity_properties": 2,
        "connected_entities": 1,
        "type_and_summary": 1
    },
    "entropy": 1.97,
    "max_entropy": 2.32
}
```

---

**클래스 3**: `ConvergenceUtilizationEvaluator`

**역할**: 수렴 노드가 답변에 활용되었는지 평가 (query_type별 가중치)

**평가 대상**: Stage 5의 convergence_nodes, Stage 6의 final_answer

**query_type별 가중치**:

```python
IMPORTANCE_WEIGHTS = {
    "causal": 1.5,         # 인과관계 → 수렴 노드 매우 중요
    "deep_analysis": 1.3,  # 심층 분석 → 수렴 노드 중요
    "comparative": 1.2,    # 비교 → 수렴 노드 중요
    "factual": 1.0         # 사실 확인 → 수렴 노드 덜 중요
}
```

**계산 방식**:

```python
# 수렴 노드: ["명나라", "일본"]
# 답변에 "명나라"만 언급됨
utilization_rate = 1 / 2 = 0.5

# query_type = "causal" → weight = 1.5
final_score = 0.5 * 1.5 = 0.75 (1.0 상한)
```

**출력**:

```python
{
    "score": 0.75,
    "convergence_nodes": 2,
    "mentioned_nodes": 1,
    "utilization_rate": 0.5,
    "importance_weight": 1.5
}
```

---

### 4️⃣ `utils/` - 유틸리티

#### `llm_judge.py`

**클래스**: `LLMJudge`

**역할**: GPT-4를 Judge로 사용하여 평가

**메서드**:

1. `evaluate_intent_preservation()`: Intent 상태 평가

```python
llm_judge.evaluate_intent_preservation(
    query="임진왜란의 원인은?",
    query_intent="원인 분석",
    source_entity="임진왜란",
    target_entity="명나라 요청",
    expansion_method="causal_chain"
)
# → ("Enrich", "원인의 배경을 탐구하여 의도를 심화시킴")
```

2. `evaluate_triple_contribution()`: Triple 기여도 평가

```python
llm_judge.evaluate_triple_contribution(
    query="세종대왕의 업적은?",
    query_intent="업적 조회",
    subject="세종대왕",
    predicate="built",
    obj="경복궁"
)
# → ("기여함", "건설 업적에 직접적으로 답함")
```

**사용 모델**: `gpt-4o` (기본값)

---

#### `result_analyzer.py`

**클래스**: `ResultAnalyzer`

**역할**: Ablation 실험 결과 분석

**메서드**:

1. `calculate_metric_averages()`: 실험별 평균 점수 계산

```python
analyzer = ResultAnalyzer("data/results/semantic_expander_ablation.json")
df = analyzer.calculate_metric_averages()

# 출력 예시:
#                                  intent_preservation  terminal_triple_validity
# semantic_expander_baseline                    0.65                      0.72
# semantic_expander_temporal_only               0.78                      0.85
# semantic_expander_full                        0.92                      0.94
```

2. `compare_to_baseline()`: Baseline 대비 성능 비교

```python
diff_df = analyzer.compare_to_baseline("semantic_expander_baseline")

# 출력 예시:
#                                  intent_preservation  terminal_triple_validity
# semantic_expander_temporal_only              +0.13                     +0.13
# semantic_expander_full                       +0.27                     +0.22
```

3. `generate_report()`: 분석 리포트 생성

```python
analyzer.generate_report("data/results/report.txt")

# 출력:
# ======================================================================
# Ablation Study 결과 분석
# ======================================================================
# 총 실험 개수: 30
#
# 실험별 평균 점수:
# ...
#
# 메트릭별 최고 성능 실험:
#   - intent_preservation: semantic_expander_full (0.92)
#   - terminal_triple_validity: semantic_expander_full (0.94)
```

---

### 5️⃣ `experiments/` - 실험 실행 스크립트

#### `run_baseline.py`

**역할**: Phase 1 (Baseline Ablation Study) 실행

**주요 함수**:

1. `load_queries()`: 테스트 질문 로드
2. `evaluate_state()`: GraphState에 대해 모든 평가 메트릭 실행
3. `main()`: 실험 실행 메인 함수

**사용 예시**:

```bash
python -m backend.ragas.ontology_evaluate.experiments.run_baseline \
    --group semantic_expander \
    --limit 5
```

**실행 흐름**:

```
1. 테스트 질문 로드 (40개)
2. LLM Judge 초기화 (GPT-4)
3. 온톨로지 스키마 로드
4. Ablation 설정 생성 (6개)
5. 각 설정 × 각 질문 실행:
   - LangGraph 실행
   - 6개 evaluator로 평가
   - 결과 저장
6. JSON 파일 저장
```

---

#### `run_grid_search.py`

**역할**: Phase 2 (Grid Search 가중치 최적화) 실행

**주요 클래스**: `GridSearchRunner`

**메서드**:

- `generate_semantic_weight_grid()`: Semantic Expander 가중치 조합 생성 (4^4 = 256개)
- `generate_thread_weight_grid()`: Thread 가중치 조합 생성 (4^5 = 1024개)
- `run_semantic_weight_search()`: Semantic 가중치 탐색
- `run_thread_weight_search()`: Thread 가중치 탐색

**가중치 범위**:

```python
SEMANTIC_WEIGHTS = {
    "temporal": [0.5, 1.0, 1.5, 2.0],
    "causal_chain": [0.5, 1.0, 1.5, 2.0],
    "pgvector": [0.5, 1.0, 1.5, 2.0],
    ...
}
```

**사용 예시**:

```bash
python experiments/run_grid_search.py \
    --baseline-results data/results/semantic_expander_ablation.json \
    --search-type semantic
```

---

## 4. 요약

### 핵심 원칙

> **"기존 LangGraph 코드는 최소한만 수정하고, 평가는 별도로 실행한다"**

### 코드 역할 요약

| 파일                             | 역할             | 입력                 | 출력                    |
| -------------------------------- | ---------------- | -------------------- | ----------------------- |
| `baseline_ablation.py`           | 실험 설정 생성   | 없음                 | `AblationConfig` 리스트 |
| `build_queries_persona.py`       | 테스트 질문 생성 | 없음                 | `test_queries.json`     |
| `evaluators/l1_*.py`             | TBox 검증        | `GraphState`         | 점수 (0~1)              |
| `evaluators/l2_*.py`             | 경로 품질 평가   | `GraphState`         | 점수 (0~1.2)            |
| `evaluators/l3_*.py`             | 최종 지식 평가   | `GraphState`         | 점수 (0~1)              |
| `utils/llm_judge.py`             | LLM 평가         | 질문, 엔티티, Triple | 판단, 근거              |
| `utils/result_analyzer.py`       | 결과 분석        | JSON 결과 파일       | DataFrame, 리포트       |
| `experiments/run_baseline.py`    | 실험 실행        | 질문, 설정           | JSON 결과 파일          |
| `experiments/run_grid_search.py` | 가중치 최적화    | Baseline 결과        | 최적 가중치             |

### 데이터 흐름

```
질문 생성 (build_queries_persona.py)
    ↓
test_queries.json
    ↓
실험 설정 생성 (baseline_ablation.py)
    ↓
LangGraph 실행 (run_baseline.py)
    ↓
GraphState
    ↓
평가 (evaluators/)
    ↓
결과 JSON
    ↓
분석 (result_analyzer.py)
    ↓
인사이트 & 가중치 최적화
```
