"""
Optimized Grid Search - Isolation 실험 기반 최적화된 설정 탐색

실험 기간: Isolation 실험 결과 기반
쿼리 범위: 41-60 (20개)
설정 수: 6개
총 실험: 120회

목적:
- Isolation 실험에서 발견한 최적 컴포넌트 조합 검증
- causal_chain + entity_properties + type_and_summary 기본 조합의 효과 확인
- temporal/outgoing 추가 시 시너지 확인
- entity_boost_mode 비교 (normalized vs exact)
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ========== Grid Search 설정 ==========

GRID_CONFIGS = [
    # 1. 권장 기본 설정 (Isolation 기반 최적)
    {
        "name": "recommended_default",
        "description": "Isolation 최적 컴포넌트 조합 (causal + entity_properties + type_and_summary + normalized)",
        "semantic_expander": {"temporal": False, "causal_chain": True, "pgvector": False},
        "aggregator_threads": {
            "outgoing_relations": False,
            "incoming_relations": False,  # ❌ 확정
            "entity_properties": True,
            "connected_entities": False,  # ❌ 확정
            "type_and_summary": True
        },
        "entity_boost_mode": "normalized"
    },

    # 2. causal + temporal 조합 (시너지 확인)
    {
        "name": "causal_temporal_combo",
        "description": "causal과 temporal 동시 활성화로 시너지 효과 확인",
        "semantic_expander": {"temporal": True, "causal_chain": True, "pgvector": False},
        "aggregator_threads": {
            "outgoing_relations": False,
            "incoming_relations": False,
            "entity_properties": True,
            "connected_entities": False,
            "type_and_summary": True
        },
        "entity_boost_mode": "normalized"
    },

    # 3. 최소 설정 (causal만 + type_and_summary만)
    {
        "name": "minimal",
        "description": "최소 컴포넌트로 성능 확인 (causal + type_and_summary만)",
        "semantic_expander": {"temporal": False, "causal_chain": True, "pgvector": False},
        "aggregator_threads": {
            "outgoing_relations": False,
            "incoming_relations": False,
            "entity_properties": False,
            "connected_entities": False,
            "type_and_summary": True
        },
        "entity_boost_mode": "normalized"
    },

    # 4. Thread 확장 (outgoing 추가)
    {
        "name": "with_outgoing",
        "description": "기본 설정 + outgoing_relations 추가",
        "semantic_expander": {"temporal": False, "causal_chain": True, "pgvector": False},
        "aggregator_threads": {
            "outgoing_relations": True,
            "incoming_relations": False,
            "entity_properties": True,
            "connected_entities": False,
            "type_and_summary": True
        },
        "entity_boost_mode": "normalized"
    },

    # 5. Entity Boost 비교 (exact)
    {
        "name": "with_exact_boost",
        "description": "normalized 대신 exact boost 모드 사용",
        "semantic_expander": {"temporal": False, "causal_chain": True, "pgvector": False},
        "aggregator_threads": {
            "outgoing_relations": False,
            "incoming_relations": False,
            "entity_properties": True,
            "connected_entities": False,
            "type_and_summary": True
        },
        "entity_boost_mode": "exact"
    },

    # 6. Ablation baseline 재현 (비교용)
    {
        "name": "ablation_baseline",
        "description": "Ablation 실험의 baseline 설정 재현 (모든 컴포넌트 활성화)",
        "semantic_expander": {"temporal": False, "causal_chain": False, "pgvector": False},
        "aggregator_threads": {
            "outgoing_relations": True,
            "incoming_relations": True,
            "entity_properties": True,
            "connected_entities": True,
            "type_and_summary": True
        },
        "entity_boost_mode": None
    }
]


def load_test_queries(queries_file: Path, start_idx: int = 41, end_idx: int = 60):
    """
    test_queries.json에서 지정된 범위의 쿼리 로드

    Args:
        queries_file: 쿼리 파일 경로
        start_idx: 시작 인덱스 (1-based, inclusive)
        end_idx: 종료 인덱스 (1-based, inclusive)

    Returns:
        선택된 쿼리 리스트
    """
    with open(queries_file, 'r', encoding='utf-8') as f:
        all_queries = json.load(f)

    # 1-based indexing을 0-based로 변환
    selected_queries = all_queries[start_idx - 1:end_idx]

    print(f"✅ 쿼리 로드 완료: {len(selected_queries)}개 (index {start_idx}-{end_idx})")

    # 쿼리 타입 분포 출력
    type_counts = {}
    for q in selected_queries:
        qtype = q.get("query_type", "unknown")
        type_counts[qtype] = type_counts.get(qtype, 0) + 1

    print("📊 쿼리 타입 분포:")
    for qtype, count in sorted(type_counts.items()):
        print(f"  - {qtype}: {count}개")

    return selected_queries


def save_grid_search_setup(output_dir: Path, configs: list, queries: list):
    """
    Grid Search 설정과 쿼리를 파일로 저장

    Args:
        output_dir: 출력 디렉토리
        configs: 설정 리스트
        queries: 쿼리 리스트
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 설정 저장
    configs_file = output_dir / "grid_configs.json"
    with open(configs_file, 'w', encoding='utf-8') as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)
    print(f"✅ 설정 저장: {configs_file}")

    # 쿼리 저장
    queries_file = output_dir / "grid_queries.json"
    with open(queries_file, 'w', encoding='utf-8') as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)
    print(f"✅ 쿼리 저장: {queries_file}")

    # 메타데이터 저장
    metadata = {
        "experiment_name": "optimized_grid_search",
        "created_at": datetime.now().isoformat(),
        "num_configs": len(configs),
        "num_queries": len(queries),
        "query_range": "41-60",
        "total_experiments": len(configs) * len(queries),
        "description": "Isolation 실험 기반 최적화된 설정 탐색"
    }
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"✅ 메타데이터 저장: {metadata_file}")


