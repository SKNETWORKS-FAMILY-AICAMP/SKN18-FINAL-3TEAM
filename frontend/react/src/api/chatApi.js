import api from "./axios";

/**
 * 프론트엔드 URL 가져오기
 */
const getFrontendUrl = () => {
  // 현재 도메인이 백엔드(8000)인 경우 프론트엔드(3000)로 변경
  if (window.location.port === "8000" || window.location.hostname.includes("8000")) {
    return `http://localhost:3000/`;
  }
  // 프론트엔드인 경우 현재 origin 사용
  return `${window.location.origin}/`;
};

/**
 * 토큰 검증 및 자동 로그아웃 처리
 */
const checkAuthToken = () => {
  const token = localStorage.getItem("access_token");
  if (!token) {
    console.warn("[chatApi] No access token found. Redirecting to login...");
    localStorage.clear();
    window.location.href = getFrontendUrl();
    throw new Error("Authentication required");
  }
  return token;
};

/**
 * 401 에러 처리
 */
const handleUnauthorized = (response) => {
  if (response && response.status === 401) {
    console.warn(
      "[chatApi] 401 Unauthorized. Token expired or invalid. Redirecting to login..."
    );
    localStorage.clear();
    window.location.href = getFrontendUrl();
    throw new Error("Authentication expired");
  }
};

/**
 * 채팅 관련 API 함수들
 */

// 질문 전송 및 답변 받기 (스트리밍 지원)
export const sendQuestion = async (question, sessionId = null, thinkingMode = false, abortSignal = null, onStream = null) => {
  // 토큰 확인 및 자동 로그아웃 처리
  const token = checkAuthToken();

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
    const baseURL = api.defaults.baseURL || "";
    const url = `${baseURL}/api/chat/question/`;
    
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
      signal: abortSignal,
      credentials: "include",  // ★ Django 세션 쿠키 전송 필수
    });
    
    if (!response.ok) {
      // 401 Unauthorized 에러 처리
      handleUnauthorized(response);
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    
    let fullText = "";
    let clarificationData = null;
    let streamError = null; // 스트리밍 에러 플래그
    let chunkCount = 0; // 수신한 청크 개수 카운터
    
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";  // 마지막 불완전한 라인은 버퍼에 보관
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const jsonStr = line.substring(6);
              if (jsonStr.trim() === "") continue; // 빈 데이터 스킵
              
              const data = JSON.parse(jsonStr);
              chunkCount++;
              
              if (data.type === "delta") {
                fullText += data.text;
                onStream({ type: "delta", text: data.text, fullText });
              } else if (data.type === "thinking") {
                // Thinking 모드 이벤트 처리
                console.log("[chatApi] Received thinking event:", data.event, data);
                onStream({ type: "thinking", event: data.event, title: data.title, stage: data.stage, data: data.data, timestamp: data.timestamp });
              } else if (data.type === "clarification") {
                clarificationData = {
                  needs_clarification: true,
                  clarification_question: data.question,
                  expansion_directions: data.options,
                };
                onStream({ type: "clarification", ...clarificationData });
              } else if (data.type === "final") {
                fullText = data.text;
                const evidencesFromStream = data.evidences || [];
                onStream({ type: "final", text: data.text, evidences: evidencesFromStream });
                // final 이벤트 후 즉시 종료
                return {
                  answer: fullText,
                  evidences: evidencesFromStream,
                };
              } else if (data.type === "error") {
                // 에러 타입은 onStream으로만 처리하고 throw하지 않음
                const errorMessage = data.text || "스트리밍 중 오류가 발생했습니다.";
                streamError = errorMessage; // 에러 플래그 설정
                onStream({ type: "error", text: errorMessage });
                // throw하지 않고 루프 종료
                break;
              }
            } catch (e) {
              // JSON 파싱 오류인 경우에만 로그 출력
              if (e instanceof SyntaxError) {
                console.error("[chatApi] Parse error:", e, "Line:", line);
              } else {
                // 예상치 못한 에러는 다시 throw
                throw e;
              }
            }
          }
        }
        
        // 스트리밍 에러가 발생하면 루프 종료
        if (streamError) {
          break;
        }
      }
    } catch (error) {
      // 연결이 끊어진 경우에도 지금까지 받은 데이터로 처리
      if (fullText) {
        onStream({ type: "final", text: fullText });
        return {
          answer: fullText,
          evidences: [],
        };
      }
      throw error;
    } finally {
      reader.releaseLock();
    }
    
    // 스트리밍 에러가 발생했으면 에러를 throw
    if (streamError) {
      throw new Error(streamError);
    }
    
    // 스트림이 비어있거나 데이터를 받지 못한 경우
    if (chunkCount === 0 && !fullText && !clarificationData) {
      console.warn("[chatApi] No data received from stream, falling back to non-streaming");
      // 비스트리밍 모드로 재시도
      const config = abortSignal ? { signal: abortSignal } : {};
      const fallbackResponse = await api.post("/api/chat/question/", { ...payload, stream: false }, config);
      return fallbackResponse.data;
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
