"""
User Intent Clarification Node (Stage 1.5)

사용자에게 확장 방향을 제시하고 선택을 받아 처리합니다.
"""

import time
from typing import Dict, Any

from backend.langgraph_fuseki.state import GraphState


class UserClarificationRequired(Exception):
    """
    사용자 재질문이 필요할 때 발생하는 예외
    Django 뷰에서 이 예외를 잡아서 프론트엔드로 재질문 데이터 전달
    """
    def __init__(self, state: GraphState):
        self.state = state
        super().__init__("User clarification required")


def get_selected_direction(state: GraphState, expansion_directions: list) -> dict:
    """사용자가 선택한 방향 정보 반환"""
    user_selected_direction_id = state.get("user_selected_direction")
    
    if not user_selected_direction_id or not expansion_directions:
        return None
    
    for direction in expansion_directions:
        if direction.get("direction_id") == user_selected_direction_id:
            return direction
    
    return None


def handle_terminal_input(expansion_directions: list, clarification_question: str) -> dict:
    """터미널 모드에서 사용자 입력 처리"""
    print(f"\n{clarification_question}")
    print("\n선택 가능한 방향:")
    
    for i, direction in enumerate(expansion_directions, 1):
        title = direction.get("title", "")
        description = direction.get("description", "")
        print(f"{i}. {title}")
        print(f"   {description}")
    
    while True:
        try:
            choice = input("\n선택 (번호 입력): ").strip()
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(expansion_directions):
                return expansion_directions[choice_num - 1]
            else:
                print(f"1-{len(expansion_directions)} 범위의 번호를 입력하세요.")
        except ValueError:
            print("숫자를 입력하세요.")
        except KeyboardInterrupt:
            print("\n종료합니다.")
            return expansion_directions[0] if expansion_directions else None


def user_intent_clarification_node(state: GraphState) -> GraphState:
    """
    Stage 1.5: 사용자 의도 확인
    """
    node_start = time.time()

    print(f"\n{'='*70}")
    print(f"[Stage 1.5] 사용자 의도 확인")

    # 의도 확인 필요 여부 체크
    if not state.get("needs_clarification", False):
        print("  스킵 (needs_clarification=False)")
        return state

    expansion_directions = state.get("expansion_directions", [])
    if not expansion_directions:
        print("  스킵 (expansion_directions 없음)")
        return {**state, "needs_clarification": False}

    # 모드 확인
    is_django_mode = (state.get("tag", "") == "chat")
    skip_clarification = state.get("skip_clarification", False)

    if skip_clarification:
        # 사용자가 이미 선택함
        selected_direction = get_selected_direction(state, expansion_directions)
        print(f"  사용자 선택: {selected_direction.get('title', 'N/A') if selected_direction else 'None'}")
        
        node_end = time.time()
        execution_time = node_end - node_start
        node_times = state.get("node_execution_times", {})
        node_times["user_intent_clarification"] = execution_time

        return {
            **state,
            "needs_clarification": False,
            "executed_nodes": state.get("executed_nodes", []) + ["user_intent_clarification"],
            "node_execution_times": node_times
        }

    # 사용자 선택 확인
    user_selected_direction_id = state.get("user_selected_direction")

    if user_selected_direction_id:
        # 이미 선택됨
        selected_direction = get_selected_direction(state, expansion_directions)
        print(f"  사용자 선택: {selected_direction.get('title', 'N/A') if selected_direction else 'None'}")
        
        node_end = time.time()
        execution_time = node_end - node_start
        node_times = state.get("node_execution_times", {})
        node_times["user_intent_clarification"] = execution_time

        return {
            **state,
            "needs_clarification": False,
            "executed_nodes": state.get("executed_nodes", []) + ["user_intent_clarification"],
            "node_execution_times": node_times
        }
    else:
        # 사용자 선택 필요
        if is_django_mode:
            # Django 모드: 예외 발생하여 중단
            print("  Django 모드 - 사용자 재질문 필요")
            print(f"  확장 방향 수: {len(expansion_directions)}")
            
            # 예외 발생
            raise UserClarificationRequired(state)
        else:
            # 터미널 모드: 사용자 입력 대기
            clarification_question = state.get("clarification_question", "")
            selected_direction = handle_terminal_input(expansion_directions, clarification_question)
            
            print(f"  터미널 선택: {selected_direction.get('title', 'N/A') if selected_direction else 'None'}")
            
            node_end = time.time()
            execution_time = node_end - node_start
            node_times = state.get("node_execution_times", {})
            node_times["user_intent_clarification"] = execution_time

            return {
                **state,
                "needs_clarification": False,
                "user_selected_direction": selected_direction.get("direction_id") if selected_direction else None,
                "executed_nodes": state.get("executed_nodes", []) + ["user_intent_clarification"],
                "node_execution_times": node_times
            }