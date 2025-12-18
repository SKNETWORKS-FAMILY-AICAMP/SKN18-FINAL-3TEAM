import api from "./axios";

/**
 * 채팅 관련 API 함수들
 */

// 질문 전송 및 답변 받기
export const sendQuestion = async (question) => {
  const response = await api.post("/api/chat/question/", {
    question: question,
  });
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

