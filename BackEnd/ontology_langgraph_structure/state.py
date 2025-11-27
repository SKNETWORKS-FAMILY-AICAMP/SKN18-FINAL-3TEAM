from typing import Any, Dict, List, NotRequired, TypedDict, Literal


class GraphState(TypedDict):
    """창작 모드용 상태 - Jena Rules 기반 병렬 추론"""

    # ========== 입력 ==========
    query: str  # 사용자 질문

    # ========== 1단계: 질문 분석 ==========
    query_type: NotRequired[Literal["causal", "what_if", "deep_analysis"]]  # 질문 유형
    extracted_entities: NotRequired[List[Dict[str, Any]]]  # LLM에서 추출된 엔티티
    # [{"name": "이순신", "type": "Person"}, {"name": "명량해전", "type": "Event"}, ...]
    ontology_schema: NotRequired[Dict[str, Any]]  # 온톨로지 스키마 (정적 딕셔너리)
    # {"classes": ["Person", "Event", ...], "properties_by_class": {"Person": ["hist:participatesIn", ...], ...}}

    # ========== 2단계: 다중 쿼리 생성 ==========
    multi_queries: NotRequired[Dict[str, str]]  # 5가지 관점의 SPARQL 쿼리
    # {
    #     "causal": "SELECT ?a ?b WHERE {?a hist:leadsTo ?b}",
    #     "person": "SELECT ?p WHERE {?p hist:participatedIn ?event}",
    #     "temporal": "SELECT ?event ?year WHERE {?event hist:year ?year}",
    #     "pattern": "SELECT ?e1 ?e2 WHERE {?e1 hist:similarPattern ?e2}",
    #     "motive": "SELECT ?person ?motive WHERE {?person hist:motivation ?motive}"
    # }

    thread_weights: NotRequired[Dict[str, float]]  # 질문 유형별 Thread 가중치
    # {"causal": 0.30, "person": 0.20, ...}

    # ========== 3단계: 가상 시나리오 (What-if만) ==========
    hypothetical_triples: NotRequired[List[str]]  # What-if용 가상 트리플
    # ["hist:Wongyun hist:wonBattle hist:GadeokdoSea .", ...]

    # ========== 4단계: 병렬 추론 실행 ==========
    parallel_inference_results: NotRequired[Dict[str, Any]]  # 5개 Thread 추론 결과
    # {
    #     "causal": {"bindings": [...], "status": "success"},
    #     "person": {"bindings": [...], "status": "success"},
    #     "temporal": {"bindings": [...], "status": "success"},
    #     "pattern": {"bindings": [...], "status": "success"},
    #     "motive": {"bindings": [...], "status": "success"}
    # }

    # ========== 5단계: 추론 경로 추출 (각 Thread별) ==========
    inference_paths: NotRequired[Dict[str, List[Dict[str, Any]]]]  # Thread별 추론 경로
    # {
    #     "causal": [
    #         {"chain": [...], "weight": 0.9, "type": "causal"},
    #         ...
    #     ],
    #     "person": [...],
    #     ...
    # }

    # ========== 6단계: 다중 근거 통합 ==========
    evidences: NotRequired[List[Dict[str, Any]]]  # 통합된 근거 (가중치 정렬)
    # [
    #     {"rank": 1, "type": "causal", "description": "...", "weight": 0.90, "source": "Thread 1"},
    #     {"rank": 2, "type": "person", "description": "...", "weight": 0.85, "source": "Thread 2"},
    #     ...
    # ]

    # ========== 7단계: 최종 생성 ==========
    final_answer: NotRequired[str]  # 최종 스토리 답변
    answer_with_sources: NotRequired[Dict[str, Any]]  # 근거 포함 답변
    # {
    #     "story": "...",
    #     "evidences": [...],
    #     "query_type": "causal",
    #     "thread_weights": {...}
    # }

    # ========== 메타 정보 ==========
    reasoning_mode: NotRequired[str]  # "creative" 고정
    executed_nodes: NotRequired[List[str]]  # 실행된 노드 추적
    execution_time: NotRequired[float]  # 실행 시간 (초)
