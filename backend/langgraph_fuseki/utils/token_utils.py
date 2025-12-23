"""
토큰 사용량 추적 유틸리티 (최소 수정)

각 노드에서 LLM 호출 후 토큰을 state에 누적하는 헬퍼 함수
"""

from typing import Dict, Any
from backend.langgraph_fuseki.state import GraphState


def extract_and_accumulate_tokens(state: GraphState, response) -> GraphState:
    """
    LLM 응답에서 토큰 사용량을 추출하여 state에 누적합니다.
    
    Args:
        state: 현재 GraphState
        response: ChatOpenAI.invoke()의 반환값 (AIMessage 객체)
    
    Returns:
        토큰이 누적된 GraphState (dict 형태로 반환)
    """
    # 현재 state의 토큰 사용량 (기본값 0)
    total_tokens = state.get("total_tokens", 0)
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)
    
    # 응답에서 토큰 사용량 추출
    if response and hasattr(response, 'response_metadata'):
        metadata = response.response_metadata
        if isinstance(metadata, dict) and "token_usage" in metadata:
            token_usage = metadata["token_usage"]
            total_tokens += token_usage.get("total_tokens", 0)
            prompt_tokens += token_usage.get("prompt_tokens", 0)
            completion_tokens += token_usage.get("completion_tokens", 0)
    
    # state 업데이트 (dict 반환)
    return {
        "total_tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }

