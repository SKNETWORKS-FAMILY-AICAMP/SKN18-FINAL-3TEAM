"""
User Intent Clarification Node (Stage 1.5/6)

사용자에게 확장 방향을 제시하고 선택을 받아 처리합니다.

Phase 1: 고정 매핑 방식
- classify_node에서 생성한 방향 리스트를 사용자에게 제시
- 사용자 선택 입력 대기
- 선택된 방향 저장
"""

import time
from typing import Dict, Any

from backend.langgraph_fuseki.state import GraphState


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
        # 자동으로 첫 번째 옵션 선택 (평가/테스트 모드)
        selected_direction = expansion_directions[0]
        node_elapsed = time.time() - node_start

        print(f"\n{'='*70}")
        print(f"[Stage 1.5/6] 사용자 의도 확인 (자동 선택 - 테스트 모드)")
        print(f"{'='*70}")
        print(f"  ├─ 자동 선택: {selected_direction['title']}")
        print(f"  ├─ Direction ID: {selected_direction['direction_id']}")
        print(f"  └─ 완료 ({node_elapsed:.2f}초)")
        print()

        node_times = state.get("node_execution_times", {})
        node_times["user_intent_clarification"] = node_elapsed

        return {
            **state,
            "user_selected_direction": selected_direction["direction_id"],
            "needs_clarification": False,
            "executed_nodes": state.get("executed_nodes", []) + ["user_intent_clarification"],
            "node_execution_times": node_times
        }

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

    # ========== 선택 결과 출력 ==========
    node_elapsed = time.time() - node_start

    print(f"\n{'='*70}")
    print(f"[Stage 1.5/6] 사용자 의도 확인 (User Intent Clarification)")
    print(f"{'='*70}")
    print(f"  ├─ 선택된 방향: {selected_direction['title']}")
    print(f"  ├─ Direction ID: {selected_direction['direction_id']}")
    print(f"  └─ 완료 ({node_elapsed:.2f}초)")
    print()

    # 노드 실행 시간 기록
    node_times = state.get("node_execution_times", {})
    node_times["user_intent_clarification"] = node_elapsed

    return {
        **state,
        "user_selected_direction": selected_direction["direction_id"],
        "needs_clarification": False,  # 선택 완료
        "executed_nodes": state.get("executed_nodes", []) + ["user_intent_clarification"],
        "node_execution_times": node_times
    }
