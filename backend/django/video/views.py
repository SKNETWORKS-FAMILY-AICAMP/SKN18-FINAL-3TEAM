from django.shortcuts import render
import json
import os, time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 시스템 프롬프트 (PD의 역할 정의)
SYSTEM_PROMPT_TEMPLATE = """
Role: You are a professional Director for creating viral Shorts videos about Korean History using Unity 3D characters.
Goal: Create a strictly valid JSON script based on the user's TOPIC.
Constraint: The video must be under 60 seconds (approx 8-12 sequences).

[Characters]
- Actors: {actors}
- Tone: Minji (Curious, Drama Queen), Minseok (Sassy Guide, Fact-checker)

[Available Assets - YOU MUST USE ONLY THESE]
Locations: {locations}
Actions (Grouped by Mood):
{action_groups}

Audio:
- BGM: {bgm_files}
- SFX: {sfx_files}

[JSON Format Rule]
Response must be a SINGLE JSON object matching this structure:
{{
  "title": "Topic Name",
  "scenes": [
    {{
      "scene_id": 1,
      "location": "Stage",
      "sequences": [
         {{ "order": 1, "actor": "None", "type": "BGM", "target_position": "BGM_File_Name", "is_parallel": true }},
         {{ "order": 2, "actor": "Minji", "type": "Animation", "action_tag": "Action_Name", "duration": 2.0, "is_parallel": false }},
         {{ "order": 3, "actor": "Minseok", "type": "Talk", "text": "Dialogue here...", "duration": 3.0, "is_parallel": false }}
      ]
    }}
  ]
}}
IMPORTANT: 
1. 'action_tag' MUST be one of the provided Action names.
2. 'target_position' for BGM/SFX MUST be one of the provided Audio files.
3. Keep the dialogue short and witty (Shorts style).
"""

@csrf_exempt
def generate_scenario(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        # 1. 유니티에서 보낸 데이터 뜯기
        data = json.loads(request.body)
        topic = data.get('topic', '')
        asset_info = data.get('asset_info', {})

        print(f"🔹 [Director] 주제 수신: {topic}")

        # 2. Fake 모드 체크 (API 키 없을 때 테스트용)
        # .env에 CHAT_USE_FAKE_COMPILE=True 로 되어있거나 키가 없으면 작동
        use_fake = os.getenv('CHAT_USE_FAKE_COMPILE', 'False') == 'True'
        api_key = os.getenv('OPENAI_API_KEY')

        if use_fake or not api_key:
            print("🔸 [Director] Fake 모드로 더미 데이터 반환")
            return JsonResponse(get_dummy_json(topic), safe=False)

        # 3. 프롬프트 조립 (자산 정보 주입)
        actors = ", ".join(asset_info.get('actors', []))
        locations = ", ".join(asset_info.get('locations', []))
        bgms = ", ".join(asset_info.get('bgm_files', []))
        sfxs = ", ".join(asset_info.get('sfx_files', []))
        
        # 동작 그룹 포맷팅
        actions_str = ""
        for group in asset_info.get('action_groups', []):
            actions_str += f"- [{group['mood']}]: {', '.join(group['tags'])}\n"

        final_system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            actors=actors,
            locations=locations,
            bgm_files=bgms,
            sfx_files=sfxs,
            action_groups=actions_str
        )

        # 4. OpenAI GPT 호출
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": f"Topic: {topic}"}
            ],
            response_format={"type": "json_object"} # JSON 모드 강제
        )

        result_json_str = response.choices[0].message.content
        result_data = json.loads(result_json_str)

        # 1. VSCode 터미널에 예쁘게 출력 (디버깅용)
        print("\n" + "="*50)
        print(f"🎬 생성된 시나리오: [{topic}]")
        print("="*50)
        # ensure_ascii=False가 있어야 한글이 깨지지 않고 나옵니다.
        print(json.dumps(result_data, indent=4, ensure_ascii=False)) 
        print("="*50 + "\n")

        # 2. (선택사항) 파일로 따로 저장해두기 (나중에 다시 보려고)
        # save_dir = "saved_scenarios"
        # if not os.path.exists(save_dir):
        #     os.makedirs(save_dir)
        
        # # 파일명: topic_날짜시간.json
        # timestamp = time.strftime("%Y%m%d-%H%M%S")
        # safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '_')).rstrip()
        # filename = f"{save_dir}/{safe_topic}_{timestamp}.json"

        # with open(filename, "w", encoding="utf-8") as f:
        #     json.dump(result_data, f, indent=4, ensure_ascii=False)
        #     print(f"💾 대본 파일 저장 완료: {filename}")

        print("✅ [Director] 생성 완료!")
        return JsonResponse(result_data)

    except Exception as e:
        print(f"❌ [Error] {e}")
        return JsonResponse({'error': str(e)}, status=500)

def get_dummy_json(topic):
    # API 키 없을 때 유니티로 보낼 테스트용 가짜 데이터
    return {
        "title": f"Fake Scenario: {topic}",
        "scenes": [
            {
                "scene_id": 1,
                "location": "Stage",
                "sequences": [
                    { "order": 1, "actor": "Minji", "type": "Talk", "text": f"서버가 '{topic}' 주제를 잘 받았대!", "duration": 3.0, "is_parallel": False },
                    { "order": 2, "actor": "Minseok", "type": "Talk", "text": "하지만 API 키가 없어서 가짜 응답을 보냈어.", "duration": 3.0, "is_parallel": False }
                ]
            }
        ]
    }