# gain_node.py
"""
Cypher 실행 + Neo4j 검색 결과 정리 노드

- 입력:
    ko_question: 한국어 질문 (임베딩 계산용)
    cypher: 이미 생성된 Cypher 쿼리

- 출력:
    summary_nodes: [
        {
            "title": str,
            "category": str,
            "summary": str,
            "similarity": float | None,
        },
        ...
    ]

LangGraph에서 쓸 때는 gain_node(state)만 호출하면 됨.

state 예시:
{
    "question": "왕의 형벌에 대해 알려줘",
    "ko_question": "조선시대 형벌에 대해 알려줘",
    "cypher": "MATCH ... RETURN ..."
}
"""

import os
import math
import json

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship
from openai import OpenAI

# ===== .env & 클라이언트 =====
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
# Embedding & Cosine Similarity
# =====================================================

def get_query_embedding(text: str):
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
    """
    Neo4j에서 가져온 직렬화 records에 similarity_score 추가
    (node.props.embedding 과 질의 임베딩 코사인 유사도)
    """
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
# Core: 검색 결과 요약 (사진처럼 뽑는 부분)
# =====================================================

def run_gain(ko_question: str, cypher: str):
    """
    실제로 Cypher 실행하고, 사진처럼 summary_nodes만 뽑는 함수.

    Args:
        ko_question: 한국어 질문 (임베딩 계산용)
        cypher: 이미 생성된 Cypher 쿼리

    Returns:
        summary_nodes: [
            { "title", "category", "summary", "similarity" }, ...
        ]
    """
    driver = get_driver()
    try:
        # 1) 질의 임베딩
        q_emb = get_query_embedding(ko_question)

        # 2) Cypher 실행
        raw = run_cypher(driver, cypher)
        ser = serialize_records(raw)

        # 3) similarity 부여
        add_similarity(ser, q_emb)

        # 4) main node 요약 정리
        grouped = {}  # {category: [nodes...]}

        for rec in ser:
            # Year 쿼리면 main_year, 나머지는 main
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

        # 전체 similarity 기준으로 다시 정렬
        summary_nodes.sort(key=lambda x: (x["similarity"] or 0), reverse=True)

        return summary_nodes

    finally:
        driver.close()


# =====================================================
# LangGraph용 노드 함수
# =====================================================

def gain_node(state: dict) -> dict:
    """
    LangGraph에서 사용할 노드.

    기대 입력 state:
    {
        "question": "...",        # 원 질문 (선택)
        "ko_question": "...",     # 한국어 질문 (필수)
        "cypher": "MATCH ...",    # Cypher 쿼리 (필수)
        ...
    }

    반환:
        state + {
            "summary_nodes": [...],   # 사진처럼 뽑힌 검색 결과
        }
    """
    ko_question = state.get("ko_question") or state.get("question")
    cypher = state.get("cypher")

    if not ko_question or not cypher:
        raise ValueError("gain_node: 'ko_question'과 'cypher'가 state에 있어야 합니다.")

    summary_nodes = run_gain(ko_question, cypher)

    # 디버깅 필요하면 여기서 print도 가능
    print("[검색 결과 요약] (카테고리별 최대 3개 → 전체 similarity 정렬)")
    print(json.dumps(summary_nodes, ensure_ascii=False, indent=2))
    print("-" * 60)

    # 기존 state에 summary_nodes만 추가해서 반환
    new_state = dict(state)
    new_state["summary_nodes"] = summary_nodes
    return new_state


# =====================================================
# 단독 실행 테스트용
# =====================================================

if __name__ == "__main__":
    # 간단 테스트용
    test_ko_q = input("한국어 질문: ").strip()
    test_cypher = input("Cypher 쿼리 붙여넣기:\n").strip()

    result = run_gain(test_ko_q, test_cypher)
    print("\n[summary_nodes]")
    print(json.dumps(result, ensure_ascii=False, indent=2))
