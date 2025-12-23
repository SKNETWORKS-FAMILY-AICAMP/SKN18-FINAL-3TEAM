"""
Neo4j 그래프DB + 3-hop contexts + LLM 답변 + Retry(질문/쿼리 재시도)

✅ 핵심
- hop(3-hop) 구조는 고정 (retry도 3-hop만)
- retry는 "트리거되기만 해도" retry.used=True 로 기록
- Neo4j 5.x 대응: exists(n.prop) -> n.prop IS NOT NULL
- no-info 메타문장 금지, 정말 못 만들면 fallback 1줄만 허용
- 답변/번역 토큰/시간 메타 기록
"""

# ===== FORCE PROJECT ROOT INTO PYTHONPATH (MUST BE FIRST) =====
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve()
PROJECT_ROOT = THIS_DIR.parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
import re
import math
import json
import argparse
import time
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship
from openai import OpenAI

from kiwipiepy import Kiwi
from backend.db_pipeline.common.embedding_model import embed

# ===== .env =====
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "skn183final")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
RETRY_REWRITE_MODEL = os.getenv("RETRY_REWRITE_MODEL", "gpt-4o-mini")

# retry 설정
MIN_CONTEXTS_OK = int(os.getenv("RETRY_MIN_CONTEXTS_OK", "2"))
RETRY_CANDIDATE_LIMIT = int(os.getenv("RETRY_CANDIDATE_LIMIT", "30"))
RETRY_MIN_CANDIDATES = int(os.getenv("RETRY_MIN_CANDIDATES", "3"))
RETRY_MAIN_LIMIT = int(os.getenv("RETRY_MAIN_LIMIT", "8"))
RETRY_PATH_LIMIT = int(os.getenv("RETRY_PATH_LIMIT", "80"))
RETRY_USE_LLM_REWRITE = os.getenv("RETRY_USE_LLM_REWRITE", "1").strip() not in {"0", "false", "False"}

# ✅ fallback 1줄 (이거 외의 "없다/확인불가" 메타문장 금지)
FALLBACK_NOINFO_SENTENCE = "해당 주제에 대한 구체적 기록은 확인되지 않습니다."


def _get_openai_client():
    key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_KEY")
        or os.getenv("OPENAI_APIKEY")
    )
    if not key:
        raise RuntimeError("OPENAI_API_KEY not found. Put OPENAI_API_KEY=... in your .env and restart terminal.")
    return OpenAI(api_key=key)


client = _get_openai_client()
kiwi = Kiwi()

# =====================================================
# ✅ Allowed Labels / Allowed Rels
# =====================================================
REL_MAP = {
    ("Place", "Event"): "PLACE_OF_EVENT",
    ("Event", "Person"): "PARTICIPANT",
    ("Event", "Object"): "USED_OBJECT",
    ("Event", "Concept"): "RELATED_CONCEPT",
    ("Heritage", "Place"): "LOCATED_IN",
    ("Organization", "Event"): "INVOLVED_IN",
    ("Organization", "System"): "OPERATES",
    ("Organization", "Policy"): "ENFORCES",
    ("Document", "Organization"): "ABOUT_ORG",
    ("Person", "Person"): "ASSOCIATED_WITH",
    ("Person", "Work"): "CREATED_WORK",
}
ALLOWED_REL_TYPES = sorted(set(REL_MAP.values()))
ALLOWED_LABELS = [
    "Person", "Event", "Place", "Organization", "Heritage",
    "Concept", "Object", "System", "Document", "Work", "Ritual",
    "Clothing", "Policy",
]

# =====================================================
# ✅ Caps
# =====================================================
MAIN_LIMIT = 10
OUT3_LIMIT = 50
IN3_LIMIT = 50
MAX_3HOP_NODES = 80

MAX_CONTEXTS = 18
MAIN_SUMMARY_MAX_CHARS = 320
MID1_SUMMARY_MAX_CHARS = 200
MID2_SUMMARY_MAX_CHARS = 200
N3_SUMMARY_MAX_CHARS = 260


