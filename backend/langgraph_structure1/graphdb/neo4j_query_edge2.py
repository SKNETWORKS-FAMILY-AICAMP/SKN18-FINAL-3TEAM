# create_edges.py
import csv
from pathlib import Path
from neo4j import GraphDatabase

import sys
csv.field_size_limit(2_147_483_647)

# --- 프로젝트 루트 경로 ---
BASE_DIR = Path(__file__).resolve().parents[3]
CSV_PATH = BASE_DIR / "infra" / "neo4j" / "import" / "encykorea_cleaned6.csv"

# --- Neo4j 접속 정보 ---
URI = "neo4j://localhost:7687"
USER = "neo4j"
PASSWORD = "skn183final"

# --- 카테고리 → 라벨 매핑 ---
CATEGORY_LABEL_MAP = {
    "인물": "Person",
    "사건": "Event",
    "문헌": "Document",
    "제도": "System",
    "유적": "Heritage",
    "개념": "Concept",
    "물품": "Object",
    "단체": "Organization",
    "지명": "Place",
    "작품": "Work",
    "의례·행사": "Ritual",
    "의복": "Clothing",
    "정책": "Policy",
}

# ============================================================
# CSV 로드
# ============================================================

def load_rows():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            row["_article_id"] = i
            yield row

# ============================================================
# YEAR 엣지 생성
# ============================================================

def create_year_edges(driver):
    YEAR_REL = {
        "main_year": "MAIN_YEAR",
        "birth_year": "BORN_IN",
        "death_year": "DIED_IN",
        "start_year": "STARTED_IN",
        "end_year": "ENDED_IN",
        "established_year": "ESTABLISHED_IN",
        "abolished_year": "ABOLISHED_IN",
        "created_year": "CREATED_IN",
        "build_year": "BUILT_IN",
        "rebuild_year": "REBUILT_IN",
        "period_start": "PERIOD_START_IN",
        "period_end": "PERIOD_END_IN",
        "exist_start_year": "EXIST_START_IN",
        "exist_end_year": "EXIST_END_IN",
    }

    with driver.session() as session:
        for prop, rel_type in YEAR_REL.items():
            print(f"[YEAR] {prop} → {rel_type}")
            cypher = f"""
            MATCH (n)
            WHERE n.{prop} IS NOT NULL
            MERGE (y:Year {{value: n.{prop}}})
            MERGE (n)-[:{rel_type}]->(y)
            """
            session.run(cypher)

# ============================================================
# 텍스트 기반 엣지 — 선언된 조합만 생성
# ============================================================

RELATION_TYPE_MAP = {
    # Event 중심
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


def canonicalize_pair(label1, id1, label2, id2):
    """
    (label1 → label2)이 선언돼 있으면 해당 방향 사용.
    (label2 → label1)이 선언돼 있으면 방향 뒤집어서 사용.
    둘 다 없으면 → None (엣지 생성 X)
    """
    key = (label1, label2)
    if key in RELATION_TYPE_MAP:
        return label1, id1, label2, id2, RELATION_TYPE_MAP[key]

    rev = (label2, label1)
    if rev in RELATION_TYPE_MAP:
        return label2, id2, label1, id1, RELATION_TYPE_MAP[rev]

    return None   # 선언되지 않은 조합은 엣지 생성 안 함


def create_text_edges(driver):
    TARGET_LABELS = {
        "Person", "Event", "Place", "Organization",
        "Concept", "Heritage", "Object", "System",
        "Document", "Work", "Ritual", "Clothing", "Policy",
    }

    # 1) 모든 노드 로드
    nodes = []
    for row in load_rows():
        category = (row.get("category") or "").strip()
        label = CATEGORY_LABEL_MAP.get(category)
        if not label:
            continue

        nodes.append({
            "article_id": int(row["_article_id"]),
            "title": (row.get("title") or "").strip(),
            "label": label,
            "text": f"{row.get('summary','')}\n{row.get('contents','')}",
        })

    candidates = [n for n in nodes if n["label"] in TARGET_LABELS and n["title"]]

    print(f"[TEXT EDGE] 후보 노드 수: {len(candidates)}")

    with driver.session() as session:
        total_edges = 0

        for i, src in enumerate(candidates, start=1):
            if i % 100 == 0:
                print(f"[TEXT EDGE] 진행중 {i}/{len(candidates)}")

            src_id = src["article_id"]
            src_label = src["label"]
            src_text = src["text"]

            for tgt in candidates:
                if tgt["article_id"] == src_id:
                    continue

                tgt_title = tgt["title"]
                tgt_label = tgt["label"]
                tgt_id = tgt["article_id"]

                if len(tgt_title) < 2:
                    continue

                # 텍스트에 타이틀 등장 체크
                if tgt_title not in src_text:
                    continue

                result = canonicalize_pair(src_label, src_id, tgt_label, tgt_id)

                # 선언된 조합만 엣지 생성
                if result is None:
                    continue

                s_label, s_id, t_label, t_id, rel_type = result

                cypher = f"""
                MATCH (a {{article_id: $sid}})
                MATCH (b {{article_id: $tid}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r.src_label=$sl, r.tgt_label=$tl, r.match_title=$mt
                """
                session.run(
                    cypher,
                    sid=s_id,
                    tid=t_id,
                    sl=s_label,
                    tl=t_label,
                    mt=tgt_title,
                )

                total_edges += 1

        print(f"[TEXT EDGE] 생성된 엣지 수 = {total_edges}")


# ============================================================
# MAIN
# ============================================================

def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    try:
        print("\n=== YEAR 엣지 생성 ===")
        create_year_edges(driver)

        print("\n=== TEXT 기반 엣지 생성 (선언된 관계만) ===")
        create_text_edges(driver)

        print("\n🎉 모든 엣지 생성 완료!")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
