"""
Semantic Expander Node

엔티티 추출 후, 의미론적으로 관련된 엔티티를 확장하는 노드:
1. 시간적 맥락 확장 (±10년 이내 이벤트)
2. 카테고리 기반 주제 확장 (동일 카테고리 이벤트)
3. 벡터 유사도 확장 (pgvector)
4. 인과관계 체인 확장 (leadsTo, ledTo, causes)

이 노드는 entity_expander 이후, parallel_knowledge_retrieval 이전에 실행됩니다.
"""

import os
import sys
import requests
from pathlib import Path
from backend.langgraph_fuseki.state import GraphState
from backend.langgraph_fuseki.config import (
    FUSEKI_URL,
    USE_PGVECTOR,
    SEMANTIC_EXPANDER_TOP_N,
    FIXED_SCORE_CAUSAL_CHAIN,
    FIXED_SCORE_TEMPORAL,
    FIXED_SCORE_CATEGORY,
    FIXED_SCORE_PGVECTOR
)

# 상위 디렉토리를 경로에 추가 (entity_expander_node와 동일한 방식)
_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # langgraph_fuseki
_parent_dir = os.path.dirname(_base_dir)  # backend
_project_root = os.path.dirname(_parent_dir)  # SKN18-FINAL-3TEAM (프로젝트 루트)
sys.path.insert(0, _base_dir)
sys.path.insert(0, _parent_dir)
sys.path.insert(0, _project_root)  # 프로젝트 루트 추가 (backend.db_pipeline import용)

# pgvector 서비스 lazy loading
_pgvector_service = None

# 벡터 유사도 점수 사용 여부 (RAGAS 평가 시 false로 설정)
USE_VECTOR_SIMILARITY_SCORE = os.getenv("USE_VECTOR_SIMILARITY_SCORE", "false").lower() == "true"

# 확장 방법별 가중치 (config에서 가져온 값 사용)
FIXED_SCORES = {
    "causal_chain": FIXED_SCORE_CAUSAL_CHAIN,
    "temporal": FIXED_SCORE_TEMPORAL,
    "category": FIXED_SCORE_CATEGORY,
    "pgvector": FIXED_SCORE_PGVECTOR
}

def calculate_relevance_score(similarity, expansion_method):
    """
    관련성 점수 계산:
    - pgvector 확장: 벡터 유사도가 있으면 유사도 × 가중치, 없으면 가중치 사용
    - 다른 확장 방법: 가중치 사용

    Args:
        similarity: 벡터 유사도 (0-1) 또는 None
        expansion_method: 확장 방법 ("causal_chain", "temporal", "category", "pgvector")

    Returns:
        관련성 점수 (0-1)

    Examples:
        >>> calculate_relevance_score(0.88, "pgvector")
        0.88  # 유사도(0.88) × 가중치(1.0) = 0.88

        >>> calculate_relevance_score(None, "pgvector")
        1.0  # 벡터 유사도 없으면 가중치만 사용

        >>> calculate_relevance_score(None, "temporal")
        1.0  # 가중치 사용
    """
    weight = FIXED_SCORES.get(expansion_method, 1.0)
    
    # pgvector 확장이고 벡터 유사도가 있고 USE_VECTOR_SIMILARITY_SCORE=true이면 유사도 × 가중치
    if expansion_method == "pgvector" and similarity is not None and USE_VECTOR_SIMILARITY_SCORE:
        return similarity * weight

    # 그 외의 경우 가중치만 사용
    return weight


def get_pgvector_service():
    """pgvector 서비스 lazy loading"""
    global _pgvector_service
    if _pgvector_service is None and USE_PGVECTOR:
        try:
            # load_title_embeddings.py와 동일한 import 방식 사용
            from backend.db_pipeline.postgres.services.title_vector_service import TitleVectorService
            
            _pgvector_service = TitleVectorService()
            print("  │  └─ pgvector 서비스 초기화 완료")
        except ImportError as e:
            print(f"  │  └─ pgvector 서비스 import 실패: {e}")
            print("  │  └─ TTL 매칭만 사용 (psycopg2-binary 설치 필요: pip install psycopg2-binary)")
        except Exception as e:
            print(f"  │  └─ pgvector 초기화 실패: {e}")
    return _pgvector_service


