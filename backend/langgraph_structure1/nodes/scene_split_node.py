from backend.langgraph_structure1.state import GraphState
from typing import Dict, Any, List
from backend.langgraph_structure1.utils import create_model
import json
import re

def scene_split_node(state: GraphState) -> GraphState:
    """
    Scene 분리 노드 (Manzai Comedy Version)
    - gpt-4o-mini의 모방 능력을 활용해 '웃긴 예시'를 그대로 따라하게 함.
    - 양반(민지)의 '권위적 무식함'과 하인(민석)의 '체념적 비꼬기'를 극대화.
    - 상황과 반대되는 동작(Action Mismatch)을 유도.
    """
    tone_corrected_answer = state.get("tone_corrected_answer", "")
    asset_context = state.get("asset_context", "")
    
    # 혹시 에셋 정보가 없으면 기본값 설정 (환각 방지용)
    if not asset_context:
        asset_context = "Available Actions: Idle, Walk, Run, Victory, Defeat, Cheer, Surprise, HeadShake, Attack, Dying"

    # -------------------------------------------------------------------------
    # 강력한 만담 전용 프롬프트
    # -------------------------------------------------------------------------
    scene_prompt = f"""
    SYSTEM:
    You are a legendary Comedy Writer for a 'Manzai' (Stand-up Comedy) show about Korean History.
    Your goal is to convert the [History Explanation] into a HILARIOUS dialogue script (JSON).

    [TITLE GENERATION RULES - VERY IMPORTANT]
    - The "title" MUST be based on the core topic of the [History Explanation].
    - Do NOT invent fantasy concepts that do not exist in the original explanation.
    - The title should be:
    1. A concise summary of the historical topic
    2. Written in a YouTube-style, click-worthy tone
    - Allowed techniques:
    - Mild exaggeration
    - Rhetorical questions
    - Modern YouTube phrasing
    - NOT allowed:
    - Completely fictional objects
    - Overly abstract metaphors unrelated to the history topic

    Replace:
    "King Sejong invented Hangul."

    With:
    - “A King Created a Language for His People.”
    - “King Sejong Gave His People a New Way to Speak.”
    - “This Is How a King Changed the Voice of a Nation.”

    [CHARACTERS]
    1. **Minji (The Boss / Boke)**: 
       - A Joseon Dynasty Aristocrat (Yangban). Extremely arrogant.
       - **KEY TRAIT**: She NEVER admits ignorance. She interprets all modern/historical facts through "Joseon Logic" (Treason, Magic, Confucianism).
       - **Action Style**: When she says something stupid, she uses CONFIDENT actions (Victory, Cheer, Attack).
       
    2. **Minseok (The Servant / Tsukkomi)**:
       - A tired, smart servant. 
       - **KEY TRAIT**: He explains facts but gets exhausted by Minji's stupidity. Eventually, he just gives up and agrees sarcastically.
       - **Action Style**: Uses tired actions (HeadShake, Dying, Idle) even when he is right.

    [COMEDY ALGORITHM]
    1. Minseok explains a fact.
    2. **Minji misunderstands it** as something offensive, treasonous, or magical. (e.g., "Election" -> "Rebellion against the King?!")
    3. Minseok sighs and corrects her.
    4. **Minji doubles down** and gets angry or proud of her wrong idea.
    5. Minseok gives up: "Yes, my lady. You are absolutely right..." (Sarcasm).

    [ASSET RULES - CRITICAL]
    - You must ONLY use 'action_tag' from this list:
    {asset_context}
    - If the exact action is not in the list, use 'Idle'.
    - DO NOT use 'Move' or 'Teleport'. Characters stand still and talk.

    [ONE-SHOT EXAMPLE (COPY THIS STYLE!)]
    Topic: "Smartphone"
    {{
      "title": "",
      "scenes": [
        {{
          "scene_id": 1,
          "image_prompt": "Joseon market street, sunny day",
          "location": "",
          "sequences": [
            {{ "order": 1, "actor": "Minseok", "type": "Animation", "action_tag": "Idle", "duration": 0.0, "is_parallel": true }},
            {{ "order": 2, "actor": "Minseok", "type": "Talk", "text": "My Lady, look at this. It is a Smartphone.", "duration": 0.0 }},
            {{ "order": 3, "actor": "Minji", "type": "Animation", "action_tag": "Surprise", "duration": 0.0, "is_parallel": true }},
            {{ "order": 4, "actor": "Minji", "type": "Talk", "text": "Smart... Phone? Is it a name of a new execution device?", "duration": 0.0 }},
            {{ "order": 5, "actor": "Minseok", "type": "Talk", "text": "No. You can talk to people far away with this glass plate.", "duration": 0.0 }},
            {{ "order": 6, "actor": "Minji", "type": "Animation", "action_tag": "Yelling Out", "duration": 0.0, "is_parallel": true }},
            {{ "order": 7, "actor": "Minji", "type": "Talk", "text": "Talking to a glass plate?! You are possessed by a demon! Guard! Behead him!", "duration": 0.0 }},
            {{ "order": 8, "actor": "Minseok", "type": "Animation", "action_tag": "Thoughtful Head Shake", "duration": 0.0, "is_parallel": true }},
            {{ "order": 9, "actor": "Minseok", "type": "Talk", "text": "(Sigh) Yes, yes. I am a demon. Please put down the sword.", "duration": 0.0 }}
          ]
        }}
      ]
    }}

    [INPUT DATA]
    [History Explanation]:
    {tone_corrected_answer}

    [OUTPUT]
    Output ONLY the valid JSON object based on the [History Explanation].
    Make it funny and long enough (15+ sequences).
    """

    client = create_model()
    # 개그와 포맷 준수에 강한 4o-mini 사용
    MODEL_NAME = "gpt-4o-mini" 

    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": scene_prompt},
        ],
    )

    raw_content = response.choices[0].message.content.strip()

    try:
        script_json = json.loads(raw_content)
    except json.JSONDecodeError:
        # JSON 파싱 실패 시, 정규식으로 JSON 부분만 추출 시도
        match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        if match:
            script_json = json.loads(match.group(0))
        else:
            print(f"❌ [SceneNode] JSON Parsing Failed. Raw: {raw_content[:50]}...")
            script_json = {"title": "Error", "scenes": []}

    scenes = script_json.get("scenes", [])

    return {
        **state,
        "scene_script": script_json,
        "scenes": scenes,
    }

