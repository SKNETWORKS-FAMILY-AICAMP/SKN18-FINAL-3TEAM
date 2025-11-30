"""
Hypothetical Triple Generator Node

What-if 질문을 분석하여 가상 트리플 생성
예: "만약 원균이 승리했다면?" → "hist:Wongyun hist:wonBattle hist:GadeokdoSea ."
"""

import os
import sys
from pathlib import Path
from langchain_openai import ChatOpenAI

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from state import GraphState


TRIPLE_EXAMPLES = """
# Turtle 형식 Triple 예시

## 예시 1: 전투 결과 변경
hist:Wongyun hist:wonBattle hist:GadeokdoSea .
hist:GadeokdoSea hist:outcome "victory" .

## 예시 2: 인물 사망
hist:YiSunSin hist:died hist:EarlyDeath .
hist:EarlyDeath hist:year 1592 .

## 예시 3: 관계 변경
hist:JoseonNavy hist:defeated hist:JapaneseNavy .
hist:ImjinWar hist:outcome "early_end" .
"""


def hypothetical_triple_node(state: GraphState) -> GraphState:
    """What-if 질문 → 가상 트리플 생성"""

    query = state.get("query", "")
    entities = state.get("extracted_entities", [])

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.3  # What-if는 약간의 창의성 허용
    )

    # 엔티티 정보
    entity_info = "\n".join([
        f"- {e['type']}: {e.get('name', e.get('value', ''))}"
        for e in entities
    ])

    triple_prompt = f"""당신은 가상 시나리오를 Turtle 형식 Triple로 변환하는 전문가입니다.

{TRIPLE_EXAMPLES}

What-if 질문: {query}
추출된 엔티티:
{entity_info or "없음"}

가상 시나리오를 나타내는 Turtle Triple을 생성하세요.

규칙:
1. hist: 네임스페이스 사용
2. 엔티티 이름은 PascalCase로 변환 (이순신 → YiSunSin)
3. 각 줄은 완전한 Triple (주어 술어 목적어 .)
4. 2-5개의 Triple 생성
5. 설명 없이 Triple만 출력

출력 예시:
hist:Wongyun hist:wonBattle hist:GadeokdoSea .
hist:GadeokdoSea hist:outcome "victory" .
"""

    try:
        response = llm.invoke(triple_prompt)
        content = response.content.strip()

        # 코드 블록 제거
        if "```turtle" in content:
            content = content.split("```turtle")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # 각 줄을 리스트로 분할
        triples = [line.strip() for line in content.split("\n") if line.strip() and not line.startswith("#")]

        print(f"🔮 생성된 가상 트리플:")
        for t in triples:
            print(f"   {t}")

    except Exception as e:
        print(f"⚠️ 가상 트리플 생성 실패: {e}")
        triples = []

    return {
        **state,
        "hypothetical_triples": triples,
        "executed_nodes": state.get("executed_nodes", []) + ["hypothetical_triple_node"]
    }
