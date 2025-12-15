import { COLORS } from "../../../constants/theme";

const UserComments = ({ onViewAll }) => {
  const comments = [
    {
      id: 1,
      title: "영상 제목",
      question: "해당 사건은 몇년도에 발생하였나요?",
      answer:
        "안녕하세요 사용자님!\n해당 사건은 1425년(세종 7년)에 발생한 사건입니다.",
    },
    {
      id: 2,
      title: "다른 영상",
      question: "흥미로운 내용이네요!",
      answer: null,
    },
    {
      id: 3,
      title: "임진왜란 해전",
      question: "이순신 장군의 전략이 정말 대단해요!",
      answer: null,
    },
    {
      id: 4,
      title: "수원 화성 축조",
      question: "화성 축조 기간이 궁금합니다.",
      answer:
        "수원 화성은 1794년부터 1796년까지 약 2년 반에 걸쳐 축조되었습니다.",
    },
  ];

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
            border: "1px solid #333",
            borderRadius: "6px",
            backgroundColor: "transparent",
            fontSize: "13px",
            cursor: "pointer",
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
          scrollbarColor: `${COLORS.primary} ${COLORS.lightGray}`,
        }}
        className="user-comments-scroll"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {comments.map((comment) => (
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
          ))}
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
            background: ${COLORS.primary};
            border-radius: 4px;
          }
          .user-comments-scroll::-webkit-scrollbar-thumb:hover {
            background: ${COLORS.secondary};
          }
        `}</style>
      </div>
    </div>
  );
};

export default UserComments;
