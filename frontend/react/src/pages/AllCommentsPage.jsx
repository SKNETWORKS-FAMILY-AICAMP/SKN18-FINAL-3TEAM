import { useState, useEffect } from "react";
import { COLORS } from "../constants/theme";
import {
  UserIcon,
  ArrowLeftIcon,
  PlusIcon,
  LogoIcon,
} from "../components/common/Icons";
import { getMyActivity } from "../api/communityApi";

const AllCommentsPage = ({ onNavigate }) => {
  const [expandedIds, setExpandedIds] = useState(new Set());
  const [allComments, setAllComments] = useState([]);
  const [loading, setLoading] = useState(true);

  // 배경색 배열 (순환)
  const colors = [COLORS.cardCream, COLORS.sub_color, COLORS.sky];

  // 시간 포맷팅 함수
  const formatTimeAgo = (dateString) => {
    if (!dateString) return "";
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return "";

      const now = new Date();
      const diffMs = now - date;
      const diffSec = Math.floor(diffMs / 1000);
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffSec < 60) return "방금 전";
      if (diffMins < 60) return `${diffMins}분 전`;
      if (diffHours < 24) return `${diffHours}시간 전`;
      if (diffDays < 7) return `${diffDays}일 전`;
      return date
        .toLocaleDateString("ko-KR", {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
        })
        .replace(/\. /g, ".")
        .replace(".", "");
    } catch (error) {
      console.error("날짜 포맷 오류:", error, dateString);
      return "";
    }
  };

  useEffect(() => {
    const fetchComments = async () => {
      try {
        setLoading(true);
        const response = await getMyActivity();
        if (response?.data?.comments) {
          // 같은 영상의 댓글을 그룹화
          const groupedByVideo = {};

          response.data.comments.forEach((c, idx) => {
            const videoId = c.video?.id || c.video || "unknown";
            const videoTitle = c.video_title || c.video?.title || "영상";

            if (!groupedByVideo[videoId]) {
              groupedByVideo[videoId] = {
                videoId,
                videoTitle,
                comments: [],
                color:
                  colors[Object.keys(groupedByVideo).length % colors.length],
              };
            }

            groupedByVideo[videoId].comments.push({
              id: c.id,
              comment_content: c.comment_content,
              created_at: c.created_at,
              replies: c.replies || [], // 백엔드에서 받은 replies
              date: formatTimeAgo(c.created_at),
            });
          });

          // 그룹화된 데이터를 배열로 변환
          const formattedComments = Object.values(groupedByVideo).map(
            (group, idx) => ({
              id: `video-${group.videoId}`, // 그룹 ID
              videoId: group.videoId,
              videoTitle: group.videoTitle,
              color: group.color,
              comments: group.comments, // 같은 영상의 모든 댓글
              date: group.comments[0]?.date || "", // 가장 최근 댓글의 날짜
            })
          );

          setAllComments(formattedComments);
        }
      } catch (error) {
        console.error("댓글 로드 실패:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchComments();
  }, []);

  const toggleExpand = (id) => {
    setExpandedIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  return (
    <div style={{ padding: "60px 60px", minHeight: "calc(100vh - 76px)" }}>
      <button
        onClick={() => onNavigate("mypage")}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: "14px",
          color: COLORS.textSecondary,
          marginBottom: "40px",
        }}
      >
        <ArrowLeftIcon size={18} color={COLORS.textSecondary} />
        마이페이지로 돌아가기
      </button>

      <div style={{ maxWidth: "900px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "20px",
            marginBottom: "40px",
          }}
        >
          <h1
            style={{
              fontSize: "32px",
              fontWeight: "800",
              color: COLORS.textPrimary,
            }}
          >
            내가 남긴 댓글
          </h1>
          <span
            style={{
              padding: "8px 18px",
              borderRadius: "25px",
              backgroundColor: COLORS.primary,
              fontSize: "15px",
              fontWeight: "700",
              color: COLORS.textPrimary,
            }}
          >
            {allComments.reduce(
              (sum, group) => sum + (group.comments?.length || 0),
              0
            )}
            개
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {loading ? (
            <div
              style={{
                textAlign: "center",
                padding: "40px",
                color: COLORS.gray,
              }}
            >
              로딩 중...
            </div>
          ) : allComments.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "40px",
                color: COLORS.gray,
              }}
            >
              작성한 댓글이 없습니다.
            </div>
          ) : (
            allComments.map((item, idx) => {
              const isExpanded = expandedIds.has(item.id);
              return (
                <div
                  key={item.id}
                  style={{
                    backgroundColor: item.color,
                    borderRadius: "12px",
                    padding: isExpanded ? "20px 24px" : "16px 24px",
                    cursor: "pointer",
                    transition: "all 0.3s ease",
                    animation: `fadeIn 0.4s ease ${idx * 0.05}s both`,
                  }}
                  onClick={() => toggleExpand(item.id)}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.transform = "translateX(4px)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.transform = "translateX(0)")
                  }
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          width: "24px",
                          height: "24px",
                          transition: "transform 0.3s ease",
                          transform: isExpanded
                            ? "rotate(45deg)"
                            : "rotate(0deg)",
                        }}
                      >
                        <PlusIcon size={20} color={COLORS.dark} />
                      </div>
                      <span
                        style={{
                          fontSize: "16px",
                          fontWeight: "600",
                          color: COLORS.dark,
                        }}
                      >
                        {item.videoTitle}
                      </span>
                    </div>
                    <span
                      style={{
                        fontSize: "13px",
                        color: COLORS.textMuted,
                        fontWeight: "500",
                      }}
                    >
                      {item.date}
                    </span>
                  </div>

                  {isExpanded && (
                    <div
                      style={{
                        marginTop: "20px",
                        paddingTop: "20px",
                        borderTop: "1px solid rgba(0, 0, 0, 0.1)",
                        animation: "slideDown 0.3s ease",
                      }}
                      onClick={(e) => e.stopPropagation()} // 확장 영역 클릭 시 닫히지 않도록
                    >
                      {/* 같은 영상의 모든 댓글 표시 */}
                      {item.comments?.map((comment, commentIdx) => (
                        <div
                          key={comment.id}
                          style={{
                            marginBottom:
                              commentIdx < item.comments.length - 1
                                ? "16px"
                                : "0",
                          }}
                        >
                          {/* 댓글 */}
                          <div
                            style={{
                              backgroundColor: "rgba(255,255,255,0.5)",
                              borderRadius: "12px",
                              padding: "16px 20px",
                              marginBottom:
                                comment.replies?.length > 0 ? "12px" : "0",
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "10px",
                                marginBottom: "8px",
                              }}
                            >
                              <div
                                style={{
                                  width: "26px",
                                  height: "26px",
                                  borderRadius: "50%",
                                  backgroundColor: COLORS.primary,
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                }}
                              >
                                <UserIcon
                                  size={14}
                                  color={COLORS.textPrimary}
                                />
                              </div>
                              <span
                                style={{
                                  fontSize: "13px",
                                  fontWeight: "700",
                                  color: COLORS.textPrimary,
                                }}
                              >
                                나
                              </span>
                              <span
                                style={{
                                  fontSize: "11px",
                                  color: COLORS.textMuted,
                                  marginLeft: "8px",
                                }}
                              >
                                {comment.date}
                              </span>
                            </div>
                            <p
                              style={{
                                fontSize: "15px",
                                color: COLORS.textPrimary,
                                margin: 0,
                                lineHeight: "1.5",
                              }}
                            >
                              {comment.comment_content}
                            </p>
                          </div>

                          {/* 하위 댓글들 (재귀적 렌더링) */}
                          {comment.replies && comment.replies.length > 0 && (
                            <div style={{ marginLeft: "20px" }}>
                              {comment.replies.map((reply, replyIdx) => (
                                <div
                                  key={reply.id}
                                  style={{
                                    position: "relative",
                                    paddingLeft: "24px",
                                    marginBottom:
                                      replyIdx < comment.replies.length - 1
                                        ? "12px"
                                        : "0",
                                  }}
                                >
                                  <div
                                    style={{
                                      position: "absolute",
                                      left: "10px",
                                      top: "-8px",
                                      width: "14px",
                                      height: "28px",
                                      borderLeft: `2px solid ${COLORS.border}`,
                                      borderBottom: `2px solid ${COLORS.border}`,
                                      borderBottomLeftRadius: "12px",
                                    }}
                                  />
                                  <div
                                    style={{
                                      backgroundColor: "rgba(255,255,255,0.7)",
                                      borderRadius: "12px",
                                      padding: "16px 20px",
                                    }}
                                  >
                                    <div
                                      style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: "10px",
                                        marginBottom: "8px",
                                      }}
                                    >
                                      <div
                                        style={{
                                          width: "26px",
                                          height: "26px",
                                          borderRadius: "50%",
                                          backgroundColor: COLORS.cardSky,
                                          display: "flex",
                                          alignItems: "center",
                                          justifyContent: "center",
                                        }}
                                      >
                                        <UserIcon
                                          size={12}
                                          color={COLORS.textPrimary}
                                        />
                                      </div>
                                      <span
                                        style={{
                                          fontSize: "13px",
                                          fontWeight: "700",
                                          color: COLORS.textPrimary,
                                        }}
                                      >
                                        {reply.user?.display_name ||
                                          reply.user?.nickname ||
                                          "사용자"}
                                      </span>
                                      <span
                                        style={{
                                          fontSize: "11px",
                                          color: COLORS.textMuted,
                                          marginLeft: "8px",
                                        }}
                                      >
                                        {formatTimeAgo(reply.created_at)}
                                      </span>
                                    </div>
                                    <p
                                      style={{
                                        fontSize: "15px",
                                        color: COLORS.textPrimary,
                                        margin: 0,
                                        lineHeight: "1.5",
                                      }}
                                    >
                                      {reply.reply_content || reply.text}
                                    </p>

                                    {/* 답글의 답글들 (재귀) */}
                                    {reply.child_replies &&
                                      reply.child_replies.length > 0 && (
                                        <div
                                          style={{
                                            marginTop: "12px",
                                            marginLeft: "20px",
                                          }}
                                        >
                                          {reply.child_replies.map(
                                            (childReply) => (
                                              <div
                                                key={childReply.id}
                                                style={{
                                                  position: "relative",
                                                  paddingLeft: "20px",
                                                  marginBottom: "8px",
                                                }}
                                              >
                                                <div
                                                  style={{
                                                    position: "absolute",
                                                    left: "8px",
                                                    top: "-6px",
                                                    width: "12px",
                                                    height: "24px",
                                                    borderLeft: `2px solid ${COLORS.border}`,
                                                    borderBottom: `2px solid ${COLORS.border}`,
                                                    borderBottomLeftRadius:
                                                      "10px",
                                                  }}
                                                />
                                                <div
                                                  style={{
                                                    backgroundColor:
                                                      "rgba(255,255,255,0.8)",
                                                    borderRadius: "10px",
                                                    padding: "12px 16px",
                                                  }}
                                                >
                                                  <div
                                                    style={{
                                                      display: "flex",
                                                      alignItems: "center",
                                                      gap: "8px",
                                                      marginBottom: "6px",
                                                    }}
                                                  >
                                                    <div
                                                      style={{
                                                        width: "20px",
                                                        height: "20px",
                                                        borderRadius: "50%",
                                                        backgroundColor:
                                                          COLORS.lightGray,
                                                        display: "flex",
                                                        alignItems: "center",
                                                        justifyContent:
                                                          "center",
                                                      }}
                                                    >
                                                      <UserIcon
                                                        size={10}
                                                        color={
                                                          COLORS.textPrimary
                                                        }
                                                      />
                                                    </div>
                                                    <span
                                                      style={{
                                                        fontSize: "12px",
                                                        fontWeight: "600",
                                                        color:
                                                          COLORS.textPrimary,
                                                      }}
                                                    >
                                                      {childReply.user
                                                        ?.display_name ||
                                                        childReply.user
                                                          ?.nickname ||
                                                        "사용자"}
                                                    </span>
                                                    <span
                                                      style={{
                                                        fontSize: "10px",
                                                        color: COLORS.textMuted,
                                                      }}
                                                    >
                                                      {formatTimeAgo(
                                                        childReply.created_at
                                                      )}
                                                    </span>
                                                  </div>
                                                  <p
                                                    style={{
                                                      fontSize: "14px",
                                                      color: COLORS.textPrimary,
                                                      margin: 0,
                                                      lineHeight: "1.5",
                                                    }}
                                                  >
                                                    {childReply.reply_content ||
                                                      childReply.text}
                                                  </p>
                                                </div>
                                              </div>
                                            )
                                          )}
                                        </div>
                                      )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(15px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideDown {
          from { opacity: 0; max-height: 0; transform: translateY(-10px); }
          to { opacity: 1; max-height: 500px; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default AllCommentsPage;
