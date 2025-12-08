# Generate된 답변의 말투 교정하는 노드
from backend.langgraph_structure.state import GraphState

def tone_adjust_node(state: GraphState) -> GraphState:
    """
    말투 교정 노드
    (현재는 단순히 final_answer 를 그대로 tone_corrected_answer 에 복사하는 더미 구현)
    """
    final_answer = state.get("final_answer", "")
    tone_corrected_answer = final_answer  # 나중에 LLM 기반 말투 교정으로 교체

    return {
        **state,
        "tone_corrected_answer": tone_corrected_answer,
    }