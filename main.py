# main.py - 창작 모드 테스트
from langgraph_structure.graph import graph


def print_result(result):
    """결과를 보기 좋게 출력"""
    print("\n" + "=" * 60)
    print("📊 실행 결과")
    print("=" * 60)

    # 실행된 노드
    executed = result.get("executed_nodes", [])
    print(f"\n✅ 실행된 노드 ({len(executed)}개):")
    for i, node in enumerate(executed, 1):
        print(f"   {i}. {node}")

    # 질문 분석
    print(f"\n🔍 질문 분석:")
    print(f"   - 유형: {result.get('query_type', '?')}")
    entities = result.get("extracted_entities", [])
    if entities:
        print(f"   - 엔티티: {len(entities)}개")
        for e in entities[:5]:
            print(f"      • {e.get('type')}: {e.get('name', e.get('value', '?'))}")

    # 추론 결과
    inference = result.get("inference_results", {})
    if inference:
        print(f"\n⚙️ 추론 결과:")
        print(f"   - 상태: {inference.get('status')}")
        bindings = inference.get("bindings", [])
        print(f"   - 추론된 트리플: {len(bindings)}개")

    # 추론 경로
    paths = result.get("inference_paths", [])
    if paths:
        print(f"\n🔗 추론 경로 ({len(paths)}개):")
        for i, path in enumerate(paths[:3], 1):
            chain_str = " → ".join([n.get("node", "?") for n in path["chain"]])
            print(f"   {i}. {chain_str}")

    # 근거
    evidences = result.get("evidences", [])
    if evidences:
        print(f"\n📚 근거 ({len(evidences)}개):")
        for ev in evidences:
            print(f"   {ev['rank']}. {ev['description']} (가중치: {ev['weight']:.0%})")

    # 최종 답변
    print(f"\n📖 최종 답변:")
    print("-" * 60)
    answer = result.get("final_answer", "답변 없음")
    print(answer)
    print("-" * 60)


def main():
    """테스트 시나리오"""

    # 테스트 케이스
    test_queries = [
        # 1. 인과관계 질문
        "명량해전이 왜 중요했을까?",

        # 2. What-if 질문
        "만약 원균이 가덕도해전에서 승리했다면 어떻게 되었을까?",

        # 3. 심화 분석 질문
        "모문룡이 조선에서 살해당한 진짜 이유는 무엇일까?",
    ]

    # 사용자 선택
    print("=" * 60)
    print("🎨 창작 모드 - 조선시대 역사 스토리텔링")
    print("=" * 60)
    print("\n테스트 질문:")
    for i, q in enumerate(test_queries, 1):
        print(f"{i}. {q}")

    choice = input("\n질문 번호를 선택하세요 (1-3) 또는 직접 입력: ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(test_queries):
        query = test_queries[int(choice) - 1]
    else:
        query = choice if choice else test_queries[0]

    print(f"\n🔍 질문: {query}")
    print("⏳ 처리 중...\n")

    # 그래프 실행
    initial_state = {"query": query}

    try:
        result = graph.invoke(initial_state)
        print_result(result)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
