import pandas as pd
from embedding import embedding_model
from create_pgvector import create_pgvector_store, ensure_table
from chunking import splitter_chunks


CONNECTION_STRING = "postgresql://admin:admin123@localhost:5432/vectordb"
TABLE_NAME = "encykorea_cleaned6"
DIM = 1536

def batch_iter(items, batch_size):
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]

def run():
    ensure_table(CONNECTION_STRING, TABLE_NAME, dim=DIM)
    store = create_pgvector_store(CONNECTION_STRING, TABLE_NAME, embedding_model())

    trimmed_docs, BATCH = splitter_chunks()  # 청킹 호출

    for batch in batch_iter(trimmed_docs, batch_size=BATCH):
        texts = [doc.page_content for doc in batch]
        metas = [doc.metadata for doc in batch]
        store.add_texts(texts, metas)

    print("insert 완료")

if __name__ == "__main__":
    run()
