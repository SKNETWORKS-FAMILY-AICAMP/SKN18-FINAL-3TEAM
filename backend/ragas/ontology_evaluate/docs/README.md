# HistoK Ontology RAG 평가 프레임워크

온톨로지 기반 RAG 시스템의 평가 및 가중치 최적화를 위한 코드

## 디렉토리 구조

```
ontology_evaluate/
├── README.md                          # 이 파일 (개요 및 빠른 시작)
├── GUIDE.md                           # 구현 가이드 (LangGraph 연동 방법, Intent-aware 평가 사용법 포함)
├── WEIGHT_CALCULATION_GUIDE.md        # 가중치 계산 방법론 및 실험 설계
├── REDESIGN_PROPOSAL.md               # 향후 계획 (Thinking Trace 구현 등)
├── baseline_ablation.py               # Ablation Study 설정 생성기
├── build_queries_persona.py           # Intent별 테스트 질문 생성
├── evaluators/                        # 평가 메트릭 구현
│   ├── __init__.py
│   ├── intent_aware_evaluator.py      # Intent-aware 평가자 (query_type별 가중치)
│   ├── l1_schema_compliance.py        # L1: TBox Consistency
│   ├── l2_path_quality.py             # L2: Intent Preservation, Relation Coherence
│   └── l3_terminal_knowledge.py       # L3: Terminal Triple Validity, Evidence Diversity, Convergence
├── utils/                             # 유틸리티
│   ├── __init__.py
│   ├── llm_judge.py                   # LLM-as-Judge 구현 (GPT-4)
│   └── result_analyzer.py             # 결과 분석 도구
├── experiments/                       # 실험 스크립트
│   ├── __init__.py
│   ├── run_baseline.py                # Phase 1: Ablation Study 실행 (Intent-aware 지원)
│   └── run_grid_search.py             # Phase 2: Grid Search 실행
└── data/                              # 테스트 데이터셋
    ├── test_queries.json              # 40개 Intent별 테스트 질문
    └── results/                       # 실험 결과 저장
```

## 평가 프레임워크

상세 설명: `../../langgraph_fuseki/docs/ontology_rag_evaluation.md`

## 실험 Phase

### Phase 1: Baseline Ablation Study

각 요소를 비활성화하여 기여도 측정:

1. **Semantic Expander 실험** (5개 설정):

   - Baseline: 모든 확장 비활성화
   - Temporal Only (±10년 시간적 확장)
   - Causal Chain Only (1-3 hop 인과관계 체인)
   - Pgvector Only (벡터 유사도 기반)
   - All Enabled (Full)

2. **Thread 실험** (6개 설정):

   - Baseline: 1개 Thread만 (outgoing_relations)
   - Leave-One-Out: 각 Thread 하나씩 제거 (5개)

3. **Entity Boost 실험** (4개 설정):
   - exact_match, partial_match, normalized_match, penalty_match

### Phase 2: Grid Search (Phase 1 이후)

Phase 1에서 필요성이 검증된 요소들의 가중치 최적화

## 사용법

## 사용법

### 1. 테스트 질문 생성

```bash
# 방법 1: 직접 모듈 실행
python -m backend.ragas.ontology_evaluate.build_queries_persona

# 방법 2: 패키지 실행 (동일한 결과)
python -m backend.ragas.ontology_evaluate
```

생성된 질문: `backend/ragas/ontology_evaluate/data/test_queries.json` (40개)

- factual: 10개
- causal: 10개
- comparative: 10개
- deep_analysis: 10개

**질문 구조** (property_groups.json 기반):

```json
{
  "query": "세종대왕이 훈민정음을 창제한 시기는 언제인가?",
  "query_type": "factual",
  "intent_keywords": ["연도", "시기", "설립"], // property_groups 그룹명
  "expected_entities": ["세종", "훈민정음"],
  "expected_property_groups": ["연도", "시기", "설립"],
  "difficulty": "easy",
  "description": "단순 사실 확인 - 시간 정보"
}
```

### 2. Baseline Ablation Study 실행

```bash
# 방법 1: 직접 모듈 실행
python -m backend.ragas.ontology_evaluate.experiments.run_baseline --group semantic_expander

# 방법 2: 패키지 실행 (동일한 결과)  
python -m backend.ragas.ontology_evaluate.experiments --group semantic_expander

# 다른 실험 그룹들
python -m backend.ragas.ontology_evaluate.experiments.run_baseline --group thread
python -m backend.ragas.ontology_evaluate.experiments.run_baseline --group all

# 옵션들
python -m backend.ragas.ontology_evaluate.experiments.run_baseline --group semantic_expander --no-intent-aware  # Intent-aware 평가 비활성화
python -m backend.ragas.ontology_evaluate.experiments.run_baseline --group semantic_expander --limit 5  # 디버깅용 (5개 질문만)
```

**출력 예시** (Intent-aware 평가 활성화 시):

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

### 3. 결과 분석

```bash
python -c "
from backend.ragas.ontology_evaluate.utils.result_analyzer import ResultAnalyzer
analyzer = ResultAnalyzer('backend/ragas/ontology_evaluate/data/results/semantic_expander_ablation.json')
analyzer.generate_report()
"
```

### 4. Grid Search (Phase 2)

