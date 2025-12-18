import { useState, useRef, useLayoutEffect } from "react";
import { COLORS } from "../../../constants/theme";
import {
  UserIcon,
  HeartIcon,
  CloseIcon,
  SendIcon,
  EditIcon,
} from "../../../components/common/Icons";
import {
  deleteComment,
  updateComment,
  createReply,
  likeComment,
  unlikeComment,
  deleteReply,
  updateReply,
} from "../../../api/communityApi";
import { getProfileImageUrl } from "../../../utils/imageUtils";

// 시간 포맷팅 함수
const formatTimeAgo = (dateString) => {
  if (!dateString) return "";

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      console.warn("Invalid date string:", dateString);
      return "";
    }

    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return "방금 전";
    if (diffMin < 60) return `${diffMin}분 전`;
    if (diffHour < 24) return `${diffHour}시간 전`;
    if (diffDay < 7) return `${diffDay}일 전`;

    return date.toLocaleDateString("ko-KR", {
      month: "short",
      day: "numeric",
    });
  } catch (error) {
    console.error("날짜 포맷 오류:", error, dateString);
    return "";
  }
};

// 재귀적 답글 컴포넌트 (유튜브 스타일)
const ReplyItem = ({
  reply,
  currentUser,
  commentId,
  depth = 1,
  onReplyAdd,
  onReplyDelete,
  hasMoreSiblings = false,
  activeReplyId,
  activeEditId,
  onSetActiveReply,
  onSetActiveEdit,
  onClearActive,
}) => {
  const replyId = `reply-${reply.id}`;
  const showReplyInput = activeReplyId === replyId;
  const [replyText, setReplyText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [childReplies, setChildReplies] = useState(reply.child_replies || []);
  const [liked, setLiked] = useState(reply.is_liked || false);
  const [likesCount, setLikesCount] = useState(reply.likes_count || 0);

  // 수정 기능 상태
  const isEditing = activeEditId === replyId;
  const [editText, setEditText] = useState(reply.reply_content || "");
  const [isSubmittingEdit, setIsSubmittingEdit] = useState(false);

  const isOwnReply = currentUser && reply.user?.id === currentUser.id;
  const isAdmin = currentUser && currentUser.permission === 'admin';
  const canDelete = isOwnReply || isAdmin; // 작성자 또는 admin은 삭제 가능
  const maxDepth = 5;

  const handleReplySubmit = async () => {
    if (!replyText.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const response = await createReply(commentId, replyText.trim(), reply.id);
      if (response?.data) {
        const newReply = {
          id: response.data.id,
          reply_content: response.data.reply_content,
          created_at: response.data.created_at,
          user: {
            id: currentUser?.id,
            nickname: currentUser?.nickname,
            display_name: currentUser?.display_name,
            profile_image: currentUser?.profile_image,
          },
          child_replies: [],
          likes_count: 0,
          is_liked: false,
        };
        setChildReplies([...childReplies, newReply]);
        if (onReplyAdd) {
          onReplyAdd(reply.id, newReply);
        }
      }
      setReplyText("");
      if (onClearActive) {
        onClearActive();
      }
    } catch (error) {
      console.error("답글 작성 실패:", error);
      alert("답글 작성에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (window.confirm("답글을 삭제하시겠습니까?")) {
      try {
        await deleteReply(reply.id);
        if (onReplyDelete) {
          onReplyDelete(reply.id);
        }
      } catch (error) {
        console.error("답글 삭제 실패:", error);
        alert("답글 삭제에 실패했습니다.");
      }
    }
  };

  const handleEdit = () => {
    if (onSetActiveEdit) {
      onSetActiveEdit(replyId);
    }
    setEditText(reply.reply_content || "");
  };

  const handleSaveEdit = async () => {
    if (!editText.trim() || isSubmittingEdit) return;

    setIsSubmittingEdit(true);
    try {
      const response = await updateReply(reply.id, editText.trim());
      if (response?.data) {
        // 답글 내용 업데이트
        reply.reply_content = response.data.reply_content;
        if (onClearActive) {
          onClearActive();
        }
      }
    } catch (error) {
      console.error("답글 수정 실패:", error);
      alert("답글 수정에 실패했습니다.");
    } finally {
      setIsSubmittingEdit(false);
    }
  };

  const handleCancelEdit = () => {
    if (onClearActive) {
      onClearActive();
    }
    setEditText(reply.reply_content || "");
  };

  const handleLike = async () => {
    setLiked(!liked);
    setLikesCount(liked ? likesCount - 1 : likesCount + 1);
  };

  const profileSize = 24;
  const hasChildren = childReplies && childReplies.length > 0;
  // 각 depth마다 추가 들여쓰기 (20px씩)
  const indentPerLevel = 20;

  // 콘텐츠 영역 ref로 높이 측정
  const contentRef = useRef(null);
  const [lineHeight, setLineHeight] = useState(28);

  // 세로선 높이 조정 상수 (조정 가능)
  const LINE_HEIGHT_OFFSET = -10; // 자식 컨테이너 여백(4px) + 첫 번째 자식 marginTop(12px) + 프로필 중앙(12px)

  useLayoutEffect(() => {
    if (contentRef.current && hasChildren) {
      // 콘텐츠 높이 + 오프셋
      const height = contentRef.current.offsetHeight + LINE_HEIGHT_OFFSET;
      setLineHeight(height);
    }
  }, [hasChildren, childReplies.length, showReplyInput, replyText]);

  return (
    <div
      style={{
        position: "relative",
        display: "flex",
        marginTop: "12px",
        marginLeft: `${indentPerLevel}px`,
      }}
    >
      {/* 왼쪽: 연결선 + 프로필 + 세로선 */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          width: `${profileSize}px`,
          flexShrink: 0,
          position: "relative",
        }}
      >
        {/* L자 연결선: 부모에서 이 프로필로 */}
        <div
          style={{
            position: "absolute",
            left: `-${indentPerLevel}px`,
            top: "0",
            width: `${indentPerLevel}px`,
            height: `${profileSize / 2}px`,
            borderLeft: "1.5px solid #ccc",
            borderBottom: "1.5px solid #ccc",
            borderBottomLeftRadius: "10px",
          }}
        />

        {/* 프로필 이미지 */}
        <div
          style={{
            width: `${profileSize}px`,
            height: `${profileSize}px`,
            borderRadius: "50%",
            backgroundColor: reply.user?.profile_image
              ? "transparent"
              : COLORS.lightGray,
            backgroundImage: reply.user?.profile_image
              ? `url(${getProfileImageUrl(reply.user.profile_image)})`
              : "none",
            backgroundSize: "cover",
            backgroundPosition: "center",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          {!reply.user?.profile_image && <UserIcon size={12} color={COLORS.gray} />}
        </div>

        {/* 세로선: 자식 답글이 있을 때 프로필 아래로 (동적 높이) */}
        {hasChildren && (
          <div
            style={{
              width: "1.5px",
              height: `${lineHeight}px`,
              backgroundColor: "#ccc",
              marginTop: "2px",
            }}
          />
        )}
      </div>

      {/* 형제가 더 있으면 L자 아래로 세로선 연장 */}
      {hasMoreSiblings && (
        <div
          style={{
            position: "absolute",
            left: `-${indentPerLevel}px`,
            top: `${profileSize / 2}px`,
            width: "1.5px",
            height: `calc(100% - ${profileSize / 2}px + 12px)`,
            backgroundColor: "#ccc",
          }}
        />
      )}

      {/* 오른쪽: 콘텐츠 + 자식 답글들 */}
      <div style={{ flex: 1, marginLeft: "10px", minWidth: 0 }}>
        {/* 콘텐츠 영역 (세로선 높이 측정용) */}
        <div ref={contentRef}>
          {/* 헤더: 닉네임, 시간, 수정/삭제 */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              marginBottom: "4px",
            }}
          >
            <span
              style={{
                fontSize: "12px",
                fontWeight: "600",
                color: COLORS.dark,
              }}
            >
              {reply.user?.display_name ||
                reply.user?.nickname ||
                reply.username ||
                "사용자"}
            </span>
            <span style={{ fontSize: "11px", color: "#999" }}>
              {formatTimeAgo(reply.created_at)}
            </span>
            {!isEditing && (
              <div style={{ marginLeft: "auto", display: "flex", gap: "4px" }}>
                {isOwnReply && (
                  <button
                    onClick={handleEdit}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      padding: "2px",
                      opacity: 0.5,
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.opacity = 1)}
                    onMouseLeave={(e) => (e.currentTarget.style.opacity = 0.5)}
                  >
                    <EditIcon size={10} color="#999" />
                  </button>
                )}
                {canDelete && (
                  <button
                    onClick={handleDelete}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      padding: "2px",
                      opacity: 0.5,
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.opacity = 1)}
                    onMouseLeave={(e) => (e.currentTarget.style.opacity = 0.5)}
                  >
                    <CloseIcon size={10} color="#999" />
                  </button>
                )}
              </div>
            )}
          </div>

          {/* 답글 내용 */}
          {isEditing ? (
            <div style={{ marginBottom: "8px" }}>
              <input
                type="text"
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSaveEdit();
                  } else if (e.key === "Escape") {
                    handleCancelEdit();
                  }
                }}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  border: "2px solid",
                  borderColor: COLORS.primary,
                  borderRadius: "8px",
                  fontSize: "11px",
                  color: COLORS.dark,
                  backgroundColor: COLORS.white,
                  outline: "none",
                  boxSizing: "border-box",
                  boxShadow: `0 0 0 2px ${COLORS.primary}20`,
                }}
                autoFocus
              />
              <div style={{ display: "flex", gap: "6px", marginTop: "8px" }}>
                <button
                  onClick={handleSaveEdit}
                  disabled={!editText.trim() || isSubmittingEdit}
                  style={{
                    padding: "6px 12px",
                    border: "none",
                    borderRadius: "4px",
                    backgroundColor: editText.trim() ? COLORS.primary : COLORS.lightGray,
                    color: COLORS.dark,
                    fontSize: "11px",
                    fontWeight: "600",
                    cursor: editText.trim() ? "pointer" : "not-allowed",
                  }}
                >
                  저장
                </button>
                <button
                  onClick={handleCancelEdit}
                  disabled={isSubmittingEdit}
                  style={{
                    padding: "6px 12px",
                    border: `1px solid ${COLORS.textSecondary}`,
                    borderRadius: "4px",
                    backgroundColor: COLORS.white,
                    color: COLORS.textSecondary,
                    fontSize: "11px",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                >
                  취소
                </button>
              </div>
            </div>
          ) : (
            <div
              style={{
                fontSize: "13px",
                color: COLORS.dark,
                lineHeight: "1.5",
                marginBottom: "6px",
              }}
            >
              {reply.text || reply.reply_content}
            </div>
          )}

          {/* 좋아요 & 답글 버튼 */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "16px",
            }}
          >
            <button
              onClick={handleLike}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: "11px",
                color: liked ? "#e63946" : "#999",
                padding: 0,
              }}
            >
              <HeartIcon size={12} filled={liked} />
              {likesCount > 0 && <span>{likesCount}</span>}
            </button>

            {currentUser && depth < maxDepth && (
              <button
                onClick={() => {
                  if (showReplyInput) {
                    if (onClearActive) {
                      onClearActive();
                    }
                    setReplyText("");
                  } else {
                    if (onSetActiveReply) {
                      onSetActiveReply(replyId);
                    }
                  }
                }}
                style={{
                  background: "none",
                  border: "none",
                  fontSize: "11px",
                  color: "#666",
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                {showReplyInput ? "취소" : "답글"}
              </button>
            )}
          </div>

          {/* 답글 입력 */}
          {showReplyInput && (
            <div
              style={{
                marginTop: "8px",
                display: "flex",
                gap: "8px",
              }}
            >
              <input
                type="text"
                placeholder="답글을 입력하세요"
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleReplySubmit();
                  }
                }}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  border: "1.5px solid #ddd",
                  borderRadius: "20px",
                  fontSize: "12px",
                  backgroundColor: COLORS.white,
                  color: COLORS.dark,
                  outline: "none",
                  transition: "border-color 0.2s ease",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = COLORS.primary;
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "#ddd";
                }}
              />
              <button
                onClick={handleReplySubmit}
                disabled={!replyText.trim() || isSubmitting}
                style={{
                  width: "32px",
                  height: "32px",
                  minWidth: "32px",
                  minHeight: "32px",
                  borderRadius: "50%",
                  backgroundColor: replyText.trim() && !isSubmitting ? COLORS.primary : COLORS.lightGray,
                  border: "none",
                  cursor: replyText.trim() && !isSubmitting ? "pointer" : "not-allowed",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  overflow: "hidden",
                  transition: "all 0.2s ease",
                  padding: 0,
                }}
              >
                <SendIcon
                  size={16}
                  color={replyText.trim() && !isSubmitting ? COLORS.dark : COLORS.textMuted}
                />
              </button>
            </div>
          )}
        </div>

        {/* 자식 답글들 */}
        {hasChildren && (
          <div
            style={{
              marginTop: "4px",
              marginLeft: `-${profileSize + 10}px`,
              paddingLeft: `${profileSize / 2}px`,
            }}
          >
            {childReplies.map((childReply, index) => (
              <ReplyItem
                key={childReply.id}
                reply={childReply}
                currentUser={currentUser}
                commentId={commentId}
                depth={depth + 1}
                onReplyAdd={onReplyAdd}
                onReplyDelete={(deletedId) => {
                  setChildReplies((prev) =>
                    prev.filter((r) => r.id !== deletedId)
                  );
                }}
                hasMoreSiblings={index < childReplies.length - 1}
                activeReplyId={activeReplyId}
                activeEditId={activeEditId}
                onSetActiveReply={onSetActiveReply}
                onSetActiveEdit={onSetActiveEdit}
                onClearActive={onClearActive}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// 메인 댓글 컴포넌트
const Comment = ({
  comment,
  currentUser,
  onDelete,
  onReplyAdd,
  isLast = false,
  activeReplyId,
  activeEditId,
  onSetActiveReply,
  onSetActiveEdit,
  onClearActive,
}) => {
  const commentId = `comment-${comment.id}`;
  const showReplyInput = activeReplyId === commentId;
  const [replyText, setReplyText] = useState("");
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);
  const [replies, setReplies] = useState(comment.replies || []);
  const [liked, setLiked] = useState(comment.is_liked || false);
  const [likesCount, setLikesCount] = useState(
    comment.comment_likes_count || comment.likes_count || 0
  );
  const isEditing = activeEditId === commentId;
  const [editText, setEditText] = useState(comment.comment_content || comment.text || "");
  const [isSubmittingEdit, setIsSubmittingEdit] = useState(false);

  const isOwnComment = currentUser && comment.user?.id === currentUser.id;
  const isAdmin = currentUser && currentUser.permission === 'admin';
  const canDelete = isOwnComment || isAdmin; // 작성자 또는 admin은 삭제 가능
  const profileSize = 32;
  const hasReplies = replies && replies.length > 0;

  // 콘텐츠 영역 ref로 높이 측정
  const commentContentRef = useRef(null);
  const [commentLineHeight, setCommentLineHeight] = useState(28);

  // 세로선 높이 조정 상수 (조정 가능)
  const COMMENT_LINE_HEIGHT_OFFSET = -19; // 자식 컨테이너 여백(4px) + 첫 번째 자식 marginTop(12px) + 프로필 중앙(12px)

  useLayoutEffect(() => {
    if (commentContentRef.current && hasReplies) {
      // 콘텐츠 높이 + 오프셋
      const height =
        commentContentRef.current.offsetHeight + COMMENT_LINE_HEIGHT_OFFSET;
      setCommentLineHeight(height);
    }
  }, [hasReplies, replies.length, showReplyInput, replyText]);

  const handleEdit = () => {
    if (onSetActiveEdit) {
      onSetActiveEdit(commentId);
    }
    setEditText(comment.comment_content || comment.text || "");
  };

  const handleSaveEdit = async () => {
    if (!editText.trim() || isSubmittingEdit) return;

    setIsSubmittingEdit(true);
    try {
      const response = await updateComment(comment.id, editText.trim());
      if (response?.data) {
        // 댓글 내용 업데이트
        comment.comment_content = response.data.comment_content;
        comment.text = response.data.comment_content;
        if (onClearActive) {
          onClearActive();
        }
      }
    } catch (error) {
      console.error("댓글 수정 실패:", error);
      alert("댓글 수정에 실패했습니다.");
    } finally {
      setIsSubmittingEdit(false);
    }
  };

  const handleCancelEdit = () => {
    if (onClearActive) {
      onClearActive();
    }
    setEditText(comment.comment_content || comment.text || "");
  };

  const handleDelete = async () => {
    if (window.confirm("댓글을 삭제하시겠습니까?")) {
      try {
        await deleteComment(comment.id);
        if (onDelete) {
          onDelete(comment.id);
        }
      } catch (error) {
        console.error("댓글 삭제 실패:", error);
        alert("댓글 삭제에 실패했습니다.");
      }
    }
  };

  const handleLike = async () => {
    try {
      if (liked) {
        await unlikeComment(comment.id);
        setLiked(false);
        setLikesCount(likesCount - 1);
      } else {
        await likeComment(comment.id);
        setLiked(true);
        setLikesCount(likesCount + 1);
      }
    } catch (error) {
      console.error("좋아요 처리 실패:", error);
    }
  };

  const handleReplySubmit = async () => {
    if (!replyText.trim() || isSubmittingReply) return;

    setIsSubmittingReply(true);
    try {
      const response = await createReply(comment.id, replyText.trim());
      if (response?.data) {
        const newReply = {
          id: response.data.id,
          reply_content: response.data.reply_content,
          created_at: response.data.created_at,
          user: {
            id: currentUser?.id,
            nickname: currentUser?.nickname,
            display_name: currentUser?.display_name,
            profile_image: currentUser?.profile_image,
          },
          child_replies: [],
          likes_count: 0,
          is_liked: false,
        };
        setReplies([...replies, newReply]);
        if (onReplyAdd) {
          onReplyAdd(comment.id, newReply);
        }
      }
      setReplyText("");
      if (onClearActive) {
        onClearActive();
      }
    } catch (error) {
      console.error("답글 작성 실패:", error);
      alert("답글 작성에 실패했습니다.");
    } finally {
      setIsSubmittingReply(false);
    }
  };

  return (
    <div
      style={{
        padding: "16px 0",
        borderBottom: isLast ? "none" : "1px solid #eee",
      }}
    >
      {/* 댓글 컨테이너 */}
      <div style={{ display: "flex" }}>
        {/* 왼쪽: 프로필 + 세로선 */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            width: `${profileSize}px`,
            flexShrink: 0,
          }}
        >
          {/* 프로필 이미지 */}
          <div
            style={{
              width: `${profileSize}px`,
              height: `${profileSize}px`,
              borderRadius: "50%",
              backgroundColor: comment.user?.profile_image
                ? "transparent"
                : COLORS.lightGray,
              backgroundImage: comment.user?.profile_image
                ? `url(${getProfileImageUrl(comment.user.profile_image)})`
                : "none",
              backgroundSize: "cover",
              backgroundPosition: "center",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            {!comment.user?.profile_image && <UserIcon size={16} color={COLORS.gray} />}
          </div>

          {/* 세로선: 답글이 있을 때 (동적 높이) */}
          {hasReplies && (
            <div
              style={{
                width: "1.5px",
                height: `${commentLineHeight}px`,
                backgroundColor: "#ccc",
                marginTop: "2px",
              }}
            />
          )}
        </div>

        {/* 오른쪽: 콘텐츠 + 답글들 */}
        <div style={{ flex: 1, marginLeft: "10px", minWidth: 0 }}>
          {/* 콘텐츠 영역 (세로선 높이 측정용) */}
          <div ref={commentContentRef}>
            {/* 헤더: 닉네임, 시간, 삭제 */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "6px",
              }}
            >
              <span
                style={{
                  fontSize: "13px",
                  fontWeight: "600",
                  color: COLORS.dark,
                }}
              >
                {comment.user?.display_name ||
                  comment.user?.nickname ||
                  comment.username ||
                  "사용자"}
              </span>
              <span style={{ fontSize: "11px", color: "#999" }}>
                {formatTimeAgo(comment.created_at || comment.timeAgo)}
              </span>
              {!isEditing && (
                <div style={{ marginLeft: "auto", display: "flex", gap: "4px" }}>
                  {isOwnComment && (
                    <button
                      onClick={handleEdit}
                      style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        padding: "4px",
                        opacity: 0.5,
                        transition: "opacity 0.2s",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.opacity = 1)}
                      onMouseLeave={(e) => (e.currentTarget.style.opacity = 0.5)}
                    >
                      <EditIcon size={14} color="#999" />
                    </button>
                  )}
                  {canDelete && (
                    <button
                      onClick={handleDelete}
                      style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        padding: "4px",
                        opacity: 0.5,
                        transition: "opacity 0.2s",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.opacity = 1)}
                      onMouseLeave={(e) => (e.currentTarget.style.opacity = 0.5)}
                    >
                      <CloseIcon size={14} color="#999" />
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* 댓글 내용 */}
            {isEditing ? (
              <div style={{ marginBottom: "8px" }}>
                <input
                  type="text"
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSaveEdit();
                    } else if (e.key === "Escape") {
                      handleCancelEdit();
                    }
                  }}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    border: "2px solid",
                    borderColor: COLORS.primary,
                    borderRadius: "8px",
                    fontSize: "13px",
                    color: COLORS.dark,
                    backgroundColor: COLORS.white,
                    outline: "none",
                    boxSizing: "border-box",
                    boxShadow: `0 0 0 2px ${COLORS.primary}20`,
                  }}
                  autoFocus
                />
                <div
                  style={{
                    display: "flex",
                    gap: "8px",
                    marginTop: "10px",
                  }}
                >
                  <button
                    onClick={handleSaveEdit}
                    disabled={!editText.trim() || isSubmittingEdit}
                    style={{
                      padding: "8px 16px",
                      border: "none",
                      borderRadius: "6px",
                      backgroundColor: editText.trim()
                        ? COLORS.primary
                        : COLORS.lightGray,
                      color: editText.trim() ? COLORS.dark : COLORS.gray,
                      fontSize: "13px",
                      fontWeight: "600",
                      cursor: editText.trim() ? "pointer" : "not-allowed",
                      transition: "all 0.2s ease",
                    }}
                    onMouseEnter={(e) => {
                      if (editText.trim()) {
                        e.currentTarget.style.transform = "scale(1.02)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "scale(1)";
                    }}
                  >
                    저장
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    disabled={isSubmittingEdit}
                    style={{
                      padding: "8px 16px",
                      border: `1.5px solid ${COLORS.textSecondary}`,
                      borderRadius: "6px",
                      backgroundColor: COLORS.white,
                      color: COLORS.textSecondary,
                      fontSize: "13px",
                      fontWeight: "600",
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = COLORS.dark;
                      e.currentTarget.style.color = COLORS.dark;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = COLORS.textSecondary;
                      e.currentTarget.style.color = COLORS.textSecondary;
                    }}
                  >
                    취소
                  </button>
                </div>
              </div>
            ) : (
              <div
                style={{
                  fontSize: "13px",
                  color: COLORS.dark,
                  lineHeight: "1.5",
                  marginBottom: "8px",
                }}
              >
                {comment.text || comment.comment_content}
              </div>
            )}

            {/* 좋아요 & 답글 버튼 */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
              }}
            >
              <button
                onClick={handleLike}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "12px",
                  color: liked ? "#e63946" : "#999",
                  padding: 0,
                }}
              >
                <HeartIcon size={14} filled={liked} />
                {likesCount > 0 && <span>{likesCount}</span>}
              </button>

              {currentUser && (
                <button
                  onClick={() => {
                    if (showReplyInput) {
                      if (onClearActive) {
                        onClearActive();
                      }
                      setReplyText("");
                    } else {
                      if (onSetActiveReply) {
                        onSetActiveReply(commentId);
                      }
                    }
                  }}
                  style={{
                    background: "none",
                    border: "none",
                    fontSize: "12px",
                    color: "#666",
                    cursor: "pointer",
                    padding: 0,
                  }}
                >
                  {showReplyInput ? "취소" : "답글 달기"}
                </button>
              )}
            </div>

            {/* 답글 입력 */}
            {showReplyInput && (
              <div
                style={{
                  marginTop: "10px",
                  display: "flex",
                  gap: "8px",
                }}
              >
                <input
                  type="text"
                  placeholder="답글을 입력하세요"
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleReplySubmit();
                    }
                  }}
                  style={{
                    flex: 1,
                    padding: "10px 40px 10px 14px",
                    border: "1.5px solid #ddd",
                    borderRadius: "20px",
                    fontSize: "13px",
                    backgroundColor: COLORS.white,
                    color: COLORS.dark,
                    outline: "none",
                    transition: "border-color 0.2s ease",
                    boxSizing: "border-box",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = COLORS.primary;
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "#ddd";
                  }}
                />
                <button
                  onClick={handleReplySubmit}
                  disabled={!replyText.trim() || isSubmittingReply}
                  style={{
                    width: "32px",
                    height: "32px",
                    minWidth: "32px",
                    minHeight: "32px",
                    borderRadius: "50%",
                    backgroundColor: replyText.trim() && !isSubmittingReply ? COLORS.primary : COLORS.lightGray,
                    border: "none",
                    cursor: replyText.trim() && !isSubmittingReply ? "pointer" : "not-allowed",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    overflow: "hidden",
                    transition: "all 0.2s ease",
                    padding: 0,
                  }}
                >
                  <SendIcon
                    size={16}
                    color={replyText.trim() && !isSubmittingReply ? COLORS.dark : COLORS.textMuted}
                  />
                </button>
              </div>
            )}
          </div>

          {/* 답글 목록 */}
          {hasReplies && (
            <div
              style={{
                marginTop: "4px",
                marginLeft: `-${profileSize + 10}px`,
                paddingLeft: `${profileSize / 2}px`,
              }}
            >
              {replies.map((reply, index) => (
                <ReplyItem
                  key={reply.id}
                  reply={reply}
                  currentUser={currentUser}
                  commentId={comment.id}
                  depth={1}
                  onReplyAdd={onReplyAdd}
                  onReplyDelete={(deletedId) => {
                    setReplies((prev) =>
                      prev.filter((r) => r.id !== deletedId)
                    );
                  }}
                  hasMoreSiblings={index < replies.length - 1}
                  activeReplyId={activeReplyId}
                  activeEditId={activeEditId}
                  onSetActiveReply={onSetActiveReply}
                  onSetActiveEdit={onSetActiveEdit}
                  onClearActive={onClearActive}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Comment;
