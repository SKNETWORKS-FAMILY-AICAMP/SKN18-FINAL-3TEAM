import { useState, useRef, useEffect } from "react";
import { COLORS } from "../../constants/theme";
import { ChatIcon } from "./Icons";

const ChatbotButton = ({ onNavigate }) => {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef(null);
  const buttonRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        showMenu &&
        menuRef.current &&
        buttonRef.current &&
        !menuRef.current.contains(event.target) &&
        !buttonRef.current.contains(event.target)
      ) {
        setShowMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showMenu]);

  const handleQuestionClick = () => {
    setShowMenu(false);
    if (onNavigate) {
      onNavigate("question", null, { newChat: true });
    }
  };

  const handleVideoCreateClick = () => {
    setShowMenu(false);
    if (onNavigate) {
      onNavigate("video-create");
    }
  };

  return (
    <>
      {/* 챗봇 버튼 */}
      <button
        ref={buttonRef}
        onClick={() => setShowMenu(!showMenu)}
        style={{
          position: "fixed",
          bottom: "24px",
          right: "24px",
          width: "56px",
          height: "56px",
          borderRadius: "50%",
          backgroundColor: COLORS.primary,
          border: "none",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
          zIndex: 999,
          transition: "transform 0.2s ease, box-shadow 0.2s ease",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = "scale(1.1)";
          e.currentTarget.style.boxShadow = "0 6px 16px rgba(0, 0, 0, 0.2)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = "scale(1)";
          e.currentTarget.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.15)";
        }}
      >
        <ChatIcon size={28} color={COLORS.dark} />
      </button>

      {/* 선택 메뉴 */}
      {showMenu && (
        <div
          ref={menuRef}
          style={{
            position: "fixed",
            bottom: "92px",
            right: "24px",
            backgroundColor: COLORS.white,
            borderRadius: "12px",
            padding: "8px 0",
            minWidth: "160px",
            boxShadow: "0 4px 16px rgba(0, 0, 0, 0.15)",
            zIndex: 1000,
            animation: "slideUp 0.2s ease",
          }}
        >
          <style>{`
            @keyframes slideUp {
              from {
                opacity: 0;
                transform: translateY(10px);
              }
              to {
                opacity: 1;
                transform: translateY(0);
              }
            }
          `}</style>
          <div
            onClick={handleQuestionClick}
            style={{
              padding: "12px 20px",
              color: COLORS.dark,
              fontSize: "14px",
              fontWeight: "500",
              cursor: "pointer",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(0, 0, 0, 0.05)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
          >
            질문하기
          </div>
          <div
            onClick={handleVideoCreateClick}
            style={{
              padding: "12px 20px",
              color: COLORS.dark,
              fontSize: "14px",
              fontWeight: "500",
              cursor: "pointer",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(0, 0, 0, 0.05)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
          >
            영상만들기
          </div>
        </div>
      )}
    </>
  );
};

export default ChatbotButton;
