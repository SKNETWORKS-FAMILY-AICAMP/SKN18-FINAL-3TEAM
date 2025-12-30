#!/bin/bash
# 병렬 테스트 실행 스크립트
# 80개 조합을 8개 워커로 분할하여 병렬 처리

NUM_WORKERS=8
LIMIT=${1:-0}
SAVE_EVERY=${2:-10}

echo "Starting parallel test execution with $NUM_WORKERS workers"
echo "Limit: $LIMIT"
echo "Save every: $SAVE_EVERY"
echo ""

# 각 워커를 백그라운드로 실행
for i in $(seq 0 $((NUM_WORKERS - 1))); do
    echo "Starting worker $i..."
    nohup python backend/ragas/fuseki/automated_test_runner.py \
        --limit "$LIMIT" \
        --save-every "$SAVE_EVERY" \
        --worker-id $i \
        --num-workers $NUM_WORKERS \
        > "ragas_test_worker${i}.log" 2>&1 &
    echo "Worker $i started (PID: $!)"
done

echo ""
echo "All workers started. Check logs: ragas_test_worker*.log"
echo "Monitor progress: tail -f ragas_test_worker*.log"
echo ""
echo "To check running processes: ps aux | grep automated_test_runner"
echo "To stop all workers: pkill -f automated_test_runner"

