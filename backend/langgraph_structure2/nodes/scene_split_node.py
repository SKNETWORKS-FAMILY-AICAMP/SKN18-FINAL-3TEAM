# scene 분리(장면/대사 분리)
from backend.langgraph_structure1.state import GraphState
from typing import Dict, Any, List
from backend.langgraph_structure1.utils import create_model
import json

def scene_split_node(state: GraphState) -> GraphState:
    """
    Scene 분리 노드
    - tone_corrected_answer(간단 영어 설명)를
      게임에서 사용하는 JSON 씬 스크립트 형태로 변환
    """
    tone_corrected_answer = state.get("tone_corrected_answer", "")

    # LLM에게 요구할 JSON 스키마 설명
    scene_prompt = """
    SYSTEM:
    You are a scenario writer for a game engine.
    You convert a simple English explanation about Korean history into a structured JSON cutscene script.

    [ABSOLUTE RULES]
    1. Do NOT change the meaning, facts, or sequence of the explanation.
    2. Keep the English difficulty simple.
    3. Do NOT add or remove historical content.
    4. All Romanized Korean names must remain unchanged.

    [TARGET FORMAT]

    You MUST output a single valid JSON object with the following structure (no comments):

    {
      "title": "Short title in simple English",
      "scenes": [
        {
          "scene_id": 1,
          "location": "Stage",
          "sequences": [
            {
              "order": 1,
              "actor": "None",
              "type": "BGM",
              "target_position": "Funny_Theme",
              "is_parallel": true
            },
            {
              "order": 2,
              "actor": "Minji",
              "type": "Animation",
              "action_tag": "Surprised",
              "duration": 1.5,
              "is_parallel": false
            },
            {
              "order": 3,
              "actor": "Minji",
              "type": "Talk",
              "text": "Wait, is this a dragon?",
              "duration": 2.0,
              "is_parallel": false
            },
            {
              "order": 4,
              "actor": "None",
              "type": "Camera",
              "target_position": "Minseok",
              "action_tag": "Bust",
              "duration": 0.5,
              "is_parallel": true
            },
            {
              "order": 5,
              "actor": "Minseok",
              "type": "Talk",
              "text": "No! It's the Turtle Ship.",
              "duration": 2.0,
              "is_parallel": false
            },
            {
              "order": 6,
              "actor": "None",
              "type": "SFX",
              "target_position": "Whoosh",
              "is_parallel": true
            }
          ]
        }
      ]
    }

    [DETAILED RULES]

    1. title
       - A short, simple-English title summarizing the overall explanation.

    2. scenes
       - Split the explanation into multiple scenes.
       - Each scene should focus on one main idea, event, or concept.

    3. scene fields
       - scene_id: integer starting from 1.
       - location: simple place name in English (e.g., "Stage", "Harbor", "Battlefield").

    4. sequences
       - An ordered list of actions inside each scene.
       - order: strictly increasing integer within the scene (1, 2, 3, ...).

       [Supported types]

       (1) "Talk"
           - Fields:
             - actor: character name (e.g., "Minji", "Minseok", "Narrator")
             - type: "Talk"
             - text: the line (simple English)
             - duration: speaking time in seconds (float, e.g., 2.0)
             - is_parallel: false (usually)
           - Use this to explain the historical content as dialogue or narration.

       (2) "Animation"
           - Fields:
             - actor: character name
             - type: "Animation"
             - action_tag: short tag (e.g., "Surprised", "Thinking")
             - duration: seconds (float)
             - is_parallel: true or false

       (3) "BGM"
           - Fields:
             - actor: "None"
             - type: "BGM"
             - target_position: BGM name (e.g., "Serious_Theme")
             - is_parallel: true

       (4) "SFX"
           - Fields:
             - actor: "None"
             - type: "SFX"
             - target_position: SFX name (e.g., "Whoosh", "Explosion")
             - is_parallel: true

       (5) "Camera"
           - Fields:
             - actor: "None"
             - type: "Camera"
             - target_position: target character or place (e.g., "Minji", "Battlefield")
             - action_tag: shot type (e.g., "Bust", "Wide")
             - duration: seconds (float)
             - is_parallel: true or false

    5. Characters
       - You may freely use simple names like "Minji", "Minseok", and "Narrator".
       - Use them consistently across scenes.

    6. Tone
       - Simple, friendly, educational.
       - All explanations must remain historically accurate to the original text.

    [OUTPUT FORMAT]
    - Output ONLY the JSON object.
    - Do NOT include any extra text, comments, or markdown.
    """

    client = create_model()
    MODEL_NAME = "gpt-4o-mini"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        # JSON 모드 (지원되는 환경이라는 전제)
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": scene_prompt},
            {"role": "user", "content": tone_corrected_answer},
        ],
    )

    raw_content = response.choices[0].message.content.strip()

    # JSON 파싱
    try:
        script_json = json.loads(raw_content)
    except json.JSONDecodeError:
        # 혹시 모델이 앞뒤에 뭔가 붙였을 경우를 대비한 fallback
        import re
        match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        if not match:
            raise
        script_json = json.loads(match.group(0))

    # script_json은 아래와 같은 형태를 기대:
    # {
    #   "title": "...",
    #   "scenes": [ { "scene_id": 1, "location": "...", "sequences": [...] }, ... ]
    # }

    scenes: List[Dict[str, Any]] = script_json.get("scenes", [])

    # 결과 터미널 출력
    print("[DEBUG] scene")
    print(f"Scene:\n{scenes}")
    print("-" * 60)

    return {
        **state,
        "scene_script": script_json,  # 전체 JSON (title + scenes)
        "scenes": scenes,            # 후속 노드에서 바로 씬 리스트만 쓰고 싶을 때
    }


