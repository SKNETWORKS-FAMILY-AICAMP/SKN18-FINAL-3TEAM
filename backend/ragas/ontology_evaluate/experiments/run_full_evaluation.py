"""
80개 질문 전체 평가 (Quick Win 설정 적용)

80개 질문을 20개씩 4개 병렬 프로세스로 실행합니다.

Usage:
    python -m backend.ragas.ontology_evaluate.experiments.run_full_evaluation
"""

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
RESULTS_DIR = DATA_DIR / "full_evaluation_results"

# 테스트 질문 로드
TEST_QUERIES_PATH = DATA_DIR / "test_queries.json"
queries = load_queries(str(TEST_QUERIES_PATH))

# 병렬 실험 실행
run_parallel_experiment(
    items=queries,
    worker_module="backend.ragas.ontology_evaluate.experiments.evaluation_worker",
    results_dir=RESULTS_DIR,
    project_root=PROJECT_ROOT,
    batch_size=20,
    num_batches=4,
    batch_prefix="batch",
    wait_for_completion=False,
    merge_command="python -m backend.ragas.ontology_evaluate.experiments.merge_results --timestamp {timestamp}",
    verbose=True
)
