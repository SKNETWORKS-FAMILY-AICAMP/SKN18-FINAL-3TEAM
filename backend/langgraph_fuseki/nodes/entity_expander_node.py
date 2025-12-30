"""
Entity Expander Node (Stage 2)

키워드 확장 + 엔티티 추출 통합:
1. 사용자 선택 방향 기반 키워드 확장 (LLM)
2. TTL 정확 매칭 (확장된 키워드 + 원본 키워드)
3. pgvector 유사도 검색 (fallback)
4. SPARQL 기반 엔티티 스코어링
5. 상위 30개 엔티티 선택
"""

import os
import json
import time
import re
from langchain_openai import ChatOpenAI

from backend.langgraph_fuseki.config import TTL_PATH, USE_PGVECTOR
from backend.langgraph_fuseki.state import GraphState
from backend.langgraph_fuseki.utils.fuseki_client import execute_sparql_query

# TTL 데이터 캐시
_ttl_cache = None
_ttl_cache_mtime = None

# pgvector 서비스 (lazy loading)
_title_vector_service = None


def get_title_vector_service():
    """제목 임베딩 pgvector 서비스 lazy loading"""
    global _title_vector_service
    if _title_vector_service is None and USE_PGVECTOR:
        try:
            from backend.db_pipeline.postgres.services.title_vector_service import TitleVectorService
            _title_vector_service = TitleVectorService()
            print("  pgvector 서비스 초기화 완료")
        except ImportError:
            print("  pgvector 서비스 import 실패 - TTL 매칭만 사용")
        except Exception as e:
            print(f"  pgvector 초기화 실패: {e}")
    return _title_vector_service


def load_ttl_entities() -> dict:
    """
    TTL 파일에서 모든 엔티티와 label 로드 (캐싱)
    
    Returns:
        {
            "label_to_uri": {"심기원역모사건": "hist:Event_심기원역모사건", ...},
            "uri_to_type": {"hist:Event_심기원역모사건": "Event", ...}
        }
    """
    global _ttl_cache, _ttl_cache_mtime
    
    # 캐시 유효성 검사
    if os.path.exists(TTL_PATH):
        current_mtime = os.path.getmtime(TTL_PATH)
        if _ttl_cache is not None and _ttl_cache_mtime == current_mtime:
            return _ttl_cache
    
    label_to_uri = {}
    uri_to_type = {}
    
    if not os.path.exists(TTL_PATH):
        print(f"  TTL 파일이 없습니다: {TTL_PATH}")
        return {"label_to_uri": {}, "uri_to_type": {}}
    
    try:
        start_time = time.time()
        with open(TTL_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 타입 추출: hist:Entity_Name rdf:type hist:Type .
        type_pattern = r'(hist:\w+_[^\s]+)\s+rdf:type\s+hist:(\w+)\s*\.'
        for match in re.finditer(type_pattern, content):
            uri = match.group(1)
            entity_type = match.group(2)
            uri_to_type[uri] = entity_type
        
        # 라벨 추출: hist:Entity_Name rdfs:label "Label" .
        label_pattern = r'(hist:\w+_[^\s]+)\s+rdfs:label\s+"([^"]+)"\s*\.'
        for match in re.finditer(label_pattern, content):
            uri = match.group(1)
            label = match.group(2)
            label_to_uri[label] = uri
            
            # 라벨 변형도 추가 (공백 제거, 괄호 내용 제거)
            clean_label = re.sub(r'\s+', '', label)
            if clean_label != label:
                label_to_uri[clean_label] = uri
            
            # 괄호 앞 부분만
            if '(' in label:
                base_label = label.split('(')[0].strip()
                if base_label:
                    label_to_uri[base_label] = uri
        
        load_time = time.time() - start_time
        print(f"  TTL 엔티티 로드 완료: {len(label_to_uri)}개 라벨, {len(uri_to_type)}개 타입 ({load_time:.2f}초)")
        
    except Exception as e:
        print(f"  TTL 파일 로드 실패: {e}")
    
    # 캐시 저장
    result = {"label_to_uri": label_to_uri, "uri_to_type": uri_to_type}
    _ttl_cache = result
    _ttl_cache_mtime = os.path.getmtime(TTL_PATH) if os.path.exists(TTL_PATH) else None
    
    return result


def expand_keywords_with_direction(query: str, basic_keywords: list, description: str, property_groups: list) -> dict:
    """
    사용자 선택 방향을 기반으로 키워드 확장
    
    Args:
        query: 원본 질문
        basic_keywords: 기본 키워드 (Stage 1에서 제공)
        description: 선택된 방향의 설명
        property_groups: 선택된 프로퍼티 그룹
    
    Returns:
        확장된 키워드 딕셔너리
    """
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0.3
    )
    
    keywords_text = ", ".join(basic_keywords)
    
    expansion_prompt = f"""당신은 역사 키워드를 확장하는 전문가입니다.

## 원본 질문
{query}

## 사용자가 선택한 답변 방향
**설명**: {description}
**관련 프로퍼티 그룹**: {', '.join(property_groups)}

## 추출된 기본 키워드
{keywords_text}

## 작업
사용자가 선택한 답변 방향을 고려하여, 기본 키워드와 관련된 구체적인 역사적 인스턴스를 확장하세요.

**확장 규칙:**
- 사용자가 선택한 방향의 설명과 프로퍼티 그룹을 중심으로 확장
- 기본 키워드 중 일반명사나 추상적 개념을 구체적인 인스턴스로 확장
- 선택된 방향과 관련성이 높은 인스턴스 우선 선택
- 최대 5-10개의 구체적 인스턴스로 확장
- **중요: "조선", "조선시대", "조선왕조"는 확장하지 마세요**

**키워드 확장 예시:**
- "궁궐" → ["경복궁", "창덕궁", "경덕궁", "창경궁"]
- "왕" → ["태조", "세종", "숙종", "영조"]
- "사건" → ["임진왜란", "정유재란", "갑자사화"]
- "제도" → ["의금부", "비변사", "경국대전"]

**중요:** 
- 선택된 방향과 관련 없는 키워드는 확장하지 마세요
- 확장할 키워드가 없으면 빈 객체를 출력하세요

## 출력 형식 (JSON만)
{{
  "expanded_keywords": {{"궁궐": ["경복궁", "창덕궁"], "왕": ["태조", "세종"]}}
}}

또는 확장 없는 경우:
{{
  "expanded_keywords": {{}}
}}
"""
    
    response = llm.invoke(expansion_prompt)
    content = response.content.strip()
    
    # JSON 파싱
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    
    return json.loads(content)


