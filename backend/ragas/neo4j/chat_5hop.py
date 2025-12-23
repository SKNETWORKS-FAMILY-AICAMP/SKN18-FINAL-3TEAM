# chat_5hop.py
"""
Neo4j 그래프DB + 검색 + 코사인 유사도 + LLM 요약
graphdb 단독 테스트 스크립트 (5-hop only)

✅ 목표
- "메인 노드 기준 5-hop만" contexts에 넣어서 RAGAS 평가
- 관계(엣지) 타입은 REL_MAP 기반 허용만 (폭발 방지)
- LIMIT/CAP으로 안 터지게 설계 (5hop은 더 보수적)
- OpenAI: Responses API 사용 + .env OPENAI_API_KEY 명시 사용
- ✅ 답변 생성 시간/토큰(입력/출력/합계) 기록 (번역/답변/총합)
- ✅ 5-hop 컨텍스트에 "중간노드(mid1, mid2, mid3, mid4) 요약" 전부 포함 (근거 강화)
- ✅ 공백/표기 차이로 CONTAINS 미스 완화 (replace 공백 제거 비교)
- ✅ contexts에 MAIN summary 1개는 항상 포함(근거 부족 방지)
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


def _get_openai_client():
    key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_KEY")
        or os.getenv("OPENAI_APIKEY")
    )
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY not found. Put OPENAI_API_KEY=... in your .env and restart terminal."
        )
    return OpenAI(api_key=key)


client = _get_openai_client()
kiwi = Kiwi()

# =====================================================
# ✅ Edge Info (니가 준 관계만 허용)
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

# =====================================================
# ✅ 폭발 방지 캡 (5-hop은 더 보수적으로)
# =====================================================
MAIN_LIMIT = 5
OUT5_LIMIT = 20
IN5_LIMIT = 20
MAX_5HOP_NODES = 40
MAX_CONTEXTS = 10

MAIN_SUMMARY_MAX_CHARS = 320
MID1_SUMMARY_MAX_CHARS = 140
MID2_SUMMARY_MAX_CHARS = 140
MID3_SUMMARY_MAX_CHARS = 140
MID4_SUMMARY_MAX_CHARS = 140
N5_SUMMARY_MAX_CHARS = 220

# =====================================================
# OpenAI (Responses API) Helper + ✅ 토큰/시간 메타
# =====================================================
def call_llm(system: str, user: str, return_meta: bool = False):
    """
    Responses API 호출
    - return_meta=False: str만 반환
    - return_meta=True : (text, meta) 반환
        meta = {
          "input_tokens": int|None,
          "output_tokens": int|None,
          "total_tokens": int|None,
          "elapsed_sec": float
        }
    """
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

    if return_meta:
        return text, meta
    return text

# =====================================================
# Neo4j Helpers
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
# Keyword Extractor (Kiwi)
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
# Embedding & Cosine Similarity
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
# Language Helper (English → Korean) + ✅ 번역 메타
# =====================================================
def translate_to_korean_if_english(text: str):
    """
    return:
      (ko_text, translated_bool, trans_meta)
      trans_meta: 번역 안 했으면 None
    """
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
# ✅ Cypher Generator (5-hop only + allowed rel types)
# =====================================================
def generate_cypher(question: str) -> str:
    q = question.strip()

    # 사용자가 직접 Cypher 입력
    if re.match(r"(?i)^(match|with|call|create|merge|return)\s", q):
        return q

    # 연도 질의 (기존 유지)
    year = re.findall(r"(\d{3,4})\s*년", q)
    if year:
        y = int(year[0])
        return f"""
MATCH (y:Year {{value: {y}}})
OPTIONAL MATCH (e:Event)-[:MAIN_YEAR|:STARTED_IN|:ENDED_IN]->(y)
RETURN y AS main_year, collect(e) AS events
"""

    kws = extract_nouns(q)
    if not kws:
        return f"""
