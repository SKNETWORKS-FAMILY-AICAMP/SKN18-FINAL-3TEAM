# Fuseki RAG System - Automated RAGAS Evaluation (80 Combinations)

이 디렉토리는 Fuseki 기반 RAG 시스템의 자동화된 RAGAS 평가를 수행합니다.

## 개요

**목적**: **80가지 노드 조합**에 대해 RAGAS 평가를 자동으로 수행하여 최적의 가중치와 설정을 찾습니다.

**평가 조합 (총 80가지 = 4 × 5 × 4)**:

### 1. Semantic Expander (4가지)
의미론적 엔티티 확장 방법:
- `temporal`: 시간적 맥락 확장 (±10년 이내 이벤트)
- `category`: 카테고리 기반 주제 확장
- `causal_chain`: 인과관계 체인 확장 (leadsTo, ledTo, causes)
- `pgvector`: 벡터 유사도 기반 확장

### 2. Aggregator Thread (5가지)
Parallel Knowledge Retrieval Thread:
- `outgoing_relations`: 엔티티에서 나가는 관계 (엔티티 → ?)
- `incoming_relations`: 엔티티로 들어오는 관계 (? → 엔티티)
- `entity_properties`: 엔티티의 속성 (리터럴 값)
- `connected_entities`: 두 엔티티를 연결하는 중간 노드
- `type_and_summary`: 엔티티 타입과 요약 정보

### 3. Entity Boost Mode (4가지)
쿼리 엔티티와의 매칭 방식:
- `exact_match`: **정확 매칭**된 엔티티만 사용 (엔티티명이 정확히 일치)
- `partial_match`: **부분 매칭**된 엔티티만 사용 (엔티티명이 부분 포함)
- `normalized_match`: **정규화 매칭**된 엔티티만 사용 (공백/언더스코어 제거 후 일치)
- `penalty_match`: **매칭 안 된** 엔티티만 사용 (품질 비교용 - 베이스라인)

**평가 메트릭 (LLM Judge 기반)**:

### 검색 단계
1. **Context Relevance** - 질문과 검색된 context의 의미적 관련성

### 생성 단계
2. **Response Relevancy (Answer Relevancy)** - 답변이 질문에 잘 답하는지
3. **Faithfulness** - 답변이 context에 기반하는지 (환각 없음)
4. **Response Groundedness (Answer Correctness)** - 답변이 context를 얼마나 사용하는지

## 파일 구조

```
backend/ragas/fuseki/
├── README.md                    # 이 파일 (상세 문서)
├── QUICKSTART.md                # 빠른 시작 가이드
├── config_manager.py            # 80가지 조합 설정 관리
├── ragas_metrics.py             # RAGAS 메트릭 로더
├── automated_test_runner.py    # 자동화 테스트 러너 (80 조합)
├── results_analyzer.py          # 결과 분석 및 리포트 생성
└── results/                     # 결과 저장 디렉토리
    ├── ragas_results_80combos_YYYYMMDD_HHMMSS.json
    ├── ragas_summary_80combos_YYYYMMDD_HHMMSS.json
    ├── ragas_results_80combos_YYYYMMDD_HHMMSS_raw.json
    ├── ragas_results_80combos_YYYYMMDD_HHMMSS_ranked.csv
    └── ragas_results_80combos_YYYYMMDD_HHMMSS_report.txt
```

## 설치

### 필수 패키지

```bash
pip install ragas pandas datasets
```

### 선택 패키지 (시각화)

```bash
pip install matplotlib seaborn
```

### 환경 변수 설정

```bash
# .env 파일에 추가
USE_VECTOR_SIMILARITY_SCORE=false  # 벡터 유사도를 가중치로 사용하지 않음
```

## 빠른 시작

자세한 시작 가이드는 [QUICKSTART.md](QUICKSTART.md)를 참고하세요.

```bash
# 빠른 테스트 (각 조합당 3개 질문만)
python backend/ragas/fuseki/automated_test_runner.py --limit 3 --debug

# 전체 테스트 (80가지 조합)
python backend/ragas/fuseki/automated_test_runner.py
```

## 사용 방법

