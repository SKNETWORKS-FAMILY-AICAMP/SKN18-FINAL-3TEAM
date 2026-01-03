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


class PropertyGroupSelectionEvaluator:
    """Property Group 선택 적합성 평가기"""
    
    def __init__(self):
        pass
    
    def evaluate(self, state_output: Dict[str, Any], expected_property_groups: List[str]) -> Dict[str, Any]:
        """LangGraph가 선택한 property_groups와 예상 그룹의 일치도 평가
        
        Args:
            state_output: LangGraph 실행 결과 (GraphState)
            expected_property_groups: 예상되는 property group 목록
            
        Returns:
            {
                "score": float,  # 0.0 ~ 1.0
                "selected_groups": List[str],
                "expected_groups": List[str], 
                "matched_groups": List[str],
                "missing_groups": List[str],
                "extra_groups": List[str]
            }
        """
        # LangGraph에서 실제 선택된 property groups
        selected_groups = state_output.get("selected_property_groups", [])
        
        if not selected_groups and not expected_property_groups:
            return {
                "score": 1.0,
                "selected_groups": [],
                "expected_groups": [],
                "matched_groups": [],
                "missing_groups": [],
                "extra_groups": []
            }
        
        # 집합으로 변환하여 비교
        selected_set = set(selected_groups)
        expected_set = set(expected_property_groups)
        
        # 교집합, 차집합 계산
        matched_groups = list(selected_set & expected_set)
        missing_groups = list(expected_set - selected_set)  # 예상했지만 선택되지 않음
        extra_groups = list(selected_set - expected_set)    # 선택되었지만 예상하지 않음
        
        # 점수 계산: Jaccard Index (교집합 / 합집합)
        union_size = len(selected_set | expected_set)
        if union_size == 0:
            score = 1.0
        else:
            score = len(matched_groups) / union_size
        
        return {
            "score": score,
            "selected_groups": selected_groups,
            "expected_groups": expected_property_groups,
            "matched_groups": matched_groups,
            "missing_groups": missing_groups,
            "extra_groups": extra_groups
        }


class RelationCoherenceEvaluator:
    """Relation Semantic Coherence 평가기"""

    # Intent별 Valid Relations (property_groups.json 기반)
    VALID_RELATIONS_BY_INTENT = {
        # 인과관계 그룹 기반
        "원인": ["caused", "causes", "hasMotive", "hasPurpose", "initiatedBy", "leadsTo", "ledTo"],
        "결과": ["caused", "causes", "leadsTo", "ledTo"],
        "영향": ["caused", "causes", "leadsTo", "ledTo"],
        
        # 설립 그룹 기반  
        "건설": ["establishedBy", "founded", "reformed"],
        "설립": ["establishedBy", "founded", "reformed"],
        "창제": ["establishedBy", "founded", "reformed"],
        
        # 참여 그룹 기반
        "참전": ["participatesIn", "involved", "involves", "involvesPerson"],
        "참여": ["participatesIn", "involved", "involves", "involvesPerson"],
        
        # 직위 그룹 기반
        "통치": ["designatedAs", "hasRank", "hasTitle", "heldOffice", "occupation"],
        "재위": ["duringReignOf", "establishedDuringReign", "hasReignEnd", "hasReignStart", "reignedDuring"],
        
        # 연도 그룹 기반
        "시기": ["establishedInYear", "establishedYear", "hasYear", "occurredInYear"],
        "시대": ["contemporaryWith", "hasEra"],
        
        # 장소 그룹 기반
        "장소": ["heldAt", "occursAt", "originatedIn", "storedAt"],
        
        # 문서 그룹 기반
        "저술": ["authored", "compiled"],
        "기록": ["describes", "documents", "records"],
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
            thread_type = evidence.get("type", "")
            
            # Thread type별로 predicate 추출
            predicate = self._extract_predicate_from_evidence(evidence)

            if not predicate:
                continue

            total_count += 1

            # Intent와 일치 여부 확인
            is_coherent = self._is_relation_coherent(predicate, intent_keywords)

            if is_coherent:
                coherent_count += 1
            else:
                # Entity와 value 추출
                subject, _, obj = self._extract_triple_from_evidence(evidence)
                incoherent_relations.append({
                    "predicate": predicate,
                    "entity": subject or "",
                    "value": obj or "",
                    "thread_type": thread_type
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

    def _extract_predicate_from_evidence(self, evidence: Dict[str, Any]) -> str:
        """
        Evidence에서 predicate 추출
        
        Args:
            evidence: Evidence 객체 (type, raw_data 포함)
        
        Returns:
            predicate 문자열 또는 빈 문자열
        """
        thread_type = evidence.get("type", "")
        raw_data = evidence.get("raw_data", {})
        
        if isinstance(raw_data, dict):
            # path 객체에서 직접 추출
            predicate = raw_data.get("predicate", "")
            if predicate:
                return predicate
            
            # SPARQL binding 형식인 경우
            predicate_obj = raw_data.get("predicate", {})
            if isinstance(predicate_obj, dict):
                predicate_value = predicate_obj.get("value", "")
                if predicate_value:
                    return predicate_value.split("#")[-1]
        
        return ""

    def _extract_triple_from_evidence(self, evidence: Dict[str, Any]) -> tuple:
        """
        Evidence에서 Triple (subject, predicate, object) 추출
        
        Args:
            evidence: Evidence 객체 (type, raw_data 포함)
        
        Returns:
            (subject, predicate, object) 또는 (None, None, None) if 추출 불가
        """
        thread_type = evidence.get("type", "")
        raw_data = evidence.get("raw_data", {})
        
        if isinstance(raw_data, dict):
            # Thread type별로 다른 필드명 사용
            if thread_type in ["outgoing_relations", "incoming_relations"]:
                subject = raw_data.get("subject", "")
                predicate = raw_data.get("predicate", "")
                obj = raw_data.get("object", "")
                return (subject, predicate, obj)
            
            elif thread_type == "entity_properties":
                subject = raw_data.get("entity", "")
                predicate = raw_data.get("predicate", "")
                obj = raw_data.get("value", "")
                return (subject, predicate, obj)
            
            elif thread_type == "connected_entities":
                subject = raw_data.get("entity1", "")
                predicate = raw_data.get("predicate", "")
                obj = raw_data.get("entity2", "")
                return (subject, predicate, obj)
            
            # type_and_summary는 triple이 아니므로 스킵
            elif thread_type == "type_and_summary":
                return (None, None, None)
            
            # SPARQL binding 형식도 지원 (fallback)
            else:
                entity_label = raw_data.get("entityLabel", {})
                if isinstance(entity_label, dict):
                    subject = entity_label.get("value", "")
                else:
                    subject = raw_data.get("entity_label", "")
                
                predicate_obj = raw_data.get("predicate", {})
                if isinstance(predicate_obj, dict):
                    predicate = predicate_obj.get("value", "").split("#")[-1] if predicate_obj.get("value") else ""
                else:
                    predicate = raw_data.get("predicate", "")
                
                obj_label = raw_data.get("objectLabel", {})
                if isinstance(obj_label, dict):
                    obj = obj_label.get("value", "")
                else:
                    obj = raw_data.get("value_label", "") or raw_data.get("object", "")
                
                return (subject, predicate, obj)
        
        return (None, None, None)

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
