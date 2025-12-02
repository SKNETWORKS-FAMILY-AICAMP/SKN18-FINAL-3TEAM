from typing import Any, Dict, List, TypedDict

class GraphState(TypedDict):
    # 사용자 질문
    query : str

    # 분류 결과
    query_type : str

    # retrieval results
    search_chunks: List[Dict[str, Any]]
    similarity_stats: Dict[str, float] # 선택된 청크 개수/ max, min 유사도

    # retrieval된 chunk 평가  집계 결과
    related_num : int
    context_chunks: List[Dict[str, Any]]

    # cypher 생성된 키워드
    cypher_keywords: List[str]
    cypher_query: str

    # neo4j 결과
    # json 형태의 neo4j 결과 저장
    neo4j_results: List[Dict[str, Any]]

    # 최종 답변
    final_answer : str

    # 말투 교정 결과
    tone_corrected_answer : str

    # Scene 분할 결과
    scenes : List[Dict[str, Any]]

