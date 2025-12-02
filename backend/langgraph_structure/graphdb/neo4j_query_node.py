import csv
import re
from neo4j import GraphDatabase
from pathlib import Path   # ✅ 추가

import sys
csv.field_size_limit(2_147_483_647)

# 프로젝트 루트 기준 경로 계산 (backend/langgraph_structure/graphdb/ 기준 3단계 위)
BASE_DIR = Path(__file__).resolve().parents[3]

# --- Neo4j 접속 정보 ---
URI = "neo4j://localhost:7687"
USER = "neo4j"
PASSWORD = "skn183final"

# --- CSV 경로 ---
CSV_PATH = BASE_DIR / "infra" / "neo4j" / "import" / "encykorea_cleaned6.csv"


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

# 시기 텍스트 추출용
PERIOD_KEYWORDS = [
    "조선 전기", "조선 중기", "조선 후기",
    "조선 초", "조선 말",
    "고려 전기", "고려 후기",
    "고려 말", "고려 초",
    "세종 대", "영조 대", "정조 대",
    "일제 강점기", "일제강점기",
]


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


def load_rows():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            row["_article_id"] = i
            yield row


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


def create_nodes(driver):
    with driver.session() as session:
        for row in load_rows():
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

            # 공통 필드
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

            session.run(
                f"""
                MERGE (n:{label} {{article_id: $article_id}})
                SET n += $props
                """,
                article_id=props["article_id"],
                props=props,
            )


def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    try:
        create_constraints(driver)
        create_nodes(driver)
        print("노드 생성 완료.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
