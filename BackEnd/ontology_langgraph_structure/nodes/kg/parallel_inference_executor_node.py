"""
Parallel Inference Executor Node (통합 버전)

5개의 Thread에서 쿼리 생성 + 추론 실행을 병렬로 수행
- ThreadPoolExecutor로 병렬 처리
- 각 Thread마다: LLM 쿼리 생성 → Jena Reasoner API 호출
- 추론 결과를 TTL 형식으로 저장
"""

import os
import time
import requests
import concurrent.futures
from datetime import datetime
from pathlib import Path
from langchain_openai import ChatOpenAI
from state import GraphState


API_URL = os.getenv("INFERENCE_API_URL", "http://localhost:8001")
SAVE_INFERENCE_TRIPLES = os.getenv("SAVE_INFERENCE_TRIPLES", "true").lower() == "true"
INFERENCE_OUTPUT_DIR = os.getenv("INFERENCE_OUTPUT_DIR", "./inference_results")


# 질문 유형별 Thread 가중치 (5-stage plan 기반)
THREAD_WEIGHTS = {
    "causal": {
        "causal": 0.35,      # Stage 2: 역사 시뮬레이터
        "person": 0.25,      # Stage 1, 3: 인물 분석
        "temporal": 0.20,    # Stage 4: 시대적 배경
        "pattern": 0.10,     # Stage 5: 심화 분석
        "motive": 0.10       # Stage 1: 동기 분석
    },
    "what_if": {
        "causal": 0.45,      # Stage 2: 가상 인과 중요
        "person": 0.20,      # Stage 1, 3: 인물 영향
        "temporal": 0.15,    # Stage 4: 시대 맥락
        "pattern": 0.10,     # Stage 5: 전략 패턴
        "motive": 0.10       # Stage 1: 동기
    },
    "deep_analysis": {
        "motive": 0.30,      # Stage 1: 동기 분석 중요
        "person": 0.25,      # Stage 1, 3: 인물 관계
        "causal": 0.20,      # Stage 2: 인과관계
        "pattern": 0.15,     # Stage 5: 패턴 분석
        "temporal": 0.10     # Stage 4: 시대 배경
    }
}

# Stage별 추론 프로퍼티 매핑
INFERENCE_PROPERTIES_BY_STAGE = {
    "causal": {
        "description": "Stage 2: 역사 시뮬레이터 (인과관계 추론)",
        "properties": [
            "hist:leadsTo", "hist:causedBy", "hist:hasImpact", "hist:hasOutcome",
            "hist:indirectlyCausedBy", "hist:hasStatus", "hist:hasStrategicAdvantage",
            "hist:strategicImportance", "hist:relatedToPolicy"
        ]
    },
    "person": {
        "description": "Stage 1, 3: 비하인드 스토리 + 인물 분석",
        "properties": [
            "hist:commands", "hist:participatesIn", "hist:affiliatedWith", "hist:hasRole",
            "hist:hasAchievement", "hist:initiatedBy", "hist:establishedBy",
            "hist:hasRelationshipWith", "hist:hasEnemyRelationship", "hist:hasLocalTies",
            "hist:hasInfluence", "hist:hasLoyalty"
        ]
    },
    "temporal": {
        "description": "Stage 4: 시대적 배경 분석",
        "properties": [
            "hist:hasYear", "hist:hasDate", "hist:hasBirthYear", "hist:hasDeathYear",
            "hist:occursBefore", "hist:occursAfter", "hist:contemporaryWith",
            "hist:simultaneousWith", "hist:hasLifespan", "hist:hasDuration", "hist:belongsToPeriod"
        ]
    },
    "pattern": {
        "description": "Stage 5: 심화 분석 (전략 패턴)",
        "properties": [
            "hist:occursAt", "hist:hasVictor", "hist:hasDefeated", "hist:hasStrategyPattern",
            "hist:hasWinningStreak", "hist:hasComebackPattern", "hist:hasContestedStatus",
            "hist:hasCommandPattern"
        ]
    },
    "motive": {
        "description": "Stage 1: 비하인드 스토리 (동기 분석)",
        "properties": [
            "hist:commands", "hist:bornIn", "hist:affiliatedWith", "hist:initiatedBy",
            "hist:establishedBy", "hist:hasObjective", "hist:hasPurpose", "hist:hasMotive",
            "hist:hasLocalTies"
        ]
    }
}


