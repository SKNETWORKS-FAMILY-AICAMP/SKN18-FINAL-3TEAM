from pathlib import Path
from typing import Union
import pandas as pd

from backend.db_pipeline.common.config import INPUT_CSV


def load_raw_data(
    csv_path: Union[str, Path] = INPUT_CSV,
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
