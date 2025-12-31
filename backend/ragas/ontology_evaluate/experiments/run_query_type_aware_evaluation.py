"""
Query-Type Aware Scoring System v4.0 실험 (병렬 실행)

v4.0 설정만 실행 (Baseline 실행하지 않음)
- v4.0: 쿼리 타입별 Component 점수 차별화 (80개 질문)
- 총 80개 실험셋

4개 병렬 프로세스로 실행:
- Batch 1: 질문 0-19 (20개 실험)
- Batch 2: 질문 20-39 (20개 실험)
- Batch 3: 질문 40-59 (20개 실험)
- Batch 4: 질문 60-79 (20개 실험)

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.run_query_type_aware_evaluation
"""

import json
from pathlib import Path
from datetime import datetime

from backend.ragas.ontology_evaluate.utils.experiment_utils import (
    load_queries,
    run_parallel_experiment
)

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
EVAL_DIR = BACKEND_DIR / "ragas" / "ontology_evaluate"
DATA_DIR = EVAL_DIR / "data"
RESULTS_DIR = DATA_DIR / "results_v4"

print(f"\n{'='*80}")
print("Query-Type Aware Scoring System v4.0 실험")
print(f"{'='*80}")
print(f"실험 설계:")
print(f"  - v4.0: Query-Type Aware (모든 Component 쿼리 타입별 점수)")
print(f"  - 질문 수: 80개")
print(f"  - 총 실험: 80개")
print(f"  - 병렬: 4개 프로세스 (배치당 20개 실험)")
print(f"{'='*80}\n")

# 테스트 질문 로드
TEST_QUERIES_PATH = DATA_DIR / "test_queries.json"
queries = load_queries(str(TEST_QUERIES_PATH))

# 병렬 실험 실행
run_parallel_experiment(
    items=queries,
    worker_module="backend.ragas.ontology_evaluate.experiments.query_type_aware_worker",
    results_dir=RESULTS_DIR,
    project_root=PROJECT_ROOT,
    batch_size=20,
    num_batches=4,
    batch_prefix="batch",
    wait_for_completion=False,
    merge_command="python -m backend.ragas.ontology_evaluate.experiments.merge_query_type_aware_results --timestamp {timestamp}",
    verbose=True
)
