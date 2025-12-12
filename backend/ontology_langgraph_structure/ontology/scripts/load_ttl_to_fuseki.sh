#!/bin/bash

# ==============================================================================
# Fuseki TTL 업로드 스크립트 (팀원용)
# ==============================================================================
# 사용법:
#   ./load_ttl_to_fuseki.sh [TTL 파일 경로]
#
# 예시:
#   ./load_ttl_to_fuseki.sh normalized_file.ttl
#   ./load_ttl_to_fuseki.sh ../instances/korean_history_normalized.ttl
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

# 명령줄 인자 처리
if [ $# -eq 0 ]; then
    # 인자가 없으면 기본 경로 사용
    OUTPUT_TTL="${OUTPUT_TTL:-$INSTANCES_DIR/korean_history_normalized.ttl}"
else
    # 인자가 있으면 해당 경로 사용 (상대 경로는 스크립트 디렉토리 기준)
    if [ -f "$1" ]; then
        OUTPUT_TTL="$1"
    elif [ -f "$SCRIPT_DIR/$1" ]; then
        OUTPUT_TTL="$SCRIPT_DIR/$1"
    elif [ -f "$INSTANCES_DIR/$1" ]; then
        OUTPUT_TTL="$INSTANCES_DIR/$1"
    else
        echo -e "${RED}ERROR: 파일을 찾을 수 없습니다: $1${NC}"
        echo "사용법: $0 [TTL 파일 경로]"
        exit 1
    fi
fi

# Fuseki 설정 (환경 변수 또는 기본값)
FUSEKI_URL="${FUSEKI_URL:-http://localhost:3030}"
DATASET="${DATASET:-korean-history}"
FUSEKI_USER="${FUSEKI_USER:-admin}"
FUSEKI_PASSWORD="${FUSEKI_PASSWORD:-${FUSEKI_ADMIN_PASSWORD:-fuseki1234}}"

# 파일 존재 확인
if [ ! -f "$OUTPUT_TTL" ]; then
    echo -e "${RED}ERROR: TTL 파일이 없습니다: $OUTPUT_TTL${NC}"
    exit 1
fi

echo "======================================================================"
echo "Fuseki 업로드 (팀원용)"
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

HTTP_CODE=$(curl -X POST "$FUSEKI_URL/$DATASET/data" \
    -u "$FUSEKI_USER:$FUSEKI_PASSWORD" \
    -H "Content-Type: text/turtle" \
    --data-binary "@$OUTPUT_TTL" \
    -s -o /tmp/fuseki_upload_error.txt \
    -w "%{http_code}" \
    --max-time 300)

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    echo -e "${GREEN}SUCCESS: TTL 업로드 완료${NC}"
elif [ "$HTTP_CODE" = "400" ]; then
    echo -e "${RED}ERROR: TTL 파일 구문 오류 (400)${NC}"
    echo "오류 상세:"
    cat /tmp/fuseki_upload_error.txt 2>/dev/null | head -10
    exit 1
elif [ "$HTTP_CODE" = "401" ]; then
    echo -e "${RED}ERROR: 인증 실패 (401) - Fuseki 사용자명/비밀번호를 확인하세요${NC}"
    exit 1
elif [ "$HTTP_CODE" = "404" ]; then
    echo -e "${RED}ERROR: 데이터셋을 찾을 수 없습니다 (404)${NC}"
    exit 1
else
    echo -e "${YELLOW}WARNING: HTTP $HTTP_CODE - 업로드 상태 불명확${NC}"
    cat /tmp/fuseki_upload_error.txt 2>/dev/null | head -10
fi

echo ""

# 업로드 확인 (트리플 개수 조회)
echo "업로드 확인 중..."
TRIPLE_COUNT=$(curl -s -X POST "$FUSEKI_URL/$DATASET/sparql" \
    -u "$FUSEKI_USER:$FUSEKI_PASSWORD" \
    --data-urlencode "query=SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }" \
    -H "Accept: application/sparql-results+json" \
    --max-time 10 \
    2>/dev/null | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(data['results']['bindings'][0]['count']['value'])" 2>/dev/null)

if [ -n "$TRIPLE_COUNT" ] && [ "$TRIPLE_COUNT" != "None" ]; then
    echo -e "${GREEN}OK: 업로드된 트리플 개수: $TRIPLE_COUNT${NC}"
else
    echo -e "${YELLOW}WARNING: 트리플 개수 확인 실패 (Fuseki 서버 응답 없음 또는 데이터 없음)${NC}"
fi

# TTL 파일에서 노드 및 엣지 수 계산
echo ""
echo "TTL 파일 통계 계산 중..."
STATS_SCRIPT="$SCRIPT_DIR/count_ttl_stats.py"
if [ -f "$STATS_SCRIPT" ]; then
    STATS_OUTPUT=$(python3 "$STATS_SCRIPT" --ttl "$OUTPUT_TTL" --quiet 2>&1)
    if [ $? -eq 0 ] && [ -n "$STATS_OUTPUT" ]; then
        NODE_COUNT=$(echo "$STATS_OUTPUT" | grep "노드 수:" | awk '{print $3}' | tr -d ',')
        EDGE_COUNT=$(echo "$STATS_OUTPUT" | grep "엣지 수:" | awk '{print $3}' | tr -d ',')
        if [ -n "$NODE_COUNT" ] && [ -n "$EDGE_COUNT" ]; then
            echo -e "${GREEN}OK: 적재된 노드 수: ${NODE_COUNT}${NC}"
            echo -e "${GREEN}OK: 적재된 엣지 수: ${EDGE_COUNT}${NC}"
        else
            echo -e "${YELLOW}WARNING: 노드/엣지 수 파싱 실패${NC}"
        fi
    else
        echo -e "${YELLOW}WARNING: TTL 통계 계산 실패${NC}"
    fi
else
    echo -e "${YELLOW}WARNING: 통계 스크립트를 찾을 수 없습니다: $STATS_SCRIPT${NC}"
fi

echo ""