# chat_2hop.py
"""
Neo4j 그래프DB + 검색 + 코사인 유사도 + LLM 요약
graphdb 단독 테스트 스크립트 (2-hop only)

✅ 목표
- "메인 노드 기준 2-hop만" contexts에 넣어서 RAGAS 평가
- 관계(엣지) 타입은 니가 준 것만 허용 (폭발 방지)
- LIMIT/CAP으로 안 터지게 설계
- OpenAI: Responses API 사용 + .env OPENAI_API_KEY 명시 사용
- ✅ 답변 생성 시간/토큰(입력/출력/합계) 기록 (번역/답변/총합)
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

    # Heritage
    ("Heritage", "Place"): "LOCATED_IN",

    # Organization
    ("Organization", "Event"): "INVOLVED_IN",
    ("Organization", "System"): "OPERATES",
    ("Organization", "Policy"): "ENFORCES",

    # Document
    ("Document", "Organization"): "ABOUT_ORG",

    # Person 관련
    ("Person", "Person"): "ASSOCIATED_WITH",
    ("Person", "Work"): "CREATED_WORK",
}
ALLOWED_REL_TYPES = sorted(set(REL_MAP.values()))

# =====================================================
# 폭발 방지 캡 (필요하면 여기만 조절)
# =====================================================
MAIN_LIMIT = 10
OUT_LIMIT = 40
IN_LIMIT = 40
MAX_2HOP_NODES = 80
MAX_CONTEXTS = 15

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

    # ✅ SDK/버전별 usage 타입이 dict 또는 ResponseUsage 객체일 수 있음
    usage = getattr(r, "usage", None)

    def _u(field: str):
        """usage가 dict든 객체든 안전하게 값 꺼내기"""
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
# ✅ Cypher Generator (2-hop only + allowed rel types)
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

    # ✅ 핵심: allowedRels를 WITH에서 절대 날리지 않음
    return f"""
WITH {keywords_literal} AS keywords, {rels_literal} AS allowedRels

MATCH (n)
WHERE any(l IN labels(n) WHERE l IN [
 'Person','Event','Place','Organization','Heritage',
 'Concept','Object','System','Document','Work','Ritual',
 'Clothing','Policy'
])
AND any(kw IN keywords WHERE coalesce(n.title,'') CONTAINS kw OR coalesce(n.summary,'') CONTAINS kw)
WITH n, allowedRels
LIMIT {MAIN_LIMIT}

CALL {{
  WITH n, allowedRels
  MATCH (n)-[r1]->(m)-[r2]->(n2)
  WHERE type(r1) IN allowedRels AND type(r2) IN allowedRels
  WITH DISTINCT r1, m, r2, n2
  LIMIT {OUT_LIMIT}
  RETURN
    collect(DISTINCT {{
      dir: 'OUT',
      r1: type(r1),
      mid: coalesce(m.title, toString(m.value), ''),
      r2: type(r2),
      n2: coalesce(n2.title, toString(n2.value), ''),
      n2_summary: coalesce(n2.summary, '')
    }}) AS out_paths,
    collect(DISTINCT n2) AS out_2hop
}}

CALL {{
  WITH n, allowedRels
  MATCH (n2)-[r2]->(m)-[r1]->(n)
  WHERE type(r1) IN allowedRels AND type(r2) IN allowedRels
  WITH DISTINCT r1, m, r2, n2
  LIMIT {IN_LIMIT}
  RETURN
    collect(DISTINCT {{
      dir: 'IN',
      r1: type(r1),
      mid: coalesce(m.title, toString(m.value), ''),
      r2: type(r2),
      n2: coalesce(n2.title, toString(n2.value), ''),
      n2_summary: coalesce(n2.summary, '')
    }}) AS in_paths,
    collect(DISTINCT n2) AS in_2hop
}}

WITH n,
     (out_paths + in_paths) AS twohop_paths,
     (out_2hop + in_2hop) AS twohop_nodes_raw

WITH n, twohop_paths, twohop_nodes_raw[..{MAX_2HOP_NODES}] AS twohop_nodes

RETURN
  n AS main,
  n.summary AS main_summary,
  twohop_nodes AS twohop_nodes,
  twohop_paths AS twohop_paths
"""

# =====================================================
# ✅ RAGAS contexts builder (2-hop only)
# =====================================================
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
        paths = rec.get("twohop_paths")
        if isinstance(paths, list):
            for p in paths:
                if not isinstance(p, dict):
                    continue
                n2 = (p.get("n2") or "").strip()
                summ = (p.get("n2_summary") or "").strip()
                if not n2 and not summ:
                    continue

                r1 = p.get("r1") or ""
                mid = p.get("mid") or ""
                r2 = p.get("r2") or ""
                direction = p.get("dir") or ""

                s = f"{direction}: ({r1}) {mid} ({r2}) {n2}"
                if summ:
                    s += f" - {summ}"
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

    # 디버깅용 요약(메인 + 2hop 일부)
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

        t2 = rec.get("twohop_nodes")
        if isinstance(t2, list):
            for n2 in t2:
                if isinstance(n2, dict) and n2.get("_type") == "node":
                    p = n2.get("props", {})
                    summary_nodes.append({
                        "scope": "2hop",
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

    # ✅ 답변 생성(시간/토큰)
    answer, ans_meta = generate_llm_answer(ko_question, contexts)

    # ✅ 번역+답변 총합
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

        # ✅ 메타
        "llm_meta_answer": ans_meta,        # 답변 생성만
        "llm_meta_translation": trans_meta, # 번역만(없으면 None)
        "llm_meta_total": llm_total_meta,   # 번역+답변 합(없으면 None)
    }

def answer_question(question, driver):
    result = answer_question_structured(question, driver)
    print(f"\n[원본 질문] {result['question_original']}\n")
    if result["translated"]:
        print(f"[번역된 한국어 질문] {result['question_ko']}\n")

    print("[생성된 Cypher]")
    print(result["cypher"])
    print("-" * 60)

    print("[DEBUG summary_nodes (top)]")
    print(json.dumps(result["summary_nodes"], ensure_ascii=False, indent=2))
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
