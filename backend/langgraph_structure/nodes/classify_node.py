"""
질의 분류 테스트용 단일 스크립트 (인터랙티브)

- PowerShell/터미널에서 질문을 직접 입력하면
  - VECTOR_ONLY / GRAPH_ONLY / HYBRID 분류
  - use_vector / use_graph 플래그
  - 실제로 어떤 노드(Retrival / Cyper+Neo4j)를 타는지
를 출력한다.

필수:
    pip install openai python-dotenv

환경변수(.env):
    OPENAI_API_KEY=...
"""
from backend.langgraph_structure.state import GraphState
from langgraph.graph import END
from backend.langgraph_structure.utils import create_model

def classify_node(state: GraphState) -> GraphState:

    query = state.get("query")

    if not query:
        raise ValueError("classify_node: 'query' 값이 state에 없습니다.")

    query = query.lower()

    CLASSIFY_SYSTEM_PROMPT = """
    당신의 역할은 "질문 라우터(Query Router)"입니다.

    입력으로 사용자의 질문을 한 문장 또는 여러 문장으로 받습니다.
    당신은 이 질문을 보고 아래 기준에 따라,
    - 벡터 DB + 그래프 DB 기반 Hybrid RAG로 처리할지
    - GraphDB(Neo4j) 기반 질의(Graph)로 처리할지
    - 역사와 연관이 없다고 판단할지 결정해야합니다.

    1) hybrid
    - "설명 + 관계/리스트/타임라인"을 동시에 요구하는 질문
    - 스토리 설명과 함께 관련 인물/사건 목록을 요구하는 질문
    - 애매하지만 그래프형 단어(연결, 관계, 관련, 네트워크, 타임라인, 순서 등)가 섞인 경우

    예시:
    - "임진왜란이 뭔지 설명해주고, 관련 인물 5명만 골라줘."
    - "세종대왕의 업적을 설명하고, 그와 관련된 제도들을 정리해줘."
    - "조선 초기 중요한 인물들 사이의 관계를 간단히 설명해주고, 인물 리스트도 알려줘."

    2) no_related
    - 질문 내용이 조선시대와 전혀 관련 없는 경우
    - '물품', '문헌', '제도', '사건', '개념', '인물', '지명', '작품', '유적', '의례·행사','단체', '의복'과 무관한 주제인 경우
    - 역사 관련 단어가 포함 되어있더라도 문장 전체의 맥락이 조선시대 또는 역사와 무관한 경우

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
            {"role": "user", "content": f"사용자 질문: {query}"},
        ],
    )

    query_type = query_type = response.choices[0].message.content.strip()

    print(query_type)

    return {
        **state,
        "query_type": query_type,
    }

def route_classify(state: GraphState) -> str:
    """
    node 결과에 따라 다른 node로 분기
    """
    query_type = state.get("query_type")
    # if query_type=="vector_only":
    #     return "retrieval_node"
    # elif query_type=="graph_only":
    #     return "generate_cypher_node"
    if query_type=="hybrid":
        # 둘 다 동시에 사용
        return "hybrid_node"
    elif query_type=="no_related":
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
        print("  질문        :", q)
        print("  query_type  :", result.get("query_type"))
        print("  다음 노드    :",nodes)
        print("-" * 80)