"""
History Check Node

사용자 질문이 조선시대 역사와 관련이 있는지 먼저 확인하는 노드.
비역사 질문은 조기 종료하여 비용 절감.
"""

import os
import json
from pathlib import Path
from langchain_openai import ChatOpenAI

from backend.langgraph_fuseki.state import GraphState
from backend.langgraph_fuseki.utils.token_utils import extract_and_accumulate_tokens


def history_check_node(state: GraphState) -> GraphState:
    """
    0단계: 역사 관련 여부 체크

    - 조선시대 역사 질문인지 LLM 1회 호출로 확인
    - is_historical=false 시 조기 종료 (비용 절감)
    - is_historical=true 시 Query Classifier로 진행
    """

    import time
    node_start = time.time()

    query = state.get("query", "")

    # LLM 초기화
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0
    )

    # 역사 관련 여부 판단 프롬프트
    history_check_prompt = f"""당신은 질문을 분류하는 전문가입니다.

## 질문
{query}

## 작업
이 질문이 **조선시대 한국 역사**와 관련이 있는지 판단하세요.

### 판단 기준:
- **true**: 조선시대의 인물, 사건, 제도, 정책, 장소, 문화 등에 대한 질문
- **false**: 현대, 다른 나라 역사, 과학, 수학, 프로그래밍, 일반 상식 등

### 예시 (false):
- "파이썬 프로그래밍 방법"
- "2024년 대선 결과"
- "태양계 행성은 몇 개?"
- "미국의 독립전쟁"
- "날씨가 어때?"

### 예시 (true):
- "조선의 환국"
- "경복궁을 지은 왕"
- "세종대왕의 업적"
- "을미사변의 원인"
- "정약용과 사도세자의 관계"

## 출력 형식 (JSON만)
{{
  "is_historical": true
}}

또는

{{
  "is_historical": false
}}
"""

    try:
        response = llm.invoke(history_check_prompt)
        
        # 토큰 사용량 추출 및 state에 누적
        token_update = extract_and_accumulate_tokens(state, response)
        state.update(token_update)
        
        content = response.content.strip()

        # JSON 파싱
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)
        is_historical = result.get("is_historical", True)

        print(f"\n{'='*70}")
        print(f"[Stage 0/6] 역사 관련 여부 체크 (History Check)")
        print(f"{'='*70}")
        print(f"  └─ 결과: {'✅ 역사 질문' if is_historical else '❌ 비역사 질문 (조기 종료)'}")

    except Exception as e:
        print(f"⚠️ 역사 관련 여부 판단 실패: {e}")
        # 오류 시 안전하게 True로 처리 (정상 플로우 진행)
        is_historical = True

    # 실행 시간 측정
    node_end = time.time()
    elapsed = node_end - node_start

    # 상태 업데이트
    state["is_historical"] = is_historical

    # 노드 실행 시간 기록
    if "node_execution_times" not in state:
        state["node_execution_times"] = {}
    state["node_execution_times"]["history_check"] = elapsed

    # 실행된 노드 추적
    if "executed_nodes" not in state:
        state["executed_nodes"] = []
    state["executed_nodes"].append("history_check")

    return state
