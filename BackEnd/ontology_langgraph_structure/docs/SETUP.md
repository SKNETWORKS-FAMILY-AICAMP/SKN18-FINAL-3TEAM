# 한국 역사 온톨로지 LangGraph 시스템 설치 가이드

이 문서는 `main.py`를 실행하기 위한 전체 환경 설정 가이드입니다.

---

## 📝 새로운 TTL 파일 생성 시 절차

`backend/ontology_langgraph_structure/ontology/instances/` 폴더에 새로운 TTL 파일을 생성했을 경우:

### 🚀 방법 1: 자동화 스크립트 사용 (권장)

가장 간편한 방법으로, 정규화부터 업로드까지 한 번에 처리합니다.

```bash
# 1. API 서버 시작 (가상환경 활성화 상태에서)
cd backend/ontology_langgraph_structure/ontology/scripts
pkill -f realtime_inference_api.py  # 기존 서버 종료
python realtime_inference_api.py &

# 2. 잠시 대기
sleep 5

# 3. 자동화 스크립트 실행
./update_data.sh
```

**스크립트가 자동으로 처리하는 작업:**
1. ✅ TTL 파일 정규화 (`normalize_ttl.py`)
2. ✅ 기존 Fuseki 데이터 삭제
3. ✅ Jena Reasoner 추론 실행
4. ✅ 추론 결과 Fuseki 업로드
5. ✅ 트리플 수 확인

**스크립트 설정:**
- Java 메모리: 8GB (`-Xmx8g`)
- 타임아웃: 240초 (4분)
- 가상환경 자동 감지

---

### 🔧 방법 2: 수동 단계별 실행

세부적인 제어가 필요한 경우 사용합니다.

#### 1. TTL 파일 정규화

한글 URI와 특수문자를 포함한 TTL 파일은 Jena Reasoner가 파싱할 수 없으므로 정규화가 필요합니다.

```bash
# ontology/scripts 디렉토리로 이동
cd backend/ontology_langgraph_structure/ontology/scripts

# TTL 정규화 실행
python normalize_ttl.py \
  --input ../instances/korean_history_instances.ttl \
  --output ../instances/korean_history_normalized.ttl
```

**정규화 작업:**
- 한글 URI → 영숫자 해시 ID로 변환 (예: `Event_갑술환국` → `Event_abc123`)
- 한글 프로퍼티 → 영문 변환
- 특수문자 제거 (괄호, 하이픈 등)
- 원본 한글 이름은 `rdfs:label`로 보존
- TTL 문법 검증

#### 2. Reasoner JAR 재빌드 (선택사항)

OWL 스키마나 규칙이 변경된 경우에만 필요:

```bash
cd backend/ontology_langgraph_structure/ontology/reasoner
mvn clean package -DskipTests
```

#### 3. Reasoner API 서버 재시작

정규화된 TTL 파일을 사용하도록 API 서버 재시작:

```bash
# 기존 API 서버 종료 (프로세스 ID 확인 후)
pkill -f realtime_inference_api.py

# API 서버 재시작
cd ../scripts
python realtime_inference_api.py &
```

#### 4. 데이터 업로드 확인

**데이터 업로드 흐름:**

1. Reasoner API 서버가 시작되면 자동으로 `temp_inference` 데이터셋을 생성
2. `/infer` 엔드포인트를 호출하면:
   - `korean_history_normalized.ttl` 파일을 자동으로 로드
   - Jena Reasoner로 추론 실행
   - 추론 결과를 Fuseki의 `temp_inference` 데이터셋에 자동 업로드

API를 통해 추론 및 업로드:

```bash
# Health check
curl http://localhost:8001/health

# 기본 추론 실행 (정규화된 TTL 자동 로드)
curl -X POST http://localhost:8001/infer \
  -H "Content-Type: application/json" \
  -d '{}'
```

**참고:**

