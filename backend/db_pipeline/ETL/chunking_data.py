# db_pipeline/ETL/chunking_data.py

from typing import List, Dict
import tiktoken

# OpenAI text-embedding-3-small tokenizer
enc = tiktoken.encoding_for_model("text-embedding-3-small")

def count_tokens(text: str) -> int:
    return len(enc.encode(text))


def chunk_text(text: str, max_tokens: int = 500, overlap: int = 100) -> List[str]:
    """ 긴 본문을 토큰 단위로 청킹 """
    tokens = enc.encode(text)
    chunks = []

    start = 0
    end = max_tokens

    while start < len(tokens):
        chunk = enc.decode(tokens[start:end])
        chunks.append(chunk)

        # 다음 chunk를 위해 overlap 만큼 뒤로 물러서기
        start = end - overlap
        end = start + max_tokens

    return chunks


def chunk_dataframe(df):
    """
    df: category, title, summary, contents가 있는 DataFrame
    반환: [{"text": chunk_text, "metadata": {...}}]
    """
    results = []

    for _, row in df.iterrows():
        content = row["contents"]

        # contents를 chunk로 분할
        chunks = chunk_text(content)

        for idx, chunk in enumerate(chunks):
            meta = {
                "category": row["category"],
                "title": row["title"],
                "summary": row["summary"],
                "chunk_index": idx,
                "source": row["title"],      # 검색시 유용
                "token_length": count_tokens(chunk),
            }

            results.append({
                "text": chunk,
                "metadata": meta
            })

    return results
