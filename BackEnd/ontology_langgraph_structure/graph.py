"""
창작 모드 - 병렬 추론 기반 LangGraph

병렬 실행으로 5가지 관점의 추론을 동시에 수행하여
풍부한 근거 기반 역사 스토리 생성

개선사항:
- multi_query_generator_node 제거
- parallel_inference_executor_node에서 쿼리 생성 + 실행 통합
- 총 실행 시간 ~13초 → ~3-5초로 단축
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 환경변수 로드 (가장 먼저 실행)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path, override=True)  # override=True: 기존 환경변수도 .env로 덮어쓰기

# LangSmith 프로젝트 이름 설정 (랭그래프 전용)
os.environ["LANGCHAIN_PROJECT"] = "Korean-History-LangGraph"

from langgraph.graph import StateGraph, END
from state import GraphState

# 노드 import
from nodes.classify_node import query_classifier_node
from nodes.entity_extractor_node import entity_extractor_node
from nodes.kg.hypothetical_triple_node import hypothetical_triple_node
from nodes.kg.parallel_inference_executor_node import parallel_inference_executor_node
from nodes.kg.multi_path_extractor_node import multi_path_extractor_node
from nodes.evidence_aggregator_node import evidence_aggregator_node
from nodes.generate_node import story_generator_node


def route_by_query_type(state: GraphState) -> str:
    """
    질문 유형에 따라 다음 노드 선택

    - what_if: 가상 트리플 생성 → 병렬 추론
    - causal/deep_analysis: 직접 병렬 추론
    """
    query_type = state.get("query_type", "causal")

    if query_type == "what_if":
        return "hypothetical_triple_node"
    else:
        return "parallel_inference_executor"


def create_graph_flow():
    """
    병렬 추론 기반 창작 모드 랭그래프 (최적화 버전)

    Flow:
    1. Query Classifier → 질문 유형 분류 (causal/what_if/deep_analysis)
    2. Entity Extractor → Milvus 기반 엔티티 추출
    3. Conditional Router:
        ├─ What-if → Hypothetical Triple → Parallel Inference (통합)
        └─ 일반/심화 → Parallel Inference (통합)
    4. Parallel Inference Executor → 5개 Thread 동시 실행 (쿼리생성+추론 통합)
       ├─ Thread 1: causal 쿼리생성 → 추론
       ├─ Thread 2: person 쿼리생성 → 추론
       ├─ Thread 3: temporal 쿼리생성 → 추론
       ├─ Thread 4: pattern 쿼리생성 → 추론
       └─ Thread 5: motive 쿼리생성 → 추론
    5. Multi-Path Extractor → 각 Thread별 추론 경로 추출
    6. Evidence Aggregator → 5가지 근거 통합 + 가중치 정렬
    7. Story Generator → 풍부한 스토리 생성
    """

    workflow = StateGraph(GraphState)

    # ========== 노드 등록 ==========
    workflow.add_node("query_classifier", query_classifier_node)
    workflow.add_node("entity_extractor", entity_extractor_node)
    workflow.add_node("hypothetical_triple_node", hypothetical_triple_node)
    workflow.add_node("parallel_inference_executor", parallel_inference_executor_node)
    workflow.add_node("multi_path_extractor", multi_path_extractor_node)
    workflow.add_node("evidence_aggregator", evidence_aggregator_node)
    workflow.add_node("story_generator", story_generator_node)

    # ========== 플로우 정의 ==========
    # 1. 시작: 질문 분류
    workflow.set_entry_point("query_classifier")

    # 2. 엔티티 추출 (Milvus)
    workflow.add_edge("query_classifier", "entity_extractor")

    # 3. 조건부 라우팅: 질문 유형별 분기
    workflow.add_conditional_edges(
        "entity_extractor",
        route_by_query_type,
        {
            "parallel_inference_executor": "parallel_inference_executor",
            "hypothetical_triple_node": "hypothetical_triple_node",
        }
    )

    # 4. What-if 경로: 가상 트리플 → 병렬 추론 (통합)
    workflow.add_edge("hypothetical_triple_node", "parallel_inference_executor")

    # 5. 다중 경로 추출 (각 Thread별)
    workflow.add_edge("parallel_inference_executor", "multi_path_extractor")

    # 6. 근거 통합 (5가지 관점 병합 + 우선순위)
    workflow.add_edge("multi_path_extractor", "evidence_aggregator")

    # 7. 스토리 생성
    workflow.add_edge("evidence_aggregator", "story_generator")

    # 8. 종료
    workflow.add_edge("story_generator", END)

    return workflow.compile()


# 그래프 인스턴스 생성
graph = create_graph_flow()
