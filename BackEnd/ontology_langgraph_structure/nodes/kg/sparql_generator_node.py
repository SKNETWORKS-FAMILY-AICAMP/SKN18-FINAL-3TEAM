"""
SPARQL Generator Node

LLM을 사용하여 자연어 질문을 SPARQL 쿼리로 변환
- 온톨로지 스키마 참조
- 엔티티 URI 매핑
"""

import os
import sys
from pathlib import Path
from langchain_openai import ChatOpenAI

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from state import GraphState


# 온톨로지 스키마 예시 (실제로는 OWL 파일에서 로드)
ONTOLOGY_SCHEMA = """
# 조선시대 역사 온톨로지 스키마

## 클래스 (Classes)
- hist:Person (인물)
- hist:Event (사건)
- hist:Nation (국가)
- hist:Place (장소)

## 프로퍼티 (Properties)
- hist:leadsTo (이어진다) - 인과관계
- hist:causedBy (원인)
- hist:indirectlyCausedBy (간접 원인) - 추론으로 생성
- hist:participatedIn (참여)
- hist:year (연도)
- hist:outcome (결과)
- hist:relatedTo (관련)

## 네임스페이스
PREFIX hist: <http://www.example.org/korean-history#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

SPARQL_EXAMPLES = """
# SPARQL 예시

## 예시 1: 특정 인물이 참여한 사건
SELECT ?event ?year WHERE {
  hist:YiSunSin hist:participatedIn ?event .
  ?event hist:year ?year .
}

## 예시 2: 인과관계 체인
SELECT ?cause ?effect WHERE {
  ?cause hist:leadsTo ?effect .
}

## 예시 3: 간접 원인 (추론 결과)
SELECT ?root ?final WHERE {
  ?final hist:indirectlyCausedBy ?root .
}
"""


def sparql_generator_node(state: GraphState) -> GraphState:
    """자연어 → SPARQL 변환"""

    query = state.get("query", "")
    entities = state.get("extracted_entities", [])
    query_type = state.get("query_type", "causal")

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0
    )

    # 엔티티 정보 포맷팅
    entity_info = "\n".join([
        f"- {e['type']}: {e.get('name', e.get('value', ''))}"
        for e in entities
    ])

    sparql_prompt = f"""당신은 SPARQL 쿼리 생성 전문가입니다.

다음 정보를 바탕으로 SPARQL 쿼리를 작성하세요:

{ONTOLOGY_SCHEMA}

{SPARQL_EXAMPLES}

질문: {query}
질문 유형: {query_type}
추출된 엔티티:
{entity_info or "없음"}

요구사항:
1. 추출된 엔티티를 hist: 네임스페이스의 URI로 변환
   예: "이순신" → hist:YiSunSin, "명량해전" → hist:Myeongnyang
2. 질문 유형에 맞는 쿼리 작성:
   - causal: hist:leadsTo, hist:indirectlyCausedBy 사용
   - deep_analysis: 여러 관계 조합
3. 결과는 ?subject ?predicate ?object 형태로 반환
4. LIMIT는 100으로 설정

반드시 유효한 SPARQL 쿼리만 출력하세요. 설명은 제외하세요.
"""

    try:
        response = llm.invoke(sparql_prompt)
        sparql_query = response.content.strip()

        # 코드 블록 제거
        if "```sparql" in sparql_query:
            sparql_query = sparql_query.split("```sparql")[1].split("```")[0].strip()
        elif "```" in sparql_query:
            sparql_query = sparql_query.split("```")[1].split("```")[0].strip()

        print(f"🔍 생성된 SPARQL:\n{sparql_query}")

    except Exception as e:
        print(f"⚠️ SPARQL 생성 실패: {e}")
        # 기본 쿼리
        sparql_query = """
PREFIX hist: <http://www.example.org/korean-history#>
SELECT ?s ?p ?o WHERE {
    ?s ?p ?o
} LIMIT 100
"""

    return {
        **state,
        "sparql_query": sparql_query,
        "executed_nodes": state.get("executed_nodes", []) + ["sparql_generator"]
    }
