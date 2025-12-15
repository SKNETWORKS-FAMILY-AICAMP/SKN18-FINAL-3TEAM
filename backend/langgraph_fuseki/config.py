"""
HistoK LangGraph Fuseki 설정 및 경로 관리

이 파일은 Fuseki 기반 LangGraph의 모든 경로를 중앙에서 관리합니다.

실행 방법:
    python -m backend.langgraph_fuseki.main
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# 경로 설정 (데이터 파일용 - __file__ 기반)
# ============================================================
PACKAGE_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# TTL 파일 경로
ONTOLOGY_DIR = PACKAGE_DIR / "ontology"
INSTANCES_DIR = ONTOLOGY_DIR / "instances"
TTL_PATH = INSTANCES_DIR / "korean_history_normalized.ttl"
PROPERTY_GROUPS_PATH = INSTANCES_DIR / "property_groups.json"

# ============================================================
# 환경변수 로드
# ============================================================
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH, override=True)

# ============================================================
# 환경변수 설정
# ============================================================
# LangSmith 프로젝트 이름 설정
os.environ["LANGCHAIN_PROJECT"] = "HistoK-LangGraph-Fuseki"

# Fuseki 설정
FUSEKI_URL = os.getenv("FUSEKI_URL", "http://localhost:3030/korean-history")

# pgvector 사용 여부
USE_PGVECTOR = os.getenv("USE_PGVECTOR", "true").lower() == "true"

# ============================================================
# 추론 결과 저장 경로 (선택사항)
# ============================================================
INFERENCE_OUTPUT_DIR = PACKAGE_DIR / "outputs" / "inference"
INFERENCE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
