import { useState } from "react";
import { COLORS } from "../constants/theme";
import { ArrowLeftIcon } from "../components/common/Icons";

const VideoCreatePage = ({ onNavigate }) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!title.trim()) {
      setMessage({ type: "error", text: "제목을 입력해주세요." });
      return;
    }

    setIsSubmitting(true);
    setMessage({ type: "", text: "" });

    // TODO: API 연결
    try {
      // API 호출 예정
      console.log("영상 만들기 제출:", { title, description });
      
      // 임시 성공 메시지
      setTimeout(() => {
        setMessage({
          type: "success",
          text: "영상 생성 요청이 제출되었습니다. (API 연결 예정)",
        });
        setIsSubmitting(false);
        setTitle("");
        setDescription("");
      }, 1000);
    } catch (error) {
      console.error("영상 생성 실패:", error);
      setMessage({ type: "error", text: "영상 생성 중 오류가 발생했습니다." });
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "calc(100vh - 76px)",
        backgroundColor: COLORS.background,
        padding: "60px",
      }}
    >
      <div
        style={{
          maxWidth: "800px",
          margin: "0 auto",
        }}
      >
        {/* 뒤로가기 버튼 */}
        <button
          onClick={() => onNavigate("main")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "14px",
            color: COLORS.textSecondary,
            marginBottom: "32px",
            padding: 0,
          }}
        >
          <ArrowLeftIcon size={18} color={COLORS.textSecondary} />
          메인으로 돌아가기
        </button>

        {/* 제목 */}
        <h1
          style={{
            fontSize: "32px",
            fontWeight: "700",
            color: COLORS.dark,
            marginBottom: "8px",
          }}
        >
          영상만들기
        </h1>
        <p
          style={{
            fontSize: "14px",
            color: COLORS.gray,
            marginBottom: "40px",
          }}
        >
          AI를 활용하여 영상을 생성해보세요. (API 연결 예정)
        </p>

        {/* 영상 생성 폼 */}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "24px" }}>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: "600",
                color: COLORS.dark,
                marginBottom: "8px",
              }}
            >
              영상 제목 *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="영상 제목을 입력해주세요"
              style={{
                width: "100%",
                padding: "12px 16px",
                border: "1.5px solid #ddd",
                borderRadius: "8px",
                fontSize: "14px",
                backgroundColor: COLORS.white,
                color: COLORS.dark,
                outline: "none",
                transition: "border-color 0.2s",
                boxSizing: "border-box",
              }}
              onFocus={(e) => (e.target.style.borderColor = COLORS.primary)}
              onBlur={(e) => (e.target.style.borderColor = "#ddd")}
            />
          </div>

          <div style={{ marginBottom: "24px" }}>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: "600",
                color: COLORS.dark,
                marginBottom: "8px",
              }}
            >
              영상 설명 (선택사항)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="영상에 대한 설명을 입력해주세요..."
              rows={6}
              style={{
                width: "100%",
                padding: "16px",
                border: "1.5px solid #ddd",
                borderRadius: "12px",
                fontSize: "14px",
                backgroundColor: COLORS.white,
                color: COLORS.dark,
                outline: "none",
                transition: "border-color 0.2s",
                boxSizing: "border-box",
                resize: "vertical",
                fontFamily: "inherit",
              }}
              onFocus={(e) => (e.target.style.borderColor = COLORS.primary)}
              onBlur={(e) => (e.target.style.borderColor = "#ddd")}
            />
          </div>

          {/* 메시지 */}
          {message.text && (
            <div
              style={{
                padding: "12px 16px",
                borderRadius: "8px",
                marginBottom: "24px",
                backgroundColor:
                  message.type === "success" ? "#d4edda" : "#f8d7da",
                color: message.type === "success" ? "#155724" : "#721c24",
                fontSize: "14px",
              }}
            >
              {message.text}
            </div>
          )}

          {/* 제출 버튼 */}
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              width: "100%",
              padding: "14px",
              backgroundColor: isSubmitting ? COLORS.lightGray : "#effd9a",
              border: "none",
              borderRadius: "8px",
              fontSize: "16px",
              fontWeight: "600",
              color: COLORS.dark,
              cursor: isSubmitting ? "not-allowed" : "pointer",
              transition: "opacity 0.2s",
            }}
            onMouseEnter={(e) =>
              !isSubmitting && (e.currentTarget.style.opacity = 0.8)
            }
            onMouseLeave={(e) => (e.currentTarget.style.opacity = 1)}
          >
            {isSubmitting ? "생성 중..." : "영상 생성 요청"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default VideoCreatePage;

