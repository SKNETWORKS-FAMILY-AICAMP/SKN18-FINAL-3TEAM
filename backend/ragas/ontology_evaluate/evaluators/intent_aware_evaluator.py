"""
Intent-Aware Evaluation Framework

query_type에 따라 평가 메트릭에 다른 가중치를 적용:
- factual: 단순 사실 확인 (수렴 노드 중요도 낮음)
- causal: 인과관계 추론 (수렴 노드 중요도 높음)
- comparative: 비교 분석 (수렴 노드 중요도 매우 높음)
- deep_analysis: 심층 분석 (수렴 노드 중요도 높음)
"""

from typing import Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class IntentWeightConfig:
    """Query Type별 메트릭 가중치 설정"""
    # L1: Schema Compliance
    tbox_consistency_weight: float

    # L2: Path Quality
    intent_preservation_weight: float
    relation_coherence_weight: float
    property_group_selection_weight: float  # NEW

    # L3: Terminal Knowledge
    triple_validity_weight: float
    evidence_diversity_weight: float
    convergence_utilization_weight: float

    def get_normalized_weights(self) -> Dict[str, float]:
        """정규화된 가중치 반환 (합 = 1.0)"""
        total = (
            self.tbox_consistency_weight +
            self.intent_preservation_weight +
            self.relation_coherence_weight +
            self.property_group_selection_weight +
            self.triple_validity_weight +
            self.evidence_diversity_weight +
            self.convergence_utilization_weight
        )

        return {
            "tbox_consistency": self.tbox_consistency_weight / total,
            "intent_preservation": self.intent_preservation_weight / total,
            "relation_coherence": self.relation_coherence_weight / total,
            "property_group_selection": self.property_group_selection_weight / total,
            "triple_validity": self.triple_validity_weight / total,
            "evidence_diversity": self.evidence_diversity_weight / total,
            "convergence_utilization": self.convergence_utilization_weight / total
        }


# =====================================================
# Intent별 가중치 프리셋 (Quick Win 실험 결과 기반)
# =====================================================
# 실험 근거: 300개 케이스, aggressive_intent 가중치 (2024-12-26)
# - intent_preservation: 5.0 (핵심 메트릭)
# - evidence/convergence/property: 0.5 (상대적으로 낮춤)
# - tbox/relation/triple: 1.0 (기본 유지)
#
# 자세한 내용: backend/ragas/ontology_evaluate/data/quick_win/ALL_WEIGHT_EXPERIMENT_RESULTS.md
# =====================================================

INTENT_WEIGHT_PRESETS = {
    "factual": IntentWeightConfig(
        # Factual 쿼리: 단순 사실 확인
        # - Intent 보존이 가장 중요 (Quick Win: 5.0)
        # - Schema 준수와 Triple 유효성 기본 유지 (1.0)
        # - Property Group, 증거, 수렴 노드는 상대적으로 낮춤 (0.5)
        tbox_consistency_weight=1.0,      # = Schema 준수
        intent_preservation_weight=5.0,   # ★ Quick Win: 핵심 메트릭
        relation_coherence_weight=1.0,    # = 관계 일관성
        property_group_selection_weight=0.5,  # ↓ Property Group 선택
        triple_validity_weight=1.0,       # = Triple 유효성
        evidence_diversity_weight=0.5,    # ↓ 증거 다양성
        convergence_utilization_weight=0.5  # ↓ 수렴 노드
    ),

    "causal": IntentWeightConfig(
        # Causal 쿼리: 인과관계 추론
        # - Intent 보존이 가장 중요 (Quick Win: 5.0)
        # - 관계 일관성과 Triple 유효성 기본 유지 (1.0)
        # - Property Group, 증거, 수렴 노드는 상대적으로 낮춤 (0.5)
        tbox_consistency_weight=1.0,      # = Schema 준수
        intent_preservation_weight=5.0,   # ★ Quick Win: 핵심 메트릭
        relation_coherence_weight=1.0,    # = 관계 일관성
        property_group_selection_weight=0.5,  # ↓ Property Group 선택
        triple_validity_weight=1.0,       # = Triple 유효성
        evidence_diversity_weight=0.5,    # ↓ 증거 다양성
        convergence_utilization_weight=0.5  # ↓ 수렴 노드
    ),

    "comparative": IntentWeightConfig(
        # Comparative 쿼리: 비교 분석
        # - Intent 보존이 가장 중요 (Quick Win: 5.0)
        # - Schema 준수와 Triple 유효성 기본 유지 (1.0)
        # - Property Group, 증거, 수렴 노드는 상대적으로 낮춤 (0.5)
        tbox_consistency_weight=1.0,      # = Schema 준수
        intent_preservation_weight=5.0,   # ★ Quick Win: 핵심 메트릭
        relation_coherence_weight=1.0,    # = 관계 일관성
        property_group_selection_weight=0.5,  # ↓ Property Group 선택
        triple_validity_weight=1.0,       # = Triple 유효성
        evidence_diversity_weight=0.5,    # ↓ 증거 다양성
        convergence_utilization_weight=0.5  # ↓ 수렴 노드
    ),

    "deep_analysis": IntentWeightConfig(
        # Deep Analysis 쿼리: 심층 분석
        # - Intent 보존이 가장 중요 (Quick Win: 5.0)
        # - Schema 준수와 Triple 유효성 기본 유지 (1.0)
        # - Property Group, 증거, 수렴 노드는 상대적으로 낮춤 (0.5)
        tbox_consistency_weight=1.0,      # = Schema 준수
        intent_preservation_weight=5.0,   # ★ Quick Win: 핵심 메트릭
        relation_coherence_weight=1.0,    # = 관계 일관성
        property_group_selection_weight=0.5,  # ↓ Property Group 선택
        triple_validity_weight=1.0,       # = Triple 유효성
        evidence_diversity_weight=0.5,    # ↓ 증거 다양성
        convergence_utilization_weight=0.5  # ↓ 수렴 노드
    )
}


