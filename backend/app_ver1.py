# Langgraph 테스트 코드
import asyncio
import argparse

from backend.langgraph_structure1.graph import create_graph_flow


async def main(initial_state):
    # LangGraph 앱 생성
    app = create_graph_flow()

    # 실행 (hybrid_node가 async이므로 ainvoke 사용)
    result = await app.ainvoke(initial_state)


if __name__ == "__main__":

    # arguments 설정
    parser = argparse.ArgumentParser(description='데이터 파이프라인 실행기')
    parser.add_argument('--chat', action='store_true', help='챗봇/댓글 생성')
    parser.add_argument('--video', action='store_true', help='비디오 생성')

    args = parser.parse_args()

    while True:

        user_query = input("질문을 입력하세요 (종료하려면 'exit' 입력): ")
        if user_query.lower() == 'exit':
            break

        if args.chat:
            initial_state = {
                "query": user_query,
                "tag": "chat"
            }
        elif args.video:
            initial_state = {
                "query": user_query,
                "tag": "video"
            }
        else:
            # 기본값: chat 태그
            initial_state = {
                "query": user_query,
                "tag": "chat"
            }

        asyncio.run(main(initial_state=initial_state))
