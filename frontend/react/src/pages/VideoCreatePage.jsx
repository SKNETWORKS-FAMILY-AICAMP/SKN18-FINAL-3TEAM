import { useState, useRef, useEffect } from "react";
import { COLORS } from "../constants/theme";
import { SendIcon } from "../components/common/Icons";
import { createVideo } from "../api/videoApi";
import VideoPlayer from "../features/video/components/VideoPlayer";
import { getVideoUrl } from "../utils/imageUtils";
import { useBackgroundTask } from "../contexts/BackgroundTaskContext";

// 환영 메시지 컴포넌트 (스트리밍 애니메이션)
const VideoCreateWelcomeMessage = ({ nickname }) => {
  const [displayedName, setDisplayedName] = useState("");
  const [displayedQuestion, setDisplayedQuestion] = useState("");
  const nameText = `${nickname}님,`;
  const questionText = "어떤 이야기를 들려드릴까요?";

  useEffect(() => {
    // 초기화
    setDisplayedName("");
    setDisplayedQuestion("");
    
    // 이름 텍스트 스트리밍
    let nameIndex = 0;
    const nameInterval = setInterval(() => {
      if (nameIndex < nameText.length) {
        setDisplayedName(nameText.slice(0, nameIndex + 1));
        nameIndex++;
      } else {
        clearInterval(nameInterval);
        // 이름이 완성되면 질문 텍스트 스트리밍 시작
        let questionIndex = 0;
        const questionInterval = setInterval(() => {
          if (questionIndex < questionText.length) {
            setDisplayedQuestion(questionText.slice(0, questionIndex + 1));
            questionIndex++;
          } else {
            clearInterval(questionInterval);
          }
        }, 50);
        return () => clearInterval(questionInterval);
      }
    }, 100);
    return () => clearInterval(nameInterval);
  }, [nickname]);

  return (
    <>
      <div
        style={{
          fontFamily: "'Noto Serif KR', serif",
          fontSize: "clamp(28px, 4vw, 36px)",
          fontWeight: "700",
          color: COLORS.white,
          margin: 0,
          lineHeight: "1.4",
          marginBottom: "0.5rem",
        }}
      >
        {displayedName}
        {displayedName.length < `${nickname}님,`.length && (
          <span style={{ opacity: 0.5 }}>|</span>
        )}
      </div>
      <div
        style={{
          fontFamily: "'Noto Serif KR', serif",
          fontSize: "clamp(18px, 2.5vw, 24px)",
          fontWeight: "300",
          color: COLORS.white,
          margin: 0,
          lineHeight: "1.5",
          opacity: 0.9,
        }}
      >
        {displayedQuestion}
        {displayedQuestion.length < "어떤 이야기를 들려드릴까요?".length && (
          <span style={{ opacity: 0.5 }}>|</span>
        )}
      </div>
    </>
  );
};

