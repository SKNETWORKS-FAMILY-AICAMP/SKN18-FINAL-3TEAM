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

    아래 스펙을 만족하는 **JSON 객체 하나만** 출력하십시오.

    - 앞뒤에 어떤 설명 문장도 붙이지 마십시오.
    - 코드 블록 표시(예: ```json 같은 것)를 절대 넣지 마십시오.
    - 반드시 `{` 로 시작해서 `}` 로 끝나는 한 개의 JSON 객체만 출력하십시오.

    필드 스펙:
    - query_type: "VECTOR_ONLY", "GRAPH_ONLY", "HYBRID" 중 하나
    - use_vector: true/false
    - use_graph: true/false
    - reason: 왜 이렇게 분류했는지 한국어로 1~3문장
    - detected_intents: ["explanation", "timeline", "relation", "list"] 중에서 관련되는 것들만 배열로 나열
    - important_keywords: 질문에서 중요한 고유명사나 키워드를 뽑아서 배열로 나열
    """



class ClassifyResult(TypedDict):
    query: str
    query_type: Literal["VECTOR_ONLY", "GRAPH_ONLY", "HYBRID"]
    use_vector: bool
    use_graph: bool
    reason: str
    detected_intents: List[str]
    important_keywords: List[str]





def classify_query(query: str) -> ClassifyResult:
    """LLM에게 질의를 보내서 분류 결과(JSON)를 받는다."""
    client = create_model()
    MODEL_NAME = "gpt-5-mini"
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
            {"role": "user", "content": f"사용자 질문: {query}"},
        ],
    )

    raw = resp.choices[0].message.content or ""
    json_str = _extract_json(raw)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # 실패 시 기본값 + 디버그용 reason
        data = {
            "query_type": "VECTOR_ONLY",
            "use_vector": True,
            "use_graph": False,
            "reason": f"JSON 파싱 실패. 원본: {raw}",
            "detected_intents": ["explanation"],
            "important_keywords": [],
        }

    data["query"] = query
    return data  # type: ignore[return-value]


def decide_nodes(result: ClassifyResult) -> List[str]:
    """
    use_vector / use_graph 플래그를 기반으로
    실제 파이프라인 상 어떤 노드를 타는지 간단히 시뮬레이션.
    """
    nodes: List[str] = ["Query", "Classify"]

    if result["use_vector"]:
        nodes += ["Retrival", "Evaluate_Chunk", "Generate_Answer"]

    if result["use_graph"]:
        if result["use_vector"]:
            nodes.append("|| (parallel) ||")
        nodes += ["Cyper", "Neo4j", "Generate_Answer"]

    if not result["use_vector"] and not result["use_graph"]:
        nodes += ["Generate_Answer"]

    nodes.append("End")
    return nodes

def route_classify(state: GraphState) -> str:
    if state.get("is_history_related") == "irrelevant":
        return END
    return "retrieval_node"

if __name__ == "__main__":
    print("=== 질의 분류 인터랙티브 테스트 ===")
    print("질문을 입력하고 Enter. 종료하려면 q 입력.\n")

    while True:
        q = input("질문> ").strip()
        if not q:
            continue
        if q.lower() == "q":
            break

        result = classify_query(q)
        nodes = decide_nodes(result)

        print("\n--- Classify Result ---")
        print("  질문        :", result["query"])
        print("  query_type  :", result["query_type"])
        print("  use_vector  :", result["use_vector"])
        print("  use_graph   :", result["use_graph"])
        print("  reason      :", result["reason"])
        print("  intents     :", ", ".join(result["detected_intents"]))
        print("  keywords    :", ", ".join(result["important_keywords"]))
        print("  node flow   :", " -> ".join(nodes))
        print("-" * 80)