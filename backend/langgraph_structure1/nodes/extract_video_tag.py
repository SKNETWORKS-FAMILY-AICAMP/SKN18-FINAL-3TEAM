# video scene script에서 tag 추출
# 적어도 2-3개의 tag를 추출
# 정의된 tag 내에서 추출

from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.utils import create_model
import json

def extract_video_tag(state: GraphState) -> GraphState:

    SCRIPT_JSON_STR = state.get("tone_corrected_answer")

    SYSTEM_PROMPT = """
    당신은 스토리텔링 JSON 스크립트에서 추천용 태그를 추출하는 분류기입니다.
    입력은 단 하나의 JSON 객체이며, title/scenes/image_prompt/location/sequences 안의 텍스트를 근거로 태그를 선택합니다.

    [목표]
    - 아래 '허용 태그 목록'에서만 선택하여, 추천을 위한 태그를 2~3개 뽑습니다.
    - 태그는 '스크립트의 핵심 소재/주제'를 대표해야 합니다.
    - 애매하면 1개만 출력해도 됩니다.

    [허용 태그 목록 — 이 외 출력 금지]
    - 전쟁
    - 정치
    - 왕실
    - 사회
    - 문화
    - 과학기술
    - 예술
    - 신분제
    - 군사제도
    - 인물
    - 경제
    - 행정
    - 법과 형벌
    - 의례
    - 문헌·기록

    [판단 기준]
    - image_prompt + Talk.text + action_tag를 모두 고려합니다.
    - 스크립트의 '주된 갈등/오해/설명 대상'이 무엇인지 우선합니다.
    - 특정 인물의 성장/전기/업적이 중심이 아니면 '인물' 태그는 사용하지 않습니다.
    - 현대 기술/도구/기계/과학 개념이 핵심이면 '과학기술'을 우선합니다.
    - 조선 시대 풍속/생활/가치관 대비가 핵심이면 '문화' 또는 '사회'를 선택합니다.
    - 법 집행/처벌/재판이 핵심이면 '법과 형벌'을 선택합니다.
    - 공식 행사/제례/의식이 핵심이면 '의례'를 선택합니다.
    - 군사 조직/군역 제도가 핵심이면 '군사제도'를 선택합니다. 전투/전쟁 경과면 '전쟁'입니다.
    - 권력 다툼/정치적 결정이 핵심이면 '정치'입니다. 왕족 개인사 중심이면 '왕실'입니다.

    [출력 형식 — 반드시 JSON만 출력]
    {
    "tags": ["태그1", "태그2", "태그3"],
    "evidence": {
        "태그1": ["근거 키워드/구절(짧게)", "..."],
        "태그2": ["..."],
        "태그3": ["..."]
    }
    }

    [제약]
    - tags 배열은 1~3개
    - evidence는 각 태그당 1~3개 짧은 근거만
    - 설명 문장, 추가 텍스트, 마크다운 금지
    """

    client = create_model()
    MODEL_NAME = "gpt-5-mini"

    USER_PROMPT_TEMPLATE = """
    아래 JSON 스크립트에서 추천용 태그 1~3개를 추출하세요.

    JSON:
    {script_json}
    """

    user_content = USER_PROMPT_TEMPLATE.format(script_json=SCRIPT_JSON_STR)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    result_text = response.choices[0].message.content.strip()

    # tags만 추출해서 db에 저장
    return {
        **state,
        "video_tags": result_text,
    }


if __name__ == "__main__":
    dummy_state : GraphState={
        "tone_corrected_answer": json.dumps(
            {
                "title": "The Imjin War",
                "scenes": [
                    {
                        "scene_id": 1,
                        "location": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                        "sequences": [
                            {"order": 1, "actor": "Minseok", "type": "Camera", "action_tag": "Full", "target_position": "Camera", "duration": 0.1, "is_parallel": False},
                            {"order": 2, "actor": "Minseok", "type": "Talk", "text": "The Imjin War was a conflict that took place from 1592 to 1598, when Japan invaded Joseon.", "duration": 4.5, "is_parallel": False},
                            {"order": 3, "actor": "Minji", "type": "Talk", "text": "So it wasn’t just a sudden attack, right? There must have been deeper reasons behind it.", "duration": 4.0, "is_parallel": False},
                            {"order": 4, "actor": "Minseok", "type": "Talk", "text": "Exactly. Japan’s expansionist ambitions collided with internal political and social divisions within Joseon.", "duration": 5.5, "is_parallel": False},
                            {"order": 5, "actor": "Minji", "type": "Talk", "text": "Those internal divisions weakened Joseon’s ability to defend itself, didn’t they?", "duration": 4.5, "is_parallel": False},
                            {"order": 6, "actor": "Minseok", "type": "Talk", "text": "Yes. Combined with external pressure from Japan, they are considered the fundamental causes of the war.", "duration": 5.5, "is_parallel": False},
                            {"order": 7, "actor": "Minseok", "type": "Camera", "action_tag": "SlowPan", "target_position": "Sea", "duration": 0.1, "is_parallel": False},
                            {"order": 8, "actor": "Minji", "type": "Talk", "text": "I’ve heard that the Joseon navy played a crucial role during the war.", "duration": 4.0, "is_parallel": False},
                            {"order": 9, "actor": "Minseok", "type": "Talk", "text": "That’s right. Admiral Yi Sun-sin led the Joseon naval forces and achieved numerous victories at sea.", "duration": 5.5, "is_parallel": False},
                            {"order": 10, "actor": "Minji", "type": "Talk", "text": "Those naval victories really changed the course of the war, didn’t they?", "duration": 4.5, "is_parallel": False},
                            {"order": 11, "actor": "Minseok", "type": "Talk", "text": "They did. Continuous success at sea disrupted enemy operations and helped Joseon endure repeated crises.", "duration": 6.0, "is_parallel": False},
                            {"order": 12, "actor": "Minji", "type": "Talk", "text": "And the fighting went on for years, with naval battles becoming a key turning point.", "duration": 5.0, "is_parallel": False},
                            {"order": 13, "actor": "Minseok", "type": "Camera", "action_tag": "FadeOut", "target_position": "Battlefield", "duration": 0.1, "is_parallel": False},
                            {"order": 14, "actor": "Minseok", "type": "Talk", "text": "The Imjin War showed that Japan’s expansionism posed a real threat to the Korean Peninsula.", "duration": 5.0, "is_parallel": False},
                            {"order": 15, "actor": "Minji", "type": "Talk", "text": "And it also proved how dangerous internal division can be during a national crisis.", "duration": 4.5, "is_parallel": False},
                            {"order": 16, "actor": "Minseok", "type": "Talk", "text": "Exactly. The military and strategic lessons from this war became lasting historical lessons.", "duration": 5.0, "is_parallel": False},
                            {"order": 17, "actor": "Minji", "type": "Talk", "text": "That’s why the Imjin War is remembered as a defining moment highlighting the importance of unity and national security.", "duration": 6.5, "is_parallel": False}
                        ]
                    }
                ]
            },
            ensure_ascii=False
        )
    }

    tag_list = extract_video_tag(dummy_state)
    # print("=== Extract Video Tag Node Result ===")   
    # print(tag_list['extracted_tags_json'])