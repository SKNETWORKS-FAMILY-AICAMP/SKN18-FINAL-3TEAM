# Thinking Event Migration Guide

모든 노드 파일에서 기존 thinking_callback 호출을 통일된 구조로 변경하는 가이드

## 1. Import 추가

모든 노드 파일 상단에 다음 import 추가:

```python
from backend.langgraph_fuseki.utils.thinking_events import send_thinking_event, get_stage_info
```

## 2. 노드별 Stage 정보

각 노드에서 적절한 stage_key 사용:

```python
# classify_node.py
stage_info = get_stage_info("query_classifier")  # Stage 1

# entity_expander_node.py
stage_info = get_stage_info("entity_expander")  # Stage 2

# semantic_expander_node.py
stage_info = get_stage_info("semantic_expander")  # Stage 3

# parallel_knowledge_retrieval_node.py
stage_info = get_stage_info("knowledge_retrieval")  # Stage 4

# evidence_aggregator_node.py
stage_info = get_stage_info("evidence_aggregator")  # Stage 5

# generate_node.py
stage_info = get_stage_info("answer_generator")  # Stage 6

# history_check_node.py
stage_info = get_stage_info("history_check")  # Stage 0
```

## 3. 이벤트 호출 변경 패턴

### 변경 전:
```python
if thinking_callback:
    thinking_callback("event_name", {
        "title": "제목",
        "some_data": "값"
    })
```

### 변경 후:
```python
send_thinking_event(
    callback=thinking_callback,
    event_type="event_name",
    title="제목",
    stage_number=stage_info["number"],
    stage_name=stage_info["name"],
    data={"some_data": "값"},
    is_pre_clarification=True  # 또는 False
)
```

## 4. is_pre_clarification 설정

- **True**: 재질문 전 단계 (classify_node의 모든 이벤트)
- **False**: 재질문 후 단계 (entity_expander, semantic_expander, knowledge_retrieval, generate 등)

### 예시:

```python
# classify_node.py (재질문 전)
send_thinking_event(
    callback=thinking_callback,
    event_type="question_analysis_started",
    title="질문 분석 시작",
    stage_number=stage_info["number"],
    stage_name=stage_info["name"],
    data={"query": query},
    is_pre_clarification=True  # 재질문 전
)

# entity_expander_node.py (재질문 후)
send_thinking_event(
    callback=thinking_callback,
    event_type="entity_expansion_started",
    title="엔티티 확장 시작",
    stage_number=stage_info["number"],
    stage_name=stage_info["name"],
    data={"entity_count": len(entities)},
    is_pre_clarification=False  # 재질문 후
)
```

## 5. 변경 필요한 파일 목록

다음 파일들의 thinking_callback 호출을 모두 변경:

1. `backend/langgraph_fuseki/nodes/classify_node.py` ✅ (완료)
2. `backend/langgraph_fuseki/nodes/entity_expander_node.py`
3. `backend/langgraph_fuseki/nodes/kg/semantic_expander_node.py`
4. `backend/langgraph_fuseki/nodes/kg/parallel_knowledge_retrieval_node.py`
5. `backend/langgraph_fuseki/nodes/evidence_aggregator_node.py`
6. `backend/langgraph_fuseki/nodes/generate_node.py`
7. `backend/langgraph_fuseki/nodes/history_check_node.py`

## 6. 검증 방법

변경 후 확인사항:

1. 모든 thinking_callback 호출이 send_thinking_event로 변경되었는지
2. 각 노드에서 stage_info를 올바르게 가져왔는지
3. is_pre_clarification이 올바르게 설정되었는지

```bash
# 미변경 thinking_callback 찾기
grep -n 'thinking_callback("' backend/langgraph_fuseki/nodes/*.py
grep -n 'thinking_callback("' backend/langgraph_fuseki/nodes/kg/*.py
```

결과가 없으면 모두 변경 완료.
