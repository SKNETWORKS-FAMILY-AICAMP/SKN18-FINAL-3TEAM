# backend/db_pipeline/main.py

from ETL.load_data import load_raw_data
from ETL.preprocess_data import preprocess_data
from ETL.chunking_data import chunk_dataframe
from services.vector_store import create_pgvector_store
from services.embedding_model import get_embedding
from services.db_connection import prepare_vectordb
from config import POSTGRES_CONN_STR

def run():

    prepare_vectordb(POSTGRES_CONN_STR)
    df = load_raw_data()
    df = preprocess_data(df)
    chunks = chunk_dataframe(df)

    texts = [c["text"] for c in chunks]
    metas = [c["metadata"] for c in chunks]

    store = create_pgvector_store(POSTGRES_CONN_STR, "korean_history", get_embedding())
    store.add_texts(texts, metas)

    print("전체 청킹 + 임베딩 + DB 저장 완료!")

if __name__ == "__main__":
    run()