- `instances` 파라미터를 비워두면 자동으로 `korean_history_normalized.ttl` 사용
- What-if 시나리오는 `/what-if` 엔드포인트 사용
- 추론 결과는 자동으로 Fuseki에 업로드됨

#### 5. Fuseki에서 데이터 확인

브라우저에서 [http://localhost:3030](http://localhost:3030) 접속 후:

- Dataset: `temp_inference` 선택
- Query 탭에서 SPARQL 실행:

```sparql
SELECT ?s ?p ?o WHERE {
  ?s ?p ?o .
} LIMIT 100
```

**데이터 확인 항목:**

- 원본 데이터 (`hist:source "manual"`)
- 추론 데이터 (`hist:source "inferred"`)
- 추론 시각 (`hist:inferredAt`)

```sparql
# 추론된 데이터만 조회
SELECT ?s ?p ?o WHERE {
  ?s hist:source "inferred" .
  ?s ?p ?o .
} LIMIT 50
```

---

## 🔄 정규화 없이 더미 데이터 작성 시 (구버전, 비권장)

**경고:** 이 방법은 더 이상 권장되지 않습니다. 위의 정규화 절차를 따르세요.

<details>
<summary>구버전 절차 보기 (클릭)</summary>

더미 데이터를 직접 Fuseki에 업로드:

```bash
# Mac/Linux
curl -u admin:fuseki1234 -X POST \
  -H "Content-Type: text/turtle" \
  --data-binary "@backend/ontology_langgraph_structure/ontology/instances/korean_history_instances.ttl" \
  http://localhost:3030/korean_history/data
```

**문제점:**

- 한글 URI 파싱 실패
- 추론 엔진 오류
- 비정규화된 데이터로 인한 일관성 문제

</details>

---

## 📋 사전 요구사항

### 공통 (Windows/Mac)

- Python 3.9 이상
- Docker Desktop
- Git

### Windows 전용

- Scoop (패키지 매니저)
- OpenJDK 17

### Mac 전용

- Homebrew (패키지 매니저)
- OpenJDK 17

---

## 🛠️ 1단계: 기본 환경 설정

### Windows

#### 1.1 Scoop 설치 (PowerShell 관리자 권한)

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
```

#### 1.2 Java 17 설치

```powershell
scoop bucket add java
scoop install openjdk17
java -version  # 확인
```

#### 1.3 Maven 설치

```powershell
scoop install maven
mvn -version  # 확인
```

#### 1.4 Docker Desktop 설치

- [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) 다운로드 및 설치
- WSL2 백엔드 활성화 필요

---

### Mac

#### 1.1 Homebrew 설치 (터미널)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 1.2 Java 17 설치

```bash
brew install openjdk@17
sudo ln -sfn $(brew --prefix)/opt/openjdk@17/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk
java -version  # 확인
```

#### 1.3 Maven 설치

```bash
brew install maven
mvn -version  # 확인
```

#### 1.4 Docker Desktop 설치

```bash
brew install --cask docker
```

또는 [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) 다운로드

---

## 🐍 2단계: Python 환경 설정

### 2.1 저장소 클론 및 이동

```bash
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN18-FINAL-3TEAM.git
cd SKN18-FINAL-3TEAM
```

### 2.2 가상환경 생성 및 활성화

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Mac/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2.3 Python 패키지 설치

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🔑 3단계: 환경변수 설정 (.env 파일)

프로젝트 루트에 `.env` 파일 생성:

```bash
# OpenAI API 키
OPENAI_API_KEY=sk-proj-...your-api-key...

# LangSmith (선택사항 - 추적 비활성화 시 주석 처리)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...your-langsmith-key...
LANGCHAIN_PROJECT=Korean-History-LangGraph

# Fuseki 인증 정보
FUSEKI_USER=admin
FUSEKI_PASSWORD=fuseki1234

# OpenAI 모델 (기본값: gpt-4o-mini)
OPENAI_MODEL=gpt-4o-mini
```

**⚠️ 필수 설정:**

- `OPENAI_API_KEY`: [OpenAI Platform](https://platform.openai.com/api-keys)에서 발급
- `LANGCHAIN_API_KEY`: [LangSmith](https://smith.langchain.com/)에서 발급 (추적 사용 시)

---

## 🐳 4단계: Apache Jena Fuseki 실행

### 4.1 Docker Compose로 Fuseki 시작

**프로젝트 루트에서 실행:**

```bash
docker-compose up -d
```

### 4.2 Fuseki 접속 확인

브라우저에서 [http://localhost:3030](http://localhost:3030) 접속

- 로그인: `admin` / `fuseki1234`
- 데이터셋 `korean_history` 생성 확인

### 4.3 데이터셋 생성

**Windows (PowerShell):**

```powershell
$auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:fuseki1234"))
$headers = @{"Authorization" = "Basic $auth"}

Invoke-WebRequest -Uri "http://localhost:3030/$/datasets" -Method POST -Body "dbName=korean_history&dbType=tdb2" -Headers $headers
```

**Mac/Linux (Bash):**

```bash
curl -u admin:fuseki1234 -X POST \
  -d "dbName=korean_history&dbType=tdb2" \
  http://localhost:3030/$/datasets
```

**참고:**

- 데이터 업로드는 Reasoner API 서버가 자동으로 처리합니다 (6단계 참조)
- 수동으로 업로드할 필요가 없습니다

---

## ⚙️ 5단계: Jena Reasoner JAR 빌드

### 5.1 Reasoner 디렉토리 이동

```bash
cd backend/ontology_langgraph_structure/ontology/reasoner
```

### 5.2 Maven 빌드 실행

```bash
mvn clean package -DskipTests
```

### 5.3 빌드 확인

```bash
ls target/swrl-reasoner-0.1.0.jar  # Mac/Linux
dir target\swrl-reasoner-0.1.0.jar  # Windows
```

성공 시 약 22MB 크기의 JAR 파일 생성

---

## 🚀 6단계: Jena Reasoner API 서버 실행 및 데이터 업로드

### 6.1 스크립트 디렉토리 이동

```bash
cd ../scripts  # ontology/scripts로 이동
```

### 6.2 API 서버 시작

**Windows (PowerShell - 백그라운드):**

```powershell
Start-Process python -ArgumentList "realtime_inference_api.py" -WindowStyle Hidden
```

**Mac/Linux (백그라운드):**

```bash
python realtime_inference_api.py &
```

### 6.3 API 서버 확인

```bash
curl http://localhost:8001/health
```

응답 예시:

```json
{ "status": "healthy", "reasoner": "loaded" }
```

### 6.4 초기 데이터 업로드

API 서버가 실행되면 `/infer` 엔드포인트를 통해 데이터를 업로드하고 추론을 실행합니다:

```bash
# 예시: What-if 시나리오 추론 및 업로드
curl -X POST http://localhost:8001/infer \
  -H "Content-Type: application/json" \
  -d '{
    "what_if_triples": "hist:Event_example rdf:type hist:Event .\nhist:Event_example rdfs:label \"예시 이벤트\" ."
  }'
