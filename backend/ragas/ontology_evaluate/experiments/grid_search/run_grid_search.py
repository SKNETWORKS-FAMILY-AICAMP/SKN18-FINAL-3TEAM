"""
Grid Search 실행 스크립트

Quick Win 실험 결과를 바탕으로 효율적인 파라미터 탐색 수행
- Semantic Expander: 주요 조합만 (Quick Win: OFF가 최적이지만 검증 필요)
- Thread Weight: incoming/outgoing 가중치 탐색
- Entity Boost: normalized/partial 가중치 탐색

실행 방법:
    python -m backend.ragas.ontology_evaluate.experiments.grid_search.run_grid_search

결과:
    data/grid_search_results/grid_search_results_{timestamp}.json
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from itertools import product

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
RESULTS_DIR = DATA_DIR / "grid_search_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Grid Search 파라미터 정의
# ============================================================
# Quick Win 실험 결과 기반 효율적 탐색:
# - Semantic Expander: OFF가 최적이었으나, 쿼리 타입별로 다를 수 있음
# - Thread: incoming 0.0이 최적, outgoing도 검증 필요
# - Entity Boost: 1.5가 추정치, 실제 최적값 탐색 필요
# ============================================================

GRID_PARAMS = {
    # Semantic Expander (Quick Win: 모두 OFF가 최적)
    # → 3가지 조합만 테스트: all_off, causal_only, temporal_causal
    "semantic_expander": [
        {"temporal": False, "causal_chain": False, "pgvector": False, "name": "se_off"},
        {"temporal": False, "causal_chain": True, "pgvector": False, "name": "se_causal"},
        {"temporal": True, "causal_chain": True, "pgvector": False, "name": "se_temporal_causal"},
    ],
    
    # Thread Weights (Quick Win: incoming=0.0이 최적)
    # → incoming/outgoing 가중치 조합 탐색
    "thread_weights": [
        {"incoming": 0.0, "outgoing": 1.0, "name": "thread_no_incoming"},
        {"incoming": 0.5, "outgoing": 1.0, "name": "thread_half_incoming"},
        {"incoming": 1.0, "outgoing": 1.0, "name": "thread_full"},
        {"incoming": 0.0, "outgoing": 0.0, "name": "thread_minimal"},
    ],
    
    # Entity Boost (Quick Win: 1.5 추정치)
    # → normalized/partial 가중치 탐색
    "entity_boost": [
        {"normalized": 1.0, "partial": 1.0, "name": "boost_baseline"},
        {"normalized": 1.5, "partial": 1.0, "name": "boost_normalized"},
        {"normalized": 1.0, "partial": 1.5, "name": "boost_partial"},
        {"normalized": 1.5, "partial": 1.5, "name": "boost_both"},
        {"normalized": 2.0, "partial": 1.5, "name": "boost_strong_normalized"},
    ],
}

# 총 조합: 3 × 4 × 5 = 60가지


def generate_all_configs():
    """모든 파라미터 조합 생성"""
    configs = []
    
    for se, thread, boost in product(
        GRID_PARAMS["semantic_expander"],
        GRID_PARAMS["thread_weights"],
        GRID_PARAMS["entity_boost"]
    ):
        config_name = f"{se['name']}_{thread['name']}_{boost['name']}"
        config = {
            "name": config_name,
            "semantic_expander": {
                "temporal": se["temporal"],
                "causal_chain": se["causal_chain"],
                "pgvector": se["pgvector"]
            },
            "thread_weights": {
                "incoming_relations": thread["incoming"],
                "outgoing_relations": thread["outgoing"],
                "connected_entities": 1.0,
                "entity_properties": 1.0,
                "type_and_summary": 1.0
            },
            "entity_boost": {
                "normalized": boost["normalized"],
                "partial": boost["partial"],
                "exact": 1.0
            }
        }
        configs.append(config)
    
    return configs


def select_test_queries(n=20):
    """
    테스트 질문 20개 선별 (쿼리 타입별 균등 배분)
    - factual: 5개
    - causal: 5개
    - comparative: 5개
    - deep_analysis: 5개
    """
    queries_file = DATA_DIR / "test_queries.json"
    
    with open(queries_file, "r", encoding="utf-8") as f:
        all_queries = json.load(f)
    
    # 쿼리 타입별 분류
    by_type = {"factual": [], "causal": [], "comparative": [], "deep_analysis": []}
    for q in all_queries:
        qtype = q.get("query_type", "deep_analysis")
        if qtype in by_type:
            by_type[qtype].append(q)
    
    # 각 타입에서 5개씩 선별 (난이도 다양하게)
    selected = []
    for qtype, queries in by_type.items():
        # 난이도별로 정렬하여 다양하게 선택
        easy = [q for q in queries if q.get("difficulty") == "easy"]
        medium = [q for q in queries if q.get("difficulty") == "medium"]
        hard = [q for q in queries if q.get("difficulty") == "hard"]
        
        # easy 2개, medium 1개, hard 2개 (또는 가능한 만큼)
        type_selected = []
        type_selected.extend(easy[:2])
        type_selected.extend(medium[:1])
        type_selected.extend(hard[:2])
        
        # 부족하면 나머지에서 채움
        if len(type_selected) < 5:
            remaining = [q for q in queries if q not in type_selected]
            type_selected.extend(remaining[:5 - len(type_selected)])
        
        selected.extend(type_selected[:5])
    
    return selected[:n]


def split_configs_for_parallel(configs, n_workers=4):
    """설정을 n개 워커로 분할"""
    batches = [[] for _ in range(n_workers)]
    for i, config in enumerate(configs):
        batches[i % n_workers].append(config)
    return batches


def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("=" * 80)
    print("Grid Search 실행")
    print("=" * 80)
    print(f"시작 시간: {datetime.now()}")
    
    # 1. 모든 설정 조합 생성
    all_configs = generate_all_configs()
    print(f"\n총 설정 조합: {len(all_configs)}개")
    print(f"  - Semantic Expander: {len(GRID_PARAMS['semantic_expander'])}가지")
    print(f"  - Thread Weights: {len(GRID_PARAMS['thread_weights'])}가지")
    print(f"  - Entity Boost: {len(GRID_PARAMS['entity_boost'])}가지")
    
    # 2. 테스트 질문 선별
    test_queries = select_test_queries(n=20)
    print(f"\n테스트 질문: {len(test_queries)}개")
    for qtype in ["factual", "causal", "comparative", "deep_analysis"]:
        count = len([q for q in test_queries if q.get("query_type") == qtype])
        print(f"  - {qtype}: {count}개")
    
    # 3. 질문 파일 저장
    queries_file = RESULTS_DIR / f"grid_search_queries_{timestamp}.json"
    with open(queries_file, "w", encoding="utf-8") as f:
        json.dump(test_queries, f, ensure_ascii=False, indent=2)
    print(f"\n질문 파일 저장: {queries_file}")
    
    # 4. 설정을 4개 배치로 분할
    config_batches = split_configs_for_parallel(all_configs, n_workers=4)
    print(f"\n배치 분할:")
    for i, batch in enumerate(config_batches, 1):
        print(f"  - Batch {i}: {len(batch)}개 설정")
    
    # 5. 배치별 설정 파일 저장
    batch_files = []
    for i, batch in enumerate(config_batches, 1):
        batch_file = RESULTS_DIR / f"batch_{i}_configs_{timestamp}.json"
        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)
        batch_files.append(batch_file)
        print(f"  배치 {i} 설정 저장: {batch_file}")
    
    # 6. 4개 병렬 프로세스 실행 (nohup)
    print("\n" + "=" * 80)
    print("병렬 프로세스 시작 (nohup)")
    print("=" * 80)
    
    worker_script = SCRIPT_DIR / "grid_search_worker.py"
    
    for i, batch_file in enumerate(batch_files, 1):
        output_file = RESULTS_DIR / f"batch_{i}_results_{timestamp}.json"
        log_file = RESULTS_DIR / f"batch_{i}_log_{timestamp}.txt"
        
        cmd = [
            "nohup", "python", "-m",
            "backend.ragas.ontology_evaluate.experiments.grid_search.grid_search_worker",
            "--config-file", str(batch_file),
            "--queries-file", str(queries_file),
            "--output", str(output_file),
            "--batch-num", str(i)
        ]
        
        with open(log_file, "w") as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=str(PROJECT_ROOT)
            )
        
        print(f"  Batch {i} 시작: PID={process.pid}")
        print(f"    설정 파일: {batch_file}")
        print(f"    출력 파일: {output_file}")
        print(f"    로그 파일: {log_file}")
    
    # 7. 실행 정보 저장
    run_info = {
        "timestamp": timestamp,
        "total_configs": len(all_configs),
        "total_queries": len(test_queries),
        "total_runs": len(all_configs) * len(test_queries),
        "n_workers": 4,
        "batch_files": [str(f) for f in batch_files],
        "queries_file": str(queries_file),
        "grid_params": {
            "semantic_expander": [s["name"] for s in GRID_PARAMS["semantic_expander"]],
            "thread_weights": [t["name"] for t in GRID_PARAMS["thread_weights"]],
            "entity_boost": [e["name"] for e in GRID_PARAMS["entity_boost"]]
        }
    }
    
    info_file = RESULTS_DIR / f"run_info_{timestamp}.json"
    with open(info_file, "w", encoding="utf-8") as f:
        json.dump(run_info, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 80)
    print("Grid Search 시작 완료")
    print("=" * 80)
    print(f"\n총 실행 횟수: {len(all_configs)} 설정 × {len(test_queries)} 질문 = {len(all_configs) * len(test_queries)}회")
    print(f"예상 소요 시간: 약 {len(all_configs) * len(test_queries) * 1 // 60}분 ~ {len(all_configs) * len(test_queries) * 2 // 60}분")
    print(f"\n진행 상황 확인:")
    print(f"  tail -f {RESULTS_DIR}/batch_1_log_{timestamp}.txt")
    print(f"\n결과 통합:")
    print(f"  python -m backend.ragas.ontology_evaluate.experiments.grid_search.merge_grid_results --timestamp {timestamp}")


if __name__ == "__main__":
    main()