# create_edges.py
import csv
from pathlib import Path
from neo4j import GraphDatabase

csv.field_size_limit(2_147_483_647)

from backend.db_pipeline.common.config import (
    NEO4J_URI as URI,
    NEO4J_USER as USER,
    NEO4J_PASSWORD as PASSWORD,
    CATEGORY_LABEL_MAP,
    INPUT_CSV,
)

# ============================================================
# 공통: CSV 로딩
# ============================================================

def load_rows():
    """create_nodes.py에서처럼 _article_id 포함해서 로딩."""
    with open(Path(INPUT_CSV), encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            row["_article_id"] = i
            yield row

# ============================================================
# 1) 연도(Year) 엣지 생성
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
# 2) 텍스트 기반 엔티티 간 엣지 생성 (정방향/단방향 설계 반영)
# ============================================================

# 라벨 조합별 "정방향" 관계 타입
RELATION_TYPE_MAP: dict[tuple[str, str], str] = {
    # === 참여 / 소속 =================================================
    ("Person", "Event"): "PARTICIPATED_IN",
    ("Organization", "Event"): "INVOLVED_IN",
    ("Person", "Organization"): "MEMBER_OF",

    # === 위치 ========================================================
    ("Event", "Place"): "OCCURRED_IN",
    ("Heritage", "Place"): "LOCATED_IN",
    ("Place", "Place"): "IN_REGION",  # 한양 -> 조선 같은 상위 지역

    # === 사건에서 사용하는 것들 ======================================
    ("Event", "Object"): "USED_OBJECT",        # 임진왜란 -> 거북선
    ("Event", "Concept"): "APPLIED_CONCEPT",   # 한산도대첩 -> 학익진

    # === 유적 / 사건 / 인물 ==========================================
    ("Heritage", "Event"): "RELATED_EVENT",    # 진주성 -> 임진왜란
    ("Person", "Heritage"): "RELATED_SITE",    # 이순신 -> 현충사

    # === 제도 / 정책 (집행 주체는 조직) ================================
    ("Organization", "System"): "OPERATES_SYSTEM",
    ("Organization", "Policy"): "ENFORCES_POLICY",

    # === 문헌 / 작품 (자료 → 대상) ====================================
    ("Document", "Event"): "ABOUT_EVENT",      # 난중일기 -> 임진왜란
    ("Document", "Person"): "ABOUT_PERSON",    # 난중일기 -> 이순신

    ("Work", "Event"): "DEPICTS_EVENT",      
    ("Work", "Person"): "DEPICTS_PERSON",    

    # === 인물 ↔ 개념/물품 =============================================
    ("Person", "Concept"): "RELATED_CONCEPT",
    ("Person", "Object"): "RELATED_OBJECT",

    # === 네트워크(대칭 관계지만 단방향만 저장) ==========================
    ("Person", "Person"): "ASSOCIATED_WITH",
    ("Organization", "Organization"): "ASSOCIATED_WITH",
}


def canonicalize_pair(
    label1: str,
    id1: int,
    label2: str,
    id2: int,
) -> tuple[str, int, str, int, str]:
    """
    두 노드의 (라벨, article_id)를 받으면
    - 우리가 정의한 "정방향" (src_label, src_id, tgt_label, tgt_id)
    - 관계 타입 rel_type
    을 반환한다.

    1) (label1, label2)가 RELATION_TYPE_MAP에 있으면 그대로 사용
    2) 없으면 (label2, label1)를 찾아보고 있으면 방향을 뒤집어서 사용
    3) 둘 다 없으면 그냥 (label1 -> label2, "RELATED_TO") 로 처리
    """
    key = (label1, label2)
    if key in RELATION_TYPE_MAP:
        return label1, id1, label2, id2, RELATION_TYPE_MAP[key]

    rev_key = (label2, label1)
    if rev_key in RELATION_TYPE_MAP:
        return label2, id2, label1, id1, RELATION_TYPE_MAP[rev_key]

    # 정의 안 한 조합은 generic 관계로 처리
    return label1, id1, label2, id2, "RELATED_TO"


def create_text_edges(driver):
    """
    summary + contents 안에 다른 항목 title 이 등장하면 엣지 생성.

    - 중심 라벨들(사람/사건/지명/단체 + 개념/유적/물품/문헌/작품/제도/정책)을 대상으로 네트워크 구성
    - 제목 길이가 너무 짧은 건 스킵해서 노이즈 최소화
    """
    TARGET_LABELS = {
        "Person", "Event", "Place", "Organization",
        "Concept", "Heritage", "Object", "System",
        "Document", "Work", "Ritual", "Clothing", "Policy",
    }

    # 1) CSV에서 article_id, title, label, text 준비
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

        nodes.append(
            {
                "article_id": article_id,
                "title": title,
                "label": label,
                "text": text,
            }
        )

    # 2) 대상 라벨 필터링
    candidate_nodes = [
        n for n in nodes if n["label"] in TARGET_LABELS and n["title"]
    ]

    print(f"[TextEdge] 후보 노드 수: {len(candidate_nodes)}")

    with driver.session() as session:
        total_edges = 0

        # 3) N^2 탐색 (데이터 커지면 나중에 최적화 고려)
        for i, src in enumerate(candidate_nodes, start=1):
            src_raw_id = src["article_id"]
            src_raw_label = src["label"]
            src_text = src["text"]

            if not src_text:
                continue

            if i % 100 == 0:
                print(f"[TextEdge] 진행 중... {i}/{len(candidate_nodes)}")

            for tgt in candidate_nodes:
                tgt_raw_id = tgt["article_id"]
                tgt_raw_label = tgt["label"]

                if src_raw_id == tgt_raw_id:
                    continue

                tgt_title = tgt["title"]

                # 너무 짧은 제목은 노이즈라 스킵
                if len(tgt_title) < 2:
                    continue

                # 단순 포함 매칭
                if tgt_title in src_text:
                    (
                        src_label,
                        src_id,
                        tgt_label,
                        tgt_id,
                        rel_type,
                    ) = canonicalize_pair(
                        src_raw_label,
                        src_raw_id,
                        tgt_raw_label,
                        tgt_raw_id,
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
                        match_title=tgt_title,
                    )
                    total_edges += 1

        print(f"[TextEdge] 생성된 엣지 수: {total_edges}")

# ============================================================
# main
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
