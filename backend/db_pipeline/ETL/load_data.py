# 데이터 로딩
import pandas as pd

PATH = "data/encykorea_cleaned6.csv"

def load_raw_data():
    return pd.read_csv(PATH)
