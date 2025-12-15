from backend.langgraph_structure1.state import GraphState
from typing import Dict, Any, List
from backend.langgraph_structure1.utils import create_model
import json
import re

def scene_split_node(state: GraphState) -> GraphState:
    """
    Scene 분리 노드
    - 이동(Move/Teleport) 및 시선(LookAt) 제거
    - 고정된 위치에서 Animation + Talk 조합으로만 연출
    """
    tone_corrected_answer = state.get("tone_corrected_answer", "")
    asset_context = state.get("asset_context", "")

    if not asset_context:
        asset_context = "No specific assets provided. Use generic character names."

    # 모델에게 줄 강력한 가이드라인
    scene_prompt = f"""
    SYSTEM:
    You are a Director/Writer for a "Manzai" style (Stand-up Comedy) 3D animation.
    Convert the [History Explanation] into a JSON script where two characters stand in fixed positions and talk.

    [NEW REQUIREMENT - VISUAL DESCRIPTION]
    For each scene, you MUST generate a "image_prompt" field.
    - Describe the visual background atmosphere in detail for an AI Image Generator.
    - Focus on: Location, Lighting, Time of day, Historical Era (Joseon Dynasty), Weather.
    - Example: "A busy marketplace in Hanyang, Joseon Dynasty, sunny day, traditional thatched houses, crowded with people wearing hanbok."

    [RESTRICTIONS - CRITICAL]
    1. **NO MOVEMENT**: Do NOT use "Move" or "Teleport". Characters stay where they spawned.
    2. **NO LOOKAT**: Do NOT use "LookAt". Characters face forward or the camera automatically.
    3. **ALLOWED TYPES**: Only use ["Talk", "Animation", "Camera", "BGM", "SFX"].

    [ASSET CONTEXT]
    Use ONLY these provided assets:
    {asset_context}

    [FIELD GUIDE & BEHAVIOR LOGIC]
    Each sequence object in the JSON represents one instruction for the game engine.

    1. "type": "Talk"
       - **Behavior**: Displays a speech bubble over the actor's head.
       - **Fields**: 
         - "actor": (Required) Name of the speaker.
         - "text": (Required) Dialogue string (Max 15 words).
         - "duration": 0.0 (Engine calculates based on text length).
         - "is_parallel": false (Wait until text finishes).

    2. "type": "Animation"
       - **Behavior**: Plays a body gesture or emotion.
       - **Fields**:
         - "actor": (Required) Who performs the action.
         - "action_tag": (Required) EXACT TAG from [ASSET CONTEXT].
         - "is_parallel": **true** (MUST be true so the character acts WHILE talking in the next line).
       - **Pattern**: Always place [Animation] -> [Talk] pair.

    3. "type": "Camera"
       - **Behavior**: Switches camera shot.
       - **Fields**:
         - "action_tag": "Full" (Both actors) or "CloseUp" (One actor) or "Bust" (Upper body).
         - "target_position": "Camera" (for Full shot) or "ActorName" (for CloseUp).
         - "is_parallel": true (Switch camera instantly).
       - **Rule**: Start with "Full". Use "CloseUp" only for emphasis.

    4. "type": "BGM" / "SFX"
       - **Behavior**: Plays sound.
       - **Fields**:
         - "target_position": Exact filename from [ASSET CONTEXT].

    [EXAMPLE JSON STRUCTURE]
    {{
      "title": "Battle of Hansan",
      "scenes": [
        {{
          "scene_id": 1,
          "image_prompt": "Wide shot of a Joseon Dynasty Panokseon warship deck during a fierce naval battle, dramatic sunset lighting with thick smoke rising, traditional wooden textures, military flags waving in the wind, crashing ocean waves, chaotic 16th-century war atmosphere.",
          "location": "", 
          "sequences": [
            {{ "order": 1, "actor": "None", "type": "Camera", "action_tag": "Full", "target_position": "Camera", "duration": 0.1, "is_parallel": false }},
            {{ "order": 2, "actor": "Minseok", "type": "Animation", "action_tag": "Thinking", "duration": 0.0, "is_parallel": true }},
            {{ "order": 3, "actor": "Minseok", "type": "Talk", "text": "The enemy fleet is approaching fast!", "duration": 0.0, "is_parallel": false }},
            {{ "order": 4, "actor": "None", "type": "Camera", "action_tag": "CloseUp", "target_position": "Minji", "duration": 0.1, "is_parallel": true }},
            {{ "order": 5, "actor": "Minji", "type": "Animation", "action_tag": "Surprised", "duration": 0.0, "is_parallel": true }},
            {{ "order": 6, "actor": "Minji", "type": "Talk", "text": "Prepare the cannons immediately!", "duration": 0.0, "is_parallel": false }}
          ]
        }}
      ]
    }}

    [OUTPUT]
    Output ONLY the valid JSON object.
    """

    client = create_model()
    MODEL_NAME = "gpt-4o-mini"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": scene_prompt},
            {"role": "user", "content": f"[History Explanation]:\n{tone_corrected_answer}"},
        ],
    )

    raw_content = response.choices[0].message.content.strip()

    try:
        script_json = json.loads(raw_content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        if match:
            script_json = json.loads(match.group(0))
        else:
            print(f"❌ [SceneNode] JSON Parsing Failed.")
            script_json = {"title": "Error", "scenes": []}

    scenes = script_json.get("scenes", [])

    return {
        **state,
        "scene_script": script_json,
        "scenes": scenes,
    }