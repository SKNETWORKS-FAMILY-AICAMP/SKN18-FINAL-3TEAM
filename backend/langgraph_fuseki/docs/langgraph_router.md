## 핵심 질문 정리

1. **Thinking 모드 ON** : Fuseki (RDF) + LangGraph (현재 시스템)
2. **Thinking 모드 OFF** : Neo4j + pgvector 하이브리드
3. **문제** : 같은 세션 내에서 모드 전환 시 메모리 공유 가능 여부?

---

## 답변: 가능하지만 **공통 메모리 레이어** 필요

### 1. LangGraph Checkpointing의 한계

**문제점** :

```python
# LangGraph Checkpointing은 GraphState를 직렬화/역직렬화
# → GraphState 구조가 다르면 호환 불가

# Thinking 모드 ON (Fuseki)
class FusekiGraphState(TypedDict):
    query: str
    extracted_entities: List[Dict]
    sparql_results: Dict
    # ... Fuseki 전용 필드

# Thinking 모드 OFF (Neo4j)
class Neo4jGraphState(TypedDict):
    query: str
    cypher_results: Dict
    graph_embeddings: List[float]
    # ... Neo4j 전용 필드
```

**결론** : LangGraph Checkpointing만으로는 **서로 다른 그래프 시스템 간 메모리 공유 불가능**

---

## 해결 방안: 3단계 메모리 아키텍처

### 아키텍처 개요

```
┌─────────────────────────────────────────────────────────┐
│                   Session Memory Layer                   │
│  (공통 대화 컨텍스트: Redis 또는 PostgreSQL)              │
│  - thread_id: "session_123"                              │
│  - conversation_history: [Q1, A1, Q2, A2, ...]          │
│  - user_context: {"previous_topic": "명성황후 시해"}     │
│  - mode_history: ["thinking", "normal", "thinking"]      │
└─────────────────────────────────────────────────────────┘
                            ↕
        ┌───────────────────────────────────────┐
        │    Mode Router (모드 전환 로직)       │
        │    - thinking_mode: bool              │
        │    - select_graph_system()            │
        └───────────────────────────────────────┘
                ↙                       ↘
┌─────────────────────┐       ┌─────────────────────┐
│  Thinking Mode      │       │  Normal Mode        │
│  (Fuseki + SPARQL)  │       │  (Neo4j + pgvector) │
├─────────────────────┤       ├─────────────────────┤
│ LangGraph           │       │ LangGraph           │
│ Checkpointing       │       │ Checkpointing       │
│ (모드 전용 상태)     │       │ (모드 전용 상태)     │
└─────────────────────┘       └─────────────────────┘
```

---

## 구현 방법

### 1. 공통 Session Memory (Redis 권장)

**이유** :

- ✅ 두 모드 간 빠른 메모리 공유
- ✅ TTL로 세션 자동 만료
- ✅ 분산 환경에서도 동작

```python
# backend/langgraph_fuseki/memory/session_manager.py

import redis
import json
from typing import Dict, Any, List
from datetime import datetime

class SessionMemoryManager:
    """
    공통 세션 메모리 관리자
    - Thinking 모드와 Normal 모드 간 대화 컨텍스트 공유
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.session_ttl = 3600 * 24  # 24시간

    def save_conversation_turn(
        self,
        thread_id: str,
        query: str,
        answer: str,
        mode: str,  # "thinking" or "normal"
        metadata: Dict[str, Any] = None
    ):
        """대화 턴 저장"""
        key = f"session:{thread_id}"

        # 기존 대화 기록 로드
        session_data = self.get_session(thread_id)

        # 새로운 턴 추가
        turn = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "answer": answer,
            "mode": mode,
            "metadata": metadata or {}
        }

        session_data["conversation_history"].append(turn)
        session_data["mode_history"].append(mode)
        session_data["last_mode"] = mode
        session_data["last_updated"] = datetime.now().isoformat()

        # 최근 주제 추출 (간단한 예시)
        if "user_context" not in session_data:
            session_data["user_context"] = {}

        # Stage 1.5에서 선택한 방향 저장
        if metadata and "user_selected_direction" in metadata:
            session_data["user_context"]["last_selected_direction"] = metadata["user_selected_direction"]

        # Redis 저장
        self.redis_client.setex(
            key,
            self.session_ttl,
            json.dumps(session_data, ensure_ascii=False)
        )

    def get_session(self, thread_id: str) -> Dict[str, Any]:
        """세션 전체 데이터 로드"""
        key = f"session:{thread_id}"
        data = self.redis_client.get(key)

        if data:
            return json.loads(data)
        else:
            # 새 세션 초기화
            return {
                "thread_id": thread_id,
                "conversation_history": [],
                "mode_history": [],
                "last_mode": None,
                "user_context": {},
                "created_at": datetime.now().isoformat()
            }

    def get_conversation_context(self, thread_id: str, last_n: int = 5) -> str:
        """최근 N개 대화 요약 (모드 무관)"""
        session = self.get_session(thread_id)
        history = session["conversation_history"][-last_n:]

        context = []
        for turn in history:
            context.append(f"[{turn['mode'].upper()}] Q: {turn['query']}")
            context.append(f"A: {turn['answer'][:200]}...")  # 답변 200자까지만

        return "\n".join(context)

    def get_previous_topic(self, thread_id: str) -> str:
        """이전 대화 주제 추출"""
        session = self.get_session(thread_id)

        if session["conversation_history"]:
            last_turn = session["conversation_history"][-1]
            return last_turn["query"]

        return None
```

