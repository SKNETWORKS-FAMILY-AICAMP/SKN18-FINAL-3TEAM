import { useState, useRef, useEffect } from "react";
import { COLORS } from "../constants/theme";
import { SendIcon, ThinkingIcon, CloseIcon } from "../components/common/Icons";
import { sendQuestion, getChatHistory } from "../api/chatApi";

const Chatbot = ({ onNavigate, user }) => {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [showSoonMessage, setShowSoonMessage] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const containerRef = useRef(null);

  const nickname =
    user?.nickname ||
    user?.display_name ||
    user?.email?.split("@")[0] ||
    "사용자";

  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const history = await getChatHistory();
        setChatHistory(history || []);
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

    try {
      const response = await sendQuestion(userMessage);

      if (response.answer) {
        simulateStreamingResponse(response.answer);
      } else {
        simulateStreamingResponse("답변을 받을 수 없습니다.");
      }
    } catch (error) {
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

    setTimeout(() => {
      setIsSubmitting(false);
    }, 300);
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
    setShowSoonMessage(true);
    setTimeout(() => {
      setShowSoonMessage(false);
    }, 2000);
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
      {messages.length > 0 && (
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
                padding: "0 0 20px 0",
                fontSize: "16px",
                fontWeight: "600",
                color: COLORS.dark,
              }}
            >
              대화 기록
            </div>
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "0",
              }}
            >
              {chatHistory.length === 0 ? (
                <div
                  style={{
                    padding: "20px",
                    textAlign: "center",
                    color: COLORS.gray,
                    fontSize: "14px",
                  }}
                >
                  대화 기록이 없습니다.
                </div>
              ) : (
                chatHistory.map((session) => (
                  <div
                    key={session.id}
                    onClick={() => {
                      setSelectedSessionId(session.id);
                    }}
                    style={{
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
                        e.currentTarget.style.backgroundColor =
                          COLORS.lightGray;
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (selectedSessionId !== session.id) {
                        e.currentTarget.style.backgroundColor = "transparent";
                      }
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
                        ? new Date(session.created_at).toLocaleDateString(
                            "ko-KR"
                          )
                        : ""}
                    </div>
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
              paddingLeft: "280px",
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
                  gap: "24px",
                }}
              >
                {messages.map((msg, index) => (
                  <div key={index}>
                    {msg.type === "user" && (
                      <div
                        style={{
                          marginBottom: "16px",
                        }}
                      >
                        <div
                          style={{
                            padding: "12px 16px",
                            backgroundColor: COLORS.lightGray,
                            borderRadius: "12px",
                            fontSize: "14px",
                            color: COLORS.dark,
                            display: "inline-block",
                            maxWidth: "70%",
                            wordWrap: "break-word",
                          }}
                        >
                          {msg.text}
                        </div>
                      </div>
                    )}

                    {msg.type === "assistant" && (
                      <div
                        style={{
                          fontSize: "14px",
                          color: COLORS.dark,
                          lineHeight: "1.8",
                          whiteSpace: "pre-wrap",
                          wordWrap: "break-word",
                        }}
                      >
                        {msg.text}
                      </div>
                    )}
                  </div>
                ))}

                {streamingText && (
                  <div
                    style={{
                      fontSize: "14px",
                      color: COLORS.dark,
                      lineHeight: "1.8",
                      whiteSpace: "pre-wrap",
                      wordWrap: "break-word",
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
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* 입력 영역 */}
            <div
              style={{
                position: "fixed",
                bottom: "40px",
                left: "50%",
                transform: "translateX(-50%)",
                width: "calc(100% - 420px)",
                maxWidth: "900px",
                marginLeft: "120px",
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
                      backgroundColor: COLORS.white,
                      border: "1.5px solid #ddd",
                      borderRadius: "16px",
                      cursor: "pointer",
                      transition: "all 0.2s",
                      fontSize: "13px",
                      fontWeight: "500",
                      color: COLORS.dark,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = COLORS.primary;
                      e.currentTarget.style.backgroundColor = COLORS.tertiary;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "#ddd";
                      e.currentTarget.style.backgroundColor = COLORS.white;
                    }}
                  >
                    <ThinkingIcon size={16} color={COLORS.dark} />
                    <span>Thinking</span>
                  </button>

                  <button
                    type="submit"
                    disabled={!message.trim() || isSubmitting}
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "8px",
                      backgroundColor:
                        message.trim() && !isSubmitting
                          ? COLORS.primary
                          : COLORS.lightGray,
                      border: "none",
                      cursor:
                        message.trim() && !isSubmitting
                          ? "pointer"
                          : "not-allowed",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      transition: "all 0.2s",
                      padding: 0,
                    }}
                    onMouseEnter={(e) => {
                      if (message.trim() && !isSubmitting) {
                        e.currentTarget.style.transform = "scale(1.05)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "scale(1)";
                    }}
                  >
                    <SendIcon
                      size={16}
                      color={
                        message.trim() && !isSubmitting
                          ? COLORS.dark
                          : COLORS.gray
                      }
                    />
                  </button>
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
                        backgroundColor: isThinking
                          ? COLORS.secondary
                          : COLORS.white,
                        border: `1.5px solid ${
                          isThinking ? COLORS.secondary : "#ddd"
                        }`,
                        borderRadius: "16px",
                        cursor: "pointer",
                        transition: "all 0.2s",
                        fontSize: "13px",
                        fontWeight: "500",
                        color: COLORS.dark,
                      }}
                      onMouseEnter={(e) => {
                        if (!isThinking) {
                          e.currentTarget.style.borderColor = COLORS.primary;
                          e.currentTarget.style.backgroundColor =
                            COLORS.tertiary;
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isThinking) {
                          e.currentTarget.style.borderColor = "#ddd";
                          e.currentTarget.style.backgroundColor = COLORS.white;
                        }
                      }}
                    >
                      {isThinking ? (
                        <CloseIcon size={14} color={COLORS.dark} />
                      ) : (
                        <ThinkingIcon size={16} color={COLORS.dark} />
                      )}
                      <span>Thinking</span>
                    </button>

                    <button
                      type="submit"
                      disabled={!message.trim() || isSubmitting}
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "8px",
                        backgroundColor:
                          message.trim() && !isSubmitting
                            ? COLORS.primary
                            : COLORS.lightGray,
                        border: "none",
                        cursor:
                          message.trim() && !isSubmitting
                            ? "pointer"
                            : "not-allowed",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "all 0.2s",
                        padding: 0,
                      }}
                      onMouseEnter={(e) => {
                        if (message.trim() && !isSubmitting) {
                          e.currentTarget.style.transform = "scale(1.05)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = "scale(1)";
                      }}
                    >
                      <SendIcon
                        size={16}
                        color={
                          message.trim() && !isSubmitting
                            ? COLORS.dark
                            : COLORS.gray
                        }
                      />
                    </button>
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
