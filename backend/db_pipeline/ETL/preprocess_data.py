# 데이터 전처리
import pandas as pd
import re

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    # 원본 보호용 복사
    df_ = df.copy()

    # 필수 컬럼 체크 (contents는 반드시 있어야 한다고 가정)
    required_cols = ["title", "summary", "contents"]
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
        # 중복 공백 정리
        df_[col] = df_[col].str.replace(r"\s+", " ", regex=True).str.strip()

    return df_
