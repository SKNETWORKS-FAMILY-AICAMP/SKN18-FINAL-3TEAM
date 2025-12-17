# Fuseki RAG System - RAGAS 평가

Fuseki 기반 한국사 RAG 시스템의 RAGAS 평가 도구 모음입니다.

## 📋 목차

1. [테스트 개요](#테스트-개요)
2. [질문 데이터셋](#질문-데이터셋)
3. [테스트 모드](#테스트-모드)
4. [실행 방법](#실행-방법)
5. [결과 분석](#결과-분석)
6. [가중치 설정](#가중치-설정)

---

## 테스트 개요

### 테스트 구성 요소

#### 1. Semantic Expanders (4가지)

- **temporal**: 시간 기반 확장 (연도, 기간 등)
- **category**: 카테고리 기반 확장 (인물, 사건, 제도 등)
- **causal_chain**: 인과관계 기반 확장
- **pgvector**: 벡터 유사도 기반 확장

#### 2. Aggregator Threads (5가지)

- **outgoing_relations**: 엔티티에서 나가는 관계 (A → B)
- **incoming_relations**: 엔티티로 들어오는 관계 (B → A)
- **entity_properties**: 엔티티의 속성 (Year, Location, Title 등)
- **connected_entities**: 2-hop 연결된 엔티티
- **type_and_summary**: 엔티티 타입과 요약 정보

#### 3. Entity Boost Modes (4가지)

- **exact_match**: 정확히 일치하는 엔티티만 높은 점수
- **partial_match**: 부분 일치하는 엔티티
- **normalized_match**: 정규화 매칭 (공백, 대소문자 무시)
- **penalty_match**: 매칭 안 된 엔티티 (품질 비교용)

### RAGAS 평가 지표

1. **nv_context_relevance**: 검색된 컨텍스트의 질문 관련성
2. **answer_relevancy**: 생성된 답변의 질문 관련성
3. **faithfulness**: 답변이 컨텍스트에 기반했는지 (환각 감지)
4. **nv_response_groundedness**: 답변의 근거 기반성

---

## 질문 데이터셋

### 위치

```
backend/ragas/questions.jsonl
```

### 구성

- **총 40개 질문**
  - 외국인 페르소나 (`foreigner_culture_history`): 20개
  - 아이들 페르소나 (`kids_child`): 20개

### 형식

```json
{
  "question_ko": "세조는 누구였나요?",
  "question_en": "Who was King Sejo?",
  "persona_id": "foreigner_culture_history",
  "reference": "세조는 조선 제7대 임금으로..."
}
```

---

## 테스트 모드

### 1. 80가지 조합 테스트 (Isolation Test)

**목적**: 각 구성 요소를 독립적으로 평가하여 최적 조합 발견

**조합 수**: 4 (semantic) × 5 (thread) × 4 (boost) = **80가지**

**특징**:

- 각 테스트마다 **하나의 semantic expander + 하나의 thread + 하나의 boost mode**만 활성화
- 각 조합의 성능을 독립적으로 측정
- 40개 질문(외국인 20개 + 아이들 20개)으로 테스트

**파일**: `automated_test_runner.py`

### 2. 통합 테스트 (Integrated Test)

**목적**: 모든 기능을 동시에 활성화하여 시너지 효과 측정

**조합 수**: **1가지** (모든 기능 ON)

**특징**:

- **모든 semantic expanders** 동시 활성화
- **모든 aggregator threads** 동시 활성화
- **커스텀 가중치** 적용하여 중요도 반영
- 40개 질문(외국인 20개 + 아이들 20개)으로 테스트

**파일**: `integrated_test_runner.py`

---

## 실행 방법

### 사전 준비

1. **Fuseki 서버 실행 확인**

**Linux/Mac:**

```bash
# Fuseki가 http://localhost:3030/korean_history 에서 실행 중이어야 함
curl http://localhost:3030/korean_history/sparql
```

**Windows:**

```powershell
# PowerShell에서 확인
Invoke-WebRequest -Uri http://localhost:3030/korean_history/sparql

# 또는 브라우저에서 직접 접속
# http://localhost:3030/korean_history/sparql
```

2. **환경 설정**

**Linux/Mac:**

```bash
cd /path/to/SKN18-FINAL-3TEAM
```

**Windows:**

```cmd
cd C:\path\to\SKN18-FINAL-3TEAM
```

### 1. 80가지 조합 테스트

#### 기본 실행 (전체 40개 질문, 단일 프로세스)

```bash
python backend/ragas/fuseki/automated_test_runner.py --save-every 10
```

#### 병렬 실행 (8개 워커로 분할 처리)

**Linux/Mac:**

```bash
# 80개 조합을 8개 워커로 분할 (각 워커당 10개 조합)
./backend/ragas/fuseki/run_parallel.sh 0 10

# 또는 직접 실행
python backend/ragas/fuseki/automated_test_runner.py \
  --save-every 10 \
  --worker-id 0 \
  --num-workers 8
```

**Windows (PowerShell):**

```powershell
# PowerShell 스크립트 실행
.\backend\ragas\fuseki\run_parallel.ps1 -Limit 0 -SaveEvery 10 -NumWorkers 8

# 또는 직접 실행
python backend/ragas/fuseki/automated_test_runner.py `
  --save-every 10 `
  --worker-id 0 `
  --num-workers 8
```

**Windows (Command Prompt):**

```cmd
REM 배치 파일 실행
backend\ragas\fuseki\run_parallel.bat 0 10

REM 또는 직접 실행
python backend/ragas/fuseki/automated_test_runner.py --save-every 10 --worker-id 0 --num-workers 8
```

**병렬 실행 예시:**

**Linux/Mac:**

```bash
# 8개 워커로 병렬 처리 (각 워커가 10개 조합 처리)
./backend/ragas/fuseki/run_parallel.sh 0 10

# 로그 확인
tail -f ragas_test_worker*.log

# 실행 중인 프로세스 확인
ps aux | grep automated_test_runner

# 모든 워커 중지
pkill -f automated_test_runner
```

**Windows (PowerShell):**

```powershell
# 8개 워커로 병렬 처리
.\backend\ragas\fuseki\run_parallel.ps1 -Limit 0 -SaveEvery 10

# 작업 상태 확인
Get-Job

# 작업 출력 확인
Get-Job | Receive-Job

# 모든 작업 중지
Get-Job | Stop-Job
Get-Job | Remove-Job
```

**Windows (Command Prompt):**

```cmd
REM 8개 워커로 병렬 처리
backend\ragas\fuseki\run_parallel.bat 0 10

REM 실행 중인 프로세스 확인
tasklist | findstr python

REM 모든 워커 중지
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Worker*"
```

#### 디버깅 (3개 질문만)

```bash
python backend/ragas/fuseki/automated_test_runner.py --limit 3 --debug
```

#### 특정 조합만 테스트

```bash
# Temporal + Outgoing Relations + Exact Match 조합만
python backend/ragas/fuseki/automated_test_runner.py \
  --semantic temporal \
  --thread outgoing_relations \
  --boost exact_match \
  --limit 3
```

#### 특정 Semantic Expander만 테스트 (20가지)

```bash
python backend/ragas/fuseki/automated_test_runner.py \
  --semantic temporal \
  --save-every 5
```

#### 특정 Thread만 테스트 (16가지)

```bash
python backend/ragas/fuseki/automated_test_runner.py \
  --thread outgoing_relations \
  --save-every 5
```

### 2. 통합 테스트

#### 기본 실행 (전체 40개 질문)

```bash
python backend/ragas/fuseki/integrated_test_runner.py
```

#### 디버깅 (3개 질문만)

```bash
python backend/ragas/fuseki/integrated_test_runner.py --limit 3 --debug
```

### 옵션 설명

| 옵션              | 설명                           | 기본값        |
| ----------------- | ------------------------------ | ------------- |
| `--limit N`       | 테스트할 질문 개수 제한        | 0 (전체 40개) |
| `--debug`         | 디버그 모드 (상세 로그 출력)   | False         |
| `--save-every N`  | N개 조합마다 중간 저장         | 5             |
| `--semantic X`    | Semantic Expander 필터링       | None          |
| `--thread X`      | Aggregator Thread 필터링       | None          |
| `--boost X`       | Entity Boost Mode 필터링       | None          |
| `--worker-id N`   | 워커 ID (병렬 처리용, 0-based) | None          |
| `--num-workers N` | 총 워커 수 (병렬 처리용)       | None          |

**참고**: `--worker-id`와 `--num-workers`는 함께 사용해야 합니다. 병렬 실행 시 각 워커가 조합의 일부만 처리합니다.

---

## 결과 분석

### 결과 파일 위치

#### 80가지 조합 테스트

```
backend/ragas/fuseki/results/
├── ragas_results_10combos_YYYYMMDD_HHMMSS_worker0_raw_worker0.json  # 워커 0 결과
├── ragas_results_10combos_YYYYMMDD_HHMMSS_worker1_raw_worker1.json  # 워커 1 결과
├── ... (워커별로 파일 생성)
└── ragas_results_10combos_YYYYMMDD_HHMMSS_worker7_raw_worker7.json  # 워커 7 결과
```

**병렬 실행 시**: 각 워커가 자신의 조합만 처리하므로, 각 워커별로 별도의 결과 파일이 생성됩니다.

#### 통합 테스트

```
backend/ragas/fuseki/integrated_results/
├── integrated_results_all_YYYYMMDD_HHMMSS.json          # 간소화된 결과
└── integrated_results_all_YYYYMMDD_HHMMSS_raw.json      # 전체 로그 포함
```

### 결과 파일 구조

#### 간소화된 결과 (`*.json`)

```json
{
  "combination_id": 1,
  "semantic_expander": "temporal",
  "aggregator_thread": "outgoing_relations",
  "entity_boost_mode": "exact_match",
  "short_name": "temp_out_exact",
  "n_questions": 40,
  "n_samples": 40,
  "scores": {
    "nv_context_relevance": 0.5,
    "answer_relevancy": 0.733,
    "faithfulness": 0.572,
    "nv_response_groundedness": 0.95
  },
  "timestamp": "2025-12-17T..."
}
```

#### Raw 결과 (`*_raw.json`)

위 정보 + `raw_logs` 포함:

```json
{
  "raw_logs": [
    {
      "idx": 1,
      "persona": "foreigner_culture_history",
      "question": "세조는 누구였나요?",
      "answer": "세조는 조선 제7대 임금으로...",
      "contexts": ["...", "..."],
      "n_contexts": 15,
      "elapsed_seconds": 5.23,
      "tokens": {
        "total": 1234,
        "prompt": 890,
        "completion": 344
      }
    }
  ]
}
```

### 결과 분석 팁

#### 1. 최고 성능 조합 찾기

```python
import json

# 결과 로드
with open("ragas_results_80combos_*.json", "r") as f:
    results = json.load(f)

# nv_context_relevance 기준 정렬
sorted_results = sorted(results, key=lambda x: x["scores"]["nv_context_relevance"], reverse=True)

# Top 5 출력
for i, r in enumerate(sorted_results[:5], 1):
    print(f"{i}. {r['short_name']}: {r['scores']['nv_context_relevance']:.4f}")
```

#### 2. Thread별 평균 점수 비교

```python
from collections import defaultdict

thread_scores = defaultdict(list)
for r in results:
    thread = r["aggregator_thread"]
    score = r["scores"]["nv_context_relevance"]
    thread_scores[thread].append(score)

for thread, scores in thread_scores.items():
    avg = sum(scores) / len(scores)
    print(f"{thread}: {avg:.4f} (n={len(scores)})")
```

#### 3. 페르소나별 성능 비교

```python
# Raw 결과에서 페르소나별 분석
with open("integrated_results_all_*_raw.json", "r") as f:
    result = json.load(f)

persona_contexts = defaultdict(list)
for log in result["raw_logs"]:
    persona = log["persona"]
    n_contexts = log["n_contexts"]
    persona_contexts[persona].append(n_contexts)

for persona, contexts in persona_contexts.items():
    avg = sum(contexts) / len(contexts)
    print(f"{persona}: avg {avg:.2f} contexts")
```

---

## 가중치 설정

### 통합 테스트 가중치

자세한 내용은 [WEIGHTS_ANALYSIS.md](./WEIGHTS_ANALYSIS.md) 참조

#### Semantic Expanders 가중치

```python
"semantic_expanders": {
    "temporal": 1.3,      # 시간 정보는 역사에서 핵심
    "category": 1.2,      # 카테고리 분류로 정확도 향상
    "causal_chain": 1.4,  # 인과관계가 가장 중요 (최고)
    "pgvector": 1.0       # 벡터 검색은 보조적
}
```

#### Aggregator Threads 가중치

```python
"aggregator_threads": {
    "outgoing_relations": 1.3,    # 서술적 풍부함 (최고 점수)
    "entity_properties": 1.2,     # 정확한 정보, 다양성
    "type_and_summary": 1.15,     # 개요 제공
    "incoming_relations": 1.1,    # 대칭 관계이지만 활용도 낮음
    "connected_entities": 1.0     # 2-hop, 보조적
}
```

### 가중치 수정 방법

`integrated_test_runner.py`의 `OPTIMIZED_WEIGHTS` 딕셔너리를 수정:

```python
OPTIMIZED_WEIGHTS = {
    "semantic_expanders": {
        "temporal": 1.5,  # 시간 정보 가중치 증가
        ...
    },
    ...
}
```

---

## 문제 해결

### 1. Fuseki 연결 실패

```
ConnectionError: Failed to connect to Fuseki
```

**해결**:

```bash
# Fuseki 상태 확인
curl http://localhost:3030/korean_history/sparql

# Fuseki 재시작
cd /path/to/fuseki
./fuseki-server --config=config.ttl
```

### 2. 메모리 부족

```
MemoryError: Out of memory
```

**해결**:

```bash
# limit 옵션으로 질문 수 제한
python backend/ragas/fuseki/automated_test_runner.py --limit 10

# 또는 배치 크기 축소 (save-every)
python backend/ragas/fuseki/automated_test_runner.py --save-every 3
```

### 3. RAGAS 평가 실패

```
RAGAS evaluation failed: ...
```

**해결**:

```bash
# 디버그 모드로 실행하여 상세 로그 확인
python backend/ragas/fuseki/automated_test_runner.py --debug --limit 3
```

---

## 참고 문서

- [WEIGHTS_ANALYSIS.md](./WEIGHTS_ANALYSIS.md): 가중치 분석 및 근거
- [config_manager.py](./config_manager.py): 80가지 조합 생성 로직
- [ragas_metrics.py](./ragas_metrics.py): RAGAS 메트릭 구현

---

## 예상 실행 시간

### 80가지 조합 테스트

- **전체 (40개 질문 × 80가지 조합, 단일 프로세스)**: 약 8-10시간
- **전체 (40개 질문 × 80가지 조합, 8개 병렬)**: 약 1-1.5시간 (각 워커당 10개 조합)
- **디버깅 (3개 질문 × 80가지 조합)**: 약 40-60분
- **단일 조합 (40개 질문)**: 약 5-8분

**병렬 실행 권장**: 전체 테스트는 병렬 실행을 통해 시간을 크게 단축할 수 있습니다.

### 통합 테스트

- **전체 (40개 질문)**: 약 10-15분
- **디버깅 (3개 질문)**: 약 2-3분

_실행 시간은 하드웨어 사양과 Fuseki 서버 성능에 따라 달라질 수 있습니다._

---

## 라이선스

이 프로젝트는 SKN18-FINAL-3TEAM의 일부입니다.
