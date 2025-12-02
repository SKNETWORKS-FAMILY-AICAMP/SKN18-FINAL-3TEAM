"""
LangGraph 온톨로지 추론 시스템 초기화

환경변수 로드 및 LangSmith 프로젝트 설정
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)  # override=True: 기존 환경변수도 .env로 덮어쓰기

# LangSmith 프로젝트 이름 설정 (랭그래프 전용)
os.environ["LANGCHAIN_PROJECT"] = "Korean-History-LangGraph"