def parallel_inference_executor_node(state: GraphState) -> GraphState:
    """
    5개 Thread에서 쿼리 생성 + 추론 실행을 병렬로 수행
    
    기존 multi_query_generator_node를 통합하여 효율성 향상:
    - 기존: 쿼리 5개 순차 생성(~10초) → 추론 5개 병렬 실행(~3초) = ~13초
    - 개선: 쿼리생성+추론을 Thread별로 동시 실행 = ~3-5초
    """
    
    query = state.get("query", "")
    query_type = state.get("query_type", "causal")
    entities = state.get("extracted_entities", [])
    hypothetical_triples = state.get("hypothetical_triples", [])
    
    # Thread 가중치 설정
    thread_weights = THREAD_WEIGHTS.get(query_type, THREAD_WEIGHTS["causal"])
    
    print(f"\n⚡ 병렬 추론 시작 (쿼리생성+실행 통합, {len(INFERENCE_PROPERTIES_BY_STAGE)}개 Thread)")
    print(f"   - 질문 유형: {query_type}")
    print(f"   - 추출된 엔티티: {len(entities)}개")
    start_time = time.time()
    
    # LLM 초기화 (Thread 간 공유)
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0
    )
    
    # ThreadPoolExecutor로 병렬 실행 (쿼리 생성 + 추론 통합)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                execute_unified_thread,
                llm=llm,
                thread_type=thread_type,
                query=query,
                query_type=query_type,
                entities=entities,
                hypothetical=hypothetical_triples,
                properties=INFERENCE_PROPERTIES_BY_STAGE[thread_type]["properties"],
                description=INFERENCE_PROPERTIES_BY_STAGE[thread_type]["description"]
            ): thread_type
            for thread_type in INFERENCE_PROPERTIES_BY_STAGE.keys()
        }
        
        # 결과 수집
        results = {}
        multi_queries = {}  # 생성된 쿼리도 저장 (디버깅용)
        
        for future in concurrent.futures.as_completed(futures):
            thread_type = futures[future]
            try:
                result = future.result(timeout=45)  # 쿼리 생성 + 실행이므로 timeout 증가
                results[thread_type] = result
                multi_queries[thread_type] = result.get("sparql", "")
                
                status_icon = "✅" if result["status"] == "success" else "⚠️"
                print(f"   {status_icon} {thread_type}: {result['status']} ({len(result.get('bindings', []))}개 결과)")
                
            except concurrent.futures.TimeoutError:
                print(f"   ⏱️ {thread_type}: 시간 초과 (45초)")
                results[thread_type] = {"status": "timeout", "bindings": [], "thread_type": thread_type}
            except Exception as e:
                print(f"   ❌ {thread_type}: 실패 - {e}")
                results[thread_type] = {"status": "error", "bindings": [], "error": str(e), "thread_type": thread_type}
    
    elapsed = time.time() - start_time
    print(f"⚡ 병렬 추론 완료 ({elapsed:.1f}초)")
    
    # 총 결과 통계
    total_bindings = sum(len(r.get("bindings", [])) for r in results.values())
    print(f"   - 총 추론 결과: {total_bindings}개")
    
    # 추론 결과를 TTL로 저장 (옵션)
    inference_ttl_path = None
    if SAVE_INFERENCE_TRIPLES and total_bindings > 0:
        try:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            inference_ttl_path = save_inference_results_as_ttl(
                results=results,
                query=query,
                session_id=session_id,
                execution_time=elapsed
            )
            print(f"   💾 추론 결과 저장: {inference_ttl_path}")
        except Exception as e:
            print(f"   ⚠️ 추론 결과 저장 실패: {e}")
    
    return {
        **state,
        "multi_queries": multi_queries,  # 생성된 쿼리도 state에 저장
        "thread_weights": thread_weights,
        "parallel_inference_results": results,
        "execution_time": elapsed,
        "inference_ttl_path": inference_ttl_path,
        "executed_nodes": state.get("executed_nodes", []) + ["parallel_inference_executor"]
    }