### 1. 전체 테스트 실행 (80가지 조합)

```bash
# 기본 실행
python backend/ragas/fuseki/automated_test_runner.py

# 백그라운드 실행 + 로그 저장
nohup python backend/ragas/fuseki/automated_test_runner.py > ragas_test.log 2>&1 &
tail -f ragas_test.log
```

### 2. 옵션을 사용한 실행

```bash
# 질문 수 제한 (각 조합당 5개 질문만)
python backend/ragas/fuseki/automated_test_runner.py --limit 5

# 디버그 모드
python backend/ragas/fuseki/automated_test_runner.py --debug

# Persona 지정
python backend/ragas/fuseki/automated_test_runner.py --persona foreigner_culture_history

# 중간 저장 주기 설정 (10개 조합마다 저장 - 기본값)
python backend/ragas/fuseki/automated_test_runner.py --save-every 10

# 특정 semantic 방법만 테스트 (20가지 조합)
python backend/ragas/fuseki/automated_test_runner.py --semantic temporal

# 특정 thread만 테스트 (16가지 조합)
python backend/ragas/fuseki/automated_test_runner.py --thread outgoing_relations

# 특정 boost 모드만 테스트 (20가지 조합)
python backend/ragas/fuseki/automated_test_runner.py --boost exact_match

# 특정 조합 하나만 테스트 (1가지 조합)
python backend/ragas/fuseki/automated_test_runner.py \
  --semantic temporal \
  --thread outgoing_relations \
  --boost exact_match \
  --limit 3 \
  --debug
```

### 3. 결과 분석

```bash
# 기본 분석 (콘솔 출력)
python backend/ragas/fuseki/results_analyzer.py \
  --input results/ragas_results_80combos_20250101_120000.json

# CSV 내보내기
python backend/ragas/fuseki/results_analyzer.py \
  --input results/ragas_results_80combos_20250101_120000.json \
  --export-csv

# 리포트 생성
python backend/ragas/fuseki/results_analyzer.py \
  --input results/ragas_results_80combos_20250101_120000.json \
  --export-report

# 전체 옵션
python backend/ragas/fuseki/results_analyzer.py \
  --input results/ragas_results_80combos_20250101_120000.json \
  --export-csv \
  --export-report
```

## 테스트 워크플로우

### 전체 프로세스

```
1. 질문 로드 (questions.jsonl)
   └─ Persona 필터링: foreigner_culture_history

2. 80가지 조합 생성
   ├─ 4 Semantic × 5 Thread × 4 Boost = 80 조합
   └─ 각 조합마다 고유한 test_config 생성

3. 각 조합마다:
   ├─ test_config를 GraphState에 추가
   ├─ 랭그래프 노드들이 test_config 확인
   │   ├─ semantic_expander_node: 해당 semantic 방법만 실행
   │   ├─ parallel_knowledge_retrieval_node: 해당 thread만 실행
   │   └─ path_evidence_aggregator_node: 해당 boost 모드로 필터링
   ├─ 그래프 실행 (질문 → 답변 생성)
   ├─ 컨텍스트 추출 (evidences → contexts)
   ├─ 시간/토큰 사용량 기록
   └─ RAGAS 샘플 생성

4. RAGAS 평가 실행
   ├─ 검색 단계: Context Relevance
   └─ 생성 단계: Response Relevancy, Faithfulness, Response Groundedness

5. 결과 저장
   ├─ 전체 결과: ragas_results_80combos_TIMESTAMP.json
   ├─ 요약: ragas_summary_80combos_TIMESTAMP.json
   └─ 질문별 상세: ragas_results_80combos_TIMESTAMP_raw.json

6. 결과 분석
   ├─ 순위 계산 (메트릭별, 종합)
   ├─ 리포트 생성
   └─ CSV 내보내기
```

## 출력 파일 설명

### 1. `ragas_results_80combos_TIMESTAMP.json`

모든 테스트 결과를 포함하는 전체 데이터:

