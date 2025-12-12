from typing import Any, Dict, List, NotRequired, TypedDict
from backend.langgraph_structure1.state_type import Evidence


class GraphState(TypedDict):
    # 사용자 질문(필수)
    query: str

    # 분류 결과
    detect_lang: NotRequired[str]
    translated_query: NotRequired[str]
    query_type: NotRequired[str]

    # Retrieval 결과
    vector_evidences: NotRequired[List[Evidence]]

    # Neo4j 검색 결과
    cypher: NotRequired[str]
    neo4j_results: NotRequired[List[Dict[str, Any]]]

    # 최종 답변 및 후처리
    final_answer: NotRequired[str]

    # tone 교정 결과
    tone_corrected_answer: NotRequired[str]

    # Scene 분할 결과
    scenes: NotRequired[List[Dict[str, Any]]]