def select_property_groups_with_llm(query: str, keywords: list, available_groups: list) -> list:
    """
    LLM을 사용하여 질문과 키워드에 적합한 프로퍼티 그룹 선택
    
    Args:
        query: 원본 질문
        keywords: 추출된 키워드
        available_groups: 선택 가능한 프로퍼티 그룹 목록
    
    Returns:
        선택된 프로퍼티 그룹 리스트 (3-5개)
    """
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0.3
    )
    
    keywords_text = ", ".join(keywords) if keywords else "없음"
    groups_text = ", ".join(available_groups)
    
    selection_prompt = f"""당신은 역사 지식 그래프 전문가입니다.

## 질문
{query}

## 추출된 키워드
{keywords_text}

## 사용 가능한 프로퍼티 그룹
{groups_text}

## 작업
위 질문과 키워드에 가장 적합한 프로퍼티 그룹 3-5개를 선택하세요.

**선택 기준:**
- 질문의 핵심 의도와 관련된 그룹을 우선 선택
- 키워드와 직접적으로 연결된 그룹 선택
- 질문 유형에 따른 선택:
  - "왜/이유/원인" → 인과관계, 외교, 통치
  - "누구/인물" → 직위, 참여, 소속
  - "언제/시기" → 연도, 시기, 기간중
  - "어떻게/과정" → 시행, 참여, 법률
  - "결과/영향" → 변경, 인과관계, 법률

## 출력 형식 (JSON만)
{{
  "selected_groups": ["그룹1", "그룹2", "그룹3"]
}}
"""
    
    response = llm.invoke(selection_prompt)
    content = response.content.strip()
    
    # JSON 파싱
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    
    result = json.loads(content)
    selected = result.get("selected_groups", [])
    
    # 유효한 그룹만 필터링
    valid_groups = [g for g in selected if g in available_groups]
    
    if not valid_groups:
        # 기본 그룹 반환
        valid_groups = ["속성", "인과관계", "참여", "변경"]
        print(f"  ⚠️ LLM 선택 그룹이 없어 기본값 사용: {valid_groups}")
    
    return valid_groups


