from langgraph.graph import StateGraph, END
from langgraph_structure.state import GraphState
from langgraph_structure.nodes.classify_node import classify_node, route_classify
from langgraph_structure.rag.retrieval_node import retrieval_node, route_retrieval
from langgraph_structure.rag.evaluate_node import evaluate_node, route_evaluate
from langgraph_structure.graphdb.generate_cypher_node import generate_cypher_node
from langgraph_structure.graphdb.neo4j_query_node import neo4j_query_node, route_neo4j_query
from langgraph_structure.nodes.generate_node import generate_node
from langgraph_structure.nodes.tone_adjust_node import tone_adjust_node
from langgraph_structure.nodes.scene_split_node import scene_split_node
from langgraph_structure.rag.hybrid_node import hybrid_retrieval_node


def create_graph_flow():
    # 그래프에 사용할 변수 정의
    workflow = StateGraph(GraphState)

    # 노드 추가
    workflow.add_node("classify_node",classify_node)
    workflow.add_node("retrieval_node", retrieval_node)
    workflow.add_node("evaluate_node", evaluate_node)
    workflow.add_node("generate_cypher_node", generate_cypher_node)
    workflow.add_node("neo4j_query_node",neo4j_query_node)
    workflow.add_node("generate_node", generate_node)
    workflow.add_node("tone_adjust_node",tone_adjust_node)
    workflow.add_node("scene_split_node",scene_split_node)

    # 하이브리드 노드 추가
    workflow.add_node("hybrid_retrieval_node", hybrid_retrieval_node)

    # 노드 연결(엣지 추가)
    workflow.set_entry_point("classify_node")

    # classify_node → hybrid_node 또는 END 로 분기
    workflow.add_conditional_edges(
        "classify_node",
        route_classify,
        { 
            "hybrid_retrieval_node": "hybrid_retrieval_node",
            END: END,
        },
    )

    # retrieval_node → route_retrieval 로 분기
    # route_retrieval(state) 가 "generate_cypher_node" 또는 "evaluate_node"를 리턴
    workflow.add_conditional_edges(
        "retrieval_node",
        route_retrieval,
        {
            "generate_cypher_node": "generate_cypher_node",
            "evaluate_node": "evaluate_node",
        },
    )

    # evaluate_node → route_evaluate 로 분기
    # route_evaluate(state) 가 "generate_node" 또는 generate_cypher_node를 리턴
    workflow.add_conditional_edges(
        "evaluate_node",
        route_evaluate,
        {
            "generate_node": "generate_node",
            "generate_cypher_node": "generate_cypher_node",
        },
    )
    
    workflow.add_edge("generate_cypher_node", "neo4j_query_node")

    # neo4j_query_node → route_neo4j_query 로 분기
    # route_neo4j_query(state) 가 "generate_node" 또는 END를 리턴
    workflow.add_conditional_edges(
        "neo4j_query_node",
        route_neo4j_query,
        {
            "generate_node": "generate_node",
            END: END,
        },
    )

    # 말투 및 scene 분리 노드 연결
    workflow.add_edge("generate_node", "tone_adjust_node")
    workflow.add_edge("tone_adjust_node", "scene_split_node")
    workflow.add_edge("scene_split_node", END)

    # 4) 그래프 compile
    graph = workflow.compile()
    
    return graph

graph = create_graph_flow()