# =====================================================
# OpenAI helper (Responses API) + meta
# =====================================================
def call_llm(system: str, user: str, return_meta: bool = False):
    t0 = time.perf_counter()
    r = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    elapsed = time.perf_counter() - t0

    text = (getattr(r, "output_text", None) or "").strip()
    usage = getattr(r, "usage", None)

    def _u(field: str):
        if usage is None:
            return None
        if isinstance(usage, dict):
            return usage.get(field)
        return getattr(usage, field, None)

    input_tokens = _u("input_tokens") or _u("prompt_tokens")
    output_tokens = _u("output_tokens") or _u("completion_tokens")
    total_tokens = _u("total_tokens")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    meta = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "elapsed_sec": float(elapsed),
    }
    return (text, meta) if return_meta else text


# =====================================================
# Neo4j
# =====================================================
def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def run_cypher(driver, query, params=None):
    params = params or {}
    with driver.session() as session:
        return list(session.run(query, **params))


def serialize_value(v):
    if isinstance(v, Node):
        return {"_type": "node", "labels": list(v.labels), "props": dict(v)}
    if isinstance(v, Relationship):
        return {"_type": "relationship", "type": v.type, "props": dict(v)}
    if isinstance(v, list):
        return [serialize_value(i) for i in v]
    if isinstance(v, dict):
        return {k: serialize_value(val) for k, val in v.items()}
    return v


def serialize_records(records):
    return [{k: serialize_value(v) for k, v in r.items()} for r in records]


# =====================================================
# Kiwi keywords
# =====================================================
STOPWORDS = {
    "은", "는", "이", "가", "을", "를", "과", "와",
    "에서", "으로", "로", "에게", "한테",
    "도", "만", "까지", "부터",
    "뭐", "뭐야", "뭔데", "왜", "어떻게",
    "알려줘", "설명", "대해", "대해서",
    "에", "의", "것", "거", "관계",
}


def extract_nouns(text: str):
    analyzed = kiwi.analyze(text)
    if not analyzed:
        return []
    tokens = analyzed[0][0]
    nouns = []
    for tok in tokens:
        if tok.tag in {"NNP", "NNG"}:
            w = tok.form.strip()
            if len(w) < 2:
                continue
            if w in STOPWORDS:
                continue
            nouns.append(w)

    uniq = []
    for w in nouns:
        if w not in uniq:
            uniq.append(w)
    return uniq


# =====================================================
# Embedding & similarity
# =====================================================
def get_query_embedding(text):
    return embed(text)


def cosine_sim(a, b):
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def add_similarity_records_and_lists(records, query_emb):
    def _handle_node_dict(d):
        props = d.get("props", {})
        emb = props.get("embedding")
        if isinstance(emb, list):
            props["similarity_score"] = cosine_sim(query_emb, emb)
            del props["embedding"]

    for rec in records:
        for _, v in rec.items():
            if isinstance(v, dict) and v.get("_type") == "node":
                _handle_node_dict(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict) and item.get("_type") == "node":
                        _handle_node_dict(item)


# =====================================================
# Translate (English -> Korean) + meta
# =====================================================
def translate_to_korean_if_english(text: str):
    if re.search(r"[가-힣]", text):
        return text, False, None

    if re.search(r"[A-Za-z]", text):
        system = (
            "You are a translator who converts English questions about Korean history "
            "into natural Korean. Answer ONLY with the translated Korean sentence."
        )
        user = (
            "다음 문장을 자연스러운 한국어 '질문' 형태로 번역해줘. "
            "불필요한 설명은 쓰지 말고 번역문만 출력해.\n\n"
            f"{text}"
        )
        ko, meta = call_llm(system, user, return_meta=True)
        return ko.strip(), True, meta

    return text, False, None