def search_entities_with_pgvector(keywords: list, ttl_data: dict, top_k: int = 5) -> list:
    """
    pgvector 제목 임베딩 유사도 검색으로 엔티티 찾기 (fallback)
    """
    title_vector_service = get_title_vector_service()
    if title_vector_service is None:
        return []

    entities = []
    seen_titles = set()

    try:
        # TitleVectorService 연결 확인
        if not title_vector_service.conn:
            if not title_vector_service.connect():
                print("  pgvector 연결 실패")
                return []

        # 키워드로 벡터 검색
        query_text = " ".join(keywords)
        results = title_vector_service.search(query=query_text, top_k=top_k, threshold=0.5)

        for result in results:
            title = result["title"]
            if title in seen_titles:
                continue
            seen_titles.add(title)

            # TTL에서 URI 찾기
            uri = ttl_data["label_to_uri"].get(title)
            entity_type = "Event"

            if uri:
                entity_type = ttl_data["uri_to_type"].get(uri, "Event")
            else:
                # category로 타입 추정
                category = result.get("category", "")
                type_map = {
                    "인물": "Person",
                    "사건": "Event",
                    "제도": "Institution",
                    "문헌": "Document",
                    "전투": "Battle",
                    "장소": "Place",
                    "물품": "Object"
                }
                entity_type = type_map.get(category, "Event")

            entities.append({
                "type": entity_type,
                "name": title,
                "uri": uri,
                "matched": uri is not None,
                "pgvector_score": result["similarity"],
                "matched_keyword": query_text
            })

        # 점수 순 정렬
        entities.sort(key=lambda x: x.get("pgvector_score", 0), reverse=True)

    except Exception as e:
        print(f"  pgvector 검색 실패: {e}")

    return entities


def calculate_entity_score_with_connections(entity, keywords, ttl_data):
    """
    엔티티와 키워드의 연관성 점수 계산 (SPARQL 기반)
    """
    # 기본 점수
    match_method = entity.get("match_method", "exact")
    base_score = {
        "exact": 1.0,
        "partial": 0.7,
        "pgvector": entity.get("pgvector_score", 0.5),
        "llm": 0.3
    }.get(match_method, 0.5)

    # 이름에 키워드 포함 점수
    name = entity.get("name", "").lower()
    name_match_score = sum(0.5 for kw in keywords if kw.lower() in name)

    # 연결된 노드에 키워드 포함 점수 (SPARQL 기반)
    connected_score = 0.0
    uri = entity.get("uri")

    if uri and uri in ttl_data.get("uri_to_type", {}):
        # URI 형식 변환
        full_uri = uri.replace("hist:", "http://www.example.org/korean-history#")
        
        sparql_query = f"""
            PREFIX hist: <http://www.example.org/korean-history#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            SELECT DISTINCT ?connectedLabel WHERE {{
                {{
                    <{full_uri}> ?p ?connected .
                    ?connected rdfs:label ?connectedLabel .
                    FILTER(?p != rdf:type)
                    FILTER(?p != rdfs:label)
                }}
                UNION
                {{
                    ?connected ?p <{full_uri}> .
                    ?connected rdfs:label ?connectedLabel .
                    FILTER(?p != rdf:type)
                    FILTER(?p != rdfs:label)
                }}
            }} LIMIT 50
        """

        try:
            fuseki_url = os.getenv("FUSEKI_URL", "http://localhost:3030/korean-history")
            results = execute_sparql_query(fuseki_url, sparql_query, timeout=5)
            
            if results:
                bindings = results.get("results", {}).get("bindings", [])
                
                # 연결된 엔티티의 label에 키워드가 있는지 확인
                for binding in bindings:
                    connected_label = binding.get("connectedLabel", {}).get("value", "")
                    if connected_label:
                        for kw in keywords:
                            if kw.lower() in connected_label.lower():
                                connected_score += 0.1
                                if connected_score >= 0.3:  # 최대값
                                    break
                        if connected_score >= 0.3:
                            break

        except Exception as e:
            print(f"    SPARQL 예외: {entity.get('name')} - {str(e)}")

    total_score = base_score + name_match_score + min(connected_score, 0.3)
    entity["relevance_score"] = total_score
    return total_score