def expand_by_temporal_context(entities: list, ttl_data: dict, window_years: int = 10) -> list:
    """
    시간적 맥락 확장: 엔티티와 동일 시대 (±window_years) 이벤트 찾기

    Args:
        entities: 추출된 엔티티 리스트
        ttl_data: TTL 데이터 (label_to_uri, uri_to_type)
        window_years: 시간 윈도우 (±N년)

    Returns:
        시간적으로 관련된 엔티티 리스트
    """

    expanded_entities = []
    seen = set()

    # 엔티티에서 연도 추출 (Person: BirthYear/DeathYear, Event: hasYear/hasStartYear/hasEndYear)
    entity_years = []

    for entity in entities[:10]:  # 상위 10개만
        uri = entity.get("uri")
        entity_type = entity.get("type", "")
        entity_name = entity.get("name", "")
        if not uri:
            continue

        # SPARQL로 연도 조회 (타입별 다른 프로퍼티 사용)
        # URI는 hist:Person_xxx 형식이므로 그대로 사용
        if entity_type == "Person":
            # Person: hasBirthYear 또는 hasDeathYear 사용
            sparql = f"""
                PREFIX hist: <http://www.example.org/korean-history#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

                SELECT ?year WHERE {{
                    {{
                        {uri} hist:hasBirthYear ?year .
                    }}
                    UNION
                    {{
                        {uri} hist:hasDeathYear ?year .
                    }}
                }} LIMIT 1
            """
        else:
            # Event, Battle 등: hasYear, hasStartYear, hasEndYear 모두 확인
            sparql = f"""
                PREFIX hist: <http://www.example.org/korean-history#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

                SELECT ?year WHERE {{
                    {{
                        {uri} hist:hasYear ?year .
                    }}
                    UNION
                    {{
                        {uri} hist:hasStartYear ?year .
                    }}
                    UNION
                    {{
                        {uri} hist:hasEndYear ?year .
                    }}
                }} LIMIT 1
            """

        try:
            response = requests.post(
                f"{FUSEKI_URL}/sparql",
                data={"query": sparql},
                headers={"Accept": "application/sparql-results+json"},
                timeout=2
            )

            if response.status_code == 200:
                results = response.json()
                bindings = results.get("results", {}).get("bindings", [])
                if bindings:
                    year = bindings[0].get("year", {}).get("value")
                    if year:
                        try:
                            year_int = int(year)
                            entity_years.append((entity, year_int))
                        except ValueError:
                            pass
        except:
            pass

    if not entity_years:
        return []

    # 각 연도에 대해 ±window_years 이내 이벤트 검색
    for entity, year in entity_years[:5]:  # 최대 5개 엔티티
        min_year = year - window_years
        max_year = year + window_years

        sparql = f"""
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            SELECT DISTINCT ?entity ?label ?type ?year WHERE {{
                ?entity rdf:type ?type .
                ?entity rdfs:label ?label .
                FILTER(?type IN (hist:Event, hist:Battle))
                {{
                    # hasYear가 있는 경우
                    ?entity hist:hasYear ?year .
                    FILTER(?year >= {min_year} && ?year <= {max_year})
                }}
                UNION
                {{
                    # hasStartYear만 있는 경우
                    ?entity hist:hasStartYear ?year .
                    FILTER(?year >= {min_year} && ?year <= {max_year})
                }}
                UNION
                {{
                    # hasEndYear만 있는 경우
                    ?entity hist:hasEndYear ?year .
                    FILTER(?year >= {min_year} && ?year <= {max_year})
                }}
                UNION
                {{
                    # hasStartYear와 hasEndYear가 모두 있는 경우 (기간이 겹치는 경우 포함)
                    ?entity hist:hasStartYear ?startYear .
                    ?entity hist:hasEndYear ?endYear .
                    BIND(?startYear AS ?year)
                    FILTER(
                        (?startYear >= {min_year} && ?startYear <= {max_year}) ||
                        (?endYear >= {min_year} && ?endYear <= {max_year}) ||
                        (?startYear <= {min_year} && ?endYear >= {max_year})
                    )
                }}
            }} LIMIT 10
        """

        try:
            response = requests.post(
                f"{FUSEKI_URL}/sparql",
                data={"query": sparql},
                headers={"Accept": "application/sparql-results+json"},
                timeout=3
            )

            if response.status_code == 200:
                results = response.json()
                bindings = results.get("results", {}).get("bindings", [])

                for binding in bindings:
                    uri = binding.get("entity", {}).get("value", "")
                    label = binding.get("label", {}).get("value", "")
                    entity_type = binding.get("type", {}).get("value", "").split("#")[-1]

                    if uri not in seen and label:
                        seen.add(uri)
                        expanded_entities.append({
                            "type": entity_type,
                            "name": label,
                            "uri": uri,
                            "matched": True,
                            "expansion_method": "temporal",
                            "expansion_source": entity.get("name"),
                            "relevance_score": calculate_relevance_score(None, "temporal")  # 가중치 사용
                        })
        except:
            pass

    return expanded_entities


