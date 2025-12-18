"""
vectordb/neo4j 모두에서 참조하는 공통 설정 파일
"""
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

# --------------------------------------
# DATABASE SETTINGS
# --------------------------------------
# PostgreSQL Info
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

POSTGRES_CONN_STR = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Neo4j Info
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


# --------------------------------------
# EMBEDDING MODEL SETTINGS
# --------------------------------------
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536


# --------------------------------------
# OPENAI API KEY
# --------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 임베딩 모듈에 기존 이름을 유지하기 위한 alias
OPENAPI_API_KEY = OPENAI_API_KEY

# --------------------------------------
# DATA PATH SETTINGS
# --------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
INPUT_CSV = os.path.join(DATA_DIR, "encykorea_cleaned6.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "transformed_chunks.csv")

# --------------------------------------
# TABLE / COLLECTION SETTINGS (고정)
# --------------------------------------
HISTORY_TABLE_NAME = "korean_history"
TITLE_TABLE_NAME = "title_embeddings"


#--------------------------------------
# LABEL_MAP
# --------------------------------------
CATEGORY_LABEL_MAP = {
        "인물": "Person",
        "사건": "Event",
        "문헌": "Document",
        "제도": "System",
        "유적": "Heritage",
        "개념": "Concept",
        "물품": "Object",
        "단체": "Organization",
        "지명": "Place",
        "작품": "Work",
        "의례·행사": "Ritual",
        "의복": "Clothing",
        "정책": "Policy",
    }

PERIOD_KEYWORDS = [
        "조선 전기", "조선 중기", "조선 후기",
        "조선 초", "조선 말",
        "고려 전기", "고려 후기",
        "고려 말", "고려 초",
        "세종 대", "영조 대", "정조 대",
        "일제 강점기", "일제강점기",
    ]