def entity_expander_node(state: GraphState) -> GraphState:
    """
    Stage 2: Entity Expander - 키워드 확장 + 엔티티 추출 통합
    
    작업:
    1. 사용자 선택 방향 기반 키워드 확장 (LLM)
    2. TTL 정확 매칭
    3. pgvector 유사도 검색 (fallback)
    4. SPARQL 기반 엔티티 스코어링
    5. 상위 30개 엔티티 선택
    """
    node_start = time.time()
    
    query = state.get("query", "")
    user_selected_direction = state.get("user_selected_direction")
    expansion_directions = state.get("expansion_directions", [])
    basic_keywords = state.get("basic_keywords", [])
    thinking_callback = state.get("thinking_callback")
    
    print(f"\n{'='*70}")
    print(f"[Stage 2] Entity Expander (키워드 확장 + 엔티티 추출)")
    print(f"{'='*70}")
    print(f"  질문: '{query}'")
    print(f"  선택된 방향: {user_selected_direction}")
    print(f"  ★ basic_keywords 수: {len(basic_keywords)}개")
    print(f"  ★ basic_keywords 내용: {basic_keywords}")
    print(f"  ★ expansion_directions 수: {len(expansion_directions)}개")
    
    if not query:
        print(f"  ERROR: query가 비어있습니다!")
        return state
    
    if not basic_keywords:
        print(f"  ⚠️ WARNING: basic_keywords가 비어있습니다! 세션 복원 확인 필요")
    

    # 🎯 Thinking 이벤트: Entity Expander 시작
    if thinking_callback:
        thinking_callback("entity_expansion_started", {
            "title": "엔티티 확장 시작",
            "stage": "Stage 2: Entity Expander",
            "basic_keywords": basic_keywords,
            "selected_direction": user_selected_direction
        })
    
    # ========== 1. 사용자 선택 방향 정보 조회 ==========
    selected_direction_info = None
    if user_selected_direction and expansion_directions:
        for direction in expansion_directions:
            if direction.get("direction_id") == user_selected_direction:
                selected_direction_info = direction
                break
        
        if not selected_direction_info:
            print(f"  ⚠️ 경고: direction_id '{user_selected_direction}'를 expansion_directions에서 찾을 수 없음")
            print(f"  expansion_directions 수: {len(expansion_directions)}")
    
    expanded_keywords = basic_keywords.copy()
    expanded_keywords_dict = {}
    selected_property_groups = []
    selected_properties = []
    
    # ========== 2. LLM 키워드 확장 (항상 실행) ==========
    if basic_keywords:
        # 방향 정보에서 description과 property_groups 가져오기
        if selected_direction_info:
            description = selected_direction_info.get("description", "")
            property_groups = selected_direction_info.get("property_groups", [])
            
            print(f"  ★ 선택된 방향 정보 발견!")
            print(f"  선택된 방향: {selected_direction_info.get('title', '')}")
            print(f"  설명: {description}")
            print(f"  프로퍼티 그룹: {property_groups}")
        else:
            # 방향 정보 없으면 기본값 사용
            description = "역사적 맥락에서 관련 키워드 확장"
            property_groups = []
            print(f"  ⚠️ 선택된 방향 정보 없음, 기본 맥락으로 확장")
            print(f"  기본 키워드: {basic_keywords}")

        # 🎯 Thinking 이벤트: 키워드 확장 시작
        if thinking_callback:
            thinking_callback("keyword_expansion_started", {
                "title": "LLM 키워드 확장 시작",
                "direction_title": selected_direction_info.get('title', '역사적 맥락') if selected_direction_info else "역사적 맥락",
                "direction_description": description,
                "property_groups": property_groups,
                "basic_keywords": basic_keywords
            })
        
        # ★ LLM 키워드 확장 (항상 실행)
        try:
            print(f"  ★ LLM 키워드 확장 시작...")
            expanded_result = expand_keywords_with_direction(
                query, basic_keywords, description, property_groups
            )
            expanded_keywords_dict = expanded_result.get("expanded_keywords", {})
            
            # 확장된 키워드를 기본 키워드에 추가
            for keyword, instances in expanded_keywords_dict.items():
                expanded_keywords.extend(instances)
            
            # 중복 제거
            expanded_keywords = list(set(expanded_keywords))
            
            print(f"  ★ LLM 확장된 키워드: {len(expanded_keywords)}개")
            print(f"  확장 매핑: {expanded_keywords_dict}")

            # 🎯 Thinking 이벤트: 키워드 확장 완료
            if thinking_callback:
                thinking_callback("keyword_expansion_completed", {
                    "title": "LLM 키워드 확장 완료",
                    "expanded_keywords": expanded_keywords,
                    "expansion_mapping": expanded_keywords_dict,
                    "total_keywords": len(expanded_keywords)
                })
            
        except Exception as e:
            print(f"  ⚠️ LLM 키워드 확장 실패: {e}")
            import traceback
            traceback.print_exc()
        
        # ========== 3. 프로퍼티 그룹 선택 (항상 실행) ==========
        from backend.langgraph_fuseki.nodes.classify_node import load_property_groups
        all_groups = load_property_groups()
        
        if property_groups:
            # 방향 정보에서 프로퍼티 그룹 사용
            for group_name in property_groups:
                if group_name in all_groups:
                    selected_properties.extend(all_groups[group_name])
            
            selected_property_groups = property_groups
            print(f"  ★ 방향 기반 프로퍼티 그룹: {property_groups}")
        else:
            # ★ 방향 정보 없으면 LLM으로 프로퍼티 그룹 선택
            print(f"  ★ LLM 기반 프로퍼티 그룹 선택 시작...")
            try:
                selected_property_groups = select_property_groups_with_llm(
                    query, basic_keywords, list(all_groups.keys())
                )
                
                for group_name in selected_property_groups:
                    if group_name in all_groups:
                        selected_properties.extend(all_groups[group_name])
                
                print(f"  ★ LLM 선택 프로퍼티 그룹: {selected_property_groups}")
            except Exception as e:
                print(f"  ⚠️ LLM 프로퍼티 그룹 선택 실패: {e}, 기본 그룹 사용")
                # 기본 그룹 사용
                selected_property_groups = ["속성", "인과관계", "참여", "변경"]
                for group_name in selected_property_groups:
                    if group_name in all_groups:
                        selected_properties.extend(all_groups[group_name])
        
        selected_properties = list(set(selected_properties))
        print(f"  ★ 선택된 프로퍼티: {len(selected_properties)}개")
    
    else:
        print(f"  ⚠️ basic_keywords가 비어있어 키워드 확장 및 프로퍼티 선택 불가")

    # 🎯 Thinking 이벤트: TTL 매칭 시작
    if thinking_callback:
        thinking_callback("ttl_matching_started", {
            "title": "TTL 데이터 매칭 시작",
            "keywords_to_match": expanded_keywords,
            "matching_methods": ["정확 매칭", "부분 매칭"]
        })
    
    # ========== 2. TTL 데이터 로드 및 엔티티 매칭 ==========
    ttl_data = load_ttl_entities()
    
    # 모든 키워드로 엔티티 매칭
    all_keywords = expanded_keywords
    matched_entities = []
    seen_uris = set()
    
    # TTL 정확 매칭
    ttl_matched = 0
    for keyword in all_keywords:
        # 정확한 라벨 매칭
        if keyword in ttl_data.get("label_to_uri", {}):
            uri = ttl_data["label_to_uri"][keyword]
            if uri not in seen_uris:
                seen_uris.add(uri)
                entity_type = ttl_data["uri_to_type"].get(uri, "Event")
                matched_entities.append({
                    "uri": uri,
                    "name": keyword,
                    "type": entity_type,
                    "match_method": "exact",
                    "relevance_score": 1.0
                })
                ttl_matched += 1
        
        # 부분 매칭 (최대 3개)
        if len(keyword) >= 3:
            partial_count = 0
            for label, uri in ttl_data.get("label_to_uri", {}).items():
                if keyword in label and uri not in seen_uris:
                    seen_uris.add(uri)
                    entity_type = ttl_data["uri_to_type"].get(uri, "Event")
                    matched_entities.append({
                        "uri": uri,
                        "name": label,
                        "type": entity_type,
                        "match_method": "partial",
                        "relevance_score": 0.7,
                        "matched_keyword": keyword
                    })
                    ttl_matched += 1
                    partial_count += 1
                    if partial_count >= 3:
                        break
    
    print(f"  TTL 매칭 결과: {ttl_matched}개")

    # 🎯 Thinking 이벤트: TTL 매칭 완료
    if thinking_callback:
        thinking_callback("ttl_matching_completed", {
            "title": "TTL 매칭 완료",
            "matched_entities": ttl_matched,
            "exact_matches": len([e for e in matched_entities if e.get("match_method") == "exact"]),
            "partial_matches": len([e for e in matched_entities if e.get("match_method") == "partial"])
        })
    
    # ========== 3. pgvector 유사도 검색 (fallback) ==========
    pgvector_added = 0
    if len(matched_entities) < 20 and USE_PGVECTOR:
        # 🎯 Thinking 이벤트: pgvector 검색 시작
        if thinking_callback:
            thinking_callback("pgvector_search_started", {
                "title": "pgvector 유사도 검색 시작",
                "reason": f"TTL 매칭 결과 부족 ({len(matched_entities)}개 < 20개)",
                "search_keywords": expanded_keywords
            })

        try:
            vector_results = search_entities_with_pgvector(
                expanded_keywords, ttl_data, top_k=15
            )
            
            for result in vector_results:
                uri = result.get("uri")
                if uri and uri not in seen_uris:
                    seen_uris.add(uri)
                    result["match_method"] = "pgvector"
                    matched_entities.append(result)
                    pgvector_added += 1
            
            print(f"  pgvector 추가 결과: {pgvector_added}개")

            # 🎯 Thinking 이벤트: pgvector 검색 완료
            if thinking_callback:
                thinking_callback("pgvector_search_completed", {
                    "title": "pgvector 검색 완료",
                    "added_entities": pgvector_added,
                    "total_entities": len(matched_entities)
                })

        except Exception as e:
            print(f"  pgvector 검색 실패: {e}")
    
    # ========== 4. SPARQL 기반 엔티티 스코어링 ==========
    print(f"  SPARQL 기반 스코어링 중...")

    # 🎯 Thinking 이벤트: SPARQL 스코어링 시작
    if thinking_callback:
        thinking_callback("sparql_scoring_started", {
            "title": "SPARQL 기반 스코어링 시작",
            "entities_to_score": len(matched_entities),
            "scoring_factors": ["기본 점수", "이름 매칭", "연결 노드 매칭"]
        })
    
    for entity in matched_entities:
        try:
            score = calculate_entity_score_with_connections(
                entity, all_keywords, ttl_data
            )
            entity["final_score"] = score
        except Exception as e:
            entity["final_score"] = entity.get("relevance_score", 0.5)
    
    # ========== 5. 상위 30개 엔티티 선택 ==========
    matched_entities.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    top_entities = matched_entities[:30]
    
    print(f"  최종 선택된 엔티티: {len(top_entities)}개")
    
    # 상위 10개 엔티티 출력
    if top_entities:
        print(f"  상위 엔티티:")
        for i, entity in enumerate(top_entities[:10], 1):
            name = entity.get("name", "")
            entity_type = entity.get("type", "Unknown")
            method = entity.get("match_method", "")
            score = entity.get("final_score", 0)
            print(f"    {i:2d}. [{method:7s}] [{entity_type:12s}] {name} (점수: {score:.2f})")

    # 🎯 Thinking 이벤트: Entity Expander 완료
    if thinking_callback:
        top_entity_names = [e.get("name", "") for e in top_entities[:10]]
        thinking_callback("entity_expansion_completed", {
            "title": "엔티티 확장 완료",
            "final_entity_count": len(top_entities),
            "top_entities": top_entity_names,
            "processing_summary": {
                "ttl_matches": ttl_matched,
                "pgvector_additions": pgvector_added,
                "final_selection": len(top_entities)
            }
        })
    
    # 실행 시간 계산
    node_end = time.time()
    execution_time = node_end - node_start
    node_times = state.get("node_execution_times", {})
    node_times["entity_expander"] = execution_time
    
    print(f"  실행 시간: {execution_time:.2f}초")
    
    return {
        **state,
        "expanded_keywords": expanded_keywords,
        "expanded_keywords_dict": expanded_keywords_dict,
        "selected_property_groups": selected_property_groups,
        "selected_properties": selected_properties,
        "extracted_entities": top_entities,
        "ttl_data": ttl_data,
        "executed_nodes": state.get("executed_nodes", []) + ["entity_expander"],
        "node_execution_times": node_times
    }