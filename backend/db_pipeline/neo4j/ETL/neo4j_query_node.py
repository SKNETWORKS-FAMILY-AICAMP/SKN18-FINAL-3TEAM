import csv
import re
from pathlib import Path
from backend.db_pipeline.common.embedding_model import embed
from backend.db_pipeline.neo4j.services.neo4j_connection import get_driver

from backend.db_pipeline.common.config import (
    NEO4J_URI as URI,
    NEO4J_USER as USER,
    NEO4J_PASSWORD as PASSWORD,
    CATEGORY_LABEL_MAP,
    PERIOD_KEYWORDS,
    INPUT_CSV,
)


# ============================================================
# 공통: CSV 로딩
# ============================================================

def load_rows(csv_module, csv_path: Path):
    """create_nodes.py에서처럼 _article_id 포함해서 로딩."""
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            row["_article_id"] = i
            yield row


# 연도 추출
def extract_years(text: str | None) -> list[int]:
    if not text:
        return []
    matches = re.findall(r"(1[0-9]{3}|20[0-9]{2})", text)
    years: list[int] = []
    for m in matches:
        y = int(m)
        if 1000 <= y <= 2100:
            years.append(y)
    return years


def extract_period_text(text: str | None) -> str | None:
    if not text:
        return None
    for kw in PERIOD_KEYWORDS:
        if kw in text:
            return kw
    return None


def create_constraints(driver):
    with driver.session() as session:
        # 연도 노드 제약
        session.run("""
        CREATE CONSTRAINT year_value_unique IF NOT EXISTS
        FOR (y:Year) REQUIRE y.value IS UNIQUE
        """)

        # 각 라벨별 article_id 유니크
        for label in set(CATEGORY_LABEL_MAP.values()):
            session.run(f"""
            CREATE CONSTRAINT article_id_unique_{label} IF NOT EXISTS
            FOR (n:{label}) REQUIRE n.article_id IS UNIQUE
            """)


def generate_summary_embedding(summary: str) -> list[float] | None:
    """
    summary 텍스트만 임베딩.
    summary가 비어있으면 None.
    """
    summary = (summary or "").strip()
    if not summary:
        return None

    return embed(summary)


def create_nodes(csv_module, driver, csv_path: Path):
    with driver.session() as session:
        for row in load_rows(csv_module, csv_path):
            category = (row.get("category") or "").strip()
            title = (row.get("title") or "").strip()
            summary = (row.get("summary") or "").strip()
            contents = (row.get("contents") or "").strip()

            label = CATEGORY_LABEL_MAP.get(category)
            if not label:
                print(f"[WARN] Unknown category: {category}, title={title}")
                continue

            text_for_extract = summary or contents
            years = extract_years(text_for_extract)
            period_text = extract_period_text(text_for_extract)
            main_year = years[0] if years else None

            # 공통 필드 (contents는 Neo4j에 저장하지 않음)
            props: dict = {
                "article_id": int(row["_article_id"]),
                "category": category,
                "title": title,
                "summary": summary,
            }

            if main_year:
                props["main_year"] = main_year
            if period_text:
                props["period_text"] = period_text

            # 카테고리별 연도 필드
            if label == "Person":
                if len(years) >= 1:
                    props["birth_year"] = years[0]
                if len(years) >= 2:
                    props["death_year"] = years[1]

            elif label == "Event":
                if len(years) >= 1:
                    props["start_year"] = years[0]
                if len(years) >= 2:
                    props["end_year"] = years[1]

            elif label in ("System", "Policy"):
                if len(years) >= 1:
                    props["established_year"] = years[0]
                if len(years) >= 2:
                    props["abolished_year"] = years[1]

            elif label in ("Document", "Work"):
                if len(years) >= 1:
                    props["created_year"] = years[0]

            elif label == "Heritage":
                if len(years) >= 1:
                    props["build_year"] = years[0]
                if len(years) >= 2:
                    props["rebuild_year"] = years[1]

            elif label == "Ritual":
                if len(years) >= 1:
                    props["start_year"] = years[0]
                if len(years) >= 2:
                    props["end_year"] = years[1]

            elif label in ("Object", "Clothing"):
                if len(years) >= 1:
                    props["period_start"] = years[0]
                if len(years) >= 2:
                    props["period_end"] = years[1]

            elif label == "Organization":
                if len(years) >= 1:
                    props["founded_year"] = years[0]
                if len(years) >= 2:
                    props["dissolved_year"] = years[1]

            elif label == "Place":
                if len(years) >= 1:
                    props["exist_start_year"] = years[0]
                if len(years) >= 2:
                    props["exist_end_year"] = years[1]

            # 🔹 summary 임베딩 생성
            embedding = generate_summary_embedding(summary)

            # Neo4j에 저장
            session.run(
                f"""
                MERGE (n:{label} {{article_id: $article_id}})
                SET n += $props
                SET n.embedding = $embedding
                """,
                article_id=props["article_id"],
                props=props,
                embedding=embedding,   # None이면 속성 저장 안 됨
            )


def run_node_job(csv_module=csv, csv_path: Path | None = None):
    driver = get_driver()
    try:
        create_constraints(driver)
        target_path = Path(csv_path) if csv_path else Path(INPUT_CSV)
        create_nodes(csv_module, driver, target_path)
        print("노드 생성 + summary 임베딩 완료.")
    finally:
        driver.close()

if __name__ == "__main__":
    csv.field_size_limit(2_147_483_647)
    run_node_job(csv)