```

**참고:**

- Reasoner API가 실행되면서 자동으로 `temp_inference` 데이터셋을 생성합니다
- What-if 트리플과 함께 추론 결과가 Fuseki에 업로드됩니다
- 실제 운영 시에는 LangGraph 노드가 자동으로 이 API를 호출합니다

---

## ✅ 7단계: main.py 실행

### 7.1 LangGraph 디렉토리 이동

```bash
cd ../../  # backend/ontology_langgraph_structure로 이동
```

### 7.2 main.py 실행

```bash
python main.py
```

### 7.3 사용 예시

```
╔═══════════════════════════════════════════════════════════╗
║     한국 역사 온톨로지 LangGraph 시스템 (창작 모드)     ║
╚═══════════════════════════════════════════════════════════╝

❓ 질문을 입력하세요 (종료: quit/exit/q): 이순신이 명량대첩에서 승리한 이유는?

🔍 분석 중...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[결과 출력]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🧪 8단계: 시스템 테스트 (선택사항)

전체 시스템 검증:

```bash
python test_setup.py
```

테스트 항목:

- ✅ Fuseki 연결
- ✅ Fuseki 데이터 업로드
- ✅ Jena Reasoner API 연결
- ✅ 노드 연결 및 실행
- ✅ What-if 트리플 생성
- ✅ SPARQL 쿼리 생성

