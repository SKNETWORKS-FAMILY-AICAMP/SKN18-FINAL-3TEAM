from backend.langgraph_structure1.state import GraphState
from langgraph.graph import END
from backend.langgraph_structure1.utils import create_model
from deep_translator import GoogleTranslator

def is_korean(text: str) -> bool:
    """텍스트에 한글이 하나라도 포함되어 있는지 간단 체크."""
    return any("가" <= ch <= "힣" for ch in text)


def translate_en_to_ko_if_needed(text: str) -> tuple[str, str]:
    """
    - text에 한글이 있으면: (원문, 'ko')
    - 한글이 없으면: 영어로 보고, GoogleTranslator로 ko로 번역 후 (번역문, 'en')
    """
    if is_korean(text):
        return text, "ko"

    # 영어라고 보고 한국어로 번역
    try:
        translated = GoogleTranslator(source="en", target="ko").translate(text)
    except Exception as e:
        print(f"[WARN] 번역 실패, 원문 사용: {e}")
        translated = text

    return translated, "en"


def classify_node(state: GraphState) -> GraphState:
    query = state.get("query")

    if not query:
        raise ValueError("classify_node: 'query' 값이 state에 없습니다.")

    # 1) 언어 판별 + (영어이면) 한국어 번역
    translated_query, src_lang = translate_en_to_ko_if_needed(query)

    CLASSIFY_SYSTEM_PROMPT = """
    당신의 역할은 "질문 라우터(Query Router)"입니다.

    입력으로 사용자의 질문(한국어)을 한 문장 또는 여러 문장으로 받습니다.
    당신은 이 질문을 보고 아래 기준에 따라,
    - 벡터 DB + 그래프 DB 기반 Hybrid RAG로 처리할지
    - 역사와 전혀 관련이 없다고 판단할지 결정해야 합니다.

    1) hybrid
    - "설명 + 관계/리스트/타임라인"을 동시에 요구하는 질문
    - 스토리 설명과 함께 관련 인물/사건 목록을 요구하는 질문
    - 애매하지만 그래프형 단어(연결, 관계, 관련, 네트워크, 타임라인, 순서 등)가 섞인 경우

    예시:
    - "임진왜란이 뭔지 설명해주고, 관련 인물 5명만 골라줘."
    - "세종대왕의 업적을 설명하고, 그와 관련된 제도들을 정리해줘."
    - "조선 초기 중요한 인물들 사이의 관계를 간단히 설명해주고, 인물 리스트도 알려줘."

    2) no_related
    - 질문 내용이 조선시대 및 한국사와 전혀 관련 없는 경우
    - '물품', '문헌', '제도', '사건', '개념', '인물', '지명', '작품', '유적', '의례·행사','단체', '의복'과 무관한 주제인 경우
    - 역사 관련 단어가 포함되어 있더라도 문장 전체의 맥락이 조선시대 또는 역사와 무관한 경우

    예시:
    - "오늘 날씨 어때?"
    - "현대 기업의 조선사업 전망이 어때?"
    - "이순신은 어떤 신이야?"  (이순신 장군이 아니라 '신' 또는 캐릭터로 말하는 경우)
    - "학익진의 다리 개수가 몇 개인지 맞춰봐."  (조선 수군 전술 구조가 아니라 농담인 경우)
    - "신라면이랑 진라면 중 뭐가 더 맛있어?"

    질문이 애매하거나 조선시대와 관련이 없다면 no_related로 분류하십시오.

    ### 출력 형식 (중요)

    아래 중 하나만 정확히 출력하십시오. 다른 문장이나 설명은 절대 쓰지 마십시오.
    - hybrid
    - no_related
    """

    client = create_model()
    MODEL_NAME = "gpt-5-mini"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_format={"type": "text"},
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
            # LLM에는 항상 "한국어 문장"만 보냄
            {"role": "user", "content": f"사용자 질문: {translated_query}"},
        ],
    )

    query_type = response.choices[0].message.content.strip()
    print(f"[DEBUG] src_lang={src_lang}, query_type={query_type!r}")

    return {
        **state,
        "detect_lang": src_lang,
        "translated_query": translated_query,
        "query_type": query_type,
    }


def route_classify(state: GraphState) -> str:
    """
    node 결과에 따라 다른 node로 분기
    """
    query_type = state.get("query_type")

    if query_type == "hybrid":
        return "hybrid_node"
    elif query_type == "no_related":
        return END
    else:
        raise ValueError(f"지원하지 않는 query_type={query_type}")


if __name__ == "__main__":
    print("=== 질의 분류 인터랙티브 테스트 ===")
    print("질문을 입력하고 Enter. 종료하려면 q 입력.\n")

    while True:
        q = input("질문> ").strip()
        if not q:
            continue
        if q.lower() == "q":
            break

        result = classify_node({"query": q})
        nodes = route_classify(result)

        print("\n--- Classify Result ---")
        print("  질문 원본    :", q)
        print("  감지 언어    :", result.get("detect_lang"))
        print("  질문 번역    :", result.get("translated_query"))
        print("  query_type   :", result.get("query_type"))
        print("  다음 노드    :", nodes)
        print("-" * 80)