MATCH (n)
RETURN n AS main
LIMIT {MAIN_LIMIT}
"""

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
  MATCH (n)-[r1]->(m1)-[r2]->(m2)-[r3]->(m3)-[r4]->(m4)-[r5]->(n5)
  WHERE type(r1) IN allowedRels AND type(r2) IN allowedRels AND type(r3) IN allowedRels
    AND type(r4) IN allowedRels AND type(r5) IN allowedRels
    AND id(m1) <> id(n) AND id(m2) <> id(n) AND id(m3) <> id(n) AND id(m4) <> id(n) AND id(n5) <> id(n)
    AND id(m1) <> id(m2) AND id(m1) <> id(m3) AND id(m1) <> id(m4) AND id(m1) <> id(n5)
    AND id(m2) <> id(m3) AND id(m2) <> id(m4) AND id(m2) <> id(n5)
    AND id(m3) <> id(m4) AND id(m3) <> id(n5)
    AND id(m4) <> id(n5)
  WITH DISTINCT r1, m1, r2, m2, r3, m3, r4, m4, r5, n5
  LIMIT {OUT5_LIMIT}
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
      mid3: coalesce(m3.title, toString(m3.value), ''),
      mid3_summary: coalesce(m3.summary, ''),
      r4: type(r4),
      mid4: coalesce(m4.title, toString(m4.value), ''),
      mid4_summary: coalesce(m4.summary, ''),
      r5: type(r5),
      n5: coalesce(n5.title, toString(n5.value), ''),
      n5_summary: coalesce(n5.summary, '')
    }}) AS out_paths,
    collect(DISTINCT n5) AS out_5hop
}}

CALL {{
  WITH n, allowedRels
  MATCH (n5)-[r5]->(m4)-[r4]->(m3)-[r3]->(m2)-[r2]->(m1)-[r1]->(n)
  WHERE type(r1) IN allowedRels AND type(r2) IN allowedRels AND type(r3) IN allowedRels
    AND type(r4) IN allowedRels AND type(r5) IN allowedRels
    AND id(m1) <> id(n) AND id(m2) <> id(n) AND id(m3) <> id(n) AND id(m4) <> id(n) AND id(n5) <> id(n)
    AND id(m1) <> id(m2) AND id(m1) <> id(m3) AND id(m1) <> id(m4) AND id(m1) <> id(n5)
    AND id(m2) <> id(m3) AND id(m2) <> id(m4) AND id(m2) <> id(n5)
    AND id(m3) <> id(m4) AND id(m3) <> id(n5)
    AND id(m4) <> id(n5)
  WITH DISTINCT r1, m1, r2, m2, r3, m3, r4, m4, r5, n5
  LIMIT {IN5_LIMIT}
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
      mid3: coalesce(m3.title, toString(m3.value), ''),
      mid3_summary: coalesce(m3.summary, ''),
      r4: type(r4),
      mid4: coalesce(m4.title, toString(m4.value), ''),
      mid4_summary: coalesce(m4.summary, ''),
      r5: type(r5),
      n5: coalesce(n5.title, toString(n5.value), ''),
      n5_summary: coalesce(n5.summary, '')
    }}) AS in_paths,
    collect(DISTINCT n5) AS in_5hop
}}

WITH n,
     (out_paths + in_paths) AS fivehop_paths,
     (out_5hop + in_5hop) AS fivehop_nodes_raw
WITH n, fivehop_paths, fivehop_nodes_raw[..{MAX_5HOP_NODES}] AS fivehop_nodes

RETURN
  n AS main,
  n.summary AS main_summary,
  fivehop_nodes AS fivehop_nodes,
  fivehop_paths AS fivehop_paths
"""