---

## 🔧 문제 해결 (Troubleshooting)

### 문제 1: Fuseki 401 Unauthorized

**증상:** 데이터셋 생성/조회 시 인증 오류

**해결:**

```bash
# .env 파일 확인
FUSEKI_USER=admin
FUSEKI_PASSWORD=fuseki1234
```

### 문제 2: Reasoner API 연결 실패

**증상:** `http://localhost:8001` 연결 거부

**해결:**

```bash
# API 서버 재시작
cd backend/ontology_langgraph_structure/ontology/scripts
python realtime_inference_api.py

# 다른 터미널에서 main.py 실행
```

### 문제 3: Java 버전 오류

**증상:** `UnsupportedClassVersionError`

**해결:**

```bash
# Java 버전 확인 (17 이상 필요)
java -version

# Mac에서 Java 전환
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

### 문제 4: Docker 포트 충돌

**증상:** `Port 3030 is already in use`

**해결:**

```bash
# 기존 컨테이너 종료
docker-compose down

# 또는 다른 포트 사용 (docker-compose.yml 수정)
ports:
  - "3031:3030"  # 3031로 변경
```

### 문제 5: LangSmith 추적 안됨

**증상:** LangSmith에 트레이스가 보이지 않음

**해결:**

```bash
# .env 파일 확인
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=Korean-History-LangGraph

# Python 재시작
```

### 문제 6: Maven 빌드 실패

**증상:** `BUILD FAILURE`

**해결:**

```bash
# Maven 캐시 정리
mvn clean

# 의존성 다운로드 재시도
mvn dependency:resolve

# 다시 빌드
mvn clean package -DskipTests
```

---

## 📂 프로젝트 구조

```
SKN18-FINAL-3TEAM/
├── .env                          # 환경변수 파일
├── docker-compose.yml            # Fuseki 컨테이너 설정
├── requirements.txt              # Python 패키지
└── backend/
    └── ontology_langgraph_structure/
        ├── main.py              # 🎯 메인 실행 파일
        ├── graph.py             # LangGraph 워크플로우
        ├── state.py             # GraphState 정의
        ├── nodes/               # 노드 구현
        │   ├── classify_node.py
        │   ├── entity_extractor_node.py
        │   ├── multi_query_generator_node.py
        │   ├── evidence_aggregator_node.py
        │   ├── generate_node.py
        │   └── kg/
        │       ├── hypothetical_triple_node.py
        │       ├── parallel_inference_executor_node.py
        │       └── multi_path_extractor_node.py
        └── ontology/
            ├── korean_history.owl           # OWL 온톨로지 스키마
            ├── reasoner/
            │   ├── pom.xml                  # Maven 설정
            │   └── target/
            │       └── swrl-reasoner-0.1.0.jar  # 빌드된 JAR
            ├── scripts/
            │   ├── normalize_ttl.py         # TTL 정규화 스크립트
            │   └── realtime_inference_api.py  # Reasoner API 서버
            ├── instances/
            │   ├── korean_history_instances.ttl     # 원본 TTL (한글 포함)
            │   └── korean_history_normalized.ttl    # 정규화된 TTL
            └── rules/
                └── all_rules.rules          # Jena 추론 규칙
