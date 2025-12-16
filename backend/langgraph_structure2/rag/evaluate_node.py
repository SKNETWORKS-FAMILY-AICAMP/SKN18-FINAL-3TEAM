import json
from typing import Any, Dict, List

from backend.langgraph_structure1.utils import create_model
from backend.langgraph_structure2.state import GraphState
from backend.langgraph_structure2.rag.rag_config import COSINE_SIMILARITY_THRESHOLD


def evaluate_node(state: GraphState) -> GraphState:
    evidences: List[Dict[str, Any]] = state.get("vector_evidences", [])
    if not evidences:
        return {**state, "related_num": 0, "vector_evidences": []}

    question = state.get("translated_query") or state.get("query") or ""
    client = create_model()
    MODEL_NAME = "gpt-5-mini"

    # 1) LLM 입력용 chunks 구성
    chunks = []
    for i, ev in enumerate(evidences):
        content = ev["payload"].get("content", "")
        chunks.append({
            "id": i,
            "content": content[:2000],  # 길이 보호
        })

    judge_prompt = f"""
    사용자의 질문과 각 근거 자료의 관련도를 0~1 사이 점수로 평가하세요.
    1은 매우 관련 있음, 0은 전혀 관련 없음입니다.

    질문:
    {question}

    근거 목록:
    {json.dumps(chunks, ensure_ascii=False)}

    출력은 반드시 JSON만 반환하세요.
    형식:
    {{
    "results": [
        {{ "id": <int>, "score": <float 0~1> }}
    ]
    }}
    """.strip()

    # 2) LLM 단일 호출
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        response_format={"type": "text"},
        messages=[
            {"role": "system", "content": judge_prompt},
        ],
    )

    text = resp.choices[0].message.content.strip()

    # 3) 파싱
    try:
        data = json.loads(text)
        scores = {
            int(r["id"]): float(r["score"])
            for r in data.get("results", [])
        }
    except Exception:
        scores = {}

    # 4) score 반영 + 필터링
    filtered: List[Dict[str, Any]] = []
    for i, ev in enumerate(evidences):
        llm_score = scores.get(i, 0.0)
        if llm_score < 0.0:
            llm_score = 0.0
        if llm_score > 1.0:
            llm_score = 1.0

        if llm_score >= 0.5:
            filtered.append({
                **ev,
                "llm_score": llm_score,
            })

    # 5) 결과 출력
    print(f"[DEBUG] LLM 평가 결과: question={question!r}, "
          f"original_num={len(evidences)}, filtered_num={len(filtered)}")
    for ev in filtered:
        print(ev)
    print("-" * 60)

    return {
        **state,
        "related_num": len(filtered),
        "vector_evidences": filtered,
    }



def route_evaluate(state: GraphState) -> str:
    """
    임계값 통과한 evidence가 없으면 cypher 생성 노드로 보낸다.
    """
    return "generate_node" if state.get("related_num", 0) >= 1 else "generate_cypher_node"