def expand_by_category(entities: list, ttl_data: dict) -> list:
    """
    카테고리 기반 주제 확장: 동일 카테고리의 다른 엔티티 찾기

    Args:
        entities: 추출된 엔티티 리스트
        ttl_data: TTL 데이터

    Returns:
        카테고리가 동일한 엔티티 리스트
    """

    expanded_entities = []
    seen = set()

    for entity in entities[:8]:  # 상위 8개만
        uri = entity.get("uri")
        entity_name = entity.get("name", "")
        if not uri:
            continue

        # URI 형식 처리: hist:Entity_xxx 형태면 그대로 사용, full URI면 <> 감싸기
        if uri.startswith("hist:"):
            # PREFIX 형식 (hist:Person_xxx) - 그대로 사용
            uri_sparql = uri
        elif uri.startswith("http://"):
            # Full URI 형식 - <> 감싸기
            uri_sparql = f"<{uri}>"
        elif uri.startswith("<"):
            # 이미 <> 감싸져 있음
            uri_sparql = uri
        else:
            # 기타 형식 - hist: prefix 추가
            uri_sparql = f"hist:{uri}"

        # 1. 엔티티의 카테고리 조회 (hist:category 또는 hist:hasCategory 모두 확인)
        sparql_category = f"""
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT ?category WHERE {{
                {{
                    {uri_sparql} hist:hasCategory ?category .
                }}
                UNION
                {{
                    {uri_sparql} hist:category ?category .
                }}
            }} LIMIT 1
        """

        try:
            response = requests.post(
                f"{FUSEKI_URL}/sparql",
                data={"query": sparql_category},
                headers={"Accept": "application/sparql-results+json"},
                timeout=2
            )

            if response.status_code != 200:
                print(f"  │  │  └─ [{entity_name}] 카테고리 조회 실패 (HTTP {response.status_code})")
                continue

            results = response.json()
            bindings = results.get("results", {}).get("bindings", [])
            if not bindings:
                print(f"  │  │  └─ [{entity_name}] 카테고리 없음")
                continue

            category = bindings[0].get("category", {}).get("value")
            if not category:
                print(f"  │  │  └─ [{entity_name}] 카테고리 값 없음")
                continue

            print(f"  │  ├─ [{entity_name}] 카테고리: {category}, 동일 카테고리 검색 중...")

            # 2. 동일 카테고리의 다른 엔티티 검색 (hist:category 또는 hist:hasCategory 모두 확인)
            sparql_similar = f"""
                PREFIX hist: <http://www.example.org/korean-history#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                SELECT DISTINCT ?entity ?label ?type WHERE {{
                    {{
                        ?entity hist:hasCategory "{category}" .
                        ?entity rdfs:label ?label .
                        ?entity rdf:type ?type .
                        FILTER(?entity != {uri_sparql})
                    }}
                    UNION
                    {{
                        ?entity hist:category "{category}" .
                        ?entity rdfs:label ?label .
                        ?entity rdf:type ?type .
                        FILTER(?entity != {uri_sparql})
                    }}
                }} LIMIT 8
            """

            response2 = requests.post(
                f"{FUSEKI_URL}/sparql",
                data={"query": sparql_similar},
                headers={"Accept": "application/sparql-results+json"},
                timeout=3
            )

            if response2.status_code == 200:
                results2 = response2.json()
                bindings2 = results2.get("results", {}).get("bindings", [])
                print(f"  │  │  └─ SPARQL 결과: {len(bindings2)}개 발견")

                for binding in bindings2:
                    uri_new = binding.get("entity", {}).get("value", "")
                    label = binding.get("label", {}).get("value", "")
                    entity_type = binding.get("type", {}).get("value", "").split("#")[-1]

                    if uri_new not in seen and label:
                        seen.add(uri_new)
                        expanded_entities.append({
                            "type": entity_type,
                            "name": label,
                            "uri": uri_new,
                            "matched": True,
                            "expansion_method": "category",
                            "expansion_source": entity.get("name"),
                            "category": category,
                            "relevance_score": calculate_relevance_score(None, "category")  # 가중치 사용
                        })
            else:
                print(f"  │  │  └─ 동일 카테고리 검색 실패 (HTTP {response2.status_code})")
        except Exception as e:
            print(f"  │  │  └─ [{entity_name}] 예외 발생 - {str(e)[:60]}")

    return expanded_entities