# =====================================================
# Cypher generator (3-hop fixed)
# =====================================================
def generate_cypher(question: str) -> str:
    q = question.strip()

    # 사용자가 직접 Cypher 입력
    if re.match(r"(?i)^(match|with|call|create|merge|return)\s", q):
        return q

    # 연도 질의
    year = re.findall(r"(\d{3,4})\s*년", q)
    if year:
        y = int(year[0])
        return f"""
MATCH (y:Year {{value: {y}}})
OPTIONAL MATCH (e:Event)-[:MAIN_YEAR|:STARTED_IN|:ENDED_IN]->(y)
RETURN y AS main_year, collect(e) AS events
""".strip()

    kws = extract_nouns(q)
    if not kws:
        return f"MATCH (n) RETURN n AS main LIMIT {MAIN_LIMIT}"

    rels_literal = "[" + ", ".join(f"'{t}'" for t in ALLOWED_REL_TYPES) + "]"
    keywords_literal = "[" + ", ".join(f"'{k}'" for k in kws) + "]"

    return f"""
WITH {keywords_literal} AS keywords, {rels_literal} AS allowedRels

MATCH (n)
WHERE any(l IN labels(n) WHERE l IN [
 'Person','Event','Place','Organization','Heritage',
 'Concept','Object','System','Document','Work','Ritual',
 'Clothing','Policy'
])
AND any(kw IN keywords WHERE
  replace(coalesce(n.title,''), ' ', '') CONTAINS replace(kw,' ','')
  OR replace(coalesce(n.summary,''), ' ', '') CONTAINS replace(kw,' ','')
)
WITH n, allowedRels
LIMIT {MAIN_LIMIT}

CALL {{
  WITH n, allowedRels
  MATCH (n)-[r1]->(m1)-[r2]->(m2)-[r3]->(n3)
  WHERE type(r1) IN allowedRels AND type(r2) IN allowedRels AND type(r3) IN allowedRels
  WITH DISTINCT r1, m1, r2, m2, r3, n3
  LIMIT {OUT3_LIMIT}
  RETURN
    collect(DISTINCT {{
      dir: 'OUT',
      r1: type(r1),
      mid1: coalesce(m1.title, toString(m1.value), ''),
      mid1_summary: coalesce(m1.summary, ''),
      r2: type(r2),
      mid2: coalesce(m2.title, toString(m2.value), ''),
      mid2_summary: coalesce(m2.summary, ''),
      r3: type(r3),
      n3: coalesce(n3.title, toString(n3.value), ''),
      n3_summary: coalesce(n3.summary, '')
    }}) AS out_paths,
    collect(DISTINCT n3) AS out_3hop
}}

CALL {{
  WITH n, allowedRels
  MATCH (n3)-[r3]->(m2)-[r2]->(m1)-[r1]->(n)
  WHERE type(r1) IN allowedRels AND type(r2) IN allowedRels AND type(r3) IN allowedRels
  WITH DISTINCT r1, m1, r2, m2, r3, n3
  LIMIT {IN3_LIMIT}
  RETURN
    collect(DISTINCT {{
      dir: 'IN',
      r1: type(r1),
      mid1: coalesce(m1.title, toString(m1.value), ''),
      mid1_summary: coalesce(m1.summary, ''),
      r2: type(r2),
      mid2: coalesce(m2.title, toString(m2.value), ''),
      mid2_summary: coalesce(m2.summary, ''),
      r3: type(r3),
      n3: coalesce(n3.title, toString(n3.value), ''),
      n3_summary: coalesce(n3.summary, '')
    }}) AS in_paths,
    collect(DISTINCT n3) AS in_3hop
}}

WITH n,
     (out_paths + in_paths) AS threehop_paths,
     (out_3hop + in_3hop) AS threehop_nodes_raw
WITH n, threehop_paths, threehop_nodes_raw[..{MAX_3HOP_NODES}] AS threehop_nodes

RETURN
  n AS main,
  n.summary AS main_summary,
  threehop_nodes AS threehop_nodes,
  threehop_paths AS threehop_paths
""".strip()


# =====================================================
# contexts builder
# =====================================================
def _truncate(s: str, max_chars: int) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    return s if len(s) <= max_chars else s[:max_chars].rstrip() + "…"


