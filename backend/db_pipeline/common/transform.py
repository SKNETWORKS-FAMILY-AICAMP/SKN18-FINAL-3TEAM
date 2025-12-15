"""
Transform: CSV 데이터 정규화 + 청킹

1. Extract: encykorea_cleaned6.csv 읽기
2. Normalize: 데이터 정규화 (한자 제거, 괄호 제거, 공백 정리)
3. Chunking: contents 긴 텍스트 청킹 (800자, 100자 오버랩)
4. Output: transformed_chunks.csv 생성
"""

from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pandas as pd
from backend.db_pipeline.common.config import INPUT_CSV

def split_chunk():
    # 청킹 파라미터
    CHUNK_SIZE = 600  # 800자
    OVERLAP_SIZE = 100  # 100자

    # RecursiveCharacterTextSplitter 초기화
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=OVERLAP_SIZE,
        separators=["\n\n", "\n", " ", ""],  # 우선순위: 문단 > 줄 > 공백 > 문자
    )

    return text_splitter


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    # 원본 보호용 복사
    df_ = df.copy()

    # 필수 컬럼 체크 (category, title, summary, contents는 반드시 있어야 한다고 가정)
    required_cols = ["category", "title", "summary", "contents"]
    missing = [col for col in required_cols if col not in df_.columns]
    if missing:
        raise KeyError(f"입력 DataFrame에 '{', '.join(missing)}' 컬럼이 없습니다.")

    # 결측치 처리 및 문자열 변환
    df_[required_cols] = df_[required_cols].fillna("").astype(str)

    # contents 기준으로 완전히 빈 행 제거
    df_ = df_[df_["contents"].str.strip() != ""].reset_index(drop=True)

    # 정규식 패턴: 확장 한자 포함, 모든 괄호와 내용 제거
    han_pattern = r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]"
    paren_pattern = r"\([^)]*\)"

    for col in required_cols:
        # 한자 제거
        df_[col] = df_[col].str.replace(han_pattern, "", regex=True)
        # 괄호 및 괄호 내부 내용 제거
        df_[col] = df_[col].str.replace(paren_pattern, "", regex=True)
        # 연속 공백 → 단일 공백
        df_[col] = df_[col].str.replace(r'\s+', ' ', regex=True)
        # Zero-width characters 제거
        df_[col] = df_[col].str.replace(r'[\u200b-\u200d\ufeff]', '', regex=True)
        # BOM 제거
        df_[col] = df_[col].str.replace('\ufeff', '', regex=False)
        # 앞뒤 공백 제거
        df_[col] = df_[col].str.strip()

    return df_


def count_tokens(text: str) -> int:
    """
    엄밀한 '토큰 수'가 아니라 대략적인 길이 정보용.
    비용/컨텍스트 정확 계산이 필요하면 tiktoken 을 나중에만 붙여도 됩니다.
    """
    return len(text.split())  # 대략적인 단어 수


def chunk_text(text: str, text_splitter: RecursiveCharacterTextSplitter) -> List[str]:
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
        text_splitter = split_chunk()
        chunks = chunk_text(content,text_splitter)

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


def transform_csv_to_chunks() -> pd.DataFrame:
    """
    CSV 데이터를 읽어 정규화 + 청킹하여 DataFrame으로 변환

    Returns:
        DataFrame with columns: text, category, title, summary, chunk_index, source, token_length
    """
    print(f"CSV 파일 읽기: {INPUT_CSV}")
    
    # CSV를 DataFrame으로 읽기
    df = pd.read_csv(INPUT_CSV, encoding='utf-8')
    
    # 전처리
    print("데이터 전처리 중...")
    df_processed = preprocess_data(df)
    print(f"  └─ 처리된 문서 수: {len(df_processed):,}개")
    
    # 청킹
    print("텍스트 청킹 중...")
    results = chunk_dataframe(df_processed)
    print(f"  └─ 총 청크 수: {len(results):,}개")

    # 결과를 DataFrame으로 변환
    chunks_df = pd.DataFrame([
        {
            "text": item["text"],
            "category": item["metadata"]["category"],
            "title": item["metadata"]["title"],
            "summary": item["metadata"]["summary"],
            "chunk_index": item["metadata"]["chunk_index"],
            "source": item["metadata"]["source"],
            "token_length": item["metadata"]["token_length"],
        }
        for item in results
    ])

    return chunks_df


def save_chunks_to_csv(chunks_df: pd.DataFrame, output_path: str):
    """청킹된 데이터를 CSV로 저장"""
    print(f"\nCSV 파일 저장 중: {output_path}")
    chunks_df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"Transform 완료")
    print(f"  └─ 출력 파일: {output_path}")
