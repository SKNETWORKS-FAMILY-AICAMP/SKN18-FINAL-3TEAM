"""
L2: Expansion Path Quality

- Intent Preservation Score: 각 hop에서 질문 의도가 유지되는지 평가
- Relation Semantic Coherence: relation이 질문 의도와 일관되는지 평가
"""

from typing import Dict, List, Any, Literal
from dataclasses import dataclass


IntentState = Literal["Preserve", "Enrich", "Drift", "Hallucinated"]


@dataclass
class IntentHop:
    """Intent 상태 변화 hop"""
    source_entity: str
    target_entity: str
    expansion_method: str
    intent_state: IntentState
    score: float


class IntentPreservationEvaluator:
    """Intent Preservation 평가기 (LLM-as-Judge)"""

    def __init__(self, llm_judge):
        """
        Args:
            llm_judge: LLM Judge 인스턴스 (utils/llm_judge.py)
        """
        self.llm_judge = llm_judge

    def evaluate(self, state_output: Dict[str, Any]) -> Dict[str, Any]:
        """Intent Preservation 평가

        Args:
            state_output: LangGraph 실행 결과 (GraphState)

        Returns:
            {
                "score": float,  # 0.0 ~ 1.2 (Enrich 보너스 포함)
                "hops": List[IntentHop],
                "hop_count": int,
                "average_score": float
            }
        """
        query = state_output.get("query", "")
        query_intent = state_output.get("query_intent", "")
        extracted_entities = state_output.get("extracted_entities", [])

        # Stage 3 (Semantic Expander)에서 생성된 확장 hop 평가
        hops = []

        for entity in extracted_entities:
            expansion_method = entity.get("expansion_method")
            if not expansion_method:
                continue  # 원본 엔티티는 스킵

            source = entity.get("expansion_source", "")
            target = entity.get("name", "")

            if not source or not target:
                continue

            # LLM Judge로 Intent 상태 평가
            intent_state, reasoning = self.llm_judge.evaluate_intent_preservation(
                query=query,
                query_intent=query_intent,
                source_entity=source,
                target_entity=target,
                expansion_method=expansion_method
            )

            # Intent 상태별 점수
            state_scores = {
                "Preserve": 1.0,
                "Enrich": 1.2,
                "Drift": 0.5,
                "Hallucinated": 0.0
            }
            score = state_scores.get(intent_state, 1.0)

            hops.append(IntentHop(
                source_entity=source,
                target_entity=target,
                expansion_method=expansion_method,
                intent_state=intent_state,
                score=score
            ))

        # 평균 점수 계산
        hop_count = len(hops)
        if hop_count == 0:
            average_score = 1.0
        else:
            total_score = sum(hop.score for hop in hops)
            average_score = total_score / hop_count

        return {
            "score": average_score,
            "hops": [vars(hop) for hop in hops],
            "hop_count": hop_count,
            "average_score": average_score
        }


class RelationCoherenceEvaluator:
    """Relation Semantic Coherence 평가기"""

    # Intent별 Valid Relations (도메인 지식)
    VALID_RELATIONS_BY_INTENT = {
        "원인": ["causedBy", "leadsTo", "influences", "triggeredBy"],
        "업적": ["built", "established", "achieved", "founded", "created"],
        "결과": ["leadsTo", "causes", "affects", "results"],
        "관계": ["participatesIn", "involvesPerson", "relatedTo", "associatedWith"],
        "건설": ["built", "builtBy", "constructed", "established"],
        "통치": ["ruled", "governed", "reigned", "administered"],
    }

    def __init__(self):
        pass

    def evaluate(self, state_output: Dict[str, Any]) -> Dict[str, Any]:
        """Relation Coherence 평가

        Args:
            state_output: LangGraph 실행 결과 (GraphState)

        Returns:
            {
                "score": float,  # 0.0 ~ 1.0
                "coherent_relations": int,
                "total_relations": int,
                "incoherent_relations": List[Dict]
            }
        """
        query_intent = state_output.get("query_intent", "")
        evidences = state_output.get("evidences", [])

        # 질문 의도에서 키워드 추출 (간단한 매칭)
        intent_keywords = self._extract_intent_keywords(query_intent)

        # 각 Thread에서 사용된 relation 수집
        coherent_count = 0
        total_count = 0
        incoherent_relations = []

        for evidence in evidences:
            raw_data = evidence.get("raw_data", {})
            predicate = raw_data.get("predicate", "")

            if not predicate:
                continue

            total_count += 1

            # Intent와 일치 여부 확인
            is_coherent = self._is_relation_coherent(predicate, intent_keywords)

            if is_coherent:
                coherent_count += 1
            else:
                incoherent_relations.append({
                    "predicate": predicate,
                    "entity": raw_data.get("entity_label", ""),
                    "value": raw_data.get("value_label", ""),
                    "thread_type": evidence.get("type", "")
                })

        # 점수 계산
        if total_count == 0:
            score = 1.0
        else:
            score = coherent_count / total_count

        return {
            "score": score,
            "coherent_relations": coherent_count,
            "total_relations": total_count,
            "incoherent_relations": incoherent_relations
        }

    def _extract_intent_keywords(self, query_intent: str) -> List[str]:
        """질문 의도에서 키워드 추출"""
        # 간단한 키워드 매칭 (실제로는 LLM 사용 가능)
        keywords = []
        for intent_key in self.VALID_RELATIONS_BY_INTENT.keys():
            if intent_key in query_intent:
                keywords.append(intent_key)
        return keywords

    def _is_relation_coherent(self, predicate: str, intent_keywords: List[str]) -> bool:
        """Relation이 Intent와 일관되는지 확인"""
        for keyword in intent_keywords:
            valid_relations = self.VALID_RELATIONS_BY_INTENT.get(keyword, [])
            if predicate in valid_relations:
                return True

        # 키워드가 없으면 통과
        if not intent_keywords:
            return True

        return False
