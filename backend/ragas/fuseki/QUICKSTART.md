# 빠른 시작 가이드 (Quick Start)

이 가이드는 Fuseki 기반 RAG 시스템의 RAGAS 자동 평가 시스템을 빠르게 시작하는 방법을 설명합니다.

## 개요

이 평가 시스템은 **80가지 조합**을 자동으로 테스트합니다:
- **4가지 Semantic Expander**: temporal, category, causal_chain, pgvector
- **5가지 Aggregator Thread**: outgoing_relations, incoming_relations, entity_properties, connected_entities, type_and_summary
- **4가지 Entity Boost Mode**: exact_match, partial_match, normalized_match, penalty_match

**총 조합**: 4 × 5 × 4 = **80가지**

## 1. 준비 사항

### 필수 패키지 설치

```bash
pip install ragas pandas datasets
```

### Fuseki 서버 실행 확인

```bash
# Docker로 Fuseki 실행 중인지 확인
docker ps | grep fuseki

# 실행 중이 아니면 시작
docker-compose up -d fuseki

# 접속 테스트
curl http://localhost:3030
```

### 환경 변수 설정

```bash
# .env 파일에 추가 (벡터 유사도 점수 비활성화)
USE_VECTOR_SIMILARITY_SCORE=false
```

## 2. 빠른 테스트 (각 조합당 3개 질문만)

처음 시작할 때는 소수의 질문으로 테스트하는 것을 추천합니다:

```bash
# 각 조합당 3개 질문만 테스트 (약 20-30분 소요)
python backend/ragas/fuseki/automated_test_runner.py --limit 3 --debug

# 특정 조합만 테스트 (디버깅용)
python backend/ragas/fuseki/automated_test_runner.py \
  --semantic temporal \
  --thread outgoing_relations \
  --boost exact_match \
  --limit 3 \
  --debug
```

## 3. 결과 확인

테스트가 완료되면 `backend/ragas/fuseki/results/` 디렉토리에 결과가 저장됩니다:

```bash
# 최신 결과 파일 확인
ls -lt backend/ragas/fuseki/results/

# 예시 출력:
# ragas_results_80combos_20250116_144900.json      # 모든 조합 결과
# ragas_summary_80combos_20250116_144900.json      # 요약 (평균 점수)
# ragas_results_80combos_20250116_144900_raw.json  # 질문별 상세 로그
```

## 4. 결과 분석

```bash
# 기본 분석 (콘솔에 상위 10개 출력)
python backend/ragas/fuseki/results_analyzer.py \
  --input backend/ragas/fuseki/results/ragas_results_80combos_20250116_144900.json

# CSV와 리포트 생성
python backend/ragas/fuseki/results_analyzer.py \
  --input backend/ragas/fuseki/results/ragas_results_80combos_20250116_144900.json \
  --export-csv \
  --export-report
```

생성되는 파일:
- `ragas_results_80combos_20250116_144900_ranked.csv` - Excel에서 열 수 있는 순위표
- `ragas_results_80combos_20250116_144900_report.txt` - 텍스트 리포트

## 5. 전체 테스트 실행

빠른 테스트로 시스템이 잘 작동하는 것을 확인했다면, 전체 질문으로 테스트합니다:

```bash
# 전체 질문으로 80가지 조합 테스트 (약 2-3시간 소요)
python backend/ragas/fuseki/automated_test_runner.py

# 백그라운드 실행 + 로그 저장
nohup python backend/ragas/fuseki/automated_test_runner.py > ragas_test.log 2>&1 &

# 진행상황 모니터링
tail -f ragas_test.log
```

## 6. 주요 옵션

### automated_test_runner.py

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--persona` | 테스트할 persona ID | `foreigner_culture_history` |
| `--limit` | 조합당 질문 수 제한 (0 = 제한 없음) | `0` |
| `--debug` | 디버그 모드 활성화 | `False` |
| `--save-every` | N개 조합마다 중간 저장 | `10` |
| `--semantic` | 특정 semantic 방법만 테스트 | `None` (전체) |
| `--thread` | 특정 thread만 테스트 | `None` (전체) |
| `--boost` | 특정 boost 모드만 테스트 | `None` (전체) |

### 예시:

```bash
# Persona 변경
python backend/ragas/fuseki/automated_test_runner.py --persona kids_child

