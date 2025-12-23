"""
L3: Terminal Knowledge Contribution

- Terminal Triple Validity: 최종 triple이 질문에 기여하는지 평가
- Evidence Diversity: 5개 Thread에서 고르게 선택되었는지 평가
- Convergence Utilization: 수렴 노드가 답변에 활용되었는지 평가
"""

from typing import Dict, List, Any, Literal
from dataclasses import dataclass
import math


TripleContribution = Literal["기여함", "간접 기여", "무관함"]


@dataclass
class TripleEvaluation:
    """Triple 평가 결과"""
    subject: str
    predicate: str
    object: str
    contribution: TripleContribution
    score: float


class TerminalTripleValidityEvaluator:
    """Terminal Triple Validity 평가기 (LLM-as-Judge)"""

    def __init__(self, llm_judge):
        """
        Args:
            llm_judge: LLM Judge 인스턴스
        """
        self.llm_judge = llm_judge

    def evaluate(self, state_output: Dict[str, Any]) -> Dict[str, Any]:
        """Terminal Triple Validity 평가

        Args:
            state_output: LangGraph 실행 결과 (GraphState)

        Returns:
            {
                "score": float,  # 0.0 ~ 1.0
                "triple_evaluations": List[TripleEvaluation],
                "total_evidences": int,
                "contributing_evidences": int
            }
        """
        query = state_output.get("query", "")
        query_intent = state_output.get("query_intent", "")
        evidences = state_output.get("evidences", [])

        triple_evaluations = []

        for evidence in evidences:
            raw_data = evidence.get("raw_data", {})

            subject = raw_data.get("entity_label", "")
            predicate = raw_data.get("predicate", "")
            obj = raw_data.get("value_label", "")

            if not subject or not predicate or not obj:
                continue

            # LLM Judge로 Triple 기여도 평가
            contribution, reasoning = self.llm_judge.evaluate_triple_contribution(
                query=query,
                query_intent=query_intent,
                subject=subject,
                predicate=predicate,
                obj=obj
            )

            # 기여도별 점수
            contribution_scores = {
                "기여함": 1.0,
                "간접 기여": 0.5,
                "무관함": 0.0
            }
            score = contribution_scores.get(contribution, 0.0)

            triple_evaluations.append(TripleEvaluation(
                subject=subject,
                predicate=predicate,
                object=obj,
                contribution=contribution,
                score=score
            ))

        # 평균 점수 계산
        total_evidences = len(triple_evaluations)
        if total_evidences == 0:
            average_score = 1.0
        else:
            total_score = sum(te.score for te in triple_evaluations)
            average_score = total_score / total_evidences

        contributing_evidences = sum(1 for te in triple_evaluations if te.contribution in ["기여함", "간접 기여"])

        return {
            "score": average_score,
            "triple_evaluations": [vars(te) for te in triple_evaluations],
            "total_evidences": total_evidences,
            "contributing_evidences": contributing_evidences
        }


class EvidenceDiversityEvaluator:
    """Evidence Diversity 평가기 (Shannon Entropy)"""

    def __init__(self):
        pass

    def evaluate(self, state_output: Dict[str, Any]) -> Dict[str, Any]:
        """Evidence Diversity 평가

        Args:
            state_output: LangGraph 실행 결과 (GraphState)

        Returns:
            {
                "score": float,  # 0.0 ~ 1.0 (정규화된 Shannon Entropy)
                "thread_distribution": Dict[str, int],
                "entropy": float,
                "max_entropy": float
            }
        """
        evidences = state_output.get("evidences", [])

        # Thread별 분포 계산
        thread_distribution = {}
        for evidence in evidences:
            thread_type = evidence.get("type", "unknown")
            thread_distribution[thread_type] = thread_distribution.get(thread_type, 0) + 1

        # Shannon Entropy 계산
        total = len(evidences)
        entropy = 0.0

        if total > 0:
            for count in thread_distribution.values():
                p = count / total
                if p > 0:
                    entropy -= p * math.log2(p)

        # 최대 entropy (5개 Thread 기준)
        max_entropy = math.log2(5) if total > 0 else 1.0

        # 정규화된 점수
        diversity_score = entropy / max_entropy if max_entropy > 0 else 0.0

        return {
            "score": diversity_score,
            "thread_distribution": thread_distribution,
            "entropy": entropy,
            "max_entropy": max_entropy
        }


class ConvergenceUtilizationEvaluator:
    """Convergence Node Utilization 평가기 (query_type별 차등)"""

    # query_type별 중요도 가중치
    IMPORTANCE_WEIGHTS = {
        "causal": 1.5,
        "deep_analysis": 1.3,
        "comparative": 1.2,
        "factual": 1.0
    }

    def __init__(self):
        pass

    def evaluate(self, state_output: Dict[str, Any]) -> Dict[str, Any]:
        """Convergence Utilization 평가

        Args:
            state_output: LangGraph 실행 결과 (GraphState)

        Returns:
            {
                "score": float,  # 0.0 ~ 1.0
                "convergence_nodes": int,
                "mentioned_nodes": int,
                "utilization_rate": float,
                "importance_weight": float
            }
        """
        query_type = state_output.get("query_type", "factual")
        convergence_nodes = state_output.get("convergence_nodes", [])
        final_answer = state_output.get("final_answer", "")

        if not convergence_nodes:
            # 수렴 노드가 없으면 중립 점수
            return {
                "score": 1.0,
                "convergence_nodes": 0,
                "mentioned_nodes": 0,
                "utilization_rate": 1.0,
                "importance_weight": 1.0
            }

        # query_type별 가중치
        importance_weight = self.IMPORTANCE_WEIGHTS.get(query_type, 1.0)

        # 각 수렴 노드가 답변에 언급되었는지 확인
        mentioned_count = 0
        for node in convergence_nodes:
            node_label = node.get("label", "")
            if node_label and node_label in final_answer:
                mentioned_count += 1

        # Utilization Rate 계산
        utilization_rate = mentioned_count / len(convergence_nodes)

        # 최종 점수 (가중치 적용)
        final_score = utilization_rate * importance_weight
        final_score = min(final_score, 1.0)  # 1.0 상한

        return {
            "score": final_score,
            "convergence_nodes": len(convergence_nodes),
            "mentioned_nodes": mentioned_count,
            "utilization_rate": utilization_rate,
            "importance_weight": importance_weight
        }
