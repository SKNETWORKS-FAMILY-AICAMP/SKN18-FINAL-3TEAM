"""
LLM-as-Judge 구현

GPT-4를 Judge로 사용하여 평가
"""

from typing import Tuple, Literal
import os
from openai import OpenAI


IntentState = Literal["Preserve", "Enrich", "Drift", "Hallucinated"]
TripleContribution = Literal["기여함", "간접 기여", "무관함"]


class LLMJudge:
    """LLM-as-Judge 구현"""

    def __init__(self, model: str = "gpt-4o", api_key: str = None):
        """
        Args:
            model: 사용할 모델 ("gpt-4o", "gpt-4-turbo")
            api_key: API 키 (None이면 환경변수에서 로드)
        """
        self.model = model

        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")

        self.client = OpenAI(api_key=api_key)

    def evaluate_intent_preservation(
        self,
        query: str,
        query_intent: str,
        source_entity: str,
        target_entity: str,
        expansion_method: str
    ) -> Tuple[IntentState, str]:
        """Intent Preservation 평가

        Args:
            query: 원본 질문
            query_intent: 질문 의도
            source_entity: 출발 엔티티
            target_entity: 도착 엔티티
            expansion_method: 확장 방법

        Returns:
            (intent_state, reasoning): Intent 상태와 판단 근거
        """
        prompt = f"""당신은 온톨로지 기반 RAG 시스템의 평가자입니다.

질문: {query}
질문 의도: {query_intent}

확장 경로:
- 출발 엔티티: {source_entity}
- 도착 엔티티: {target_entity}
- 확장 방법: {expansion_method}

이 확장이 질문 의도를 유지하는지 평가하세요.

평가 기준:
1. **Preserve (1.0점)**: 의도 유지
   - 질문 의도와 직접적으로 관련된 확장

2. **Enrich (1.2점)**: 의도 심화 (보너스)
   - 질문 의도를 더 깊이 있게 탐구
   - 원인의 원인, 결과의 결과 등

3. **Drift (0.5점)**: 의도 전환 (페널티)
   - 질문과 관련은 있지만 의도에서 벗어남
   - 예: "임진왜란의 원인" → "인조반정" (시간적으로 너무 멀어짐)

4. **Hallucinated (0.0점)**: 의도 무관 (실패)
   - 질문 의도와 전혀 무관
   - 예: "임진왜란의 원인" → "이순신의 식습관"

다음 형식으로 답변하세요:
판단: [Preserve/Enrich/Drift/Hallucinated]
근거: [판단 이유를 1-2문장으로 설명]
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        result = response.choices[0].message.content.strip()

        # 결과 파싱
        intent_state = self._parse_intent_state(result)
        reasoning = self._extract_reasoning(result)

        return intent_state, reasoning

    def evaluate_triple_contribution(
        self,
        query: str,
        query_intent: str,
        subject: str,
        predicate: str,
        obj: str
    ) -> Tuple[TripleContribution, str]:
        """Terminal Triple 기여도 평가

        Args:
            query: 원본 질문
            query_intent: 질문 의도
            subject: Triple의 Subject
            predicate: Triple의 Predicate
            obj: Triple의 Object

        Returns:
            (contribution, reasoning): 기여도와 판단 근거
        """
        prompt = f"""당신은 온톨로지 기반 RAG 시스템의 평가자입니다.

질문: {query}
질문 의도: {query_intent}

Triple:
({subject}) -[{predicate}]-> ({obj})

이 Triple이 질문에 답하는 데 기여하는지 평가하세요.

평가 기준:
1. **기여함 (1.0점)**: 질문에 직접적으로 답함
   - 질문 의도와 직접 관련된 정보
   - 예: "세종대왕의 업적" → (세종대왕) -[built]-> (경복궁)

2. **간접 기여 (0.5점)**: 질문과 간접적으로 관련
   - 배경 정보나 맥락 제공
   - 예: "세종대왕의 업적" → (세종대왕) -[contemporaryWith]-> (성삼문)

3. **무관함 (0.0점)**: 질문과 무관
   - 답변에 도움이 되지 않음
   - 예: "세종대왕의 업적" → (세종대왕) -[marriedTo]-> (소헌왕후)

다음 형식으로 답변하세요:
판단: [기여함/간접 기여/무관함]
근거: [판단 이유를 1-2문장으로 설명]
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        result = response.choices[0].message.content.strip()

        # 결과 파싱
        contribution = self._parse_contribution(result)
        reasoning = self._extract_reasoning(result)

        return contribution, reasoning

    def _parse_intent_state(self, result: str) -> IntentState:
        """결과에서 Intent State 추출"""
        result_lower = result.lower()

        if "enrich" in result_lower:
            return "Enrich"
        elif "drift" in result_lower:
            return "Drift"
        elif "hallucinated" in result_lower:
            return "Hallucinated"
        else:
            return "Preserve"

    def _parse_contribution(self, result: str) -> TripleContribution:
        """결과에서 Contribution 추출"""
        if "무관함" in result or "무관" in result:
            return "무관함"
        elif "간접" in result:
            return "간접 기여"
        else:
            return "기여함"

    def _extract_reasoning(self, result: str) -> str:
        """결과에서 근거 추출"""
        lines = result.split("\n")
        for line in lines:
            if "근거:" in line:
                return line.replace("근거:", "").strip()

        # 근거가 명시되지 않으면 전체 결과 반환
        return result
