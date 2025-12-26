# Langgraph 테스트 코드 (neo4j 결과 확인용)
import asyncio
import argparse
import json

from backend.langgraph_structure1.graph import create_graph_flow


async def main(initial_state):
    app = create_graph_flow()
    result = await app.ainvoke(initial_state)
    return result  # ✅ 결과를 반환해야 밖에서 확인 가능


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="데이터 파이프라인 실행기")
    parser.add_argument("--chat", action="store_true", help="챗봇/댓글 생성")
    parser.add_argument("--video", action="store_true", help="비디오 생성")

    args = parser.parse_args()

    while True:
        user_query = input("질문을 입력하세요 (종료하려면 'exit' 입력): ")
        if user_query.lower() == "exit":
            break

        tag = "chat"
        if args.video:
            tag = "video"
        elif args.chat:
            tag = "chat"

        initial_state = {"query": user_query, "tag": tag}

        result = asyncio.run(main(initial_state=initial_state))

        # ✅ 여기서 Neo4j 결과만 확인
        if isinstance(result, dict):
            neo = result.get("neo4j_candidates")
            if neo is None:
                neo = result.get("neo4j_results")  # 기존 키 fallback

            if neo is None:
                print("\n[neo4j 결과] 없음 (state에 neo4j_candidates/neo4j_results 키가 안 들어옴)")
                print("[result keys]", list(result.keys()))
            else:
                print(f"\n[neo4j 결과] total={len(neo)}")
                print(json.dumps(neo[:20], ensure_ascii=False, indent=2))  # 앞 20개만 프리뷰
        else:
            print("\n[result] dict 아님:", type(result))

        print("-" * 80)
