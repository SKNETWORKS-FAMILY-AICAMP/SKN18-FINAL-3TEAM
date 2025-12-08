# scene 분리(장면/대사 분리)
from backend.langgraph_structure.state import GraphState
from typing import Dict, Any, List

def scene_split_node(state: GraphState) -> GraphState:
    """
    Scene 분리 노드
    (현재는 tone_corrected_answer 전체를 하나의 scene 으로 넣는 더미 구현)
    """
    answer = state.get("tone_corrected_answer", "")

    # answer을 여러 scene으로 분리하는 로직은 추후 구현 예정
    # 현재는 하나의 scene으로만 구성
    scenes: List[Dict[str, Any]] = [
        {
            "cut": 1,
            "content": answer, # 변경 필요
        }
    ]

    return {
        **state,
        "scenes": scenes,
    }
