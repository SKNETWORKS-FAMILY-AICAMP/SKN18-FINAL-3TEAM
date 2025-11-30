#!/bin/bash
# 전체 CSV 데이터 TTL 변환 (백그라운드 실행)

# 프로젝트 루트로 이동
cd "$(dirname "$0")/../../../.."

# 로그 파일 경로
LOG_DIR="backend/ontology_langgraph_structure/ontology/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/full_ttl_generation_$(date +%Y%m%d_%H%M%S).log"

echo "=========================================="
echo "🚀 전체 TTL 생성기 백그라운드 실행"
echo "=========================================="
echo ""
echo "📄 로그 파일: $LOG_FILE"
echo "✅ 실행 후 맥북을 덮어도 계속 실행됩니다 (caffeinate 사용)"
echo "✅ tail 명령어를 종료해도 Python 프로세스는 계속 실행됩니다"
echo ""
echo "⚠️  예상 소요 시간: CSV 행 수 × 2~3초"
echo "   (예: 1000개 = 약 30~50분)"
echo ""

# nohup + caffeinate으로 백그라운드 실행
# - nohup: 터미널이 닫혀도 계속 실행
# - caffeinate: 맥북을 덮어도(sleep 모드) 계속 실행
# - python -u: unbuffered output (실시간 로그)
# 중요: tail을 종료해도 Python 프로세스는 계속 실행됩니다 (별도 프로세스)
nohup bash -c "source .venv/bin/activate && caffeinate -i python -u backend/ontology_langgraph_structure/ontology/scripts/generate_all_ttl.py" > "$LOG_FILE" 2>&1 &

# PID 저장
PID=$!
echo "🔢 프로세스 ID (PID): $PID"
echo "$PID" > "$LOG_DIR/full_ttl_generator.pid"

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
