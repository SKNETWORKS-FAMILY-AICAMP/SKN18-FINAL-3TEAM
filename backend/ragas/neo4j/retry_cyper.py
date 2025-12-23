# backend/ragas/neo4j/retry_cyper.py
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from kiwipiepy import Kiwi

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

load_dotenv()

KIWI = Kiwi()

ALLOWED_LABELS = [
    "Person", "Event", "Place", "Organization", "Heritage",
    "Concept", "Object", "System", "Document", "Work", "Ritual",
    "Clothing", "Policy",
]

RETRY_REWRITE_MODEL = os.getenv("RETRY_REWRITE_MODEL", "gpt-4o-mini")


def _get_openai_client():
    key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_KEY")
        or os.getenv("OPENAI_APIKEY")
    )
    if not key:
        return None
    if OpenAI is None:
        return None
    return OpenAI(api_key=key)


def extract_keywords_kiwi(text: str, *, min_len: int = 2) -> List[str]:
    analyzed = KIWI.analyze(text, top_n=1)
    if not analyzed:
        return []
    tokens = analyzed[0][0]
    kws: List[str] = []
    for tok in tokens:
        if tok.tag in ("NNP", "NNG", "NNB") and len(tok.form) >= min_len:
            kws.append(tok.form)

    uniq: List[str] = []
    for k in kws:
        if k not in uniq:
            uniq.append(k)
    return uniq


def fetch_candidate_nodes(driver, keywords: List[str], *, limit: int = 30) -> List[Dict[str, Any]]:
    """
    ✅ Neo4j 5.x 대응: exists(n.prop) -> n.prop IS NOT NULL
    """
    if not keywords:
        return []

    cypher = """
    WITH $keywords AS keywords, $allowed_labels AS allowed_labels
    MATCH (n)
    WHERE any(l IN labels(n) WHERE l IN allowed_labels)
      AND (
        any(kw IN keywords WHERE n.title IS NOT NULL AND n.title CONTAINS kw)
        OR any(kw IN keywords WHERE n.summary IS NOT NULL AND n.summary CONTAINS kw)
      )
    WITH n,
         reduce(score = 0, kw IN keywords |
            score +
            CASE WHEN n.title IS NOT NULL AND n.title CONTAINS kw THEN 3 ELSE 0 END +
            CASE WHEN n.summary IS NOT NULL AND n.summary CONTAINS kw THEN 1 ELSE 0 END
         ) AS score
    RETURN labels(n) AS labels,
           coalesce(n.title, '') AS title,
           coalesce(n.summary, '') AS summary,
           score
    ORDER BY score DESC
    LIMIT $limit
    """

    with driver.session() as session:
        rows = session.run(
            cypher,
            keywords=keywords,
            allowed_labels=ALLOWED_LABELS,
            limit=limit,
        )
        out: List[Dict[str, Any]] = []
        for r in rows:
            title = (r.get("title") or "").strip()
            if not title:
                continue
            out.append({
                "labels": r.get("labels") or [],
                "title": title,
                "summary": r.get("summary") or "",
                "score": int(r.get("score") or 0),
            })
        return out


def _cypher_list_literal(items: List[str]) -> str:
    escaped = []
    for s in items:
        s = (s or "").replace("\\", "\\\\").replace("'", "\\'")
        escaped.append(f"'{s}'")
    return "[" + ", ".join(escaped) + "]"


def regen_cypher_from_titles(
    titles: List[str],
    *,
    hop: int,
    main_limit: int = 8,
    path_limit: int = 80,
) -> str:
    """
    후보 title을 main으로 확정 매칭하고 hop은 그대로 유지.
    (반환 키는 chat_3hop의 컨텍스트 빌더가 처리할 수 있게 main/main_summary/threehop_nodes/threehop_paths 로 맞춤)
    """
    if hop != 3:
        # 3hop 전용으로 강제 (요구사항)
        raise ValueError("regen_cypher_from_titles: hop must be 3 for chat_3hop retry.")

    uniq: List[str] = []
    for t in titles:
        t = (t or "").strip()
        if t and t not in uniq:
            uniq.append(t)
        if len(uniq) >= main_limit:
            break

    if not uniq:
        return "MATCH (n) RETURN n AS main LIMIT 10"

    titles_literal = _cypher_list_literal(uniq)

    return f"""
    WITH {titles_literal} AS titles
    MATCH (n)
    WHERE n.title IS NOT NULL AND n.title IN titles
    WITH n
    LIMIT {int(main_limit)}

    CALL {{
      WITH n
      MATCH p = (n)-[*1..3]-(m)
      RETURN p
      LIMIT {int(path_limit)}
    }}
    WITH n, collect(DISTINCT p) AS paths

    UNWIND paths AS p1
    UNWIND nodes(p1) AS nd
    WITH n, paths, collect(DISTINCT nd) AS hop_nodes

    RETURN
      n AS main,
      n.summary AS main_summary,
      hop_nodes AS threehop_nodes,
      paths AS threehop_paths
    """.strip()


