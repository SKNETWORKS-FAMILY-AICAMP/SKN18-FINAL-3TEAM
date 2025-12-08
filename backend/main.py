# Langgraph 테스트 코드
from backend.langgraph_structure.graph import create_graph_flow

def main():
    # LangGraph 앱 생성
    app = create_graph_flow()

    # 테스트용 입력 state
    initial_state = {
        "query": "세종대왕은 어떤 업적이 있어?",
    }

    # 실행
    result = app.invoke(initial_state)

    print("=== 최종 결과 ===")
    print(result)

if __name__ == "__main__":
    main()