def save_batched_queries(output_dir: Path, queries: list, num_batches: int = 4):
    """
    쿼리를 배치로 나눠서 저장 (병렬 실행용)

    Args:
        output_dir: 출력 디렉토리
        queries: 전체 쿼리 리스트
        num_batches: 배치 수 (기본 4개)
    """
    batch_size = len(queries) // num_batches
    remainder = len(queries) % num_batches

    for batch_idx in range(num_batches):
        # 배치 크기 계산 (나머지를 앞쪽 배치에 분배)
        start_idx = batch_idx * batch_size + min(batch_idx, remainder)
        end_idx = start_idx + batch_size + (1 if batch_idx < remainder else 0)

        batch_queries = queries[start_idx:end_idx]

        # 배치 쿼리 저장
        batch_file = output_dir / f"batch_{batch_idx + 1}_queries.json"
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch_queries, f, indent=2, ensure_ascii=False)

        print(f"  - Batch {batch_idx + 1}: {len(batch_queries)}개 쿼리 (index {start_idx}-{end_idx - 1}) → {batch_file.name}")


def generate_parallel_worker_script(output_dir: Path, num_batches: int = 4):
    """
    4개 병렬 nohup 실행 스크립트 생성

    Args:
        output_dir: 출력 디렉토리
        num_batches: 배치 수 (기본 4개)
    """
    script_content = """#!/bin/bash
# Optimized Grid Search - 4개 병렬 실행 (nohup)
#
# 사용법:
#   chmod +x run_parallel_grid_search.sh
#   ./run_parallel_grid_search.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

echo "=========================================="
echo "Optimized Grid Search - 병렬 실행 시작"
echo "=========================================="
echo "프로젝트 루트: $PROJECT_ROOT"
echo "출력 디렉토리: $SCRIPT_DIR"
echo "병렬 프로세스: 4개"
echo ""

cd "$PROJECT_ROOT"

# Python 경로 설정
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 로그 디렉토리 생성
mkdir -p "$SCRIPT_DIR/logs"

# 4개 프로세스 병렬 실행
for BATCH in {1..4}; do
    echo "🚀 Batch $BATCH 시작..."
    nohup python -m backend.ragas.ontology_evaluate.experiments.grid_search.grid_search_worker \\
        --config-file "$SCRIPT_DIR/grid_configs.json" \\
        --queries-file "$SCRIPT_DIR/batch_${BATCH}_queries.json" \\
        --output "$SCRIPT_DIR/batch_${BATCH}_results.json" \\
        --batch-num $BATCH \\
        > "$SCRIPT_DIR/logs/batch_${BATCH}.log" 2>&1 &

    echo "  → PID: $!"
    echo "  → Log: $SCRIPT_DIR/logs/batch_${BATCH}.log"
done

echo ""
echo "=========================================="
echo "✅ 모든 배치 시작 완료!"
echo "=========================================="
echo ""
echo "진행 상황 모니터링:"
echo "  tail -f $SCRIPT_DIR/logs/batch_1.log"
echo "  tail -f $SCRIPT_DIR/logs/batch_2.log"
echo "  tail -f $SCRIPT_DIR/logs/batch_3.log"
echo "  tail -f $SCRIPT_DIR/logs/batch_4.log"
echo ""
echo "모든 프로세스 확인:"
echo "  ps aux | grep grid_search_worker"
echo ""
echo "완료 후 결과 병합:"
echo "  python -m backend.ragas.ontology_evaluate.experiments.grid_search.merge_results \\\\"
echo "      --input $SCRIPT_DIR/batch_*_results.json \\\\"
echo "      --output $SCRIPT_DIR/grid_results_merged.json"
echo ""
"""

    script_file = output_dir / "run_parallel_grid_search.sh"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)

    # 실행 권한 부여
    import os
    os.chmod(script_file, 0o755)

    print(f"✅ 병렬 실행 스크립트 생성: {script_file}")


