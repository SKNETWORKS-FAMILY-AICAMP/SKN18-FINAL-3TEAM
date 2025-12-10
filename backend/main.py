# Langgraph 테스트 코드
import asyncio

from backend.langgraph_structure.graph import create_graph_flow


async def main():
    # LangGraph 앱 생성
    app = create_graph_flow()

    # 테스트용 입력 state
    initial_state = {
        "query": "Who founded the Joseon Dynasty?",
    }

    # 실행 (hybrid_node가 async이므로 ainvoke 사용)
    result = await app.ainvoke(initial_state)

    print("=== 최종 결과 ===")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
