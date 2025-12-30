# RAGAS 80가지 조합 테스트 실행 가이드

## 빠른 시작

### 1. 테스트 실행 (3개 질문만 - 디버깅용)

```bash
# 프로젝트 루트에서 실행
python backend/ragas/fuseki/automated_test_runner.py --limit 3 --debug
```

### 2. 전체 테스트 (80가지 조합)

```bash
# 백그라운드 실행 + 로그 저장
nohup python backend/ragas/fuseki/automated_test_runner.py > ragas_test.log 2>&1 &

# 진행상황 모니터링
tail -f ragas_test.log
```

### 3. 특정 조합만 테스트

```bash
# Temporal semantic만 (20가지)
python backend/ragas/fuseki/automated_test_runner.py --semantic temporal --limit 3

# Exact match boost만 (20가지)
python backend/ragas/fuseki/automated_test_runner.py --boost exact_match --limit 3

# 특정 조합 1가지만
python backend/ragas/fuseki/automated_test_runner.py \
  --semantic temporal \
  --thread outgoing_relations \
  --boost exact_match \
  --limit 3 \
  --debug
```

## 주요 옵션

| 옵션           | 설명                                | 기본값                      |
| -------------- | ----------------------------------- | --------------------------- |
| `--persona`    | 테스트할 persona ID                 | `foreigner_culture_history` |
| `--limit`      | 조합당 질문 수 제한 (0 = 제한 없음) | `0`                         |
| `--debug`      | 디버그 모드 활성화                  | `False`                     |
| `--save-every` | N개 조합마다 중간 저장              | 5                           |
| `--semantic`   | Semantic expander 필터              | `None` (전체)               |
| `--thread`     | Aggregator thread 필터              | `None` (전체)               |
| `--boost`      | Entity boost mode 필터              | `None` (전체)               |

## Semantic Expander (4가지)

- `temporal` - 시간적 맥락 확장 (±10년 이내 이벤트)
- `category` - 카테고리 기반 주제 확장
- `causal_chain` - 인과관계 체인 확장
- `pgvector` - 벡터 유사도 기반 확장

## Aggregator Thread (5가지)

- `outgoing_relations` - 나가는 관계 (엔티티 → ?)
- `incoming_relations` - 들어오는 관계 (? → 엔티티)
- `entity_properties` - 엔티티 속성 (리터럴 값)
- `connected_entities` - 연결된 엔티티 (2-hop)
- `type_and_summary` - 타입과 요약 정보

## Entity Boost Mode (4가지)

- `exact_match` - 정확 매칭된 엔티티만 사용
- `partial_match` - 부분 매칭된 엔티티만 사용
- `normalized_match` - 정규화 매칭된 엔티티만 사용
- `penalty_match` - 매칭 안 된 엔티티만 사용 (품질 비교용)

## 결과 파일

테스트 완료 후 `backend/ragas/fuseki/results/` 디렉토리에 생성됩니다:

```
backend/ragas/fuseki/results/
├── ragas_results_80combos_20250116_144900.json           # 간소화 결과 (raw logs 제외)
├── ragas_results_80combos_20250116_144900_raw.json       # 전체 결과 (질문/답변/컨텍스트 포함)
└── ragas_summary_80combos_20250116_144900.json           # 요약 (평균 점수)
```

## 결과 분석

```bash
# 결과 분석 및 순위 확인
python backend/ragas/fuseki/results_analyzer.py \
  --input backend/ragas/fuseki/results/ragas_results_80combos_20250116_144900.json

# CSV와 리포트 생성
python backend/ragas/fuseki/results_analyzer.py \
  --input backend/ragas/fuseki/results/ragas_results_80combos_20250116_144900.json \
  --export-csv \
  --export-report
```

## RAGAS 평가 지표

### 검색 단계

- **Context Relevance** - 질문과 검색된 context의 의미적 관련성

### 생성 단계

- **Response Relevancy (Answer Relevancy)** - 답변이 질문에 잘 답하는지
- **Faithfulness** - 답변이 context에 기반하는지 (환각 없음)
- **Response Groundedness (Answer Correctness)** - 답변이 context를 얼마나 사용하는지

## 환경 변수

`.env` 파일에 다음 설정이 필요합니다:

```bash
# OpenAI API Key (RAGAS 평가에 사용)
OPENAI_API_KEY=your-api-key-here

# 벡터 유사도 점수 비활성화 (공정한 비교를 위해)
USE_VECTOR_SIMILARITY_SCORE=false
```

**중요**: `USE_VECTOR_SIMILARITY_SCORE=false`는:

- pgvector 검색을 **비활성화하지 않습니다**
- pgvector는 **여전히 실행되며** 유사도 ≥0.5 결과를 가져옵니다
- 단지 유사도 점수를 **가중치로 사용하지 않고 1.0으로 설정**합니다
- 이렇게 하면 4가지 semantic 방법을 **공정하게 비교**할 수 있습니다

## 예상 소요 시간

- **3개 질문 × 80가지 조합** → 약 20-30분
- **전체 질문 × 80가지 조합** → 약 2-3시간 (질문 수에 따라 달라짐)

## 트러블슈팅

### Fuseki 서버 연결 실패

```bash
# Fuseki 실행 확인
docker ps | grep fuseki

# 재시작
docker-compose restart fuseki
```

### RAGAS import 오류

```bash
pip install ragas datasets pandas
```

### OpenAI API Rate Limit

- `--limit 3` 옵션으로 질문 수를 줄이세요
- OpenAI API 요금제를 확인하세요

## 다음 단계

1. **결과 분석** - CSV 파일을 Excel이나 pandas로 열어서 상세 분석
2. **가중치 반영** - 최고 성능 조합의 설정을 시스템에 적용
3. **추가 검증** - 다른 persona나 질문 세트로 재검증
