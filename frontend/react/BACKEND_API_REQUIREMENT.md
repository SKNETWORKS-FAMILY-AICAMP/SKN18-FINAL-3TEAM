# 백엔드 API 요구사항

## 1. 영상 좋아요 상태 확인

**프론트엔드 구현 완료:**

- 영상 상세 페이지에서 좋아요 하트 클릭 시 색상 표시/토글
- 좋아요 개수 실시간 업데이트
- localStorage로 상태 유지 (임시)

**백엔드 추가 필요:**

- `GET /api/video/{video_id}/` 응답에 `is_liked: boolean` 필드 추가
- 로그인한 사용자의 경우 해당 영상에 좋아요를 눌렀는지 여부 반환
- 비로그인 사용자는 `false` 반환

**연결 위치:**

- `frontend/react/src/pages/VideoDetailPage.jsx` - 비디오 정보 로드 시 `is_liked` 사용

## 2. 채팅 API (OpenAI 및 랭그래프 노드)

**프론트엔드 구현 완료:**

- 질문하기 페이지에서 OpenAI API를 통한 질문/답변 기능
- 대화 기록 조회 및 표시 기능
- 스트리밍 응답 표시 기능

**백엔드 추가 필요:**

- `POST /api/chat/question/` API 구현
  - 요청: `{ question: string }`
  - 응답: `{ answer: string }` (OpenAI API를 통한 답변)
  - OpenAI API 연동 필요
  - **환경변수 사용 필수:**
    - `OPENAI_API_KEY`: OpenAI API 키 (필수)
    - `OPENAI_MODEL`: 사용할 OpenAI 모델명 (예: "gpt-4", "gpt-3.5-turbo" 등)
  - 환경변수가 설정되지 않은 경우 적절한 에러 메시지 반환 필요

- `GET /api/chat/history/` API 구현
  - 응답: `[{ id: number, title: string, first_message: string, created_at: string }]`
  - 사용자의 대화 기록 목록 반환

- `GET /api/chat/session/{session_id}/` API 구현
  - 응답: `{ id: number, messages: [{ type: string, text: string, created_at: string }] }`
  - 특정 대화 세션의 메시지 목록 반환

**랭그래프 노드 API 연결 (추가 요청):**

- Thinking 버튼 클릭 시 fuseki API 연결 필요
- 랭그래프 노드를 통한 지식 그래프 검색 기능 구현 필요
- 현재는 "곧만나요" 메시지만 표시되며, fuseki API 연결 시 활성화 예정

**연결 위치:**

- `frontend/react/src/pages/QuestionPage.jsx` - 질문 전송 및 답변 표시
- `frontend/react/src/api/chatApi.js` - 채팅 API 함수들
