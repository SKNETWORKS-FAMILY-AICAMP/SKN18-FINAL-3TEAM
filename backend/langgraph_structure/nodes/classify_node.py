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
from langgraph_structure.state import GraphState
from langgraph.graph import END
from typing import Literal, TypedDict, List
import json
from langgraph_structure.utils import create_model, _extract_json

def classify_node(state: GraphState) -> GraphState:

    query = state.get("query")

    if not query:
        raise ValueError("classify_node: 'query' 값이 state에 없습니다.")

    query = query.lower()

    CLASSIFY_SYSTEM_PROMPT = """
    당신의 역할은 "질문 라우터(Query Router)"입니다.

    입력으로 사용자의 질문을 한 문장 또는 여러 문장으로 받습니다.
    당신은 이 질문을 보고 아래 기준에 따라,
    - 벡터 DB 기반 RAG(Vector)로 처리할지
    - GraphDB(Neo4j) 기반 질의(Graph)로 처리할지
    - 둘 다 사용하는 하이브리드(Hybrid)로 처리할지를 결정해야 합니다.

    1) VECTOR_ONLY (use_vector=true, use_graph=false)
    - 예/아니오 질문
    - 단순 사실/정의/설명/요약
    - 자연어로 쉽게 설명해달라는 요청

    예시:
    - "임진왜란이 뭐야?"
    - "세종대왕이 누구야?"
    - "임진왜란이 1592년에 시작했나요?"
    - "초등학생도 이해할 수 있게 세종대왕 업적 설명해줘."

    2) GRAPH_ONLY (use_vector=false, use_graph=true)
    - 관계/연결/네트워크/사이/영향을 묻는 질문
    - '~한 사람들', '~에 참여한 인물들' 같은 리스트/집합
    - 타임라인/순서/연대기를 묻는 질문
    - 원인-결과/사건 흐름/경로를 묻는 질문

    예시:
    - "임진왜란에 참여한 주요 인물들 알려줘."
    - "세종대왕과 관련된 제도들을 알려줘."
    - "조선 건국부터 임진왜란까지 중요한 사건들을 시간 순서대로 정리해줘."
    - "위화도 회군에서 조선 건국까지 사건 흐름을 알려줘."

    3) HYBRID (use_vector=true, use_graph=true)
    - "설명 + 관계/리스트/타임라인"을 동시에 요구하는 질문
    - 스토리 설명과 함께 관련 인물/사건 목록을 요구하는 질문
    - 애매하지만 그래프형 단어(연결, 관계, 관련, 네트워크, 타임라인, 순서 등)가 섞인 경우

    예시:
    - "임진왜란이 뭔지 설명해주고, 관련 인물 5명만 골라줘."
    - "세종대왕의 업적을 설명하고, 그와 관련된 제도들을 정리해줘."
    - "조선 초기 중요한 인물들 사이의 관계를 간단히 설명해주고, 인물 리스트도 알려줘."

    질문이 애매하면 HYBRID 로 분류하십시오.

    ### 출력 형식 (중요)

    아래 스펙을 만족하는 **문자열**을 출력하십시오.
    - 앞뒤에 어떤 설명 문장도 붙이지 마십시오.

    필드 스펙:
    - query_type: "VECTOR_ONLY", "GRAPH_ONLY", "HYBRID" 중 하나
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

    query_type = response.choices[0].message["content"].strip()
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
    if query_type=="VECTOR_ONLY":
        return "retrieval_node"
    elif query_type=="GRAPH_ONLY":
        return "generate_cypher_node"
    elif query_type=="HYBRID":
        # 둘 다 동시에 사용
        pass


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
        print("  질문        :", result["query"])
        print("  query_type  :", )
        print("  다음 노드    :",nodes)
        print("-" * 80)