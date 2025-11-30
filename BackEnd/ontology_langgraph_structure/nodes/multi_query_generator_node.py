"""
Multi-Query Generator Node

LLM 기반 5가지 관점의 SPARQL 쿼리 생성 + Thread 가중치 설정

5-Stage Analysis Plan:
- Stage 1: 비하인드 스토리 (motive_inference.rules + person_inference.rules)
- Stage 2: 역사 시뮬레이터 (causal_inference.rules)
- Stage 3: 인물 분석 (person_inference.rules)
- Stage 4: 시대적 배경 분석 (temporal_inference.rules)
- Stage 5: 심화 분석 (pattern_inference.rules)
"""

import os
import sys
from pathlib import Path

# 환경변수 로드
sys.path.insert(0, str(Path(__file__).parent.parent))
import __init__  # 환경변수 및 LangSmith 설정 로드

from state import GraphState
from langchain_openai import ChatOpenAI
from ontology_schema import get_schema_summary


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

# Stage별 추론 프로퍼티 매핑 (ontology_schema.py와 동기화)
INFERENCE_PROPERTIES_BY_STAGE = {
    "causal": {
        "description": "Stage 2: 역사 시뮬레이터 (인과관계 추론)",
        "properties": [
            "hist:leadsTo",              # 직접 인과
            "hist:causedBy",             # 원인
            "hist:hasImpact",            # 영향
            "hist:hasOutcome",           # 결과
            "hist:indirectlyCausedBy",   # [추론] 간접 인과 (2-3단계)
            "hist:hasStatus",            # [추론] 국가 상태
            "hist:hasStrategicAdvantage",# [추론] 전략적 우위
            "hist:strategicImportance",  # [추론] 전략적 중요도
            "hist:relatedToPolicy"       # 제도-정책 연계
        ]
    },
    "person": {
        "description": "Stage 1, 3: 비하인드 스토리 + 인물 분석",
        "properties": [
            "hist:commands",                # 지휘
            "hist:participatesIn",          # 참여
            "hist:affiliatedWith",          # 소속
            "hist:hasRole",                 # 역할
            "hist:hasAchievement",          # 업적
            "hist:initiatedBy",             # 정책 시행 (역방향)
            "hist:establishedBy",           # 제도 설립 (역방향)
            "hist:hasRelationshipWith",     # [추론] 동료 관계
            "hist:hasEnemyRelationship",    # [추론] 적대 관계
            "hist:hasLocalTies",            # [추론] 지역 연고
            "hist:hasInfluence",            # [추론] 영향력
            "hist:hasLoyalty"               # [추론] 충성도
        ]
    },
    "temporal": {
        "description": "Stage 4: 시대적 배경 분석",
        "properties": [
            "hist:hasYear",              # 연도
            "hist:hasDate",              # 날짜
            "hist:hasBirthYear",         # 출생년도
            "hist:hasDeathYear",         # 사망년도
            "hist:occursBefore",         # [추론] 시간 순서
            "hist:occursAfter",          # [추론] 시간 순서
            "hist:contemporaryWith",     # [추론] 동시대 인물
            "hist:simultaneousWith",     # [추론] 동시 사건 (Policy-Event 동시성)
            "hist:hasLifespan",          # [추론] 수명
            "hist:hasDuration",          # [추론] 지속 기간 (전쟁, 제도)
            "hist:belongsToPeriod"       # [추론] 역사적 시대 (세종대왕 시기 등)
        ]
    },
    "pattern": {
        "description": "Stage 5: 심화 분석 (전략 패턴)",
        "properties": [
            "hist:occursAt",             # 발생 장소
            "hist:hasVictor",            # 승자
            "hist:hasDefeated",          # 패자
            "hist:hasStrategyPattern",   # [추론] 전략 패턴
            "hist:hasWinningStreak",     # [추론] 연승 패턴
            "hist:hasComebackPattern",   # [추론] 역전 패턴
            "hist:hasContestedStatus",   # [추론] 경합 지역
            "hist:hasCommandPattern"     # [추론] 지휘 교체 패턴
        ]
    },
    "motive": {
        "description": "Stage 1: 비하인드 스토리 (동기 분석)",
        "properties": [
            "hist:commands",             # 지휘한 전투
            "hist:bornIn",              # 출생지
            "hist:affiliatedWith",       # 소속 국가
            "hist:initiatedBy",         # 정책을 시작한 인물
            "hist:establishedBy",       # 제도를 설립한 인물
            "hist:hasObjective",        # 정책 목표
            "hist:hasPurpose",          # 제도 목적
            "hist:hasMotive",           # [추론] 동기 (revenge, national_defense, national_development, cultural_promotion 등)
            "hist:hasLocalTies"         # [추론] 지역 연고
        ]
    }
}