---

### 2. Mode Router (모드 전환 로직)

```python
# backend/langgraph_fuseki/mode_router.py

from typing import Dict, Any
from enum import Enum

class GraphMode(Enum):
    THINKING = "thinking"  # Fuseki + SPARQL (현재 시스템)
    NORMAL = "normal"      # Neo4j + pgvector

class ModeRouter:
    """
    모드 선택 및 그래프 시스템 라우팅
    """

    def __init__(self, session_manager: SessionMemoryManager):
        self.session_manager = session_manager

    def select_mode(self, thread_id: str, thinking_mode: bool) -> GraphMode:
        """
        사용자 선택에 따라 모드 결정

        Args:
            thread_id: 세션 ID
            thinking_mode: Thinking 모드 활성화 여부

        Returns:
            선택된 모드
        """
        session = self.session_manager.get_session(thread_id)

        # 모드 전환 감지
        last_mode = session.get("last_mode")
        current_mode = GraphMode.THINKING if thinking_mode else GraphMode.NORMAL

        if last_mode and last_mode != current_mode.value:
            print(f"⚠️ 모드 전환 감지: {last_mode} → {current_mode.value}")
            # 모드 전환 시 컨텍스트 유지 로직 실행
            self._handle_mode_switch(thread_id, last_mode, current_mode.value)

        return current_mode

    def _handle_mode_switch(self, thread_id: str, from_mode: str, to_mode: str):
        """
        모드 전환 시 컨텍스트 브리지

        예시:
        - Thinking 모드에서 추출한 엔티티 → Normal 모드에서 재사용
        - Normal 모드의 대화 히스토리 → Thinking 모드 프롬프트에 포함
        """
        session = self.session_manager.get_session(thread_id)

        # 이전 대화 요약
        previous_context = self.session_manager.get_conversation_context(thread_id, last_n=3)

        # 모드 전환 메타데이터 저장
        session["user_context"]["mode_switch"] = {
            "from": from_mode,
            "to": to_mode,
            "previous_context": previous_context
        }

        # Redis 업데이트
        key = f"session:{thread_id}"
        self.session_manager.redis_client.setex(
            key,
            self.session_manager.session_ttl,
            json.dumps(session, ensure_ascii=False)
        )
```

---

### 3. 통합 Workflow

```python
# backend/langgraph_fuseki/main.py (수정)

import uuid
from memory.session_manager import SessionMemoryManager
from mode_router import ModeRouter, GraphMode
from graph_fuseki import create_fuseki_graph  # Thinking 모드
from graph_neo4j import create_neo4j_graph    # Normal 모드 (추후 구현)

def main():
    # 공통 메모리 초기화
    session_manager = SessionMemoryManager(redis_url="redis://localhost:6379")
    mode_router = ModeRouter(session_manager)

    # 세션 ID 생성 (사용자별)
    thread_id = str(uuid.uuid4())
    print(f"세션 시작: {thread_id}")

    while True:
        # 1. 사용자 입력
        query = input("\n질문을 입력하세요: ")
        if query.lower() in ["exit", "quit"]:
            break

        # 2. Thinking 모드 확인
        thinking_mode = input("Thinking 모드를 사용하시겠습니까? (y/n): ").lower() == 'y'

        # 3. 모드 선택
        selected_mode = mode_router.select_mode(thread_id, thinking_mode)

        # 4. 이전 대화 컨텍스트 로드
        previous_context = session_manager.get_conversation_context(thread_id, last_n=3)

        # 5. 모드에 따라 다른 그래프 실행
        if selected_mode == GraphMode.THINKING:
            print("🧠 Thinking 모드 (Fuseki + SPARQL)")
            graph_app = create_fuseki_graph()

            # LangGraph 실행 (기존 코드)
            config = {"configurable": {"thread_id": f"{thread_id}_thinking"}}
            result = graph_app.invoke({
                "query": query,
                "previous_context": previous_context  # 이전 대화 포함
            }, config)

            answer = result["final_answer"]
            metadata = {
                "user_selected_direction": result.get("user_selected_direction"),
                "query_type": result.get("query_type"),
                "extracted_entities": result.get("extracted_entities", [])[:5]  # 상위 5개만
            }

        else:  # GraphMode.NORMAL
            print("💬 Normal 모드 (Neo4j + pgvector)")
            graph_app = create_neo4j_graph()

            config = {"configurable": {"thread_id": f"{thread_id}_normal"}}
            result = graph_app.invoke({
                "query": query,
                "previous_context": previous_context
            }, config)

            answer = result["final_answer"]
            metadata = {
                "graph_type": "neo4j",
                "nodes_visited": result.get("nodes_visited", 0)
            }

        # 6. 공통 메모리에 저장
        session_manager.save_conversation_turn(
            thread_id=thread_id,
            query=query,
            answer=answer,
            mode=selected_mode.value,
            metadata=metadata
        )

        # 7. 답변 출력
        print(f"\n{answer}")

        # 8. 모드 히스토리 표시
        session = session_manager.get_session(thread_id)
        print(f"\n[세션 정보] 모드 히스토리: {' → '.join(session['mode_history'])}")
```

