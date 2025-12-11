# db_pipeline/config.py
import os
from dotenv import load_dotenv

load_dotenv(override=True,dotenv_path="backend/langgraph_structure/nodes/.env")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

POSTGRES_CONN_STR = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# 임베딩 모델 설정
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# 데이터 경로 설정
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INPUT_CSV = os.path.join(DATA_DIR, "encykorea_cleaned6.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "transformed_chunks.csv")
