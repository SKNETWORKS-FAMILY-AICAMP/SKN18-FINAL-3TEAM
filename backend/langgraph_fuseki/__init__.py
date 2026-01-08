"""
HistoK LangGraph Fuseki

Fuseki 기반 LangGraph 온톨로지 추론 시스템
환경변수 로드 및 LangSmith 프로젝트 설정은 config.py에서 자동으로 처리됩니다.

실행 방법:
    python -m backend.langgraph_fuseki.main
"""

# config.py를 import하면 자동으로 환경변수 및 LangSmith 설정이 로드됨
# 상대 import 사용 (실행 위치와 무관하게 작동)
from .config import (
    PACKAGE_DIR,
    PROJECT_ROOT,
    TTL_PATH,
    FUSEKI_URL,
    USE_PGVECTOR,
)

__all__ = [
    "PACKAGE_DIR",
    "PROJECT_ROOT",
    "TTL_PATH",
    "FUSEKI_URL",
    "USE_PGVECTOR",
]
