# db_pipeline/ETL/chunking_data.py

from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter

# -------------------------------------------------------------------
# 1) 실무에서 가장 흔하게 쓰는 LangChain 청킹 전략:
#    RecursiveCharacterTextSplitter
#    - 문단 / 줄바꿈 / 공백 위주로 자연스럽게 끊어줌
#    - chunk_size, chunk_overlap만 조절하면 됨
# -------------------------------------------------------------------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,        # 대략 800~1200 정도를 많이 사용
    chunk_overlap=100,      # 앞/뒤로 겹치게 해서 문맥 보존
    separators=["\n\n", "\n", " ", ""],  # 우선순위: 문단 > 줄 > 공백 > 문자
)


def count_tokens(text: str) -> int:
    """
    엄밀한 '토큰 수'가 아니라 대략적인 길이 정보용.
    비용/컨텍스트 정확 계산이 필요하면 tiktoken 을 나중에만 붙여도 됩니다.
    """
    return len(text.split())  # 대략적인 단어 수


def chunk_text(text: str) -> List[str]:
    """긴 본문을 RecursiveCharacterTextSplitter 로 청킹"""
    chunks = text_splitter.split_text(text)

    # 공백만 있는 chunk 제거
    chunks = [c for c in chunks if c.strip()]

    return chunks


def chunk_dataframe(df):
    """
    df: category, title, summary, contents 가 있는 DataFrame
    반환: [{"text": chunk_text, "metadata": {...}}]
    """
    results = []

    # 성능상 iterrows()보다 itertuples()이 빠릅니다.
    for row in df.itertuples(index=False):
        content = getattr(row, "contents", "") or ""

        # contents를 chunk로 분할
        chunks = chunk_text(content)

        for idx, chunk in enumerate(chunks):
            meta = {
                "category": getattr(row, "category", None),
                "title": getattr(row, "title", None),
                "summary": getattr(row, "summary", None),
                "chunk_index": idx,
                "source": getattr(row, "title", None),  # 검색시 유용
                "token_length": count_tokens(chunk),
            }

            results.append({
                "text": chunk,
                "metadata": meta,
            })

    return results
