import pandas as pd
from backend.db_pipeline.common.embedding_model import get_embedding

# 본문 청크 설정
CHUNK = 5000        # 한 청크 길이
OVERLAP = 300       # 청크 간 겹침
MAX = 65000         # VARCHAR 안전 마진 (title+summary+chunk)
BATCH = 200         # gRPC 메시지 크기 회피용 insert 배치 크기

def split_contents(text: str):
    # 본문을 CHUNK 길이로 자르고 OVERLAP만큼 겹치게 슬라이드
    if not text:
        return [""]
    chunks = []
    start = 0
    step = max(1, CHUNK - OVERLAP)
    while start < len(text):
        end = min(start + CHUNK, len(text))
        chunks.append(text[start:end])
        start += step
    return chunks

def insert_data(collection, csv_path="data/encykorea_cleaned.csv"):
    # CSV 읽기
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    categories = df["category"].fillna("").tolist()
    titles    = df["title"].fillna("").tolist()
    summaries = df["summary"].fillna("").tolist()
    contents  = df["contents"].fillna("").tolist()

    # 청크 단위로 행 펼치기
    rows = []
    for cat, title, summary, content in zip(categories, titles, summaries, contents):
        base = f"{title} {summary} "
        available = max(0, MAX - len(base))  # chunk에 쓸 수 있는 최대 길이
        for chunk in split_contents(content):
            trimmed = chunk[:available]
            embed_text = (base + trimmed)[:MAX]  # 만일을 대비해 MAX까지 자름
            rows.append((cat, title, summary, trimmed, embed_text))

    # 임베딩 모델 (싱글톤)
    embedding_model = get_embedding()

    inserted = 0
    # 배치 단위 insert로 gRPC 메시지 크기 제한 회피
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        cats, ts, sums, conts, embed_inputs = map(list, zip(*batch))
        embeddings = embedding_model.embed_documents(embed_inputs)
        data = [cats, ts, sums, conts, embeddings]
        collection.insert(data)
        inserted += len(batch)

    collection.flush()
    print(f"{inserted}개 청크 삽입 완료 (원본 문서 수: {len(df)})")
