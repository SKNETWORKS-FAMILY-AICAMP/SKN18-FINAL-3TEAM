import { useState } from "react";
import { COLORS } from "../constants/theme";
import {
  UserIcon,
  ArrowLeftIcon,
  PlusIcon,
  LogoIcon,
} from "../components/common/Icons";

const AllCommentsPage = ({ onNavigate }) => {
  const [expandedIds, setExpandedIds] = useState(new Set());

  const allComments = [
    {
      id: 1,
      videoTitle: "정조의 군사 개혁",
      date: "2025.12.10",
      comment: "해당 사건은 몇년도에 발생하였나요?",
      reply: { text: "해당 사건은 1425년(세종 7년)에 발생한 사건입니다." },
      color: COLORS.cardCream,
    },
    {
      id: 2,
      videoTitle: "해시계 앙부일구",
      date: "2025.12.08",
      comment: "앙부일구의 작동 원리가 궁금합니다.",
      reply: {
        text: "앙부일구는 해의 그림자를 이용해 시간을 측정하는 해시계입니다.",
      },
      color: COLORS.sub_color,
    },
    {
      id: 3,
      videoTitle: "수원 화성 축조",
      date: "2025.12.05",
      comment: "화성 축조에 걸린 기간이 얼마나 되나요?",
      reply: null,
      color: COLORS.cardCream,
    },
    {
      id: 4,
      videoTitle: "임진왜란 해전",
      date: "2025.12.01",
      comment: "이순신 장군의 전략이 정말 대단하네요!",
      reply: null,
      color: COLORS.sky,
    },
    {
      id: 5,
      videoTitle: "집현전의 학자들",
      date: "2025.11.28",
      comment: "집현전에서 가장 유명한 학자는 누구인가요?",
      reply: {
        text: "정인지, 성삼문, 신숙주 등이 대표적인 집현전 학자입니다.",
      },
      color: COLORS.sub_color,
    },
  ];

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
            {allComments.length}개
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {allComments.map((item, idx) => {
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
                  >
                    <div
                      style={{
                        backgroundColor: "rgba(255,255,255,0.5)",
                        borderRadius: "12px",
                        padding: "16px 20px",
                        marginBottom: item.reply ? "12px" : 0,
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
                          <UserIcon size={14} color={COLORS.textPrimary} />
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
                      </div>
                      <p
                        style={{
                          fontSize: "15px",
                          color: COLORS.textPrimary,
                          margin: 0,
                          lineHeight: "1.5",
                        }}
                      >
                        {item.comment}
                      </p>
                    </div>

                    {item.reply && (
                      <div
                        style={{ position: "relative", paddingLeft: "24px" }}
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
                              <LogoIcon size={14} />
                            </div>
                            <span
                              style={{
                                fontSize: "13px",
                                fontWeight: "700",
                                color: COLORS.textPrimary,
                              }}
                            >
                              AI 답변
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
                            {item.reply.text}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
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
