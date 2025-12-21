"""
LangGraph LLM 호출의 토큰 사용량을 추적하는 유틸리티

문제: LangGraph의 astream_events()에서 response_metadata에 token_usage가 없음
원인: LangGraph가 이벤트를 생성할 때 token_usage를 필터링하거나 제거함
해결: 현재로서는 LangGraph 이벤트에서 토큰을 추출할 수 없음
"""

from typing import Dict, Any
import asyncio


def _extract_token_usage_from_event(event_data: dict) -> Dict[str, int]:
    """
    이벤트 데이터에서 토큰 사용량을 추출합니다.
    
    주의: LangGraph의 이벤트 시스템에서 token_usage가 response_metadata에 포함되지 않을 수 있습니다.
    이는 LangGraph의 버전이나 설정에 따라 다를 수 있습니다.
    """
    usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
    
    # 경로 1: output이 AIMessage 객체인 경우
    output = event_data.get("output")
    if output and hasattr(output, 'response_metadata'):
        metadata = output.response_metadata
        if isinstance(metadata, dict) and "token_usage" in metadata:
            token_data = metadata["token_usage"]
            usage["total_tokens"] = token_data.get("total_tokens", 0)
            usage["prompt_tokens"] = token_data.get("prompt_tokens", 0)
            usage["completion_tokens"] = token_data.get("completion_tokens", 0)
            return usage
    
    # 경로 2: input에서 원본 응답 확인
    input_data = event_data.get("input")
    if input_data and hasattr(input_data, 'response_metadata'):
        metadata = input_data.response_metadata
        if isinstance(metadata, dict) and "token_usage" in metadata:
            token_data = metadata["token_usage"]
            usage["total_tokens"] = token_data.get("total_tokens", 0)
            usage["prompt_tokens"] = token_data.get("prompt_tokens", 0)
            usage["completion_tokens"] = token_data.get("completion_tokens", 0)
            return usage
    
    # 경로 3: output이 딕셔너리인 경우
    if isinstance(output, dict):
        metadata = output.get("response_metadata", {})
        if isinstance(metadata, dict) and "token_usage" in metadata:
            token_data = metadata["token_usage"]
            usage["total_tokens"] = token_data.get("total_tokens", 0)
            usage["prompt_tokens"] = token_data.get("prompt_tokens", 0)
            usage["completion_tokens"] = token_data.get("completion_tokens", 0)
            return usage
    
    # 경로 4: llm_output에서 추출
    llm_output = event_data.get("llm_output", {})
    if isinstance(llm_output, dict) and "token_usage" in llm_output:
        token_data = llm_output["token_usage"]
        usage["total_tokens"] = token_data.get("total_tokens", 0)
        usage["prompt_tokens"] = token_data.get("prompt_tokens", 0)
        usage["completion_tokens"] = token_data.get("completion_tokens", 0)
        return usage
    
    return usage


def track_tokens_from_events(graph, initial_state):
    """
    LangGraph 그래프를 실행하고 state에서 토큰 사용량을 추출합니다.
    
    각 노드에서 LLM 호출 후 토큰을 state에 누적하므로,
    최종 state에서 토큰 사용량을 읽어옵니다.
    
    Args:
        graph: LangGraph 컴파일된 그래프
        initial_state: 초기 상태
    
    Returns:
        (final_state, token_usage) 튜플
    """
    # 그래프 실행 (각 노드에서 토큰을 state에 누적)
    final_state = graph.invoke(initial_state)
    
    # state에서 토큰 사용량 추출
    token_usage = {
        "total_tokens": final_state.get("total_tokens", 0),
        "prompt_tokens": final_state.get("prompt_tokens", 0),
        "completion_tokens": final_state.get("completion_tokens", 0)
    }
    
    return final_state, token_usage