def multi_query_generator_node(state: GraphState) -> GraphState:
    """LLM 기반 5가지 관점의 SPARQL 쿼리 생성 + Thread 가중치 설정"""

    query = state.get("query", "")
    query_type = state.get("query_type", "causal")
    entities = state.get("extracted_entities", [])

    print(f"📝 LLM 기반 다중 쿼리 생성 중... (유형: {query_type})")

    # 1. Thread 가중치 설정
    thread_weights = THREAD_WEIGHTS.get(query_type, THREAD_WEIGHTS["causal"])

    print(f"   - Thread 가중치:")
    for thread, weight in sorted(thread_weights.items(), key=lambda x: -x[1]):
        print(f"     • {thread}: {weight:.0%}")

    # 2. LLM 초기화
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0
    )

    # 3. 각 Stage별로 LLM이 SPARQL 생성
    multi_queries = {}

    for thread_type, weight in thread_weights.items():
        if thread_type in INFERENCE_PROPERTIES_BY_STAGE:
            try:
                sparql = generate_sparql_with_llm(
                    llm=llm,
                    query=query,
                    query_type=query_type,
                    thread_type=thread_type,
                    entities=entities,
                    properties=INFERENCE_PROPERTIES_BY_STAGE[thread_type]["properties"],
                    description=INFERENCE_PROPERTIES_BY_STAGE[thread_type]["description"]
                )
                multi_queries[thread_type] = sparql
                print(f"   ✅ {thread_type} 쿼리 생성 완료")
            except Exception as e:
                print(f"   ❌ {thread_type} 쿼리 생성 실패: {e}")
                # 기본 쿼리 사용
                multi_queries[thread_type] = generate_fallback_sparql(thread_type, entities)

    print(f"✅ 총 {len(multi_queries)}개 쿼리 생성")

    return {
        **state,
        "multi_queries": multi_queries,
        "thread_weights": thread_weights,
        "executed_nodes": state.get("executed_nodes", []) + ["multi_query_generator"]
    }


def generate_sparql_with_llm(
    llm: ChatOpenAI,
    query: str,
    query_type: str,
    thread_type: str,
    entities: list,
    properties: list,
    description: str
) -> str:
    """
    LLM을 사용하여 특정 Stage에 맞는 SPARQL 쿼리 생성

    Args:
        llm: ChatOpenAI 인스턴스
        query: 사용자 질문
        query_type: 질문 유형 (causal/what_if/deep_analysis)
        thread_type: Thread 타입 (causal/person/temporal/pattern/motive)
        entities: 추출된 엔티티 목록
        properties: 사용 가능한 프로퍼티 목록
        description: Stage 설명

    Returns:
        SPARQL 쿼리 문자열
    """

    # 엔티티 정보 포맷팅
    entity_info = "\n".join([
        f"- {e.get('type', 'Unknown')}: {e.get('name', e.get('value', 'N/A'))}"
        for e in entities
    ]) if entities else "없음"

    # 프로퍼티 목록 포맷팅
    properties_info = "\n".join([f"  - {prop}" for prop in properties])

    sparql_prompt = f"""당신은 한국 역사 온톨로지 SPARQL 쿼리 생성 전문가입니다.

**분석 단계:** {description}

**사용자 질문:** {query}
**질문 유형:** {query_type}

**추출된 엔티티:**
{entity_info}

**사용 가능한 프로퍼티:**
{properties_info}

**네임스페이스:**
PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

**요구사항:**
1. 위 프로퍼티만 사용하여 SPARQL SELECT 쿼리 작성
2. 추출된 엔티티를 hist: 네임스페이스 URI로 변환
   예: "이순신" → hist:YiSunSin, "명량해전" → hist:Myeongnyang
3. [추론] 표시가 있는 프로퍼티는 추론 결과로 생성된 것
4. 질문에 맞는 변수를 SELECT하고, 관련 패턴을 WHERE절에 작성
5. OPTIONAL 절을 사용하여 일부 데이터가 없어도 결과 반환
6. LIMIT 100 설정
7. 반드시 유효한 SPARQL 쿼리만 출력 (설명 제외)

**출력 예시:**
PREFIX hist: <http://www.example.org/korean-history#>
SELECT ?person ?battle ?motive WHERE {{
    ?person hist:commands ?battle .
    ?person hist:hasMotive ?motive .
    OPTIONAL {{ ?person hist:affiliatedWith ?nation }}
}} LIMIT 100
"""

    response = llm.invoke(sparql_prompt)
    sparql_query = response.content.strip()

    # 코드 블록 제거
    if "```sparql" in sparql_query:
        sparql_query = sparql_query.split("```sparql")[1].split("```")[0].strip()
    elif "```" in sparql_query:
        sparql_query = sparql_query.split("```")[1].split("```")[0].strip()

    return sparql_query


def generate_fallback_sparql(thread_type: str, entities: list) -> str:
    """
    LLM 실패 시 기본 SPARQL 쿼리 반환

    Args:
        thread_type: Thread 타입
        entities: 추출된 엔티티 목록

    Returns:
        기본 SPARQL 쿼리
    """

    # 엔티티 URI 추출
    entity_uris = [e.get("uri") for e in entities if e.get("uri")]
    entity_filter = ""

    if entity_uris:
        filters = [f"?s = hist:{uri.split(':')[-1]}" for uri in entity_uris[:2]]
        entity_filter = f"FILTER ({' || '.join(filters)})"

    fallback_templates = {
        "causal": f"""PREFIX hist: <http://www.example.org/korean-history#>
SELECT ?cause ?effect WHERE {{
    ?cause hist:leadsTo ?effect .
    {entity_filter}
}} LIMIT 100""",

        "person": f"""PREFIX hist: <http://www.example.org/korean-history#>
SELECT ?person ?event ?role WHERE {{
    ?person hist:participatesIn ?event .
    OPTIONAL {{ ?person hist:hasRole ?role }}
    {entity_filter}
}} LIMIT 100""",

        "temporal": f"""PREFIX hist: <http://www.example.org/korean-history#>
SELECT ?event ?year WHERE {{
    ?event hist:hasYear ?year .
    {entity_filter}
}} LIMIT 100""",

        "pattern": f"""PREFIX hist: <http://www.example.org/korean-history#>
SELECT ?person ?pattern WHERE {{
    ?person hist:hasStrategyPattern ?pattern .
    {entity_filter}
}} LIMIT 100""",

        "motive": f"""PREFIX hist: <http://www.example.org/korean-history#>
SELECT ?person ?motive WHERE {{
    ?person hist:hasMotive ?motive .
    {entity_filter}
}} LIMIT 100"""
    }

    return fallback_templates.get(thread_type, f"""PREFIX hist: <http://www.example.org/korean-history#>
SELECT ?s ?p ?o WHERE {{
    ?s ?p ?o .
    {entity_filter}
}} LIMIT 100""")


def generate_entity_filter(entities: list) -> str:
    """엔티티 기반 FILTER 조건 생성"""

    if not entities:
        return ""

    # URI 추출
    uris = [e.get("uri") for e in entities if e.get("uri")]

    if not uris:
        return ""

    # FILTER 조건 생성
    filter_parts = []
    for uri in uris[:3]:  # 최대 3개만
        filter_parts.append(f"?cause = <{uri}> || ?effect = <{uri}> || ?event = <{uri}> || ?person = <{uri}>")

    if filter_parts:
        return f"FILTER ({' || '.join(filter_parts)})"

    return ""