def main():
    """Main 실행 함수"""

    print("\n" + "="*70)
    print("Optimized Grid Search - Setup")
    print("="*70)
    print()

    # 경로 설정
    base_dir = PROJECT_ROOT / "backend" / "ragas" / "ontology_evaluate"
    queries_file = base_dir / "data" / "test_queries.json"
    output_dir = base_dir / "data" / "grid_search_optimized"  # data/ 직속에 저장

    # 1. 쿼리 로드 (41-60번)
    print("📂 Step 1: 쿼리 로드")
    queries = load_test_queries(queries_file, start_idx=41, end_idx=60)
    print()

    # 2. Grid Search 설정 출력
    print("⚙️  Step 2: Grid Search 설정")
    print(f"총 설정 수: {len(GRID_CONFIGS)}개")
    print(f"총 쿼리 수: {len(queries)}개")
    print(f"총 실험 횟수: {len(GRID_CONFIGS) * len(queries)}회")
    print()

    print("설정 목록:")
    for i, config in enumerate(GRID_CONFIGS, 1):
        print(f"  {i}. {config['name']}")
        print(f"     - {config['description']}")
    print()

    # 3. 파일 저장
    print("💾 Step 3: 파일 저장")
    save_grid_search_setup(output_dir, GRID_CONFIGS, queries)
    print()

    # 4. 배치 쿼리 저장 (병렬 실행용)
    print("📦 Step 4: 배치 쿼리 분할 (4개 병렬)")
    save_batched_queries(output_dir, queries, num_batches=4)
    print()

    # 5. 병렬 실행 스크립트 생성
    print("📜 Step 5: 병렬 실행 스크립트 생성")
    generate_parallel_worker_script(output_dir, num_batches=4)
    print()

    # 6. 다음 단계 안내
    print("="*70)
    print("✅ Setup 완료!")
    print("="*70)
    print()
    print("📊 실험 정보:")
    print(f"  - 총 설정 수: {len(GRID_CONFIGS)}개")
    print(f"  - 총 쿼리 수: {len(queries)}개")
    print(f"  - 배치 수: 4개 (병렬)")
    print(f"  - 배치당 쿼리: {len(queries) // 4}개")
    print(f"  - 총 실험 횟수: {len(GRID_CONFIGS) * len(queries)}회")
    print()
    print("다음 단계:")
    print()
    print("1️⃣  병렬 실행 (권장):")
    print(f"   cd {output_dir}")
    print("   ./run_parallel_grid_search.sh")
    print()
    print("2️⃣  진행 상황 모니터링:")
    print(f"   tail -f {output_dir}/logs/batch_1.log")
    print(f"   tail -f {output_dir}/logs/batch_2.log")
    print()
    print("3️⃣  실험 완료 후 결과 병합:")
    print(f"   cd {PROJECT_ROOT}")
    print("   python -m backend.ragas.ontology_evaluate.experiments.grid_search.merge_results \\")
    print(f"       --output-dir {output_dir}")
    print()
    print("4️⃣  결과 분석:")
    print("   python -m backend.ragas.ontology_evaluate.experiments.grid_search.analyze_grid_results \\")
    print(f"       --results {output_dir}/grid_results_merged.json")
    print()


if __name__ == "__main__":
    main()