if __name__ == "__main__":
    # 테스트용 메인 함수
    test_state = GraphState({
        "tone_corrected_answer": "The Imjin War was a conflict in which Japan invaded Joseon from 1592 to 1598. The war began as external expansionist ambitions intersected with internal political and social divisions within Joseon. The fundamental causes are commonly identified as Japan’s aggressive expansionist intentions and the weakening of Joseon’s defensive capabilities due to internal fragmentation. This background invited foreign intervention on the Korean Peninsula and has remained a central focus of historical discussions regarding the structural causes of the war’s outbreak. During the course of the war, the role of the Joseon navy was particularly significant. Admiral Yi Sun-sin led the navy to numerous victories, which had a profound impact on the overall direction of the war. Sustained naval successes disrupted the enemy’s operational capabilities and are widely regarded as a primary reason why Joseon was able to overcome several critical crises during the conflict. As the war continued for several years, achievements in naval battles emerged as a key variable influencing shifts in momentum and turning points in the war. The Imjin War demonstrated that Japanese expansionism posed a tangible threat to the Korean Peninsula and clearly revealed how internal divisions could weaken a state’s ability to respond to crises. Furthermore, the importance of military and strategic competence displayed during the war became an enduring historical lesson. The experiences of this period are evaluated as a significant event in Korean history, underscoring the necessity of national security and internal unity.",
        "asset_context": "Available Actions: Idle, Walk, Run, Victory, Defeat, Cheer, Surprise, HeadShake, Attack, Dying"
    })
    result_state = scene_split_node(test_state)
    print(json.dumps(result_state.get("scene_script", {}), indent=2, ensure_ascii=False))