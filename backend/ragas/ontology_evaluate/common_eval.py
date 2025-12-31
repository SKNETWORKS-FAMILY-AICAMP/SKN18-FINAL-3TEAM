"""
공통 평가 함수 모듈

모든 실험 스크립트에서 사용하는 표준 평가 로직
Grid Search를 기준으로 작성됨
"""

from typing import List, Dict, Any

from backend.ragas.ontology_evaluate.evaluators import (
    TBoxConsistencyEvaluator,
    IntentPreservationEvaluator,
    RelationCoherenceEvaluator,
    PropertyGroupSelectionEvaluator,
    TerminalTripleValidityEvaluator,
    EvidenceDiversityEvaluator,
    ConvergenceUtilizationEvaluator,
    AnswerQualityEvaluator
)
from backend.ragas.ontology_evaluate.evaluators.intent_aware_evaluator import IntentAwareEvaluator
from backend.ragas.ontology_evaluate.utils.llm_judge import LLMJudge


def get_ontology_schema() -> dict:
    """온톨로지 스키마 (하드코딩 - 표준)"""
    return {
        "classes": ["Person", "Event", "Place", "Organization", "Battle", "Dynasty"],
        "properties": {
            "participatesIn": {"domain": "Person", "range": "Event"},
            "built": {"domain": "Person", "range": "Place"},
            "causedBy": {"domain": "Event", "range": "Event"},
        }
    }


def evaluate_state(
    state_output: dict,
    llm_judge: LLMJudge,
    ontology_schema: dict,
    answer_quality_evaluator: AnswerQualityEvaluator,
    query: str = None,
    query_type: str = None,
    expected_property_groups: List[str] = None,
    use_intent_aware: bool = True
) -> dict:
    """GraphState에 대해 모든 평가 메트릭 실행

    Args:
        state_output: LangGraph 실행 결과
        llm_judge: LLM Judge 인스턴스
        ontology_schema: 온톨로지 스키마
        answer_quality_evaluator: Answer Quality 평가자
        query: 질문 텍스트
        query_type: 질문 유형 (factual, analytical, comparative)
        expected_property_groups: 예상 속성 그룹 리스트
        use_intent_aware: Intent-aware 평가 사용 여부

    Returns:
        {
            "raw_metrics": {...},
            "intent_aware": {...} or None,
            "llm_judge_quality": {...}
        }
    """
    # L1: TBox Consistency
    tbox_evaluator = TBoxConsistencyEvaluator(ontology_schema)
    tbox_result = tbox_evaluator.evaluate(state_output)

    # L2: Intent Preservation
    intent_evaluator = IntentPreservationEvaluator(llm_judge)
    intent_result = intent_evaluator.evaluate(state_output)

    # L2: Relation Coherence
    relation_evaluator = RelationCoherenceEvaluator()
    relation_result = relation_evaluator.evaluate(state_output)

    # L2: Property Group Selection
    property_group_result = None
    if expected_property_groups:
        property_group_evaluator = PropertyGroupSelectionEvaluator()
        property_group_result = property_group_evaluator.evaluate(state_output, expected_property_groups)

    # L3: Terminal Triple Validity
    triple_evaluator = TerminalTripleValidityEvaluator(llm_judge)
    triple_result = triple_evaluator.evaluate(state_output)

    # L3: Evidence Diversity
    diversity_evaluator = EvidenceDiversityEvaluator()
    diversity_result = diversity_evaluator.evaluate(state_output)

    # L3: Convergence Utilization
    convergence_evaluator = ConvergenceUtilizationEvaluator()
    convergence_result = convergence_evaluator.evaluate(state_output)

    # Raw metrics
    raw_metrics = {
        "tbox_consistency": tbox_result["score"],
        "intent_preservation": intent_result["score"],
        "relation_coherence": relation_result["score"],
        "triple_validity": triple_result["score"],
        "evidence_diversity": diversity_result["score"],
        "convergence_utilization": convergence_result["score"]
    }

    # Property Group Selection 점수 추가
    if property_group_result:
        raw_metrics["property_group_selection"] = property_group_result["score"]
    else:
        raw_metrics["property_group_selection"] = 0.5  # 기본값

    # Intent-aware 평가
    intent_aware_result = None
    if use_intent_aware and query_type:
        intent_aware_evaluator = IntentAwareEvaluator()
        user_selected_direction = state_output.get("user_selected_direction")
        intent_aware_result = intent_aware_evaluator.evaluate(
            query_type,
            raw_metrics,
            user_selected_direction
        )

    # LLM Judge Quality 평가
    llm_judge_quality = None
    if query:
        final_answer = state_output.get("final_answer", "")
        llm_judge_quality = answer_quality_evaluator.evaluate(query, query_type or "factual", final_answer)

    return {
        "raw_metrics": raw_metrics,
        "intent_aware": intent_aware_result,
        "llm_judge_quality": llm_judge_quality
    }


def build_test_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    실험 설정을 LangGraph test_config 형식으로 변환

    Args:
        config: 실험 설정
            - name: 실험 이름 (예: "baseline_quick_win", "v3_query_type_aware")
            - semantic_expander: {temporal: bool, causal_chain: bool, pgvector: bool}
            - aggregator_threads: {thread_name: bool}
            - entity_boost_mode: "normalized" | "exact" | None

    Returns:
        LangGraph test_config 형식
    """
    # Baseline vs v3.0 구분: experiment_name으로 판단
    experiment_name = config.get("name", "")
    use_query_type_aware = "v3" in experiment_name.lower() or "query_type_aware" in experiment_name.lower()
    
    return {
        "skip_clarification": True,
        "semantic_expander": config.get("semantic_expander", {}),
        "aggregator_threads": config.get("aggregator_threads", {}),
        "entity_boost_mode": config.get("entity_boost_mode"),
        "use_query_type_aware": use_query_type_aware,  # Baseline: False, v3.0: True
        "experiment_name": experiment_name  # 디버깅용
    }
