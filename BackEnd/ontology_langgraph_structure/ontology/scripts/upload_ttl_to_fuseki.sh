#!/bin/bash

# TTL 파일을 Fuseki에 직접 업로드 (Java Reasoner 없이)
# 메모리 부족 환경에서 사용

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTANCES_DIR="${SCRIPT_DIR}/../instances"
FUSEKI_URL="${FUSEKI_URL:-http://localhost:3030}"
DATASET="${DATASET:-korean-history}"

# Python 명령어 설정
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

echo "==================================="
echo "📝 TTL → Fuseki 직접 업로드 (경량 모드)"
echo "==================================="
echo ""
echo "⚠️ 이 모드는 Java Reasoner를 사용하지 않습니다."
echo "   SWRL 규칙 기반 추론은 수행되지 않습니다."
echo ""

# 1. TTL 정규화
echo "1️⃣ TTL 파일 정규화 중..."
$PYTHON_CMD "${SCRIPT_DIR}/normalize_ttl.py" \
  --input "${INSTANCES_DIR}/korean_history_instances.ttl" \
  --output "${INSTANCES_DIR}/korean_history_normalized.ttl"

if [ $? -ne 0 ]; then
  echo "❌ 정규화 실패"
  exit 1
fi

# 2. Fuseki 데이터셋 생성 (없으면)
echo ""
echo "2️⃣ Fuseki 데이터셋 확인/생성..."
DATASET_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "${FUSEKI_URL}/${DATASET}")

if [ "$DATASET_CHECK" = "200" ]; then
  echo "   ✅ 데이터셋 '${DATASET}' 존재"
else
  echo "   📦 데이터셋 '${DATASET}' 생성 중..."
  curl -X POST "${FUSEKI_URL}/\$/datasets" \
    -u admin:fuseki1234 \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "dbName=${DATASET}&dbType=mem" 2>/dev/null
  echo "   ✅ 데이터셋 생성 완료"
fi

# 3. 기존 데이터 삭제
echo ""
echo "3️⃣ 기존 데이터 삭제 중..."
curl -X POST "${FUSEKI_URL}/${DATASET}/update" \
  -u admin:fuseki1234 \
  --data-urlencode "update=CLEAR DEFAULT" \
  -H "Content-Type: application/x-www-form-urlencoded" 2>/dev/null
echo "   ✅ 기존 데이터 삭제 완료"

# 4. TTL 파일 직접 업로드
echo ""
echo "4️⃣ TTL 파일 업로드 중..."
TTL_FILE="${INSTANCES_DIR}/korean_history_normalized.ttl"

if [ ! -f "$TTL_FILE" ]; then
  echo "❌ TTL 파일이 없습니다: $TTL_FILE"
  exit 1
fi

FILE_SIZE=$(ls -lh "$TTL_FILE" | awk '{print $5}')
echo "   📄 파일: korean_history_normalized.ttl (${FILE_SIZE})"

curl -X POST "${FUSEKI_URL}/${DATASET}/data" \
  -u admin:fuseki1234 \
  -H "Content-Type: text/turtle" \
  --data-binary "@${TTL_FILE}" \
  -w "\n   ⏱️ 업로드 시간: %{time_total}초\n"

if [ $? -eq 0 ]; then
  echo "   ✅ 업로드 완료"
else
  echo "   ❌ 업로드 실패"
  exit 1
fi

# 5. 데이터 확인
echo ""
echo "5️⃣ 업로드된 데이터 확인..."
TRIPLE_COUNT=$(curl -s "${FUSEKI_URL}/${DATASET}/query" \
  --data-urlencode "query=SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }" \
  -H "Accept: application/sparql-results+json" | \
  $PYTHON_CMD -c "import sys, json; data=json.load(sys.stdin); print(data['results']['bindings'][0]['count']['value'])" 2>/dev/null)

if [ -n "$TRIPLE_COUNT" ]; then
  echo "   📊 총 트리플 수: ${TRIPLE_COUNT}"
else
  echo "   ⚠️ 트리플 수 확인 실패"
fi

echo ""
echo "==================================="
echo "✅ 경량 모드 업로드 완료!"
echo "==================================="
echo ""
echo "💡 사용 방법:"
echo "   export INFERENCE_MODE=light"
echo "   python main.py"
echo ""
echo "📌 참고:"
echo "   - Java Reasoner 없이 Fuseki에 직접 쿼리합니다"
echo "   - SWRL 규칙 기반 추론은 수행되지 않습니다"
echo "   - 기본 데이터에서 SPARQL 쿼리만 가능합니다"