```

---

## 📋 새 TTL 파일 생성 시 전체 절차 요약

새로운 온톨로지 인스턴스 데이터를 추가할 때:

### 🚀 빠른 시작 (자동화 스크립트)

```bash
# 1. 원본 TTL 작성
vim backend/ontology_langgraph_structure/ontology/instances/korean_history_instances.ttl

# 2. 스크립트 디렉토리 이동
cd backend/ontology_langgraph_structure/ontology/scripts

# 3. API 서버 시작
pkill -f realtime_inference_api.py
python realtime_inference_api.py &
sleep 5

# 4. 자동화 스크립트 실행 (정규화 + 업로드)
./update_data.sh

# 5. main.py 실행
cd ../../
python main.py
```

---

### 🔧 수동 절차 (상세 제어 필요 시)

#### 1️⃣ TTL 파일 작성 및 정규화

```bash
# 1. 원본 TTL 작성 (한글 URI 포함 가능)
vim backend/ontology_langgraph_structure/ontology/instances/korean_history_instances.ttl

# 2. TTL 정규화 실행
cd backend/ontology_langgraph_structure/ontology/scripts
python normalize_ttl.py \
  --input ../instances/korean_history_instances.ttl \
  --output ../instances/korean_history_normalized.ttl
```

#### 2️⃣ Reasoner API 서버 재시작

```bash
# 기존 서버 종료
pkill -f realtime_inference_api.py

# 새 서버 시작
python realtime_inference_api.py &

# Health check
curl http://localhost:8001/health
```

#### 3️⃣ 데이터 업로드 및 추론

```bash
# 기존 데이터 삭제
curl -X POST "http://localhost:3030/temp_inference/update" \
  --data-urlencode "update=CLEAR DEFAULT"

# 추론 실행 (정규화된 TTL 자동 로드 및 Fuseki 업로드)
curl -X POST http://localhost:8001/infer \
  -H "Content-Type: application/json" \
  -d '{}' \
  --max-time 200
```

#### 4️⃣ Fuseki에서 확인

- 브라우저: [http://localhost:3030](http://localhost:3030)
- Dataset: `temp_inference`
- SPARQL:

```sparql
SELECT ?s ?p ?o WHERE {
  ?s ?p ?o .
} LIMIT 100
```

#### 5️⃣ main.py 실행

```bash
cd ../../  # backend/ontology_langgraph_structure
python main.py
```

---

### 💡 핵심 포인트

- ✅ 정규화는 **필수** (한글 URI → 영숫자 해시)
- ✅ Reasoner API가 자동으로 데이터 업로드
- ✅ Maven 빌드는 OWL/규칙 변경 시에만 필요
- ✅ Fuseki 데이터셋은 API가 자동 생성
- ✅ Java 메모리: 8GB, 타임아웃: 240초 자동 설정
- ✅ **자동화 스크립트(`update_data.sh`) 사용 권장**

---

## 📞 지원

문제가 지속될 경우:

1. GitHub Issues 등록
2. `.env` 파일 설정 재확인
3. Docker/Java/Maven 버전 확인
4. `test_setup.py` 실행하여 각 단계별 상태 점검

---

## 📝 체크리스트

실행 전 최종 확인:

- [ ] Java 17 이상 설치 확인 (`java -version`)
- [ ] Maven 설치 확인 (`mvn -version`)
- [ ] Docker Desktop 실행 중
- [ ] `.env` 파일 생성 및 API 키 설정
- [ ] `docker-compose up -d` 실행
- [ ] Fuseki 웹 UI 접속 확인 (http://localhost:3030)
- [ ] Maven 빌드 완료 (`swrl-reasoner-0.1.0.jar` 존재)
- [ ] Reasoner API 서버 실행 중 (http://localhost:8001/health)
- [ ] Python 가상환경 활성화
- [ ] Python 패키지 설치 완료

모든 항목 체크 후 `python main.py` 실행!
