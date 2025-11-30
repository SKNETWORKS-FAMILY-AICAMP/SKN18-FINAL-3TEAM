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
echo "✅ 실행 후 맥북을 닫아도 계속 실행됩니다"
echo "📊 진행 상황 확인: tail -f $LOG_FILE"
echo ""

# nohup으로 백그라운드 실행 (python-dotenv가 .env 자동 로드)
nohup bash -c "source .venv/bin/activate && python backend/ontology_langgraph_structure/ontology/scripts/llm_ttl_generator.py" > "$LOG_FILE" 2>&1 &

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
