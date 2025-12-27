import api from "./axios";

/**
 * 채팅 관련 API 함수들
 */

// 질문 전송 및 답변 받기
export const sendQuestion = async (question, sessionId = null, thinkingMode = false, abortSignal = null) => {
  const payload = {
    question: question,
    thinking_mode: thinkingMode,
  };
  if (sessionId) {
    payload.session_id = sessionId;
  }
  const config = abortSignal ? { signal: abortSignal } : {};
  const response = await api.post("/api/chat/question/", payload, config);
  return response.data;
};

// 대화 기록 조회
export const getChatHistory = async () => {
  const response = await api.get("/api/chat/history/");
  return response.data;
};

// 특정 대화 세션 조회
export const getChatSession = async (sessionId) => {
  const response = await api.get(`/api/chat/session/${sessionId}/`);
  return response.data;
};

// 새 세션 생성
export const createChatSession = async () => {
  const response = await api.post("/api/chat/new-session/");
  return response.data;
};

// 세션 삭제
export const deleteChatSession = async (sessionId) => {
  const response = await api.delete(`/api/chat/session/${sessionId}/delete/`);
  return response.data;
};