def expand_by_causal_chain(entities: list, ttl_data: dict, max_hops: int = 3) -> list:
    """
    인과관계 체인 확장: leadsTo, ledTo, causes 관계를 따라 확장

    Args:
        entities: 추출된 엔티티 리스트
        ttl_data: TTL 데이터
        max_hops: 최대 hop 수 (기본 3)

    Returns:
        인과관계로 연결된 엔티티 리스트
    """

    expanded_entities = []
    seen = set()

    print(f"  │  ├─ [인과관계 확장] {len(entities[:5])}개 엔티티 대상")

    for entity in entities[:5]:  # 상위 5개만
        uri = entity.get("uri")
        entity_name = entity.get("name", "")
        entity_type = entity.get("type", "")
        if not uri:
            continue

        print(f"  │  ├─ [{entity_name}] 인과관계 체인 검색 중...")

        # URI 형식 처리: hist:Entity_xxx 형태면 그대로 사용, full URI면 <> 감싸기
        if uri.startswith("hist:"):
            uri_sparql = uri
        elif uri.startswith("http://"):
            uri_sparql = f"<{uri}>"
        elif uri.startswith("<"):
            uri_sparql = uri
        else:
            uri_sparql = f"hist:{uri}"

        # Person 타입인 경우, 관련 Event를 먼저 찾아서 그 Event의 인과관계를 검색
        if entity_type == "Person":
            # Person과 관련된 Event 찾기 (양방향: participatesIn, involvesPerson 등)
            sparql = f"""
                PREFIX hist: <http://www.example.org/korean-history#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                SELECT DISTINCT ?related ?label ?type ?predicate WHERE {{
                    {{
                        # Person → Event (participatesIn)
                        {uri_sparql} hist:participatesIn ?event .
                        ?event rdf:type hist:Event .
                        
                        # 그 Event의 인과관계 찾기 (leadsTo, ledTo, causes 사용)
                        {{
                            ?event ?predicate ?related .
                            ?related rdfs:label ?label .
                            ?related rdf:type ?type .
                            FILTER(?predicate IN (hist:leadsTo, hist:ledTo, hist:causes))
                        }}
                        UNION
                        {{
                            ?related ?predicate ?event .
                            ?related rdfs:label ?label .
                            ?related rdf:type ?type .
                            FILTER(?predicate IN (hist:leadsTo, hist:ledTo, hist:causes))
                        }}
                    }}
                    UNION
                    {{
                        # Event → Person (involvesPerson)
                        ?event hist:involvesPerson {uri_sparql} .
                        ?event rdf:type hist:Event .

                        # 그 Event의 인과관계 찾기 (leadsTo, ledTo, causes 사용)
                        {{
                            ?event ?predicate ?related .
                            ?related rdfs:label ?label .
                            ?related rdf:type ?type .
                            FILTER(?predicate IN (hist:leadsTo, hist:ledTo, hist:causes))
                        }}
                        UNION
                        {{
                            ?related ?predicate ?event .
                            ?related rdfs:label ?label .
                            ?related rdf:type ?type .
                            FILTER(?predicate IN (hist:leadsTo, hist:ledTo, hist:causes))
                        }}
                    }}
                }} LIMIT 10
            """
        else:
            # Event 타입인 경우 직접 인과관계 검색 (leadsTo, ledTo, causes 사용)
            sparql = f"""
                PREFIX hist: <http://www.example.org/korean-history#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                SELECT DISTINCT ?related ?label ?type ?predicate WHERE {{
                    {{
                        # 나가는 인과관계: entity → related
                        {uri_sparql} ?predicate ?related .
                        ?related rdfs:label ?label .
                        ?related rdf:type ?type .
                        FILTER(?predicate IN (hist:leadsTo, hist:ledTo, hist:causes))
                    }}
                    UNION
                    {{
                        # 들어오는 인과관계: related → entity
                        ?related ?predicate {uri_sparql} .
                        ?related rdfs:label ?label .
                        ?related rdf:type ?type .
                        FILTER(?predicate IN (hist:leadsTo, hist:ledTo, hist:causes))
                    }}
                }} LIMIT 10
            """

        try:
            response = requests.post(
                f"{FUSEKI_URL}/sparql",
                data={"query": sparql},
                headers={"Accept": "application/sparql-results+json"},
                timeout=3
            )

            if response.status_code == 200:
                results = response.json()
                bindings = results.get("results", {}).get("bindings", [])
                print(f"  │  │  └─ SPARQL 결과: {len(bindings)}개 발견")

                for binding in bindings:
                    uri_related = binding.get("related", {}).get("value", "")
                    label = binding.get("label", {}).get("value", "")
                    entity_type = binding.get("type", {}).get("value", "").split("#")[-1]
                    predicate = binding.get("predicate", {}).get("value", "").split("#")[-1]

                    if uri_related not in seen and label:
                        seen.add(uri_related)
                        expanded_entities.append({
                            "type": entity_type,
                            "name": label,
                            "uri": uri_related,
                            "matched": True,
                            "expansion_method": "causal_chain",
                            "expansion_source": entity.get("name"),
                            "causal_relation": predicate,
                            "relevance_score": calculate_relevance_score(None, "causal_chain")  # 가중치 사용
                        })
            else:
                print(f"  │  │  └─ SPARQL 실패 (HTTP {response.status_code})")
        except Exception as e:
            print(f"  │  │  └─ 예외 발생 - {str(e)[:60]}")

    return expanded_entities


