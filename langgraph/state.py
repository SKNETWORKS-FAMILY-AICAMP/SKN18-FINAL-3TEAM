from typing import Any, Dict, List, NotRequired, TypedDict

class GraphState(TypedDict):
    """창작 모드용 상태"""

    # 사용자 질문
    query: str

    # Reasoner 결과
    kg_results: NotRequired[List[Dict[str, Any]]]

    # 최종 답변
    final_answer: NotRequired[str]
