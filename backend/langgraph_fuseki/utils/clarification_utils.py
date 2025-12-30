"""
User Intent Clarification 유틸리티 함수들

사용자 의도 확인 노드에서 사용하는 헬퍼 함수들을 모듈화
"""

import time
from typing import Dict, Any, Optional, List

from backend.langgraph_fuseki.state import GraphState


def get_stage1b_result(stage1b_task_id: str, stage1b_started: bool, state: GraphState, timeout: int = 60) -> Dict[str, Any]:
    """
    Stage 1-B 결과를 가져오는 헬퍼 함수
    
    Args:
        stage1b_task_id: Stage 1-B 작업 ID
        stage1b_started: Stage 1-B 시작 여부
        state: 현재 GraphState
        timeout: 최대 대기 시간 (초)
    
    Returns:
        Stage 1-B 결과 딕셔너리
    """
    from backend.langgraph_fuseki.nodes.classify_node import _STAGE1B_RESULTS, query_classifier_stage1b_background
    
    if stage1b_started and stage1b_task_id and stage1b_task_id in _STAGE1B_RESULTS:
        task_info = _STAGE1B_RESULTS[stage1b_task_id]
        status = task_info.get("status", "running")
        
        if status == "completed":
            return task_info.get("result", {})
        elif status == "error":
            return task_info.get("result", {"status": "error"})
        elif status == "running":
            # 완료까지 대기
            print(f"[INFO] Stage 1-B 대기 중... (task_id={stage1b_task_id})")
            wait_start = time.time()
            while time.time() - wait_start < timeout:
                task_info = _STAGE1B_RESULTS.get(stage1b_task_id, {})
                status = task_info.get("status", "running")
                if status == "completed":
                    elapsed = time.time() - wait_start
                    print(f"[INFO] Stage 1-B 완료 (대기={elapsed:.1f}초)")
                    return task_info.get("result", {})
                elif status == "error":
                    return task_info.get("result", {"status": "error"})
                time.sleep(0.5)
            return {"status": "timeout"}
    
    # 새로 실행
    print("[INFO] Stage 1-B 새로 실행...")
    try:
        return query_classifier_stage1b_background(state)
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_selected_direction(state: GraphState, expansion_directions: List[Dict]) -> Optional[Dict]:
    """
    사용자 선택 방향을 가져오는 헬퍼 함수
    
    Args:
        state: 현재 GraphState
        expansion_directions: 확장 방향 리스트
    
    Returns:
        선택된 방향 딕셔너리 또는 None
    """
    user_selected_direction_id = state.get("user_selected_direction")
    
    if user_selected_direction_id:
        for direction in expansion_directions:
            if direction.get("direction_id") == user_selected_direction_id:
                return direction
        print(f"[WARN] 선택 '{user_selected_direction_id}' 없음, 첫 번째 사용")
    
    return expansion_directions[0] if expansion_directions else None


def build_result_state(state: GraphState, selected_direction: Dict, stage1b_result: Dict, node_start: float) -> GraphState:
    """
    결과 상태를 구성하는 헬퍼 함수
    
    Args:
        state: 현재 GraphState
        selected_direction: 선택된 방향
        stage1b_result: Stage 1-B 결과
        node_start: 노드 시작 시간
    
    Returns:
        업데이트된 GraphState
    """
    if not selected_direction:
        return state
        
    node_elapsed = time.time() - node_start
    
    print(f"\n[Stage 1.5/6] 사용자 의도 확인 완료")
    print(f"├─ 선택: {selected_direction['title']}")
    print(f"├─ ID: {selected_direction['direction_id']}")
    
    if stage1b_result.get("status") == "success":
        print(f"├─ Stage 1-B: 성공")
        print(f"├─ 키워드: {len(stage1b_result.get('expanded_keywords', []))}개")
    else:
        print(f"├─ Stage 1-B: {stage1b_result.get('status', 'unknown')}")
    
    print(f"└─ 완료 ({node_elapsed:.2f}초)")
    
    # 결과 상태 구성
    result_state = {
        **state,
        "user_selected_direction": selected_direction["direction_id"],
        "needs_clarification": False,
        "executed_nodes": state.get("executed_nodes", []) + ["user_intent_clarification"],
        "node_execution_times": {**state.get("node_execution_times", {}), "user_intent_clarification": node_elapsed}
    }
    
    # Stage 1-B 결과 통합
    if stage1b_result.get("status") == "success":
        if stage1b_result.get("query_type"):
            result_state["query_type"] = stage1b_result["query_type"]
        if stage1b_result.get("expanded_keywords"):
            result_state["expanded_keywords"] = stage1b_result["expanded_keywords"]
            result_state["expanded_keywords_dict"] = stage1b_result.get("expanded_keywords_dict", {})
        if stage1b_result.get("selected_property_groups"):
            result_state["selected_property_groups"] = stage1b_result["selected_property_groups"]
            result_state["selected_properties"] = stage1b_result.get("selected_properties", [])
        print("[INFO] Stage 1-B 결과 통합 완료")
    else:
        # 기본값 설정
        if not result_state.get("query_type"):
            result_state["query_type"] = state.get("query_type_initial", "causal")
        if not result_state.get("expanded_keywords"):
            result_state["expanded_keywords"] = []
        if not result_state.get("selected_properties"):
            result_state["selected_properties"] = []
        print("[WARN] Stage 1-B 결과 없음, 기본값 사용")
    
    return result_state


