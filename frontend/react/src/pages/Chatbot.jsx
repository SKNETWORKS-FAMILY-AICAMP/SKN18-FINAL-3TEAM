import { useState, useRef, useEffect } from "react";
import { COLORS } from "../constants/theme";
import {
  SendIcon,
  StopIcon,
  ThinkingIcon,
  CloseIcon,
  ChatIcon,
  TrashIcon,
} from "../components/common/Icons";
import {
  sendQuestion,
  getChatHistory,
  getChatSession,
  createChatSession,
  deleteChatSession,
} from "../api/chatApi";
import MarkdownRenderer from "../components/common/MarkdownRenderer";
import EvidencePathView from "../components/common/EvidencePathView";
import ThinkingMode from "../components/common/ThinkingMode/ThinkingMode";
import { useBackgroundTask } from "../contexts/BackgroundTaskContext";

const Chatbot = ({ onNavigate, user, newChatTrigger, initialSessionId }) => {
  const { showToast } = useBackgroundTask();
  const [isOnChatbotPage, setIsOnChatbotPage] = useState(true);

  // 페이지 마운트/언마운트 감지
  useEffect(() => {
    setIsOnChatbotPage(true);
    return () => {
      setIsOnChatbotPage(false);
    };
  }, []);

  // 스크롤바 스타일 및 드래그 색상을 위한 CSS 추가
  useEffect(() => {
    const style = document.createElement("style");
    style.id = "chatbot-selection-style";
    style.textContent = `
      /* 챗봇 페이지 드래그 색상 - !important로 전역 스타일 오버라이드 */
      ::selection {
        background-color: ${COLORS.primary} !important;
        color: #000000 !important;
      }
      ::-moz-selection {
        background-color: ${COLORS.primary} !important;
        color: #000000 !important;
      }
      
      .clarification-cards-scroll::-webkit-scrollbar {
        height: 6px;
      }
      .clarification-cards-scroll::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.05);
        border-radius: 3px;
        margin: 0 8px; /* 스크롤바가 카드 영역에만 표시되도록 */
      }
      .clarification-cards-scroll::-webkit-scrollbar-thumb {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 3px;
        transition: background 0.2s ease;
      }
      .clarification-cards-scroll::-webkit-scrollbar-thumb:hover {
        background: rgba(0, 0, 0, 0.4);
      }
      .clarification-cards-scroll::-webkit-scrollbar-thumb:active {
        background: rgba(0, 0, 0, 0.6);
      }
      
      /* Firefox 스크롤바 스타일 */
      .clarification-cards-scroll {
        scrollbar-width: thin;
        scrollbar-color: rgba(0, 0, 0, 0.2) rgba(0, 0, 0, 0.05);
      }
      
      /* 사이드바 스크롤바 스타일 */
      .sidebar-scroll::-webkit-scrollbar {
        width: 6px;
      }
      .sidebar-scroll::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.05);
        border-radius: 3px;
      }
      .sidebar-scroll::-webkit-scrollbar-thumb {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 3px;
        transition: background 0.2s ease;
      }
      .sidebar-scroll::-webkit-scrollbar-thumb:hover {
        background: rgba(0, 0, 0, 0.4);
      }
      
      /* 세션 삭제 버튼 스타일 */
      .session-delete-btn {
        opacity: 0.8 !important; /* 항상 보이도록 변경 */
        background: transparent !important;
        background-color: transparent !important;
        transition: opacity 0.2s ease, color 0.2s ease, transform 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
      }
      .session-delete-btn:hover {
        opacity: 1 !important;
        background: transparent !important;
        background-color: transparent !important;
        transform: scale(1.1) !important;
      }
      
      .session-item:hover .session-delete-btn {
        opacity: 1 !important;
        background: transparent !important;
        background-color: transparent !important;
      }
      
      .session-delete-btn:hover {
        color: #EF4444 !important;
        background: transparent !important;
        background-color: transparent !important;
      }
    `;
    // 기존 스타일이 있으면 제거 후 추가
    const existingStyle = document.getElementById("chatbot-selection-style");
    if (existingStyle) {
      document.head.removeChild(existingStyle);
    }
    document.head.appendChild(style);
    return () => {
      const styleToRemove = document.getElementById("chatbot-selection-style");
      if (styleToRemove) {
        document.head.removeChild(styleToRemove);
      }
    };
  }, []);

  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [showSoonMessage, setShowSoonMessage] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [hoveredDeleteBtn, setHoveredDeleteBtn] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [isThinkingMode, setIsThinkingMode] = useState(false); // Thinking 모드 상태 추가
  const [thinkingEvents, setThinkingEvents] = useState([]); // Thinking 이벤트 저장
  const [isThinkingComplete, setIsThinkingComplete] = useState(false); // Thinking 완료 상태
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const containerRef = useRef(null);
  const abortControllerRef = useRef(null); // API 요청 취소를 위한 ref

  const nickname =
    user?.nickname ||
    user?.display_name ||
    user?.email?.split("@")[0] ||
    "사용자";

  const hydrateMessages = (sessionMessages = []) => {
    const normalized = sessionMessages.map((msg) => {
      // 재질문 메타데이터 체크
      if (
        msg.role === "assistant" &&
        msg.content.startsWith("__CLARIFICATION_METADATA__:")
      ) {
        try {
          const jsonStr = msg.content.substring(
            "__CLARIFICATION_METADATA__:".length
          );
          const metadata = JSON.parse(jsonStr);
          return {
            type: "clarification",
            question: metadata.question,
            options: metadata.options,
            isActive: false, // 과거 기록은 비활성화
          };
        } catch (e) {
          console.error(
            "[hydrateMessages] ❌ Failed to parse clarification metadata:",
            e
          );
          console.error("[hydrateMessages] Content was:", msg.content);
          // 파싱 실패 시 일반 메시지로 fallback
          return {
            type: "assistant",
            text: msg.content,
            evidences: msg.evidences || [],
          };
        }
      }

      // 일반 메시지
      const messageObj = {
        type: msg.role === "assistant" ? "assistant" : "user",
        text: msg.content,
      };

      // evidences가 있으면 포함
      if (
        msg.evidences &&
        Array.isArray(msg.evidences) &&
        msg.evidences.length > 0
      ) {
        messageObj.evidences = msg.evidences;
      }

      return messageObj;
    });
    setMessages(normalized);
  };

  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const token = localStorage.getItem("access_token");
        if (!token) {
          setChatHistory([]);
          return;
        }
        const raw = await getChatHistory();
        const history = Array.isArray(raw) ? raw : raw?.sessions || [];
        setChatHistory(history || []);

        // URL에서 세션 ID가 있으면 해당 세션 로드
        if (initialSessionId) {
          setSelectedSessionId(initialSessionId);
          try {
            const sessionData = await getChatSession(initialSessionId);
            hydrateMessages(sessionData?.messages || []);
          } catch (error) {
            console.error("세션 불러오기 실패:", error);
            setSelectedSessionId(null);
            setMessages([]);
          }
        } else {
          setSelectedSessionId(null);
          setMessages([]);
        }
      } catch (error) {
        if (error.response?.status === 404) {
          setChatHistory([]);
        } else {
          console.error("대화 기록 로드 실패:", error);
          setChatHistory([]);
        }
      }
    };
    loadChatHistory();
  }, [initialSessionId]);

  useEffect(() => {
    const startNewSession = async () => {
      try {
        const token = localStorage.getItem("access_token");
        if (!token) {
          setSelectedSessionId(null);
          setMessages([]);
          return;
        }
        const newSession = await createChatSession();
        setSelectedSessionId(newSession.id);
        setMessages([]);
        // URL 업데이트
        window.location.hash = `question/session/${newSession.id}`;
        const raw = await getChatHistory();
        const history = Array.isArray(raw) ? raw : raw?.sessions || [];
        setChatHistory(history || []);
        setShowHistory(false);
      } catch (error) {
        console.error("새 세션 생성 실패:", error);
      }
    };

    if (newChatTrigger) {
      startNewSession();
    }
  }, [newChatTrigger]);

  useEffect(() => {
    if (inputRef.current && messages.length === 0) {
      inputRef.current.focus();
    }
  }, [messages.length]);

  useEffect(() => {
    if (inputRef.current && messages.length > 0) {
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 100);
    }
  }, [messages.length]);

  useEffect(() => {
    if (containerRef.current && messages.length > 0) {
      requestAnimationFrame(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
      });
    }
  }, [messages, streamingText]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!message.trim() || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    const userMessage = message.trim();
    setMessage("");

    // Thinking 모드는 이벤트를 초기화하지 않음 (재질문 후 이벤트 누적)

    setMessages((prev) => [...prev, { type: "user", text: userMessage }]);

    requestAnimationFrame(() => {
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 50);
    });

    // AbortController 생성
    abortControllerRef.current = new AbortController();

    // 스트리밍 에러가 이미 처리되었는지 플래그 (try-catch 밖에서 선언)
    let streamErrorHandled = false;

    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        simulateStreamingResponse("로그인 후에 질문할 수 있어요.");
        setIsSubmitting(false);
        localStorage.clear();
        // 프론트엔드 URL로 리다이렉트
        const frontendUrl =
          window.location.port === "8000" ||
          window.location.hostname.includes("8000")
            ? "http://localhost:3000/"
            : `${window.location.origin}/`;
        window.location.href = frontendUrl;
        return;
      }

      // 세션이 없으면 새 세션 생성
      let sessionId = selectedSessionId;
      if (!sessionId) {
        const newSession = await createChatSession();
        sessionId = newSession.id;
        setSelectedSessionId(sessionId);
        // 히스토리도 갱신
        const raw = await getChatHistory();
        const history = Array.isArray(raw) ? raw : raw?.sessions || [];
        setChatHistory(history || []);
      }

      // 실제 스트리밍 처리
      let accumulatedText = "";
      let clarificationData = null;
      let finalHandled = false; // ★ final 이벤트 처리 완료 플래그

      const response = await sendQuestion(
        userMessage,
        sessionId,
        isThinkingMode,
        abortControllerRef.current.signal,
        (streamEvent) => {
          // 스트리밍 이벤트 처리
          if (streamEvent.type === "delta") {
            // 실시간으로 텍스트 업데이트 - 받는 즉시 표시
            accumulatedText =
              streamEvent.fullText || accumulatedText + streamEvent.text;
            setStreamingText(accumulatedText);
          } else if (streamEvent.type === "thinking") {
            // Thinking 모드 이벤트 처리
            if (isThinkingMode) {
              setThinkingEvents((prev) => [...prev, streamEvent]);
            }
          } else if (streamEvent.type === "clarification") {
            // 재질문 데이터 저장
            clarificationData = streamEvent;
          } else if (streamEvent.type === "final") {
            // 최종 답변 완료
            accumulatedText = streamEvent.text;
            setStreamingText("");
            if (isThinkingMode) {
              setIsThinkingComplete(true);
            }
            const messageObj = { type: "assistant", text: accumulatedText };
            // ★ evidences 처리
            if (
              streamEvent.evidences &&
              Array.isArray(streamEvent.evidences) &&
              streamEvent.evidences.length > 0
            ) {
              messageObj.evidences = streamEvent.evidences;
            }
            setMessages((prev) => [...prev, messageObj]);

            // 스트리밍 완료 처리
            finalHandled = true; // ★ 완료 플래그 설정
            setIsSubmitting(false);
            abortControllerRef.current = null;

            // 페이지 이탈 시에만 토스트 표시
            if (!isOnChatbotPage) {
              const modeText = isThinkingMode ? "Thinking 모드" : "일반 모드";
              showToast(`챗봇 ${modeText} 답변 생성 완료`, "success");
            }
          } else if (streamEvent.type === "error") {
            // 에러 타입 처리 - 이미 처리되었음을 표시
            streamErrorHandled = true;
            const errorMessage =
              streamEvent.text ||
              "오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
            setStreamingText("");
            simulateStreamingResponse(errorMessage);
            setIsSubmitting(false);
            abortControllerRef.current = null;
          }
        }
      );

      // 재질문이 있는 경우
      if (
        response.needs_clarification &&
        response.expansion_directions &&
        response.expansion_directions.length > 0
      ) {
        setStreamingText(""); // 스트리밍 텍스트 초기화
        setMessages((prev) => [
          ...prev,
          {
            type: "clarification",
            question: response.clarification_question,
            options: response.expansion_directions,
            isActive: true, // 현재 진행 중인 재질문은 활성화
          },
        ]);
        setIsSubmitting(false);

        // 페이지 이탈 시 재질문 완료 토스트 표시
        if (!isOnChatbotPage) {
          showToast("챗봇 의도 파악 완료 - 선택지 제공", "success");
        }

        return;
      }

      // ★ final 이벤트가 이미 처리되었으면 fallback 건너뛰기
      if (finalHandled) {
        return;
      }

      // 스트리밍이 완료되지 않은 경우 (fallback)
      if (accumulatedText) {
        setStreamingText("");
        const messageObj = { type: "assistant", text: accumulatedText };
        setMessages((prev) => [...prev, messageObj]);
      } else if (response.answer) {
        // 일반 응답 (스트리밍이 아닌 경우)
        setStreamingText("");
        const messageObj = { type: "assistant", text: response.answer };
        if (
          response.evidences &&
          Array.isArray(response.evidences) &&
          response.evidences.length > 0
        ) {
          messageObj.evidences = response.evidences;
        }
        setMessages((prev) => [...prev, messageObj]);
      } else {
        setStreamingText("");
        simulateStreamingResponse("답변을 받을 수 없습니다.");
      }
    } catch (error) {
      // 사용자가 취소한 경우
      if (error.name === "CanceledError" || error.code === "ERR_CANCELED") {
        // 마지막 사용자 메시지 제거
        setMessages((prev) => prev.slice(0, -1));
        setIsSubmitting(false);
        abortControllerRef.current = null;
        return;
      }

      // 스트리밍 에러가 이미 onStream 콜백에서 처리된 경우 중복 처리 방지
      if (streamErrorHandled) {
        return;
      }

      console.error("질문 전송 실패:", error);

      let errorMessage = "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.";

      if (error.response?.status === 404) {
        errorMessage =
          "채팅 API가 아직 구현되지 않았습니다. 백엔드 개발자에게 문의해주세요.";
      } else if (error.response?.status === 500) {
        errorMessage = "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
      } else if (error.response?.status === 503) {
        errorMessage =
          "OpenAI API 연결에 실패했습니다. 환경변수(OPENAI_API_KEY, OPENAI_MODEL) 설정을 확인해주세요.";
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      }

      simulateStreamingResponse(errorMessage);
    }

    abortControllerRef.current = null;
    setTimeout(() => {
      setIsSubmitting(false);
    }, 300);
  };

  const handleStopSubmit = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsSubmitting(false);
      // 마지막 사용자 메시지 제거
      setMessages((prev) => prev.slice(0, -1));
      setMessage(""); // 입력창도 비움
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey && !isSubmitting) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const simulateStreamingResponse = (text, evidences = []) => {
    setStreamingText("");
    let index = 0;
    const interval = setInterval(() => {
      if (index < text.length) {
        setStreamingText(text.substring(0, index + 1));
        index++;
      } else {
        clearInterval(interval);
        const messageObj = { type: "assistant", text: text };
        if (evidences && Array.isArray(evidences) && evidences.length > 0) {
          messageObj.evidences = evidences;
        }
        setMessages((prev) => [...prev, messageObj]);
        setStreamingText("");
      }
    }, 20);
  };

  const handleThinkingClick = () => {
    setIsThinkingMode(!isThinkingMode);
  };

  const handleClarificationChoice = async (directionId, optionTitle) => {
    // 재질문 카드를 비활성화하고 사용자 선택을 메시지에 추가
    setMessages((prev) => {
      const updated = prev.map((msg) =>
        msg.type === "clarification" && msg.isActive
          ? { ...msg, isActive: false }
          : msg
      );
      return [...updated, { type: "user", text: optionTitle }];
    });

    setIsSubmitting(true);

    // Thinking 모드는 이벤트를 초기화하지 않음 (재질문 후 이벤트 누적)

    // AbortController 생성
    abortControllerRef.current = new AbortController();

    // 스트리밍 에러가 이미 처리되었는지 플래그 (try-catch 밖에서 선언)
    let streamErrorHandled = false;

    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        localStorage.clear();
        // 프론트엔드 URL로 리다이렉트
        const frontendUrl =
          window.location.port === "8000" ||
          window.location.hostname.includes("8000")
            ? "http://localhost:3000/"
            : `${window.location.origin}/`;
        window.location.href = frontendUrl;
        return;
      }

      // 선택한 방향을 백엔드로 전달 (direction_id와 title 함께 전송)
      let accumulatedText = "";
      let finalHandled = false; // ★ final 이벤트 처리 완료 플래그

      const response = await sendQuestion(
        `__CLARIFICATION__:${directionId}:${optionTitle}`,
        selectedSessionId,
        isThinkingMode,
        abortControllerRef.current.signal,
        (streamEvent) => {
          // 스트리밍 이벤트 처리
          if (streamEvent.type === "delta") {
            // 실시간으로 텍스트 업데이트 - 받는 즉시 표시
            accumulatedText =
              streamEvent.fullText || accumulatedText + streamEvent.text;
            setStreamingText(accumulatedText);
          } else if (streamEvent.type === "thinking") {
            // Thinking 모드 이벤트 처리
            if (isThinkingMode) {
              setThinkingEvents((prev) => [...prev, streamEvent]);
            }
          } else if (streamEvent.type === "final") {
            // 최종 답변 완료 - 받는 즉시 처리
            accumulatedText = streamEvent.text;
            setStreamingText("");
            if (isThinkingMode) {
              setIsThinkingComplete(true);
            }
            const messageObj = { type: "assistant", text: accumulatedText };
            // ★ evidences는 streamEvent에서 가져오거나, 나중에 response에서 처리
            if (
              streamEvent.evidences &&
              Array.isArray(streamEvent.evidences) &&
              streamEvent.evidences.length > 0
            ) {
              messageObj.evidences = streamEvent.evidences;
            }
            setMessages((prev) => [...prev, messageObj]);

            // 스트리밍 완료 처리
            finalHandled = true; // ★ 완료 플래그 설정
            setIsSubmitting(false);
            abortControllerRef.current = null;
          } else if (streamEvent.type === "error") {
            // 에러 타입 처리 - 이미 처리되었음을 표시
            streamErrorHandled = true;
            const errorMessage =
              streamEvent.text ||
              "오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
            setStreamingText("");
            simulateStreamingResponse(errorMessage);
            setIsSubmitting(false);
            abortControllerRef.current = null;
          }
        }
      );

      // ★ final 이벤트가 이미 처리되었으면 fallback 건너뛰기
      if (finalHandled) {
        return;
      }

      // 스트리밍이 완료되지 않은 경우 (fallback)
      if (accumulatedText) {
        setStreamingText("");
        const messageObj = { type: "assistant", text: accumulatedText };
        if (
          response.evidences &&
          Array.isArray(response.evidences) &&
          response.evidences.length > 0
        ) {
          messageObj.evidences = response.evidences;
        }
        setMessages((prev) => [...prev, messageObj]);
      } else if (response.answer) {
        setStreamingText("");
        const messageObj = { type: "assistant", text: response.answer };
        if (
          response.evidences &&
          Array.isArray(response.evidences) &&
          response.evidences.length > 0
        ) {
          messageObj.evidences = response.evidences;
        }
        setMessages((prev) => [...prev, messageObj]);
      } else {
        setStreamingText("");
        simulateStreamingResponse("답변을 받을 수 없습니다.");
      }
    } catch (error) {
      // 사용자가 취소한 경우
      if (error.name === "CanceledError" || error.code === "ERR_CANCELED") {
        setMessages((prev) => prev.slice(0, -1));
        setIsSubmitting(false);
        abortControllerRef.current = null;
        return;
      }

      // 스트리밍 에러가 이미 onStream 콜백에서 처리된 경우 중복 처리 방지
      if (streamErrorHandled) {
        return;
      }

      console.error("선택지 전송 실패:", error);
      simulateStreamingResponse(
        "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요."
      );
    }

    abortControllerRef.current = null;
    setTimeout(() => {
      setIsSubmitting(false);
    }, 300);
  };

  useEffect(() => {
    if (messages.length > 0) {
      document.body.style.overflow = "hidden";
      document.documentElement.style.overflow = "hidden";

      const preventScroll = (e) => {
        const target = e.target;
        const isScrollable =
          target.closest('[style*="overflow-y: auto"]') ||
          target.closest('[style*="overflow-y: scroll"]');
        if (!isScrollable) {
          e.preventDefault();
        }
      };

      window.addEventListener("wheel", preventScroll, { passive: false });
      window.addEventListener("touchmove", preventScroll, { passive: false });

      return () => {
        document.body.style.overflow = "";
        document.documentElement.style.overflow = "";
        window.removeEventListener("wheel", preventScroll);
        window.removeEventListener("touchmove", preventScroll);
      };
    } else {
      document.body.style.overflow = "";
      document.documentElement.style.overflow = "";
    }
  }, [messages.length]);

  return (
    <div
      style={{
        height: "calc(100vh - 76px)", // 비디오 생성 페이지와 동일한 높이로 맞춤
        maxHeight: "calc(100vh - 76px)",
        backgroundColor: COLORS.background,
        display: "flex",
        flexDirection: "row",
        padding: 0,
        position: "relative",
        overflow: "hidden",
        touchAction: messages.length > 0 ? "none" : "auto",
      }}
    >
      {/* 사이드바 (메시지가 있을 때만) */}
      {chatHistory.length > 0 && (
        <>
          {/* 사이드바 토글 버튼 */}
          <button
            onClick={() => setShowHistory(!showHistory)}
            style={{
              position: "fixed",
              left: showHistory ? "280px" : "40px", // 닫혀있을 때는 사이드바보다 오른쪽에
              top: "86px", // 비디오 생성 페이지와 동일한 높이로 맞춤 (76px + 10px 여백)
              width: "72px",
              height: "72px",
              backgroundColor: "transparent",
              border: "none",
              outline: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1001,
              transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "scale(1.08)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "scale(1)";
            }}
          >
            <svg
              width="81"
              height="81"
              viewBox="0 0 24 24"
              fill="none"
              stroke={COLORS.dark}
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{
                transform: showHistory ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
              }}
            >
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </button>

          {/* 사이드바 */}
          <div
            style={{
              position: "fixed",
              left: showHistory ? "0" : "-320px",
              top: "76px", // 비디오 생성 페이지와 동일한 높이로 맞춤
              width: "300px",
              backgroundColor: "rgba(255, 255, 255, 0.95)",
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
              border: "1px solid rgba(255, 255, 255, 0.2)",
              borderLeft: "none",
              borderTopRightRadius: "20px",
              borderBottomRightRadius: "20px",
              boxShadow: "0 8px 32px rgba(0, 0, 0, 0.1)",
              display: "flex",
              flexDirection: "column",
              overflowY: "auto",
              overflowX: "hidden",
              height: "calc(100vh - 76px)", // 비디오 생성 페이지와 동일한 높이로 맞춤
              padding: "32px 24px",
              transition: "left 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
              zIndex: 1000,
            }}
          >
            <div
              style={{
                padding: "0 0 24px 0",
                display: "flex",
                flexDirection: "column",
                gap: "16px",
                alignItems: "stretch",
                borderBottom: `1px solid ${COLORS.border}`,
                marginBottom: "24px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  marginBottom: "8px",
                }}
              >
                <div
                  style={{
                    width: "32px",
                    height: "32px",
                    borderRadius: "8px",
                    backgroundColor: COLORS.primary,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke={COLORS.dark}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                  </svg>
                </div>
                <span
                  style={{
                    fontSize: "18px",
                    fontWeight: "700",
                    color: COLORS.dark,
                  }}
                >
                  대화 기록
                </span>
              </div>
              <button
                onClick={async () => {
                  try {
                    const token = localStorage.getItem("access_token");
                    if (!token) {
                      setSelectedSessionId(null);
                      setMessages([]);
                      return;
                    }
                    const newSession = await createChatSession();
                    setSelectedSessionId(newSession.id);
                    setMessages([]);
                    setShowHistory(false); // 사이드바 자동 접기
                    // URL 업데이트
                    window.location.hash = `question/session/${newSession.id}`;
                    const raw = await getChatHistory();
                    const history = Array.isArray(raw)
                      ? raw
                      : raw?.sessions || [];
                    setChatHistory(history || []);
                  } catch (error) {
                    console.error("새 세션 생성 실패:", error);
                  }
                }}
                style={{
                  width: "100%",
                  background: `linear-gradient(135deg, ${COLORS.primary} 0%, ${COLORS.sub_color} 100%)`,
                  border: "none",
                  boxShadow: `0 4px 16px ${COLORS.primary}40`,
                  color: COLORS.dark,
                  cursor: "pointer",
                  fontSize: "15px",
                  fontWeight: "600",
                  padding: "14px 20px",
                  borderRadius: "12px",
                  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "10px",
                  position: "relative",
                  overflow: "hidden",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform =
                    "translateY(-2px) scale(1.02)";
                  e.currentTarget.style.boxShadow = `0 8px 25px ${COLORS.primary}50`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "translateY(0) scale(1)";
                  e.currentTarget.style.boxShadow = `0 4px 16px ${COLORS.primary}40`;
                }}
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke={COLORS.dark}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 2v20M2 12h20"></path>
                </svg>
                새 채팅 시작
              </button>
            </div>
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "8px 0 0 0",
                // 커스텀 스크롤바
                scrollbarWidth: "thin",
                scrollbarColor: `${COLORS.border} transparent`,
              }}
              className="sidebar-scroll"
            >
              {chatHistory.length === 0 ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "40px 20px",
                    textAlign: "center",
                    color: COLORS.gray,
                  }}
                >
                  <svg
                    width="48"
                    height="48"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ marginBottom: "16px", opacity: 0.5 }}
                  >
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                  </svg>
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: "500",
                      marginBottom: "8px",
                    }}
                  >
                    아직 대화가 없습니다
                  </div>
                  <div
                    style={{
                      fontSize: "12px",
                      lineHeight: "1.5",
                      opacity: 0.7,
                    }}
                  >
                    새 채팅을 시작해보세요
                  </div>
                </div>
              ) : (
                chatHistory.map((session) => (
                  <div
                    key={session.id}
                    className="session-item"
                    onClick={async () => {
                      setSelectedSessionId(session.id);
                      setMessages([]);
                      setShowHistory(false); // 사이드바 자동 접기
                      // URL 업데이트
                      window.location.hash = `question/session/${session.id}`;
                      try {
                        const sessionData = await getChatSession(session.id);
                        hydrateMessages(sessionData?.messages || []);
                      } catch (error) {
                        console.error("세션 불러오기 실패:", error);
                      }
                    }}
                    style={{
                      position: "relative",
                      padding: "16px",
                      marginBottom: "12px",
                      borderRadius: "12px",
                      cursor: "pointer",
                      backgroundColor:
                        selectedSessionId === session.id
                          ? `${COLORS.primary}20`
                          : "rgba(255, 255, 255, 0.6)",
                      border:
                        selectedSessionId === session.id
                          ? `2px solid ${COLORS.primary}`
                          : "2px solid transparent",
                      backdropFilter: "blur(10px)",
                      WebkitBackdropFilter: "blur(10px)",
                      transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                      boxShadow:
                        selectedSessionId === session.id
                          ? `0 4px 20px ${COLORS.primary}30`
                          : "0 2px 8px rgba(0, 0, 0, 0.06)",
                      overflow: "visible",
                    }}
                    onMouseEnter={(e) => {
                      if (selectedSessionId !== session.id) {
                        e.currentTarget.style.backgroundColor =
                          "rgba(255, 255, 255, 0.8)";
                        e.currentTarget.style.transform = "translateY(-2px)";
                        e.currentTarget.style.boxShadow =
                          "0 6px 20px rgba(0, 0, 0, 0.1)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (selectedSessionId !== session.id) {
                        e.currentTarget.style.backgroundColor =
                          "rgba(255, 255, 255, 0.6)";
                        e.currentTarget.style.transform = "translateY(0)";
                        e.currentTarget.style.boxShadow =
                          "0 2px 8px rgba(0, 0, 0, 0.06)";
                      }
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "12px",
                        marginBottom: "8px",
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: "14px",
                            fontWeight: "600",
                            color: COLORS.dark,
                            marginBottom: "4px",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            lineHeight: "1.4",
                          }}
                        >
                          {session.title ||
                            session.first_message ||
                            "새로운 대화"}
                        </div>
                        <div
                          style={{
                            fontSize: "12px",
                            color: COLORS.gray,
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <svg
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12,6 12,12 16,14"></polyline>
                          </svg>
                          {session.created_at
                            ? new Date(session.created_at).toLocaleDateString(
                                "ko-KR",
                                {
                                  month: "short",
                                  day: "numeric",
                                }
                              )
                            : ""}
                        </div>
                      </div>
                    </div>
                    <button
                      className="session-delete-btn"
                      onClick={async (e) => {
                        e.stopPropagation();
                        try {
                          await deleteChatSession(session.id);
                          const filtered = (chatHistory || []).filter(
                            (s) => s.id !== session.id
                          );
                          setChatHistory(filtered);
                          if (selectedSessionId === session.id) {
                            setSelectedSessionId(null);
                            setMessages([]);
                            // URL 업데이트 (세션 ID 제거)
                            window.location.hash = "question";
                          }
                        } catch (error) {
                          console.error("세션 삭제 실패:", error);
                        }
                      }}
                      style={{
                        position: "absolute",
                        bottom: "12px",
                        right: "12px",
                        width: "24px",
                        height: "24px",
                        border: "none",
                        background: "transparent",
                        backgroundColor: "transparent",
                        color: "#666666",
                        cursor: "pointer",
                        opacity: 0.8, // 더 잘 보이도록 조정
                        transition: "opacity 0.2s ease, color 0.2s ease",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        zIndex: 10,
                        pointerEvents: "auto",
                      }}
                      onMouseEnter={(e) => {
                        e.stopPropagation();
                        setHoveredDeleteBtn(session.id);
                        e.currentTarget.style.color = "#EF4444";
                        e.currentTarget.style.background = "transparent";
                        e.currentTarget.style.backgroundColor = "transparent";
                        e.currentTarget.style.opacity = "1";
                      }}
                      onMouseLeave={(e) => {
                        e.stopPropagation();
                        setHoveredDeleteBtn(null);
                        e.currentTarget.style.color = "#666666";
                        e.currentTarget.style.background = "transparent";
                        e.currentTarget.style.backgroundColor = "transparent";
                        e.currentTarget.style.opacity = "0.8";
                      }}
                    >
                      <TrashIcon
                        size={18}
                        color={
                          hoveredDeleteBtn === session.id
                            ? "#EF4444"
                            : "#666666"
                        }
                      />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}

      {/* 메인 컨텐츠 */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          padding: messages.length > 0 ? "40px 60px" : "40px 60px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Thinking 상태 표시 */}
        {isThinking && (
          <div
            style={{
              position: "absolute",
              top: "40px",
              left: "50%",
              transform: "translateX(-50%)",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontSize: "16px",
              color: COLORS.gray,
              fontStyle: "italic",
              zIndex: 10,
            }}
          >
            <span style={{ color: "#ff6b35" }}>✦</span>
            <span>{nickname} is thinking</span>
          </div>
        )}

        {/* 곧만나요 토스트 */}
        {showSoonMessage && (
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              padding: "12px 20px",
              backgroundColor: COLORS.lightGray,
              borderRadius: "12px",
              fontSize: "14px",
              color: COLORS.dark,
              zIndex: 20,
              animation: "fadeInOut 2s ease",
              boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
            }}
          >
            <style>{`
            @keyframes fadeInOut {
              0% { opacity: 0; transform: translate(-50%, -50%) translateY(-10px); }
              20% { opacity: 1; transform: translate(-50%, -50%) translateY(0); }
              80% { opacity: 1; transform: translate(-50%, -50%) translateY(0); }
              100% { opacity: 0; transform: translate(-50%, -50%) translateY(-10px); }
            }
          `}</style>
            곧만나요
          </div>
        )}

        {/* 메시지가 있을 때 */}
        {messages.length > 0 ? (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              maxWidth: "900px",
              width: "100%",
              marginLeft: "auto",
              marginRight: "auto",
              paddingLeft: showHistory ? "340px" : "60px", // 사이드바 너비 + 여백, 닫혀있을 때도 토글 버튼 공간 확보
              height: "100%",
              minHeight: 0,
              position: "relative",
            }}
          >
            {/* 대화 목록 */}
            <div
              ref={containerRef}
              style={{
                flex: 1,
                overflowY: "auto",
                overflowX: "hidden",
                paddingTop: "40px", // 상단 패딩 증가로 위 내용이 가려지지 않도록
                paddingRight: "16px",
                paddingLeft: "16px",
                paddingBottom: "100px", // 마지막 대화와 입력창 사이 간격 조정
                touchAction: "pan-y",
                WebkitOverflowScrolling: "touch",
              }}
              onWheel={(e) => {
                e.stopPropagation();
              }}
              onTouchMove={(e) => {
                e.stopPropagation();
              }}
            >
              {/* Thinking Mode 컴포넌트 (Thinking 모드일 때만 표시) */}
              {isThinkingMode && thinkingEvents.length > 0 && (
                <div style={{ marginBottom: "24px" }}>
                  <ThinkingMode
                    thinkingEvents={thinkingEvents}
                    isComplete={isThinkingComplete}
                  />
                </div>
              )}

              <div
                style={{
                  minHeight: "100%",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "flex-end",
                  gap: "24px",
                  paddingTop: "20px", // 상단 여백 추가로 첫 메시지가 가려지지 않도록
                }}
              >
                {messages.map((msg, index) => (
                  <div key={index} style={{ marginBottom: "8px" }}>
                    {/* 구분선 */}
                    {index > 0 && (
                      <div
                        style={{
                          height: "1px",
                          backgroundColor: COLORS.lightGray,
                          margin: "16px 0",
                          opacity: 0.5,
                        }}
                      />
                    )}
                    <div
                      style={{
                        display: "flex",
                        justifyContent:
                          msg.type === "user" ? "flex-end" : "flex-start",
                        alignItems: "flex-start",
                        gap: "12px",
                        padding: "0 8px",
                      }}
                    >
                      {msg.type === "user" ? (
                        <div
                          style={{
                            marginBottom: "8px",
                            padding: "12px 16px",
                            backgroundColor: COLORS.lightGray,
                            borderRadius: "12px",
                            fontSize: "14px",
                            color: COLORS.dark,
                            display: "inline-block",
                            maxWidth: "68%",
                            wordWrap: "break-word",
                            lineHeight: "1.5",
                          }}
                        >
                          {msg.text}
                        </div>
                      ) : msg.type === "clarification" ? (
                        <>
                          <div
                            style={{
                              width: "32px",
                              height: "32px",
                              borderRadius: "50%",
                              backgroundColor: COLORS.primary,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              flexShrink: 0,
                              marginTop: "2px",
                            }}
                          >
                            <ChatIcon size={18} color={COLORS.dark} />
                          </div>
                          <div
                            style={{
                              flex: 1,
                              minWidth: 0, // flex item이 축소될 수 있도록
                              overflow: "hidden", // 컨테이너 overflow 제어
                            }}
                          >
                            <div
                              style={{
                                fontSize: "14px",
                                color: COLORS.dark,
                                lineHeight: "1.5",
                                marginBottom: "16px",
                                fontWeight: "500",
                              }}
                            >
                              어떤 방향의 정보가 더 궁금하신가요?
                            </div>
                            <div
                              className="clarification-cards-scroll"
                              style={{
                                display: "flex",
                                gap: "12px",
                                overflowX: "auto",
                                overflowY: "hidden",
                                paddingBottom: "8px",
                                // paddingLeft: "5px", // 첫 번째 카드 여백 더 증가
                                paddingRight: "40px", // 마지막 카드 여백 더 대폭 증가
                                // marginLeft: "-5px", // 패딩으로 인한 시각적 오프셋 보정
                                marginRight: "-40px", // 패딩으로 인한 시각적 오프셋 보정
                                WebkitOverflowScrolling: "touch", // iOS 부드러운 스크롤
                                scrollbarWidth: "thin", // Firefox 스크롤바
                                msOverflowStyle: "auto", // IE/Edge 스크롤바
                                scrollBehavior: "smooth", // 부드러운 스크롤
                                // 터치 디바이스에서 스크롤 관성 개선
                                touchAction: "pan-x",
                                // 스크롤 스냅 효과
                                scrollSnapType: "x proximity",
                                // 컨테이너 최대 너비 제한 해제
                                width: "100%",
                                maxWidth: "none",
                                // 스크롤바 스타일링은 CSS 클래스(.clarification-cards-scroll)에서 처리됨
                              }}
                            >
                              {msg.options?.map((option, idx) => {
                                const isDisabled =
                                  !msg.isActive || isSubmitting;
                                return (
                                  <button
                                    key={option.id}
                                    onClick={(e) => {
                                      if (msg.isActive && !isSubmitting) {
                                        // 클릭 시 즉시 시각적 피드백
                                        e.currentTarget.style.transform =
                                          "scale(0.98)";
                                        e.currentTarget.style.borderColor =
                                          COLORS.primary;
                                        e.currentTarget.style.backgroundColor =
                                          COLORS.primary;
                                        e.currentTarget.style.color =
                                          COLORS.dark;

                                        // 선택 처리
                                        handleClarificationChoice(
                                          option.direction_id,
                                          option.title
                                        );
                                      }
                                    }}
                                    disabled={isDisabled}
                                    style={{
                                      minWidth: "180px", // 카드 최소 너비 줄임 (220px → 180px)
                                      maxWidth: "240px", // 카드 최대 너비 줄임 (280px → 240px)
                                      padding: "16px",
                                      backgroundColor: COLORS.white,
                                      border: `2px solid ${COLORS.border}`,
                                      borderRadius: "16px",
                                      cursor: isDisabled
                                        ? "not-allowed"
                                        : "pointer",
                                      textAlign: "left",
                                      transition: "all 0.2s ease-out",
                                      opacity: isDisabled ? 0.6 : 1,
                                      flexShrink: 0,
                                      boxShadow: isDisabled
                                        ? "0 1px 3px rgba(0,0,0,0.04)"
                                        : "0 2px 8px rgba(0,0,0,0.06)", // 기본 그림자 추가
                                      scrollSnapAlign: "start", // 스크롤 스냅 정렬
                                      // 첫 번째와 마지막 카드 여백 개선
                                      marginLeft: idx === 0 ? "12px" : "0px", // 첫 카드 여백 증가
                                      marginRight:
                                        idx === msg.options.length - 1
                                          ? "32px" // 마지막 카드 여백 대폭 증가 (8px → 32px)
                                          : "0px",
                                    }}
                                    onMouseEnter={(e) => {
                                      if (!isDisabled) {
                                        e.currentTarget.style.borderColor =
                                          COLORS.primary;
                                        e.currentTarget.style.backgroundColor =
                                          COLORS.tertiary;
                                        e.currentTarget.style.transform =
                                          "translateY(-3px) scale(1.02)";
                                        e.currentTarget.style.boxShadow =
                                          "0 8px 25px rgba(0,0,0,0.12)";
                                      }
                                    }}
                                    onMouseLeave={(e) => {
                                      if (!isDisabled) {
                                        e.currentTarget.style.borderColor =
                                          COLORS.border;
                                        e.currentTarget.style.backgroundColor =
                                          COLORS.white;
                                        e.currentTarget.style.transform =
                                          "translateY(0) scale(1)";
                                        e.currentTarget.style.boxShadow =
                                          "0 2px 8px rgba(0,0,0,0.06)";
                                      }
                                    }}
                                    onTouchStart={(e) => {
                                      if (!isDisabled) {
                                        e.currentTarget.style.transform =
                                          "scale(0.98)";
                                      }
                                    }}
                                    onTouchEnd={(e) => {
                                      if (!isDisabled) {
                                        e.currentTarget.style.transform =
                                          "translateY(0) scale(1)";
                                      }
                                    }}
                                  >
                                    <div
                                      style={{
                                        fontSize: "12px",
                                        fontWeight: "700",
                                        color: COLORS.primary,
                                        marginBottom: "8px",
                                        display: "flex",
                                        alignItems: "center",
                                        gap: "6px",
                                      }}
                                    >
                                      <span
                                        style={{
                                          width: "24px",
                                          height: "24px",
                                          borderRadius: "50%",
                                          backgroundColor: COLORS.primary,
                                          color: COLORS.dark,
                                          display: "flex",
                                          alignItems: "center",
                                          justifyContent: "center",
                                          fontSize: "13px",
                                          fontWeight: "700",
                                        }}
                                      >
                                        {idx + 1}
                                      </span>
                                    </div>
                                    <div
                                      style={{
                                        fontSize: "15px",
                                        fontWeight: "600",
                                        color: COLORS.dark,
                                        marginBottom: "8px",
                                        lineHeight: "1.3",
                                      }}
                                    >
                                      {option.title}
                                    </div>
                                    <div
                                      style={{
                                        fontSize: "13px",
                                        color: COLORS.gray,
                                        lineHeight: "1.5",
                                      }}
                                    >
                                      {option.description}
                                    </div>
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        </>
                      ) : (
                        <>
                          <div
                            style={{
                              width: "32px",
                              height: "32px",
                              borderRadius: "50%",
                              backgroundColor: COLORS.primary,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              flexShrink: 0,
                              marginTop: "2px",
                            }}
                          >
                            <ChatIcon size={18} color={COLORS.dark} />
                          </div>
                          <div
                            style={{
                              marginBottom: "8px",
                              flex: 1,
                              width: "100%",
                              maxWidth: "100%",
                              overflow: "hidden",
                              minWidth: 0,
                              boxSizing: "border-box",
                            }}
                          >
                            <MarkdownRenderer content={msg.text} />
                            {msg.evidences && msg.evidences.length > 0 && (
                              <EvidencePathView evidences={msg.evidences} />
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                ))}

                {/* 로딩 애니메이션 - 답변 대기 중 */}
                {isSubmitting && !streamingText && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "12px",
                    }}
                  >
                    <div
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "50%",
                        backgroundColor: COLORS.primary,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        marginTop: "2px",
                      }}
                    >
                      <ChatIcon size={18} color={COLORS.dark} />
                    </div>
                    <div
                      style={{
                        fontSize: "14px",
                        color: COLORS.gray,
                        lineHeight: "1.5",
                        display: "flex",
                        alignItems: "center",
                        gap: "2px",
                        paddingTop: "2px",
                      }}
                    >
                      <span
                        style={{
                          display: "inline-block",
                          width: "6px",
                          height: "6px",
                          borderRadius: "50%",
                          backgroundColor: COLORS.gray,
                          animation: "dotBounce 1.4s infinite ease-in-out",
                          animationDelay: "0s",
                        }}
                      />
                      <span
                        style={{
                          display: "inline-block",
                          width: "6px",
                          height: "6px",
                          borderRadius: "50%",
                          backgroundColor: COLORS.gray,
                          animation: "dotBounce 1.4s infinite ease-in-out",
                          animationDelay: "0.2s",
                        }}
                      />
                      <span
                        style={{
                          display: "inline-block",
                          width: "6px",
                          height: "6px",
                          borderRadius: "50%",
                          backgroundColor: COLORS.gray,
                          animation: "dotBounce 1.4s infinite ease-in-out",
                          animationDelay: "0.4s",
                        }}
                      />
                      <style>{`
                        @keyframes dotBounce {
                          0%, 60%, 100% {
                            transform: translateY(0);
                            opacity: 0.5;
                          }
                          30% {
                            transform: translateY(-10px);
                            opacity: 1;
                          }
                        }
                      `}</style>
                    </div>
                  </div>
                )}

                {streamingText && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "12px",
                    }}
                  >
                    <div
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "50%",
                        backgroundColor: COLORS.primary,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        marginTop: "2px",
                      }}
                    >
                      <ChatIcon size={18} color={COLORS.dark} />
                    </div>
                    <div
                      style={{
                        flex: 1,
                      }}
                    >
                      <MarkdownRenderer content={streamingText} />
                      <span
                        style={{
                          display: "inline-block",
                          width: "2px",
                          height: "16px",
                          backgroundColor: COLORS.dark,
                          marginLeft: "2px",
                          animation: "blink 1s infinite",
                        }}
                      >
                        <style>{`
                        @keyframes blink {
                          0%, 50% { opacity: 1; }
                          51%, 100% { opacity: 0; }
                        }
                      `}</style>
                      </span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* 입력 영역 */}
            <div
              style={{
                position: "fixed",
                bottom: "40px",
                left: showHistory ? "calc(50% + 170px)" : "calc(50% + 30px)", // 사이드바 상태에 따른 중앙 조정
                transform: "translateX(-50%)",
                width: "100%",
                maxWidth: "900px",
                marginLeft: "auto",
                marginRight: "auto",
                zIndex: 998,
                transition: "left 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
              }}
            >
              <form
                onSubmit={handleSubmit}
                style={{
                  position: "relative",
                  display: "flex",
                  alignItems: "center",
                  width: "100%",
                }}
              >
                <input
                  ref={inputRef}
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="질문을 입력하세요..."
                  disabled={isSubmitting}
                  style={{
                    flex: 1,
                    padding: "12px 100px 12px 20px",
                    border: `1.5px solid ${
                      message.trim() ? COLORS.primary : "#ddd"
                    }`,
                    borderRadius: "24px",
                    fontSize: "14px",
                    backgroundColor: COLORS.white,
                    color: COLORS.dark,
                    outline: "none",
                    transition: "border-color 0.2s",
                    opacity: isSubmitting ? 0.6 : 1,
                    cursor: isSubmitting ? "not-allowed" : "text",
                  }}
                  onFocus={(e) => {
                    if (!isSubmitting) {
                      e.target.style.borderColor = COLORS.primary;
                    }
                  }}
                  onBlur={(e) => (e.target.style.borderColor = "#ddd")}
                />
                <div
                  style={{
                    position: "absolute",
                    right: "8px",
                    display: "flex",
                    gap: "8px",
                    alignItems: "center",
                  }}
                >
                  <button
                    type="button"
                    onClick={handleThinkingClick}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "6px 12px",
                      backgroundColor: isThinkingMode
                        ? COLORS.primary
                        : COLORS.white,
                      border: `1.5px solid ${
                        isThinkingMode ? COLORS.primary : "#ddd"
                      }`,
                      borderRadius: "16px",
                      cursor: "pointer",
                      transition: "all 0.2s",
                      fontSize: "13px",
                      fontWeight: "500",
                      color: COLORS.dark,
                    }}
                    onMouseEnter={(e) => {
                      if (!isThinkingMode) {
                        e.currentTarget.style.borderColor = COLORS.primary;
                        e.currentTarget.style.backgroundColor = COLORS.tertiary;
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isThinkingMode) {
                        e.currentTarget.style.borderColor = "#ddd";
                        e.currentTarget.style.backgroundColor = COLORS.white;
                      }
                    }}
                  >
                    {isThinkingMode ? (
                      <CloseIcon size={14} color={COLORS.dark} />
                    ) : (
                      <ThinkingIcon size={16} color={COLORS.dark} />
                    )}
                    <span>Thinking</span>
                  </button>

                  {isSubmitting ? (
                    <button
                      type="button"
                      onClick={handleStopSubmit}
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "8px",
                        backgroundColor: COLORS.cardSky,
                        border: "none",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "all 0.2s",
                        padding: 0,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = "scale(1.05)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = "scale(1)";
                      }}
                    >
                      <StopIcon
                        size={16}
                        color={COLORS.cardSky}
                        fillColor={COLORS.sub_color}
                      />
                    </button>
                  ) : (
                    <button
                      type="submit"
                      disabled={!message.trim()}
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "8px",
                        backgroundColor: message.trim()
                          ? COLORS.primary
                          : COLORS.lightGray,
                        border: "none",
                        cursor: message.trim() ? "pointer" : "not-allowed",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "all 0.2s",
                        padding: 0,
                      }}
                      onMouseEnter={(e) => {
                        if (message.trim()) {
                          e.currentTarget.style.transform = "scale(1.05)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = "scale(1)";
                      }}
                    >
                      <SendIcon
                        size={16}
                        color={message.trim() ? COLORS.dark : COLORS.gray}
                      />
                    </button>
                  )}
                </div>
              </form>
            </div>
          </div>
        ) : (
          /* 메시지가 없을 때 */
          <div
            style={{
              width: "100%",
              maxWidth: "900px",
              marginLeft: "auto",
              marginRight: "auto",
              marginTop: "-40px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              flex: 1,
              gap: "32px",
              paddingLeft: showHistory ? "340px" : "60px",
              transition: "padding-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            }}
          >
            <div
              style={{
                textAlign: "center",
              }}
            >
              <h1
                style={{
                  fontFamily: "'SB 어그로', 'Pretendard', sans-serif",
                  fontSize: "clamp(32px, 5vw, 40px)",
                  fontWeight: "500",
                  color: "#effd9a",
                  margin: 0,
                  lineHeight: "1.2",
                }}
              >
                {`${nickname}님, 조선역사에 대해서 궁금하신게 있으신가요?`}
              </h1>
            </div>

            <div
              style={{
                width: "100%",
                maxWidth: "900px",
                margin: "0 auto",
              }}
            >
              <form onSubmit={handleSubmit}>
                <div
                  style={{
                    position: "relative",
                    backgroundColor: COLORS.white,
                    borderRadius: "16px",
                    border: `2px solid ${
                      message.trim() ? COLORS.primary : "#ddd"
                    }`,
                    padding: "20px 100px 20px 20px",
                    transition: "border-color 0.2s",
                    minHeight: "80px",
                    display: "flex",
                    alignItems: "flex-start",
                  }}
                >
                  <textarea
                    ref={inputRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="질문을 입력하세요..."
                    disabled={isSubmitting}
                    style={{
                      width: "100%",
                      border: "none",
                      outline: "none",
                      fontSize: "16px",
                      color: COLORS.dark,
                      backgroundColor: "transparent",
                      resize: "none",
                      fontFamily: "inherit",
                      lineHeight: "1.5",
                      minHeight: "40px",
                      paddingTop: 0,
                      opacity: isSubmitting ? 0.6 : 1,
                      cursor: isSubmitting ? "not-allowed" : "text",
                    }}
                    rows={1}
                    onInput={(e) => {
                      e.target.style.height = "auto";
                      e.target.style.height =
                        Math.max(40, e.target.scrollHeight) + "px";
                      const container = e.target
                        .closest("form")
                        .querySelector("div");
                      if (container) {
                        container.style.minHeight =
                          Math.max(80, e.target.scrollHeight + 40) + "px";
                      }
                    }}
                  />

                  <div
                    style={{
                      position: "absolute",
                      bottom: "12px",
                      right: "12px",
                      display: "flex",
                      gap: "8px",
                      alignItems: "center",
                    }}
                  >
                    <button
                      type="button"
                      onClick={handleThinkingClick}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "6px 12px",
                        backgroundColor: isThinkingMode
                          ? COLORS.primary
                          : COLORS.white,
                        border: `1.5px solid ${
                          isThinkingMode ? COLORS.primary : "#ddd"
                        }`,
                        borderRadius: "16px",
                        cursor: "pointer",
                        transition: "all 0.2s",
                        fontSize: "13px",
                        fontWeight: "500",
                        color: COLORS.dark,
                      }}
                      onMouseEnter={(e) => {
                        if (!isThinkingMode) {
                          e.currentTarget.style.borderColor = COLORS.primary;
                          e.currentTarget.style.backgroundColor =
                            COLORS.tertiary;
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isThinkingMode) {
                          e.currentTarget.style.borderColor = "#ddd";
                          e.currentTarget.style.backgroundColor = COLORS.white;
                        }
                      }}
                    >
                      {isThinkingMode ? (
                        <CloseIcon size={14} color={COLORS.dark} />
                      ) : (
                        <ThinkingIcon size={16} color={COLORS.dark} />
                      )}
                      <span>Thinking</span>
                    </button>

                    {isSubmitting ? (
                      <button
                        type="button"
                        onClick={handleStopSubmit}
                        style={{
                          width: "32px",
                          height: "32px",
                          borderRadius: "8px",
                          backgroundColor: COLORS.cardSky,
                          border: "none",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          transition: "all 0.2s",
                          padding: 0,
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = "scale(1.05)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = "scale(1)";
                        }}
                      >
                        <StopIcon
                          size={16}
                          color={COLORS.cardSky}
                          fillColor={COLORS.sub_color}
                        />
                      </button>
                    ) : (
                      <button
                        type="submit"
                        disabled={!message.trim()}
                        style={{
                          width: "32px",
                          height: "32px",
                          borderRadius: "8px",
                          backgroundColor: message.trim()
                            ? COLORS.primary
                            : COLORS.lightGray,
                          border: "none",
                          cursor: message.trim() ? "pointer" : "not-allowed",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          transition: "all 0.2s",
                          padding: 0,
                        }}
                        onMouseEnter={(e) => {
                          if (message.trim()) {
                            e.currentTarget.style.transform = "scale(1.05)";
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = "scale(1)";
                        }}
                      >
                        <SendIcon
                          size={16}
                          color={message.trim() ? COLORS.dark : COLORS.gray}
                        />
                      </button>
                    )}
                  </div>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Chatbot;
