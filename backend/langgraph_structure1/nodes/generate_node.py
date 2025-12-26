from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.state_type import Evidence, EvidencePayload
from backend.langgraph_structure1.utils import create_model
from typing import List, Dict, Any
import time


def _safe_float(x, default=0.0) -> float:
    try:
        if x is None:
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def build_llm_prompt(question: str, evidences: List[Evidence]) -> str:
    parts = []
    for idx, ev in enumerate(evidences, start=1):
        src = ev["source"]
        payload = ev["payload"]
        meta = payload.get("metadata", {})
        content = str(payload.get("content", ""))

        if src == "graph":
            title = meta.get("title", "")
            category = meta.get("category", "")
            header = f"[그래프 근거 #{idx}]"
            if category:
                header += f" (분류: {category})"
            if title:
                header += f" 제목: {title}"
            parts.append(f"{header}\n요약: {content}")
        else:
            header = f"[문서 근거 #{idx}]"
            parts.append(f"{header}\n내용: {content[:1200]}")

    evidence_block = "\n\n".join(parts)

    return f"""
당신은 한국사를 설명하는 교사입니다.

아래에는 학생의 질문과, 그 질문과 직접적으로 관련된 근거 자료들이 주어집니다.
이 근거들을 바탕으로, 학생이 읽으면 한 단원 설명처럼 느껴질 정도로 **충분히 자세한** 설명 글을 작성해 주세요.

[질문]
{question}

[근거 자료]
{evidence_block}

지침:
- 답변은 반드시 한국어로 작성합니다.
- 한두 줄짜리 요약이 아니라, 배경 → 전개 → 결과·의의가 드러나는 **완성된 설명문**을 작성합니다.
- 전체 분량은 3~5단락 정도로 작성합니다.
- 근거 자료에 있는 정보들을 중심으로 서술하고, 근거에 전혀 없는 사실은 새로 지어내지 않습니다.
- 목록/불릿/번호 매기기를 사용하지 말고, 문단 형태로만 작성합니다.
- 최종 출력에는 위의 [질문], [근거 자료], '지침'이라는 말은 포함하지 말고, 설명 본문만 출력합니다.
""".strip()


def generate_node(state: GraphState) -> GraphState:
    """
    우선순위:
    1) merged_candidates (하이브리드에서 벡터+그래프를 이미 합쳐 소팅한 결과)
    2) vector_evidences + neo4j_candidates (기존 방식 fallback)

    최종적으로 Evidence로 통합해서 score 기준으로 정렬 후 LLM 호출
    """
    question = state.get("translated_query") or state.get("query", "")
    t0 = state.get("t0")

    all_evidences: List[Evidence] = []

    # =====================================================
    # 1) ✅ merged_candidates 우선 사용
    # =====================================================
    merged: List[Dict[str, Any]] = state.get("merged_candidates") or []
    if merged:
        merged_evidences: List[Evidence] = []
        for row in merged:
            src = row.get("_src") or row.get("source") or "unknown"
            score = _safe_float(row.get("_score"), default=_safe_float(row.get("similarity"), 0.0))

            if src == "neo4j" or src == "graph":
                payload: EvidencePayload = {
                    "content": row.get("summary", "") or "",
                    "metadata": {
                        "title": row.get("title", "") or "",
                        "category": row.get("category", "") or "",
                        "source_depth": row.get("source_depth", None),
                        "raw": row,
                    },
                }
                merged_evidences.append({"source": "graph", "score": score, "payload": payload})
            else:
                # vector
                payload: EvidencePayload = {
                    "content": row.get("summary", "") or row.get("content", "") or "",
                    "metadata": row.get("metadata", {}) or {
                        "title": row.get("title", "") or "",
                        "category": row.get("category", "") or "",
                        "raw": row,
                    },
                }
                merged_evidences.append({"source": "vector", "score": score, "payload": payload})

        # score 기준 정렬 보장
        merged_evidences.sort(key=lambda e: _safe_float(e.get("score"), 0.0), reverse=True)
        all_evidences = merged_evidences

    # =====================================================
    # 2) fallback: 기존 방식
    # =====================================================
    if not all_evidences:
        vector_evidences: List[Evidence] = state.get("vector_evidences", []) or []

        neo4j_rows: List[Dict[str, Any]] = (
            state.get("neo4j_candidates")
            or state.get("neo4j_results")
            or []
        )

        neo4j_evidences: List[Evidence] = []
        for row in neo4j_rows:
            similarity = _safe_float(row.get("similarity"), default=0.0)

            payload: EvidencePayload = {
                "content": row.get("summary", "") or "",
                "metadata": {
                    "title": row.get("title", "") or "",
                    "category": row.get("category", "") or "",
                    "source_depth": row.get("source_depth", None),
                    "raw": row,
                },
            }
            neo4j_evidences.append({"source": "graph", "score": similarity, "payload": payload})

        all_evidences = vector_evidences + neo4j_evidences
        all_evidences.sort(key=lambda e: _safe_float(e.get("score"), 0.0), reverse=True)

    if not all_evidences:
        return {
            **state,
            "final_answer": (
                "주어진 자료에서는 해당 질문에 대한 관련 정보를 찾을 수 없습니다. "
                "더 구체적인 질문이나 추가 자료가 필요합니다."
            ),
        }

    TOP_EVIDENCE_K = 8  # 하이브리드면 좀 더 줘도 좋음
    top_evidences = all_evidences[:TOP_EVIDENCE_K]

    prompt = build_llm_prompt(question, top_evidences)

    client = create_model()
    MODEL_NAME = "gpt-5-mini"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_format={"type": "text"},
        messages=[{"role": "user", "content": prompt}],
    )

    final_answer = (response.choices[0].message.content or "").strip()
    total_elapsed = (time.perf_counter() - t0) if t0 else None

    print(f"[질문] {question}")
    print("[최종 답변]")
    print(final_answer)
    if total_elapsed is not None:
        print(f"[DEBUG] 최종 답변 생성 시간: {total_elapsed:.2f}초")
    print("-" * 60)

    out: GraphState = {
        **state,
        "final_answer": final_answer,
        "answer_input_tokens": getattr(response.usage, "prompt_tokens", None),
        "answer_output_tokens": getattr(response.usage, "completion_tokens", None),
        "answer_total_tokens": getattr(response.usage, "total_tokens", None),
    }
    if total_elapsed is not None:
        out["final_answer_elapsed"] = float(total_elapsed)

    return out
