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

# ============================================================
# 가중치 설정 (모두 기본값 1.0)
# ============================================================

# Thread 타입별 가중치 (Parallel Knowledge Retrieval과 Path Evidence Aggregator에서 공통 사용)
THREAD_WEIGHT_OUTGOING_RELATIONS = float(os.getenv("THREAD_WEIGHT_OUTGOING_RELATIONS", "1.0"))
THREAD_WEIGHT_INCOMING_RELATIONS = float(os.getenv("THREAD_WEIGHT_INCOMING_RELATIONS", "1.0"))
THREAD_WEIGHT_CONNECTED_ENTITIES = float(os.getenv("THREAD_WEIGHT_CONNECTED_ENTITIES", "1.0"))
THREAD_WEIGHT_ENTITY_PROPERTIES = float(os.getenv("THREAD_WEIGHT_ENTITY_PROPERTIES", "1.0"))
THREAD_WEIGHT_TYPE_AND_SUMMARY = float(os.getenv("THREAD_WEIGHT_TYPE_AND_SUMMARY", "1.0"))

# 쿼리 엔티티 매칭 부스트 값
QUERY_ENTITY_MATCH_BOOST_EXACT = float(os.getenv("QUERY_ENTITY_MATCH_BOOST_EXACT", "1.0"))
QUERY_ENTITY_MATCH_BOOST_PARTIAL = float(os.getenv("QUERY_ENTITY_MATCH_BOOST_PARTIAL", "1.0"))
QUERY_ENTITY_MATCH_BOOST_NORMALIZED = float(os.getenv("QUERY_ENTITY_MATCH_BOOST_NORMALIZED", "1.0"))

# 쿼리 엔티티와 매칭되지 않은 경우 페널티
THREAD_TYPE_PENALTY_NO_MATCH = float(os.getenv("THREAD_TYPE_PENALTY_NO_MATCH", "1.0"))

# Semantic Expander 관련 설정
SEMANTIC_EXPANDER_TOP_N = int(os.getenv("SEMANTIC_EXPANDER_TOP_N", "30"))

# Semantic Expander 확장 방법별 가중치 (기본값: 모두 1.0)
FIXED_SCORE_CAUSAL_CHAIN = float(os.getenv("FIXED_SCORE_CAUSAL_CHAIN", "1.0"))
FIXED_SCORE_TEMPORAL = float(os.getenv("FIXED_SCORE_TEMPORAL", "1.0"))
FIXED_SCORE_PGVECTOR = float(os.getenv("FIXED_SCORE_PGVECTOR", "1.0"))