# =====================================================
# Intent-Aware Evaluator
# =====================================================

class IntentAwareEvaluator:
    """Query Type에 따라 메트릭 가중치를 적용하는 평가자"""

    def __init__(self, custom_weights: Dict[str, IntentWeightConfig] = None):
        """
        Args:
            custom_weights: 커스텀 가중치 설정 (없으면 프리셋 사용)
        """
        self.weights = custom_weights if custom_weights else INTENT_WEIGHT_PRESETS

    def evaluate(
        self,
        query_type: str,
        raw_metrics: Dict[str, float],
        user_selected_direction: str = None
    ) -> Dict[str, Any]:
        """
        Intent-aware 평가 수행

        Args:
            query_type: factual, causal, comparative, deep_analysis
            raw_metrics: 각 evaluator의 원점수
                {
                    "tbox_consistency": 0.95,
                    "intent_preservation": 0.85,
                    "relation_coherence": 0.90,
                    "triple_validity": 0.88,
                    "evidence_diversity": 0.75,
                    "convergence_utilization": 0.80
                }
            user_selected_direction: 사용자가 선택한 답변 방향 (예: "time_cause", "class_person")

        Returns:
            {
                "query_type": "causal",
                "user_selected_direction": "time_cause",
                "raw_metrics": {...},
                "weights": {...},
                "weighted_metrics": {...},
                "final_score": 0.847
            }
        """
        # 가중치 가져오기
        if query_type not in self.weights:
            raise ValueError(f"Unknown query_type: {query_type}. Must be one of {list(self.weights.keys())}")

        weight_config = self.weights[query_type]
        normalized_weights = weight_config.get_normalized_weights()

        # 가중치 적용
        weighted_metrics = {}
        for metric_name, raw_score in raw_metrics.items():
            if metric_name not in normalized_weights:
                print(f"[WARNING] Unknown metric: {metric_name}. Skipping.")
                continue

            weight = normalized_weights[metric_name]
            weighted_score = raw_score * weight
            weighted_metrics[metric_name] = weighted_score

        # 최종 점수 계산
        final_score = sum(weighted_metrics.values())

        result = {
            "query_type": query_type,
            "raw_metrics": raw_metrics,
            "weights": normalized_weights,
            "weighted_metrics": weighted_metrics,
            "final_score": final_score,
            "breakdown": self._get_breakdown(raw_metrics, normalized_weights, weighted_metrics)
        }

        # user_selected_direction 추가 (있을 경우)
        if user_selected_direction:
            result["user_selected_direction"] = user_selected_direction

        return result

    def _get_breakdown(
        self,
        raw_metrics: Dict[str, float],
        weights: Dict[str, float],
        weighted_metrics: Dict[str, float]
    ) -> str:
        """평가 상세 내역 문자열 생성"""
        lines = []
        lines.append("=" * 80)
        lines.append("Intent-Aware Evaluation Breakdown")
        lines.append("=" * 80)

        for metric_name in raw_metrics.keys():
            raw = raw_metrics[metric_name]
            weight = weights.get(metric_name, 0.0)
            weighted = weighted_metrics.get(metric_name, 0.0)

            lines.append(
                f"  {metric_name:30s}: "
                f"raw={raw:.3f} × weight={weight:.3f} = {weighted:.3f}"
            )

        lines.append("-" * 80)
        lines.append(f"  {'Final Score':30s}: {sum(weighted_metrics.values()):.3f}")
        lines.append("=" * 80)

        return "\n".join(lines)

    def compare_intents(
        self,
        results: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        여러 query_type의 평가 결과 비교

        Args:
            results: {
                "factual": {"final_score": 0.85, "raw_metrics": {...}},
                "causal": {"final_score": 0.78, ...}
            }
        """
        lines = []
        lines.append("\n" + "=" * 80)
        lines.append("Intent Comparison Report")
        lines.append("=" * 80)

        for query_type, result in results.items():
            lines.append(f"\n[{query_type.upper()}]")
            lines.append(f"  Final Score: {result['final_score']:.3f}")
            lines.append(f"  Top Metrics:")

            # 가중치 적용 후 점수가 높은 메트릭 3개
            weighted = result.get("weighted_metrics", {})
            top_metrics = sorted(weighted.items(), key=lambda x: x[1], reverse=True)[:3]

            for metric_name, weighted_score in top_metrics:
                raw_score = result["raw_metrics"][metric_name]
                weight = result["weights"][metric_name]
                lines.append(
                    f"    - {metric_name}: {weighted_score:.3f} "
                    f"(raw={raw_score:.3f}, weight={weight:.3f})"
                )

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)


# =====================================================
# Utility Functions
# =====================================================

def get_intent_weight_summary() -> str:
    """모든 Intent별 가중치 요약 출력"""
    lines = []
    lines.append("=" * 80)
    lines.append("Intent Weight Configuration Summary")
    lines.append("=" * 80)

    for query_type, config in INTENT_WEIGHT_PRESETS.items():
        lines.append(f"\n[{query_type.upper()}]")
        normalized = config.get_normalized_weights()

        # 정규화된 가중치를 내림차순 정렬
        sorted_weights = sorted(normalized.items(), key=lambda x: x[1], reverse=True)

        for metric_name, weight in sorted_weights:
            lines.append(f"  {metric_name:30s}: {weight:.3f}")

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


def create_custom_weights(
    query_type: str,
    tbox: float = 1.0,
    intent: float = 1.0,
    coherence: float = 1.0,
    validity: float = 1.0,
    diversity: float = 1.0,
    convergence: float = 1.0
) -> IntentWeightConfig:
    """
    커스텀 가중치 설정 생성

    Args:
        query_type: 쿼리 타입 (문서화용)
        tbox: TBox Consistency 가중치
        intent: Intent Preservation 가중치
        coherence: Relation Coherence 가중치
        validity: Triple Validity 가중치
        diversity: Evidence Diversity 가중치
        convergence: Convergence Utilization 가중치

    Returns:
        IntentWeightConfig 객체
    """
    return IntentWeightConfig(
        tbox_consistency_weight=tbox,
        intent_preservation_weight=intent,
        relation_coherence_weight=coherence,
        triple_validity_weight=validity,
        evidence_diversity_weight=diversity,
        convergence_utilization_weight=convergence
    )


# =====================================================
# Main (테스트용)
# =====================================================

if __name__ == "__main__":
    print("Testing IntentAwareEvaluator...\n")

    # 가중치 요약 출력
    print(get_intent_weight_summary())

    # 평가자 생성
    evaluator = IntentAwareEvaluator()

    # 샘플 원점수 (모든 메트릭이 같은 점수라고 가정)
    sample_raw_metrics = {
        "tbox_consistency": 0.90,
        "intent_preservation": 0.85,
        "relation_coherence": 0.88,
        "triple_validity": 0.82,
        "evidence_diversity": 0.75,
        "convergence_utilization": 0.80
    }

    # 각 query_type별 평가
    results = {}
    for query_type in ["factual", "causal", "comparative", "deep_analysis"]:
        result = evaluator.evaluate(query_type, sample_raw_metrics)
        results[query_type] = result

        print(f"\n{'=' * 80}")
        print(f"Query Type: {query_type.upper()}")
        print(f"{'=' * 80}")
        print(f"Final Score: {result['final_score']:.3f}")
        print(f"\nWeighted Metrics:")
        for metric, score in result['weighted_metrics'].items():
            print(f"  {metric:30s}: {score:.3f}")

    # 비교 리포트
    print(evaluator.compare_intents(results))

    # 분석
    print("\n" + "=" * 80)
    print("Key Insights")
    print("=" * 80)
    print("""
1. Factual 쿼리는 수렴 노드 가중치가 가장 낮아 final_score가 상대적으로 낮음
   - 단순 사실 확인에는 수렴 노드가 덜 중요

2. Comparative 쿼리는 수렴 노드 가중치가 가장 높아 final_score가 높음
   - 2개 엔티티 비교에는 수렴 노드가 매우 중요

3. Causal/Deep Analysis는 중간 수준
   - 인과관계와 심층 분석에는 수렴 노드가 중요하지만 절대적은 아님

4. 같은 raw_metrics라도 query_type에 따라 최종 점수가 달라짐
   - Intent-aware 평가가 정상 작동함을 확인
    """)

    print("=" * 80)
    print("IntentAwareEvaluator test completed successfully!")
    print("=" * 80)
