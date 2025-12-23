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
      "title": "The Magic Stone",
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