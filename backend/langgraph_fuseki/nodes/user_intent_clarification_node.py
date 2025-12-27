"""
User Intent Clarification Node (Stage 1.5/6)

사용자에게 확장 방향을 제시하고 선택을 받아 처리합니다.

Phase 1: 고정 매핑 방식 + Stage 1-B 백그라운드 실행
- classify_node에서 생성한 방향 리스트를 사용자에게 제시
- 사용자 선택 입력 대기 중 Stage 1-B 백그라운드 실행
- 선택된 방향 저장 + Stage 1-B 결과 통합
"""

import time
import threading
from typing import Dict, Any

from backend.langgraph_fuseki.state import GraphState
from backend.langgraph_fuseki.nodes.classify_node import query_classifier_stage1b_background


# ========== Phase 2: 메모리 기반 체크포인트 ==========
# 세션별 중단된 그래프 state 저장 (백그라운드 작업 유지)
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

    # ========== 디버그: State 상태 확인 ==========
    print(f"\n{'='*70}")
    print(f"[Stage 1.5/6] 사용자 의도 확인 노드 진입")
    print(f"{'='*70}")
    print(f"  ├─ State keys: {sorted(state.keys())}")
    print(f"  ├─ 'tag' in state: {'tag' in state}")
    print(f"  ├─ tag value: '{state.get('tag', 'NOT_SET')}'")
    print(f"  ├─ 'skip_clarification' in state: {'skip_clarification' in state}")
    print(f"  ├─ skip_clarification value: {state.get('skip_clarification', 'NOT_SET')}")
    print(f"  ├─ needs_clarification: {state.get('needs_clarification', 'NOT_SET')}")
    print(f"  └─ expansion_directions count: {len(state.get('expansion_directions', []))}")

    # 의도 확인 필요 여부 체크
    if not state.get("needs_clarification", False):
        # 의도 확인 필요 없으면 스킵 (그대로 반환)
        print("\n[Stage 1.5/6] 사용자 의도 확인 - 스킵 (needs_clarification=False)")
        return state

    # 질문 출력
    clarification_question = state.get("clarification_question", "")
    expansion_directions = state.get("expansion_directions", [])

    if not expansion_directions:
        # 방향이 없으면 스킵
        print("\n[Stage 1.5/6] 사용자 의도 확인 - 스킵 (expansion_directions 없음)")
        return {
            **state,
            "needs_clarification": False
        }

    # ========== Django/API 모드 확인 ==========
    tag = state.get("tag", "")
    is_django_mode = (tag == "chat")
    print(f"\n[DEBUG] ★ Django 모드 체크:")
    print(f"  ├─ tag='{tag}'")
    print(f"  ├─ is_django_mode={is_django_mode}")

    # ========== skip_clarification 확인 ==========
    test_config = state.get("test_config")
    skip_clarification = (
        state.get("skip_clarification", False) or  # 최상위 레벨 (Django에서 설정)
        (test_config and test_config.get("skip_clarification", False))  # test_config 내부
    )
    print(f"  └─ skip_clarification={skip_clarification}")

    # ========== 공통 변수 초기화 ==========
    stage1b_started = state.get("stage1b_started", False)
    stage1b_task_id = state.get("stage1b_task_id")
    stage1b_result = {}
    stage1b_thread = None

    if skip_clarification:
        # ========== Phase 2: 저장된 state 복원 (백그라운드 작업 활용) ==========
        session_id = state.get("session_id")
        previous_state = None
        stage1b_task_id_from_checkpoint = None

        if session_id and session_id in _PENDING_GRAPH_STATES:
            # 체크포인트에서 state 복원
            checkpoint = _PENDING_GRAPH_STATES[session_id]
            previous_state = checkpoint["state"]
            stage1b_task_id_from_checkpoint = checkpoint.get("stage1b_task_id")
            elapsed_since_checkpoint = time.time() - checkpoint["timestamp"]

            print(f"[INFO] 체크포인트 복원 (session_id={session_id}, "
                  f"경과 시간={elapsed_since_checkpoint:.1f}초, "
                  f"stage1b_task_id={stage1b_task_id_from_checkpoint})")

            # state 병합 (사용자 선택 + 이전 state)
            state = {
                **previous_state,  # 이전 state (Stage 1-A, 1-B 결과 포함)
                **state,  # 현재 state (user_selected_direction 포함)
            }

            # 정리
            del _PENDING_GRAPH_STATES[session_id]
        else:
            print(f"[INFO] 체크포인트 없음 (session_id={session_id}), 새로 실행")

        # ========== Stage 1-B 백그라운드 실행 또는 결과 확인 ==========
        stage1b_result = {}

        def run_stage1b_background_test():
            """백그라운드 스레드에서 Stage 1-B 실행 (테스트 모드)"""
            nonlocal stage1b_result
            try:
                stage1b_result = query_classifier_stage1b_background(state)
            except Exception as e:
                print(f"[WARN] Stage 1-B 백그라운드 실행 실패: {e}")
                stage1b_result = {"status": "error", "error": str(e)}

        # ========== 체크포인트 복원 시 Stage 1-B 결과 확인 ==========
        if stage1b_task_id_from_checkpoint:
            # 체크포인트에서 복원된 경우: 전역 딕셔너리에서 결과 확인
            from backend.langgraph_fuseki.nodes.classify_node import _STAGE1B_RESULTS

            if stage1b_task_id_from_checkpoint in _STAGE1B_RESULTS:
                task_info = _STAGE1B_RESULTS[stage1b_task_id_from_checkpoint]
                if task_info.get("status") == "completed":
                    stage1b_result = task_info.get("result", {})
                    print(f"[INFO] Stage 1-B 백그라운드 결과 복원 완료 (task_id={stage1b_task_id_from_checkpoint})")
                elif task_info.get("status") == "error":
                    stage1b_result = task_info.get("result", {"status": "error"})
                    print(f"[WARN] Stage 1-B 백그라운드 실행 실패 (task_id={stage1b_task_id_from_checkpoint})")
                elif task_info.get("status") == "running":
                    # 아직 실행 중이면 대기
                    print(f"[INFO] Stage 1-B 백그라운드 실행 중, 대기... (task_id={stage1b_task_id_from_checkpoint})")
                    max_wait = 60.0
                    wait_start = time.time()

                    while time.time() - wait_start < max_wait:
                        task_info = _STAGE1B_RESULTS.get(stage1b_task_id_from_checkpoint, {})
                        if task_info.get("status") == "completed":
                            stage1b_result = task_info.get("result", {})
                            print(f"[INFO] Stage 1-B 백그라운드 완료 (대기 시간={time.time() - wait_start:.1f}초)")
                            break
                        elif task_info.get("status") == "error":
                            stage1b_result = task_info.get("result", {"status": "error"})
                            break
                        time.sleep(0.5)

                    if time.time() - wait_start >= max_wait:
                        print("[WARN] Stage 1-B 백그라운드 시간 초과")
                        stage1b_result = {"status": "timeout"}
            else:
                print(f"[WARN] Stage 1-B task_id={stage1b_task_id_from_checkpoint} 결과 없음")
        else:
            # 체크포인트 없이 새로 실행하는 경우
            stage1b_thread = threading.Thread(target=run_stage1b_background_test, daemon=True)
            stage1b_thread.start()
            stage1b_thread.join(timeout=10.0)  # 최대 10초 대기

        # 사용자가 이미 선택한 방향이 있는지 확인 (Django에서 전달)
        user_selected_direction_id = state.get("user_selected_direction")

        if user_selected_direction_id:
            # 사용자가 선택한 방향 찾기
            selected_direction = None
            for direction in expansion_directions:
                if direction["direction_id"] == user_selected_direction_id:
                    selected_direction = direction
                    break

            # 찾지 못한 경우 첫 번째 옵션 사용
            if selected_direction is None:
                print(f"[WARN] 사용자 선택 '{user_selected_direction_id}'를 찾을 수 없음, 첫 번째 옵션 사용")
                selected_direction = expansion_directions[0]
        else:
            # 사용자 선택이 없으면 자동으로 첫 번째 옵션 선택 (평가/테스트 모드)
            selected_direction = expansion_directions[0]

        node_elapsed = time.time() - node_start

        print(f"\n{'='*70}")
        print(f"[Stage 1.5/6] 사용자 의도 확인 (skip_clarification=True)")
        print(f"{'='*70}")
        print(f"  ├─ 선택된 방향: {selected_direction['title']}")
        print(f"  ├─ Direction ID: {selected_direction['direction_id']}")

        # Stage 1-B 결과 확인
        if stage1b_result.get("status") == "success":
            print(f"  ├─ [백그라운드] LLM 정밀 분류: {stage1b_result.get('query_type', 'N/A')}")
            print(f"  ├─ [백그라운드] 확장 키워드: {len(stage1b_result.get('expanded_keywords', []))}개")
            print(f"  ├─ [백그라운드] 프로퍼티 그룹: {len(stage1b_result.get('selected_property_groups', []))}개")

        print(f"  └─ 완료 ({node_elapsed:.2f}초)")
        print()

        node_times = state.get("node_execution_times", {})
        node_times["user_intent_clarification"] = node_elapsed

        # ========== Stage 1-B 결과 통합 (테스트 모드) ==========
        result_state = {
            **state,
            "user_selected_direction": selected_direction["direction_id"],
            "needs_clarification": False,
            "executed_nodes": state.get("executed_nodes", []) + ["user_intent_clarification"],
            "node_execution_times": node_times
        }

        # Stage 1-B 성공 시 결과 통합
        if stage1b_result.get("status") == "success":
            if stage1b_result.get("query_type"):
                result_state["query_type"] = stage1b_result["query_type"]
            if stage1b_result.get("expanded_keywords"):
                result_state["expanded_keywords"] = stage1b_result["expanded_keywords"]
                result_state["expanded_keywords_dict"] = stage1b_result.get("expanded_keywords_dict", {})
            if stage1b_result.get("selected_property_groups"):
                result_state["selected_property_groups"] = stage1b_result["selected_property_groups"]
                result_state["selected_properties"] = stage1b_result.get("selected_properties", [])
            print("[INFO] Stage 1-B 백그라운드 결과가 state에 통합되었습니다.")

        return result_state

    # ========== Stage 1-B 백그라운드 실행 확인 ==========
    # Stage 1-A에서 이미 시작되었는지 확인
    # 주의: Thread 객체는 LangGraph state에서 직렬화되지 않으므로 플래그로 확인
    if not stage1b_started:
        # Stage 1-A에서 시작되지 않았다면 여기서 시작 (하위 호환성)
        import uuid
        stage1b_task_id = str(uuid.uuid4())
        
        # 전역 딕셔너리 초기화
        from backend.langgraph_fuseki.nodes.classify_node import _STAGE1B_RESULTS
        
        _STAGE1B_RESULTS[stage1b_task_id] = {"status": "running", "result": None}
        
        def run_stage1b_background():
            """백그라운드 스레드에서 Stage 1-B 실행"""
            try:
                result = query_classifier_stage1b_background(state)
                _STAGE1B_RESULTS[stage1b_task_id]["status"] = "completed"
                _STAGE1B_RESULTS[stage1b_task_id]["result"] = result
            except Exception as e:
                print(f"[WARN] Stage 1-B 백그라운드 실행 실패: {e}")
                _STAGE1B_RESULTS[stage1b_task_id]["status"] = "error"
                _STAGE1B_RESULTS[stage1b_task_id]["result"] = {"status": "error", "error": str(e)}

        stage1b_thread = threading.Thread(target=run_stage1b_background, daemon=True)
        stage1b_thread.start()
        print("[INFO] Stage 1-B 백그라운드 분석 시작 (하위 호환성)")
    else:
        # Stage 1-A에서 이미 시작됨 (백그라운드에서 실행 중)
        print("[INFO] Stage 1-B 백그라운드 분석 진행 중 (Stage 1-A에서 시작됨)")
        # 전역 딕셔너리에서 현재 상태 확인
        from backend.langgraph_fuseki.nodes.classify_node import _STAGE1B_RESULTS
        if stage1b_task_id and stage1b_task_id in _STAGE1B_RESULTS:
            task_info = _STAGE1B_RESULTS[stage1b_task_id]
            if task_info.get("status") == "completed":
                stage1b_result = task_info.get("result", {})
            elif task_info.get("status") == "error":
                stage1b_result = task_info.get("result", {"status": "error"})

    # ========== 사용자 선택 확인 또는 입력 대기 ==========
    user_selected_direction_id = state.get("user_selected_direction")

    if user_selected_direction_id:
        # 사용자가 선택한 방향 찾기
        selected_direction = None
        for direction in expansion_directions:
            if direction["direction_id"] == user_selected_direction_id:
                selected_direction = direction
                break

        # 찾지 못한 경우 첫 번째 옵션 사용
        if selected_direction is None:
            print(f"[WARN] 사용자 선택 '{user_selected_direction_id}'를 찾을 수 없음, 첫 번째 옵션 사용")
            selected_direction = expansion_directions[0]
    else:
        # 사용자 선택이 아직 없음
        if is_django_mode:
            # ========== Django/API 모드: 예외 발생하여 중단 ==========
            print("\n" + "="*70)
            print("[INFO] ★★★ Django/API 호출 감지 - 사용자 재질문 필요 ★★★")
            print("="*70)
            print(f"  ├─ 질문: {state.get('query', '')[:50]}...")
            print(f"  ├─ 확장 방향 수: {len(expansion_directions)}")
            for i, d in enumerate(expansion_directions, 1):
                print(f"  │   {i}. {d.get('title', 'N/A')}")
            print(f"  └─ UserClarificationRequired 예외 발생 예정")
            print("="*70)

            # ========== Phase 2: State 저장 (백그라운드 작업 유지) ==========
            session_id = state.get("session_id")
            if session_id:
                _PENDING_GRAPH_STATES[session_id] = {
                    "state": state,
                    "stage1b_task_id": state.get("stage1b_task_id"),
                    "stage1b_started": stage1b_started,
                    "timestamp": time.time()
                }
                print(f"[INFO] State 저장 완료 (session_id={session_id}, stage1b_task_id={state.get('stage1b_task_id')})")
            else:
                print("[WARN] session_id 없음, state 저장 실패")

            # 예외를 발생시켜 Django 뷰로 제어권 반환
            raise UserClarificationRequired(state)
        else:
            # 터미널 모드에서만 input() 사용
            print("\n[INFO] 터미널 모드 - 사용자 입력 대기")
            print(clarification_question)

            # ========== 사용자 입력 대기 ==========
            while True:
                try:
                    user_input = input("\n선택 (번호 입력): ").strip()

                    # 숫자 검증
                    choice_idx = int(user_input) - 1  # 1-based → 0-based

                    if 0 <= choice_idx < len(expansion_directions):
                        selected_direction = expansion_directions[choice_idx]
                        break
                    else:
                        print(f"[ERROR] 1~{len(expansion_directions)} 사이의 번호를 입력해주세요.")

                except ValueError:
                    print("[ERROR] 숫자를 입력해주세요.")
                except KeyboardInterrupt:
                    print("\n\n[WARN] 사용자가 입력을 중단했습니다. 기본값(1번)으로 진행합니다.")
                    selected_direction = expansion_directions[0]
                    break
                except EOFError:
                    # 파이프/리다이렉션 등으로 stdin이 닫힌 경우
                    print("\n[WARN] 입력을 받을 수 없습니다. 기본값(1번)으로 진행합니다.")
                    selected_direction = expansion_directions[0]
                    break

    # ========== Stage 1-B 백그라운드 결과 대기 ==========
    # Stage 1-A에서 시작된 경우: 전역 딕셔너리에서 결과 확인
    # 여기서 시작한 경우: 스레드가 실행 중
    if stage1b_thread is not None and stage1b_thread.is_alive():
        print("\n[INFO] Stage 1-B 백그라운드 분석 완료 대기 중...")
        stage1b_thread.join(timeout=60.0)  # 최대 60초 대기

        if stage1b_thread.is_alive():
            print("[WARN] Stage 1-B 백그라운드 분석 시간 초과 (60초), 결과 무시")
            stage1b_result = {"status": "timeout"}
        else:
            # 스레드가 완료되었으면 전역 딕셔너리에서 결과 가져오기
            from backend.langgraph_fuseki.nodes.classify_node import _STAGE1B_RESULTS
            if stage1b_task_id and stage1b_task_id in _STAGE1B_RESULTS:
                task_info = _STAGE1B_RESULTS[stage1b_task_id]
                if task_info.get("status") == "completed":
                    stage1b_result = task_info.get("result", {})
                elif task_info.get("status") == "error":
                    stage1b_result = task_info.get("result", {"status": "error"})
    elif stage1b_started and stage1b_task_id:
        # Stage 1-A에서 시작된 경우: 전역 딕셔너리에서 결과 확인 및 대기
        from backend.langgraph_fuseki.nodes.classify_node import _STAGE1B_RESULTS
        
        if stage1b_task_id in _STAGE1B_RESULTS:
            task_info = _STAGE1B_RESULTS[stage1b_task_id]
            current_status = task_info.get("status", "running")
            
            # 결과가 아직 없으면 대기
            if current_status == "running":
                print("\n[INFO] Stage 1-B 백그라운드 분석 완료 대기 중...")
                wait_start = time.time()
                max_wait = 60.0  # 최대 60초 대기
                
                while time.time() - wait_start < max_wait:
                    # 전역 딕셔너리에서 상태 확인
                    if stage1b_task_id in _STAGE1B_RESULTS:
                        task_info = _STAGE1B_RESULTS[stage1b_task_id]
                        current_status = task_info.get("status", "running")
                        if current_status == "completed":
                            stage1b_result = task_info.get("result", {})
                            break
                        elif current_status == "error":
                            stage1b_result = task_info.get("result", {"status": "error"})
                            break
                    time.sleep(0.5)  # 0.5초마다 확인
                
                # 타임아웃 확인
                if time.time() - wait_start >= max_wait:
                    print("[WARN] Stage 1-B 백그라운드 분석 시간 초과 (60초), 결과 무시")
                    stage1b_result = {"status": "timeout"}
            elif current_status == "completed":
                # 이미 완료된 경우
                stage1b_result = task_info.get("result", {})
            elif current_status == "error":
                # 이미 에러가 발생한 경우
                stage1b_result = task_info.get("result", {"status": "error"})

    # ========== 선택 결과 출력 ==========
    node_elapsed = time.time() - node_start

    print(f"\n{'='*70}")
    print(f"[Stage 1.5/6] 사용자 의도 확인 (User Intent Clarification)")
    print(f"{'='*70}")
    print(f"  ├─ 선택된 방향: {selected_direction['title']}")
    print(f"  ├─ Direction ID: {selected_direction['direction_id']}")

    # Stage 1-B 결과 확인
    if stage1b_result.get("status") == "success":
        print(f"  ├─ [백그라운드] LLM 정밀 분류: {stage1b_result.get('query_type', 'N/A')}")
        print(f"  ├─ [백그라운드] 확장 키워드: {len(stage1b_result.get('expanded_keywords', []))}개")
        print(f"  ├─ [백그라운드] 프로퍼티 그룹: {len(stage1b_result.get('selected_property_groups', []))}개")
    elif stage1b_result.get("status") == "error":
        print(f"  ├─ [백그라운드] Stage 1-B 실패: {stage1b_result.get('error', 'Unknown')}")
    elif stage1b_result.get("status") == "timeout":
        print(f"  ├─ [백그라운드] Stage 1-B 시간 초과")

    print(f"  └─ 완료 ({node_elapsed:.2f}초)")
    print()

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["user_intent_clarification"] = node_elapsed

    # ========== Stage 1-B 결과 통합 ==========
    result_state = {
        **state,
        "user_selected_direction": selected_direction["direction_id"],
        "needs_clarification": False,  # 선택 완료
        "executed_nodes": state.get("executed_nodes", []) + ["user_intent_clarification"],
        "node_execution_times": node_times
    }

    # Stage 1-B 성공 시 결과 통합
    if stage1b_result.get("status") == "success":
        # query_type 최종 확정 (LLM 기반)
        if stage1b_result.get("query_type"):
            result_state["query_type"] = stage1b_result["query_type"]

        # 확장 키워드 추가
        if stage1b_result.get("expanded_keywords"):
            result_state["expanded_keywords"] = stage1b_result["expanded_keywords"]
            result_state["expanded_keywords_dict"] = stage1b_result.get("expanded_keywords_dict", {})

        # 프로퍼티 그룹 추가
        if stage1b_result.get("selected_property_groups"):
            result_state["selected_property_groups"] = stage1b_result["selected_property_groups"]
            result_state["selected_properties"] = stage1b_result.get("selected_properties", [])

        print("[INFO] Stage 1-B 백그라운드 결과가 state에 통합되었습니다.")

    return result_state