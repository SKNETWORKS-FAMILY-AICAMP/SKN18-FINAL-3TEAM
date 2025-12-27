#!/bin/bash
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
    nohup python -m backend.ragas.ontology_evaluate.experiments.grid_search.grid_search_worker \
        --config-file "$SCRIPT_DIR/grid_configs.json" \
        --queries-file "$SCRIPT_DIR/batch_${BATCH}_queries.json" \
        --output "$SCRIPT_DIR/batch_${BATCH}_results.json" \
        --batch-num $BATCH \
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
echo "  python -m backend.ragas.ontology_evaluate.experiments.grid_search.merge_results \\"
echo "      --input $SCRIPT_DIR/batch_*_results.json \\"
echo "      --output $SCRIPT_DIR/grid_results_merged.json"
echo ""
