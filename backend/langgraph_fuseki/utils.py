"""
공통 유틸리티 함수
"""

import os

# config.py를 import하면 자동으로 환경변수가 로드됨
# (config.py에서 load_dotenv가 실행됨)
from backend.langgraph_fuseki.config import PROJECT_ROOT


def get_openai_model() -> str:
    """
    현재 설정된 OpenAI 모델 반환
    
    Returns:
        모델 이름 (.env에서 로드)
    
    Note:
        config.py를 import하면 자동으로 .env 파일이 로드되므로
        별도로 load_dotenv를 호출할 필요가 없습니다.
    """
    # config.py가 이미 .env를 로드했으므로 직접 읽기만 하면 됨
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

