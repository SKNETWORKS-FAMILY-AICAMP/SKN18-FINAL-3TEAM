"""
ontology_evaluate 패키지의 진입점 - 테스트 질문 생성

Usage:
    python -m backend.ragas.ontology_evaluate
"""

from .build_queries_persona import PersonaQueryBuilder

if __name__ == "__main__":
    # 질문 생성 및 저장
    output_path = "backend/ragas/ontology_evaluate/data/test_queries.json"
    PersonaQueryBuilder.save_to_json(output_path)