#!/bin/bash

# ==============================================================================
# TTL 데이터 설정 스크립트
# ==============================================================================
# 순서:
#   1. TTL 정규화 (normalize_ttl.py)
#   2. Fuseki 업로드 (curl)
#   3. 프로퍼티 그룹 생성 (extract_property_groups.py)
# ==============================================================================

set -e  # 오류 발생 시 즉시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 경로 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTANCES_DIR="$SCRIPT_DIR/../instances"
INPUT_TTL="$INSTANCES_DIR/korean_history_instances.ttl"
OUTPUT_TTL="$INSTANCES_DIR/korean_history_normalized.ttl"
PROPERTY_GROUPS_JSON="$INSTANCES_DIR/property_groups.json"
NORMALIZE_SCRIPT="$SCRIPT_DIR/normalize_ttl.py"
EXTRACT_SCRIPT="$SCRIPT_DIR/extract_property_groups.py"

# Fuseki 설정
FUSEKI_URL="${FUSEKI_URL:-http://localhost:3030}"
DATASET="${DATASET:-korean-history}"
FUSEKI_USER="${FUSEKI_USER:-admin}"
FUSEKI_PASSWORD="${FUSEKI_PASSWORD:-fuseki1234}"

# ==============================================================================
# 1단계: TTL 정규화
# ==============================================================================

echo ""
echo "======================================================================"
echo "[1/3] TTL 정규화"
echo "======================================================================"
echo "입력:  $INPUT_TTL"
echo "출력:  $OUTPUT_TTL"
echo ""

if [ ! -f "$INPUT_TTL" ]; then
    echo -e "${RED}ERROR: 입력 파일이 없습니다: $INPUT_TTL${NC}"
    exit 1
fi

if [ ! -f "$NORMALIZE_SCRIPT" ]; then
    echo -e "${RED}ERROR: 정규화 스크립트가 없습니다: $NORMALIZE_SCRIPT${NC}"
    exit 1
fi

echo "정규화 실행 중..."
python3 "$NORMALIZE_SCRIPT" \
    --input "$INPUT_TTL" \
    --output "$OUTPUT_TTL"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}SUCCESS: 정규화 완료${NC}"
else
    echo -e "${RED}ERROR: 정규화 실패${NC}"
    exit 1
fi

echo ""

# ==============================================================================
# 2단계: Fuseki 업로드
# ==============================================================================

echo "======================================================================"
echo "[2/3] Fuseki 업로드"
echo "======================================================================"
echo "Fuseki URL: $FUSEKI_URL"
echo "데이터셋:   $DATASET"
echo "파일:       $OUTPUT_TTL"
echo ""

# Fuseki 서버 연결 확인
echo "Fuseki 서버 연결 확인 중..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$FUSEKI_URL")

if [ "$HTTP_CODE" != "200" ]; then
    echo -e "${RED}ERROR: Fuseki 서버에 연결할 수 없습니다 ($FUSEKI_URL)${NC}"
    echo -e "${YELLOW}힌트: docker-compose up -d fuseki 로 Fuseki를 시작하세요${NC}"
    exit 1
fi

echo -e "${GREEN}OK: Fuseki 서버 연결 성공${NC}"
echo ""

# 데이터셋 존재 확인
echo "데이터셋 확인 중..."
DATASET_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "$FUSEKI_URL/$DATASET")

if [ "$DATASET_CHECK" == "404" ]; then
    echo "데이터셋 '$DATASET'가 없습니다. 생성 중..."

    curl -X POST "$FUSEKI_URL/$/datasets" \
        -u "$FUSEKI_USER:$FUSEKI_PASSWORD" \
        -d "dbName=$DATASET" \
        -d "dbType=tdb2" \
        -s -o /dev/null

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}OK: 데이터셋 생성 완료${NC}"
    else
        echo -e "${RED}ERROR: 데이터셋 생성 실패${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}OK: 데이터셋 존재${NC}"
fi

echo ""

# 기존 데이터 삭제
echo "기존 데이터 삭제 중..."
curl -X POST "$FUSEKI_URL/$DATASET/update" \
    -u "$FUSEKI_USER:$FUSEKI_PASSWORD" \
    -H "Content-Type: application/sparql-update" \
    -d "DROP ALL" \
    -s -o /dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}OK: 기존 데이터 삭제 완료${NC}"
else
    echo -e "${YELLOW}WARNING: 기존 데이터 삭제 실패 (데이터가 없을 수 있음)${NC}"
fi

echo ""

# TTL 파일 업로드
echo "TTL 파일 업로드 중..."
FILE_SIZE=$(du -h "$OUTPUT_TTL" | cut -f1)
echo "파일 크기: $FILE_SIZE"

curl -X POST "$FUSEKI_URL/$DATASET/data" \
    -u "$FUSEKI_USER:$FUSEKI_PASSWORD" \
    -H "Content-Type: text/turtle" \
    --data-binary "@$OUTPUT_TTL" \
    -s -o /dev/null \
    -w "HTTP Status: %{http_code}\n"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}SUCCESS: TTL 업로드 완료${NC}"
else
    echo -e "${RED}ERROR: TTL 업로드 실패${NC}"
    exit 1
fi

echo ""

# 업로드 확인 (트리플 개수 조회)
echo "업로드 확인 중..."
TRIPLE_COUNT=$(curl -s "$FUSEKI_URL/$DATASET/query" \
    --data-urlencode "query=SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }" \
    -H "Accept: application/sparql-results+json" | \
    python3 -c "import sys, json; print(json.load(sys.stdin)['results']['bindings'][0]['count']['value'])")

if [ -n "$TRIPLE_COUNT" ]; then
    echo -e "${GREEN}OK: 업로드된 트리플 개수: $TRIPLE_COUNT${NC}"
else
    echo -e "${YELLOW}WARNING: 트리플 개수 확인 실패${NC}"
fi

echo ""

# ==============================================================================
# 3단계: 프로퍼티 그룹 생성
# ==============================================================================

echo "======================================================================"
echo "[3/3] 프로퍼티 그룹 생성"
echo "======================================================================"
echo "입력:  $OUTPUT_TTL"
echo "출력:  $PROPERTY_GROUPS_JSON"
echo ""

if [ ! -f "$EXTRACT_SCRIPT" ]; then
    echo -e "${RED}ERROR: 프로퍼티 추출 스크립트가 없습니다: $EXTRACT_SCRIPT${NC}"
    exit 1
fi

echo "프로퍼티 그룹 추출 중..."
python3 "$EXTRACT_SCRIPT" \
    --input "$OUTPUT_TTL" \
    --output "$PROPERTY_GROUPS_JSON"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}SUCCESS: 프로퍼티 그룹 생성 완료${NC}"
else
    echo -e "${RED}ERROR: 프로퍼티 그룹 생성 실패${NC}"
    exit 1
fi

echo ""

# ==============================================================================
# 완료
# ==============================================================================

echo "======================================================================"
echo "설정 완료"
echo "======================================================================"
echo ""
echo "생성된 파일:"
echo "  - 정규화된 TTL:      $OUTPUT_TTL"
echo "  - 프로퍼티 그룹:     $PROPERTY_GROUPS_JSON"
echo ""
echo "Fuseki 정보:"
echo "  - URL:               $FUSEKI_URL/$DATASET"
echo "  - SPARQL 엔드포인트: $FUSEKI_URL/$DATASET/sparql"
echo "  - 트리플 개수:       $TRIPLE_COUNT"
echo ""
echo -e "${GREEN}모든 설정이 완료되었습니다!${NC}"
echo ""
