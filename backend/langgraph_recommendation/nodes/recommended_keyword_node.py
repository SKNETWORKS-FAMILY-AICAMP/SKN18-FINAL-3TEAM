"""
Recommend Keyword Generation Node

video_title과 video_keywords를 기반으로 추천 키워드 생성:
1. LLM 의도파악 (자동)
2. LLM 키워드 확장
3. TTL 엔티티 추출
4. Thread 병렬 실행 (outgoing/incoming/connected_entities)
5. 상위 3-4개 엔티티를 LLM이 선택
"""

import os
import json
import re
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.langgraph_recommendation.state import RecommendationState
from backend.langgraph_fuseki.utils.fuseki_client import execute_sparql_query

# TTL 캐시 (video_keyword_node와 공유)
_ttl_cache = None
_ttl_cache_mtime = None


def load_ttl_entities() -> dict:
    """TTL 엔티티 로드 (video_keyword_node와 동일)"""
    global _ttl_cache, _ttl_cache_mtime
    from backend.langgraph_fuseki.config import TTL_PATH

    if os.path.exists(TTL_PATH):
        current_mtime = os.path.getmtime(TTL_PATH)
        if _ttl_cache is not None and _ttl_cache_mtime == current_mtime:
            return _ttl_cache

    label_to_uri = {}
    uri_to_type = {}

    if not os.path.exists(TTL_PATH):
        return {"label_to_uri": {}, "uri_to_type": {}}

    try:
        with open(TTL_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        type_pattern = r'(hist:\w+_[^\s]+)\s+rdf:type\s+hist:(\w+)\s*\.'
        for match in re.finditer(type_pattern, content):
            uri_to_type[match.group(1)] = match.group(2)

        label_pattern = r'(hist:\w+_[^\s]+)\s+rdfs:label\s+"([^"]+)"\s*\.'
        for match in re.finditer(label_pattern, content):
            uri, label = match.group(1), match.group(2)
            label_to_uri[label] = uri
            clean_label = re.sub(r'\s+', '', label)
            if clean_label != label:
                label_to_uri[clean_label] = uri
            if '(' in label:
                base_label = label.split('(')[0].strip()
                if base_label:
                    label_to_uri[base_label] = uri

    except Exception as e:
        print(f"⚠️ TTL 파일 로드 실패: {e}")

    result = {"label_to_uri": label_to_uri, "uri_to_type": uri_to_type}
    _ttl_cache = result
    _ttl_cache_mtime = os.path.getmtime(TTL_PATH) if os.path.exists(TTL_PATH) else None
    return result


def analyze_intent_with_llm(user_query: str, video_title: str, basic_keywords: List[str]) -> str:
    """
    LLM으로 사용자 쿼리 + 영상 제목(답변)의 의도 파악
    - 사용자의 질문 의도와 답변의 의도를 종합 분석
    """
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0.3
    )

    keywords_text = ", ".join(basic_keywords) if basic_keywords else "없음"

    prompt = f"""당신은 역사 콘텐츠 분석 전문가입니다.

사용자 질문: "{user_query}"
영상 제목 (답변): "{video_title}"
추출된 키워드: {keywords_text}

위 질문과 답변을 종합하여 사용자의 학습 의도를 한 문장으로 파악하세요.

분석 기준:
- 사용자가 무엇을 알고 싶어 하는가? (질문 의도)
- 답변이 다루는 핵심 내용은 무엇인가? (답변 의도)
- 두 가지를 종합한 학습 목표는?

예시:
- 질문: "대동법이 시행된 배경은?" + 답변: "광해군의 재정 개혁" → "조선 중기 세금 제도 개혁 배경 이해"
- 질문: "경복궁을 지은 왕" + 답변: "태조 이성계" → "조선 건국과 궁궐 건설 과정 탐색"
- 질문: "임진왜란의 원인" + 답변: "일본의 대륙 진출 야심" → "16세기 동아시아 국제 정세와 전쟁 배경 분석"

JSON 형식으로만 응답:
{{"intent": "의도 문장"}}
"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        # JSON 파싱
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)
        intent = result.get("intent", "역사적 맥락 탐색")
        return intent

    except Exception as e:
        print(f"⚠️ LLM 의도파악 실패: {e}, 기본값 사용")
        return "역사적 맥락 탐색"


def expand_keywords_with_llm(user_query: str, video_title: str, intent: str, basic_keywords: List[str]) -> List[str]:
    """
    LLM으로 키워드 확장
    fuseki의 entity_expander_node 로직 간소화
    """
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0.3
    )

    keywords_text = ", ".join(basic_keywords) if basic_keywords else "없음"

    prompt = f"""당신은 역사 키워드 확장 전문가입니다.

사용자 질문: "{user_query}"
영상 제목 (답변): "{video_title}"
파악된 의도: {intent}
기본 키워드: {keywords_text}

