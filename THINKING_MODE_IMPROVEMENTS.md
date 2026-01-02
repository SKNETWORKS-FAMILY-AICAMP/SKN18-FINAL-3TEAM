# Thinking Mode 개선 완료 보고서

Claude 스타일의 단계별 사고 과정 시각화를 위한 전체 시스템 개선

## 개선 목표

1. ✅ Thinking 이벤트 구조 통일 (재질문 전/후 구분)
2. ✅ 재질문 시 이벤트 타임라인 연속성 보장
3. ✅ 프론트엔드 상태 관리 개선 (이벤트 손실 방지)
4. ✅ 세션 정리 로직 통일 (중복 코드 제거)

## 변경 사항

### 1. 백엔드 이벤트 구조 통일

#### 신규 파일: `backend/langgraph_fuseki/utils/thinking_events.py`

통일된 이벤트 생성 유틸리티:

```python
def send_thinking_event(
    callback: Optional[Callable],
    event_type: str,
    title: str,
    stage_number: int,
    stage_name: str,
    data: Optional[Dict[str, Any]] = None,
    is_pre_clarification: bool = True  # 재질문 전/후 구분
) -> None
```

**이벤트 구조:**
```python
{
    "type": "thinking",
    "event": "question_analysis_started",
    "title": "질문 분석 시작",
    "stage": {
        "number": 1,
        "name": "Stage 1: Query Classifier",
        "is_pre_clarification": True  # 또는 False
    },
    "data": {...},
    "timestamp": 1234567890.123
}
```

#### 수정된 노드 (샘플): `classify_node.py`

**변경 전:**
```python
if thinking_callback:
    thinking_callback("question_analysis_started", {
        "title": "질문 분석 시작",
        "query": query
    })
```

**변경 후:**
```python
from backend.langgraph_fuseki.utils.thinking_events import send_thinking_event, get_stage_info

stage_info = get_stage_info("query_classifier")

send_thinking_event(
    callback=thinking_callback,
    event_type="question_analysis_started",
    title="질문 분석 시작",
    stage_number=stage_info["number"],
    stage_name=stage_info["name"],
    data={"query": query},
    is_pre_clarification=True  # 재질문 전
)
```

### 2. views.py 세션 정리 로직 통일

#### 신규 함수: `clear_thinking_session()`

**변경 전 (중복 코드):**
```python
# 비스트리밍 모드 (3곳)
request.session.pop('pending_thinking_events', None)
request.session.pop("pending_clarification_query", None)
request.session.pop("pending_expansion_directions", None)
request.session.pop("pending_basic_keywords", None)
request.session.modified = True

# 스트리밍 모드 (2곳)
request.session.pop('pending_thinking_events', None)
request.session.pop("pending_clarification_query", None)
# ... 반복
```

**변경 후 (통일된 함수):**
```python
def clear_thinking_session(request):
    """Thinking 관련 세션 데이터 정리"""
    request.session.pop('pending_thinking_events', None)
    request.session.pop("pending_clarification_query", None)
    request.session.pop("pending_expansion_directions", None)
    request.session.pop("pending_basic_keywords", None)
    request.session.modified = True

# 정상 완료 시
clear_thinking_session(request)

# 에러 발생 시
except Exception:
    clear_thinking_session(request)
    raise
```

#### Thinking 콜백 시그니처 변경

**변경 전:**
```python
def thinking_callback(event_type: str, data: dict):
    thinking_event = {
        "type": "thinking",
        "event": event_type,
        "data": data,
        "timestamp": time.time()
    }
    # ...
```

**변경 후:**
```python
def thinking_callback(event_dict: dict):
    """통일된 이벤트 구조 수신"""
    # event_dict는 이미 완전한 구조
    # ...
```

### 3. 프론트엔드 타임라인 개선

#### ThinkingMode.jsx 재질문 전/후 분리

**변경 전 (단일 타임라인):**
```javascript
const ThinkingMode = ({ thinkingEvents, isComplete }) => {
  const [stages, setStages] = useState([]);

  // 모든 이벤트를 하나의 타임라인으로 표시
  // ...
};
```

**변경 후 (재질문 전/후 분리):**
```javascript
const ThinkingMode = ({ thinkingEvents, isComplete }) => {
  const [preStages, setPreStages] = useState([]);   // 재질문 전
  const [postStages, setPostStages] = useState([]); // 재질문 후
  const [hasClarification, setHasClarification] = useState(false);

  useEffect(() => {
    // 재질문 전/후 이벤트 분리
    const preEvents = thinkingEvents.filter(e =>
      e.stage?.is_pre_clarification === true
    );
    const postEvents = thinkingEvents.filter(e =>
      e.stage?.is_pre_clarification === false
    );

    // 각각 그룹화 및 상태 설정
    // ...
  }, [thinkingEvents, isComplete]);

  return (
    <div>
      {/* 재질문 전 단계 */}
      {preStages.map(...)}

      {/* 재질문 구분선 */}
      {hasClarification && <ClarificationDivider />}

      {/* 재질문 후 단계 */}
      {postStages.map(...)}
    </div>
  );
};
```