def execute_unified_thread(
    llm: ChatOpenAI,
    thread_type: str,
    query: str,
    query_type: str,
    entities: list,
    hypothetical: list,
    properties: list,
    description: str
) -> dict:
    """
    개별 Thread에서 쿼리 생성 + 추론 실행을 순차적으로 수행
    
    Args:
        llm: ChatOpenAI 인스턴스 (Thread 간 공유)
        thread_type: Thread 타입 (causal/person/temporal/pattern/motive)
        query: 사용자 질문
        query_type: 질문 유형
        entities: 추출된 엔티티 목록
        hypothetical: 가상 트리플 목록 (what-if용)
        properties: 사용 가능한 프로퍼티 목록
        description: Stage 설명
        
    Returns:
        추론 결과 딕셔너리
    """
    
    # 1️⃣ SPARQL 쿼리 생성 (LLM)
    try:
        sparql = generate_sparql_with_llm(
            llm=llm,
            query=query,
            query_type=query_type,
            thread_type=thread_type,
            entities=entities,
            properties=properties,
            description=description
        )
    except Exception as e:
        # LLM 실패 시 fallback 쿼리 사용
        sparql = generate_fallback_sparql(thread_type, entities)
    
    # 2️⃣ 추론 실행 (Jena Reasoner API)
    result = execute_inference_api(
        thread_type=thread_type,
        sparql=sparql,
        hypothetical=hypothetical,
        query_type=query_type
    )
    
    # 생성된 쿼리도 결과에 포함
    result["sparql"] = sparql
    
    return result


def generate_sparql_with_llm(
    llm: ChatOpenAI,
    query: str,
    query_type: str,
    thread_type: str,
    entities: list,
    properties: list,
    description: str
) -> str:
    """LLM을 사용하여 특정 Stage에 맞는 SPARQL 쿼리 생성"""
    
    # 엔티티 정보 포맷팅 (이름과 URI 모두 포함)
    entity_info = "\n".join([
        f"- {e.get('type', 'Unknown')}: {e.get('name', e.get('value', 'N/A'))} (URI: {e.get('uri', 'N/A')})"
        for e in entities
    ]) if entities else "없음"
    
    # 프로퍼티 목록 포맷팅
    properties_info = "\n".join([f"  - {prop}" for prop in properties])
    
    sparql_prompt = f"""당신은 한국 역사 온톨로지 SPARQL 쿼리 생성 전문가입니다.

**분석 단계:** {description}

**사용자 질문:** {query}
**질문 유형:** {query_type}

**추출된 엔티티 (이름과 URI 포함):**
{entity_info}

**사용 가능한 프로퍼티:**
{properties_info}

**네임스페이스:**
PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

**중요 요구사항:**
1. 위 프로퍼티만 사용하여 SPARQL SELECT 쿼리 작성
2. **엔티티 검색은 URI를 직접 사용하세요** (예: hist:Person_69465817)
3. 제공된 URI가 없는 경우에만 rdfs:label로 검색
4. OPTIONAL 절을 사용하여 일부 데이터가 없어도 결과 반환
5. LIMIT 100 설정
6. 반드시 유효한 SPARQL 쿼리만 출력 (설명 제외)

**예시 (URI 직접 사용):**
```sparql
SELECT ?event ?year WHERE {{
  hist:Person_69465817 hist:participatesIn ?event .
  OPTIONAL {{ ?event hist:hasYear ?year }}
}} LIMIT 100
```"""
    
    response = llm.invoke(sparql_prompt)
    sparql_query = response.content.strip()
    
    # 코드 블록 제거
    if "```sparql" in sparql_query:
        sparql_query = sparql_query.split("```sparql")[1].split("```")[0].strip()
    elif "```" in sparql_query:
        sparql_query = sparql_query.split("```")[1].split("```")[0].strip()
    
    return sparql_query


