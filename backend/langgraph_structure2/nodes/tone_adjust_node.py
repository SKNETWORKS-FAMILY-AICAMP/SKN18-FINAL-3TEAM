# Generate된 답변의 말투 교정하는 노드
from langgraph.graph import END
from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.utils import create_model

def tone_adjust_node(state: GraphState) -> GraphState:
    """
    말투 교정 노드
    (현재는 단순히 final_answer 를 그대로 tone_corrected_answer 에 복사하는 더미 구현)
    """
    final_answer = state.get("final_answer", "")

    if not final_answer:
        raise ValueError("tone_adjust_node: 'final_answer' 값이 state에 없습니다.")

    # LLM 호출(모델 GPT-5-mini) -> 추후 파인튜닝 모델로 교체 예정
    TRANSLATE_TONE_PROMPT = f"""
    SYSTEM:
    You transform a Korean answer or explanation text into simple English for foreign audiences.
    The content is about Korean history, so the explanation must be easy, culturally clear, and friendly to readers who are not familiar with Korea.

    [RULES]
    1. Translate all sentences into simple English (B1–B2 level).
    2. Keep the original meaning, facts, and logical order. Do NOT add or remove content.
    3. Because the topic is Korean history, explain in a way that a foreign reader with no background knowledge can understand.
    4. For people, places, and historical events, output both the Romanized Korean and its English meaning.
        Example:
        - 세종대왕 → Sejong Daewang (King Sejong)
        - 조선 → Joseon (the Joseon Dynasty)
        - 한강 → Hangang (Han River)
    5. For any Korean text inside parentheses, translate it into natural English.
    - Example: (조용히 속삭이며) → (whispering quietly)
    6. Keep the tone: clear, friendly, and suitable for people learning about Korea for the first time.
    7. Do NOT format as scenes, narration, or dialogue yet. Just produce a coherent simple-English answer.
    8. Do NOT add explanations about your changes. Output only the transformed text.

    """.strip()

    # user 메시지: 번역 대상 텍스트를 [Answer] 블록으로 감싸서 전달
    user_content = f"""
    다음은 한국어로 된 '한국사'에 대한 답변입니다.
    위 시스템 지침과 [RULES]를 엄격히 따르면서, 이 답변을 변환해 주세요.

    [Answer]
    {final_answer}
    """.strip()

    client = create_model()
    MODEL_NAME = "gpt-5-mini"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_format={"type": "text"},
        messages=[
            {"role": "system", "content": TRANSLATE_TONE_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    tranformed_text = response.choices[0].message.content.strip()

    # 결과 터미널 출력
    print(f"[DEBUG] tone_adjust_node - Transformed Text:\n{tranformed_text}")
    print("-" * 60)

    return {
        **state,
        "tone_corrected_answer": tranformed_text,
    }

def route_tone_adjust_node(state: GraphState) -> str:
    """
    tone_adjust_node에서 라우팅하는 함수
    """

    tag = state.get("tag", "")
    if tag == "chat":
        return END
    elif tag == "video":
        return "scene_split_node"


if __name__ == "__main__":
    # 예시 final_answer (한국어 한국사 설명 텍스트)
    final_answer = """
    임진왜란은 1592년부터 1598년까지 일본이 조선을 침략하면서 벌어진 전쟁이다.
    이 전쟁의 주요 원인은 일본의 팽창주의와 조선 내부의 분열로 요약할 수 있다.
    일본의 대외적 팽창 의도와 함께 조선 사회의 내부 갈등이 맞물리며 외부 침략을 막아내기 어려운 상황을 만들었다는 점이 배경이 된다.
    전쟁은 일본의 침략으로 본격적으로 시작되어 조선은 국토 방어와 군사적 대응을 펼쳐야 했다.
    이 시기 조선 수군을 이끈 이순신 장군은 여러 차례 승리를 거두며 해상에서 중요한 역할을 수행했다.
    이순신의 지휘 아래 조선 수군은 적의 해상 세력을 제어하거나 격파하는 성과를 올렸고, 이는 전쟁의 전개에 중 요한 영향을 미쳤다.
    임진왜란은 여러 해에 걸쳐 지속되었고 전쟁 기간 동안 조선 사회와 군사에 큰 영향을 남겼다.
    특히 이순신과 같은 핵심 인물들의 군사적 업적은 전쟁사의 중요한 부분으로 남아 후대에 평가되었다.
    전반적으로 임진왜란은 외세의 침략과 내부 문제가 결합될 때 국가가 얼마나 취약해지는지를 보여준 사건으로, 역사적 교훈과 평가의 대상이 되고 있다.
    """

    # GraphState 형태로 감싸서 전달
    test_state: GraphState = {
        "final_answer": final_answer,
    }

    result_state = tone_adjust_node(test_state)
    print("\n=== Translated & Tone-adjusted Answer ===")
    print(result_state["tone_corrected_answer"])