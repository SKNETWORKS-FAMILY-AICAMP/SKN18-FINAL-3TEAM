## SWRL Reasoner Bridge

이 서브모듈은 OWL + TTL + SWRL 규칙을 로컬에서 **실제 추론을 실행**하고, 추론 결과를 메타데이터(`source: "inferred"`, `inferredBy: "rule_id"`)와 함께 Apache Jena Fuseki에 반영하기 위한 Java 애플리케이션입니다.

### 사전 설치 (필수)

#### Windows (Scoop)

```powershell
# Java 17
scoop bucket add java
scoop install openjdk17

# Maven
scoop install maven

# Docker Desktop (Fuseki 실행용)
# https://www.docker.com/products/docker-desktop 에서 다운로드
```

#### macOS (Homebrew)

```bash
# Java 17
brew install openjdk@17

# Maven
brew install maven

# Docker Desktop
brew install --cask docker
```

### 전체 워크플로우

#### 1단계: Fuseki 서버 시작 및 Dataset 생성

```bash
# 프로젝트 루트에서
docker compose up -d fuseki

# 브라우저에서 http://localhost:3030 접속
# 1. admin 로그인 (비밀번호는 .env의 FUSEKI_ADMIN_PASSWORD)
# 2. "Manage datasets" → "Add new dataset"
# 3. 이름 입력 (예: "history") → "Persistent dataset" 선택 → 생성
# 4. Dataset 상세 페이지에서 "Upload data" 버튼 클릭
# 5. knowledge_engineering/ontology/schemas/*.owl 파일 업로드
# 6. knowledge_engineering/ontology/instances/*.ttl 파일 업로드
```

#### 2단계: SWRL 추론 실행 및 Fuseki 업로드

```bash
# 프로젝트 루트에서
cd knowledge_engineering/ontology/reasoner

# 빌드 (최초 1회 또는 의존성 변경 시)
mvn -U clean package

# 추론 실행 (Windows)
java -jar target/swrl-reasoner-0.1.0.jar ^
    ..\schemas\korean_folktale.owl ^
    ..\instances\heungbu_nolbu.ttl ^
    ..\rules\historical_inference_rules.swrl ^
    http://localhost:3030/history

# 추론 실행 (macOS/Linux)
java -jar target/swrl-reasoner-0.1.0.jar \
    ../schemas/korean_folktale.owl \
    ../instances/heungbu_nolbu.ttl \
    ../rules/historical_inference_rules.swrl \
    http://localhost:3030/history
```

**인자 설명:**

- 첫 번째: 기준 OWL 스키마 파일
- 두 번째: 인스턴스 TTL 파일
- 세 번째: SWRL 규칙 파일
- 네 번째: Fuseki dataset base URL (`/sparql` 제외, 예: `http://localhost:3030/history`)

**실행 결과:**

- SWRL 규칙이 실행되어 추론된 triple이 생성됨
- 추론 결과에 메타데이터 자동 추가:
  - `source: "inferred"` (추론 결과임을 표시)
  - `inferredBy: "swrl_rule_001"` (사용된 규칙 ID)
  - `inferredAt: "2024-01-15T10:00:00Z"` (추론 시각)
- 원본 데이터는 `source: "manual"`로 마킹
- 모든 결과가 Fuseki dataset에 자동 업로드됨

#### 3단계: LangGraph 연결

```bash
# 환경 변수 설정
# Windows PowerShell:
$env:FUSEKI_ENDPOINT = "http://localhost:3030/history/sparql"

# macOS/Linux:
export FUSEKI_ENDPOINT="http://localhost:3030/history/sparql"

# Python 가상환경 활성화 및 실행
# Windows:
.\.venv\Scripts\Activate.ps1

# macOS/Linux:
source .venv/bin/activate

# LangGraph 실행
python main.py
```

### 중요 사항

> **참고 1**: SWRLAPI는 중앙 Maven 저장소에 없으므로 `pom.xml`에서 [JitPack](https://jitpack.io)을 사용하도록 설정되어 있습니다. 첫 빌드 시 JitPack에서 소스를 컴파일하므로 시간이 걸릴 수 있습니다.

> **참고 2**: 이 Reasoner는 **실제 SWRL 추론을 실행**합니다. `engine.infer()`로 추론된 결과를 가져와 ontology에 추가하고, 메타데이터를 자동으로 붙입니다. 단순히 파일을 복사하는 것이 아닙니다.

> **참고 3**: 추론 결과는 `source: "inferred"`로 마킹되므로, SPARQL 쿼리에서 원본 데이터와 추론 결과를 구분할 수 있습니다:

```sparql
# 추론된 관계만 조회
SELECT ?effect ?cause ?rule
WHERE {
    ?effect <http://example.org/korean-history#indirectlyCausedBy> ?cause ;
            <http://example.org/korean-history#source> "inferred" ;
            <http://example.org/korean-history#inferredBy> ?rule .
}
```