const VideoCreatePage = ({ onNavigate, user }) => {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef(null);
  const containerRef = useRef(null);
  const { registerTask } = useBackgroundTask();

  const nickname =
    user?.nickname ||
    user?.display_name ||
    user?.email?.split("@")[0] ||
    "사용자";

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
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!message.trim() || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setIsLoading(true);
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

    // 백그라운드 작업으로 등록
    const videoCreationPromise = createVideo(userMessage)
      .then((response) => {
        // API 응답에서 video_url을 받아서 처리
        if (response.video_url) {
          // video_url이 있으면 영상만 표시 (메시지 없음)
          setMessages((prev) => [
            ...prev,
            {
              type: "assistant",
              video_url: response.video_url,
            },
          ]);
          return { success: true, video_url: response.video_url };
        } else {
          // video_url이 없으면 에러 메시지 표시
          let errorMessage = "영상 생성에 실패했습니다. 다시 시도해주세요.";
          setMessages((prev) => [
            ...prev,
            {
              type: "assistant",
              error: errorMessage,
            },
          ]);
          throw new Error(errorMessage);
        }
      })
      .catch((error) => {
        console.error("영상 생성 실패:", error);

        let errorMessage = "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.";

        if (error.response?.status === 404) {
          errorMessage =
            "영상 만들기 API가 아직 구현되지 않았습니다. 백엔드 개발자에게 문의해주세요.";
        } else if (error.response?.status === 500) {
          errorMessage = "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
        } else if (error.response?.data?.error) {
          errorMessage = error.response.data.error;
        } else if (error.message) {
          errorMessage = error.message;
        }

        setMessages((prev) => [
          ...prev,
          {
            type: "assistant",
            error: errorMessage,
          },
        ]);

        throw error;
      })
      .finally(() => {
        setTimeout(() => {
          setIsSubmitting(false);
          setIsLoading(false);
        }, 300);
      });

    // 백그라운드 작업으로 등록
    registerTask("영상 생성", videoCreationPromise);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey && !isSubmitting) {
      e.preventDefault();
      handleSubmit(e);
    }
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
      className={messages.length > 0 ? "chat-page" : ""}
      style={{
        height: "calc(100vh - 76px)",
        maxHeight: "calc(100vh - 76px)",
        backgroundColor: messages.length > 0 ? "var(--cream)" : COLORS.background,
        display: "flex",
        flexDirection: "row",
        padding: 0,
        position: "relative",
        overflow: "hidden",
        touchAction: messages.length > 0 ? "none" : "auto",
      }}
    >
      {/* 메인 컨텐츠 */}
      <div
        className={messages.length > 0 ? "chat-main" : ""}
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          padding: messages.length > 0 ? "0" : "40px 60px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* 메시지가 있을 때 */}
        {messages.length > 0 ? (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              maxWidth: "1200px",
              width: "100%",
              marginLeft: "auto",
              marginRight: "auto",
              height: "100%",
              minHeight: 0,
              position: "relative",
            }}
          >
            {/* 대화 목록 */}
            <div
              ref={containerRef}
              className={messages.length > 0 ? "chat-messages" : ""}
              style={{
                flex: 1,
                overflowY: "auto",
                overflowX: "hidden",
                padding: messages.length > 0 ? "2rem 4rem" : "0 8px 120px 0",
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
                  gap: "32px",
                }}
              >
                {messages.map((msg, index) => (
                  <div key={index}>
                    {msg.type === "user" && (
                      <div className="chat-message user">
                        <div className="chat-message-bubble">
                          {msg.text}
                        </div>
                      </div>
                    )}

                    {msg.type === "assistant" && (
                      <div className="chat-message bot">
                        <div className="chat-message-header">
                          <div className="chat-message-avatar">秀</div>
                          <span className="chat-message-name">아가씨</span>
                        </div>
                        <div className="chat-message-bubble">
                          {/* 영상이 있으면 VideoPlayer 표시 */}
                          {msg.video_url && (
                            <div
                              style={{
                                width: "100%",
                                maxWidth: "100%",
                                marginBottom: "1rem",
                              }}
                            >
                              <VideoPlayer
                                videoUrl={
                                  getVideoUrl(msg.video_url) || msg.video_url
                                }
                              />
                            </div>
                          )}
                          {/* 에러가 있으면 표시 (에러 상황일 때만) */}
                          {msg.error && (
                            <div
                              style={{
                                fontSize: "14px",
                                color: "#e63946",
                                lineHeight: "1.8",
                                whiteSpace: "pre-wrap",
                                wordWrap: "break-word",
                              }}
                            >
                              {msg.error}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {/* 로딩 중 표시 */}
                {isLoading && (
                  <div
                    style={{
                      fontSize: "14px",
                      color: COLORS.gray,
                      fontStyle: "italic",
                    }}
                  >
                    영상을 생성하고 있습니다...
                  </div>
                )}
              </div>
            </div>

            {/* 입력 영역 */}
            <div className={messages.length > 0 ? "chat-input-area" : ""} style={messages.length > 0 ? {} : {
              position: "fixed",
              bottom: "40px",
              left: "50%",
              transform: "translateX(-50%)",
              width: "calc(100% - 120px)",
              maxWidth: "1200px",
              zIndex: 998,
            }}>
              <form onSubmit={handleSubmit}>
                {messages.length > 0 ? (
                  <div className="chat-input-wrapper">
                    <input
                      ref={inputRef}
                      type="text"
                      className="chat-input"
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="영상에 대한 설명을 입력하세요..."
                      disabled={isSubmitting}
                    />
                    <button
                      type="submit"
                      disabled={!message.trim() || isSubmitting}
                      className="chat-send-btn"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                      >
                        <path d="M5 12h14M12 5l7 7-7 7" />
                      </svg>
                    </button>
                  </div>
                ) : (
                  <>
                    <input
                      ref={inputRef}
                      type="text"
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="영상에 대한 설명을 입력하세요..."
                      disabled={isSubmitting}
                      style={{
                        flex: 1,
                        padding: "12px 60px 12px 20px",
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
                  </>
                )}
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
                width: "100%",
                maxWidth: "800px",
              }}
            >
              <VideoCreateWelcomeMessage nickname={nickname} />
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
                    placeholder="영상에 대한 설명을 입력하세요..."
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

export default VideoCreatePage;