```json
[
  {
    "test_id": 1,
    "combination_id": "temporal__outgoing_relations__exact_match",
    "config": {
      "semantic_expander": {"temporal": true, "category": false, ...},
      "aggregator_threads": {"outgoing_relations": true, ...},
      "entity_boost_mode": "exact_match"
    },
    "n_questions": 10,
    "n_samples": 10,
    "scores": {
      "context_relevance": 0.8234,
      "answer_relevancy": 0.8123,
      "faithfulness": 0.7651,
      "response_groundedness": 0.8012
    },
    "avg_elapsed_seconds": 3.45,
    "avg_tokens": {"total": 2450, "prompt": 1200, "completion": 1250},
    "timestamp": "2025-01-01T12:00:00"
  },
  ...
]
```

### 2. `ragas_summary_80combos_TIMESTAMP.json`

점수 요약:

```json
{
  "timestamp": "20250101_120000",
  "persona_id": "foreigner_culture_history",
  "n_tests": 80,
  "test_results": [
    {
      "test_id": 1,
      "combination_id": "temporal__outgoing_relations__exact_match",
      "semantic_expander": "temporal",
      "aggregator": "outgoing_relations",
      "entity_boost_mode": "exact_match",
      "n_samples": 10,
      "scores": {...},
      "avg_elapsed_seconds": 3.45,
      "avg_tokens": {...}
    },
    ...
  ]
}
```

### 3. `ragas_results_80combos_TIMESTAMP_raw.json`

질문별 상세 로그 (디버깅용):

```json
{
  "temporal__outgoing_relations__exact_match": [
    {
      "idx": 0,
      "question": "세조는 누구였나요?",
      "answer": "세조는 조선의 제7대 왕입니다...",
      "contexts": ["세조 → [즉위] → 1455년", ...],
      "n_contexts": 15,
      "elapsed_seconds": 3.2,
      "tokens": {"total": 2400, ...}
    },
    ...
  ],
  ...
}
```

### 4. `ragas_results_80combos_TIMESTAMP_ranked.csv`

순위가 포함된 CSV 파일 (pandas, Excel에서 분석 가능)

### 5. `ragas_results_80combos_TIMESTAMP_report.txt`

텍스트 리포트:
- 전체 순위 Top 10
- 메트릭별 1위 조합
- Semantic/Thread/Boost 별 평균 점수
- 상세 점수

## Entity Boost Mode 상세 설명

### 목적
쿼리 엔티티와의 매칭 정도에 따라 evidence를 필터링하여, 어떤 매칭 방식이 가장 효과적인지 비교

### 각 모드의 동작

#### 1. exact_match
- **사용**: 정확히 매칭된 evidence만
- **예시**: 질문에 "세조"가 있고, evidence에 "세조"가 정확히 있는 경우
- **목적**: 가장 정확한 정보만 사용했을 때 품질 측정

#### 2. partial_match
- **사용**: 부분 매칭된 evidence만
- **예시**: 질문에 "조선왕"이 있고, evidence에 "조선왕조"가 있는 경우
- **목적**: 부분 일치하는 정보의 품질 측정

#### 3. normalized_match
- **사용**: 정규화 후 매칭된 evidence만
- **예시**: 질문에 "경복궁"이 있고, evidence에 "경복_궁"이 있는 경우 (공백/언더스코어 제거 후 일치)
- **목적**: 표기 변형에 강건한 매칭의 품질 측정

#### 4. penalty_match
- **사용**: 매칭 **안 된** evidence만
- **목적**: 쿼리 엔티티와 직접 관련 없는 정보만 사용했을 때 얼마나 품질이 낮은지 측정 (베이스라인)
- **가중치**: 1.0 (순수 측정 - 인위적인 패널티 없음)

### 비교 예시

질문: "세조는 누구였나요?"

| Boost Mode | 사용하는 Evidence 예시 | 목적 |
|------------|------------------------|------|
| exact_match | "세조 → [즉위] → 1455년" | 정확 매칭의 품질 |
| partial_match | "세조대왕의 업적" | 부분 매칭의 품질 |
| normalized_match | "세_조 → [통치]" | 정규화 매칭의 품질 |
| penalty_match | "조선왕조의 역사" | 매칭 없는 정보의 품질 (낮을 것으로 예상) |

