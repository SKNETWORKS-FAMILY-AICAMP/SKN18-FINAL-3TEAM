"""
Query Classifier Node

사용자 질문을 분석하여 유형 분류:
- causal: 인과관계 질문 ("왜 ~했을까?", "어떻게 ~했나?")
- what_if: 가상 시나리오 ("만약 ~했다면?", "~가 없었다면?")
- deep_analysis: 심화 질문 ("진짜 이유는?", "숨은 의도는?")
"""

import os
from typing import Literal
from langgraph_structure.state import GraphState
from langchain_openai import ChatOpenAI


def query_classifier_node(state: GraphState) -> GraphState:
    """질문 유형 분류"""

    query = state.get("query", "")

    # LLM을 사용한 질문 분류
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0
    )

    classification_prompt = f"""당신은 역사 질문을 분류하는 전문가입니다.

다음 질문을 3가지 유형 중 하나로 분류하세요:

1. causal (인과관계): "왜 ~했을까?", "어떤 영향을 미쳤나?", "~의 결과는?"
2. what_if (가상 시나리오): "만약 ~했다면?", "~가 없었다면?", "~가 성공했다면?"
3. deep_analysis (심화 분석): "진짜 이유는?", "숨은 의도는?", "이면에는?"

질문: {query}

답변은 반드시 다음 중 하나만 출력하세요: causal, what_if, deep_analysis
"""

    try:
        response = llm.invoke(classification_prompt)
        query_type = response.content.strip().lower()

        # 검증
        if query_type not in ["causal", "what_if", "deep_analysis"]:
            query_type = "causal"  # 기본값

    except Exception as e:
        print(f"⚠️ 질문 분류 실패: {e}")
        query_type = "causal"  # 기본값

    print(f"📌 질문 유형: {query_type}")

    return {
        **state,
        "query_type": query_type,
        "executed_nodes": state.get("executed_nodes", []) + ["query_classifier"]
    }
