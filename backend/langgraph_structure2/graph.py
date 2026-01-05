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


# ✅ create_cypher는 str을 반환하므로 LangGraph 노드로 쓰려면 dict로 감싸야 함
def generate_cypher_node(state: GraphState):
    cypher = create_cypher(state)
    print("\n[생성된 Cypher]\n", cypher)
    return {"cypher": cypher}


def create_graph_flow():
    workflow = StateGraph(GraphState)

    # 노드 추가
    workflow.add_node("classify_node", classify_node)
    workflow.add_node("retrieval_node", retrieval_node)
    workflow.add_node("evaluate_node", evaluate_node)
    workflow.add_node("generate_node", generate_node)

    # ✅ 여기: create_cypher 직접 등록 금지 (str 반환이라 터짐)
    workflow.add_node("generate_cypher_node", generate_cypher_node)

    workflow.add_node("neo4j_query_node", neo4j_search_node)
    workflow.add_node("tone_adjust_node", tone_adjust_node)
    workflow.add_node("scene_split_node", scene_split_node)
    workflow.add_node("extract_keywords_node", extract_keywords_node)

    # 엔트리
    workflow.set_entry_point("classify_node")

    # classify_node → 분기
    workflow.add_conditional_edges(
        "classify_node",
        route_classify,
        {
            "extract_keywords_node": "extract_keywords_node",
            "generate_cypher_node": "generate_cypher_node",
            END: END,
        },
    )

    # RAG 라인
    workflow.add_edge("extract_keywords_node", "retrieval_node")
    workflow.add_edge("retrieval_node", "evaluate_node")

    # evaluate_node → 분기
    workflow.add_conditional_edges(
        "evaluate_node",
        route_evaluate,
        {
            "generate_node": "generate_node",
            "generate_cypher_node": "generate_cypher_node",
        },
    )

    # GraphDB 라인
    workflow.add_edge("generate_cypher_node", "neo4j_query_node")
    workflow.add_edge("neo4j_query_node", "generate_node")

    # 말투/scene 라인
#    workflow.add_edge("generate_node", "tone_adjust_node")

#    workflow.add_conditional_edges(
#        "tone_adjust_node",
#        route_tone_adjust_node,
#        {
#            "scene_split_node": "scene_split_node",
#            END: END,
#        },
#    )

#    workflow.add_edge("scene_split_node", END)



    # ✅ RAGAS 테스트용: 답변 생성 후 바로 종료
    workflow.add_edge("generate_node", END)

    return workflow.compile()


# ✅ import 시점에 자동 실행되면 꼬일 수 있어서 보통은 제거하는 게 안전함
# graph = create_graph_flow()
