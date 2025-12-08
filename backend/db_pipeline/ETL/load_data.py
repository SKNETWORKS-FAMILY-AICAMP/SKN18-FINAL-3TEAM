from embedding import embedding_model
from create_pgvector import create_pgvector_store, ensure_table
from chunking import chunk_text, batch_iter  # 또는 파일 내 정의
import pandas as pd

CONN = "postgresql://admin:admin123@localhost:5432/vectordb"
TABLE = "encykorea_cleaned6"
DIM = 1536

# 본문 청크 설정
CHUNK = 5000
OVERLAP = 300
MAX = 65000
BATCH = 200

# 1) 데이터 로드
df = pd.read_csv("./backend/db_pipeline/data/encykorea_cleaned6.csv")
df["contents"] = df["contents"].fillna("").astype(str)
rows = df.to_dict("records")

# 2) 청크 생성
chunked = []
for i, row in enumerate(rows):
    metas = {k: v for k, v in row.items() if k != "contents"}
    for j, chunk in enumerate(chunk_text(row["contents"], max_chars=CHUNK, overlap=OVERLAP)):
        max_chunk_len = MAX - len(metas.get("title", "")) - len(metas.get("summary", ""))
        if max_chunk_len > 0 and len(chunk) > max_chunk_len:
            chunk = chunk[:max_chunk_len]
        item = {"chunk": chunk, "row_idx": i, "chunk_idx": j}
        item.update(metas)
        chunked.append(item)

# 3) 테이블 준비 + 스토어 초기화
ensure_table(CONN, TABLE, dim=DIM)
store = create_pgvector_store(CONN, TABLE, embedding_model())

# 4) 배치 적재
for batch in batch_iter(chunked, batch_size=BATCH):
    texts = [b["chunk"] for b in batch]
    metas = [{k: v for k, v in b.items() if k not in ("chunk", "row_idx", "chunk_idx")} for b in batch]
    store.add_texts(texts, metas)

print("insert 완료")