# 디버그 모드 + 질문 제한
python backend/ragas/fuseki/automated_test_runner.py --limit 3 --debug

# 자주 중간 저장 (5개 조합마다)
python backend/ragas/fuseki/automated_test_runner.py --save-every 5

# temporal + outgoing_relations 조합만 테스트
python backend/ragas/fuseki/automated_test_runner.py \
  --semantic temporal \
  --thread outgoing_relations

# exact_match boost 모드만 테스트 (20가지 조합)
python backend/ragas/fuseki/automated_test_runner.py --boost exact_match
```

## 7. 테스트 조합 이해하기

### Semantic Expander (4가지)
- **temporal**: 시간적 맥락 확장 (±10년 이내 이벤트)
- **category**: 카테고리 기반 주제 확장
- **causal_chain**: 인과관계 체인 확장
- **pgvector**: 벡터 유사도 기반 확장

### Aggregator Thread (5가지)
- **outgoing_relations**: 엔티티 → ?
- **incoming_relations**: ? → 엔티티
- **entity_properties**: 엔티티의 속성
- **connected_entities**: 두 엔티티를 연결하는 중간 노드
- **type_and_summary**: 엔티티 타입과 요약

### Entity Boost Mode (4가지)
- **exact_match**: 정확히 매칭된 엔티티만 사용
- **partial_match**: 부분 매칭된 엔티티만 사용
- **normalized_match**: 정규화 매칭된 엔티티만 사용
- **penalty_match**: 매칭 안 된 엔티티만 사용 (품질 비교용)

## 8. RAGAS 평가 지표

### 검색 단계
- **Context Relevance**: 질문과 검색된 context의 의미적 관련성

### 생성 단계
- **Response Relevancy (Answer Relevancy)**: 답변이 질문에 잘 답하는지
- **Faithfulness**: 답변이 context에 기반하는지 (환각 없음)
- **Response Groundedness (Answer Correctness)**: 답변이 context를 얼마나 사용하는지

## 9. 트러블슈팅

### 문제: RAGAS import 오류

```
ImportError: No module named 'ragas'
```

**해결:**
```bash
pip install ragas datasets
```

### 문제: Fuseki 연결 실패

```
ConnectionError: Fuseki 서버 연결 실패
```

**해결:**
```bash
# Fuseki 컨테이너 상태 확인
docker ps -a | grep fuseki

# 재시작
docker-compose restart fuseki

# 로그 확인
docker logs fuseki
```

### 문제: 메모리 부족

**해결:** 질문 수를 줄입니다
```bash
python backend/ragas/fuseki/automated_test_runner.py --limit 3
```

### 문제: OpenAI API 오류

```
OpenAIError: Rate limit exceeded
```

**해결:** API 키와 요금제 확인
```bash
# .env 파일 확인
cat .env | grep OPENAI_API_KEY

# Rate limit 확인
# https://platform.openai.com/account/rate-limits
```

### 문제: 결과 파일을 찾을 수 없음

**해결:**
```bash
# results 디렉토리 확인
ls -la backend/ragas/fuseki/results/

# 디렉토리가 없으면 생성
mkdir -p backend/ragas/fuseki/results/
```

## 10. 다음 단계

1. **결과 분석**: CSV 파일을 Excel이나 pandas로 열어서 상세 분석
2. **가중치 조정**: 최고 성능 조합의 가중치를 시스템에 반영
3. **추가 테스트**: 다른 persona나 질문 세트로 검증

## 11. 주요 파일 위치

```
backend/ragas/fuseki/
├── automated_test_runner.py   # 메인 테스트 러너 (80가지 조합)
├── results_analyzer.py         # 결과 분석기
├── config_manager.py           # 80가지 조합 설정 관리
├── ragas_metrics.py            # RAGAS 메트릭 로더
├── README.md                   # 상세 문서
├── QUICKSTART.md               # 이 파일
└── results/                    # 결과 저장 디렉토리
    ├── ragas_results_80combos_*.json
    ├── ragas_summary_80combos_*.json
    ├── ragas_results_80combos_*_raw.json
    └── *_ranked.csv
```

## 도움말

더 자세한 정보는 [README.md](README.md)를 참고하세요.