---

## 구체적 예시: 모드 전환 시나리오

### 시나리오 1: Thinking → Normal → Thinking

```
대화 1 (Thinking 모드):
Q: "명성황후 시해사건으로 발발된 사건들은?"
  → Stage 1.5: 사용자 선택 "직후 사건"
  → Fuseki SPARQL 검색
  → A: "을미사변 직후 아관파천(1896년)이 발생했습니다..."
  → Redis 저장: {
      "conversation_history": [{"query": "명성황후...", "mode": "thinking", ...}],
      "user_context": {"last_selected_direction": "immediate_consequence"}
    }

대화 2 (Normal 모드로 전환):
Q: "아관파천에 대해 더 알려줘"
  → 모드 전환 감지: thinking → normal
  → Redis에서 이전 컨텍스트 로드: "명성황후 시해사건"
  → Neo4j 그래프 검색 (빠른 응답)
  → A: "아관파천은 고종이 러시아 공사관으로 피신한 사건으로..."
  → Redis 저장: {
      "conversation_history": [
        {"query": "명성황후...", "mode": "thinking"},
        {"query": "아관파천...", "mode": "normal"}
      ]
    }

대화 3 (Thinking 모드로 재전환):
Q: "그렇다면 장기적인 영향은?"
  → 모드 전환 감지: normal → thinking
  → Redis에서 이전 컨텍스트 로드: "명성황후 시해사건", "아관파천"
  → Fuseki SPARQL 검색 (심층 분석)
  → Stage 1.5 스킵 (이전 선택 "immediate_consequence"와 다른 방향이므로 재선택 필요)
  → 사용자 선택: "장기 영향"
  → A: "을미사변은 이후 을사조약(1905년), 한일병합(1910년)으로 이어지는..."
```

---

## 장단점 분석

### ✅ 장점

1. **모드 전환 시에도 대화 연속성 유지**
   - Redis에 공통 컨텍스트 저장
   - 이전 질문/답변 참조 가능
2. **유연한 모드 선택**
   - Thinking 모드: 심층 분석, SPARQL 추론
   - Normal 모드: 빠른 응답, 일반 대화
3. **메모리 효율**
   - 각 모드의 LangGraph Checkpointing은 모드별 상태만 저장
   - 공통 컨텍스트는 Redis에서 경량으로 관리

### ⚠️ 단점 및 고려사항

1. **Redis 의존성**
   - Redis 서버 필요 (추가 인프라)
   - Redis 장애 시 메모리 손실 가능 → PostgreSQL 백업 권장
2. **컨텍스트 브리지 복잡도**
   - Fuseki 엔티티 → Neo4j 노드 매핑 필요
   - 서로 다른 데이터 모델 간 변환 로직 필요
3. **성능 오버헤드**
   - 모드 전환 시마다 Redis 읽기/쓰기
   - 대화 히스토리가 길어지면 직렬화 비용 증가

---

## 최종 권장사항

### **Phase 1: Redis + LangGraph Checkpointing 하이브리드**

```python
# 구현 우선순위
1. SessionMemoryManager 구현 (Redis) ✅
   - 공통 대화 컨텍스트 관리
   - 모드 무관 메모리 공유

2. ModeRouter 구현 ✅
   - thinking_mode 플래그로 그래프 선택
   - 모드 전환 감지 및 컨텍스트 브리지

3. 각 모드별 LangGraph Checkpointing (SQLite) ✅
   - Thinking 모드: fuseki_checkpoints.db
   - Normal 모드: neo4j_checkpoints.db
   - 모드별 상세 상태 저장

4. 프롬프트에 이전 컨텍스트 주입 ✅
   - Story Generator에 previous_context 추가
   - "이전 대화에서 '명성황후 시해사건'에 대해 논의했습니다..."
```

### **데이터 흐름**

```
사용자 질문
  ↓
ModeRouter: thinking_mode 확인
  ↓
Redis: 이전 대화 컨텍스트 로드
  ↓
LangGraph (Fuseki 또는 Neo4j)
  ├─ 모드별 Checkpointing 로드
  ├─ 그래프 실행
  └─ 모드별 Checkpointing 저장
  ↓
Redis: 공통 컨텍스트 업데이트
  ↓
답변 반환
```

---

## 결론

**가능합니다!** 단, **3단계 메모리 아키텍처** 필요:

1. **Redis (공통 메모리)** : 대화 컨텍스트, 모드 히스토리, 사용자 선택 기록
2. **LangGraph Checkpointing (Fuseki)** : Thinking 모드 전용 상태
3. **LangGraph Checkpointing (Neo4j)** : Normal 모드 전용 상태

이 구조로 **서로 다른 그래프 시스템 간에도 대화 연속성을 유지**할 수 있습니다.
