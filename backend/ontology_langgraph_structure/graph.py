"""
창작 모드 - 데이터 기반 LangGraph

5가지 관점에서 데이터를 병렬로 검색하여
풍부한 근거 기반 역사 스토리 생성

특징:
- 하이브리드 엔티티 추출 (TTL + pgvector)
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
from nodes.history_check_node import history_check_node
from nodes.classify_node import query_classifier_node
from nodes.entity_expander_node import entity_expander_node
from nodes.semantic_expander_node import semantic_expander_node
from nodes.kg.parallel_knowledge_retrieval_node import parallel_knowledge_retrieval_node
from nodes.kg.path_evidence_aggregator_node import path_evidence_aggregator_node
from nodes.generate_node import story_generator_node


def create_graph_flow():
    """
    데이터 기반 창작 모드 랭그래프 (개선된 버전)

    Flow:
    0. History Check → 역사 관련 여부 체크 (LLM 1회) ⭐NEW
       ├─ false → 조기 종료 (비용 절감)
       └─ true → Query Classifier로 진행
    1. Query Classifier → 질문 유형 분류 (causal/deep_analysis)
    2. Entity Extractor → 하이브리드 엔티티 추출 (TTL + pgvector)
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
    5. Path Extractor & Evidence Aggregator → 경로 추출 및 근거 통합 (통합) (NEW)
       ├─ 개선된 점수 체계로 관련성 평가
       └─ 상위 15개 근거 선택 (기존 5개에서 확장)
    6. Story Generator → 풍부한 스토리 생성
    """

    workflow = StateGraph(GraphState)

    # ========== 노드 등록 ==========
    workflow.add_node("history_check", history_check_node)  # NEW: 0단계
    workflow.add_node("query_classifier", query_classifier_node)
    workflow.add_node("entity_expander", entity_expander_node)
    workflow.add_node("semantic_expander", semantic_expander_node)  # NEW
    workflow.add_node("parallel_knowledge_retrieval", parallel_knowledge_retrieval_node)
    workflow.add_node("path_evidence_aggregator", path_evidence_aggregator_node)  # 통합 노드
    workflow.add_node("story_generator", story_generator_node)

    # ========== 플로우 정의 ==========
    # 0. 시작: 역사 관련 여부 체크 (최우선)
    workflow.set_entry_point("history_check")

    # 1. 조건부 분기: 역사 관련 질문 여부에 따라 분기
    def route_after_history_check(state: GraphState) -> str:
        """history_check_node 이후 라우팅"""
        is_historical = state.get("is_historical", True)

        if not is_historical:
            # 역사 관련이 아니면 바로 스토리 생성으로 (조기 종료 메시지 출력)
            return "story_generator"
        else:
            # 역사 관련이면 Query Classifier로 진행
            return "query_classifier"

    workflow.add_conditional_edges(
        "history_check",
        route_after_history_check,
        {
            "query_classifier": "query_classifier",
            "story_generator": "story_generator"
        }
    )

    # 2. Query Classifier → Entity Expander
    workflow.add_edge("query_classifier", "entity_expander")

    # 3. 엔티티 추출 (하이브리드: TTL + pgvector)
    # 4. 의미론적 확장 (NEW)
    workflow.add_edge("entity_expander", "semantic_expander")

    # 5. 병렬 지식 검색 (5개 Thread)
    workflow.add_edge("semantic_expander", "parallel_knowledge_retrieval")

    # 6. 경로 추출 및 근거 통합 (통합 노드)
    workflow.add_edge("parallel_knowledge_retrieval", "path_evidence_aggregator")

    # 7. 스토리 생성
    workflow.add_edge("path_evidence_aggregator", "story_generator")

    # 9. 종료
    workflow.add_edge("story_generator", END)

    return workflow.compile()


# 그래프 인스턴스 생성
graph = create_graph_flow()
