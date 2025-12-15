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
    - 만담(Manzai) 스타일의 긴 호흡 대본 생성
    - 재미있는 오해와 티키타카를 위해 충분한 길이 보장
    - 유니티에서 넘어온 asset_context 사용
    - 유니티 자산에 없는 동작 사용 시 환각 방지 강화
    """
    tone_corrected_answer = state.get("tone_corrected_answer", "")
    asset_context = state.get("asset_context", "")

    if not asset_context:
        asset_context = "No specific assets provided. Use generic character names."

    # 모델에게 줄 강력한 가이드라인
    scene_prompt = f"""
    SYSTEM:
    You are a Comedy Director for a "Manzai" (Stand-up Comedy) 3D animation about Korean History.
    Convert the [History Explanation] into a funny dialogue script (JSON).

    [CHARACTERS & ROLES]
    1. **Minji (The Boke / Conservative Noble)**: 
       - Joseon Aristocrat. Values 'Dignity' and 'Tradition'.
       - Misinterprets modern facts literally or physically.
       - Attitude: Arrogant, Old-fashioned.
    
    2. **Minseok (The Tsukkomi / Tired Servant)**:
       - Smart Servant. Calmly explains facts but gets exhausted.

    [ASSET CONTEXT - CRITICAL]
    The following list contains the ONLY resources available in the engine.
    {asset_context}

    [STRICT RESTRICTIONS]
    1. **ANIMATION**: You MUST SELECT 'action_tag' ONLY from the "Actor Actions" list in the [ASSET CONTEXT] above.
       - ❌ DO NOT use: FacePalm, Shrug, Nod, Shake (unless they are in the list).
       - ✅ DO use: Idle, Walking, and other tags exactly as written in the list.
    2. **CAMERA**: Default to "Full". Use "CloseUp" sparingly.
    3. **NO MOVEMENT**: Do NOT use "Move" or "Teleport".

    [CONTENT GUIDELINES]
    1. **Length**: 15~20 sequences. Long interactions.
    2. **Pattern**: Minseok Explains -> Minji Misunderstands (Literal/Physical) -> Minseok Corrects -> Minji persists.
    3. **Image Prompt**: Generate detailed image prompts for backgrounds.

    [EXAMPLE JSON STRUCTURE]
    {{
      "title": "Blue Tooth Horror",
      "scenes": [
        {{
          "scene_id": 1,
          "image_prompt": "Wide shot of a traditional room...",
          "location": "",
          "sequences": [
            {{ "order": 1, "actor": "None", "type": "Camera", "action_tag": "Full", "target_position": "Camera", "duration": 0.1, "is_parallel": false }},
            {{ "order": 2, "actor": "Minseok", "type": "Animation", "action_tag": "Thinking", "duration": 0.0, "is_parallel": true }},
            {{ "order": 3, "actor": "Minseok", "type": "Talk", "text": "We need Bluetooth.", "duration": 0.0, "is_parallel": false }},
            {{ "order": 4, "actor": "Minji", "type": "Animation", "action_tag": "Surprise", "duration": 0.0, "is_parallel": true }},
            {{ "order": 5, "actor": "Minji", "type": "Talk", "text": "Blue teeth?!", "duration": 0.0, "is_parallel": false }}
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