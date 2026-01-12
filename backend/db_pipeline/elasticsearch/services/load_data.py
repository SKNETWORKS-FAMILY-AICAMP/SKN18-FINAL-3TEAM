from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from pathlib import Path
from typing import Union, List
import pandas as pd


def load_raw_data(
    csv_path: Union[str, Path],
    *,
    encoding: str = "utf-8",
    on_bad_lines: str = "skip",
    engine: str = "python",
    quoting=None,
):
    """
    CSV 파일에서 원본 데이터 로드 (ETL 공용)
    - field_size_limit 확장
    - 잘못된 행 건너뛰기 기본값 유지
    - encoding 등 호출처에서 조정 가능
    """
    import sys
    import csv

    # pandas 기본 quoting 값과 동일하게 설정 (None이면 QUOTE_MINIMAL)
    quoting = quoting or csv.QUOTE_MINIMAL

    csv_path = Path(csv_path).resolve()
    print(f"CSV 파일 읽기: {csv_path}")

    # CSV 필드 크기 제한 증가
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = int(max_int / 10)

    df = pd.read_csv(
        csv_path,
        encoding=encoding,
        quoting=quoting,
        on_bad_lines=on_bad_lines,  # 잘못된 행 건너뛰기
        engine=engine,  # Python 엔진 사용 (더 유연한 파싱)
    )
    print(f"  └─ 로드된 행 수: {len(df):,}개")
    return df


def _safe_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def dataframe_to_documents(df: pd.DataFrame) -> List[Document]:
    docs: List[Document] = []
    for idx, row in df.iterrows():
        title = _safe_text(row.get("title", ""))
        contents = _safe_text(row.get("contents", ""))

        if not contents:
            continue

        metadata = {
            "category": _safe_text(row.get("category", "")),
            "title": title,
            "source": "encykorea_cleaned6.csv",
            "row_id": int(idx) if isinstance(idx, int) else str(idx),
        }
        docs.append(Document(page_content=f"내용: {contents}", metadata=metadata))
    return docs


def split_documents(docs: List[Document]) -> List[Document]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600, chunk_overlap=120)
    docs_by_splitter = text_splitter.split_documents(docs)
    return docs_by_splitter


def load_and_split_data():
    csv_path = Path("./data/encykorea_cleaned6.csv")
    df = load_raw_data(csv_path)
    docs = dataframe_to_documents(df)
    docs_by_splitter = split_documents(docs)

    return docs_by_splitter