def expand_by_pgvector(entities: list, query: str, top_k: int = 15) -> list:
    """
    벡터 유사도 기반 확장 (pgvector)

    Args:
        entities: 추출된 엔티티 리스트
        query: 원본 질문 (맥락 제공)
        top_k: 최대 결과 수

    Returns:
        벡터 유사도가 높은 엔티티 리스트
    """

    pgvector = get_pgvector_service()
    if pgvector is None:
        return []

    expanded_entities = []
    seen = set()

    try:
        # TitleVectorService 초기화 (연결 확인)
        if not pgvector.conn:
            if not pgvector.connect():
                print("  │  └─ pgvector 연결 실패")
                return []

        # 1. 원본 질문으로 검색 (가장 관련성 높음)
        # TitleVectorService.search()는 [{"title": "...", "category": "...", "similarity": 0.95}] 형식 반환
        results = pgvector.search(query=query, top_k=top_k, threshold=0.5)

        for result in results:
            title = result.get("title", "")
            similarity = result.get("similarity", 0.0)
            if title and title not in seen:
                seen.add(title)
                # similarity는 이미 0-1 범위의 코사인 유사도 (1에 가까울수록 유사)

                expanded_entities.append({
                    "type": "Event",  # 기본값
                    "name": title,
                    "uri": None,  # pgvector에서는 URI 없음 (나중에 TTL 매칭)
                    "matched": False,
                    "expansion_method": "pgvector",
                    "expansion_source": "query",
                    "pgvector_similarity": similarity,
                    "relevance_score": calculate_relevance_score(similarity, "pgvector")  # 벡터 유사도 사용
                })

        # 2. 추출된 엔티티 이름으로도 검색
        for entity in entities[:5]:
            name = entity.get("name", "")
            if not name:
                continue

            results = pgvector.search(query=name, top_k=5, threshold=0.5)

            for result in results:
                title = result.get("title", "")
                similarity = result.get("similarity", 0.0)
                if title and title not in seen:
                    seen.add(title)

                    expanded_entities.append({
                        "type": "Event",
                        "name": title,
                        "uri": None,
                        "matched": False,
                        "expansion_method": "pgvector",
                        "expansion_source": name,
                        "pgvector_similarity": similarity,
                        "relevance_score": calculate_relevance_score(similarity, "pgvector")
                    })

    except Exception as e:
        print(f"  │  └─ pgvector 확장 실패: {e}")

    return expanded_entities


