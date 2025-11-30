"""
실시간 SWRL 추론 API

What-if 시나리오 및 동적 추론을 위한 API 서버
"""

import subprocess
import tempfile
import time
import shutil
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from SPARQLWrapper import SPARQLWrapper, JSON
import traceback

# ==================== 설정 ====================

# 현재 스크립트 위치: backend/ontology_langgraph_structure/ontology/scripts/
# ontology 디렉토리로 이동
ONTOLOGY_DIR = Path(__file__).parent.parent
REASONER_JAR = ONTOLOGY_DIR / "reasoner/target/swrl-reasoner-0.1.0.jar"
TEMP_FUSEKI_URL = "http://localhost:3030/temp_inference"  # 임시 데이터셋

# Java 경로 설정 (Homebrew 설치 시)
# Homebrew로 설치된 Java 우선 사용
brew_java_paths = [
    "/opt/homebrew/opt/openjdk@17/bin/java",
    "/opt/homebrew/opt/openjdk@11/bin/java",
    "/usr/local/opt/openjdk@17/bin/java",
    "/usr/local/opt/openjdk@11/bin/java",
]

JAVA_CMD = None
for java_path in brew_java_paths:
    if os.path.exists(java_path) and os.access(java_path, os.X_OK):
        JAVA_CMD = java_path
        break

# Homebrew Java가 없으면 시스템 Java 사용
if not JAVA_CMD:
    system_java = shutil.which("java")
    if system_java and os.access(system_java, os.X_OK):
        JAVA_CMD = system_java

if not JAVA_CMD:
    raise RuntimeError("Java를 찾을 수 없습니다. Homebrew로 설치: brew install openjdk@17")

print(f"☕ Java 경로: {JAVA_CMD}")

app = FastAPI(title="SWRL Inference API")


# ==================== Fuseki 데이터셋 자동 생성 ====================

