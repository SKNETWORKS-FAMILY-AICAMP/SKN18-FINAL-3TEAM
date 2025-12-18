import { COLORS } from "../../../constants/theme";

const UserComments = ({
  comments: commentsProp = [],
  loading = false,
  onViewAll,
}) => {
  // API에서 가져온 댓글을 화면에 맞는 형식으로 변환
  const comments = commentsProp.map((c) => ({
    id: c.id,
    title: c.videoTitle || "영상",
    question: c.text,
    answer: null, // 답글은 별도로 로드해야 함
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
                <div style={{ marginLeft: "12px" }}>
                  <div
                    style={{
                      fontSize: "13px",
                      color: COLORS.gray,
                      position: "relative",
                      paddingLeft: "16px",
                      marginBottom: comment.answer ? "8px" : "0",
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        left: "0",
                        top: "0",
                        width: "10px",
                        height: "100%",
                        borderLeft: "1.5px solid #ccc",
                        borderBottom: "1.5px solid #ccc",
                        borderBottomLeftRadius: "8px",
                      }}
                    ></div>
                    {comment.question}
                  </div>
                  {comment.answer && (
                    <div
                      style={{
                        fontSize: "13px",
                        color: COLORS.gray,
                        position: "relative",
                        paddingLeft: "16px",
                        marginLeft: "16px",
                        whiteSpace: "pre-line",
                      }}
                    >
                      <div
                        style={{
                          position: "absolute",
                          left: "0",
                          top: "0",
                          width: "10px",
                          height: "100%",
                          borderLeft: "1.5px solid #ccc",
                          borderBottom: "1.5px solid #ccc",
                          borderBottomLeftRadius: "8px",
                        }}
                      ></div>
                      {comment.answer}
                    </div>
                  )}
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
