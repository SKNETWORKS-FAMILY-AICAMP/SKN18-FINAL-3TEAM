"""
Entity Extractor Node

질문에서 핵심 엔티티 추출:
- 인물: 이순신, 원균, 도요토미 등
- 사건: 임진왜란, 명량해전, 가덕도해전 등
- 연도: 1592, 1597 등
- 장소: 한산도, 부산 등

+ 추출된 엔티티 타입에 맞는 온톨로지 스키마 정보 제공
"""

import os
import sys
from pathlib import Path
from langchain_openai import ChatOpenAI

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from state import GraphState
from ontology_schema import get_schema_summary


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

        print(f"\n🔍 추출된 엔티티: {len(entities)}개")
        for i, entity in enumerate(entities, 1):
            name = entity.get("name") or entity.get("value", "")
            entity_type = entity.get("type", "")
            print(f"   {i}. [{entity_type}] {name}")

    except Exception as e:
        print(f"⚠️ 엔티티 추출 실패: {e}")
        entities = []

    # 온톨로지 스키마 정보 가져오기
    ontology_schema = get_schema_summary()

    print(f"\n📐 온톨로지 스키마:")
    print(f"   - 클래스: {', '.join(ontology_schema['classes'])}")

    # 추출된 엔티티 타입에 해당하는 속성만 출력
    entity_types = list(set([e.get("type", "") for e in entities if e.get("type")]))
    if entity_types:
        print(f"   - 추출된 타입의 속성:")
        for entity_type in entity_types:
            props = ontology_schema["properties_by_class"].get(entity_type, [])
            if props:
                print(f"     • {entity_type}: {len(props)}개 ({', '.join(props[:3])}...)")

    return {
        **state,
        "extracted_entities": entities,
        "ontology_schema": ontology_schema,
        "executed_nodes": state.get("executed_nodes", []) + ["entity_extractor"]
    }
