"""
HistoK LangGraph Fuseki - 인터랙티브 실행 스크립트

사용자 질문을 입력받아 Fuseki 기반 LangGraph를 통해 온톨로지 추론 실행

실행 방법:
    python -m backend.langgraph_fuseki.main
"""

# 환경변수 및 LangSmith 설정은 config.py에서 자동 로드됨
from backend.langgraph_fuseki.config import PACKAGE_DIR
from backend.langgraph_fuseki.graph import create_graph_flow

# 그래프 인스턴스 생성 (main.py에서만 실행)
graph = create_graph_flow(use_optimized=False)


def print_header():
    """헤더 출력"""
    print(f"\n{'='*70}")
    print(f"HistoK LangGraph Fuseki - 조선시대 역사 스토리텔링")
    print(f"{'='*70}")
    print(f"  ├─ 질문 예시:")
    print(f"  │   • 경복궁을 건축한 왕은 누구인가?")
    print(f"  │   • 갑술환국의 원인은 무엇인가?")
    print(f"  │   • 세종대왕이 창제한 것은 무엇인가?")
    print(f"  └─ 종료: 'quit' 또는 'exit' 입력")
    print(f"{'='*70}\n")


def print_result(state: dict):
    """실행 결과 출력"""
    # 최종 답변
    final_answer = state.get("final_answer", "")
    if final_answer:
        print(f"\n{'='*70}")
        print(f"[6/6] 최종 답변")
        print(f"{'='*70}\n")
        print(final_answer)
    else:
        print(f"\n경고: 최종 답변이 생성되지 않았습니다.")

    # 실행 정보
    execution_time = state.get("execution_time", 0)
    node_times = state.get("node_execution_times", {})

    print(f"\n{'='*70}")
    print(f"실행 완료")
    print(f"{'='*70}")

    # 노드별 실행 시간
    if node_times:
        print(f"  노드별 실행 시간:")
        node_order = ["query_classifier", "entity_expander", "parallel_knowledge_retrieval",
                      "multi_path_extractor", "evidence_aggregator", "story_generator"]
        for node_name in node_order:
            if node_name in node_times:
                print(f"    - {node_name}: {node_times[node_name]:.2f}초")

    print(f"  총 실행 시간: {execution_time:.2f}초")
    print(f"{'='*70}\n")


def main():
    """메인 실행 함수"""
    print_header()

    while True:
        try:
            # 사용자 입력
            query = input("❓ 질문을 입력하세요: ").strip()

            # 종료 명령 체크
            if query.lower() in ['quit', 'exit', 'q', '종료']:
                print("\n프로그램을 종료합니다.\n")
                break

            # 빈 입력 체크
            if not query:
                print("경고: 질문을 입력해주세요.\n")
                continue

            # LangGraph 실행
            print(f"\n처리 시작...\n")

            import time
            start_time = time.time()

            result = graph.invoke({"query": query})

            execution_time = time.time() - start_time
            result["execution_time"] = execution_time

            # 결과 출력
            print_result(result)

        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다.\n")
            break
        except Exception as e:
            print(f"\n오류 발생: {e}\n")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    main()
