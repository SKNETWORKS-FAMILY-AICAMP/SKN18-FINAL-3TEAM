from langgraph.graph import StateGraph, END
from backend.langgraph_structure1.state import GraphState
from backend.langgraph_structure1.nodes.classify_node import classify_node, route_classify
from backend.langgraph_structure1.nodes.generate_node import generate_node
from backend.langgraph_structure1.nodes.tone_adjust_node import tone_adjust_node, route_tone_adjust_node
from backend.langgraph_structure1.nodes.scene_split_node import scene_split_node
from backend.langgraph_structure1.rag.hybrid_node import hybrid_node


def create_graph_flow():
    # 그래프에 사용할 변수 정의
    workflow = StateGraph(GraphState)

    # 노드 추가
    workflow.add_node("classify_node",classify_node)
    workflow.add_node("generate_node", generate_node)
    workflow.add_node("tone_adjust_node",tone_adjust_node)
    workflow.add_node("scene_split_node",scene_split_node)

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

    workflow.add_conditional_edges(
        "route_tone_adjust_node",
        route_tone_adjust_node,
        { 
            "scene_split_node": "scene_split_node",
            END: END,
        },
    )

    workflow.add_edge("scene_split_node", END)

    # # ragas 평가용 노드 연결
    # workflow.add_edge("generate_node", END)

    # 4) 그래프 compile
    graph = workflow.compile()
    
    return graph

graph = create_graph_flow()

