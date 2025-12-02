"""
공통 유틸리티 함수
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def load_env_config():
    """
    .env 파일 로드
    
    .env 파일의 OPENAI_MODEL을 사용합니다.
    """
    # 프로젝트 루트의 .env 파일 경로
    env_path = Path(__file__).parent.parent.parent / ".env"
    
    # .env 파일 로드 (기존 환경변수도 덮어쓰기)
    load_dotenv(env_path, override=True)
    
    return os.getenv("OPENAI_MODEL")


def get_openai_model() -> str:
    """
    현재 설정된 OpenAI 모델 반환
    
    Returns:
        모델 이름 (.env에서 로드)
    """
    # 환경변수 로드 (이미 로드되었어도 다시 확인)
    return load_env_config()