def build_contexts_from_ser(ser, max_contexts=MAX_CONTEXTS):
    seen = set()
    contexts = []

    def add_ctx(s: str):
        s = (s or "").strip()
        if len(s) < 5:
            return
        if s in seen:
            return
        seen.add(s)
        contexts.append(s)

    for rec in ser:
        # MAIN 1개는 무조건
        main_sum = rec.get("main_summary") or ""
        main_node = rec.get("main")
        title = ""
        if isinstance(main_node, dict) and main_node.get("_type") == "node":
            p = main_node.get("props", {})
            title = (p.get("title") or p.get("value") or "").strip()

        if main_sum:
            add_ctx(f"[MAIN] {title} - {_truncate(main_sum, MAIN_SUMMARY_MAX_CHARS)}")
            if len(contexts) >= max_contexts:
                break

        paths = rec.get("threehop_paths")
        if not isinstance(paths, list):
            continue

        for p in paths:
            if not isinstance(p, dict):
                continue
            direction = (p.get("dir") or "").strip()

            r1 = p.get("r1") or ""
            mid1 = (p.get("mid1") or "").strip()
            mid1_sum = _truncate(p.get("mid1_summary") or "", MID1_SUMMARY_MAX_CHARS)

            r2 = p.get("r2") or ""
            mid2 = (p.get("mid2") or "").strip()
            mid2_sum = _truncate(p.get("mid2_summary") or "", MID2_SUMMARY_MAX_CHARS)

            r3 = p.get("r3") or ""
            n3 = (p.get("n3") or "").strip()
            n3_sum = _truncate(p.get("n3_summary") or "", N3_SUMMARY_MAX_CHARS)

            s = f"{direction}: ({r1}) {mid1}"
            if mid1_sum:
                s += f" - {mid1_sum}"
            s += f" -> ({r2}) {mid2}"
            if mid2_sum:
                s += f" - {mid2_sum}"
            s += f" -> ({r3}) {n3}"
            if n3_sum:
                s += f" - {n3_sum}"

            add_ctx(s)
            if len(contexts) >= max_contexts:
                break

        if len(contexts) >= max_contexts:
            break

    return contexts[:max_contexts]


# =====================================================
# retry trigger 판단
# =====================================================
_NOINFO_PATTERNS = [
    r"주어진\s*근거",
    r"근거.*(없|않)",
    r"설명되어\s*있지\s*않",
    r"알\s*수\s*없",
    r"확인할\s*수\s*없",
    r"자료.*(없|않)",
]


def answer_looks_noinfo(answer: str) -> bool:
    a = (answer or "").strip()
    if not a:
        return True
    if a == FALLBACK_NOINFO_SENTENCE:
        return True
    for p in _NOINFO_PATTERNS:
        if re.search(p, a):
            return True
    return False


def need_retry(contexts: List[str], answer: str = "", *, min_ok: int = MIN_CONTEXTS_OK) -> bool:
    if not contexts or len(contexts) < min_ok:
        return True
    if any("검색되지 않았습니다" in c for c in contexts):
        return True
    if answer_looks_noinfo(answer):
        return True
    return False


# =====================================================
# retry util (Kiwi -> candidates -> regen cypher)
# =====================================================
def extract_keywords_kiwi_for_retry(text: str, *, min_len: int = 2) -> List[str]:
    analyzed = kiwi.analyze(text, top_n=1)
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


def fetch_candidate_nodes_for_retry(driver, keywords: List[str], *, limit: int = RETRY_CANDIDATE_LIMIT) -> List[Dict[str, Any]]:
    """
    ✅ Neo4j 5.x 대응: exists(n.title) -> n.title IS NOT NULL
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


def regen_cypher_from_titles_3hop(titles: List[str], *, main_limit: int = RETRY_MAIN_LIMIT, path_limit: int = RETRY_PATH_LIMIT) -> str:
    """
    ✅ Neo4j 5.x 대응: exists(n.title) -> n.title IS NOT NULL
    """
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
RETURN n AS main, n.summary AS main_summary, hop_nodes AS threehop_nodes, paths AS threehop_paths
""".strip()


