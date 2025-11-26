from typing import Any, Dict, List, NotRequired, TypedDict, Literal


class GraphState(TypedDict):
    """창작 모드용 상태 - Jena Rules 기반 역사 스토리텔링"""

    # ========== 입력 ==========
    query: str  # 사용자 질문

    # ========== 1단계: 질문 분석 ==========
    query_type: NotRequired[Literal["causal", "what_if", "deep_analysis"]]  # 질문 유형
    extracted_entities: NotRequired[List[Dict[str, str]]]  # 추출된 엔티티
    # [{"type": "Person", "name": "이순신", "uri": "hist:YiSunSin"}, ...]

    # ========== 2단계: SPARQL 생성 ==========
    sparql_query: NotRequired[str]  # 생성된 SPARQL 쿼리

    # ========== 3단계: 가상 시나리오 (What-if) ==========
    hypothetical_triples: NotRequired[List[str]]  # What-if용 가상 트리플
    # ["hist:YiSunSin hist:died hist:EarlyDeath .", ...]

    # ========== 4단계: Jena 추론 ==========
    inference_results: NotRequired[Dict[str, Any]]  # Jena Reasoner 결과
    # {"bindings": [...], "fuseki_endpoint": "..."}

    # ========== 5단계: 추론 경로 추출 ==========
    causal_chains: NotRequired[List[List[Dict[str, str]]]]  # 인과관계 체인들
    # [[{"subject": "도요토미", "predicate": "leadsTo", "object": "임진왜란"}, ...], ...]

    inference_paths: NotRequired[List[Dict[str, Any]]]  # 추론 경로 상세
    # [{"path": [...], "rule_used": "rule1_1", "confidence": 0.9}, ...]

    # ========== 6단계: 다중 근거 집계 ==========
    evidences: NotRequired[List[Dict[str, Any]]]  # 근거들
    # [{"type": "causal", "chain": [...], "weight": 0.8}, ...]

    # ========== 7단계: 최종 생성 ==========
    final_answer: NotRequired[str]  # 최종 스토리 답변
    answer_with_sources: NotRequired[Dict[str, Any]]  # 근거 포함 답변
    # {"story": "...", "sources": [...], "inference_rules": [...]}

    # ========== 메타 정보 ==========
    reasoning_mode: NotRequired[str]  # "creative" 고정
    executed_nodes: NotRequired[List[str]]  # 실행된 노드 추적
