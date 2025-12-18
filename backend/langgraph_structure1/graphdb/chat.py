# chat.py
"""
Neo4j 그래프DB + 검색 + 코사인 유사도 + LLM 요약
graphdb 단독 테스트를 위해 작성된 스크립트
!!!삭제하지 마세요!!!
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
from backend.db_pipeline.common.embedding_model import embed

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
# Language Helper (English → Korean for Cypher/Search)
# =====================================================

def translate_to_korean_if_english(text: str):
    """
    - 한글이 이미 들어 있으면 그대로 사용
    - 한글은 없고 알파벳만 있으면 '영어 질문'이라고 보고 한국어로 번역
    - 그 외(숫자/기호만)는 그대로 사용
    return: (한국어_질문, 번역여부_bool)
    """
    # 한글이 하나라도 있으면 그대로 사용
    if re.search(r"[가-힣]", text):
        return text, False

    # 알파벳이 있으면 영어라고 가정하고 번역
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
        r = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        ko = r.choices[0].message.content.strip()
        return ko, True

    # 한글/영어 둘 다 없으면(숫자나 특수문자 위주) 그대로 사용
    return text, False


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
너는 외국인과 어린아이에게 한국 역사를 설명하는 선생님이다.
하지만 지금 대답할 때는 내가 제공하는 JSON 데이터 안의 정보만 사용해야 한다.

- 너의 일반적인 세계 지식이나 역사 지식은 사용하지 마라.
- 추측하거나 지어내지 마라.
- JSON 내용을 그대로 나열하지 말고, 거기 있는 정보만 이용해 자연어로 정리해서 설명해라.
- 제공된 정보에 대해서 ***절대로 언급하지 마라***(예: "제공된 정보에 따르면", "제공된 정보에는" 등).
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
    print(f"\n[원본 질문] {question}\n")

    # 0) 영어 → 한국어 변환 (Cypher/검색용)
    ko_question, translated = translate_to_korean_if_english(question)
    if translated:
        print(f"[번역된 한국어 질문] {ko_question}\n")
    else:
        print("[번역 불필요] 한국어 또는 혼합 질의로 판단\n")

    # 1) embedding (한국어 질의 기준으로)
    q_emb = get_query_embedding(ko_question)

    # 2) generate cypher (한국어 질의 기준으로)
    cypher = generate_cypher(ko_question)
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

    # 6) LLM 최종 답변 (질문도 한국어 버전으로 넘김)
    answer = generate_llm_answer(ko_question, summary_nodes)

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
