"""
Parallel Inference Executor Node (통합 버전)

5개의 Thread에서 쿼리 생성 + 추론 실행을 병렬로 수행
- ThreadPoolExecutor로 병렬 처리
- 각 Thread마다: LLM 쿼리 생성 → Jena Reasoner API 호출
- 추론 결과를 TTL 형식으로 저장

경량 모드 (INFERENCE_MODE=light):
- Java Reasoner 없이 Fuseki 직접 쿼리
- 메모리 부족 환경에서 사용
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
FUSEKI_URL = os.getenv("FUSEKI_URL", "http://localhost:3030/korean-history")
INFERENCE_MODE = os.getenv("INFERENCE_MODE", "light")  # "full" (Java Reasoner) or "light" (Fuseki 직접)
QUERY_MODE = os.getenv("QUERY_MODE", "template")  # "llm" (LLM 쿼리 생성) or "template" (템플릿 쿼리, 빠름)
SAVE_INFERENCE_TRIPLES = os.getenv("SAVE_INFERENCE_TRIPLES", "true").lower() == "true"
INFERENCE_OUTPUT_DIR = os.getenv("INFERENCE_OUTPUT_DIR", "./inference_results")


# 질문 유형별 Thread 가중치 (데이터 기반)
THREAD_WEIGHTS = {
    "causal": {
        "event_context": 0.30,    # 사건 맥락 중요
        "actor_network": 0.25,    # 인물 네트워크
        "timeline": 0.20,         # 시간순 정리
        "similar_events": 0.15,   # 유사 사건
        "background": 0.10        # 배경 정보
    },
    "deep_analysis": {
        "background": 0.30,       # 배경 정보 중요
        "actor_network": 0.25,    # 인물 네트워크
        "event_context": 0.20,    # 사건 맥락
        "similar_events": 0.15,   # 유사 사건
        "timeline": 0.10          # 시간순 정리
    },
    "factual": {
        "event_context": 0.35,    # 사실 기반 질문
        "background": 0.25,       # 배경 정보
        "timeline": 0.20,         # 시간순 정리
        "actor_network": 0.10,    # 인물 네트워크
        "similar_events": 0.10    # 유사 사건
    },
    "comparative": {
        "similar_events": 0.35,   # 비교 분석 - 유사 사건 중요
        "event_context": 0.25,    # 사건 맥락
        "actor_network": 0.20,    # 인물 네트워크
        "timeline": 0.10,         # 시간순 정리
        "background": 0.10        # 배경 정보
    },
    "what_if": {
        "event_context": 0.30,    # 가상 시나리오
        "similar_events": 0.25,   # 유사 사건
        "timeline": 0.20,         # 시간순 정리
        "actor_network": 0.15,    # 인물 네트워크
        "background": 0.10        # 배경 정보
    }
}

# 데이터 기반 Thread 설정 (SPARQL 템플릿)
# ⚡ 라벨 기반 검색: URI 대신 라벨로 검색하여 데이터 불일치 문제 해결
DATA_THREADS = {
    "outgoing_relations": {
        "description": "엔티티에서 나가는 모든 관계 (엔티티 → ?)",
        "sparql_template": """
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?entity ?entityLabel ?predicate ?object ?objectLabel WHERE {{
                ?entity rdfs:label ?entityLabel .
                FILTER ({label_filter})
                ?entity ?predicate ?object .
                OPTIONAL {{ ?object rdfs:label ?objectLabel }}
                FILTER(?predicate != rdf:type)
                FILTER(?predicate != rdfs:label)
            }} LIMIT 100
        """,
        "use_milvus": False
    },
    "incoming_relations": {
        "description": "엔티티로 들어오는 모든 관계 (? → 엔티티)",
        "sparql_template": """
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?subject ?subjectLabel ?predicate ?entity ?entityLabel WHERE {{
                ?entity rdfs:label ?entityLabel .
                FILTER ({label_filter})
                ?subject ?predicate ?entity .
                OPTIONAL {{ ?subject rdfs:label ?subjectLabel }}
                FILTER(?predicate != rdf:type)
                FILTER(?predicate != rdfs:label)
            }} LIMIT 100
        """,
        "use_milvus": False
    },
    "entity_properties": {
        "description": "엔티티의 모든 속성 (리터럴 값)",
        "sparql_template": """
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?entity ?entityLabel ?predicate ?value WHERE {{
                ?entity rdfs:label ?entityLabel .
                FILTER ({label_filter})
                ?entity ?predicate ?value .
                FILTER(isLiteral(?value))
                FILTER(?predicate != rdfs:label)
            }} LIMIT 100
        """,
        "use_milvus": False
    },
    "connected_entities": {
        "description": "두 엔티티 사이의 관계",
        "sparql_template": """
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT DISTINCT ?entity1 ?label1 ?predicate ?entity2 ?label2 WHERE {{
                ?entity1 rdfs:label ?label1 .
                ?entity2 rdfs:label ?label2 .
                FILTER ({label_filter1})
                ?entity1 ?predicate ?entity2 .
                FILTER(?entity1 != ?entity2)
                FILTER(?predicate != rdf:type)
                FILTER(?predicate != rdfs:label)
            }} LIMIT 50
        """,
        "use_milvus": False
    },
    "type_and_summary": {
        "description": "엔티티 타입과 요약 정보",
        "sparql_template": """
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?entity ?entityLabel ?type ?summary ?category ?year WHERE {{
                ?entity rdfs:label ?entityLabel .
                FILTER ({label_filter})
                OPTIONAL {{ ?entity rdf:type ?type }}
                OPTIONAL {{ ?entity hist:hasSummary ?summary }}
                OPTIONAL {{ ?entity hist:hasCategory ?category }}
                OPTIONAL {{ ?entity hist:hasYear ?year }}
            }} LIMIT 50
        """,
        "use_milvus": False
    }
}

# 이전 버전 호환을 위해 INFERENCE_PROPERTIES_BY_STAGE도 유지
INFERENCE_PROPERTIES_BY_STAGE = DATA_THREADS


def parallel_inference_executor_node(state: GraphState) -> GraphState:
    """
    5개 Thread에서 쿼리 생성 + 추론 실행을 병렬로 수행

    기존 multi_query_generator_node를 통합하여 효율성 향상:
    - 기존: 쿼리 5개 순차 생성(~10초) → 추론 5개 병렬 실행(~3초) = ~13초
    - 개선: 쿼리생성+추론을 Thread별로 동시 실행 = ~3-5초

    프로퍼티 필터링:
    - classify_node에서 선택된 프로퍼티 그룹으로 SPARQL FILTER 적용
    - 관련 프로퍼티만 검색하여 정확도 향상
    """

    import time
    node_start = time.time()

    query = state.get("query", "")
    query_type = state.get("query_type", "causal")
    entities = state.get("extracted_entities", [])
    hypothetical_triples = state.get("hypothetical_triples", [])
    
    # 질문에서 핵심 키워드 추출 (kiwipiepy 사용)
    try:
        from kiwipiepy import Kiwi
        kiwi = Kiwi()
        tokens = kiwi.tokenize(query)
        # 명사만 추출 (핵심 키워드)
        core_keywords = [t.form for t in tokens if t.tag in ('NNG', 'NNP') and len(t.form) >= 2]
    except:
        # kiwipiepy 없으면 기본 키워드 추출
        import re
        core_keywords = re.findall(r'[가-힣]{2,}', query)
    
    # 엔티티를 핵심 키워드와의 관련도로 정렬
    # 핵심 키워드가 엔티티 이름에 포함되면 우선순위 높임
    def entity_priority(entity):
        name = entity.get("name", "").lower()
        score = 0
        for kw in core_keywords:
            if kw.lower() in name:
                score += 10  # 핵심 키워드 매칭 시 높은 점수
        # URI가 있으면 추가 점수
        if entity.get("uri"):
            score += 1
        return score
    
    entities_sorted = sorted(entities, key=entity_priority, reverse=True)
    
    # 선택된 프로퍼티 (classify_node에서 전달)
    selected_properties = state.get("selected_properties", [])
    selected_groups = state.get("selected_property_groups", [])
    
    # Thread 가중치 설정
    thread_weights = THREAD_WEIGHTS.get(query_type, THREAD_WEIGHTS["causal"])
    
    print(f"\n{'='*70}")
    print(f"[3/6] 병렬 지식 검색 (Parallel Knowledge Retrieval)")
    print(f"{'='*70}")
    print(f"  ├─ Thread 수: {len(DATA_THREADS)}개")
    print(f"  ├─ 엔티티: {len(entities)}개")
    if selected_groups:
        print(f"  └─ 프로퍼티 필터: {', '.join(selected_groups[:3])}{'...' if len(selected_groups) > 3 else ''} ({len(selected_groups)}개)")
    start_time = time.time()
    
    # LLM 초기화 (QUERY_MODE=llm일 때만 필요)
    if QUERY_MODE == "llm":
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            temperature=0
        )
    else:
        llm = None  # 템플릿 모드에서는 LLM 불필요
    
    # ThreadPoolExecutor로 병렬 실행 (쿼리 생성 + 추론 통합)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                execute_unified_thread,
                llm=llm,
                thread_type=thread_type,
                query=query,
                query_type=query_type,
                entities=entities_sorted,  # 정렬된 엔티티 사용 (핵심 키워드 우선)
                hypothetical=hypothetical_triples,
                thread_config=DATA_THREADS[thread_type],
                selected_properties=selected_properties  # 프로퍼티 필터 전달
            ): thread_type
            for thread_type in DATA_THREADS.keys()
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
                
                # 성공적으로 완료 (로그 최소화)
                pass

            except concurrent.futures.TimeoutError:
                results[thread_type] = {"status": "timeout", "bindings": [], "thread_type": thread_type}
            except Exception as e:
                results[thread_type] = {"status": "error", "bindings": [], "error": str(e), "thread_type": thread_type}

    elapsed = time.time() - start_time
    total_bindings = sum(len(r.get("bindings", [])) for r in results.values())

    # Thread별 검색 결과 상세
    print(f"\n      [Thread별 검색 결과]")
    for thread_type, result in results.items():
        bindings = result.get("bindings", [])
        status = result.get("status", "unknown")

        # 상태 아이콘
        status_icon = "✓" if status == "success" else "✗"

        # Thread 이름 정규화 (가독성)
        thread_name_map = {
            "outgoing_relations": "나가는 관계",
            "incoming_relations": "들어오는 관계",
            "entity_properties": "엔티티 속성",
            "connected_entities": "연결 엔티티",
            "type_and_summary": "타입/요약"
        }
        thread_display = thread_name_map.get(thread_type, thread_type)

        print(f"      {status_icon} {thread_display:15s}: {len(bindings):3d}개")

        # 상위 3개 결과 샘플 표시 (라벨만)
        if bindings and len(bindings) > 0:
            for i, binding in enumerate(bindings[:3], 1):
                # 라벨 추출 (정규화된 라벨 우선)
                label = (
                    binding.get("entityLabel", {}).get("value") or
                    binding.get("label", {}).get("value") or
                    binding.get("label1", {}).get("value") or
                    binding.get("subjectLabel", {}).get("value") or
                    binding.get("entity", {}).get("value", "")
                )

                # URI에서 라벨 추출 (라벨이 없는 경우)
                if not label or label.startswith("http"):
                    for key in ["entity", "subject", "event"]:
                        if key in binding:
                            uri = binding[key].get("value", "")
                            if "#" in uri:
                                label = uri.split("#")[-1]
                                break
                            elif "/" in uri:
                                label = uri.split("/")[-1]
                                break

                if label and len(label) > 0:
                    # 라벨 길이 제한
                    label_display = label[:40] + "..." if len(label) > 40 else label
                    print(f"         {i}. {label_display}")

    node_elapsed = time.time() - node_start
    print(f"  └─ 완료: {total_bindings}개 결과 ({node_elapsed:.2f}초)")
    print()

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
            # 추론 결과 저장 완료 (로그 간소화)
        except Exception as e:
            print(f"   경고: 추론 결과 저장 실패: {e}")

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["parallel_knowledge_retrieval"] = node_elapsed

    return {
        **state,
        "multi_queries": multi_queries,  # 생성된 쿼리도 state에 저장
        "thread_weights": thread_weights,
        "parallel_inference_results": results,
        "execution_time": elapsed,
        "inference_ttl_path": inference_ttl_path,
        "executed_nodes": state.get("executed_nodes", []) + ["parallel_inference_executor"],
        "node_execution_times": node_times
    }


def execute_unified_thread(
    llm: ChatOpenAI,
    thread_type: str,
    query: str,
    query_type: str,
    entities: list,
    hypothetical: list,
    thread_config: dict,
    selected_properties: list = None
) -> dict:
    """
    개별 Thread에서 쿼리 생성 + 지식 검색을 순차적으로 수행
    
    Args:
        llm: ChatOpenAI 인스턴스 (Thread 간 공유, QUERY_MODE=llm일 때만 사용)
        thread_type: Thread 타입 (outgoing_relations/incoming_relations/entity_properties/connected_entities/type_and_summary)
        query: 사용자 질문
        query_type: 질문 유형
        entities: 추출된 엔티티 목록
        hypothetical: 가상 트리플 목록 (미사용)
        thread_config: Thread 설정 (sparql_template, use_milvus, description)
        selected_properties: 필터링할 프로퍼티 목록 (classify_node에서 선택)
        
    Returns:
        검색 결과 딕셔너리
    """
    
    description = thread_config.get("description", "")
    use_milvus = thread_config.get("use_milvus", False)
    sparql_template = thread_config.get("sparql_template", "")
    selected_properties = selected_properties or []
    
    # similar_events는 Milvus 검색 사용
    if use_milvus:
        return execute_milvus_search(thread_type, entities, description)
    
    # 1️⃣ SPARQL 쿼리 생성
    if sparql_template and QUERY_MODE == "template":
        # 템플릿 모드: 미리 정의된 SPARQL 템플릿 사용
        # 선택된 프로퍼티로 FILTER 적용
        sparql = generate_template_sparql(thread_type, entities, sparql_template, selected_properties)
    else:
        # Fallback 쿼리 사용
        sparql = generate_fallback_sparql(thread_type, entities)
    
    # 2️⃣ 지식 검색 실행
    result = execute_inference_api(
        thread_type=thread_type,
        sparql=sparql,
        hypothetical=hypothetical,
        query_type=query_type
    )
    
    # 생성된 쿼리도 결과에 포함
    result["sparql"] = sparql
    
    return result


def execute_milvus_search(thread_type: str, entities: list, description: str) -> dict:
    """Milvus를 사용한 유사 사건 검색"""
    try:
        # Milvus 서비스 import
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        
        from db_pipeline.services.milvus_service import get_milvus_service
        
        milvus = get_milvus_service()
        if not milvus or not milvus.connect():
            return {"status": "error", "bindings": [], "thread_type": thread_type, "error": "Milvus 연결 실패"}
        
        # 엔티티 이름으로 유사 사건 검색
        all_results = []
        for entity in entities[:5]:  # 상위 5개 엔티티만
            name = entity.get("name", "")
            if name:
                results = milvus.search(name, top_k=3, threshold=0.5)
                all_results.extend(results)
        
        # 중복 제거
        seen = set()
        unique_results = []
        for r in all_results:
            if r["title"] not in seen:
                seen.add(r["title"])
                unique_results.append(r)
        
        # Fuseki 형식으로 변환
        bindings = [
            {
                "entity": {"value": r.get("title", "")},
                "label": {"value": r.get("title", "")},
                "category": {"value": r.get("category", "")},
                "summary": {"value": r.get("summary", "")[:200] if r.get("summary") else ""},
                "score": {"value": str(r.get("score", 0))}
            }
            for r in unique_results[:10]
        ]
        
        return {
            "status": "success",
            "bindings": bindings,
            "thread_type": thread_type,
            "source": "milvus"
        }
        
    except Exception as e:
        return {"status": "error", "bindings": [], "thread_type": thread_type, "error": str(e)}


def generate_template_sparql(thread_type: str, entities: list, template: str, selected_properties: list = None) -> str:
    """
    템플릿 기반 SPARQL 생성 (라벨 기반 검색)
    
    Args:
        thread_type: Thread 타입
        entities: 엔티티 목록
        template: SPARQL 템플릿
        selected_properties: 필터링할 프로퍼티 목록 (선택된 경우 FILTER 추가)
    """
    
    selected_properties = selected_properties or []
    
    # 엔티티에서 라벨(이름) 추출
    labels = [e.get("name", "") for e in entities if e.get("name")]
    
    if not labels:
        # 라벨이 없으면 URI에서 추출 시도
        for e in entities:
            uri = e.get("uri", "")
            if uri:
                # hist:Person_xxx → 라벨 추출 불가, 이름 필요
                name = e.get("label", "") or e.get("name", "")
                if name and name not in labels:
                    labels.append(name)
    
    if not labels:
        return ""  # 검색할 라벨 없음
    
    # 라벨 FILTER 생성 (정확 매칭 또는 포함 검색)
    label_conditions = []
    for label in labels[:10]:  # 최대 10개 라벨
        # 정확 매칭 우선, 2글자 이상만
        if len(label) >= 2:
            # 정확 매칭: ?entityLabel = "경복궁"
            label_conditions.append(f'?entityLabel = "{label}"')
            # 포함 검색: CONTAINS(?entityLabel, "경복궁")
            # label_conditions.append(f'CONTAINS(?entityLabel, "{label}")')
    
    if not label_conditions:
        return ""
    
    label_filter = " || ".join(label_conditions)
    
    # connected_entities는 두 개의 라벨 필터 필요
    if thread_type == "connected_entities":
        label_filter1 = " || ".join([f'?label1 = "{l}"' for l in labels[:5]])
        sparql = template.format(label_filter1=label_filter1)
    else:
        sparql = template.format(label_filter=label_filter)
    
    # 선택된 프로퍼티가 있으면 FILTER 추가 (outgoing/incoming/connected 관계 검색에)
    if selected_properties and thread_type in ["outgoing_relations", "incoming_relations", "connected_entities"]:
        # 프로퍼티 FILTER 생성
        prop_uris = [f"hist:{prop}" for prop in selected_properties[:20]]  # 최대 20개
        prop_filter = ", ".join(prop_uris)

        if prop_filter:
            # LIMIT 앞에 프로퍼티 FILTER 추가
            filter_clause = f"FILTER(?predicate IN ({prop_filter}))"
            sparql = sparql.replace("}} LIMIT", f"{filter_clause}\n            }} LIMIT")
    
    return sparql


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
    
    # 새로운 데이터 기반 Thread 템플릿 (관계 확장 포함)
    fallback_templates = {
        # ============================================================
        # event_context: 사건 맥락 + 1-hop 관계 확장
        # 엔티티 → 관련 사건/인물 (hasParticipant, occursAt, leadsTo 등)
        # ============================================================
        "event_context": f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?entity ?label ?summary ?related ?relatedLabel ?relationType WHERE {{
    {values_clause}
    ?entity rdfs:label ?label .
    OPTIONAL {{ ?entity hist:hasSummary ?summary }}
    
    # 1-hop 관계 확장: 엔티티와 연결된 모든 것
    OPTIONAL {{
        ?entity ?relationType ?related .
        ?related rdfs:label ?relatedLabel .
        FILTER(?relationType IN (
            hist:hasParticipant, hist:participatesIn,
            hist:occursAt, hist:isLocationOf,
            hist:leadsTo, hist:causedBy,
            hist:hasCommander, hist:commands,
            hist:hasVictor, hist:hasDefeated
        ))
    }}
}} LIMIT 100""",
        
        # ============================================================
        # actor_network: 인물 중심 2-hop 관계 확장
        # 인물 → 관련 사건 → 다른 인물/사건
        # ============================================================
        "actor_network": f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?person ?label ?hop1 ?hop1Label ?hop1Type ?hop2 ?hop2Label WHERE {{
    {values_clause}
    ?entity rdfs:label ?label .
    BIND(?entity AS ?person)
    
    # 1-hop: 인물과 직접 연결된 것 (사건, 기관, 역할)
    OPTIONAL {{
        ?entity ?rel1 ?hop1 .
        ?hop1 rdfs:label ?hop1Label .
        ?hop1 a ?hop1Type .
        FILTER(?rel1 IN (
            hist:participatesIn, hist:commands, hist:affiliatedWith,
            hist:hasRole, hist:authored, hist:teacherOf, hist:studentOf,
            hist:servedUnder, hist:allyOf, hist:enemyOf
        ))
        
        # 2-hop: 관련 사건에 참여한 다른 인물
        OPTIONAL {{
            ?hop1 hist:hasParticipant ?hop2 .
            ?hop2 rdfs:label ?hop2Label .
            FILTER(?hop2 != ?entity)
        }}
    }}
}} LIMIT 100""",
        
        # ============================================================
        # timeline: 시간순 + 인과관계 체인
        # 사건 → 선행 사건 → 후행 사건
        # ============================================================
        "timeline": f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?event ?label ?year ?summary ?causedBy ?causedByLabel ?leadsTo ?leadsToLabel WHERE {{
    {values_clause}
    ?entity rdfs:label ?label .
    BIND(?entity AS ?event)
    OPTIONAL {{ ?entity hist:hasYear ?year }}
    OPTIONAL {{ ?entity hist:hasSummary ?summary }}
    
    # 인과관계 체인: 원인 → 사건 → 결과
    OPTIONAL {{ 
        ?entity hist:causedBy ?causedBy . 
        ?causedBy rdfs:label ?causedByLabel 
    }}
    OPTIONAL {{ 
        ?entity hist:leadsTo ?leadsTo . 
        ?leadsTo rdfs:label ?leadsToLabel 
    }}
    
    # 시간순 관계
    OPTIONAL {{ ?entity hist:precedes ?after . ?after rdfs:label ?afterLabel }}
    OPTIONAL {{ ?before hist:precedes ?entity . ?before rdfs:label ?beforeLabel }}
}} ORDER BY ?year LIMIT 100""",
        
        # ============================================================
        # similar_events: Milvus로 처리됨 (fallback용)
        # ============================================================
        "similar_events": f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?entity ?label ?type ?summary WHERE {{
    {values_clause}
    ?entity rdfs:label ?label .
    ?entity a ?type .
    OPTIONAL {{ ?entity hist:hasSummary ?summary }}
}} LIMIT 30""",
        
        # ============================================================
        # background: 배경 정보 + 관련 정책/제도 확장
        # 사건 → 관련 정책 → 영향받은 것들
        # ============================================================
        "background": f"""PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?entity ?label ?summary ?category ?relatedPolicy ?policyLabel ?policySummary WHERE {{
    {values_clause}
    ?entity rdfs:label ?label .
    OPTIONAL {{ ?entity hist:hasSummary ?summary }}
    OPTIONAL {{ ?entity hist:hasCategory ?category }}
    
    # 관련 정책/제도 확장
    OPTIONAL {{
        ?entity hist:relatedToPolicy ?relatedPolicy .
        ?relatedPolicy rdfs:label ?policyLabel .
        OPTIONAL {{ ?relatedPolicy hist:hasSummary ?policySummary }}
    }}
    
    # 원인/결과 관계
    OPTIONAL {{ 
        ?entity hist:hasCause ?cause . 
        ?cause rdfs:label ?causeLabel 
    }}
    OPTIONAL {{ 
        ?entity hist:hasResult ?result . 
        ?result rdfs:label ?resultLabel 
    }}
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
    """
    추론 실행 (모드에 따라 분기)
    
    - INFERENCE_MODE=full: Java Reasoner API 호출 (8GB 메모리 필요)
    - INFERENCE_MODE=light: Fuseki 직접 SPARQL 쿼리 (메모리 절약)
    """
    
    if INFERENCE_MODE == "light":
        # 경량 모드: Fuseki 직접 쿼리 (Java Reasoner 불필요)
        return execute_fuseki_direct(thread_type, sparql)
    
    # 전체 모드: Java Reasoner API 호출
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


def execute_fuseki_direct(thread_type: str, sparql: str, debug: bool = False) -> dict:
    """
    Fuseki에 직접 SPARQL 쿼리 (경량 모드)
    
    Java Reasoner 없이 이미 Fuseki에 저장된 데이터에서 쿼리.
    추론은 제한되지만 메모리 부족 환경에서 유용.
    """
    
    endpoint = f"{FUSEKI_URL}/sparql"
    
    # 디버그 모드: SPARQL 쿼리 출력
    if debug:
        print(f"\n[DEBUG] {thread_type} SPARQL:")
        print(sparql[:500])
    
    try:
        response = requests.post(
            endpoint,
            data={"query": sparql},
            headers={"Accept": "application/sparql-results+json"},
            timeout=30
        )
        
        # 에러 응답 상세 로그
        if response.status_code != 200:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            if debug:
                print(f"[DEBUG] {thread_type} 에러: {error_msg}")
            return {
                "status": "error",
                "bindings": [],
                "error": error_msg,
                "thread_type": thread_type
            }
        
        result = response.json()
        bindings = result.get("results", {}).get("bindings", [])
        
        return {
            "status": "success",
            "bindings": bindings,
            "fuseki_endpoint": endpoint,
            "thread_type": thread_type,
            "mode": "light"
        }
        
    except requests.exceptions.ConnectionError:
        return {
            "status": "error", 
            "bindings": [], 
            "error": f"Fuseki 서버 연결 실패 ({endpoint}). Docker 컨테이너가 실행 중인지 확인하세요.",
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
