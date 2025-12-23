from typing import Any, Dict, List, NotRequired, TypedDict, Literal


class GraphState(TypedDict):
    """창작 모드용 상태 - Parallel Knowledge Retrieval 기반 병렬 지식 검색"""

    # ========== 입력 ==========
    query: str  # 사용자 질문

    # ========== 1단계: 질문 분석 (Query Classifier) ==========
    is_historical: NotRequired[bool]  # 역사 관련 질문 여부 (False면 조기 종료)
    query_type: NotRequired[Literal["causal", "what_if", "deep_analysis"]]  # 질문 유형
    query_intent: NotRequired[str]  # 핵심 의도 (예: "궁궐을 건설한 왕 찾기")

    # 프로퍼티 그룹 선택
    selected_property_groups: NotRequired[List[str]]  # 선택된 프로퍼티 그룹 (예: ["건설", "설립", "통치"])
    selected_properties: NotRequired[List[str]]  # 선택된 프로퍼티 목록 (예: ["built", "builtBy", "founded", ...])

    # 키워드 확장
    expanded_keywords: NotRequired[List[str]]  # 확장된 키워드 리스트 (예: ["경복궁", "창덕궁", "태조", "세종"])
    expanded_keywords_dict: NotRequired[Dict[str, List[str]]]  # 원본 매핑 (예: {"궁궐": ["경복궁", "창덕궁"], "왕": ["태조", "세종"]})

    # ========== 2단계: 엔티티 추출 (Entity Extractor) ==========
    extracted_entities: NotRequired[List[Dict[str, Any]]]  # 추출된 엔티티
    # [{"name": "이순신", "type": "Person", "uri": "hist:Person_이순신", "matched": True}, ...]
    ontology_schema: NotRequired[Dict[str, Any]]  # 온톨로지 스키마 (정적 딕셔너리)
    # {"classes": ["Person", "Event", ...], "properties_by_class": {"Person": ["hist:participatesIn", ...], ...}}
    ttl_data: NotRequired[Dict[str, Any]]  # TTL 데이터 (캐시됨)

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

    # ========== 4단계: Parallel Knowledge Retrieval (병렬 지식 검색) ==========
    parallel_inference_results: NotRequired[Dict[str, Any]]  # 5개 Thread 지식 검색 결과
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
    node_execution_times: NotRequired[Dict[str, float]]  # 노드별 실행 시간 (초)
    
    # ========== 토큰 사용량 추적 ==========
    total_tokens: NotRequired[int]  # 총 토큰 사용량
    prompt_tokens: NotRequired[int]  # 프롬프트 토큰 사용량
    completion_tokens: NotRequired[int]  # 완료 토큰 사용량

    # ========== 테스트 설정 (RAGAS 평가용) ==========
    test_config: NotRequired[Dict[str, Any]]  # 테스트 모드 설정
    # {
    #     "semantic_expander": {"temporal": True, "category": False, "causal_chain": False, "pgvector": False},
    #     "aggregator_threads": {"outgoing_relations": True, "incoming_relations": False, ...},
    #     "entity_boost_mode": "exact_match"  # "exact_match" | "partial_match" | "normalized_match" | "penalty_match"
    # }