# =====================================================
# ✅ contexts builder (MAIN + 5hop paths) + truncate
# =====================================================
def _truncate(s: str, max_chars: int) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if len(s) <= max_chars:
        return s
    return s[:max_chars].rstrip() + "…"

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
        # ✅ MAIN summary 1개는 무조건 포함
        main_sum = rec.get("main_summary") or ""
        main_node = rec.get("main")
        if isinstance(main_node, dict) and main_node.get("_type") == "node":
            p = main_node.get("props", {})
            title = (p.get("title") or p.get("value") or "").strip()
        else:
            title = ""

        if main_sum:
            add_ctx(f"[MAIN] {title} - {_truncate(main_sum, MAIN_SUMMARY_MAX_CHARS)}")
            if len(contexts) >= max_contexts:
                break

        paths = rec.get("fivehop_paths")
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
            mid3 = (p.get("mid3") or "").strip()
            mid3_sum = _truncate(p.get("mid3_summary") or "", MID3_SUMMARY_MAX_CHARS)

            r4 = p.get("r4") or ""
            mid4 = (p.get("mid4") or "").strip()
            mid4_sum = _truncate(p.get("mid4_summary") or "", MID4_SUMMARY_MAX_CHARS)

            r5 = p.get("r5") or ""
            n5 = (p.get("n5") or "").strip()
            n5_sum = _truncate(p.get("n5_summary") or "", N5_SUMMARY_MAX_CHARS)

            s = f"{direction}: ({r1}) {mid1}"
            if mid1_sum:
                s += f" - {mid1_sum}"
            s += f" -> ({r2}) {mid2}"
            if mid2_sum:
                s += f" - {mid2_sum}"
            s += f" -> ({r3}) {mid3}"
            if mid3_sum:
                s += f" - {mid3_sum}"
            s += f" -> ({r4}) {mid4}"
            if mid4_sum:
                s += f" - {mid4_sum}"
            s += f" -> ({r5}) {n5}"
            if n5_sum:
                s += f" - {n5_sum}"

            add_ctx(s)

            if len(contexts) >= max_contexts:
                break

        if len(contexts) >= max_contexts:
            break

    return contexts[:max_contexts]

# =====================================================
# LLM Answer + ✅ 답변 메타
# =====================================================
def generate_llm_answer(question, contexts):
    system = """
너는 외국인과 어린아이에게 한국 역사를 설명하는 선생님이다.
하지만 지금 대답할 때는 내가 제공하는 '근거(Context)' 안의 정보만 사용해야 한다.

- 일반 지식 사용 금지
- 추측/지어내기 금지
- 근거에 없는 내용 금지
- "제공된 정보에 따르면" 같은 표현 금지
"""
    ctx_block = "\n".join(f"- {c}" for c in (contexts or []))
    user = f"""
[질문]
{question}

[근거(Context)]
{ctx_block}

위 근거를 바탕으로 질문에 대해 쉽게 설명해줘.
"""
    answer, meta = call_llm(system, user, return_meta=True)
    return answer, meta

# =====================================================
# Main Logic (RAGAS 평가용 구조화 결과) + ✅ 메타 리턴
# =====================================================
def answer_question_structured(question: str, driver):
    ko_question, translated, trans_meta = translate_to_korean_if_english(question)

    q_emb = get_query_embedding(ko_question)
    cypher = generate_cypher(ko_question)

    raw = run_cypher(driver, cypher)
    ser = serialize_records(raw)

    add_similarity_records_and_lists(ser, q_emb)

    # 디버깅용 요약(메인 + 5hop 일부)
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

        t5 = rec.get("fivehop_nodes")
        if isinstance(t5, list):
            for n5 in t5:
                if isinstance(n5, dict) and n5.get("_type") == "node":
                    p = n5.get("props", {})
                    summary_nodes.append({
                        "scope": "5hop",
                        "title": p.get("title") or p.get("value"),
                        "category": p.get("category") or "기타",
                        "summary": p.get("summary"),
                        "similarity": p.get("similarity_score"),
                    })

    summary_nodes.sort(key=lambda x: (x["similarity"] or 0), reverse=True)
    summary_nodes = summary_nodes[:12]

    contexts = build_contexts_from_ser(ser, max_contexts=MAX_CONTEXTS)
    if not contexts:
        contexts = ["관련 요약 정보가 검색되지 않았습니다."]

    answer, ans_meta = generate_llm_answer(ko_question, contexts)

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
    }

def answer_question(question, driver):
    result = answer_question_structured(question, driver)
    print(f"\n[원본 질문] {result['question_original']}\n")
    if result["translated"]:
        print(f"[번역된 한국어 질문] {result['question_ko']}\n")

    print("[생성된 Cypher]")
    print(result["cypher"])
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
