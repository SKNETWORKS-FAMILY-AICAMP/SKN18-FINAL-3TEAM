import { COLORS } from "../../../constants/theme";
import { UserIcon } from "../../../components/common/Icons";
import { getProfileImageUrl } from "../../../utils/imageUtils";

const UserComments = ({
  comments: commentsProp = [],
  loading = false,
  onViewAll,
}) => {
  // API에서 가져온 댓글을 화면에 맞는 형식으로 변환
  const comments = commentsProp.map((c) => ({
    id: c.id,
    title: c.videoTitle || "영상",
    text: c.text || c.comment_content,
    repliesCount: c.repliesCount || (c.replies?.length || 0),
    user: c.user || null,
  }));

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "20px",
        }}
      >
        <div
          style={{
            display: "inline-block",
            padding: "10px 20px",
            backgroundColor: COLORS.gray,
            borderRadius: "8px",
            color: COLORS.white,
            fontSize: "14px",
            fontWeight: "600",
          }}
        >
          내가 남긴 댓글
        </div>
        <button
          onClick={onViewAll}
          style={{
            padding: "8px 16px",
            border: `1.5px solid ${COLORS.textSecondary}`,
            borderRadius: "6px",
            backgroundColor: "transparent",
            color: COLORS.textSecondary,
            fontSize: "13px",
            fontWeight: "500",
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
          전체보기
        </button>
      </div>
      <div
        style={{
          backgroundColor: COLORS.white,
          borderRadius: "12px",
          border: "1px solid #eee",
          padding: "20px",
          maxHeight: "400px",
          overflowY: "auto",
          scrollbarWidth: "thin",
          scrollbarColor: `${COLORS.lightGray} transparent`,
        }}
        className="user-comments-scroll"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {loading ? (
            <div
              style={{
                fontSize: "13px",
                color: COLORS.gray,
                padding: "20px",
                textAlign: "center",
              }}
            >
              로딩 중...
            </div>
          ) : comments.length === 0 ? (
            <div
              style={{
                fontSize: "13px",
                color: COLORS.gray,
                padding: "20px",
                textAlign: "center",
              }}
            >
              작성한 댓글이 없습니다.
            </div>
          ) : (
            comments.map((comment) => (
              <div
                key={comment.id}
                style={{
                  padding: "16px 0",
                  borderBottom: "1px solid #eee",
                }}
              >
                <div
                  style={{
                    fontSize: "14px",
                    fontWeight: "600",
                    marginBottom: "10px",
                  }}
                >
                  {comment.title}
                </div>
                <div style={{ display: "flex", gap: "12px" }}>
                  {/* 프로필 사진 */}
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
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
                    {!comment.user?.profile_image && (
                      <UserIcon size={16} color={COLORS.gray} />
                    )}
                  </div>
                  {/* 댓글 내용 */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: "13px",
                        color: COLORS.dark,
                        lineHeight: "1.6",
                        wordWrap: "break-word",
                        marginBottom: "6px",
                      }}
                    >
                      {comment.text}
                    </div>
                    {/* 답글 개수 표시 */}
                    {comment.repliesCount > 0 && (
                      <div
                        style={{
                          fontSize: "12px",
                          color: COLORS.gray,
                          marginTop: "4px",
                        }}
                      >
                        답글 {comment.repliesCount}개
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        <style>{`
          .user-comments-scroll::-webkit-scrollbar {
            width: 8px;
          }
          .user-comments-scroll::-webkit-scrollbar-track {
            background: ${COLORS.lightGray};
            border-radius: 4px;
          }
          .user-comments-scroll::-webkit-scrollbar-thumb {
            background: ${COLORS.lightGray};
            border-radius: 4px;
          }
          .user-comments-scroll::-webkit-scrollbar-thumb:hover {
            background: ${COLORS.gray};
          }
        `}</style>
      </div>
    </div>
  );
};

export default UserComments;
