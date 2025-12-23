# HistoK Ontology RAG 평가 프레임워크

온톨로지 기반 RAG 시스템의 평가 및 가중치 최적화를 위한 코드

## 디렉토리 구조

```
ontology_evaluate/
├── README.md                          # 이 파일
├── GUIDE.md                           # 구현 가이드 (LangGraph 연동 방법)
├── REDESIGN_PROPOSAL.md               # test_config 및 평가 프레임워크 재설계 제안
├── INTENT_AWARE_USAGE.md              # Intent-aware 평가 사용 가이드
├── INTENT_AWARE_QUERY_VALIDATION.md   # 테스트 쿼리 검증 보고서
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

1. **Semantic Expander 실험** (6개 설정):
   - Baseline: 모든 확장 비활성화
   - Temporal Only
   - Category Only
   - Causal Chain Only
   - Pgvector Only
   - All Enabled (Full)

2. **Thread 실험** (6개 설정):
   - Baseline: 1개 Thread만 (outgoing_relations)
   - Leave-One-Out: 각 Thread 하나씩 제거 (5개)

3. **Entity Boost 실험** (4개 설정):
   - exact_match, partial_match, normalized_match, penalty_match

### Phase 2: Grid Search (Phase 1 이후)

Phase 1에서 필요성이 검증된 요소들의 가중치 최적화

## 사용법

### 1. 테스트 질문 생성

```bash
cd backend/ragas/ontology_evaluate
python build_queries_persona.py
```

생성된 질문: `data/test_queries.json` (40개)
- factual: 10개
- causal: 10개
- comparative: 10개
- deep_analysis: 10개

### 2. Baseline Ablation Study 실행

```bash
# Semantic Expander 실험 (Intent-aware 평가 활성화, 기본값)
python experiments/run_baseline.py --group semantic_expander --queries data/test_queries.json

# Thread 실험
python experiments/run_baseline.py --group thread --queries data/test_queries.json

# 모든 실험
python experiments/run_baseline.py --group all --queries data/test_queries.json

# Intent-aware 평가 비활성화 (Raw 메트릭만 사용)
python experiments/run_baseline.py --group semantic_expander --queries data/test_queries.json --no-intent-aware

# 디버깅용 (5개 질문만)
python experiments/run_baseline.py --group semantic_expander --queries data/test_queries.json --limit 5
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
python -c "from utils.result_analyzer import ResultAnalyzer; analyzer = ResultAnalyzer('data/results/semantic_expander_ablation.json'); analyzer.generate_report()"
```

### 4. Grid Search (Phase 2)

```bash
# Semantic Expander 가중치 최적화
python experiments/run_grid_search.py --baseline-results data/results/semantic_expander_ablation.json --search-type semantic

# Thread 가중치 최적화
python experiments/run_grid_search.py --baseline-results data/results/thread_ablation.json --search-type thread

# 모든 가중치 최적화
python experiments/run_grid_search.py --baseline-results data/results/all_ablation.json --search-type all
```

## 평가 메트릭

| Level | 메트릭 | 구현 파일 | 자동/LLM Judge |
|-------|--------|----------|----------------|
| L1 | TBox Consistency | `evaluators/l1_schema_compliance.py` | 자동 |
| L2 | Intent Preservation | `evaluators/l2_path_quality.py` | LLM Judge |
| L2 | Relation Coherence | `evaluators/l2_path_quality.py` | 자동 |
| L3 | Terminal Triple Validity | `evaluators/l3_terminal_knowledge.py` | LLM Judge |
| L3 | Evidence Diversity | `evaluators/l3_terminal_knowledge.py` | 자동 (Shannon Entropy) |
| L3 | Convergence Utilization | `evaluators/l3_terminal_knowledge.py` | 반자동 (query_type별) |
| **Intent-Aware** | **Query Type별 가중 평가** | `evaluators/intent_aware_evaluator.py` | **자동 (가중치 적용)** |

### 평가 메트릭 상세

#### L1: Ontology Schema Compliance
- **TBox Consistency**: 확장 경로가 온톨로지 스키마(domain/range)를 위반하지 않는지 검증
- 점수: `1.0 - (violations / total_triples)`

#### L2: Expansion Path Quality
- **Intent Preservation**: 각 hop에서 질문 의도 유지 여부 (Preserve: 1.0, Enrich: 1.2, Drift: 0.5, Hallucinated: 0.0)
- **Relation Coherence**: relation이 질문 의도와 의미적으로 일관되는지 평가

#### L3: Terminal Knowledge Contribution
- **Terminal Triple Validity**: 최종 도달한 triple이 질문에 기여하는지 평가 (기여함: 1.0, 간접: 0.5, 무관: 0.0)
- **Evidence Diversity**: 5개 Thread에서 고르게 선택되었는지 Shannon Entropy로 평가
- **Convergence Utilization**: 수렴 노드가 답변에 활용되었는지, query_type별 가중치 적용
  - causal: 1.5, deep_analysis: 1.3, comparative: 1.2, factual: 1.0

#### Intent-Aware Evaluation (NEW)
- **Query Type별 가중 평가**: 각 query_type에 따라 메트릭에 다른 가중치를 적용
- **Query Type별 가중치**:

| Query Type | 수렴 노드 중요도 | Intent 보존 중요도 | Schema 준수 중요도 | 특징 |
|------------|------------------|-------------------|-------------------|------|
| **Factual** | 0.075 (낮음) | 0.194 (높음) | 0.224 (가장 높음) | 단순 사실 확인 |
| **Causal** | 0.234 (가장 높음) | 0.218 (매우 높음) | 0.156 (중간) | 인과관계 추론 |
| **Comparative** | 0.253 (가장 높음) | 0.205 (높음) | 0.158 (중간) | 2개 엔티티 비교 |
| **Deep Analysis** | 0.197 (높음) | 0.227 (가장 높음) | 0.152 (중간) | 심층 분석 |

- **사용 예시**:
  ```bash
  # Intent-aware 평가 활성화 (기본값)
  python experiments/run_baseline.py --group semantic_expander

  # Intent-aware 평가 비활성화
  python experiments/run_baseline.py --group semantic_expander --no-intent-aware
  ```
- **상세 가이드**: [INTENT_AWARE_USAGE.md](./INTENT_AWARE_USAGE.md)

## 참고 문서

### 평가 프레임워크
- [GUIDE.md](./GUIDE.md): 구현 가이드 (LangGraph 연동 방법, 단계별 실행)
- [INTENT_AWARE_USAGE.md](./INTENT_AWARE_USAGE.md): Intent-aware 평가 사용 가이드
- [INTENT_AWARE_QUERY_VALIDATION.md](./INTENT_AWARE_QUERY_VALIDATION.md): 테스트 쿼리 검증 보고서
- [REDESIGN_PROPOSAL.md](./REDESIGN_PROPOSAL.md): test_config 재설계 제안 및 향후 계획

### 상세 문서
- `../../langgraph_fuseki/docs/ontology_rag_evaluation.md`: 평가 프레임워크 상세 설명
- `../../langgraph_fuseki/docs/scoring_methodology.md`: 점수 계산 방법론

## 핵심 원칙

> **"우리는 정답(answer)을 평가하지 않고, 추론 행위(reasoning behavior)를 평가한다"**

이것이 Ground Truth 없는 평가의 이론적 근거입니다.
