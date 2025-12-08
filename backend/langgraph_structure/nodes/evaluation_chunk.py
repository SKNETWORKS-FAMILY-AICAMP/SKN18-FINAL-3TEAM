# from backend.db_pipeline.ETL.embedding import embeddings_model
# from backend.db_pipeline.ETL.custom_pgvector import CustomPGVector
# from backend.db_pipeline.ETL.config import POSTGRES_CONN_STR

# store = CustomPGVector(
#     conn_str=POSTGRES_CONN_STR,
#     embedding_fn=embeddings_model,
#     table="encykorea_cleaned6",
# )

# docs = store.similarity_search("검색하고 싶은 질문", k=5)

# test_db_conn.py
import psycopg2
from backend.db_pipeline.ETL.config import POSTGRES_CONN_STR

with psycopg2.connect(POSTGRES_CONN_STR) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM my_vectors;")
        print("my_vectors row 수:", cur.fetchone()[0])