def generate_fallback_sparql(thread_type: str, entities: list) -> str:
    """LLM 실패 시 기본 SPARQL 쿼리 반환"""
    
    # 엔티티 URI 추출 (hist:Person_xxx 형식)
    entity_uris = []
    for e in entities:
        uri = e.get("uri", "")
        if uri:
            # hist:Person_xxx → Person_xxx
            if uri.startswith("hist:"):
                entity_uris.append(uri)
            else:
                entity_uris.append(f"hist:{uri}")
    
    # VALUES 절 생성 (더 효율적인 엔티티 필터링)
    if entity_uris:
        values_clause = "VALUES ?entity { " + " ".join(entity_uris) + " }"
    else:
        values_clause = ""
    
    fallback_templates = {
        "causal": f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?subject ?subjectLabel ?predicate ?object ?objectLabel WHERE {{
    {values_clause}
    {{ ?entity hist:leadsTo ?object . ?subject hist:leadsTo ?object . FILTER(?subject = ?entity) }}
    UNION
    {{ ?subject hist:leadsTo ?entity . BIND(?entity AS ?object) }}
    OPTIONAL {{ ?subject rdfs:label ?subjectLabel }}
    OPTIONAL {{ ?object rdfs:label ?objectLabel }}
    BIND(hist:leadsTo AS ?predicate)
}} LIMIT 100""",
        
        "person": f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?person ?personLabel ?property ?value WHERE {{
    {values_clause}
    ?entity ?property ?value .
    BIND(?entity AS ?person)
    OPTIONAL {{ ?entity rdfs:label ?personLabel }}
    FILTER(?property IN (hist:participatesIn, hist:commands, hist:affiliatedWith, hist:hasRole, hist:hasAchievement))
}} LIMIT 100""",
        
        "temporal": f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?entity ?entityLabel ?year WHERE {{
    {values_clause}
    ?entity hist:hasYear ?year .
    OPTIONAL {{ ?entity rdfs:label ?entityLabel }}
}} LIMIT 100""",
        
        "pattern": f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?entity ?entityLabel ?pattern WHERE {{
    {values_clause}
    ?entity ?prop ?pattern .
    OPTIONAL {{ ?entity rdfs:label ?entityLabel }}
    FILTER(?prop IN (hist:hasStrategyPattern, hist:occursAt, hist:hasVictor, hist:hasDefeated))
}} LIMIT 100""",
        
        "motive": f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?entity ?entityLabel ?motive WHERE {{
    {values_clause}
    ?entity ?prop ?motive .
    OPTIONAL {{ ?entity rdfs:label ?entityLabel }}
    FILTER(?prop IN (hist:hasMotive, hist:hasObjective, hist:hasPurpose, hist:initiatedBy))
}} LIMIT 100"""
    }
    
    return fallback_templates.get(thread_type, f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?s ?p ?o ?sLabel WHERE {{
    {values_clause}
    ?entity ?p ?o .
    BIND(?entity AS ?s)
    OPTIONAL {{ ?s rdfs:label ?sLabel }}
}} LIMIT 100""")


def execute_inference_api(thread_type: str, sparql: str, hypothetical: list, query_type: str) -> dict:
    """Jena Reasoner API 호출"""
    
    use_hypothetical = (query_type == "what_if" and thread_type in ["causal", "person", "temporal"])
    rules_file = f"{thread_type}_inference.rules"
    
    if use_hypothetical and hypothetical:
        payload = {
            "base_ontology": "korean_history.owl",
            "base_instances": [],
            "rules": rules_file,
            "hypothetical_triples": hypothetical,
            "query": sparql
        }
        endpoint = f"{API_URL}/what-if"
    else:
        payload = {
            "ontology": "korean_history.owl",
            "instances": [],
            "rules": rules_file,
            "query": sparql  # SPARQL 쿼리 추가
        }
        endpoint = f"{API_URL}/infer"
    
    try:
        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "results" in result:
            bindings = result.get("results", {}).get("results", {}).get("bindings", [])
        else:
            bindings = []
        
        return {
            "status": "success",
            "bindings": bindings,
            "fuseki_endpoint": result.get("fuseki_endpoint"),
            "thread_type": thread_type
        }
        
    except requests.exceptions.Timeout:
        return {"status": "timeout", "bindings": [], "thread_type": thread_type}
    except Exception as e:
        return {"status": "error", "bindings": [], "error": str(e), "thread_type": thread_type}


def save_inference_results_as_ttl(
    results: dict,
    query: str,
    session_id: str,
    execution_time: float
) -> str:
    """추론 결과를 TTL 파일로 저장"""
    
    try:
        from utils.inference_triple_generator import InferenceTripleGenerator
        
        output_dir = Path(INFERENCE_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"inference_{session_id}.ttl"
        
        generator = InferenceTripleGenerator()
        
        generator.save_triples_to_file(
            inference_results=results,
            output_path=str(output_path),
            session_id=session_id
        )
        
        metadata_ttl = generator.generate_inference_metadata(
            inference_results=results,
            session_id=session_id,
            query=query,
            execution_time=execution_time
        )
        
        with open(output_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(metadata_ttl)
        
        return str(output_path)
        
    except ImportError:
        # InferenceTripleGenerator가 없는 경우 단순 저장
        output_dir = Path(INFERENCE_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"inference_{session_id}.json"
        
        import json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"query": query, "results": results, "execution_time": execution_time}, f, ensure_ascii=False, indent=2)
        
        return str(output_path)