## 주의사항

### 1. 가중치 설정

**테스트 모드**에서는 모든 가중치를 1.0으로 고정:
- 각 조합마다 하나의 semantic, thread, boost만 활성화
- 비활성화된 것들은 실행하지 않음 (빈 결과 반환)

**일반 모드** (test_config 없음):
- 모든 방법 실행
- 환경변수로 설정된 가중치 사용

### 2. 벡터 유사도 처리

**환경변수 설정**:
```bash
# 벡터 유사도 점수를 가중치로 사용하지 않음 (RAGAS 평가 시)
export USE_VECTOR_SIMILARITY_SCORE=false
```

**동작 방식**:
- `USE_VECTOR_SIMILARITY_SCORE=false` (기본값, RAGAS 평가 시):
  - `pgvector.search(threshold=0.5)`: 0.5 이상만 필터링
  - `relevance_score = 1.0` (고정값): 벡터 유사도를 가중치로 사용하지 않음
  - **sorting 및 필터링 목적으로만 사용**

- `USE_VECTOR_SIMILARITY_SCORE=true` (하이브리드 모드):
  - `relevance_score = 0.65 × 0.6 + similarity × 0.4` (하이브리드 점수)
  - 벡터 유사도를 가중치로 사용

**RAGAS 평가에서는 `USE_VECTOR_SIMILARITY_SCORE=false`로 고정**하여 벡터 유사도를 순수하게 필터링/sorting 용도로만 사용합니다.

### 3. 실행 시간

- 조합당 평균 2-5분 소요 (질문 수에 따라)
- 전체 80개 조합:
  - 질문 3개/조합: 약 40분 ~ 1시간
  - 질문 10개/조합: 약 2-3시간
  - 전체 질문: 3-5시간

### 4. 중간 저장

`--save-every 10` (기본값)으로 10개 조합마다 자동 저장하여 중단 시 재개 가능합니다.

## 트러블슈팅

### 1. RAGAS 메트릭 로드 실패

```
ImportError: Cannot resolve ragas.evaluate
```

**해결**: RAGAS 버전 확인 및 재설치

```bash
pip install --upgrade ragas datasets
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
python automated_test_runner.py --limit 3
```

### 4. OpenAI API Rate Limit

```
OpenAIError: Rate limit exceeded
```

**해결**: API 키 및 요금제 확인
```bash
# https://platform.openai.com/account/rate-limits
```

## 예시 결과

### Top 5 조합 (예시)

```
[Rank 1] temporal__outgoing_relations__exact_match
  Semantic Expander: temporal
  Aggregator: outgoing_relations
  Entity Boost: exact_match
  Average Rank: 1.50
    - context_relevance: 0.8456 (rank: 1)
    - answer_relevancy: 0.8123 (rank: 2)
    - faithfulness: 0.8234 (rank: 1)
    - response_groundedness: 0.7989 (rank: 2)

[Rank 2] causal_chain__outgoing_relations__exact_match
  Semantic Expander: causal_chain
  Aggregator: outgoing_relations
  Entity Boost: exact_match
  Average Rank: 2.25
  ...

[Rank 3] temporal__connected_entities__partial_match
  Semantic Expander: temporal
  Aggregator: connected_entities
  Entity Boost: partial_match
  Average Rank: 3.00
  ...
```

## 향후 개선 사항

1. **가중치 튜닝**: 현재는 1.0 고정, 향후 Grid Search 등으로 최적 가중치 탐색
2. **병렬 실행**: 80개 조합을 병렬로 실행하여 시간 단축
3. **Checkpoint 재개**: 중단된 테스트 자동 재개 기능
4. **추가 메트릭**: Custom 메트릭 추가 (예: Entity Coverage, Path Diversity)
5. **관계 가중치 튜닝**: RELATION_WEIGHTS, PROPERTY_WEIGHTS 최적화

## 문의

이슈가 있거나 질문이 있으면 팀원에게 문의하세요.

## 참고 문서

- [QUICKSTART.md](QUICKSTART.md) - 빠른 시작 가이드
- RAGAS 공식 문서: https://docs.ragas.io/