위 의도를 고려하여, 기본 키워드와 관련된 구체적인 역사적 인스턴스를 확장하세요.

확장 규칙:
- 의도와 관련성이 높은 인스턴스 우선
- 일반명사를 구체적인 고유명사로 확장
- 최대 5-10개
- "조선", "조선시대", "조선왕조"는 확장하지 마세요

예시:
- "궁궐" → ["경복궁", "창덕궁", "창경궁"]
- "왕" → ["태조", "세종", "영조"]

JSON 형식으로만 응답:
{{"expanded_keywords": ["키워드1", "키워드2", ...]}}
"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)
        expanded = result.get("expanded_keywords", [])

        # 기본 키워드와 확장 키워드 합치기
        all_keywords = list(set(basic_keywords + expanded))
        return all_keywords

    except Exception as e:
        print(f"⚠️ LLM 키워드 확장 실패: {e}, 기본 키워드 사용")
        return basic_keywords


def extract_entities_from_ttl(keywords: List[str], ttl_data: dict) -> List[Dict[str, Any]]:
    """
    TTL에서 키워드 매칭하여 엔티티 추출
    """
    matched_entities = []
    seen_uris = set()

    for keyword in keywords:
        # 정확한 라벨 매칭
        if keyword in ttl_data.get("label_to_uri", {}):
            uri = ttl_data["label_to_uri"][keyword]
            if uri not in seen_uris:
                seen_uris.add(uri)
                entity_type = ttl_data["uri_to_type"].get(uri, "Unknown")
                matched_entities.append({
                    "uri": uri,
                    "name": keyword,
                    "type": entity_type,
                    "match_method": "exact"
                })

        # 부분 매칭 (최대 2개)
        if len(keyword) >= 3:
            partial_count = 0
            for label, uri in ttl_data.get("label_to_uri", {}).items():
                if keyword in label and uri not in seen_uris:
                    seen_uris.add(uri)
                    entity_type = ttl_data["uri_to_type"].get(uri, "Unknown")
                    matched_entities.append({
                        "uri": uri,
                        "name": label,
                        "type": entity_type,
                        "match_method": "partial"
                    })
                    partial_count += 1
                    if partial_count >= 2:
                        break

    return matched_entities


def fetch_outgoing_relations(entity_uri: str) -> List[Dict[str, Any]]:
    """Thread 1: 나가는 관계 조회"""
    fuseki_url = os.getenv("FUSEKI_URL", "http://localhost:3030/korean-history")
    full_uri = entity_uri.replace("hist:", "http://www.example.org/korean-history#")

    query = f"""
        PREFIX hist: <http://www.example.org/korean-history#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?predicate ?object ?objectLabel WHERE {{
            <{full_uri}> ?predicate ?object .
            OPTIONAL {{ ?object rdfs:label ?objectLabel }}
            FILTER(?predicate != rdfs:label)
            FILTER(?predicate != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
        }} LIMIT 20
    """

    try:
        results = execute_sparql_query(fuseki_url, query, timeout=10)
        bindings = results.get("results", {}).get("bindings", [])
        return bindings
    except Exception as e:
        print(f"    ⚠️ outgoing_relations 실패: {e}")
        return []


def fetch_incoming_relations(entity_uri: str) -> List[Dict[str, Any]]:
    """Thread 2: 들어오는 관계 조회"""
    fuseki_url = os.getenv("FUSEKI_URL", "http://localhost:3030/korean-history")
    full_uri = entity_uri.replace("hist:", "http://www.example.org/korean-history#")

    query = f"""
        PREFIX hist: <http://www.example.org/korean-history#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?subject ?subjectLabel ?predicate WHERE {{
            ?subject ?predicate <{full_uri}> .
            OPTIONAL {{ ?subject rdfs:label ?subjectLabel }}
            FILTER(?predicate != rdfs:label)
            FILTER(?predicate != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
        }} LIMIT 20
    """

    try:
        results = execute_sparql_query(fuseki_url, query, timeout=10)
        bindings = results.get("results", {}).get("bindings", [])
        return bindings
    except Exception as e:
        print(f"    ⚠️ incoming_relations 실패: {e}")
        return []


def fetch_connected_entities(entity_uri: str) -> List[Dict[str, Any]]:
    """Thread 3: 연결된 엔티티 조회 (양방향)"""
    fuseki_url = os.getenv("FUSEKI_URL", "http://localhost:3030/korean-history")
    full_uri = entity_uri.replace("hist:", "http://www.example.org/korean-history#")

    query = f"""
        PREFIX hist: <http://www.example.org/korean-history#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?connected ?connectedLabel WHERE {{
            {{
                <{full_uri}> ?p ?connected .
                FILTER(?p != rdfs:label)
                FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
            }}
            UNION
            {{
                ?connected ?p <{full_uri}> .
                FILTER(?p != rdfs:label)
                FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
            }}
            OPTIONAL {{ ?connected rdfs:label ?connectedLabel }}
        }} LIMIT 30
    """

    try:
        results = execute_sparql_query(fuseki_url, query, timeout=10)
        bindings = results.get("results", {}).get("bindings", [])
        return bindings
    except Exception as e:
        print(f"    ⚠️ connected_entities 실패: {e}")
        return []


