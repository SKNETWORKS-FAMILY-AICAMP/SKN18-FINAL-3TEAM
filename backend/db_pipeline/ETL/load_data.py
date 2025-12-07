# 데이터 로딩
import pandas as pd
import os

PATH = "data/encykorea_cleaned6.csv"

def load_raw_data(path: str = PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path,encoding="utf-8-sig")