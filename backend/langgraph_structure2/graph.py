from langgraph.graph import StateGraph, END
from backend.langgraph_structure2.state import GraphState
from backend.langgraph_structure2.nodes.classify_node import classify_node, route_classify
from backend.langgraph_structure2.nodes.extract_keywords_node import extract_keywords_node
from backend.langgraph_structure2.rag.retrieval_node import retrieval_node
from backend.langgraph_structure2.rag.evaluate_node import evaluate_node, route_evaluate
from backend.langgraph_structure2.graphdb.generate_cypher_node import create_cypher
from backend.langgraph_structure2.graphdb.neo4j_search_node import neo4j_search_node
from backend.langgraph_structure2.nodes.generate_node import generate_node
from backend.langgraph_structure2.nodes.tone_adjust_node import tone_adjust_node, route_tone_adjust_node
from backend.langgraph_structure2.nodes.scene_split_node import scene_split_node


def create_graph_flow():
    # 그래프에 사용할 변수 정의
    workflow = StateGraph(GraphState)

    # 노드 추가
    workflow.add_node("classify_node",classify_node)
    workflow.add_node("retrieval_node", retrieval_node)
    workflow.add_node("evaluate_node", evaluate_node)
    workflow.add_node("generate_node", generate_node)
    workflow.add_node("generate_cypher_node", create_cypher)
    workflow.add_node("neo4j_query_node", neo4j_search_node)
    workflow.add_node("tone_adjust_node",tone_adjust_node)
    workflow.add_node("scene_split_node",scene_split_node)

    # 핵심 키워드 추출 노드 추가
    workflow.add_node("extract_keywords_node", extract_keywords_node)

    # 노드 연결(엣지 추가)
    workflow.set_entry_point("classify_node") 

    # classify_node → route_classify 로 분기
    workflow.add_conditional_edges(
        "classify_node",
        route_classify,
        {  # 분기 후보를 명시
            "extract_keywords_node": "extract_keywords_node",
            "generate_cypher_node": "generate_cypher_node",
            END: END,
        },
    )

    # extract_keywords_node → retrieval_node 로 연결
    workflow.add_edge("extract_keywords_node", "retrieval_node")

    # retrieval_node → evaluate_node 로 연결
    workflow.add_edge("retrieval_node", "evaluate_node")

    # evaluate_node → route_evaluate 로 분기
    # route_evaluate(state) 가 "generate_node" 또는 END로 리턴
    workflow.add_conditional_edges(
        "evaluate_node",
        route_evaluate,
        {
            "generate_node": "generate_node",
            "generate_cypher_node": "generate_cypher_node",
        },
    )


    # generate_cypher_node → neo4j_query_node → generate_node 로 연결
    workflow.add_edge("generate_cypher_node", "neo4j_query_node")
    workflow.add_edge("neo4j_query_node", "generate_node")

    # 말투 및 scene 분리 노드 연결
    workflow.add_edge("generate_node", "tone_adjust_node")

    workflow.add_conditional_edges(
        "tone_adjust_node",
        route_tone_adjust_node,
        { 
            "scene_split_node": "scene_split_node",
            END: END,
        },
    )

    workflow.add_edge("scene_split_node", END)

    # 4) 그래프 compile
    graph = workflow.compile()
    
    return graph

graph = create_graph_flow()