if __name__ == "__main__":
    # 예시 tone_corrected_answer (간단한 영어로 번역된 한국사 설명 텍스트)
    tone_corrected_answer = """
    Imjin Waeran (the Imjin War) was a war from 1592 to 1598 when Ilbon (Japan) invaded Joseon (the Joseon Dynasty).
    The main causes of this war can be summed up as Ilbon (Japan)'s expansionism and divisions inside Joseon (the Joseon Dynasty).
    Ilbon (Japan)'s outward expansion and the internal conflicts in Joseon (the Joseon Dynasty) society came together and made it hard to stop the foreign invasion.
    The war began in earnest with Ilbon (Japan)'s invasion, and Joseon (the Joseon Dynasty) had to defend its land and respond militarily.
    At this time, Yi Sun-sin (Admiral Yi Sun-sin) led the Joseon sugun (the Joseon navy) and won several victories, playing an important role at sea.
    Under Yi Sun-sin (Admiral Yi Sun-sin)'s command, the Joseon sugun (the Joseon navy) controlled or defeated the enemy's naval forces, and this had an important effect on how the war developed.
    The Imjin Waeran (the Imjin War) lasted many years and left a big impact on Joseon (the Joseon Dynasty) society and its military during the war.
    Especially the military achievements of key figures like Yi Sun-sin (Admiral Yi Sun-sin) became an important part of war history and were valued by later generations.
    Overall, the Imjin Waeran (the Imjin War) showed how vulnerable a country can become when foreign invasion and internal problems combine, and it has become a subject of historical lessons and study.
    """

    test_state: GraphState = {
        "tone_corrected_answer": tone_corrected_answer,
    }

    scene_state = scene_split_node(test_state)

    print("\n=== scene_script (full JSON) ===")
    print(json.dumps(scene_state["scene_script"], indent=2, ensure_ascii=False))
    print("-" * 60)

    print("\n=== scenes only ===")
    print(json.dumps(scene_state["scenes"], indent=2, ensure_ascii=False))
    print("-" * 60)