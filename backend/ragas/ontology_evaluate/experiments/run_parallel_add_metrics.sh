#!/bin/bash

# 배치 병렬 평가 메트릭 추가 실행 스크립트
#
# 3개 그룹을 병렬로 처리하여 평가 메트릭을 추가합니다.
#
# 사용법:
#   chmod +x run_parallel_add_metrics.sh
#   ./run_parallel_add_metrics.sh

# 프로젝트 루트로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../../../.."
cd "$PROJECT_ROOT"

echo "작업 디렉토리: $(pwd)"

# 로그 디렉토리
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# 배치 크기 설정
BATCH_SIZE=17

# 각 그룹별 배치 개수 계산 (배치 크기: 17)
# semantic_expander: 62개 → 4 batches (0-3)
# entity_boost: 83개 → 5 batches (0-4)
# thread: 111개 → 7 batches (0-6)

echo "=============================================="
echo "배치 병렬 평가 메트릭 추가 시작"
echo "=============================================="
echo "배치 크기: $BATCH_SIZE"
echo ""

# semantic_expander: 4개 배치
echo "🔵 Semantic Expander (4 batches)"
for i in {0..3}; do
    echo "  Starting batch $i..."
    nohup python -u -m backend.ragas.ontology_evaluate.experiments.add_metrics_batch \
        --group semantic_expander \
        --batch-size $BATCH_SIZE \
        --batch-num $i > "$LOG_DIR/semantic_batch_${i}.log" 2>&1 &
done

# entity_boost: 5개 배치
echo "🟢 Entity Boost (5 batches)"
for i in {0..4}; do
    echo "  Starting batch $i..."
    nohup python -u -m backend.ragas.ontology_evaluate.experiments.add_metrics_batch \
        --group entity_boost \
        --batch-size $BATCH_SIZE \
        --batch-num $i > "$LOG_DIR/entity_batch_${i}.log" 2>&1 &
done

# thread: 7개 배치
echo "🟡 Thread (7 batches)"
for i in {0..6}; do
    echo "  Starting batch $i..."
    nohup python -u -m backend.ragas.ontology_evaluate.experiments.add_metrics_batch \
        --group thread \
        --batch-size $BATCH_SIZE \
        --batch-num $i > "$LOG_DIR/thread_batch_${i}.log" 2>&1 &
done

echo ""
echo "=============================================="
echo "✅ 총 16개 배치 프로세스 시작 완료"
echo "=============================================="
echo ""
echo "진행 상황 모니터링:"
echo "  ps aux | grep add_metrics_batch | wc -l"
echo ""
echo "로그 확인:"
echo "  tail -f $LOG_DIR/semantic_batch_0.log"
echo "  tail -f $LOG_DIR/entity_batch_0.log"
echo "  tail -f $LOG_DIR/thread_batch_0.log"
echo ""

# 모든 백그라운드 프로세스 완료 대기
echo "⏳ 모든 배치 완료 대기 중..."
wait

echo ""
echo "=============================================="
echo "🎉 모든 배치 프로세스 완료!"
echo "=============================================="
echo ""
echo "완료 후 병합:"
echo "  python -m backend.ragas.ontology_evaluate.experiments.merge_batch_results --group all"
echo ""

# 모든 백그라운드 프로세스 완료 대기
wait

echo "=============================================="
echo "🎉 모든 배치 프로세스 완료!"
echo "=============================================="
echo ""
echo "다음 단계: 배치 결과 병합"
echo "  python -m backend.ragas.ontology_evaluate.experiments.merge_batch_results --group all"
