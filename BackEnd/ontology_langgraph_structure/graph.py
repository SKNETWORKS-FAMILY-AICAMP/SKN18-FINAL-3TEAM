from langgraph.graph import StateGraph, END
from langgraph_structure.state import GraphState

# 노드 import (구현 예정)
from langgraph_structure.nodes.classify_node import query_classifier_node
from langgraph_structure.nodes.entity_extractor_node import entity_extractor_node
from langgraph_structure.nodes.kg.sparql_generator_node import sparql_generator_node
from langgraph_structure.nodes.kg.hypothetical_triple_node import hypothetical_triple_node
from langgraph_structure.nodes.kg.realtime_inference_node import realtime_inference_node
from langgraph_structure.nodes.kg.inference_path_extractor_node import inference_path_extractor_node
from langgraph_structure.nodes.evidence_aggregator_node import evidence_aggregator_node
from langgraph_structure.nodes.generate_node import story_generator_node


def route_by_query_type(state: GraphState) -> str:
    """질문 유형에 따라 다음 노드 선택"""
    query_type = state.get("query_type", "causal")

    if query_type == "what_if":
        return "hypothetical_triple_node"
    elif query_type == "deep_analysis":
        return "sparql_generator_node"  # 심화 질문도 SPARQL로 시작
    else:  # causal
        return "sparql_generator_node"


def route_after_hypothetical(state: GraphState) -> str:
    """What-if 경로: 가상 트리플 생성 후 추론으로"""
    return "realtime_inference_node"


def create_graph_flow():
    """
    창작 모드용 Jena Rules 기반 랭그래프

    Flow:
    1. Query Classifier → 질문 유형 분류
    2. Entity Extractor → 엔티티 추출
    3. Conditional Router → 유형별 분기
        ├─ What-if → Hypothetical Triple → Inference
        └─ 일반/심화 → SPARQL → Inference
    4. Inference Path Extractor → 추론 경로 추출
    5. Evidence Aggregator → 다중 근거 집계
    6. Story Generator → 근거 기반 스토리 생성
    """
    workflow = StateGraph(GraphState)

    # ========== 노드 등록 ==========
    workflow.add_node("query_classifier", query_classifier_node)
    workflow.add_node("entity_extractor", entity_extractor_node)
    workflow.add_node("sparql_generator", sparql_generator_node)
    workflow.add_node("hypothetical_triple_node", hypothetical_triple_node)
    workflow.add_node("realtime_inference", realtime_inference_node)
    workflow.add_node("inference_path_extractor", inference_path_extractor_node)
    workflow.add_node("evidence_aggregator", evidence_aggregator_node)
    workflow.add_node("story_generator", story_generator_node)

    # ========== 플로우 정의 ==========
    # 1. 시작: 질문 분류
    workflow.set_entry_point("query_classifier")

    # 2. 엔티티 추출
    workflow.add_edge("query_classifier", "entity_extractor")

    # 3. 조건부 라우팅: 질문 유형별 분기
    workflow.add_conditional_edges(
        "entity_extractor",
        route_by_query_type,
        {
            "sparql_generator": "sparql_generator",
            "hypothetical_triple_node": "hypothetical_triple_node",
        }
    )

    # 4a. What-if 경로: 가상 트리플 → 추론
    workflow.add_edge("hypothetical_triple_node", "realtime_inference")

    # 4b. 일반/심화 경로: SPARQL → 추론
    workflow.add_edge("sparql_generator", "realtime_inference")

    # 5. 추론 경로 추출
    workflow.add_edge("realtime_inference", "inference_path_extractor")

    # 6. 다중 근거 집계
    workflow.add_edge("inference_path_extractor", "evidence_aggregator")

    # 7. 스토리 생성
    workflow.add_edge("evidence_aggregator", "story_generator")

    # 8. 종료
    workflow.add_edge("story_generator", END)

    return workflow.compile()


# 그래프 인스턴스 생성
graph = create_graph_flow()
