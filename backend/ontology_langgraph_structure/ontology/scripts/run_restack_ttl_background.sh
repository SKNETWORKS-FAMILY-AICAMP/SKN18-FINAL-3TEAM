#!/bin/bash
# .restack 파일에 저장된 행 번호들만 TTL로 변환 (백그라운드 실행)

# 프로젝트 루트로 이동
cd "$(dirname "$0")/../../../.."

# 로그 파일 경로
LOG_DIR="backend/ontology_langgraph_structure/ontology/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/restack_ttl_generation_$(date +%Y%m%d_%H%M%S).log"

# .restack 파일 경로
RESTACK_FILE="backend/ontology_langgraph_structure/ontology/instances/.restack"

echo "=========================================="
echo "🚀 .restack TTL 재생성기 백그라운드 실행"
echo "=========================================="
echo ""

# .restack 파일 확인
if [ ! -f "$RESTACK_FILE" ]; then
    echo "❌ .restack 파일이 없습니다: $RESTACK_FILE"
    exit 1
fi

# .restack 파일 내용 확인
RESTACK_COUNT=$(grep -v '^$' "$RESTACK_FILE" | grep -c '^[0-9]')
if [ "$RESTACK_COUNT" -eq 0 ]; then
    echo "⚠️  .restack 파일에 처리할 행이 없습니다."
    exit 1
fi

echo "📋 .restack 파일: $RESTACK_FILE"
echo "📋 처리할 행 수: $RESTACK_COUNT개"
echo "📄 로그 파일: $LOG_FILE"
echo "✅ 실행 후 맥북을 덮어도 계속 실행됩니다 (caffeinate 사용)"
echo "✅ tail 명령어를 종료해도 Python 프로세스는 계속 실행됩니다"
echo ""
echo "⚠️  예상 소요 시간: 행 수 × 5~10초 (긴 텍스트 처리)"
echo ""

# nohup + caffeinate으로 백그라운드 실행
# - nohup: 터미널이 닫혀도 계속 실행
# - caffeinate: 맥북을 덮어도(sleep 모드) 계속 실행
# - python -u: unbuffered output (실시간 로그)
nohup bash -c "source .venv/bin/activate && caffeinate -i python -u backend/ontology_langgraph_structure/ontology/scripts/generate_restack_ttl.py" > "$LOG_FILE" 2>&1 &

# PID 저장
PID=$!
echo "🔢 프로세스 ID (PID): $PID"
echo "$PID" > "$LOG_DIR/restack_ttl_generator.pid"

echo ""
echo "================================"
echo "백그라운드 실행 완료!"
echo "================================"
echo ""
echo "📌 명령어:"
echo "   - 진행 상황 확인: tail -f $LOG_FILE"
echo "   - 실시간 확인: tail -f $LOG_FILE | grep '처리 중'"
echo "   - 프로세스 확인: ps -p $PID"
echo "   - 프로세스 종료: kill $PID"
echo ""
echo "📊 실시간 로그를 보시겠습니까? (y/n)"
read -t 3 -n 1 answer || answer="n"
if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
    echo ""
    echo "📺 실시간 로그 시작 (Ctrl+C로 종료해도 Python 프로세스는 계속 실행됩니다)..."
    echo ""
    tail -f "$LOG_FILE"
else
    echo ""
    echo "💡 나중에 로그를 보려면: tail -f $LOG_FILE"
fi

