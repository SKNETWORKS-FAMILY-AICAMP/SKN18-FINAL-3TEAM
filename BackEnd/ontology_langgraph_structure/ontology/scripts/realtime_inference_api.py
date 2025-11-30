"""
실시간 SWRL 추론 API

What-if 시나리오 및 동적 추론을 위한 API 서버
"""

import subprocess
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from SPARQLWrapper import SPARQLWrapper, JSON

# ==================== 설정 ====================

# 현재 스크립트 위치: backend/ontology_langgraph_structure/ontology/scripts/
# ontology 디렉토리로 이동
ONTOLOGY_DIR = Path(__file__).parent.parent
REASONER_JAR = ONTOLOGY_DIR / "reasoner/target/swrl-reasoner-0.1.0.jar"
TEMP_FUSEKI_URL = "http://localhost:3030/temp_inference"  # 임시 데이터셋

app = FastAPI(title="SWRL Inference API")


# ==================== 모델 ====================

class InferenceRequest(BaseModel):
    """일반 추론 요청"""
    ontology: str = "korean_history.owl"
    instances: list[str] = []  # 빈 리스트면 instances 폴더의 모든 .ttl 파일 사용
    rules: str = "all_rules.rules"  # 병합된 규칙 파일


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
            result = subprocess.run(
                ["java", "-jar", str(REASONER_JAR),
                 str(ontology), str(merged), str(rules), TEMP_FUSEKI_URL],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise HTTPException(500, f"추론 실패: {result.stderr}")
            
            # 결과 반환
            return {
                "status": "success",
                "message": "추론 완료",
                "fuseki_endpoint": f"{TEMP_FUSEKI_URL}/sparql"
            }
        except subprocess.TimeoutExpired:
            raise HTTPException(500, "추론 시간 초과 (30초)")


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
            result = subprocess.run(
                ["java", "-jar", str(REASONER_JAR),
                 str(ontology), str(merged), str(rules), TEMP_FUSEKI_URL],
                capture_output=True,
                text=True,
                timeout=30
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
    
    # files가 비어있으면 instances 폴더의 모든 .ttl 파일 사용
    if not files:
        if instances_dir.exists():
            files = [f.name for f in instances_dir.glob("*.ttl")]
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
        sparql = SPARQLWrapper(endpoint)
        sparql.setReturnFormat(JSON)
        sparql.setQuery(sparql_query)
        
        results = sparql.query().convert()
        return results
    except Exception as e:
        raise HTTPException(500, f"SPARQL 쿼리 실행 실패: {e}")


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