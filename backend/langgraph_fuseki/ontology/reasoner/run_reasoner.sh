#!/bin/bash

# ============================================================
# Jena Reasoner 실행 스크립트
# ============================================================
# 
# 사용법:
#   ./run_reasoner.sh
#
# 전제조건:
#   1. Maven 설치 (mvn 명령어 사용 가능)
#   2. Java 17+ 설치
#   3. Fuseki 서버 실행 중 (http://localhost:3030)
#

set -e  # 오류 발생 시 중단

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Jena Reasoner 실행 ===${NC}"

# 1. Maven 빌드
echo -e "${GREEN}1. Maven 빌드 중...${NC}"
mvn clean package -q

if [ ! -f "target/swrl-reasoner-0.1.0.jar" ]; then
    echo -e "${RED}❌ JAR 파일 생성 실패${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 빌드 완료${NC}"

# 2. 파일 경로 설정
OWL_FILE="../korean_history.owl"
TTL_FILE="../instances/korean_history_instances.ttl"
RULES_FILE="../rules/all_rules.rules"
FUSEKI_URL="http://localhost:3030/history"

# 3. 규칙 파일 병합 (all_rules.rules 생성)
echo -e "${GREEN}2. 규칙 파일 병합 중...${NC}"
cat ../rules/causal_inference.rules \
    ../rules/person_inference.rules \
    ../rules/temporal_inference.rules \
    ../rules/pattern_inference.rules \
    ../rules/motive_inference.rules \
    > ../rules/all_rules.rules

echo -e "${GREEN}✅ 규칙 병합 완료 (all_rules.rules)${NC}"

# 4. 파일 존재 확인
if [ ! -f "$OWL_FILE" ]; then
    echo -e "${RED}❌ OWL 파일을 찾을 수 없습니다: $OWL_FILE${NC}"
    exit 1
fi

if [ ! -f "$TTL_FILE" ]; then
    echo -e "${RED}❌ TTL 파일을 찾을 수 없습니다: $TTL_FILE${NC}"
    echo -e "${BLUE}💡 먼저 llm_ttl_generator.py를 실행하여 TTL 파일을 생성하세요.${NC}"
    exit 1
fi

if [ ! -f "$RULES_FILE" ]; then
    echo -e "${RED}❌ 규칙 파일을 찾을 수 없습니다: $RULES_FILE${NC}"
    exit 1
fi

# 5. Fuseki 서버 확인
echo -e "${GREEN}3. Fuseki 서버 확인 중...${NC}"
if ! curl -s -o /dev/null -w "%{http_code}" "$FUSEKI_URL" | grep -q "200\|404"; then
    echo -e "${RED}❌ Fuseki 서버에 연결할 수 없습니다: $FUSEKI_URL${NC}"
    echo -e "${BLUE}💡 docker-compose up -d fuseki 로 Fuseki를 시작하세요.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Fuseki 서버 연결 확인${NC}"

# 6. Reasoner 실행
echo -e "${GREEN}4. Reasoner 실행 중...${NC}"
echo ""

java -jar target/swrl-reasoner-0.1.0.jar \
    "$OWL_FILE" \
    "$TTL_FILE" \
    "$RULES_FILE" \
    "$FUSEKI_URL"

echo ""
echo -e "${GREEN}=== ✅ 완료 ===${NC}"
echo -e "${BLUE}SPARQL 엔드포인트: ${FUSEKI_URL}/sparql${NC}"
echo -e "${BLUE}Fuseki UI: http://localhost:3030${NC}"