def rewrite_question_llm(
    question: str,
    candidates: List[Dict[str, Any]],
    *,
    model: str = RETRY_REWRITE_MODEL,
    max_candidates: int = 8,
) -> Tuple[str, Dict[str, Any]]:
    """
    후보 title 1~3개를 포함하도록 질문 1줄 리라이팅 (옵션)
    """
    client = _get_openai_client()
    if client is None:
        return question, {"used": False}

    cands = [{"title": c.get("title", ""), "labels": c.get("labels", []), "score": c.get("score", 0)}
             for c in candidates[:max_candidates]]

    system = "너는 GraphDB 검색을 돕는 질문 리라이팅 도우미다. 답변하지 말고 질문 1줄만 출력."
    user = (
        f"[원 질문]\n{question}\n\n"
        f"[후보 노드(title)]\n{cands}\n\n"
        "규칙:\n1) 한국어 질문 1줄\n2) 후보 title 1~3개를 가능한 그대로 포함\n3) 쓸데없는 설명 금지\n"
    )

    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
    )
    elapsed = time.perf_counter() - t0

    text = (resp.choices[0].message.content or "").strip() or question
    usage = getattr(resp, "usage", None)
    meta = {
        "used": True,
        "elapsed_sec": float(elapsed),
        "input_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "output_tokens": getattr(usage, "completion_tokens", None) if usage else None,
        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
        "model": model,
    }
    return text, meta


def retry_cyper(
    question: str,
    driver,
    *,
    hop: int,
    retrieved_count: int,
    min_retrieved_ok: int = 2,
    candidate_limit: int = 30,
    min_candidates: int = 3,
    use_llm_rewrite: bool = True,
    main_limit: int = 8,
    path_limit: int = 80,
) -> Dict[str, Any]:
    """
    반환:
      {
        should_retry: bool,
        strategy: str|None,
        reason: str|None,
        question: str,
        cypher: str|None,
        candidates: list,
        llm_meta: dict,
        hop: int
      }
    """
    if hop != 3:
        raise ValueError("retry_cyper: hop must be 3 for chat_3hop retry.")

    out: Dict[str, Any] = {
        "should_retry": False,
        "strategy": None,
        "reason": None,
        "question": question,
        "cypher": None,
        "candidates": [],
        "llm_meta": {"used": False},
        "hop": hop,
    }

    if retrieved_count >= min_retrieved_ok:
        return out

    out["reason"] = f"retrieved_count<{min_retrieved_ok} ({retrieved_count})"

    keywords = extract_keywords_kiwi(question)
    cands = fetch_candidate_nodes(driver, keywords, limit=candidate_limit)
    out["candidates"] = cands

    if len(cands) < min_candidates:
        out["reason"] = f"too_few_candidates<{min_candidates} ({len(cands)})"
        return out

    # 질문 리라이팅(옵션)
    if use_llm_rewrite:
        new_q, meta = rewrite_question_llm(question, cands)
        out["question"] = new_q
        out["llm_meta"] = meta
        out["strategy"] = "rewrite_question_llm" if meta.get("used") else None

    titles = [c.get("title") for c in cands if c.get("title")]
    out["cypher"] = regen_cypher_from_titles(
        titles, hop=hop, main_limit=main_limit, path_limit=path_limit
    )

    if out["strategy"] is None:
        out["strategy"] = "regen_cypher_from_candidates"

    out["should_retry"] = True
    return out
