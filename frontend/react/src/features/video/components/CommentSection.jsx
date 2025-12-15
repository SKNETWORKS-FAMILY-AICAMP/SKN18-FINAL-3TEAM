import { useState } from "react";
import { COLORS } from "../../../constants/theme";
import { UserIcon, SendIcon } from "../../../components/common/Icons";
import Comment from "./Comment";

const CommentSection = ({ comments }) => {
  const [commentText, setCommentText] = useState("");

  const handleSubmit = () => {
    if (commentText.trim()) {
      console.log("댓글 제출:", commentText);
      setCommentText("");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      style={{
        width: "380px",
        backgroundColor: COLORS.white,
        borderRadius: "16px",
        border: "1px solid #eee",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        maxHeight: "calc(100vh - 136px)",
      }}
    >
      <div
        style={{
          flex: 1,
          padding: "20px",
          overflowY: "auto",
          overflowX: "hidden",
          minHeight: 0,
        }}
      >
        {comments.map((comment) => (
          <Comment key={comment.id} comment={comment} />
        ))}
      </div>

      <div
        style={{
          padding: "16px 20px",
          borderTop: "1px solid #eee",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            fontSize: "14px",
            fontWeight: "600",
            marginBottom: "12px",
            color: COLORS.dark,
          }}
        >
          댓글 작성하기
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              backgroundColor: COLORS.lightGray,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <UserIcon size={16} />
          </div>
          <div style={{ flex: 1, position: "relative", minWidth: 0 }}>
            <input
              type="text"
              placeholder="댓글을 입력하세요"
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              onKeyDown={handleKeyDown}
              style={{
                width: "100%",
                padding: "10px 40px 10px 14px",
                border: "1.5px solid #ddd",
                borderRadius: "20px",
                fontSize: "13px",
                outline: "none",
                transition: "border-color 0.2s ease",
                boxSizing: "border-box",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
              onFocus={(e) => {
                e.target.style.borderColor = COLORS.primary;
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "#ddd";
              }}
            />
            <button
              onClick={handleSubmit}
              disabled={!commentText.trim()}
              style={{
                position: "absolute",
                right: "4px",
                top: "50%",
                transform: "translateY(-50%)",
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                backgroundColor: commentText.trim()
                  ? COLORS.primary
                  : COLORS.lightGray,
                border: "none",
                cursor: commentText.trim() ? "pointer" : "not-allowed",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all 0.2s ease",
              }}
            >
              <SendIcon
                size={16}
                color={commentText.trim() ? COLORS.dark : "#999"}
              />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommentSection;
