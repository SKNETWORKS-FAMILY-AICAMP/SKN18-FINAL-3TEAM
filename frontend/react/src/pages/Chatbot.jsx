import { useState, useRef, useEffect } from "react";
import { COLORS } from "../constants/theme";
import {
  SendIcon,
  StopIcon,
  ThinkingIcon,
  CloseIcon,
  ChatIcon,
} from "../components/common/Icons";
import {
  sendQuestion,
  getChatHistory,
  getChatSession,
  createChatSession,
  deleteChatSession,
} from "../api/chatApi";

const Chatbot = ({ onNavigate, user, newChatTrigger }) => {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [showSoonMessage, setShowSoonMessage] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [isThinkingMode, setIsThinkingMode] = useState(false); // Thinking 모드 상태 추가
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
    console.log("[hydrateMessages] 🔍 Raw messages from DB:", sessionMessages);
    const normalized = sessionMessages.map((msg) => {
      // 재질문 메타데이터 체크
      console.log("[hydrateMessages] Checking message:", { role: msg.role, contentStart: msg.content?.substring(0, 50) });
      if (msg.role === "assistant" && msg.content.startsWith("__CLARIFICATION_METADATA__:")) {
        console.log("[hydrateMessages] ✅ Found clarification metadata!");
        try {
          const jsonStr = msg.content.substring("__CLARIFICATION_METADATA__:".length);
          console.log("[hydrateMessages] JSON string:", jsonStr);
          const metadata = JSON.parse(jsonStr);
          console.log("[hydrateMessages] Parsed metadata:", metadata);
          return {
            type: "clarification",
            question: metadata.question,
            options: metadata.options,
            isActive: false, // 과거 기록은 비활성화
          };
        } catch (e) {
          console.error("[hydrateMessages] ❌ Failed to parse clarification metadata:", e);
          console.error("[hydrateMessages] Content was:", msg.content);
          // 파싱 실패 시 일반 메시지로 fallback
          return {
            type: "assistant",
            text: msg.content,
          };
        }
      }

      // 일반 메시지
      return {
        type: msg.role === "assistant" ? "assistant" : "user",
        text: msg.content,
      };
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
        // 세션 자동 로드는 하지 않음. 사용자가 히스토리에서 선택할 때만 불러온다.
        setSelectedSessionId(null);
        setMessages([]);
      } catch (error) {
        if (error.response?.status === 404) {
          console.warn("대화 기록 API가 아직 구현되지 않았습니다.");
          setChatHistory([]);
        } else {
          console.error("대화 기록 로드 실패:", error);
          setChatHistory([]);
        }
      }
    };
    loadChatHistory();
  }, []);

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

    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        simulateStreamingResponse("로그인 후에 질문할 수 있어요.");
        setIsSubmitting(false);
        abortControllerRef.current = null;
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

      const response = await sendQuestion(
        userMessage,
        sessionId,
        isThinkingMode,
        abortControllerRef.current.signal
      );

      // 디버깅: 응답 확인
      console.log("[Chatbot] Response:", {
        needs_clarification: response.needs_clarification,
        has_expansion_directions: !!response.expansion_directions,
        expansion_directions_count: response.expansion_directions?.length || 0,
        clarification_question: response.clarification_question,
        thinking_mode: isThinkingMode,
      });

      // 재질문이 있는 경우
      if (
        response.needs_clarification &&
        response.expansion_directions &&
        response.expansion_directions.length > 0
      ) {
        console.log(
          "[Chatbot] Showing clarification UI with",
          response.expansion_directions.length,
          "options"
        );
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
        return;
      }

      if (response.answer) {
        simulateStreamingResponse(response.answer);
      } else {
        simulateStreamingResponse("답변을 받을 수 없습니다.");
      }
    } catch (error) {
      // 사용자가 취소한 경우
      if (error.name === "CanceledError" || error.code === "ERR_CANCELED") {
        console.log("요청이 취소되었습니다.");
        // 마지막 사용자 메시지 제거
        setMessages((prev) => prev.slice(0, -1));
        setIsSubmitting(false);
        abortControllerRef.current = null;
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

  const simulateStreamingResponse = (text) => {
    setStreamingText("");
    let index = 0;
    const interval = setInterval(() => {
      if (index < text.length) {
        setStreamingText(text.substring(0, index + 1));
        index++;
      } else {
        clearInterval(interval);
        setMessages((prev) => [...prev, { type: "assistant", text: text }]);
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

    // AbortController 생성
    abortControllerRef.current = new AbortController();

    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        simulateStreamingResponse("로그인 후에 질문할 수 있어요.");
        setIsSubmitting(false);
        abortControllerRef.current = null;
        return;
      }

      // 선택한 방향을 백엔드로 전달 (direction_id와 title 함께 전송)
      const response = await sendQuestion(
        `__CLARIFICATION__:${directionId}:${optionTitle}`,
        selectedSessionId,
        isThinkingMode,
        abortControllerRef.current.signal
      );

      if (response.answer) {
        simulateStreamingResponse(response.answer);
      } else {
        simulateStreamingResponse("답변을 받을 수 없습니다.");
      }
    } catch (error) {
      // 사용자가 취소한 경우
      if (error.name === "CanceledError" || error.code === "ERR_CANCELED") {
        console.log("요청이 취소되었습니다.");
        setMessages((prev) => prev.slice(0, -1));
        setIsSubmitting(false);
        abortControllerRef.current = null;
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
        height: "calc(100vh - 76px)",
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
              left: showHistory ? "300px" : "0px",
              top: "126px",
              width: "auto",
              height: "auto",
              padding: "8px",
              backgroundColor: "transparent",
              border: "none",
              outline: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1001,
              transition: "left 0.3s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "scale(1.1)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "scale(1)";
            }}
          >
            <svg
              width="36"
              height="36"
              viewBox="0 0 24 24"
              fill="none"
              stroke={COLORS.dark}
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{
                transform: showHistory ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 0.3s ease",
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
              top: "96px",
              width: "300px",
              backgroundColor: "transparent",
              display: "flex",
              flexDirection: "column",
              overflowY: "auto",
              overflowX: "hidden",
              height: "calc(100vh - 96px)",
              padding: "40px 20px",
              transition: "left 0.3s ease",
              zIndex: 1000,
            }}
          >
            <div
              style={{
                padding: "0 0 16px 0",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
                alignItems: "flex-start",
              }}
            >
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
                  alignSelf: "flex-start",
                  border: "none",
                  background: "transparent",
                  color: COLORS.dark,
                  cursor: "pointer",
                  fontSize: "16px",
                  padding: "4px 0px",
                  borderRadius: "8px",
                  transition: "background 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = COLORS.lightGray;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "transparent";
                }}
              >
                새 채팅
              </button>
              <span
                style={{
                  fontSize: "16px",
                  fontWeight: "600",
                  color: COLORS.dark,
                  marginTop: "4px",
                  paddingLeft: "2px",
                }}
              >
                대화 기록
              </span>
            </div>
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "0",
                paddingLeft: "2px",
              }}
            >
              {chatHistory.map((session) => (
                <div
                  key={session.id}
                  onClick={async () => {
                    setSelectedSessionId(session.id);
                    setMessages([]);
                    try {
                      const sessionData = await getChatSession(session.id);
                      hydrateMessages(sessionData?.messages || []);
                    } catch (error) {
                      console.error("세션 불러오기 실패:", error);
                    }
                  }}
                  style={{
                    position: "relative",
                    padding: "12px",
                    marginBottom: "8px",
                    borderRadius: "8px",
                    cursor: "pointer",
                    backgroundColor:
                      selectedSessionId === session.id
                        ? COLORS.tertiary
                        : "transparent",
                    transition: "background 0.2s",
                  }}
                  onMouseEnter={(e) => {
                    if (selectedSessionId !== session.id) {
                      e.currentTarget.style.backgroundColor = COLORS.lightGray;
                    }
                    const btn = e.currentTarget.querySelector(
                      ".session-delete-btn"
                    );
                    if (btn) btn.style.opacity = 1;
                  }}
                  onMouseLeave={(e) => {
                    if (selectedSessionId !== session.id) {
                      e.currentTarget.style.backgroundColor = "transparent";
                    }
                    const btn = e.currentTarget.querySelector(
                      ".session-delete-btn"
                    );
                    if (btn) btn.style.opacity = 0;
                  }}
                >
                  <div
                    style={{
                      fontSize: "13px",
                      fontWeight: "500",
                      color: COLORS.dark,
                      marginBottom: "4px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {session.title || session.first_message || "대화"}
                  </div>
                  <div
                    style={{
                      fontSize: "11px",
                      color: COLORS.gray,
                    }}
                  >
                    {session.created_at
                      ? new Date(session.created_at).toLocaleDateString("ko-KR")
                      : ""}
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
                        }
                      } catch (error) {
                        console.error("세션 삭제 실패:", error);
                      }
                    }}
                    style={{
                      position: "absolute",
                      top: "50%",
                      right: "16px",
                      transform: "translateY(-50%)",
                      width: "20px",
                      height: "20px",
                      borderRadius: "50%",
                      border: "none",
                      background: "transparent",
                      color: COLORS.gray,
                      cursor: "pointer",
                      opacity: 0,
                      transition: "opacity 0.2s",
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
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
              paddingLeft: showHistory ? "280px" : "0px",
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
                paddingRight: "8px",
                paddingBottom: "120px",
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
              <div
                style={{
                  minHeight: "100%",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "flex-end",
                  gap: "12px",
                }}
              >
                {messages.map((msg, index) => (
                  <div key={index}>
                    {/* 구분선 */}
                    {index > 0 && (
                      <div
                        style={{
                          height: "1px",
                          backgroundColor: COLORS.lightGray,
                          margin: "8px 0",
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
                      }}
                    >
                      {msg.type === "user" ? (
                        <div
                          style={{
                            marginBottom: "8px",
                            padding: "10px 14px",
                            backgroundColor: COLORS.lightGray,
                            borderRadius: "12px",
                            fontSize: "14px",
                            color: COLORS.dark,
                            display: "inline-block",
                            maxWidth: "70%",
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
                              style={{
                                display: "flex",
                                gap: "12px",
                                overflowX: "auto",
                                overflowY: "hidden",
                                paddingBottom: "8px",
                                WebkitOverflowScrolling: "touch", // iOS 부드러운 스크롤
                                scrollbarWidth: "thin", // Firefox 스크롤바
                                msOverflowStyle: "auto", // IE/Edge 스크롤바
                              }}
                            >
                              {msg.options?.map((option, idx) => {
                                const isDisabled = !msg.isActive || isSubmitting;
                                return (
                                  <button
                                    key={option.id}
                                    onClick={() => {
                                      if (msg.isActive && !isSubmitting) {
                                        handleClarificationChoice(
                                          option.direction_id,
                                          option.title
                                        );
                                      }
                                    }}
                                    disabled={isDisabled}
                                    style={{
                                      minWidth: "220px",
                                      maxWidth: "280px",
                                      padding: "16px",
                                      backgroundColor: COLORS.white,
                                      border: `2px solid ${COLORS.border}`,
                                      borderRadius: "16px",
                                      cursor: isDisabled
                                        ? "not-allowed"
                                        : "pointer",
                                      textAlign: "left",
                                      transition: "all 0.2s",
                                      opacity: 1,
                                      flexShrink: 0,
                                      // 마지막 카드에 추가 여백 (스크롤 끝까지 보이도록)
                                      marginRight:
                                        idx === msg.options.length - 1
                                          ? "24px"
                                          : "0px",
                                    }}
                                    onMouseEnter={(e) => {
                                      if (!isDisabled) {
                                        e.currentTarget.style.borderColor =
                                          COLORS.primary;
                                        e.currentTarget.style.backgroundColor =
                                          COLORS.tertiary;
                                        e.currentTarget.style.transform =
                                          "translateY(-2px)";
                                        e.currentTarget.style.boxShadow =
                                          "0 4px 12px rgba(0,0,0,0.1)";
                                      }
                                    }}
                                    onMouseLeave={(e) => {
                                      if (!isDisabled) {
                                        e.currentTarget.style.borderColor =
                                          COLORS.border;
                                        e.currentTarget.style.backgroundColor =
                                          COLORS.white;
                                        e.currentTarget.style.transform =
                                          "translateY(0)";
                                        e.currentTarget.style.boxShadow = "none";
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
                              fontSize: "14px",
                              color: COLORS.dark,
                              lineHeight: "1.5",
                              whiteSpace: "pre-wrap",
                              wordWrap: "break-word",
                              marginBottom: "8px",
                              flex: 1,
                            }}
                          >
                            {msg.text}
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
                        fontSize: "14px",
                        color: COLORS.dark,
                        lineHeight: "1.5",
                        whiteSpace: "pre-wrap",
                        wordWrap: "break-word",
                        flex: 1,
                      }}
                    >
                      {streamingText}
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
                left: showHistory ? "calc(50% + 140px)" : "50%",
                transform: "translateX(-50%)",
                width: "100%",
                maxWidth: "900px",
                marginLeft: "auto",
                marginRight: "auto",
                zIndex: 998,
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
