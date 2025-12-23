"""
L1: Ontology Schema Compliance

TBox Consistency Score: 확장 경로가 온톨로지 스키마를 위반하지 않는지 검증
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class TBoxViolation:
    """TBox 위반 사항"""
    subject: str
    predicate: str
    object: str
    violation_type: str  # "domain_mismatch" | "range_mismatch" | "invalid_relation"
    expected: str
    actual: str


class TBoxConsistencyEvaluator:
    """TBox Consistency 평가기"""

    def __init__(self, ontology_schema: Dict[str, Any]):
        """
        Args:
            ontology_schema: 온톨로지 스키마 정보
            {
                "classes": ["Person", "Event", "Place", ...],
                "properties": {
                    "participatesIn": {
                        "domain": "Person",
                        "range": "Event"
                    },
                    ...
                }
            }
        """
        self.schema = ontology_schema
        self.properties = ontology_schema.get("properties", {})

    def evaluate(self, state_output: Dict[str, Any]) -> Dict[str, Any]:
        """TBox Consistency 평가

        Args:
            state_output: LangGraph 실행 결과 (GraphState)

        Returns:
            {
                "score": float,  # 0.0 ~ 1.0
                "violations": List[TBoxViolation],
                "total_triples": int,
                "violation_count": int
            }
        """
        violations = []
        total_triples = 0

        # Stage 3: Semantic Expander에서 생성된 엔티티 확장 검증
        extracted_entities = state_output.get("extracted_entities", [])
        for entity in extracted_entities:
            expansion_method = entity.get("expansion_method")
            if expansion_method:
                # 확장 경로 검증 (예: causal_chain에서 사용된 relation)
                if expansion_method == "causal_chain":
                    relation = entity.get("causal_relation", "")
                    source_type = entity.get("source_type", "")
                    target_type = entity.get("type", "")

                    if relation and source_type and target_type:
                        total_triples += 1
                        violation = self._check_relation_consistency(
                            source_type, relation, target_type
                        )
                        if violation:
                            violations.append(violation)

        # Stage 5: Path Evidence Aggregator에서 추출된 경로 검증
        evidences = state_output.get("evidences", [])
        for evidence in evidences:
            raw_data = evidence.get("raw_data", {})

            # outgoing_relations 경로 검증
            if evidence.get("type") == "outgoing_relations":
                subject = raw_data.get("entity_label", "")
                predicate = raw_data.get("predicate", "")
                obj = raw_data.get("value_label", "")
                subject_type = raw_data.get("entity_type", "")
                obj_type = raw_data.get("value_type", "")

                if subject and predicate and obj:
                    total_triples += 1
                    violation = self._check_triple_consistency(
                        subject, subject_type, predicate, obj, obj_type
                    )
                    if violation:
                        violations.append(violation)

        # 점수 계산
        violation_count = len(violations)
        if total_triples == 0:
            score = 1.0  # 검증할 triple이 없으면 통과
        else:
            score = 1.0 - (violation_count / total_triples)

        return {
            "score": score,
            "violations": [vars(v) for v in violations],
            "total_triples": total_triples,
            "violation_count": violation_count
        }

    def _check_relation_consistency(
        self,
        subject_type: str,
        predicate: str,
        object_type: str
    ) -> TBoxViolation:
        """Relation의 domain/range 일치 검증"""
        if predicate not in self.properties:
            return None  # 알 수 없는 relation은 검증 스킵

        prop_info = self.properties[predicate]
        expected_domain = prop_info.get("domain", "")
        expected_range = prop_info.get("range", "")

        # Domain 검증
        if expected_domain and subject_type != expected_domain:
            return TBoxViolation(
                subject=subject_type,
                predicate=predicate,
                object=object_type,
                violation_type="domain_mismatch",
                expected=expected_domain,
                actual=subject_type
            )

        # Range 검증
        if expected_range and object_type != expected_range:
            return TBoxViolation(
                subject=subject_type,
                predicate=predicate,
                object=object_type,
                violation_type="range_mismatch",
                expected=expected_range,
                actual=object_type
            )

        return None

    def _check_triple_consistency(
        self,
        subject: str,
        subject_type: str,
        predicate: str,
        obj: str,
        obj_type: str
    ) -> TBoxViolation:
        """Triple의 일관성 검증"""
        return self._check_relation_consistency(subject_type, predicate, obj_type)
