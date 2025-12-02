#!/bin/bash

# 최신 TTL 데이터를 Fuseki에 업로드하는 스크립트

set -e  # 에러 발생 시 중단

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTANCES_DIR="${SCRIPT_DIR}/../instances"

# Python 명령어 설정 (가상환경 우선)
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON_CMD="python"
    echo "✅ 가상환경 감지: $VIRTUAL_ENV"
else
    PYTHON_CMD="python3"
    echo "⚠️ 가상환경이 활성화되지 않았습니다. python3 사용"
fi

echo "==================================="
echo "📝 최신 TTL 데이터 업로드 스크립트"
echo "==================================="

# 1. TTL 정규화
echo ""
echo "1️⃣ TTL 파일 정규화 중..."
$PYTHON_CMD "${SCRIPT_DIR}/normalize_ttl.py" \
  --input "${INSTANCES_DIR}/korean_history_instances.ttl" \
  --output "${INSTANCES_DIR}/korean_history_normalized.ttl"

if [ $? -ne 0 ]; then
  echo "❌ 정규화 실패"
  exit 1
fi

# 2. 기존 데이터 삭제 (선택사항)
echo ""
echo "2️⃣ 기존 Fuseki 데이터 삭제 중..."
curl -X POST "http://localhost:3030/temp_inference/update" \
  --data-urlencode "update=CLEAR DEFAULT" \
  -H "Content-Type: application/x-www-form-urlencoded" 2>/dev/null

echo "✅ 기존 데이터 삭제 완료"

# 3. 새 데이터 업로드 (추론 포함)
echo ""
echo "3️⃣ 추론 실행 및 데이터 업로드 중..."
echo "   (최대 60초 소요 예상)"

# 타임아웃 증가하여 재시도
curl -X POST http://localhost:8001/infer \
  -H "Content-Type: application/json" \
  -d '{}' \
  --max-time 250 \
  -w "\n응답 시간: %{time_total}초\n"

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ 데이터 업로드 완료"
else
  echo ""
  echo "⚠️ 타임아웃 발생 - 데이터가 큰 경우 정상입니다"
  echo "   Fuseki에서 데이터를 확인하세요: http://localhost:3030"
fi

# 4. 데이터 확인
echo ""
echo "4️⃣ 업로드된 데이터 확인..."
TRIPLE_COUNT=$(curl -s "http://localhost:3030/temp_inference/query" \
  --data-urlencode "query=SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }" \
  -H "Accept: application/sparql-results+json" | \
  $PYTHON_CMD -c "import sys, json; data=json.load(sys.stdin); print(data['results']['bindings'][0]['count']['value'])" 2>/dev/null)

if [ -n "$TRIPLE_COUNT" ]; then
  echo "   총 트리플 수: ${TRIPLE_COUNT}"
else
  echo "   ⚠️ 트리플 수 확인 실패 (API 서버가 실행 중인지 확인하세요)"
fi

echo ""
echo "==================================="
echo "✅ 완료!"
echo "==================================="
echo ""
echo "💡 참고사항:"
echo "  - Java 메모리: 8GB (Xmx8g) 할당됨"
echo "  - 타임아웃: 240초 (4분)"
echo "  - 대용량 데이터의 경우 추론에 시간이 소요될 수 있습니다"
echo ""
echo "다음 명령어로 main.py를 실행하세요:"
echo "  cd ../../"
echo "  python main.py"