def ensure_fuseki_dataset():
    """
    Fuseki 서버에 temp_inference 데이터셋이 없으면 자동 생성
    """
    import requests
    from requests.auth import HTTPBasicAuth
    
    fuseki_base = "http://localhost:3030"
    dataset_name = "temp_inference"
    
    # Fuseki 인증 정보 (docker-compose에서 설정된 값)
    auth = HTTPBasicAuth("admin", "fuseki1234")
    
    try:
        # 1. 데이터셋 존재 여부 확인
        check_url = f"{fuseki_base}/{dataset_name}"
        response = requests.head(check_url, timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Fuseki 데이터셋 '{dataset_name}' 이미 존재")
            return True
        
        # 2. 데이터셋이 없으면 생성 (admin 인증 필요)
        print(f"📦 Fuseki 데이터셋 '{dataset_name}' 생성 중...")
        create_url = f"{fuseki_base}/$/datasets"
        
        create_response = requests.post(
            create_url,
            data={"dbName": dataset_name, "dbType": "mem"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=auth,  # admin 인증 추가
            timeout=10
        )
        
        if create_response.status_code in [200, 201]:
            print(f"✅ Fuseki 데이터셋 '{dataset_name}' 생성 완료")
            return True
        else:
            print(f"⚠️ Fuseki 데이터셋 생성 응답: {create_response.status_code}")
            print(f"   응답 내용: {create_response.text[:200]}")
            
            # 이미 존재하는 경우 (409 Conflict)
            if create_response.status_code == 409:
                print(f"✅ Fuseki 데이터셋 '{dataset_name}' 이미 존재 (409)")
                return True
            
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Fuseki 서버 연결 실패 (http://localhost:3030)")
        print(f"   Fuseki Docker 컨테이너가 실행 중인지 확인하세요.")
        return False
    except Exception as e:
        print(f"❌ Fuseki 데이터셋 확인/생성 실패: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 Fuseki 데이터셋 자동 생성"""
    ensure_fuseki_dataset()

# ==================== 전역 예외 핸들러 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """모든 예외를 잡아서 상세한 에러 메시지 반환"""
    error_detail = {
        "error": str(exc),
        "error_type": type(exc).__name__,
        "traceback": traceback.format_exc()
    }
    print(f"❌ 예외 발생: {error_detail}")
    return JSONResponse(
        status_code=500,
        content=error_detail
    )


# ==================== 모델 ====================

class InferenceRequest(BaseModel):
    """일반 추론 요청"""
    ontology: str = "korean_history.owl"
    instances: list[str] = []  # 빈 리스트면 instances 폴더의 모든 .ttl 파일 사용
    rules: str = "all_rules.rules"  # 병합된 규칙 파일
    query: str = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 50"  # 결과 조회용 SPARQL (선택사항)


class WhatIfRequest(BaseModel):
    """What-if 시나리오 요청"""
    base_ontology: str = "korean_history.owl"
    base_instances: list[str] = []  # 빈 리스트면 instances 폴더의 모든 .ttl 파일 사용
    rules: str = "all_rules.rules"  # 병합된 규칙 파일
    hypothetical_triples: list[str] = []  # 가상 트리플 (Turtle 형식)
    query: str = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 50"  # 결과 조회용 SPARQL


# ==================== API ====================

@app.post("/infer")
def infer(req: InferenceRequest):
    """일반 실시간 추론 실행"""
    
    # 파일 경로 확인
    ontology = ONTOLOGY_DIR / req.ontology  # korean_history.owl은 ontology 디렉토리 바로 아래
    rules = ONTOLOGY_DIR / "rules" / req.rules
    
    if not ontology.exists():
        raise HTTPException(404, f"온톨로지 파일을 찾을 수 없습니다: {ontology}")
    if not rules.exists():
        raise HTTPException(404, f"규칙 파일을 찾을 수 없습니다: {rules}")
    
    # 인스턴스 병합
    with tempfile.TemporaryDirectory() as tmpdir:
        merged = Path(tmpdir) / "merged.ttl"
        _merge_instances(req.instances, merged)
        
        if not merged.exists() or merged.stat().st_size == 0:
            raise HTTPException(400, "인스턴스 파일을 병합할 수 없습니다")
        
        # Reasoner 실행 (임시 Fuseki에 업로드)
        try:
            print(f"🔧 Reasoner 실행 중...")
            print(f"   - JAR: {REASONER_JAR}")
            print(f"   - Ontology: {ontology}")
            print(f"   - Instances: {merged} ({merged.stat().st_size} bytes)")
            print(f"   - Rules: {rules}")
            print(f"   - Fuseki: {TEMP_FUSEKI_URL}")
            
            # Java 경로를 절대 경로로 변환 (심볼릭 링크 해결)
            if os.path.islink(JAVA_CMD):
                java_abs_path = os.path.realpath(JAVA_CMD)
            else:
                java_abs_path = os.path.abspath(JAVA_CMD) if not os.path.isabs(JAVA_CMD) else JAVA_CMD
            
            # 환경변수 설정 (JAVA_HOME 포함)
            env = os.environ.copy()
            java_bin_dir = os.path.dirname(java_abs_path)
            java_home = os.path.dirname(os.path.dirname(java_bin_dir))
            
            env['JAVA_HOME'] = java_home
            if 'PATH' in env:
                env['PATH'] = f"{java_bin_dir}:{env['PATH']}"
            else:
                env['PATH'] = java_bin_dir
            
            print(f"   - Java 실행: {java_abs_path}")
            print(f"   - JAVA_HOME: {java_home}")
            
            result = subprocess.run(
                [java_abs_path, "-jar", str(REASONER_JAR),
                 str(ontology), str(merged), str(rules), TEMP_FUSEKI_URL],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            print(f"   - Return code: {result.returncode}")
            if result.stdout:
                print(f"   - stdout: {result.stdout[:500]}")
            if result.stderr:
                print(f"   - stderr: {result.stderr[:500]}")
            
            if result.returncode != 0:
                error_msg = f"추론 실패 (return code: {result.returncode})"
                if result.stderr:
                    error_msg += f"\n{result.stderr}"
                if result.stdout:
                    error_msg += f"\n{result.stdout}"
                raise HTTPException(500, error_msg)
            
            # 잠시 대기 (Fuseki 업로드 완료 대기)
            time.sleep(1)
            
            # SPARQL 쿼리 실행 (요청에 query가 있는 경우)
            response = {
                "status": "success",
                "message": "추론 완료",
                "fuseki_endpoint": f"{TEMP_FUSEKI_URL}/sparql"
            }
            
            if req.query:
                try:
                    print(f"🔍 SPARQL 쿼리 실행 중...")
                    query_results = _execute_sparql(req.query, f"{TEMP_FUSEKI_URL}/sparql")
                    response["results"] = query_results
                    print(f"   ✅ 쿼리 결과: {len(query_results.get('results', {}).get('bindings', []))}개")
                except Exception as e:
                    error_msg = str(e)
                    print(f"⚠️ SPARQL 쿼리 실행 실패: {error_msg}")
                    response["query_error"] = error_msg
                    # 에러가 있어도 추론은 성공했으므로 계속 진행
            
            return response
        except subprocess.TimeoutExpired:
            raise HTTPException(500, "추론 시간 초과 (30초)")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"예상치 못한 오류: {str(e)}")


@app.post("/what-if")
def what_if(req: WhatIfRequest):
    """What-if 시나리오 실시간 추론"""

    # 파일 경로 확인
    ontology = ONTOLOGY_DIR / req.base_ontology  # korean_history.owl은 ontology/ 바로 아래
    rules = ONTOLOGY_DIR / "rules" / req.rules
    
    if not ontology.exists():
        raise HTTPException(404, f"온톨로지 파일을 찾을 수 없습니다: {ontology}")
    if not rules.exists():
        raise HTTPException(404, f"규칙 파일을 찾을 수 없습니다: {rules}")
    
    # 가상 트리플이 있으면 인스턴스에 추가
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. 기본 인스턴스 병합
        merged = Path(tmpdir) / "merged.ttl"
        _merge_instances(req.base_instances, merged)
        
        # 2. 가상 트리플 추가
        if req.hypothetical_triples:
            _add_hypothetical_triples(merged, req.hypothetical_triples)
        
        # 3. Reasoner 실행 (임시 Fuseki에 업로드)
        try:
            # Java 경로를 절대 경로로 변환 (심볼릭 링크 해결)
            if os.path.islink(JAVA_CMD):
                java_abs_path = os.path.realpath(JAVA_CMD)
            else:
                java_abs_path = os.path.abspath(JAVA_CMD) if not os.path.isabs(JAVA_CMD) else JAVA_CMD
            
            # 환경변수 설정 (JAVA_HOME 포함)
            env = os.environ.copy()
            java_bin_dir = os.path.dirname(java_abs_path)
            java_home = os.path.dirname(os.path.dirname(java_bin_dir))
            
            env['JAVA_HOME'] = java_home
            if 'PATH' in env:
                env['PATH'] = f"{java_bin_dir}:{env['PATH']}"
            else:
                env['PATH'] = java_bin_dir
            
            result = subprocess.run(
                [java_abs_path, "-jar", str(REASONER_JAR),
                 str(ontology), str(merged), str(rules), TEMP_FUSEKI_URL],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            if result.returncode != 0:
                raise HTTPException(500, f"추론 실패: {result.stderr}")
            
            # 4. 잠시 대기 (Fuseki 업로드 완료 대기)
            time.sleep(1)
            
            # 5. SPARQL 쿼리 실행 (임시 Fuseki에서)
            query_results = _execute_sparql(req.query, f"{TEMP_FUSEKI_URL}/sparql")
            
            return {
                "status": "success",
                "message": "What-if 추론 완료",
                "results": query_results
            }
        except subprocess.TimeoutExpired:
            raise HTTPException(500, "추론 시간 초과 (30초)")


@app.get("/health")
def health():
    """헬스체크"""
    jar_exists = REASONER_JAR.exists()
    return {
        "status": "healthy" if jar_exists else "error",
        "reasoner_jar_exists": jar_exists,
        "jar_path": str(REASONER_JAR)
    }


# ==================== 헬퍼 ====================

def _merge_instances(files: list[str], output: Path):
    """TTL 파일 병합"""
    from rdflib import Graph
    
    g = Graph()
    instances_dir = ONTOLOGY_DIR / "instances"
    
    # files가 비어있으면 정규화된 파일만 사용 (생성 중인 파일 제외)
    if not files:
        if instances_dir.exists():
            # 정규화된 파일 우선 사용
            normalized_file = instances_dir / "korean_history_normalized.ttl"
            if normalized_file.exists():
                files = [normalized_file.name]
                print(f"📂 정규화된 파일 사용: {normalized_file.name}")
            else:
                # 정규화된 파일이 없으면 모든 .ttl 파일 사용 (생성 중인 파일 제외)
                all_files = [f.name for f in instances_dir.glob("*.ttl")]
                # 생성 중인 파일 제외
                files = [f for f in all_files if not f.startswith("korean_history_instances.ttl") or f == "korean_history_normalized.ttl"]
                print(f"📂 자동으로 {len(files)}개 인스턴스 파일 발견: {files}")
        else:
            raise ValueError(f"인스턴스 디렉토리가 없습니다: {instances_dir}")
    
    for file in files:
        path = instances_dir / file
        if path.exists():
            g.parse(str(path), format="turtle")
            print(f"   ✅ 로드: {file}")
        else:
            print(f"⚠️ 경고: 인스턴스 파일을 찾을 수 없습니다: {path}")
    
    if len(g) == 0:
        raise ValueError("병합할 인스턴스가 없습니다")
    
    g.serialize(str(output), format="turtle")
    print(f"   ✅ 병합 완료: {len(g)} 트리플")


def _add_hypothetical_triples(ttl_file: Path, triples: list[str]):
    """가상 트리플을 TTL 파일에 추가"""
    from rdflib import Graph
    
    g = Graph()
    g.parse(str(ttl_file), format="turtle")
    
    # 가상 트리플 추가 (Turtle 형식으로 파싱)
    for triple in triples:
        try:
            # 간단한 Turtle 문장 파싱
            # 예: "test:YiSunSin test:died test:EarlyDeath ."
            g.parse(data=triple, format="turtle")
        except Exception as e:
            print(f"⚠️ 경고: 트리플 파싱 실패: {triple} - {e}")
    
    g.serialize(str(ttl_file), format="turtle")


def _execute_sparql(sparql_query: str, endpoint: str) -> dict:
    """Fuseki에서 SPARQL 쿼리 실행"""
    try:
        print(f"   - Endpoint: {endpoint}")
        print(f"   - Query: {sparql_query[:200]}...")
        
        sparql = SPARQLWrapper(endpoint)
        sparql.setReturnFormat(JSON)
        sparql.setQuery(sparql_query)
        
        results = sparql.query().convert()
        return results
    except Exception as e:
        error_msg = f"SPARQL 쿼리 실행 실패: {str(e)}"
        print(f"   ❌ {error_msg}")
        raise Exception(error_msg)


# ==================== 실행 ====================

if __name__ == "__main__":
    import uvicorn
    
    print(f"🚀 SWRL Inference API 시작")
    print(f"📂 JAR: {REASONER_JAR.exists()} ({REASONER_JAR})")
    print(f"📂 Ontology: {ONTOLOGY_DIR}")
    print(f"🌐 서버: http://0.0.0.0:8001")
    print(f"⚠️ 주의: 임시 Fuseki 데이터셋 '{TEMP_FUSEKI_URL}' 사용")
    print(f"   - 데이터셋이 없으면 먼저 생성해야 합니다")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)