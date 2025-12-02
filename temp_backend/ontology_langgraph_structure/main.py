"""
Korean History LangGraph - 인터랙티브 실행 스크립트

사용자 질문을 입력받아 LangGraph를 통해 온톨로지 기반 추론 실행
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트에서)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path, override=True)  # override=True: 기존 환경변수도 .env로 덮어쓰기

# LangSmith 프로젝트 이름 변경 (랭그래프 전용)
os.environ["LANGCHAIN_PROJECT"] = "Korean-History-LangGraph"

from graph import graph


def print_header():
    """헤더 출력"""
    print("\n" + "="*70)
    print("🏛️  Korean History LangGraph - 조선시대 역사 스토리텔링")
    print("="*70)
    print("\n💡 질문 예시:")
    print("  - 이순신이 명량해전에서 왜 승리했을까?")
    print("  - 만약 세종대왕이 한글을 창제하지 않았다면?")
    print("  - 왕자의 난의 진짜 이유는 무엇일까?")
    print("\n종료하려면 'quit' 또는 'exit'를 입력하세요.\n")
    print("="*70 + "\n")


def print_result(state: dict):
    """실행 결과 출력"""
    print("\n" + "="*70)
    print("📊 실행 결과")
    print("="*70 + "\n")

    # 질문 유형
    query_type = state.get("query_type", "N/A")
    print(f"🔍 질문 유형: {query_type}")

    # 추출된 엔티티
    entities = state.get("extracted_entities", [])
    if entities:
        print(f"\n🎯 추출된 엔티티 ({len(entities)}개):")
        for i, entity in enumerate(entities[:5], 1):
            entity_type = entity.get("type", "Unknown")
            entity_name = entity.get("name", entity.get("value", "N/A"))
            print(f"  {i}. [{entity_type}] {entity_name}")

    # 생성된 SPARQL 쿼리
    multi_queries = state.get("multi_queries", {})
    if multi_queries:
        print(f"\n📝 생성된 SPARQL 쿼리 ({len(multi_queries)}개):")
        for thread_type in multi_queries.keys():
            print(f"  ✓ {thread_type}")

    # 추론 결과
    inference_results = state.get("parallel_inference_results", {})
    if inference_results:
        total_bindings = sum(len(r.get("bindings", [])) for r in inference_results.values())
        print(f"\n⚡ 추론 결과: {total_bindings}개 트리플")
        for thread_type, result in inference_results.items():
            count = len(result.get("bindings", []))
            status = result.get("status", "unknown")
            if count > 0:
                print(f"  ✓ {thread_type}: {count}개 ({status})")

    # 근거
    evidences = state.get("evidences", [])
    if evidences:
        print(f"\n📚 추출된 근거 ({len(evidences)}개):")
        for i, evidence in enumerate(evidences[:3], 1):
            ev_type = evidence.get("type", "Unknown")
            weight = evidence.get("weight", 0)
            print(f"  {i}. [{ev_type}] 가중치: {weight:.2f}")

    # 최종 답변
    final_answer = state.get("final_answer", "")
    if final_answer:
        print("\n" + "="*70)
        print("📖 최종 답변")
        print("="*70 + "\n")
        print(final_answer)
    else:
        print("\n⚠️  최종 답변이 생성되지 않았습니다.")

    # 실행 정보
    executed_nodes = state.get("executed_nodes", [])
    execution_time = state.get("execution_time", 0)

    print("\n" + "="*70)
    print(f"⏱️  실행 시간: {execution_time:.2f}초")
    print(f"🔗 실행된 노드: {len(executed_nodes)}개")
    print("="*70 + "\n")


def main():
    """메인 실행 함수"""
    print_header()

    while True:
        try:
            # 사용자 입력
            query = input("❓ 질문을 입력하세요: ").strip()

            # 종료 명령 체크
            if query.lower() in ['quit', 'exit', 'q', '종료']:
                print("\n👋 프로그램을 종료합니다.\n")
                break

            # 빈 입력 체크
            if not query:
                print("⚠️  질문을 입력해주세요.\n")
                continue

            # LangGraph 실행
            print(f"\n🚀 처리 중...\n")

            import time
            start_time = time.time()

            result = graph.invoke({"query": query})

            execution_time = time.time() - start_time
            result["execution_time"] = execution_time

            # 결과 출력
            print_result(result)

        except KeyboardInterrupt:
            print("\n\n👋 프로그램을 종료합니다.\n")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}\n")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    main()
