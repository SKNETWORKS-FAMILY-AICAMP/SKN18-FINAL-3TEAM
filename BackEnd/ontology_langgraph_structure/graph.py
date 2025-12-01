"""
창작 모드 - 데이터 기반 LangGraph

5가지 관점에서 데이터를 병렬로 검색하여
풍부한 근거 기반 역사 스토리 생성

특징:
- 하이브리드 엔티티 추출 (TTL + Milvus)
- 데이터 기반 5개 Thread (event_context, actor_network, timeline, similar_events, background)
- 이야기 모드 지원 (선택적)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 환경변수 로드 (가장 먼저 실행)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path, override=True)

# LangSmith 프로젝트 이름 설정 (랭그래프 전용)
os.environ["LANGCHAIN_PROJECT"] = "Korean-History-LangGraph"

from langgraph.graph import StateGraph, END
from state import GraphState

# 노드 import
from nodes.classify_node import query_classifier_node
from nodes.entity_extractor_node import entity_extractor_node
from nodes.kg.parallel_inference_executor_node import parallel_inference_executor_node
from nodes.kg.multi_path_extractor_node import multi_path_extractor_node
from nodes.evidence_aggregator_node import evidence_aggregator_node
from nodes.generate_node import story_generator_node


def create_graph_flow():
    """
    데이터 기반 창작 모드 랭그래프

    Flow:
    1. Query Classifier → 질문 유형 분류 (causal/deep_analysis)
    2. Entity Extractor → 하이브리드 엔티티 추출 (TTL + Milvus)
    3. Parallel Knowledge Retrieval → 5개 Thread 동시 실행
       ├─ Thread 1: event_context (사건 맥락)
       ├─ Thread 2: actor_network (인물 네트워크)
       ├─ Thread 3: timeline (시간순 사건)
       ├─ Thread 4: similar_events (유사 사건 - Milvus)
       └─ Thread 5: background (배경 정보)
    4. Multi-Path Extractor → 각 Thread별 경로 추출
    5. Evidence Aggregator → 5가지 근거 통합 + 가중치 정렬
    6. Story Generator → 풍부한 스토리 생성
    """

    workflow = StateGraph(GraphState)

    # ========== 노드 등록 ==========
    workflow.add_node("query_classifier", query_classifier_node)
    workflow.add_node("entity_extractor", entity_extractor_node)
    workflow.add_node("parallel_knowledge_retrieval", parallel_inference_executor_node)
    workflow.add_node("multi_path_extractor", multi_path_extractor_node)
    workflow.add_node("evidence_aggregator", evidence_aggregator_node)
    workflow.add_node("story_generator", story_generator_node)

    # ========== 플로우 정의 ==========
    # 1. 시작: 질문 분류
    workflow.set_entry_point("query_classifier")

    # 2. 엔티티 추출 (하이브리드: TTL + Milvus)
    workflow.add_edge("query_classifier", "entity_extractor")

    # 3. 병렬 지식 검색 (5개 Thread)
    workflow.add_edge("entity_extractor", "parallel_knowledge_retrieval")

    # 4. 다중 경로 추출 (각 Thread별)
    workflow.add_edge("parallel_knowledge_retrieval", "multi_path_extractor")

    # 5. 근거 통합 (5가지 관점 병합 + 우선순위)
    workflow.add_edge("multi_path_extractor", "evidence_aggregator")

    # 6. 스토리 생성
    workflow.add_edge("evidence_aggregator", "story_generator")

    # 7. 종료
    workflow.add_edge("story_generator", END)

    return workflow.compile()


# 그래프 인스턴스 생성
graph = create_graph_flow()
