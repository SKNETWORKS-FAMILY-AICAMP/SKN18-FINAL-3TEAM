import api from "./axios";

/**
 * 채팅 관련 API 함수들
 */

// 질문 전송 및 답변 받기 (스트리밍 지원)
export const sendQuestion = async (question, sessionId = null, thinkingMode = false, abortSignal = null, onStream = null) => {
  const payload = {
    question: question,
    thinking_mode: thinkingMode,
    stream: true,  // 스트리밍 활성화
  };
  if (sessionId) {
    payload.session_id = sessionId;
  }
  
  // 스트리밍 콜백이 있으면 스트리밍 모드로 처리
  if (onStream) {
    const token = localStorage.getItem("access_token");
    const baseURL = api.defaults.baseURL || "";
    const url = `${baseURL}/api/chat/question/`;
    
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: abortSignal,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    
    let fullText = "";
    let clarificationData = null;
    
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";  // 마지막 불완전한 라인은 버퍼에 보관
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.substring(6));
              
              if (data.type === "delta") {
                fullText += data.text;
                onStream({ type: "delta", text: data.text, fullText });
              } else if (data.type === "clarification") {
                clarificationData = {
                  needs_clarification: true,
                  clarification_question: data.question,
                  expansion_directions: data.options,
                };
                onStream({ type: "clarification", ...clarificationData });
              } else if (data.type === "final") {
                fullText = data.text;
                onStream({ type: "final", text: data.text });
              } else if (data.type === "error") {
                throw new Error(data.text || "스트리밍 중 오류가 발생했습니다.");
              }
            } catch (e) {
              console.error("[chatApi] Parse error:", e, "Line:", line);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
    
    // 최종 응답 반환
    if (clarificationData) {
      return clarificationData;
    }
    
    return {
      answer: fullText,
      evidences: [],
    };
  }
  
  // 스트리밍이 아닌 경우 기존 방식
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
