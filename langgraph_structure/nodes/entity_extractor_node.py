"""
Entity Extractor Node

질문에서 핵심 엔티티 추출:
- 인물: 이순신, 원균, 도요토미 등
- 사건: 임진왜란, 명량해전, 가덕도해전 등
- 연도: 1592, 1597 등
- 장소: 한산도, 부산 등
"""

import os
from langgraph_structure.state import GraphState
from langchain_openai import ChatOpenAI


def entity_extractor_node(state: GraphState) -> GraphState:
    """질문에서 핵심 엔티티 추출"""

    query = state.get("query", "")

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0
    )

    extraction_prompt = f"""당신은 조선시대 역사 데이터에서 엔티티를 추출하는 전문가입니다.

다음 질문에서 핵심 엔티티를 추출하세요:
- 인물 (Person): 이순신, 원균, 도요토미 등
- 사건 (Event): 임진왜란, 명량해전, 정유재란 등
- 연도 (Year): 1592, 1597 등
- 장소 (Place): 한산도, 부산 등
- 국가 (Nation): 조선, 일본, 명나라 등

질문: {query}

출력 형식 (JSON):
[
  {{"type": "Person", "name": "이순신"}},
  {{"type": "Event", "name": "명량해전"}},
  {{"type": "Year", "value": "1597"}}
]

엔티티가 없으면 빈 배열 []을 반환하세요.
반드시 유효한 JSON만 출력하세요.
"""

    try:
        response = llm.invoke(extraction_prompt)
        content = response.content.strip()

        # JSON 파싱
        import json
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()

        entities = json.loads(content)

        print(f"🔍 추출된 엔티티: {entities}")

    except Exception as e:
        print(f"⚠️ 엔티티 추출 실패: {e}")
        entities = []

    return {
        **state,
        "extracted_entities": entities,
        "executed_nodes": state.get("executed_nodes", []) + ["entity_extractor"]
    }
