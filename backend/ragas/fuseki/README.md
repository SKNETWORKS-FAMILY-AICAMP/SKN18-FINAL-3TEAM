# Fuseki RAG System - Automated RAGAS Evaluation

이 디렉토리는 Fuseki 기반 RAG 시스템의 자동화된 RAGAS 평가를 수행합니다.

## 개요

**목적**: 20가지 노드 조합에 대해 RAGAS 평가를 자동으로 수행하여 최적의 가중치를 찾습니다.

**평가 조합**:
- **Semantic Expander (4가지)**: 의미론적 엔티티 확장 방법
  - `temporal`: 시간적 맥락 확장 (±10년)
  - `category`: 카테고리 기반 확장
  - `causal_chain`: 인과관계 체인 확장
  - `pgvector`: 벡터 유사도 확장
- **Aggregator (5가지)**: Parallel Knowledge Retrieval Thread
  - `outgoing_relations`: 나가는 관계
  - `incoming_relations`: 들어오는 관계
  - `entity_properties`: 엔티티 속성
  - `connected_entities`: 연결된 엔티티
  - `type_and_summary`: 타입과 요약
- **총 조합**: 4 × 5 = 20가지

**평가 메트릭**:
1. Context Entities Recall - 필요한 엔티티가 컨텍스트에 포함되었는지
2. Noise Sensitivity (Context Precision) - 노이즈(무관한 정보) 필터링 성능
3. Faithfulness - 답변이 컨텍스트에 충실한지
4. Context Relevance - 컨텍스트의 관련성

## 파일 구조

```
backend/ragas/fuseki/
├── README.md                    # 이 파일
├── config_manager.py            # 노드 조합 설정 관리
├── ragas_metrics.py             # RAGAS 메트릭 로더
├── automated_test_runner.py    # 자동화 테스트 러너
├── results_analyzer.py          # 결과 분석 및 리포트 생성
├── run_tests.sh                 # 테스트 실행 스크립트
└── results/                     # 결과 저장 디렉토리
    ├── all_results_YYYYMMDD_HHMMSS.json
    ├── summary_YYYYMMDD_HHMMSS.json
    ├── all_results_YYYYMMDD_HHMMSS_ranked.csv
    └── all_results_YYYYMMDD_HHMMSS_report.txt
```

## 설치

### 필수 패키지

```bash
pip install ragas pandas
```

### 선택 패키지 (시각화)

```bash
pip install matplotlib seaborn
```

## 사용 방법

### 1. 전체 테스트 실행 (20가지 조합)

```bash
# 기본 실행
python backend/ragas/fuseki/automated_test_runner.py

# 또는 스크립트 사용
bash backend/ragas/fuseki/run_tests.sh
```

### 2. 옵션을 사용한 실행

```bash
# 질문 수 제한 (각 조합당 5개 질문만)
python backend/ragas/fuseki/automated_test_runner.py --limit 5

# 디버그 모드
python backend/ragas/fuseki/automated_test_runner.py --debug

# Persona 지정
python backend/ragas/fuseki/automated_test_runner.py --persona foreigner_culture_history

# 중간 저장 주기 설정 (2개 조합마다 저장)
python backend/ragas/fuseki/automated_test_runner.py --save-every 2

# 조합
python backend/ragas/fuseki/automated_test_runner.py \
  --persona foreigner_culture_history \
  --limit 10 \
  --save-every 5 \
  --debug
```

### 3. 결과 분석

```bash
# 기본 분석 (콘솔 출력)
python backend/ragas/fuseki/results_analyzer.py \
  --input results/all_results_20250101_120000.json

# CSV 내보내기
python backend/ragas/fuseki/results_analyzer.py \
  --input results/all_results_20250101_120000.json \
  --export-csv

# 리포트 생성
python backend/ragas/fuseki/results_analyzer.py \
  --input results/all_results_20250101_120000.json \
  --export-report

# 시각화 (matplotlib 필요)
python backend/ragas/fuseki/results_analyzer.py \
  --input results/all_results_20250101_120000.json \
  --plot

# 전체 옵션
python backend/ragas/fuseki/results_analyzer.py \
  --input results/all_results_20250101_120000.json \
  --export-csv \
  --export-report \
  --plot
```

## 테스트 워크플로우

### 전체 프로세스

```
1. 질문 로드 (questions.jsonl)
   └─ Persona 필터링: foreigner_culture_history

2. 20가지 조합에 대해 순차 실행
   ├─ 조합 1: temporal + outgoing_relations
   ├─ 조합 2: temporal + incoming_relations
   ├─ ...
   └─ 조합 20: pgvector + type_and_summary

3. 각 조합마다:
   ├─ 설정 적용 (thread_weights 오버라이드)
   ├─ 그래프 실행 (질문 → 답변 생성)
   ├─ 컨텍스트 추출 (evidences)
   └─ RAGAS 샘플 생성

4. RAGAS 평가 실행
   ├─ Context Entities Recall
   ├─ Noise Sensitivity (Context Precision)
   ├─ Faithfulness
   └─ Context Relevance

5. 결과 저장
   ├─ 전체 결과: all_results_TIMESTAMP.json
   └─ 요약: summary_TIMESTAMP.json

6. 결과 분석
   ├─ 순위 계산 (메트릭별, 종합)
   ├─ 리포트 생성
   └─ 시각화 (선택)
```