```bash
# Semantic Expander 가중치 최적화
python -m backend.ragas.ontology_evaluate.experiments.run_grid_search --baseline-results backend/ragas/ontology_evaluate/data/results/semantic_expander_ablation.json --search-type semantic

# Thread 가중치 최적화
python -m backend.ragas.ontology_evaluate.experiments.run_grid_search --baseline-results backend/ragas/ontology_evaluate/data/results/thread_ablation.json --search-type thread

# 모든 가중치 최적화
python -m backend.ragas.ontology_evaluate.experiments.run_grid_search --baseline-results backend/ragas/ontology_evaluate/data/results/all_ablation.json --search-type all
```

## 평가 메트릭

| Level            | 메트릭                     | 구현 파일                              | 자동/LLM Judge         |
| ---------------- | -------------------------- | -------------------------------------- | ---------------------- |
| L1               | TBox Consistency           | `evaluators/l1_schema_compliance.py`   | 자동                   |
| L2               | Intent Preservation        | `evaluators/l2_path_quality.py`        | LLM Judge              |
| L2               | Relation Coherence         | `evaluators/l2_path_quality.py`        | 자동                   |
| L2               | Property Group Selection   | `evaluators/l2_path_quality.py`        | 자동 (Jaccard Index)   |
| L3               | Terminal Triple Validity   | `evaluators/l3_terminal_knowledge.py`  | LLM Judge              |
| L3               | Evidence Diversity         | `evaluators/l3_terminal_knowledge.py`  | 자동 (Shannon Entropy) |
| L3               | Convergence Utilization    | `evaluators/l3_terminal_knowledge.py`  | 반자동 (query_type별)  |
| **Intent-Aware** | **Query Type별 가중 평가** | `evaluators/intent_aware_evaluator.py` | **자동 (가중치 적용)** |

### 평가 메트릭 상세

#### L1: Ontology Schema Compliance

- **TBox Consistency**: 확장 경로가 온톨로지 스키마(domain/range)를 위반하지 않는지 검증
- 점수: `1.0 - (violations / total_triples)`

#### L2: Expansion Path Quality

- **Intent Preservation**: 각 hop에서 질문 의도 유지 여부 (Preserve: 1.0, Enrich: 1.2, Drift: 0.5, Hallucinated: 0.0)
- **Relation Coherence**: relation이 질문 의도와 의미적으로 일관되는지 평가
- **Property Group Selection**: LangGraph가 선택한 property groups와 예상 그룹의 일치도 평가
  - 점수: Jaccard Index = `교집합 / 합집합`
  - 예: 선택된 ["연도", "설립"], 예상된 ["연도", "시기", "설립"] → 점수: 2/3 = 0.67

#### L3: Terminal Knowledge Contribution

- **Terminal Triple Validity**: 최종 도달한 triple이 질문에 기여하는지 평가 (기여함: 1.0, 간접: 0.5, 무관: 0.0)
- **Evidence Diversity**: 5개 Thread에서 고르게 선택되었는지 Shannon Entropy로 평가
- **Convergence Utilization**: 수렴 노드가 답변에 활용되었는지, query_type별 가중치 적용
  - causal: 1.5, deep_analysis: 1.3, comparative: 1.2, factual: 1.0

#### Intent-Aware Evaluation (NEW)

- **Query Type별 가중 평가**: 각 query_type에 따라 메트릭에 다른 가중치를 적용
- **Query Type별 가중치**:

| Query Type        | 수렴 노드 중요도  | Intent 보존 중요도 | Schema 준수 중요도 | 특징            |
| ----------------- | ----------------- | ------------------ | ------------------ | --------------- |
| **Factual**       | 0.075 (낮음)      | 0.194 (높음)       | 0.224 (가장 높음)  | 단순 사실 확인  |
| **Causal**        | 0.234 (가장 높음) | 0.218 (매우 높음)  | 0.156 (중간)       | 인과관계 추론   |
| **Comparative**   | 0.253 (가장 높음) | 0.205 (높음)       | 0.158 (중간)       | 2개 엔티티 비교 |
| **Deep Analysis** | 0.197 (높음)      | 0.227 (가장 높음)  | 0.152 (중간)       | 심층 분석       |

- **사용 예시**:

  ```bash
  # Intent-aware 평가 활성화 (기본값)
  python experiments/run_baseline.py --group semantic_expander

  # Intent-aware 평가 비활성화
  python experiments/run_baseline.py --group semantic_expander --no-intent-aware
  ```

- **상세 가이드**: [GUIDE.md](./GUIDE.md)의 "Step 7: Intent-Aware 평가 실행" 섹션 참고

## 참고 문서

### 평가 프레임워크

- [GUIDE.md](./GUIDE.md): 구현 가이드 (LangGraph 연동 방법, 단계별 실행, Intent-aware 평가 사용법 포함)
- [WEIGHT_CALCULATION_GUIDE.md](./WEIGHT_CALCULATION_GUIDE.md): 가중치 계산 방법론 및 실험 설계
- [REDESIGN_PROPOSAL.md](./REDESIGN_PROPOSAL.md): 향후 계획 (Thinking Trace 구현 등)

### 상세 문서

- `../../langgraph_fuseki/docs/ontology_rag_evaluation.md`: 평가 프레임워크 상세 설명
- `../../langgraph_fuseki/docs/scoring_methodology.md`: 점수 계산 방법론

## 핵심 원칙

> **"우리는 정답(answer)을 평가하지 않고, 추론 행위(reasoning behavior)를 평가한다"**

이것이 Ground Truth 없는 평가의 이론적 근거입니다.
