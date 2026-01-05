"""
Thinking Mode 이벤트 생성 유틸리티

프론트엔드 타임라인 연속성을 위한 통일된 이벤트 구조 제공
"""

import time
from typing import Optional, Dict, Any, Callable


def create_thinking_event(
    event_type: str,
    title: str,
    stage_number: int,
    stage_name: str,
    data: Optional[Dict[str, Any]] = None,
    is_pre_clarification: bool = True
) -> Dict[str, Any]:
    """
    통일된 thinking 이벤트 생성

    Args:
        event_type: 이벤트 타입 (예: 'question_analysis_started')
        title: 이벤트 제목
        stage_number: 단계 번호 (0-6)
        stage_name: 단계 이름 (예: 'Stage 1: Query Classifier')
        data: 추가 데이터
        is_pre_clarification: 재질문 전/후 구분

    Returns:
        통일된 구조의 thinking 이벤트
    """
    return {
        "type": "thinking",
        "event": event_type,
        "title": title,
        "stage": {
            "number": stage_number,
            "name": stage_name,
            "is_pre_clarification": is_pre_clarification
        },
        "data": data or {},
        "timestamp": time.time()
    }


def send_thinking_event(
    callback: Optional[Callable],
    event_type: str,
    title: str,
    stage_number: int,
    stage_name: str,
    data: Optional[Dict[str, Any]] = None,
    is_pre_clarification: bool = True
) -> None:
    """
    thinking 콜백으로 이벤트 전송 (콜백이 있을 때만)

    Args:
        callback: thinking_callback 함수 (event_name, event_data 두 인자를 받음)
        event_type: 이벤트 타입
        title: 이벤트 제목
        stage_number: 단계 번호
        stage_name: 단계 이름
        data: 추가 데이터
        is_pre_clarification: 재질문 전/후 구분
    """
    if callback and callable(callback):
        # 이벤트 데이터 구성 (event 필드 제외)
        event_data = {
            "title": title,
            "stage": {
                "number": stage_number,
                "name": stage_name,
                "is_pre_clarification": is_pre_clarification
            },
            "data": data or {},
            "timestamp": time.time()
        }
        try:
            # thinking_callback(event_name, event_data) 형식으로 호출
            callback(event_type, event_data)
        except Exception as e:
            print(f"  [Warning] Thinking callback failed: {e}")


STAGE_DEFINITIONS = {
    "history_check": {
        "number": 0,
        "name": "Stage 0: History Check"
    },
    "query_classifier": {
        "number": 1,
        "name": "Stage 1: Query Classifier"
    },
    "entity_expander": {
        "number": 2,
        "name": "Stage 2: Entity Expander"
    },
    "semantic_expander": {
        "number": 3,
        "name": "Stage 3: Semantic Expander"
    },
    "knowledge_retrieval": {
        "number": 4,
        "name": "Stage 4: Knowledge Retrieval"
    },
    "evidence_aggregator": {
        "number": 5,
        "name": "Stage 5: Evidence Aggregator"
    },
    "answer_generator": {
        "number": 6,
        "name": "Stage 6: Answer Generator"
    }
}


def get_stage_info(stage_key: str) -> Dict[str, Any]:
    """
    단계 정보 가져오기

    Args:
        stage_key: 단계 키 (예: 'query_classifier')

    Returns:
        단계 번호와 이름
    """
    return STAGE_DEFINITIONS.get(
        stage_key,
        {"number": -1, "name": "Unknown Stage"}
    )
