from backend.db_pipeline.neo4j.services.neo4j_connection import get_driver
from backend.db_pipeline.neo4j.services.neo4j_service import run_cypher, serialize_records
from backend.langgraph_structure1.graphdb.embedding_utils import get_query_embedding, add_similarity


def run_gain(ko_question: str, cypher: str):
    driver = get_driver()
    try:
        q_emb = get_query_embedding(ko_question)

        raw = run_cypher(driver, cypher)
        ser = serialize_records(raw)

        add_similarity(ser, q_emb)

        grouped = {}

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

        for cat, nodes in grouped.items():
            nodes.sort(key=lambda x: (x["similarity"] or 0), reverse=True)
            summary_nodes.extend(nodes[:3])

        summary_nodes.sort(key=lambda x: (x["similarity"] or 0), reverse=True)

        return summary_nodes

    finally:
        driver.close()
