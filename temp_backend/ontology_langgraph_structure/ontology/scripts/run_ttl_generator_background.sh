#!/bin/bash
# TTL 생성기를 백그라운드에서 실행 (맥북 닫아도 계속 실행)

# 프로젝트 루트로 이동
cd "$(dirname "$0")/../../../.."

# 로그 파일 경로
LOG_DIR="backend/ontology_langgraph_structure/ontology/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/ttl_generation_$(date +%Y%m%d_%H%M%S).log"

echo "🚀 TTL 생성기를 백그라운드로 실행합니다..."
echo "📄 로그 파일: $LOG_FILE"
echo ""
echo "✅ 실행 후 맥북을 덮어도 계속 실행됩니다 (caffeinate 사용)"
echo "✅ tail 명령어를 종료해도 Python 프로세스는 계속 실행됩니다"
echo "📊 진행 상황 확인: tail -f $LOG_FILE"
echo ""

# nohup + caffeinate으로 백그라운드 실행
# - nohup: 터미널이 닫혀도 계속 실행
# - caffeinate: 맥북을 덮어도(sleep 모드) 계속 실행
# - python -u: unbuffered output (실시간 로그)
# 중요: tail을 종료해도 Python 프로세스는 계속 실행됩니다 (별도 프로세스)
nohup bash -c "source .venv/bin/activate && caffeinate -i python -u backend/ontology_langgraph_structure/ontology/scripts/llm_ttl_generator.py" > "$LOG_FILE" 2>&1 &

# PID 저장
PID=$!
echo "🔢 프로세스 ID (PID): $PID"
echo "$PID" > "$LOG_DIR/ttl_generator.pid"

echo ""
echo "================================"
echo "백그라운드 실행 완료!"
echo "================================"
echo ""
echo "📌 명령어:"
echo "   - 진행 상황 확인: tail -f $LOG_FILE"
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
