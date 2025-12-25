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


def user_intent_clarification_node(state: GraphState) -> GraphState:
    """
    Stage 1.5/6: 사용자 의도 확인 (User Intent Clarification)

    Args:
        state: GraphState

    Returns:
        업데이트된 GraphState (user_selected_direction 포함)
    """
    node_start = time.time()

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

    # ========== test_config에서 자동 선택 확인 ==========
    test_config = state.get("test_config")
    if test_config and test_config.get("skip_clarification", False):
        # ========== 테스트 모드에서도 Stage 1-B 백그라운드 실행 ==========
        stage1b_result = {}

        def run_stage1b_background_test():
            """백그라운드 스레드에서 Stage 1-B 실행 (테스트 모드)"""
            nonlocal stage1b_result
            try:
                stage1b_result = query_classifier_stage1b_background(state)
            except Exception as e:
                print(f"[WARN] Stage 1-B 백그라운드 실행 실패: {e}")
                stage1b_result = {"status": "error", "error": str(e)}

        # 백그라운드 스레드 시작 및 즉시 완료 대기 (테스트 모드는 빠름)
        stage1b_thread = threading.Thread(target=run_stage1b_background_test, daemon=True)
        stage1b_thread.start()
        stage1b_thread.join(timeout=10.0)  # 최대 10초 대기

        # 자동으로 첫 번째 옵션 선택 (평가/테스트 모드)
        selected_direction = expansion_directions[0]
        node_elapsed = time.time() - node_start

        print(f"\n{'='*70}")
        print(f"[Stage 1.5/6] 사용자 의도 확인 (자동 선택 - 테스트 모드)")
        print(f"{'='*70}")
        print(f"  ├─ 자동 선택: {selected_direction['title']}")
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
    stage1b_thread = state.get("stage1b_thread")
    stage1b_result = state.get("stage1b_result", {})

    if stage1b_thread is None:
        raise RuntimeError("Stage 1-B 백그라운드 스레드가 시작되지 않았습니다. Stage 1-A 노드가 제대로 실행되었는지 확인하세요.")

    # ========== 사용자에게 질문 제시 ==========
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
    if stage1b_thread and stage1b_thread.is_alive():
        print("\n[INFO] Stage 1-B 백그라운드 분석 완료 대기 중...")
        stage1b_thread.join(timeout=60.0)  # 최대 60초 대기

        if stage1b_thread.is_alive():
            print("[WARN] Stage 1-B 백그라운드 분석 시간 초과 (60초), 결과 무시")
            stage1b_result = {"status": "timeout"}

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
