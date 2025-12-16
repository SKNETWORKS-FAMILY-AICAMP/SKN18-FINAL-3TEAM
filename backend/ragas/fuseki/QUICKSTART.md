# 빠른 시작 가이드 (Quick Start)

이 가이드는 RAGAS 평가 시스템을 빠르게 시작하는 방법을 설명합니다.

## 1. 준비 사항

### 필수 패키지 설치

```bash
pip install ragas pandas
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

## 2. 빠른 테스트 (5개 질문만)

처음 시작할 때는 소수의 질문으로 테스트하는 것을 추천합니다:

```bash
# 각 조합당 5개 질문만 테스트 (약 10-15분 소요)
python backend/ragas/fuseki/automated_test_runner.py --limit 5 --debug

# 또는 스크립트 사용
LIMIT=5 bash backend/ragas/fuseki/run_tests.sh
```

## 3. 결과 확인

테스트가 완료되면 `backend/ragas/fuseki/results/` 디렉토리에 결과가 저장됩니다:

```bash
# 최신 결과 파일 확인
ls -lt backend/ragas/fuseki/results/

# 예시 출력:
# all_results_20250116_144900.json
# summary_20250116_144900.json
```

## 4. 결과 분석

```bash
# 기본 분석 (콘솔에 출력)
python backend/ragas/fuseki/results_analyzer.py \
  --input backend/ragas/fuseki/results/all_results_20250116_144900.json

# CSV와 리포트 생성
python backend/ragas/fuseki/results_analyzer.py \
  --input backend/ragas/fuseki/results/all_results_20250116_144900.json \
  --export-csv \
  --export-report
```

이렇게 하면 다음 파일들이 생성됩니다:
- `all_results_20250116_144900_ranked.csv` - Excel에서 열 수 있는 순위표
- `all_results_20250116_144900_report.txt` - 텍스트 리포트

## 5. 전체 테스트 실행

빠른 테스트로 시스템이 잘 작동하는 것을 확인했다면, 전체 질문으로 테스트합니다:

```bash
# 전체 질문으로 테스트 (약 1-2시간 소요)
python backend/ragas/fuseki/automated_test_runner.py

# 또는 스크립트 사용
bash backend/ragas/fuseki/run_tests.sh
```

## 6. 예시 코드 실행

시스템의 동작을 이해하기 위해 예시 코드를 실행해볼 수 있습니다:

```bash
python backend/ragas/fuseki/example_usage.py
```

이 코드는 다음을 보여줍니다:
1. ConfigManager 사용법
2. 모든 테스트 설정 생성
3. RAGAS Metrics Loader 사용법
4. State에 설정 적용하기

## 7. 주요 옵션

### automated_test_runner.py

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--persona` | 테스트할 persona ID | `foreigner_culture_history` |
| `--limit` | 조합당 질문 수 제한 (0 = 제한 없음) | `0` |
| `--debug` | 디버그 모드 활성화 | `False` |
| `--save-every` | N개 조합마다 중간 저장 | `5` |

### 예시:

```bash
# Persona 변경
python backend/ragas/fuseki/automated_test_runner.py --persona kids_child

# 디버그 모드 + 질문 제한
python backend/ragas/fuseki/automated_test_runner.py --limit 3 --debug

# 자주 중간 저장 (2개 조합마다)
python backend/ragas/fuseki/automated_test_runner.py --save-every 2
```

## 8. 트러블슈팅

### 문제: RAGAS import 오류

```
ImportError: No module named 'ragas'
```

**해결:**
```bash
pip install ragas
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

### 문제: 결과 파일을 찾을 수 없음

**해결:**
```bash
# results 디렉토리 확인
ls -la backend/ragas/fuseki/results/

# 디렉토리가 없으면 생성
mkdir -p backend/ragas/fuseki/results/
```

## 9. 다음 단계

1. **결과 분석**: CSV 파일을 Excel이나 pandas로 열어서 상세 분석
2. **가중치 조정**: 최고 성능 조합의 가중치를 `config_manager.py`에 반영
3. **추가 테스트**: 다른 persona나 질문 세트로 검증

## 10. 주요 파일 위치

```
backend/ragas/fuseki/
├── automated_test_runner.py   # 메인 테스트 러너
├── results_analyzer.py         # 결과 분석기
├── config_manager.py           # 설정 관리자
├── ragas_metrics.py            # RAGAS 메트릭
├── run_tests.sh                # 실행 스크립트
├── example_usage.py            # 예시 코드
├── README.md                   # 상세 문서
└── results/                    # 결과 저장 디렉토리
    ├── all_results_*.json
    ├── summary_*.json
    └── *_ranked.csv
```

## 도움말

더 자세한 정보는 [README.md](README.md)를 참고하세요.