def semantic_expander_node(state: GraphState) -> GraphState:
    """
    의미론적 엔티티 확장 노드

    entity_expander 이후, parallel_knowledge_retrieval 이전에 실행.
    추출된 엔티티를 4가지 방법으로 확장:
    1. 시간적 맥락 (±10년)
    2. 카테고리/주제
    3. 인과관계 체인
    4. 벡터 유사도 (pgvector)
    """

    import time
    node_start = time.time()

    query = state.get("query", "")
    extracted_entities = state.get("extracted_entities", [])
    ttl_data = state.get("ttl_data", {})
    test_config = state.get("test_config")  # 테스트 설정

    print(f"\n{'='*70}")
    print(f"[2.5/6] 의미론적 확장 (Semantic Expander)")
    print(f"{'='*70}")
    print(f"  ├─ 입력 엔티티: {len(extracted_entities)}개")

    if not extracted_entities:
        print(f"  └─ 확장할 엔티티 없음 (skip)")
        return {**state}

    # 테스트 모드 확인
    if test_config and "semantic_expander" in test_config:
        semantic_config = test_config["semantic_expander"]
        print(f"  ├─ [테스트 모드] 활성화된 확장 방법:")
        for method, enabled in semantic_config.items():
            if enabled:
                print(f"  │  └─ {method}: ON")
    else:
        print(f"  ├─ [일반 모드] 모든 확장 방법 실행")
        semantic_config = None

    # 4가지 확장 방법 실행 (test_config에 따라 선택적 실행)
    temporal_expanded = []
    category_expanded = []
    causal_expanded = []
    pgvector_expanded = []

    if not semantic_config or semantic_config.get("temporal", True):
        temporal_expanded = expand_by_temporal_context(extracted_entities, ttl_data, window_years=10)

    if not semantic_config or semantic_config.get("category", True):
        category_expanded = expand_by_category(extracted_entities, ttl_data)

    if not semantic_config or semantic_config.get("causal_chain", True):
        causal_expanded = expand_by_causal_chain(extracted_entities, ttl_data, max_hops=3)

    if not semantic_config or semantic_config.get("pgvector", True):
        pgvector_expanded = expand_by_pgvector(extracted_entities, query, top_k=15)

    # 결과 병합 (중복 제거)
    all_expanded = []
    seen_uris = set()
    seen_names = set()

    # 원본 엔티티 먼저 추가 (우선순위 highest)
    for entity in extracted_entities:
        uri = entity.get("uri") or entity.get("name")
        if uri:
            seen_uris.add(uri)
            seen_names.add(entity.get("name", ""))
            all_expanded.append(entity)

    # 확장된 엔티티 추가 (관련도 순)
    for expanded_list in [causal_expanded, temporal_expanded, category_expanded, pgvector_expanded]:
        for entity in expanded_list:
            uri = entity.get("uri") or entity.get("name")
            name = entity.get("name", "")

            if uri not in seen_uris and name not in seen_names:
                seen_uris.add(uri)
                if name:
                    seen_names.add(name)
                all_expanded.append(entity)

    # TTL 매칭 (Milvus에서 온 엔티티는 URI 없음)
    label_to_uri = ttl_data.get("label_to_uri", {})
    uri_to_type = ttl_data.get("uri_to_type", {})

    for entity in all_expanded:
        if not entity.get("uri") and entity.get("name"):
            name = entity["name"]
            if name in label_to_uri:
                uri = label_to_uri[name]
                entity["uri"] = uri
                entity["matched"] = True
                entity["type"] = uri_to_type.get(uri, entity.get("type", "Event"))

    # SPARQL 기반 스코어링: 연결된 노드에 키워드가 있는지 확인
    # 질문에서 핵심 키워드 추출
    # 모든 데이터가 조선 데이터이므로 "조선" 관련 키워드는 제외
    joseon_keywords = {'조선', '조선시대', '조선왕조', '한국', '우리나라'}
    try:
        from kiwipiepy import Kiwi
        kiwi = Kiwi()
        tokens = kiwi.tokenize(query)
        core_keywords = [t.form for t in tokens if t.tag in ('NNG', 'NNP') and len(t.form) >= 2]
        # "조선" 관련 키워드 제거
        core_keywords = [kw for kw in core_keywords if kw not in joseon_keywords]
    except:
        import re
        core_keywords = re.findall(r'[가-힣]{2,}', query)
        # "조선" 관련 키워드 제거
        core_keywords = [kw for kw in core_keywords if kw not in joseon_keywords]
    
    print(f"  ├─ SPARQL 스코어링 시작 (키워드: {', '.join(core_keywords[:5])})")
    
    def calculate_sparql_score_with_connections(entity, keywords):
        """연결된 노드에 키워드가 있는지 SPARQL로 확인하여 점수 보정"""
        uri = entity.get("uri")
        if not uri or uri not in uri_to_type:
            return 0.0
        
        connected_score = 0.0
        has_keyword_match = False
        
        sparql_query = f"""
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            SELECT DISTINCT ?connectedLabel WHERE {{
                {{
                    <{uri}> ?p ?connected .
                    ?connected rdfs:label ?connectedLabel .
                    FILTER(?p != rdf:type)
                    FILTER(?p != rdfs:label)
                }}
                UNION
                {{
                    ?connected ?p <{uri}> .
                    ?connected rdfs:label ?connectedLabel .
                    FILTER(?p != rdf:type)
                    FILTER(?p != rdfs:label)
                }}
            }} LIMIT 50
        """
        
        try:
            response = requests.post(
                f"{FUSEKI_URL}/sparql",
                data={"query": sparql_query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=2
            )
            
            if response.status_code == 200:
                results = response.json()
                bindings = results.get("results", {}).get("bindings", [])
                
                for binding in bindings:
                    connected_label = binding.get("connectedLabel", {}).get("value", "")
                    if connected_label:
                        for kw in keywords:
                            if kw.lower() in connected_label.lower():
                                connected_score += 0.1
                                has_keyword_match = True
                                if connected_score >= 0.3:
                                    break
                        if connected_score >= 0.3:
                            break
        except:
            pass
        
        entity["has_keyword_in_connections"] = has_keyword_match
        return min(connected_score, 0.3)
    
    # 각 엔티티에 대해 SPARQL 스코어링 적용
    sparql_scored_count = 0
    for entity in all_expanded:
        if entity.get("uri"):
            bonus = calculate_sparql_score_with_connections(entity, core_keywords)
            if bonus > 0:
                # relevance_score에 bonus 추가
                current_score = entity.get("relevance_score", 0.0)
                entity["relevance_score"] = current_score + bonus
                sparql_scored_count += 1
    
    print(f"  │  └─ SPARQL 스코어링 완료: {sparql_scored_count}개 엔티티에 키워드 매칭 발견")

    # 상위 N개로 제한 (환경변수로 설정 가능, 기본값: 30)
    # 키워드가 연결된 노드에 있는 엔티티를 우선적으로 정렬
    all_expanded = sorted(
        all_expanded,
        key=lambda x: (
            not x.get("has_keyword_in_connections", False),  # 키워드 매칭 우선
            -x.get("relevance_score", 0.0)  # 점수 내림차순
        )
    )[:SEMANTIC_EXPANDER_TOP_N]

    # 통계 출력
    expansion_stats = {
        "temporal": len(temporal_expanded),
        "category": len(category_expanded),
        "causal": len(causal_expanded),
        "pgvector": len(pgvector_expanded)
    }

    print(f"  ├─ 확장 결과:")
    print(f"  │  ├─ 시간적 맥락: {expansion_stats['temporal']}개")
    print(f"  │  ├─ 카테고리: {expansion_stats['category']}개")
    print(f"  │  ├─ 인과관계: {expansion_stats['causal']}개")
    print(f"  │  └─ 벡터 유사도: {expansion_stats['pgvector']}개")

    # 상위 5개 샘플 출력
    if len(all_expanded) > len(extracted_entities):
        print(f"\n      [확장된 엔티티 샘플 (상위 5개)]")
        new_entities = [e for e in all_expanded if e.get("expansion_method")]
        for i, entity in enumerate(new_entities[:5], 1):
            name = entity.get("name", "")
            method = entity.get("expansion_method", "")
            source = entity.get("expansion_source", "")
            score = entity.get("relevance_score")

            method_display = {
                "temporal": "시간",
                "category": "카테고리",
                "causal_chain": "인과",
                "pgvector": "벡터"
            }.get(method, method)

            print(f"      {i}. [{method_display:6s}] {name[:40]} (출처: {source[:20]}, 점수: {score:.2f})")

    node_elapsed = time.time() - node_start
    print(f"  └─ 완료: {len(extracted_entities)}개 → {len(all_expanded)}개 (확장 +{len(all_expanded) - len(extracted_entities)}개) ({node_elapsed:.2f}초)")
    print()

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["semantic_expander"] = node_elapsed

    return {
        **state,
        "extracted_entities": all_expanded,
        "expansion_stats": expansion_stats,
        "executed_nodes": state.get("executed_nodes", []) + ["semantic_expander"],
        "node_execution_times": node_times
    }

