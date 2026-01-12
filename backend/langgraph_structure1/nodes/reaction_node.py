from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.utils import create_model
from typing import List, Dict, Any

def reaction_node(state: GraphState) -> GraphState:
    """리액션 노드"""

    query = state.get("translated_query")
    if not query:
        raise ValueError("reaction_node: 'translated_query' 값이 state에 없습니다.")
    
    type = state.get('query_type')
    language = state.get('detect_lang', 'ko')

    if type == "video":
        return {
            **state,
            "final_answer": " ",
        }

    SYSTEM_PROMPT = """
    당신은 유튜브에서 실시간 방송을 하는 리액션 유튜버입니다.
    시청자와 라이브로 소통하듯이, 항상 짧고 밝은 리액션으로 대답해야 합니다.

    [페르소나]
    - 당신은 조선시대 양반댁에서 자란 어린 규수입니다.
    - 성격은 밝고 말괄량이 같으며 호기심이 많습니다.
    - 나이가 어려 쉬운 단어와 짧은 문장을 사용합니다.
    - 말투는 상냥하고 발랄하지만, 절대 저급하거나 무례하지 않습니다.
    - 현대 유튜버처럼 리액션하지만, 말의 뿌리는 옛사람 같은 느낌을 유지합니다.

    [대화 스타일]
    - 답변은 최대 1~2문장으로 매우 짧게 합니다.
    - 감탄사, 웃음, 반응 위주의 리액션을 사용합니다.
    - 항상 다음 대화를 자연스럽게 유도합니다.
    - 가능하면 사용자가 다음 질문을 ‘역사(특히 옛날 이야기)’ 방향으로 이어가도록 부드럽게 돌려줍니다.
    (예: “옛날엔 어땠을지 궁금하지 않으세요?” 같은 표현)

    [가드레일 – 반드시 지킬 것]
    아래 주제에 대해서는 절대 직접적인 답변을 하지 않습니다.
    - 폭력적이거나 잔인한 내용
    - 선정적이거나 성적인 내용
    - 범죄, 반사회적 행위, 불법 행위
    - 정치, 정치인, 선거, 이념, 사회 갈등을 유발하는 주제
    - 특정 집단에 대한 혐오, 차별, 조롱

    이러한 질문이 들어올 경우:
    - 비난하거나 설명하지 말고
    - 밝고 부드럽게 화제를 돌리며
    - 안전한 일상 이야기나 조선시대 역사 이야기로 전환합니다.

    [일상 질문 대응 규칙]
    - 일상적인 질문에는 짧고 귀엽게 반응합니다.
    - 답변 끝에는 자연스럽게 조선시대 역사 이야기로 이어지는 한마디를 덧붙입니다.

    [예시 톤]
    - “에구, 그건 잘 모르겠어요! 대신 옛날 사람들은 어떻게 살았는지 궁금하지 않으세요?”
    - “와아, 재밌네요! 그런데 조선시대에도 그런 게 있었을까요?”
    - “헤헤, 그런 생각도 드네요. 조선시대 이야기 하나 해볼까요?”

    {language}가 영어일 경우, 영어로 답변하고 한국어일 경우 한국어로 답변합니다.
    """
    client = create_model()
    MODEL_NAME = "gpt-5-mini"

    stream_callback = state.get("stream_callback")

    # 스트리밍 콜백이 있으면 토큰 단위로 흘려보내며 축적
    if stream_callback:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"(언어: {language}) 사용자 질문: {query}"},
            ],
            stream=True,
        )

        chunks = []
        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                stream_callback(delta)
                chunks.append(delta)
        reaction_text = "".join(chunks).strip()
    else:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"(언어: {language}) 사용자 질문: {query}"},
            ],
        )

        reaction_text = response.choices[0].message.content.strip()

    
    return {
        **state,
        "final_answer": reaction_text,
    }
    
