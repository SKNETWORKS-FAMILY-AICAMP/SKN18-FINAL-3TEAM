# Langgraph 테스트 코드
import asyncio

from backend.langgraph_structure1.graph import create_graph_flow


async def main(query: str = None):
    # LangGraph 앱 생성
    app = create_graph_flow()

    # 테스트용 입력 state
    initial_state = {
        "query": "Who founded the Joseon?",
    }

    # 실행 (hybrid_node가 async이므로 ainvoke 사용)
    result = await app.ainvoke(initial_state)

    print("=== 최종 결과 ===")
    print(result)


if __name__ == "__main__":

    while True:
        user_query = input("질문을 입력하세요 (종료하려면 'exit' 입력): ")
        if user_query.lower() == 'exit':
            break
        asyncio.run(main(query=user_query))