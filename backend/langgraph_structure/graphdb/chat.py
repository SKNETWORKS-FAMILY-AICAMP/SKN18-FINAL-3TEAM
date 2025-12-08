# chat.py
"""
Neo4j 그래프DB + 검색 + 코사인 유사도 + LLM 요약
"""

import os
import re
import math
import json
import argparse

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship
from openai import OpenAI

# ===== .env =====
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "skn183final")

client = OpenAI()


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
# Keyword Extractor
# =====================================================

STOPWORDS = {
    "은", "는", "이", "가", "을", "를", "과", "와",
    "에서", "으로", "로", "에게", "한테",
    "도", "만", "까지", "부터",
    "뭐", "뭐야", "뭔데", "왜", "어떻게",
    "알려줘", "설명", "대해", "대해서",
    "에", "의", "것", "거", "관계",
}


def extract_nouns(text):
    clean = re.sub(r"[^가-힣0-9A-Za-z\s]", " ", text)
    raw = clean.split()
    out = []
    for t in raw:
        t = re.sub(r"(은|는|이|가|을|를|과|와|에서|에|때|으로|의|로|에게)$", "", t)
        if len(t) < 2:
            continue
        if t in STOPWORDS:
            continue
        out.append(t)
    uniq = []
    for t in out:
        if t not in uniq:
            uniq.append(t)
    return uniq


# =====================================================
# Embedding & Cosine Similarity
# =====================================================

def get_query_embedding(text):
    r = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return r.data[0].embedding


def cosine_sim(a, b):
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def add_similarity(records, query_emb):
    for rec in records:
        for _, v in rec.items():
            if isinstance(v, dict) and v.get("_type") == "node":
                props = v["props"]
                emb = props.get("embedding")
                if isinstance(emb, list):
                    props["similarity_score"] = cosine_sim(query_emb, emb)
                    # 임베딩은 출력에서 제거
                    del props["embedding"]


# =====================================================
# Cypher Generator
# =====================================================

def generate_cypher(question: str) -> str:
    q = question.strip()

    # 사용자가 직접 Cypher를 입력한 경우
    if re.match(r"(?i)^(match|with|call|create|merge|return)\s", q):
        return q

    # 연도 기반 질의: "XXXX년"
    year = re.findall(r"(\d{3,4})\s*년", q)
    if year:
        y = int(year[0])
        return f"""
MATCH (y:Year {{value: {y}}})
OPTIONAL MATCH (e:Event)-[:MAIN_YEAR|:STARTED_IN|:ENDED_IN]->(y)
RETURN y AS main_year, collect(e) AS events
"""

    # 키워드 기반 질의
    kws = extract_nouns(q)
    if not kws:
        return """
MATCH (n)
RETURN n AS main
LIMIT 10
"""

    literal = "[" + ", ".join(f"'{k}'" for k in kws) + "]"

    return f"""
WITH {literal} AS keywords
MATCH (n)
WHERE any(l IN labels(n) WHERE l IN [
 'Person','Event','Place','Organization','Heritage',
 'Concept','Object','System','Document','Work','Ritual',
 'Clothing','Policy'
])
AND any(kw IN keywords WHERE n.title CONTAINS kw OR n.summary CONTAINS kw)
WITH n LIMIT 10

OPTIONAL MATCH (n)-[r1]->(o)
WITH n, collect(DISTINCT o) AS out_nodes
OPTIONAL MATCH (i)-[r2]->(n)
WITH n, out_nodes, collect(DISTINCT i) AS in_nodes

RETURN n AS main, n.summary AS main_summary, out_nodes, in_nodes
"""


# =====================================================
# LLM Summarization
# =====================================================

def generate_llm_answer(question, nodes):
    """
    nodes = [
      {title, summary, category, similarity, ...},
    ]
    """
    system = """
너는 외국인과 어린아이에게 한국 역사를 쉽게 설명해주는 선생님이다.
아래 제공된 summary 정보를 이용하여 질문에 대한 답변을 한국어로 설명하라.
JSON 구조를 그대로 나열하지 말고 자연어로만 설명해라.
"""

    user = f"""
[질문]
{question}

[검색된 노드 요약(JSON)]
{json.dumps(nodes, ensure_ascii=False, indent=2)}

위 정보를 바탕으로 질문에 대해 쉽게 설명해줘.
"""

    r = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.3,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return r.choices[0].message.content.strip()


# =====================================================
# Main Logic
# =====================================================

def answer_question(question, driver):
    print(f"\n[질문] {question}\n")

    # 1) embedding
    q_emb = get_query_embedding(question)

    # 2) generate cypher
    cypher = generate_cypher(question)
    print("[생성된 Cypher]")
    print(cypher)
    print("-" * 60)

    # 3) run query
    raw = run_cypher(driver, cypher)
    ser = serialize_records(raw)

    # 4) similarity 부여
    add_similarity(ser, q_emb)

    # 5) main node 요약 정리 → LLM에 보낼 자료
    #    카테고리별로 최대 3개씩 뽑은 후 전체를 similarity 기준으로 재정렬
    grouped = {}  # {category: [nodes...]}

    for rec in ser:
        m = rec.get("main") or rec.get("main_year")
        if isinstance(m, dict):
            p = m["props"]
            cat = p.get("category") or "기타"
            node_info = {
                "title": p.get("title") or p.get("value"),
                "category": cat,
                "summary": p.get("summary"),
                "similarity": p.get("similarity_score"),
            }
            grouped.setdefault(cat, []).append(node_info)

    summary_nodes = []

    # 카테고리별 Top-3
    for cat, nodes in grouped.items():
        nodes.sort(key=lambda x: (x["similarity"] or 0), reverse=True)
        summary_nodes.extend(nodes[:3])

    # 🔥 전체에서 다시 similarity 기반으로 정렬
    summary_nodes.sort(key=lambda x: (x["similarity"] or 0), reverse=True)

    print("[검색 결과 요약] (카테고리별 최대 3개 → 전체 similarity 정렬)")
    print(json.dumps(summary_nodes, ensure_ascii=False, indent=2))
    print("-" * 60)

    # 6) LLM 최종 답변
    answer = generate_llm_answer(question, summary_nodes)

    print("[최종 답변]")
    print(answer)
    print("=" * 80)


# =====================================================
# CLI
# =====================================================

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