## 출력 파일 설명

### 1. `all_results_TIMESTAMP.json`

모든 테스트 결과를 포함하는 전체 데이터:

```json
[
  {
    "test_id": 1,
    "combination_id": "outgoing_relations__type_and_summary",
    "config": { ... },
    "n_questions": 10,
    "n_samples": 10,
    "scores": {
      "context_relevance": 0.8234,
      "faithfulness": 0.7651,
      "context_precision": 0.8012,
      "context_recall": 0.7890
    },
    "raw_logs": [ ... ],
    "timestamp": "2025-01-01T12:00:00"
  },
  ...
]
```

### 2. `summary_TIMESTAMP.json`

점수 요약:

```json
{
  "timestamp": "20250101_120000",
  "persona_id": "foreigner_culture_history",
  "n_tests": 20,
  "test_results": [
    {
      "test_id": 1,
      "combination_id": "outgoing_relations__type_and_summary",
      "semantic_expander": "outgoing_relations",
      "aggregator": "type_and_summary",
      "n_samples": 10,
      "scores": { ... }
    },
    ...
  ]
}
```

### 3. `all_results_TIMESTAMP_ranked.csv`

순위가 포함된 CSV 파일 (pandas, Excel에서 분석 가능)

### 4. `all_results_TIMESTAMP_report.txt`

텍스트 리포트:
- 전체 순위 Top 5
- 메트릭별 1위 조합
- 상세 점수

## 주의사항

### 1. 가중치 설정

현재는 모든 가중치를 1.0으로 고정하여 테스트합니다:

```python
base_weights = {
    "outgoing_relations": 1.0,
    "incoming_relations": 1.0,
    "entity_properties": 1.0,
    "connected_entities": 1.0,
    "type_and_summary": 1.0
}
```

가중치를 변경하려면 `config_manager.py`의 `create_node_config` 메서드를 수정하세요.

### 2. 벡터 유사도 처리

**환경변수 설정**:
```bash
# 벡터 유사도 점수를 가중치로 사용하지 않음 (기본값)
export USE_VECTOR_SIMILARITY_SCORE=false
```

**동작 방식**:
- `USE_VECTOR_SIMILARITY_SCORE=false` (기본값, RAGAS 평가 시):
  - `pgvector.search(threshold=0.5)`: 0.5 이상만 필터링
  - `relevance_score = 0.65` (고정값): 벡터 유사도를 가중치로 사용하지 않음
  - **sorting 및 필터링 목적으로만 사용**

- `USE_VECTOR_SIMILARITY_SCORE=true` (하이브리드 모드):
  - `relevance_score = 0.65 × 0.6 + similarity × 0.4` (하이브리드 점수)
  - 벡터 유사도를 가중치로 사용

**RAGAS 평가에서는 `USE_VECTOR_SIMILARITY_SCORE=false`로 고정**하여 벡터 유사도를 순수하게 필터링/sorting 용도로만 사용합니다.

### 3. 실행 시간

- 조합당 평균 2-5분 소요 (질문 수에 따라)
- 전체 20개 조합: 약 40분 ~ 2시간

### 4. 중간 저장

`--save-every` 옵션으로 중간 저장 주기를 설정하여 중단 시 재개 가능합니다.

## 트러블슈팅

### 1. RAGAS 메트릭 로드 실패

```
ImportError: Cannot resolve ragas.evaluate
```

**해결**: RAGAS 버전 확인 및 재설치

```bash
pip install --upgrade ragas
```

### 2. Fuseki 연결 실패

```
ConnectionError: Fuseki 서버 연결 실패
```

**해결**: Fuseki Docker 컨테이너 확인

```bash
docker ps | grep fuseki
docker-compose up -d fuseki
```

### 3. 메모리 부족

**해결**: 질문 수 제한

```bash
python automated_test_runner.py --limit 5
```

## 예시 결과

### Top 3 조합 (예시)

```
[Rank 1] temporal__outgoing_relations
  Semantic Expander: temporal
  Aggregator: outgoing_relations
  Average Rank: 1.75
    - context_relevance: 0.8456 (rank: 1)
    - faithfulness: 0.8123 (rank: 2)
    - context_precision: 0.8234 (rank: 1)
    - context_recall: 0.7989 (rank: 3)

[Rank 2] causal_chain__outgoing_relations
  Semantic Expander: causal_chain
  Aggregator: outgoing_relations
  Average Rank: 2.25
  ...

[Rank 3] category__connected_entities
  Semantic Expander: category
  Aggregator: connected_entities
  Average Rank: 3.00
  ...
```

## 향후 개선 사항

1. **가중치 튜닝**: 현재는 1.0 고정, 향후 Grid Search 등으로 최적 가중치 탐색
2. **병렬 실행**: 20개 조합을 병렬로 실행하여 시간 단축
3. **Checkpoint 재개**: 중단된 테스트 자동 재개 기능
4. **추가 메트릭**: Custom 메트릭 추가 (예: Entity Coverage)

## 문의

이슈가 있거나 질문이 있으면 팀원에게 문의하세요.
