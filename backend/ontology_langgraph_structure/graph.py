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
from nodes.semantic_expander_node import semantic_expander_node
from nodes.kg.parallel_inference_executor_node import parallel_inference_executor_node
from nodes.kg.multi_path_extractor_node import multi_path_extractor_node
from nodes.evidence_aggregator_node import evidence_aggregator_node
from nodes.generate_node import story_generator_node


def create_graph_flow():
    """
    데이터 기반 창작 모드 랭그래프 (개선된 버전)

    Flow:
    1. Query Classifier → 질문 유형 분류 (causal/deep_analysis)
    2. Entity Extractor → 하이브리드 엔티티 추출 (TTL + Milvus)
    3. Semantic Expander → 의미론적 엔티티 확장 (NEW)
       ├─ 시간적 맥락 (±10년)
       ├─ 카테고리/주제
       ├─ 인과관계 체인
       └─ 벡터 유사도
    4. Parallel Knowledge Retrieval → 5개 Thread 동시 실행
       ├─ Thread 1: outgoing_relations (나가는 관계)
       ├─ Thread 2: incoming_relations (들어오는 관계)
       ├─ Thread 3: entity_properties (엔티티 속성)
       ├─ Thread 4: connected_entities (연결 엔티티 + 양방향 BFS) (NEW)
       └─ Thread 5: type_and_summary (타입/요약)
    5. Multi-Path Extractor → 각 Thread별 경로 추출
    6. Evidence Aggregator → 5가지 근거 통합 + 수렴 노드 감지 (NEW)
    7. Story Generator → 풍부한 스토리 생성
    """

    workflow = StateGraph(GraphState)

    # ========== 노드 등록 ==========
    workflow.add_node("query_classifier", query_classifier_node)
    workflow.add_node("entity_extractor", entity_extractor_node)
    workflow.add_node("semantic_expander", semantic_expander_node)  # NEW
    workflow.add_node("parallel_knowledge_retrieval", parallel_inference_executor_node)
    workflow.add_node("multi_path_extractor", multi_path_extractor_node)
    workflow.add_node("evidence_aggregator", evidence_aggregator_node)
    workflow.add_node("story_generator", story_generator_node)

    # ========== 플로우 정의 ==========
    # 1. 시작: 질문 분류
    workflow.set_entry_point("query_classifier")

    # 2. 조건부 분기: 역사 관련 질문 여부에 따라 분기
    def route_after_classify(state: GraphState) -> str:
        """classify_node 이후 라우팅"""
        is_historical = state.get("is_historical", True)

        if not is_historical:
            # 역사 관련이 아니면 바로 스토리 생성으로 (조기 종료 메시지 출력)
            return "story_generator"
        else:
            # 역사 관련이면 정상 플로우 진행
            return "entity_extractor"

    workflow.add_conditional_edges(
        "query_classifier",
        route_after_classify,
        {
            "entity_extractor": "entity_extractor",
            "story_generator": "story_generator"
        }
    )

    # 3. 엔티티 추출 (하이브리드: TTL + Milvus)
    # 4. 의미론적 확장 (NEW)
    workflow.add_edge("entity_extractor", "semantic_expander")

    # 5. 병렬 지식 검색 (5개 Thread)
    workflow.add_edge("semantic_expander", "parallel_knowledge_retrieval")

    # 6. 다중 경로 추출 (각 Thread별)
    workflow.add_edge("parallel_knowledge_retrieval", "multi_path_extractor")

    # 7. 근거 통합 (5가지 관점 병합 + 수렴 노드 감지)
    workflow.add_edge("multi_path_extractor", "evidence_aggregator")

    # 8. 스토리 생성
    workflow.add_edge("evidence_aggregator", "story_generator")

    # 9. 종료
    workflow.add_edge("story_generator", END)

    return workflow.compile()


# 그래프 인스턴스 생성
graph = create_graph_flow()
