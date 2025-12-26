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
# 가중치 설정 (Quick Win 실험 결과 기반 최적화)
# ============================================================
# 실험 근거: 300개 케이스 분석 (2024-12-26)
# - Thread incoming 제거: +1.7%p 개선 (11승 4패)
# - Normalized + Partial 강화: intent와 accuracy 균형
# - Semantic Expander 비활성화: +20%p 개선 (baseline 최적)
#
# 자세한 내용: backend/ragas/ontology_evaluate/data/quick_win/ALL_WEIGHT_EXPERIMENT_RESULTS.md
# ============================================================

# Thread 타입별 가중치 (Parallel Knowledge Retrieval과 Path Evidence Aggregator에서 공통 사용)
THREAD_WEIGHT_OUTGOING_RELATIONS = float(os.getenv("THREAD_WEIGHT_OUTGOING_RELATIONS", "1.0"))
THREAD_WEIGHT_INCOMING_RELATIONS = float(os.getenv("THREAD_WEIGHT_INCOMING_RELATIONS", "0.0"))  # ★ Quick Win: Intent 강화를 위해 비활성화
THREAD_WEIGHT_CONNECTED_ENTITIES = float(os.getenv("THREAD_WEIGHT_CONNECTED_ENTITIES", "1.0"))
THREAD_WEIGHT_ENTITY_PROPERTIES = float(os.getenv("THREAD_WEIGHT_ENTITY_PROPERTIES", "1.0"))
THREAD_WEIGHT_TYPE_AND_SUMMARY = float(os.getenv("THREAD_WEIGHT_TYPE_AND_SUMMARY", "1.0"))

# 쿼리 엔티티 매칭 부스트 값
# ★ Quick Win: Normalized(정확성) + Partial(의도) 상호 보완
QUERY_ENTITY_MATCH_BOOST_EXACT = float(os.getenv("QUERY_ENTITY_MATCH_BOOST_EXACT", "1.0"))
QUERY_ENTITY_MATCH_BOOST_PARTIAL = float(os.getenv("QUERY_ENTITY_MATCH_BOOST_PARTIAL", "1.5"))  # ★ Intent 보존 강화
QUERY_ENTITY_MATCH_BOOST_NORMALIZED = float(os.getenv("QUERY_ENTITY_MATCH_BOOST_NORMALIZED", "1.5"))  # ★ Triple 정확도 강화

# 쿼리 엔티티와 매칭되지 않은 경우 페널티
THREAD_TYPE_PENALTY_NO_MATCH = float(os.getenv("THREAD_TYPE_PENALTY_NO_MATCH", "1.0"))

# Semantic Expander 관련 설정
SEMANTIC_EXPANDER_TOP_N = int(os.getenv("SEMANTIC_EXPANDER_TOP_N", "30"))

# Semantic Expander 확장 방법별 가중치
# ★ Quick Win: 모든 확장 비활성화 (baseline이 +20%p 우수)
FIXED_SCORE_CAUSAL_CHAIN = float(os.getenv("FIXED_SCORE_CAUSAL_CHAIN", "0.0"))  # ★ 비활성화
FIXED_SCORE_TEMPORAL = float(os.getenv("FIXED_SCORE_TEMPORAL", "0.0"))  # ★ 비활성화
FIXED_SCORE_PGVECTOR = float(os.getenv("FIXED_SCORE_PGVECTOR", "0.0"))  # ★ 비활성화

# ============================================================
# 쿼리 타입별 동적 RAG 설정 (LANGGRAPH_DYNAMIC_CONFIG_GUIDE.md 기반)
# ============================================================
# 실험 근거: 300개 케이스, 쿼리 타입별 메트릭 분석 (2024-12-26)
# - factual: Intent 손실 최대 (-0.41), 정확성 최우선
# - causal: 인과관계 정보 중요 (+0.23), 선택적 확장
# - comparative: 관계 구조 손실 방지 (-0.38), 비활성화 권장
# - deep_analysis: Intent 손실 최소 (-0.11), 폭넓은 확장
#
# 자세한 내용: backend/ragas/ontology_evaluate/docs/LANGGRAPH_DYNAMIC_CONFIG_GUIDE.md
# ============================================================

QUERY_TYPE_CONFIGS = {
    "factual": {
        "semantic_expander": {
            "temporal": False,
            "causal_chain": False,
            "pgvector": False
        },
        "thread_weights": {
            "outgoing_relations": 0.0,  # Intent 손실 방지를 위해 제거
            "incoming_relations": 1.0,
            "connected_entities": 1.0,
            "entity_properties": 1.0,
            "type_and_summary": 1.0
        },
        "entity_boost": "normalized",  # triple_validity 1.0 (완벽한 정확성)
        "description": "정확한 단답형, Intent 최우선"
    },
    "causal": {
        "semantic_expander": {
            "temporal": False,
            "causal_chain": True,  # 인과관계만 확장 (+0.23)
            "pgvector": False
        },
        "thread_weights": {
            "outgoing_relations": 1.0,
            "incoming_relations": 0.0,  # Intent 보존 향상 (+0.04)
            "connected_entities": 1.0,
            "entity_properties": 1.0,
            "type_and_summary": 1.0
        },
        "entity_boost": "partial",  # 다양한 관계 정보 허용 (intent 0.58)
        "description": "원인-결과 관계, 선택적 확장"
    },
    "comparative": {
        "semantic_expander": {
            "temporal": False,
            "causal_chain": False,
            "pgvector": False
        },
        "thread_weights": {
            "outgoing_relations": 0.0,  # 관계 손실 방지 (-0.38)
            "incoming_relations": 1.0,
            "connected_entities": 1.0,
            "entity_properties": 1.0,
            "type_and_summary": 1.0
        },
        "entity_boost": "normalized",  # 정확한 엔티티 매칭
        "description": "비교 대상 간 관계 구조 유지"
    },
    "deep_analysis": {
        "semantic_expander": {
            "temporal": True,   # 시간적 맥락 확장
            "causal_chain": True,  # 인과적 맥락 확장
            "pgvector": False
        },
        "thread_weights": {
            "outgoing_relations": 1.0,
            "incoming_relations": 0.0,  # Intent 보존
            "connected_entities": 1.0,
            "entity_properties": 1.0,
            "type_and_summary": 1.0
        },
        "entity_boost": "partial",  # evidence_diversity 0.16 (다양한 근거)
        "description": "폭넓은 맥락, 다양한 관점"
    },
}


def get_config_for_query_type(query_type: str) -> dict:
    """
    쿼리 타입에 따른 최적 설정 반환

    Args:
        query_type: "factual", "causal", "comparative", "deep_analysis"

    Returns:
        설정 딕셔너리 (semantic_expander, thread_weights, entity_boost)

    Example:
        >>> config = get_config_for_query_type("causal")
        >>> config["semantic_expander"]["causal_chain"]
        True
    """
    if query_type not in QUERY_TYPE_CONFIGS:
        # 기본값: deep_analysis (가장 포괄적)
        query_type = "deep_analysis"

    return QUERY_TYPE_CONFIGS[query_type]
