from langgraph.graph import StateGraph, END
from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.nodes.classify_node import classify_node, route_classify
from backend.langgraph_structure1.nodes.generate_node import generate_node
from backend.langgraph_structure1.nodes.tone_adjust_node import tone_adjust_node, route_tone_adjust_node
from backend.langgraph_structure1.nodes.scene_split_node import scene_split_node
from backend.langgraph_structure1.rag.hybrid_node import hybrid_node
# [HEAD 기능] 배경 생성 노드 임포트 유지
from backend.langgraph_structure1.nodes.background_gen_node import background_gen_node


def create_graph_flow():
    # 그래프에 사용할 변수 정의
    workflow = StateGraph(GraphState)

    # 노드 추가
    workflow.add_node("classify_node", classify_node)
    workflow.add_node("generate_node", generate_node)
    workflow.add_node("tone_adjust_node", tone_adjust_node)
    workflow.add_node("scene_split_node", scene_split_node)
    workflow.add_node("background_gen_node", background_gen_node) # 배경 생성 노드 추가

    # 하이브리드 노드 추가
    workflow.add_node("hybrid_node", hybrid_node)

    # 노드 연결(엣지 추가)
    workflow.set_entry_point("classify_node")

    # classify_node → hybrid_node 또는 END 로 분기
    workflow.add_conditional_edges(
        "classify_node",
        route_classify,
        { 
            "hybrid_node": "hybrid_node",
            END: END,
        },
    )

    workflow.add_edge("hybrid_node", "generate_node")

    # 말투 및 scene 분리 노드 연결
    workflow.add_edge("generate_node", "tone_adjust_node")

    # [충돌 해결 구간]
    # 1. DEV의 안전장치(조건부 엣지)를 먼저 적용
    # 말투 수정이 잘 되었는지 확인 후 분기
    workflow.add_conditional_edges(
        "tone_adjust_node",
        route_tone_adjust_node,
        { 
            "scene_split_node": "scene_split_node", # 성공 시 장면 분리로 이동
            END: END,                               # 실패 시 여기서 종료
        },
    )

    # 2. HEAD의 추가 기능 연결
    # 장면 분리가 끝나면 -> 바로 끝내지 말고 -> 배경 생성 노드로 이동
    workflow.add_edge("scene_split_node", "background_gen_node")
    
    # 3. 배경 생성이 끝나면 종료
    workflow.add_edge("background_gen_node", END)

    # 4) 그래프 compile
    graph = workflow.compile()
    
    return graph

graph = create_graph_flow()