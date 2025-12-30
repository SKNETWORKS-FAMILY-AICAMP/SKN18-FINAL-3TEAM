"""
User Intent Clarification Node (Stage 1.5/6)

사용자에게 확장 방향을 제시하고 선택을 받아 처리합니다.
"""

import time
from typing import Dict, Any

from backend.langgraph_fuseki.state import GraphState
from backend.langgraph_fuseki.utils.clarification_utils import (
    get_stage1b_result,
    get_selected_direction,
    build_result_state,
    restore_checkpoint,
    save_checkpoint,
    start_stage1b_background,
    handle_terminal_input
)


# ========== 메모리 기반 체크포인트 ==========
_PENDING_GRAPH_STATES = {}


class UserClarificationRequired(Exception):
    """
    사용자 재질문이 필요할 때 발생하는 예외
    Django 뷰에서 이 예외를 잡아서 프론트엔드로 재질문 데이터 전달
    """
    def __init__(self, state: GraphState):
        self.state = state
        super().__init__("User clarification required")


def user_intent_clarification_node(state: GraphState) -> GraphState:
    """
    Stage 1.5/6: 사용자 의도 확인 (User Intent Clarification)

    Args:
        state: GraphState

    Returns:
        업데이트된 GraphState (user_selected_direction 포함)
    """
    node_start = time.time()

    print(f"\n{'='*70}")
    print(f"[Stage 1.5/6] 사용자 의도 확인 노드 진입")

    # 의도 확인 필요 여부 체크
    if not state.get("needs_clarification", False):
        print("[Stage 1.5/6] 스킵 (needs_clarification=False)")
        return state

    expansion_directions = state.get("expansion_directions", [])
    if not expansion_directions:
        print("[Stage 1.5/6] 스킵 (expansion_directions 없음)")
        return {**state, "needs_clarification": False}

    # 모드 및 설정 확인
    is_django_mode = (state.get("tag", "") == "chat")
    skip_clarification = state.get("skip_clarification", False)
    print(f"└─ skip_clarification={skip_clarification}")

    # Stage 1-B 관련 변수
    stage1b_started = state.get("stage1b_started", False)
    stage1b_task_id = state.get("stage1b_task_id")

    if skip_clarification:
        # Thinking 모드 콜백 함수 가져오기
        thinking_callback = state.get("thinking_callback")
        
        # 🎯 Thinking 이벤트: 사용자 선택 처리 시작
        if thinking_callback:
            thinking_callback("user_selection_processing", {
                "title": "사용자 선택 처리 중",
                "status": "processing"
            })

        # 체크포인트에서 state 복원
        session_id = state.get("session_id")
        state, stage1b_task_id, stage1b_result = restore_checkpoint(session_id, state)

        # Stage 1-B 결과 확인 및 대기
        if not stage1b_result:
            stage1b_result = get_stage1b_result(stage1b_task_id, stage1b_started, state)
        
        # 사용자 선택 처리
        selected_direction = get_selected_direction(state, expansion_directions)
        
        # 🎯 Thinking 이벤트: 선택된 의도와 1-B 결과 통합
        if thinking_callback and selected_direction:
            thinking_callback("intent_integration", {
                "title": "의도 분석 및 전략 통합",
                "selected_intent": {
                    "title": selected_direction.get("title", ""),
                    "description": selected_direction.get("description", "")[:150] + "..." if len(selected_direction.get("description", "")) > 150 else selected_direction.get("description", "")
                },
                "stage1b_status": stage1b_result.get("status", "unknown"),
                "expanded_keywords": stage1b_result.get("expanded_keywords", [])[:10] if stage1b_result.get("status") == "success" else [],
                "selected_properties": stage1b_result.get("selected_properties", [])[:5] if stage1b_result.get("status") == "success" else [],
                "status": "completed"
            })
        
        # 결과 반환
        return build_result_state(state, selected_direction, stage1b_result, node_start)

    # Stage 1-B 백그라운드 실행 시작 (아직 시작되지 않은 경우)
    if not stage1b_started:
        stage1b_task_id = start_stage1b_background(state)

    # 사용자 선택 확인
    user_selected_direction_id = state.get("user_selected_direction")

    if user_selected_direction_id:
        # 이미 선택됨 - 처리
        selected_direction = get_selected_direction(state, expansion_directions)
        stage1b_result = get_stage1b_result(stage1b_task_id, True, state)
        return build_result_state(state, selected_direction, stage1b_result, node_start)
    else:
        # 사용자 선택 필요
        if is_django_mode:
            # Django 모드: 예외 발생하여 중단
            print("\n" + "="*70)
            print("[INFO] ★★★ Django/API 호출 감지 - 사용자 재질문 필요 ★★★")
            print("="*70)
            print(f"├─ 질문: {state.get('query', '')[:50]}...")
            print(f"├─ 확장 방향 수: {len(expansion_directions)}")
            for i, d in enumerate(expansion_directions, 1):
                print(f"│   {i}. {d.get('title', 'N/A')}")
            print(f"└─ UserClarificationRequired 예외 발생 예정")
            print("="*70)

            # 체크포인트 저장
            session_id = state.get("session_id")
            stage1b_result_for_checkpoint = _get_completed_stage1b_result(stage1b_task_id)
            save_checkpoint(session_id, state, stage1b_task_id, stage1b_result_for_checkpoint)

            # 예외 발생
            raise UserClarificationRequired(state)
        else:
            # 터미널 모드: 사용자 입력 대기
            clarification_question = state.get("clarification_question", "")
            selected_direction = handle_terminal_input(expansion_directions, clarification_question)

            # Stage 1-B 결과 대기 및 처리
            stage1b_result = get_stage1b_result(stage1b_task_id, True, state)
            return build_result_state(state, selected_direction, stage1b_result, node_start)


def _get_completed_stage1b_result(stage1b_task_id: str) -> Dict:
    """완료된 Stage 1-B 결과만 가져오는 함수 (대기하지 않음)"""
    if not stage1b_task_id:
        return None
        
    from backend.langgraph_fuseki.nodes.classify_node import _STAGE1B_RESULTS
    
    if stage1b_task_id in _STAGE1B_RESULTS:
        task_info = _STAGE1B_RESULTS[stage1b_task_id]
        if task_info.get("status") == "completed":
            return task_info.get("result", {})
    
    return None