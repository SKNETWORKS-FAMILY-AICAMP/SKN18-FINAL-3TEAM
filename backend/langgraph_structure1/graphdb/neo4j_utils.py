import os
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship
from dotenv import load_dotenv

load_dotenv()

# neo4j 접속 정보
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# neo4j 접속
def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# Cypher 실행 함수
def run_cypher(driver, query, params=None):
    params = params or {}
    with driver.session() as session:
        return list(session.run(query, **params))


# 결과 직렬화 함수
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