def rewrite_question_llm_for_retry(question: str, candidates: List[Dict[str, Any]], *, model: str = RETRY_REWRITE_MODEL) -> Tuple[str, Dict[str, Any]]:
    """
    B안(프롬프트 기반 리라이팅) 유지.
    """
    if not (RETRY_USE_LLM_REWRITE and bool(os.getenv("OPENAI_API_KEY"))):
        return question, {"used": False}

    rewrite_client = _get_openai_client()

    cands = [{"title": c.get("title", ""), "labels": c.get("labels", []), "score": c.get("score", 0)}
             for c in candidates[:8]]

    system = "너는 GraphDB 검색을 돕는 질문 리라이팅 도우미다. 답변하지 말고 질문 1줄만 출력."
    user = (
        f"[원 질문]\n{question}\n\n"
        f"[후보 노드(title)]\n{cands}\n\n"
        "규칙:\n1) 한국어 질문 1줄\n2) 후보 title 1~3개를 가능한 그대로 포함\n3) 쓸데없는 설명 금지\n"
    )

    t0 = time.perf_counter()
    resp = rewrite_client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
    )
    elapsed = time.perf_counter() - t0
    usage = getattr(resp, "usage", None)

    text = (resp.choices[0].message.content or "").strip() or question
    meta = {
        "used": True,
        "elapsed_sec": float(elapsed),
        "input_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "output_tokens": getattr(usage, "completion_tokens", None) if usage else None,
        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
        "model": model,
    }
    return text, meta


# =====================================================
# Answer prompt (메타 no-info 문장 금지)
# =====================================================
def generate_llm_answer(question, contexts):
    system = f"""
너는 한국사 지식을 '편집'하는 역할만 수행한다.

규칙:
1) 반드시 아래 Context 안의 정보만 재구성해서 답하라.
2) "설명되어 있지 않다", "알 수 없다", "확인할 수 없다",
   "제공된 자료에는 없다", "주어진 근거에는 없다" 같은 메타 판단 문장은 절대 쓰지 마라.
3) Context에 직접적인 문장이 없더라도 관련 사실 조각이 있으면 묶어서 설명하라.
4) 정말로 Context로 답을 구성할 수 있는 정보가 전혀 없을 때만, 아래 문장 1줄만 출력하라:

"{FALLBACK_NOINFO_SENTENCE}"

5) 위 1줄 외의 부정/판단 표현은 금지한다.
6) 일반 지식/추측/상식 사용은 절대 금지한다.
""".strip()

    ctx_block = "\n".join(f"- {c}" for c in (contexts or []))
    user = f"""
[질문]
{question}

[Context]
{ctx_block}

위 규칙을 반드시 지켜서 답변을 작성하라.
""".strip()

    answer, meta = call_llm(system, user, return_meta=True)
    return answer, meta


