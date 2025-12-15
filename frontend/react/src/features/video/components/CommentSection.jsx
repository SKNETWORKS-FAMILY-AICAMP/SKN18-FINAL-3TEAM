import { useState, useEffect } from "react";
import { COLORS } from "../../../constants/theme";
import { UserIcon, SendIcon } from "../../../components/common/Icons";
import Comment from "./Comment";
import { createComment } from "../../../api/communityApi";
import { getProfileImageUrl } from "../../../utils/imageUtils";

const CommentSection = ({
  comments,
  videoId,
  user,
  onCommentDelete,
  onCommentAdd,
}) => {
  const [commentText, setCommentText] = useState("");
  const [commentsList, setCommentsList] = useState(comments);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // comments prop이 변경되면 상태 업데이트
  useEffect(() => {
    setCommentsList(comments);
  }, [comments]);

  const handleSubmit = async () => {
    if (!commentText.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const response = await createComment(videoId, commentText.trim());
      if (response?.data) {
        // 새 댓글을 목록에 추가
        const newComment = {
          id: response.data.id,
          text: response.data.comment_content,
          comment_content: response.data.comment_content,
          author:
            user?.nickname || user?.display_name || user?.email?.split("@")[0],
          profileImage: user?.profile_image,
          created_at: response.data.created_at || new Date().toISOString(),
          likes: 0,
          replies: [],
          user: {
            id: user?.id,
            nickname: user?.nickname,
            display_name: user?.display_name,
            profile_image: user?.profile_image,
          },
        };
        setCommentsList([newComment, ...commentsList]);
        if (onCommentAdd) {
          onCommentAdd(newComment);
        }
      }
      setCommentText("");
    } catch (error) {
      console.error("댓글 작성 실패:", error);
      console.error("에러 상세:", {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        headers: error.response?.headers,
      });

      if (error.response?.status === 403) {
        const token = localStorage.getItem("access_token");
        console.log(
          "현재 토큰:",
          token ? token.substring(0, 20) + "..." : "없음"
        );
        alert("권한이 없습니다. 다시 로그인해주세요.");
      } else {
        alert("댓글 작성에 실패했습니다.");
      }
    } finally {
      setIsSubmitting(false);
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
        <div style={{ display: "flex", flexDirection: "column" }}>
          {commentsList.map((comment, index) => (
            <div key={`comment-wrapper-${comment.id || index}`}>
              <Comment
                key={`comment-${comment.id || index}`}
                comment={comment}
                currentUser={user}
                isLast={index === commentsList.length - 1}
                onDelete={(commentId) => {
                  setCommentsList((prev) =>
                    prev.filter((c) => c.id !== commentId)
                  );
                  if (onCommentDelete) {
                    onCommentDelete(commentId);
                  }
                }}
                onReplyAdd={(commentId, newReply) => {
                  // 답글 추가 시 로컬 상태 업데이트
                  console.log("답글 추가:", commentId, newReply);
                }}
              />
            </div>
          ))}
        </div>
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
              backgroundColor: user?.profile_image
                ? "transparent"
                : COLORS.lightGray,
              backgroundImage: user?.profile_image
                ? `url(${getProfileImageUrl(user.profile_image)})`
                : "none",
              backgroundSize: "cover",
              backgroundPosition: "center",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {!user?.profile_image && <UserIcon size={16} />}
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