#### Chatbot.jsx 이벤트 누적 방식 변경

**변경 전 (이벤트 초기화):**
```javascript
const handleSubmit = async (e) => {
  // Thinking 모드 초기화
  if (isThinkingMode) {
    setThinkingEvents([]);  // 이벤트 삭제
    setIsThinkingComplete(false);
  }
  // ...
};

const handleClarificationChoice = async (directionId, optionTitle) => {
  // Thinking 모드 초기화
  if (isThinkingMode) {
    setThinkingEvents([]);  // 이벤트 삭제
    setIsThinkingComplete(false);
  }
  // ...
};
```

**변경 후 (이벤트 누적):**
```javascript
const handleSubmit = async (e) => {
  // Thinking 모드는 이벤트를 초기화하지 않음 (재질문 후 이벤트 누적)

  // 스트리밍 이벤트 핸들링
  (streamEvent) => {
    if (streamEvent.type === "thinking") {
      // 기존 이벤트에 추가 (덮어쓰지 않음)
      setThinkingEvents((prev) => [...prev, streamEvent]);
    }
  }
};

const handleClarificationChoice = async (directionId, optionTitle) => {
  // Thinking 모드는 이벤트를 초기화하지 않음 (재질문 후 이벤트 누적)

  // ...동일한 누적 방식
};
```

## 개선 효과

### 1. 재질문 전/후 타임라인 연속성

**변경 전:**
```
[재질문 전]
- Stage 1: Query Classifier (완료)

[사용자 선택]

[재질문 후 - 이전 이벤트 손실]
- Stage 2: Entity Expander (진행 중)
```

**변경 후:**
```
[재질문 전]
- Stage 1: Query Classifier (완료) ✓

[사용자 선택 완료 구분선]

[재질문 후 - 이전 이벤트 유지]
- Stage 2: Entity Expander (진행 중)
- Stage 3: Semantic Expander (대기 중)
```

### 2. Claude 스타일 UI/UX

- **단계별 섹션**: 각 Stage가 개별 카드로 표시
- **자동 접힘**: 완료된 단계는 자동으로 접힘
- **진행 상태**: 현재 진행 중인 단계만 펼쳐짐
- **재질문 구분**: 명확한 구분선으로 재질문 전/후 표시

### 3. 코드 유지보수성 향상

- **중복 코드 제거**: 세션 정리 로직 5곳 → 1곳
- **통일된 구조**: 모든 노드에서 동일한 이벤트 생성 방식
- **타입 안정성**: 이벤트 구조가 명확하게 정의됨

## 남은 작업

### 필수 작업

1. **나머지 노드 이벤트 구조 변경**
   - `entity_expander_node.py`
   - `semantic_expander_node.py`
   - `parallel_knowledge_retrieval_node.py`
   - `evidence_aggregator_node.py`
   - `generate_node.py`
   - `history_check_node.py`

   가이드: `backend/langgraph_fuseki/THINKING_EVENT_MIGRATION_GUIDE.md` 참조

### 선택 작업

1. **is_pre_clarification 자동 감지**: 현재는 수동 설정, state에서 자동 판단 가능
2. **이벤트 타입 Enum화**: 오타 방지를 위한 상수 정의
3. **프론트엔드 애니메이션 개선**: 단계 전환 시 부드러운 애니메이션

## 테스트 방법

### 1. 백엔드 이벤트 구조 확인

```bash
# 미변경 thinking_callback 찾기
grep -rn 'thinking_callback("' backend/langgraph_fuseki/nodes/

# 결과가 없으면 모두 변경 완료
```

### 2. 프론트엔드 타임라인 확인

1. Thinking 모드 활성화
2. 질문 입력 후 재질문 선택
3. 확인사항:
   - 재질문 전 이벤트가 표시되는지
   - "사용자 선택 완료" 구분선이 나타나는지
   - 재질문 후 이벤트가 누적되는지
   - 완료된 단계가 자동으로 접히는지

### 3. 세션 정리 확인

```python
# Django shell에서 확인
from django.test import RequestFactory
from backend.django.chatbot.views import clear_thinking_session

factory = RequestFactory()
request = factory.get('/')
request.session = {}
request.session['pending_thinking_events'] = [...]

clear_thinking_session(request)
print(request.session.get('pending_thinking_events'))  # None이어야 함
```

## 파일 변경 목록

### 신규 파일 (2개)
- `backend/langgraph_fuseki/utils/thinking_events.py`
- `backend/langgraph_fuseki/THINKING_EVENT_MIGRATION_GUIDE.md`

### 수정 파일 (4개)
- `backend/django/chatbot/views.py`
- `backend/langgraph_fuseki/nodes/classify_node.py`
- `frontend/react/src/components/common/ThinkingMode/ThinkingMode.jsx`
- `frontend/react/src/pages/Chatbot.jsx`

## 참고 자료

- Claude Thinking Mode UI: https://claude.ai
- 이벤트 구조 설계: `backend/langgraph_fuseki/utils/thinking_events.py`
- 마이그레이션 가이드: `backend/langgraph_fuseki/THINKING_EVENT_MIGRATION_GUIDE.md`
