# drop_neo4j_all.py
from neo4j import GraphDatabase

# ===== Neo4j 접속정보 =====

URI = "neo4j://localhost:7687"   # bolt:// 도 OK
USER = "neo4j"
PASSWORD = "skn183final"            # 너의 실제 비번으로 변경

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def drop_all_nodes_and_edges(session):
    print("[1/3] 모든 노드 + 관계 삭제 중...")
    session.run("MATCH (n) DETACH DELETE n;")
    print("   → 삭제 완료")


def drop_all_constraints(session):
    print("[2/3] 제약(CONSTRAINTS) 삭제 중...")

    constraints = session.run("SHOW CONSTRAINTS;")
    for record in constraints:
        name = record["name"]
        print(f"   → DROP CONSTRAINT {name}")
        session.run(f"DROP CONSTRAINT {name} IF EXISTS;")

    print("   → 제약 삭제 완료")


def drop_all_indexes(session):
    print("[3/3] 인덱스(INDEXES) 삭제 중...")

    indexes = session.run("SHOW INDEXES;")
    for record in indexes:
        name = record["name"]
        print(f"   → DROP INDEX {name}")
        session.run(f"DROP INDEX {name} IF EXISTS;")

    print("   → 인덱스 삭제 완료")


def main():
    with driver.session() as session:
        drop_all_nodes_and_edges(session)
        drop_all_constraints(session)
        drop_all_indexes(session)
    print("\n🎉 Neo4j 전체 초기화 완료!")


if __name__ == "__main__":
    main()
