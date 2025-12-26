"""
80개 질문 전체 평가 (Quick Win 설정 적용)

80개 질문을 20개씩 4개 병렬 프로세스로 실행합니다.

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.run_full_evaluation
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
EVAL_DIR = BACKEND_DIR / "ragas" / "ontology_evaluate"
DATA_DIR = EVAL_DIR / "data"
RESULTS_DIR = DATA_DIR / "full_evaluation_results"

# 결과 디렉토리 생성
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# 타임스탬프
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# 테스트 질문 로드
TEST_QUERIES_PATH = DATA_DIR / "test_queries.json"
with open(TEST_QUERIES_PATH, "r", encoding="utf-8") as f:
    queries = json.load(f)

print(f"총 {len(queries)}개 질문 로드 완료")

# 80개 질문을 20개씩 4개 그룹으로 분할
BATCH_SIZE = 20
NUM_BATCHES = 4

batches = []
for i in range(NUM_BATCHES):
    start_idx = i * BATCH_SIZE
    end_idx = min((i + 1) * BATCH_SIZE, len(queries))
    batch = queries[start_idx:end_idx]
    batches.append(batch)
    print(f"Batch {i+1}: {len(batch)}개 질문 (인덱스 {start_idx}-{end_idx-1})")

# 배치별 질문 파일 저장
batch_files = []
for i, batch in enumerate(batches):
    batch_file = DATA_DIR / f"batch_{i+1}_queries.json"
    with open(batch_file, "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)
    batch_files.append(batch_file)
    print(f"Batch {i+1} 파일 저장: {batch_file}")

# nohup으로 병렬 실행할 스크립트 생성
print("\n" + "="*80)
print("4개 병렬 프로세스 실행 시작")
print("="*80)

processes = []
log_files = []

for i in range(NUM_BATCHES):
    batch_num = i + 1
    batch_file = batch_files[i]
    output_file = RESULTS_DIR / f"batch_{batch_num}_results_{TIMESTAMP}.json"
    log_file = RESULTS_DIR / f"batch_{batch_num}_log_{TIMESTAMP}.txt"

    log_files.append(log_file)

    # Python 스크립트 경로
    worker_script = EVAL_DIR / "experiments" / "evaluation_worker.py"

    # nohup 명령어
    cmd = [
        "nohup",
        sys.executable,  # python3
        "-m", "backend.ragas.ontology_evaluate.experiments.evaluation_worker",
        "--batch-file", str(batch_file),
        "--output", str(output_file),
        "--batch-num", str(batch_num)
    ]

    # 로그 파일로 리다이렉트
    with open(log_file, "w") as log_f:
        process = subprocess.Popen(
            cmd,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT)
        )

    processes.append(process)
    print(f"✓ Batch {batch_num} 프로세스 시작 (PID: {process.pid})")
    print(f"  - 입력: {batch_file.name}")
    print(f"  - 출력: {output_file.name}")
    print(f"  - 로그: {log_file.name}")

print("\n" + "="*80)
print("모든 프로세스 실행 완료!")
print("="*80)
print(f"\n진행 상황 모니터링:")
for i, log_file in enumerate(log_files):
    print(f"  Batch {i+1}: tail -f {log_file}")

print(f"\n프로세스 상태 확인:")
for i, process in enumerate(processes):
    print(f"  Batch {i+1} PID: {process.pid}")

print(f"\n결과 파일 위치: {RESULTS_DIR}")
print(f"\n모든 프로세스가 완료되면 다음 명령어로 결과를 통합하세요:")
print(f"  python -m backend.ragas.ontology_evaluate.experiments.merge_results --timestamp {TIMESTAMP}")
