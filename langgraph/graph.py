from langgraph.graph import StateGraph, END
from langgraph.state import GraphState
from langgraph.nodes.kg.realtime_inference_node import realtime_inference_node
from langgraph.nodes.generate_node import generate_node


def create_graph_flow():
    """
    창작 모드용 단순 그래프
    - 입력 → Reasoner → Generator
    """
    workflow = StateGraph(GraphState)

    workflow.add_node("realtime_inference_node", realtime_inference_node)
    workflow.add_node("generate_node", generate_node)

    workflow.set_entry_point("realtime_inference_node")
    workflow.add_edge("realtime_inference_node", "generate_node")
    workflow.add_edge("generate_node", END)

    return workflow.compile()


graph = create_graph_flow()