# =====================================================
# Main structured
# =====================================================
def answer_question_structured(question: str, driver):
    ko_question, translated, trans_meta = translate_to_korean_if_english(question)
    q_emb = get_query_embedding(ko_question)

    # 1차
    cypher = generate_cypher(ko_question)
    raw = run_cypher(driver, cypher)
    ser = serialize_records(raw)
    add_similarity_records_and_lists(ser, q_emb)

    contexts = build_contexts_from_ser(ser, max_contexts=MAX_CONTEXTS)
    if not contexts:
        contexts = ["관련 요약 정보가 검색되지 않았습니다."]

    answer1, ans_meta1 = generate_llm_answer(ko_question, contexts)

    # ✅ retry report (항상 dict) + used는 "트리거만" 기준
    retry_report = {
        "used": False,       # ✅ 트리거만 돼도 True
        "triggered": False,
        "executed": False,
        "applied": False,
        "reason": None,
        "strategy": None,
        "candidates_n": 0,
        "llm_meta": None,
    }

    answer, ans_meta = answer1, ans_meta1

    # retry 트리거
    if need_retry(contexts, answer=answer1, min_ok=MIN_CONTEXTS_OK):
        retry_report["used"] = True
        retry_report["triggered"] = True
        retry_report["reason"] = "noinfo_or_low_context"

        # 후보 찾기
        keywords = extract_keywords_kiwi_for_retry(ko_question)
        cands = fetch_candidate_nodes_for_retry(driver, keywords, limit=RETRY_CANDIDATE_LIMIT)
        retry_report["candidates_n"] = len(cands)

        if len(cands) >= RETRY_MIN_CANDIDATES:
            # 질문 리라이팅(B안)
            _, llm_meta = rewrite_question_llm_for_retry(ko_question, cands)
            retry_report["llm_meta"] = llm_meta
            retry_report["strategy"] = "rewrite_question_llm" if llm_meta.get("used") else "regen_cypher_from_candidates"

            titles = [c.get("title") for c in cands if c.get("title")]
            cypher2 = regen_cypher_from_titles_3hop(titles, main_limit=RETRY_MAIN_LIMIT, path_limit=RETRY_PATH_LIMIT)

            retry_report["executed"] = True

            raw2 = run_cypher(driver, cypher2)
            ser2 = serialize_records(raw2)
            add_similarity_records_and_lists(ser2, q_emb)
            contexts2 = build_contexts_from_ser(ser2, max_contexts=MAX_CONTEXTS)

            if len(contexts2) > len(contexts):
                retry_report["applied"] = True
                contexts = contexts2
                cypher = cypher2
                ser = ser2

            # retry 트리거됐으면 답변은 최종 contexts로 다시 생성
            answer, ans_meta = generate_llm_answer(ko_question, contexts)

    # summary_nodes (디버그용)
    summary_nodes = []
    for rec in ser:
        m = rec.get("main") or rec.get("main_year")
        if isinstance(m, dict) and m.get("_type") == "node":
            p = m.get("props", {})
            summary_nodes.append({
                "scope": "main",
                "title": p.get("title") or p.get("value"),
                "category": p.get("category") or "기타",
                "summary": p.get("summary"),
                "similarity": p.get("similarity_score"),
            })
    summary_nodes.sort(key=lambda x: (x["similarity"] or 0), reverse=True)
    summary_nodes = summary_nodes[:12]

    def _sum_meta(a, b):
        if not a and not b:
            return None
        a = a or {}
        b = b or {}

        def s(k):
            va = a.get(k)
            vb = b.get(k)
            if va is None and vb is None:
                return None
            return (va or 0) + (vb or 0)

        return {
            "input_tokens": s("input_tokens"),
            "output_tokens": s("output_tokens"),
            "total_tokens": s("total_tokens"),
            "elapsed_sec": float((a.get("elapsed_sec") or 0.0) + (b.get("elapsed_sec") or 0.0)),
        }

    llm_total_meta = _sum_meta(trans_meta, ans_meta)

    return {
        "question_original": question,
        "question_ko": ko_question,
        "translated": translated,
        "cypher": cypher,
        "summary_nodes": summary_nodes,
        "contexts": contexts,
        "answer": answer,

        "llm_meta_answer": ans_meta,
        "llm_meta_translation": trans_meta,
        "llm_meta_total": llm_total_meta,

        "retry": retry_report,  # ✅ 항상 dict
    }


def answer_question(question, driver):
    result = answer_question_structured(question, driver)
    print(f"\n[원본 질문] {result['question_original']}\n")
    if result["translated"]:
        print(f"[번역된 한국어 질문] {result['question_ko']}\n")

    print("[생성된 Cypher]")
    print(result["cypher"])
    print("-" * 60)

    print("[RETRY]")
    print(json.dumps(result["retry"], ensure_ascii=False, indent=2))
    print("-" * 60)

    print("[RAGAS contexts]")
    print(json.dumps(result["contexts"], ensure_ascii=False, indent=2))
    print("-" * 60)

    print("[최종 답변]")
    print(result["answer"])
    print("-" * 60)

    print("[LLM META]")
    print(json.dumps({
        "answer": result.get("llm_meta_answer"),
        "translation": result.get("llm_meta_translation"),
        "total": result.get("llm_meta_total"),
    }, ensure_ascii=False, indent=2))
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="*")
    args = parser.parse_args()

    driver = get_driver()
    try:
        if args.question:
            q0 = " ".join(args.question)
            answer_question(q0, driver)

        print("그래프DB 질의 모드. 종료: exit, quit, q, 종료, 끝")
        while True:
            q = input("질문: ").strip()
            if q in {"exit", "quit", "q", "종료", "끝"}:
                print("종료")
                break
            if q:
                answer_question(q, driver)
    finally:
        driver.close()


if __name__ == "__main__":
    main()

