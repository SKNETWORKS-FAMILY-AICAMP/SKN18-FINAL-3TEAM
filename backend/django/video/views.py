import json
import asyncio
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# LangGraph 앱 생성 함수 임포트
from backend.langgraph_structure1.graph import create_graph_flow

@csrf_exempt
async def generate_scenario(request):
    """
    [Unity] -> [Django View] -> [LangGraph] -> [Django View] -> [Unity]
    유니티의 자산 정보를 LangGraph로 전달하여 시나리오를 생성하는 비동기 뷰
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        # 1. 유니티 데이터 수신 (Body 파싱)
        body_unicode = request.body.decode('utf-8')
        data = json.loads(body_unicode)
        
        topic = data.get('topic', '')
        asset_info = data.get('asset_info', {}) # 유니티가 보낸 ProjectContextData

        print(f"🔹 [View] 유니티 요청 수신: Topic='{topic}'")

        # 2. 자산 정보를 LangGraph가 이해하기 쉬운 문자열(Prompt)로 변환
        # (리스트들을 쉼표로 연결)
        actors = ", ".join(asset_info.get('actors', []))        #배우(Minji, Minseok)
        locations = ", ".join(asset_info.get('locations', []))  #배경
        bgms = ", ".join(asset_info.get('bgm_files', []))       #BGM(아직 없음)
        sfxs = ", ".join(asset_info.get('sfx_files', []))       #효과음(아직 없음)
        
        # 동작 그룹 포맷팅
        actions_str = ""
        for group in asset_info.get('action_groups', []):
            mood = group.get('mood', 'General')
            tags = group.get('tags', [])
            actions_str += f"- [{mood}]: {', '.join(tags)}\n"

        # LangGraph의 'scene_split_node'로 전달될 자산 가이드라인
        asset_context_prompt = f"""
        [Available Assets from Unity Engine]
        1. Characters: {actors}
        2. Locations: {locations} (IMPORTANT: Use strictly exactly these names for 'location' field)
        3. Background Music: {bgms}
        4. Sound Effects: {sfxs}
        5. Actor Actions (Animation Tags):
        {actions_str}
        
        WARNING: You MUST use ONLY the assets listed above. Do not hallucinate file names.
        """

        # 3. LangGraph 앱 생성
        app = create_graph_flow()

        # 4. LangGraph 실행 (입력 State 주입)
        # query: 주제(역사 질문), asset_context: 유니티 자산 정보
        initial_state = {
            "query": topic,
            "asset_context": asset_context_prompt 
        }

        print("🔹 [View] LangGraph 실행 시작... (검색 및 생성 중)")
        
        # LangGraph는 비동기(async)로 실행됩니다.
        result = await app.ainvoke(initial_state)
        
        print("✅ [View] LangGraph 실행 완료")

        # 5. 결과에서 최종 JSON 대본 추출
        # (우리가 3단계에서 scene_split_node를 수정해서 'scene_script'에 담을 예정입니다)
        final_script = result.get('scene_script')

        if not final_script:
            # 혹시라도 실패했을 경우를 대비한 디버깅 로그
            print("⚠️ [View] 대본 생성 실패. 결과 State:", result.keys())
            return JsonResponse({'error': 'Failed to generate script from LangGraph'}, status=500)

        # 6. 유니티로 최종 JSON 반환
        return JsonResponse(final_script, safe=False)

    except Exception as e:
        print(f"❌ [View Error] {e}")
        return JsonResponse({'error': str(e)}, status=500)