def restore_checkpoint(session_id: str, current_state: GraphState) -> tuple[GraphState, Optional[str], Dict]:
    """
    체크포인트에서 상태를 복원하는 함수
    
    Args:
        session_id: 세션 ID
        current_state: 현재 상태
    
    Returns:
        (복원된_상태, stage1b_task_id, stage1b_result)
    """
    from backend.langgraph_fuseki.nodes.user_intent_clarification_node import _PENDING_GRAPH_STATES
    
    if session_id and session_id in _PENDING_GRAPH_STATES:
        checkpoint = _PENDING_GRAPH_STATES[session_id]
        previous_state = checkpoint["state"]
        stage1b_task_id = checkpoint.get("stage1b_task_id")
        stage1b_result = checkpoint.get("stage1b_result", {})
        
        elapsed = time.time() - checkpoint["timestamp"]
        print(f"[INFO] 체크포인트 복원 (session_id={session_id}, 경과={elapsed:.1f}초)")
        
        # state 병합
        merged_state = {**previous_state, **current_state, "skip_clarification": True}
        del _PENDING_GRAPH_STATES[session_id]
        
        return merged_state, stage1b_task_id, stage1b_result
    
    return current_state, None, {}


def save_checkpoint(session_id: str, state: GraphState, stage1b_task_id: str, stage1b_result: Optional[Dict] = None):
    """
    체크포인트를 저장하는 함수
    
    Args:
        session_id: 세션 ID
        state: 저장할 상태
        stage1b_task_id: Stage 1-B 작업 ID
        stage1b_result: Stage 1-B 결과 (완료된 경우)
    """
    from backend.langgraph_fuseki.nodes.user_intent_clarification_node import _PENDING_GRAPH_STATES
    
    if session_id:
        _PENDING_GRAPH_STATES[session_id] = {
            "state": state,
            "stage1b_task_id": stage1b_task_id,
            "stage1b_started": True,
            "stage1b_result": stage1b_result,
            "timestamp": time.time()
        }
        result_status = "완료됨" if stage1b_result else "진행 중"
        print(f"[INFO] 체크포인트 저장 (session_id={session_id}, Stage 1-B: {result_status})")


def start_stage1b_background(state: GraphState) -> str:
    """
    Stage 1-B 백그라운드 작업을 시작하는 함수
    
    Args:
        state: 현재 상태
    
    Returns:
        작업 ID
    """
    import uuid
    import threading
    from backend.langgraph_fuseki.nodes.classify_node import _STAGE1B_RESULTS, query_classifier_stage1b_background
    
    stage1b_task_id = str(uuid.uuid4())
    _STAGE1B_RESULTS[stage1b_task_id] = {"status": "running", "result": None}
    
    def run_stage1b_background():
        try:
            result = query_classifier_stage1b_background(state)
            _STAGE1B_RESULTS[stage1b_task_id]["status"] = "completed"
            _STAGE1B_RESULTS[stage1b_task_id]["result"] = result
        except Exception as e:
            print(f"[WARN] Stage 1-B 실행 실패: {e}")
            _STAGE1B_RESULTS[stage1b_task_id]["status"] = "error"
            _STAGE1B_RESULTS[stage1b_task_id]["result"] = {"status": "error", "error": str(e)}

    stage1b_thread = threading.Thread(target=run_stage1b_background, daemon=True)
    stage1b_thread.start()
    print("[INFO] Stage 1-B 백그라운드 시작")
    
    return stage1b_task_id


def handle_terminal_input(expansion_directions: List[Dict], clarification_question: str) -> Dict:
    """
    터미널 모드에서 사용자 입력을 처리하는 함수
    
    Args:
        expansion_directions: 확장 방향 리스트
        clarification_question: 재질문 내용
    
    Returns:
        선택된 방향
    """
    print("\n[INFO] 터미널 모드 - 사용자 입력 대기")
    print(clarification_question)

    while True:
        try:
            user_input = input("\n선택 (번호 입력): ").strip()
            choice_idx = int(user_input) - 1

            if 0 <= choice_idx < len(expansion_directions):
                return expansion_directions[choice_idx]
            else:
                print(f"[ERROR] 1~{len(expansion_directions)} 사이의 번호를 입력해주세요.")

        except (ValueError, KeyboardInterrupt, EOFError):
            print("\n[WARN] 기본값(1번)으로 진행합니다.")
            return expansion_directions[0]