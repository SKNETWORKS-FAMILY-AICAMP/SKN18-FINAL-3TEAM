# Jena Reasoner

Apache Jena 기반 추론 엔진입니다. OWL 온톨로지 + TTL 인스턴스 + Jena Rules를 사용하여 추론을 실행하고, 결과를 Fuseki에 자동 업로드합니다.

## 📋 기능

1. **OWL + TTL 로드**: 온톨로지 스키마와 인스턴스 데이터 로드
2. **Jena Rules 적용**: 5개 카테고리 69개 규칙 적용
3. **추론 실행**: 암묵적 지식 도출 (간접 인과관계, 인물 역할, 동기 등)
4. **메타데이터 추가**: `source: "manual"` 또는 `"inferred"` 자동 태깅
5. **Fuseki 업로드**: 추론 결과를 Fuseki에 자동 업로드

## 🚀 빠른 시작

### 1. 전제조건

```bash
# Java 17+ 설치 확인
java -version

# Maven 설치 확인
mvn -version

# Fuseki 서버 시작
cd /path/to/project/root
docker-compose up -d fuseki
```

### 2. Reasoner 실행

```bash
cd backend/ontology_langgraph_structure/ontology/reasoner

# 자동 실행 스크립트
./run_reasoner.sh
```

**스크립트가 자동으로 수행하는 작업**:

1. Maven 빌드 (`mvn clean package`)
2. 규칙 파일 병합 (`all_rules.rules` 생성)
3. 파일 존재 확인 (OWL, TTL, Rules)
4. Fuseki 서버 연결 확인
5. Reasoner 실행
6. 결과 출력

### 3. 수동 실행 (고급)

```bash
# 1. Maven 빌드
mvn clean package

# 2. 규칙 파일 병합
cat ../rules/causal_inference.rules \
    ../rules/person_inference.rules \
    ../rules/temporal_inference.rules \
    ../rules/pattern_inference.rules \
    ../rules/motive_inference.rules \
    > ../rules/all_rules.rules

# 3. Reasoner 실행
java -jar target/swrl-reasoner-0.1.0.jar \
    ../korean_history.owl \
    ../instances/korean_history_instances.ttl \
    ../rules/all_rules.rules \
    http://localhost:3030/history
```

## 📊 추론 결과 확인

### SPARQL 쿼리로 확인

```bash
# Fuseki UI 접속
open http://localhost:3030

# 또는 Python으로 조회
python3 << EOF
from SPARQLWrapper import SPARQLWrapper, JSON

sparql = SPARQLWrapper("http://localhost:3030/history/sparql")

# 추론된 데이터만 조회
query = """
PREFIX hist: <http://www.example.org/korean-history#>

SELECT ?subject ?predicate ?object
WHERE {
    ?subject ?predicate ?object .
    ?subject hist:source "inferred" .
}
LIMIT 100
"""

sparql.setQuery(query)
sparql.setReturnFormat(JSON)
results = sparql.query().convert()

for result in results["results"]["bindings"]:
    print(result)
EOF
```

### 추론 결과 예시

```sparql
# 1. 명장 추론
hist:YiSunSin hist:hasRole "great_general" .
hist:YiSunSin hist:source "inferred" .

# 2. 간접 인과관계 추론
hist:Battle1 hist:indirectlyCausedBy hist:Battle3 .

# 3. 동시대 인물 추론
hist:YiSunSin hist:contemporaryWith hist:WonGyun .

# 4. 전략 패턴 추론
hist:YiSunSin hist:hasStrategyPattern "naval_warfare_specialist" .

# 5. 동기 추론
hist:YiSunSin hist:hasMotive "national_defense" .
```

## 🔧 설정

### 환경변수

```bash
# .env 파일 또는 환경변수 설정
export FUSEKI_ENDPOINT="http://localhost:3030/history/sparql"
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4o"
```

### 파일 경로

```
backend/ontology_langgraph_structure/ontology/
├── korean_history.owl              # OWL 온톨로지 스키마
├── instances/
│   └── korean_history_instances.ttl  # TTL 인스턴스 데이터
├── rules/
│   ├── causal_inference.rules      # 인과관계 추론 규칙
│   ├── person_inference.rules      # 인물 추론 규칙
│   ├── temporal_inference.rules    # 시간 추론 규칙
│   ├── pattern_inference.rules     # 패턴 추론 규칙
│   ├── motive_inference.rules      # 동기 추론 규칙
│   └── all_rules.rules             # 병합된 규칙 (자동 생성)
└── reasoner/
    ├── run_reasoner.sh             # 실행 스크립트
    ├── pom.xml                     # Maven 설정
    └── src/main/java/com/skn18/reasoner/
        └── JenaReasoner.java       # Reasoner 메인 클래스
```

## 📝 워크플로우

```
1. CSV 데이터 준비
   ↓
2. LLM으로 TTL 생성 (llm_ttl_generator.py)
   ↓
3. Reasoner 실행 (run_reasoner.sh)
   - OWL + TTL 로드
   - Jena Rules 적용
   - 추론 실행
   - Fuseki 업로드
   ↓
4. LangGraph에서 SPARQL 쿼리 (sparql_query_node.py)
   ↓
5. 결과 활용
```

## 🐛 트러블슈팅

### 1. JAR 파일이 생성되지 않음

```bash
# Maven 의존성 강제 업데이트
mvn clean install -U

# Java 버전 확인
java -version  # 17 이상 필요
```

### 2. Fuseki 연결 실패

```bash
# Fuseki 서버 상태 확인
curl http://localhost:3030

# Fuseki 재시작
docker-compose restart fuseki

# Dataset 생성 확인
# http://localhost:3030 접속 → "Manage datasets" → "history" 확인
```

### 3. TTL 파일이 없음

```bash
# TTL 생성 스크립트 실행
cd backend/ontology_langgraph_structure/ontology/scripts
python llm_ttl_generator.py
```

### 4. 추론 결과가 없음

```bash
# 규칙 파일 확인
ls -la ../rules/*.rules

# 규칙 병합 확인
cat ../rules/all_rules.rules

# 인스턴스 데이터 확인
head -n 50 ../instances/korean_history_instances.ttl
```

## 📚 참고 자료

- [Apache Jena](https://jena.apache.org/)
- [Jena Rules](https://jena.apache.org/documentation/inference/#rules)
- [SPARQL 1.1](https://www.w3.org/TR/sparql11-query/)
- [Turtle (TTL)](https://www.w3.org/TR/turtle/)

## 🔗 관련 파일

- `../rules/README.md` - Jena Rules 상세 설명
- `../scripts/llm_ttl_generator.py` - TTL 생성 스크립트
- `../../nodes/kg/sparql_query_node.py` - SPARQL 쿼리 노드
- `../../nodes/kg/ttl_generator_node.py` - TTL 생성 노드 (LangGraph용)
