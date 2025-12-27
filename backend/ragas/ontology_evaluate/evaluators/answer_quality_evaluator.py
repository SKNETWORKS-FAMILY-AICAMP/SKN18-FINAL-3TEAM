"""
LLM Judge 기반 답변 품질 평가 Evaluator
"""

import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# 프로젝트 루트에서 환경변수 로드
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class AnswerQualityEvaluator:
    """LLM Judge를 사용한 답변 품질 평가"""

    def __init__(self, model: str = None, api_key: str = None):
        if model is None:
            model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")

        self.model = model
        self.client = OpenAI(api_key=api_key)

    def evaluate(self, query: str, query_type: str, answer: str) -> dict:
        """
        답변 품질 종합 평가

        Args:
            query: 질문
            query_type: 질문 유형
            answer: 시스템 답변

        Returns:
            {
                "completeness": 0.0~1.0,
                "information_richness": 0.0~1.0,
                "factual_accuracy": 0.0~1.0,
                "coherence": 0.0~1.0,
                "helpfulness": 0.0~1.0,
                "overall_score": 0.0~1.0,
                "reasoning": str
            }
        """
        if not answer:
            return {
                "completeness": 0,
                "information_richness": 0,
                "factual_accuracy": 0,
                "coherence": 0,
                "helpfulness": 0,
                "overall_score": 0,
                "reasoning": "답변 없음",
                "error": True
            }

        prompt = f"""당신은 한국사 전문가이자 RAG 시스템 평가자입니다.

질문: {query}
질문 유형: {query_type}

시스템 답변:
{answer}

다음 기준으로 답변 품질을 평가하세요 (각 0.0~1.0):

1. **completeness** (완성도): 질문에 충분히 답했는가?
   - 1.0: 질문의 모든 측면에 완벽히 답함
   - 0.5: 핵심은 답했지만 일부 누락
   - 0.0: 질문에 제대로 답하지 못함

2. **information_richness** (정보 풍부함): 추가로 유용한 정보를 제공했는가?
   - 1.0: 관련 배경, 맥락, 연결 정보까지 풍부하게 제공
   - 0.5: 기본 정보만 제공
   - 0.0: 정보가 빈약함

3. **factual_accuracy** (사실 정확성): 역사적 사실과 일치하는가?
   - 1.0: 모든 내용이 사실과 일치
   - 0.5: 대부분 맞지만 일부 오류
   - 0.0: 심각한 사실 오류

4. **coherence** (논리성): 답변이 논리적으로 일관되는가?
   - 1.0: 논리적으로 완벽하게 연결됨
   - 0.5: 대체로 논리적이지만 일부 비약
   - 0.0: 논리적 연결이 부족

5. **helpfulness** (유용성): 사용자에게 실제로 도움이 되는가?
   - 1.0: 매우 도움됨, 이해하기 쉬움
   - 0.5: 어느 정도 도움됨
   - 0.0: 도움이 안 됨

다음 JSON 형식으로만 응답하세요:
{{
    "completeness": 0.X,
    "information_richness": 0.X,
    "factual_accuracy": 0.X,
    "coherence": 0.X,
    "helpfulness": 0.X,
    "reasoning": "평가 근거 요약 (2-3문장)"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # overall_score 계산 (가중 평균)
            weights = {
                "completeness": 0.25,
                "information_richness": 0.20,
                "factual_accuracy": 0.25,
                "coherence": 0.15,
                "helpfulness": 0.15
            }

            overall = sum(
                result.get(k, 0) * w
                for k, w in weights.items()
            )
            result["overall_score"] = round(overall, 4)

            return result

        except Exception as e:
            return {
                "completeness": 0,
                "information_richness": 0,
                "factual_accuracy": 0,
                "coherence": 0,
                "helpfulness": 0,
                "overall_score": 0,
                "reasoning": f"평가 실패: {str(e)}",
                "error": True
            }
