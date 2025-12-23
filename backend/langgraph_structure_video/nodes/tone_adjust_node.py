# Generate된 답변의 말투 교정하는 노드
from langgraph.graph import END
from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.utils import create_model
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

def tone_adjust_node(state: GraphState) -> GraphState:
    """
    말투 교정 노드
    """
    final_answer = state.get("final_answer", "")

    if not final_answer:
        raise ValueError("tone_adjust_node: 'final_answer' 값이 state에 없습니다.")
    
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

    return {
        **state,
        "tone_corrected_answer": tranformed_text,
    }


if __name__ == "__main__":
    # 예시 final_answer (한국어 한국사 설명 텍스트)
    final_answer = """
    위화도 회군은 1388년 고려 말, 이성계가 최영과 우왕의 명을 받아 요동 정벌에 나섰다가 위화도에서 군대를 돌려 개경으로 진격한 사건으로, 이후 권력 장악과 조선 건국으로 이어지는 결정적 계기가 되었습니다. 이 사건의 원인은 단일하지 않으며, 군사적 판단, 국제 정세 인식, 국내 정치 갈등, 그리고 개인적·정파적 이해관계가 복합적으로 작용한 결과로 이해됩니다. 당시 요동 지역은 명나라의 세력권 아래에 있었고, 원·명 교체기라는 국제 질서의 변화 속에서 고려가 요동을 공격할 경우 명과의 정면 충돌은 불가피했습니다. 이성계는 이러한 외교·군사적 현실을 인식하고, 국력에 비해 지나치게 무리한 원정이며 장기전으로 확대될 경우 막대한 인명 피해와 국가적 손실이 발생할 가능성이 크다고 판단한 것으로 해석됩니다. 국내 정치 상황 또한 회군 결정에 중요한 배경이 되었습니다. 최영과 우왕은 대외 강경 노선을 유지하며 요동 정벌을 추진했으나, 이는 친원적 정책 기조와도 맞닿아 있었습니다. 반면 이성계는 이러한 노선에 비판적이었고, 출병 명령 자체를 권력 투쟁의 연장선으로 인식했을 가능성이 큽니다. 요동 정벌은 단순한 대외 전쟁이 아니라, 고려 말 정치 권력의 향방을 둘러싼 갈등이 외부로 표출된 사건이기도 했습니다. 현실적인 군사 여건 역시 무시할 수 없는 요소였습니다. 장거리 원정에 따른 보급의 어려움, 병력의 피로 누적, 계절과 지형상의 불리함, 그리고 병사들의 낮은 사기와 귀향 의지는 회군을 정당화하는 실질적 이유로 작용했습니다. 일부 사료에서는 군 내부에서 원정에 대한 반발과 불만이 적지 않았음을 전하고 있습니다. 결과적으로 위화도 회군은 단순한 철군이 아니라, 이성계가 권력을 장악할 수 있는 결정적 기회가 되었습니다. 회군 직후 개경으로 진격한 이성계는 최영을 숙청하고 우왕을 폐위한 뒤 공양왕을 옹립하였으며, 이는 1392년 조선 건국으로 이어졌습니다. 따라서 이 사건에는 국가와 백성을 보호하려는 명분과 함께, 정치적 야심과 권력 재편을 향한 전략적 판단이 결합되어 있었다고 볼 수 있습니다. 역사적 평가는 관점에 따라 엇갈립니다. 조선왕조실록을 비롯한 조선 초기의 유교적 사관에서는 위화도 회군을 국가를 위기에서 구한 정당한 결단으로 서술하는 경향이 강한 반면, 다른 시각에서는 이를 군사 쿠데타이자 권력 찬탈로 비판하기도 합니다. 오늘날에는 어느 한 가지 이유로 단정하기보다는, 국제 정세, 국내 정치, 군사 현실, 개인적 선택이 복합적으로 작용한 역사적 전환점으로 이해하는 것이 일반적입니다.
    """

    # GraphState 형태로 감싸서 전달
    test_state: GraphState = {
        "final_answer": final_answer,
    }

    result_state = tone_adjust_node(test_state)
    print("\n=== Translated & Tone-adjusted Answer ===")
    print(result_state["tone_corrected_answer"])
