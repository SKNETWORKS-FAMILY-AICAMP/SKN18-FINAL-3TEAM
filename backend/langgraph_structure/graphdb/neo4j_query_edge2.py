# create_edges.py
import csv
from pathlib import Path
from neo4j import GraphDatabase

import sys
csv.field_size_limit(2_147_483_647)

# --- 프로젝트 루트 기준 경로 ---
BASE_DIR = Path(__file__).resolve().parents[3]
CSV_PATH = BASE_DIR / "infra" / "neo4j" / "import" / "encykorea_cleaned6.csv"

# --- Neo4j 접속 정보 ---
URI = "neo4j://localhost:7687"
USER = "neo4j"
PASSWORD = "skn183final"

# --- 카테고리 라벨 맵 ---
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
    """create_nodes.py와 동일하게 _article_id 부여."""
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            row["_article_id"] = i
            yield row

# ============================================================
# YEAR 기반 관계 생성
# ============================================================

def create_year_edges(driver):
    YEAR_RELATIONS = {
        "main_year": ("MAIN_YEAR",),
        "birth_year": ("BORN_IN",),
        "death_year": ("DIED_IN",),
        "start_year": ("STARTED_IN",),
        "end_year": ("ENDED_IN",),
        "established_year": ("ESTABLISHED_IN",),
        "abolished_year": ("ABOLISHED_IN",),
        "created_year": ("CREATED_IN",),
        "build_year": ("BUILT_IN",),
        "rebuild_year": ("REBUILT_IN",),
        "period_start": ("PERIOD_START_IN",),
        "period_end": ("PERIOD_END_IN",),
        "exist_start_year": ("EXIST_START_IN",),
        "exist_end_year": ("EXIST_END_IN",),
    }

    with driver.session() as session:
        for prop, (rel_type,) in YEAR_RELATIONS.items():
            print(f"[YearEdge] {prop} -> {rel_type}")
            cypher = f"""
            MATCH (n)
            WHERE n.{prop} IS NOT NULL
            MERGE (y:Year {{value: n.{prop}}})
            MERGE (n)-[r:{rel_type}]->(y)
            """
            session.run(cypher)


# ============================================================
# 텍스트 기반 엔티티 관계 생성
# ============================================================

# >>>>>>> 네가 정의한 최종 관계 <<<<<<<
RELATION_TYPE_MAP = {
    # === Event 중심 ===
    ("Place", "Event"): "PLACE_OF_EVENT",
    ("Event", "Person"): "PARTICIPANT",
    ("Event", "Object"): "USED_OBJECT",
    ("Event", "Concept"): "RELATED_CONCEPT",

    # === Heritage → Place ===
    ("Heritage", "Place"): "LOCATED_IN",

    # === Organization 관련 ===
    ("Organization", "Event"): "INVOLVED_IN",
    ("Organization", "System"): "OPERATES",
    ("Organization", "Policy"): "ENFORCES",

    # === Document → Organization ===
    ("Document", "Organization"): "ABOUT_ORG",

    # === Person 관련 ===
    ("Person", "Person"): "ASSOCIATED_WITH",
    ("Person", "Work"): "CREATED_WORK",
}

def canonicalize_pair(label1, id1, label2, id2):
    """
    (label1 → label2) 형태가 RELATION_TYPE_MAP에 있으면 그대로 사용.
    반대(label2 → label1)에 있으면 방향을 뒤집어서 사용.
    없으면 RELATED_TO.
    """
    key = (label1, label2)
    if key in RELATION_TYPE_MAP:
        return label1, id1, label2, id2, RELATION_TYPE_MAP[key]

    rev_key = (label2, label1)
    if rev_key in RELATION_TYPE_MAP:
        return label2, id2, label1, id1, RELATION_TYPE_MAP[rev_key]

    # 관계 미정의 → generic relation
    return label1, id1, label2, id2, "RELATED_TO"


def create_text_edges(driver):
    """
    summary + contents 안에 다른 항목의 title이 등장하면 엣지를 생성한다.
    """
    TARGET_LABELS = {
        "Person", "Event", "Place", "Organization",
        "Concept", "Heritage", "Object", "System",
        "Document", "Work", "Ritual", "Clothing", "Policy",
    }

    # 1) CSV 내용 → 메모리 로드
    nodes = []
    for row in load_rows():
        category = (row.get("category") or "").strip()
        label = CATEGORY_LABEL_MAP.get(category)
        if not label:
            continue

        article_id = int(row["_article_id"])
        title = (row.get("title") or "").strip()
        summary = (row.get("summary") or "").strip()
        contents = (row.get("contents") or "").strip()
        text = f"{summary}\n{contents}"

        nodes.append({
            "article_id": article_id,
            "title": title,
            "label": label,
            "text": text,
        })

    # 2) 필터링
    candidate_nodes = [n for n in nodes if n["label"] in TARGET_LABELS and n["title"]]

    print(f"[TextEdge] 후보 노드 수: {len(candidate_nodes)}")

    # 3) 텍스트 기반 탐색
    with driver.session() as session:
        total_edges = 0

        for i, src in enumerate(candidate_nodes, start=1):
            if i % 100 == 0:
                print(f"[TextEdge] 진행 중 {i}/{len(candidate_nodes)}")

            src_id_raw = src["article_id"]
            src_label_raw = src["label"]
            src_text = src["text"]

            if not src_text:
                continue

            for tgt in candidate_nodes:
                tgt_id_raw = tgt["article_id"]
                if tgt_id_raw == src_id_raw:
                    continue

                tgt_label_raw = tgt["label"]
                tgt_title = tgt["title"]

                if len(tgt_title) < 2:
                    continue

                # 텍스트 안에 대상 title 이 포함되면 관계 생성
                if tgt_title in src_text:
                    src_label, src_id, tgt_label, tgt_id, rel_type = canonicalize_pair(
                        src_label_raw, src_id_raw,
                        tgt_label_raw, tgt_id_raw
                    )

                    cypher = f"""
                    MATCH (a {{article_id: $src_id}})
                    MATCH (b {{article_id: $tgt_id}})
                    MERGE (a)-[r:{rel_type}]->(b)
                    SET r.src_label = $src_label,
                        r.tgt_label = $tgt_label,
                        r.match_source = "text_cooccurrence",
                        r.match_title  = $match_title
                    """
                    session.run(
                        cypher,
                        src_id=src_id,
                        tgt_id=tgt_id,
                        src_label=src_label,
                        tgt_label=tgt_label,
                        match_title=tgt_title
                    )

                    total_edges += 1

        print(f"[TextEdge] 생성된 텍스트 기반 엣지 수: {total_edges}")


# ============================================================
# MAIN
# ============================================================

def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    try:
        print("=== Year 엣지 생성 ===")
        create_year_edges(driver)

        print("=== 텍스트 기반 엔티티 엣지 생성 ===")
        create_text_edges(driver)

        print("엣지 생성 완료.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
