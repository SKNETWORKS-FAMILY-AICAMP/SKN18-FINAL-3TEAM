"""
HistoK LangGraph Fuseki - 데이터 기반 LangGraph

5가지 관점에서 데이터를 병렬로 검색하여
풍부한 근거 기반 역사 스토리 생성

특징:
- 하이브리드 엔티티 추출 (TTL + pgvector)
- 데이터 기반 5개 Thread (event_context, actor_network, timeline, similar_events, background)
- 이야기 모드 지원 (선택적)
- 성능 최적화 지원 (비동기 파이프라인)

실행 방법:
    python -m backend.langgraph_fuseki.main
    python -m backend.langgraph_fuseki.main --optimized  # 최적화 버전
"""

# 환경변수 설정은 config.py에서 자동 로드됨
from backend.langgraph_fuseki.config import PACKAGE_DIR
import os

from langgraph.graph import StateGraph, END
from backend.langgraph_fuseki.state import GraphState

# 노드 import
from backend.langgraph_fuseki.nodes.history_check_node import history_check_node
from backend.langgraph_fuseki.nodes.classify_node import query_classifier_node
from backend.langgraph_fuseki.nodes.user_intent_clarification_node import user_intent_clarification_node  # NEW: Phase 1
from backend.langgraph_fuseki.nodes.entity_expander_node import entity_expander_node
from backend.langgraph_fuseki.nodes.kg.semantic_expander_node import semantic_expander_node
from backend.langgraph_fuseki.nodes.kg.parallel_knowledge_retrieval_node import parallel_knowledge_retrieval_node
from backend.langgraph_fuseki.nodes.kg.path_evidence_aggregator_node import path_evidence_aggregator_node
from backend.langgraph_fuseki.nodes.generate_node import story_generator_node


def create_graph_flow(use_optimized: bool = None):
    """
    데이터 기반 창작 모드 랭그래프 (개선된 버전)
    
    Args:
        use_optimized: True면 최적화된 파이프라인 사용, None이면 환경변수 확인

    Flow:
    0. History Check → 역사 관련 여부 체크 (LLM 1회) ⭐NEW
       ├─ false → 조기 종료 (비용 절감)
       └─ true → Query Classifier로 진행
    1. Query Classifier → 질문 유형 분류 (causal/factual/deep_analysis/comparative) + 확장 방향 생성 ⭐UPDATED
    1.5. User Intent Clarification → 사용자 의도 확인 (Phase 1) ⭐NEW
       ├─ 사용자에게 2-4개 확장 방향 제시
       ├─ 사용자 선택 입력
       └─ 선택 방향 저장
    2. Entity Extractor → 하이브리드 엔티티 추출 (TTL + pgvector) + 방향 반영 ⭐UPDATED
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
    
    # 최적화 사용 여부 결정
    if use_optimized is None:
        use_optimized = os.getenv("USE_OPTIMIZED_PIPELINE", "false").lower() == "true"
    
    if use_optimized:
        print("[INFO] 최적화된 파이프라인 사용")
        try:
            # 비동기 그래프 우선 시도
            from backend.langgraph_fuseki.graph_async import create_async_graph_flow
            return create_async_graph_flow()
        except ImportError:
            try:
                # 기존 최적화 그래프 시도
                from backend.langgraph_fuseki.graph_optimized import create_optimized_graph_flow
                return create_optimized_graph_flow()
            except ImportError:
                print("[WARN] 최적화 모듈 없음, 기본 그래프 사용")
                use_optimized = False
    
    if not use_optimized:
        print("[INFO] 기본 순차 그래프 사용")

    workflow = StateGraph(GraphState)

    # ========== 노드 등록 ==========
    workflow.add_node("history_check", history_check_node)  # 0단계
    workflow.add_node("query_classifier", query_classifier_node)  # 1단계
    workflow.add_node("user_intent_clarification", user_intent_clarification_node)  # 1.5단계 (Phase 1)
    workflow.add_node("entity_expander", entity_expander_node)  # 2단계
    workflow.add_node("semantic_expander", semantic_expander_node)  # 3단계
    workflow.add_node("parallel_knowledge_retrieval", parallel_knowledge_retrieval_node)  # 4단계
    workflow.add_node("path_evidence_aggregator", path_evidence_aggregator_node)  # 5단계
    workflow.add_node("story_generator", story_generator_node)  # 6단계

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

    # 2. Query Classifier → User Intent Clarification (Phase 1)
    workflow.add_edge("query_classifier", "user_intent_clarification")

    # 2.5. User Intent Clarification → Entity Expander
    workflow.add_edge("user_intent_clarification", "entity_expander")

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


# 주의: 모듈 레벨에서 그래프 인스턴스를 생성하지 않음
# Django에서 import 시 자동 실행 방지
# 필요할 때는 create_graph_flow() 함수를 직접 호출하세요