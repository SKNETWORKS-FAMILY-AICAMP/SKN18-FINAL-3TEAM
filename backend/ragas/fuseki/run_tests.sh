#!/bin/bash

# Automated RAGAS Evaluation Test Runner
#
# Usage:
#   bash backend/ragas/fuseki/run_tests.sh
#   bash backend/ragas/fuseki/run_tests.sh --limit 5 --debug

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Fuseki RAG - RAGAS Evaluation${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

cd "$PROJECT_ROOT"

echo -e "${YELLOW}[INFO]${NC} Project Root: $PROJECT_ROOT"
echo -e "${YELLOW}[INFO]${NC} Working Directory: $(pwd)"
echo ""

# Python 가상환경 확인
if [ -d "venv" ]; then
    echo -e "${YELLOW}[INFO]${NC} Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${YELLOW}[INFO]${NC} Activating virtual environment..."
    source .venv/bin/activate
else
    echo -e "${YELLOW}[WARNING]${NC} No virtual environment found. Using system Python."
fi

# Fuseki 서버 확인
echo -e "${YELLOW}[INFO]${NC} Checking Fuseki server..."
FUSEKI_URL="${FUSEKI_URL:-http://localhost:3030}"

if curl -s "$FUSEKI_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC} Fuseki server is running at $FUSEKI_URL"
else
    echo -e "${RED}[ERROR]${NC} Fuseki server is not running at $FUSEKI_URL"
    echo -e "${YELLOW}[INFO]${NC} Please start Fuseki server first:"
    echo -e "  docker-compose up -d fuseki"
    exit 1
fi

echo ""

# 질문 파일 확인
QUESTIONS_FILE="backend/ragas/questions.jsonl"
if [ ! -f "$QUESTIONS_FILE" ]; then
    echo -e "${RED}[ERROR]${NC} Questions file not found: $QUESTIONS_FILE"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Questions file found: $QUESTIONS_FILE"
echo ""

# 결과 디렉토리 생성
RESULTS_DIR="backend/ragas/fuseki/results"
mkdir -p "$RESULTS_DIR"

echo -e "${YELLOW}[INFO]${NC} Results will be saved to: $RESULTS_DIR"
echo ""

# 테스트 실행
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Running Tests...${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# 기본 옵션
PERSONA="${PERSONA:-foreigner_culture_history}"
LIMIT="${LIMIT:-0}"
SAVE_EVERY="${SAVE_EVERY:-5}"

# 명령행 인자 전달
python backend/ragas/fuseki/automated_test_runner.py \
    --persona "$PERSONA" \
    --limit "$LIMIT" \
    --save-every "$SAVE_EVERY" \
    "$@"

# 종료 상태 확인
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}Tests Completed Successfully!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""

    # 최신 결과 파일 찾기
    LATEST_RESULT=$(ls -t "$RESULTS_DIR"/all_results_*.json 2>/dev/null | head -1)

    if [ -n "$LATEST_RESULT" ]; then
        echo -e "${YELLOW}[INFO]${NC} Latest result: $LATEST_RESULT"
        echo ""
        echo -e "${YELLOW}[INFO]${NC} To analyze results, run:"
        echo -e "  python backend/ragas/fuseki/results_analyzer.py --input $LATEST_RESULT --export-csv --export-report"
        echo ""
    fi
else
    echo ""
    echo -e "${RED}================================${NC}"
    echo -e "${RED}Tests Failed!${NC}"
    echo -e "${RED}================================${NC}"
    exit 1
fi
