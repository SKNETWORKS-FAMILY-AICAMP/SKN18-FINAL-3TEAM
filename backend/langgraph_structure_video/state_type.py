"""
postgres에서 검색된 청크의 타입 정의
"""

from typing import TypedDict, Any, Dict

class EvidencePayload(TypedDict):
    content: str
    metadata: Dict[str, Any]

class Evidence(TypedDict):
    source: str          # "vector" | "graph"
    score: float
    payload: EvidencePayload