def run_threads_parallel(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Thread 병렬 실행
    각 엔티티에 대해 3가지 Thread 실행
    """
    thread_results = {
        "outgoing_relations": [],
        "incoming_relations": [],
        "connected_entities": []
    }

    # 최대 5개 엔티티만 처리 (성능 최적화)
    top_entities = entities[:5]

    print(f"  Thread 병렬 실행 시작 ({len(top_entities)}개 엔티티)...")

    with ThreadPoolExecutor(max_workers=15) as executor:  # 5개 엔티티 * 3개 Thread = 15
        futures = {}

        for entity in top_entities:
            entity_uri = entity.get("uri")
            if not entity_uri:
                continue

            # 3가지 Thread 제출
            future1 = executor.submit(fetch_outgoing_relations, entity_uri)
            future2 = executor.submit(fetch_incoming_relations, entity_uri)
            future3 = executor.submit(fetch_connected_entities, entity_uri)

            futures[future1] = ("outgoing", entity["name"])
            futures[future2] = ("incoming", entity["name"])
            futures[future3] = ("connected", entity["name"])

        # 결과 수집
        for future in as_completed(futures):
            thread_type, entity_name = futures[future]
            try:
                result = future.result(timeout=15)
                if thread_type == "outgoing":
                    thread_results["outgoing_relations"].extend(result)
                elif thread_type == "incoming":
                    thread_results["incoming_relations"].extend(result)
                elif thread_type == "connected":
                    thread_results["connected_entities"].extend(result)
                print(f"    ✓ {thread_type} for '{entity_name}': {len(result)}개")
            except Exception as e:
                print(f"    ⚠️ {thread_type} for '{entity_name}' 실패: {e}")

    print(f"  Thread 결과:")
    print(f"    - outgoing_relations: {len(thread_results['outgoing_relations'])}개")
    print(f"    - incoming_relations: {len(thread_results['incoming_relations'])}개")
    print(f"    - connected_entities: {len(thread_results['connected_entities'])}개")

    return thread_results


def select_top_recommendations_with_llm(
    user_query: str,
    video_title: str,
    intent: str,
    thread_results: Dict[str, Any],
    ttl_data: dict
) -> List[str]:
    """
    LLM이 Thread 결과에서 상위 3-4개 추천 키워드 선택
    """
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0.3
    )

    # Thread 결과에서 연결된 엔티티 label 추출
    candidate_labels = set()

    # outgoing/incoming에서 추출
    for binding in thread_results.get("outgoing_relations", []):
        label = binding.get("objectLabel", {}).get("value")
        if label:
            candidate_labels.add(label)

    for binding in thread_results.get("incoming_relations", []):
        label = binding.get("subjectLabel", {}).get("value")
        if label:
            candidate_labels.add(label)

    # connected_entities에서 추출
    for binding in thread_results.get("connected_entities", []):
        label = binding.get("connectedLabel", {}).get("value")
        if label:
            candidate_labels.add(label)

    # TTL에 실제 존재하는 엔티티만 필터링
    valid_candidates = [label for label in candidate_labels if label in ttl_data.get("label_to_uri", {})]

    if not valid_candidates:
        print(f"  ⚠️ 추천 후보가 없습니다.")
        return []

    candidates_text = ", ".join(list(valid_candidates)[:30])  # 최대 30개

    prompt = f"""당신은 역사 콘텐츠 추천 전문가입니다.

사용자 질문: "{user_query}"
영상 제목 (답변): "{video_title}"
파악된 의도: {intent}

연결된 엔티티 후보들:
{candidates_text}

**중요: 위 후보 목록에서만 선택해야 합니다. 새로운 엔티티를 만들지 마세요.**

위 후보 중에서 영상 시청자에게 추천할 만한 **관련도가 높은** 엔티티를 **정확히 3-4개** 선택하세요.

선택 기준:
- 영상 제목 및 의도와의 관련성
- 역사적 중요도
- 다양성 (인물, 사건, 장소 등 균형)

**주의사항:**
- 후보 목록에 없는 엔티티는 절대 선택하지 마세요
- 후보 목록의 엔티티 이름을 정확히 그대로 사용하세요

JSON 형식으로만 응답:
{{"recommendations": ["엔티티1", "엔티티2", "엔티티3"]}}
"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)
        recommendations = result.get("recommendations", [])

        # 1차 필터링: valid_candidates에 있는 것만
        filtered_recommendations = [r for r in recommendations if r in valid_candidates]

        # 2차 필터링: TTL에도 실제로 존재하는지 재확인 (안전장치)
        final_recommendations = [r for r in filtered_recommendations if r in ttl_data.get("label_to_uri", {})]

        # LLM이 후보 목록 외 엔티티를 선택한 경우 경고
        invalid_selections = set(recommendations) - set(valid_candidates)
        if invalid_selections:
            print(f"    ⚠️ LLM이 후보 목록에 없는 엔티티를 선택함 (제거됨): {invalid_selections}")

        return final_recommendations[:4]  # 최대 4개

    except Exception as e:
        print(f"⚠️ LLM 추천 선택 실패: {e}, 상위 3개 사용")
        return list(valid_candidates)[:3]


def recommended_keyword_node(state: RecommendationState) -> RecommendationState:
    """
    Stage 2: 추천 키워드 생성

    작업:
    1. LLM 의도파악 (쿼리 + 제목)
    2. LLM 키워드 확장
    3. TTL 엔티티 추출
    4. Thread 병렬 실행 (outgoing/incoming/connected)
    5. LLM이 상위 3-4개 선택
    """
    print(f"\n{'='*70}")
    print(f"[Stage 2] Recommend Keyword Generation")
    print(f"{'='*70}")

    user_query = state.get("user_query", "")
    video_title = state.get("video_title", "")
    basic_keywords = state.get("basic_keywords", [])

    print(f"  사용자 쿼리: '{user_query}'")
    print(f"  영상 제목: '{video_title}'")
    print(f"  기본 키워드: {basic_keywords}")

    if not basic_keywords:
        print(f"  ⚠️ basic_keywords가 비어있어 추천 생성 불가")
        return {
            **state,
            "recommended_keywords": "",
            "errors": state.get("errors", []) + ["basic_keywords 없음"],
            "executed_nodes": state.get("executed_nodes", []) + ["recommended_keyword_generation"]
        }

    # 1. 의도파악 (쿼리 + 제목)
    print(f"  1. LLM 의도파악 (쿼리 + 제목)...")
    intent = analyze_intent_with_llm(user_query, video_title, basic_keywords)
    print(f"    의도: {intent}")

    # 2. 키워드 확장
    print(f"  2. LLM 키워드 확장...")
    expanded_keywords = expand_keywords_with_llm(user_query, video_title, intent, basic_keywords)
    print(f"    확장 키워드: {expanded_keywords} ({len(expanded_keywords)}개)")

    # 3. TTL 엔티티 추출
    print(f"  3. TTL 엔티티 추출...")
    ttl_data = load_ttl_entities()
    extracted_entities = extract_entities_from_ttl(expanded_keywords, ttl_data)
    print(f"    추출된 엔티티: {len(extracted_entities)}개")

    if not extracted_entities:
        print(f"  ⚠️ TTL 엔티티 추출 실패")
        return {
            **state,
            "intent": intent,
            "expanded_keywords": expanded_keywords,
            "recommended_keywords": "",
            "errors": state.get("errors", []) + ["TTL 엔티티 없음"],
            "executed_nodes": state.get("executed_nodes", []) + ["recommended_keyword_generation"]
        }

    # 4. Thread 병렬 실행
    print(f"  4. Thread 병렬 실행...")
    thread_results = run_threads_parallel(extracted_entities)

    # 5. LLM이 상위 3-4개 선택
    print(f"  5. LLM 추천 키워드 선택...")
    final_recommendations = select_top_recommendations_with_llm(
        user_query, video_title, intent, thread_results, ttl_data
    )
    print(f"    최종 추천: {final_recommendations}")

    # 6. TTL 재검증 (안전장치)
    print(f"  6. TTL 최종 검증...")
    verified_recommendations = [
        keyword for keyword in final_recommendations
        if keyword in ttl_data.get("label_to_uri", {})
    ]

    if len(verified_recommendations) < len(final_recommendations):
        removed = set(final_recommendations) - set(verified_recommendations)
        print(f"    ⚠️ TTL에 없어서 제거된 키워드: {removed}")

    print(f"    검증된 추천: {verified_recommendations}")

    # 7. 콤마 구분 문자열로 변환
    recommended_keywords_str = ",".join(verified_recommendations) if verified_recommendations else ""

    return {
        **state,
        "intent": intent,
        "expanded_keywords": expanded_keywords,
        "extracted_entities": extracted_entities,
        "thread_results": thread_results,
        "final_recommendations": verified_recommendations,  # 검증된 것만 저장
        "recommended_keywords": recommended_keywords_str,
        "executed_nodes": state.get("executed_nodes", []) + ["recommended_keyword_generation"]
    }
