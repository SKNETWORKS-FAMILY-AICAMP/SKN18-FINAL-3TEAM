# drop_edges_only.py
from neo4j import GraphDatabase

# ===== Neo4j 접속정보 =====
URI = "neo4j://localhost:7687"
USER = "neo4j"
PASSWORD = "skn183final"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def drop_all_edges(session):
    print("[1/1] 모든 관계(엣지) 삭제 중...")
    session.run("MATCH ()-[r]->() DELETE r;")
    print("   → 모든 엣지 삭제 완료")


def main():
    with driver.session() as session:
        drop_all_edges(session)

    print("\n🎉 모든 관계만 삭제 완료! 노드는 그대로 유지됨.")


if __name__ == "__main__":
    main()
