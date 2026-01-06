import { useState, useEffect } from "react";
import { COLORS } from "../../../constants/theme";
import { getWatchingAnalytics } from "../../../api/activityApi";
import { KeyIcon, TagIcon } from "../../../components/common/Icons";

const UserAnalytics = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const response = await getWatchingAnalytics();
        if (response?.data) {
          setAnalytics(response.data);
        }
      } catch (error) {
        console.error("분석 데이터 로딩 실패:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  // 파이 차트 데이터 생성 (video_keywords와 tags 합쳐서 상위 5개)
  const getPieChartData = () => {
    if (!analytics) return [];

    const combined = [];

    // video_keywords를 추가
    analytics.video_keywords.forEach((item) => {
      combined.push({
        label: item.keyword,
        count: item.count,
        type: "keyword",
      });
    });

    // tags를 추가
    analytics.tags.forEach((item) => {
      combined.push({
        label: item.tag,
        count: item.count,
        type: "tag",
      });
    });

    // 빈도수 기준으로 정렬하고 상위 5개만 선택
    combined.sort((a, b) => b.count - a.count);
    return combined.slice(0, 5);
  };

  // 파이 차트 각 조각의 경로 계산
  const calculatePieSlice = (index, total, radius = 40) => {
    const pieData = getPieChartData();
    if (pieData.length === 0) return null;

    const totalCount = pieData.reduce((sum, item) => sum + item.count, 0);
    let currentAngle = -90; // 시작 각도 (12시 방향)

    for (let i = 0; i < index; i++) {
      const sliceAngle = (pieData[i].count / totalCount) * 360;
      currentAngle += sliceAngle;
    }

    const sliceAngle = (pieData[index].count / totalCount) * 360;
    const startAngle = currentAngle;
    const endAngle = currentAngle + sliceAngle;

    // SVG 경로 계산
    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;
    const x1 = 50 + radius * Math.cos(startRad);
    const y1 = 50 + radius * Math.sin(startRad);
    const x2 = 50 + radius * Math.cos(endRad);
    const y2 = 50 + radius * Math.sin(endRad);
    const largeArcFlag = sliceAngle > 180 ? 1 : 0;

    return {
      path: `M 50 50 L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`,
      color: getColorForIndex(index),
    };
  };

  // 색상 팔레트
  // 색상 팔레트 - 차분한 Jade/Warm 톤
  const chartColors = [
    "#7BA697",  // jade
    "#a8c5bb",  // jade-light  
    "#d4e4dd",  // jade-pale
    "#c4a882",  // warm
    "#e8dcc8",  // warm-light
  ];

  const getColorForIndex = (index) => {
    return chartColors[index % chartColors.length];
  };

  if (loading) {
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
              backgroundColor: "var(--jade)",
              borderRadius: "8px",
              color: "var(--black)",
              fontSize: "14px",
              fontWeight: "600",
            }}
          >
            기록 분석
          </div>
        </div>
        <div
          style={{
            backgroundColor: "var(--ink)",
            borderRadius: "12px",
            border: "1px solid var(--line)",
            padding: "20px",
            textAlign: "center",
            color: "var(--gray)",
          }}
        >
          분석 데이터를 불러오는 중...
        </div>
      </div>
    );
  }

  if (
    !analytics ||
    (analytics.total_keywords === 0 && analytics.total_tags === 0)
  ) {
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
              backgroundColor: "var(--jade)",
              borderRadius: "8px",
              color: "var(--black)",
              fontSize: "14px",
              fontWeight: "600",
            }}
          >
            기록 분석
          </div>
        </div>
        <div
          style={{
            backgroundColor: "var(--ink)",
            borderRadius: "12px",
            border: "1px solid var(--line)",
            padding: "20px",
            textAlign: "center",
            color: "var(--gray)",
          }}
        >
          시청 기록이 없습니다.
          <br />
          영상을 시청하면 분석 데이터가 표시됩니다.
        </div>
      </div>
    );
  }

  const pieData = getPieChartData();
  const maxCount =
    pieData.length > 0 ? Math.max(...pieData.map((item) => item.count)) : 1;

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
          기록 분석
        </div>
      </div>
      <div
        style={{
          backgroundColor: "var(--ink)",
          borderRadius: "12px",
          border: "1px solid var(--line)",
          padding: "20px",
        }}
      >
        {/* 통계 요약 */}
        <div
          style={{
            display: "flex",
            gap: "20px",
            marginBottom: "20px",
            paddingBottom: "20px",
            borderBottom: "1px solid var(--line)",
          }}
        >
          <div style={{ flex: 1, textAlign: "center" }}>
            <div
              style={{
                fontSize: "24px",
                fontWeight: "700",
                color: "var(--white)",
              }}
            >
              {analytics.total_videos}
            </div>
            <div
              style={{
                fontSize: "12px",
                color: "var(--gray)",
                marginTop: "4px",
              }}
            >
              시청 영상
            </div>
          </div>
          <div style={{ flex: 1, textAlign: "center" }}>
            <div
              style={{
                fontSize: "24px",
                fontWeight: "700",
                color: "var(--jade)",
              }}
            >
              {analytics.total_keywords}
            </div>
            <div
              style={{
                fontSize: "12px",
                color: "var(--gray)",
                marginTop: "4px",
              }}
            >
              키워드
            </div>
          </div>
          <div style={{ flex: 1, textAlign: "center" }}>
            <div
              style={{ fontSize: "24px", fontWeight: "700", color: "var(--jade-light)" }}
            >
              {analytics.total_tags}
            </div>
            <div
              style={{
                fontSize: "12px",
                color: "var(--gray)",
                marginTop: "4px",
              }}
            >
              태그
            </div>
          </div>
        </div>

        {/* 파이 차트와 바 차트 */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "30px",
            marginTop: "20px",
          }}
        >
          {/* 파이 차트 */}
          <div style={{ flexShrink: 0 }}>
            <svg width="160" height="160" viewBox="0 0 100 100">
              {pieData.length === 0 ? (
                <circle cx="50" cy="50" r="40" fill="#e8e4df" />
              ) : (
                pieData.map((item, index) => {
                  const slice = calculatePieSlice(index, pieData.length);
                  if (!slice) return null;
                  return (
                    <path
                      key={`${item.type}-${item.label}-${index}`}
                      d={slice.path}
                      fill={slice.color}
                      stroke="#fafaf8"
                      strokeWidth="1"
                    />
                  );
                })
              )}
            </svg>
          </div>

          {/* 바 차트 */}
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            {pieData.length === 0 ? (
              <div style={{ color: "var(--gray)", fontSize: "14px" }}>
                데이터가 없습니다.
              </div>
            ) : (
              pieData.map((item, index) => {
                const widthPercent = (item.count / maxCount) * 100;
                const color = getColorForIndex(index);
                const isKeyword = item.type === "keyword";

                return (
                  <div
                    key={`${item.type}-${item.label}-${index}`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                    }}
                  >
                    <div
                      style={{
                        minWidth: "60px",
                        fontSize: "12px",
                        color: "var(--white)",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                    >
                      {isKeyword ? (
                        <KeyIcon size={14} color="var(--jade)" />
                      ) : (
                        <TagIcon size={14} color="var(--jade-light)" />
                      )}
                      <span>{item.label}</span>
                    </div>
                    <div
                      style={{
                        flex: 1,
                        height: "20px",
                        borderRadius: "10px",
                        backgroundColor: color,
                        width: `${widthPercent}%`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "flex-end",
                        paddingRight: "8px",
                        fontSize: "11px",
                        fontWeight: "600",
                        color: "var(--black)",
                      }}
                    >
                      {item.count}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* 키워드와 태그 분리 표시 */}
        {(analytics.video_keywords.length > 0 || analytics.tags.length > 0) && (
          <div
            style={{
            marginTop: "24px",
            paddingTop: "20px",
            borderTop: "1px solid var(--line)",
            }}
          >
            <div
              style={{
                fontSize: "14px",
                fontWeight: "600",
                color: "var(--white)",
                marginBottom: "12px",
              }}
            >
              상세 분석
            </div>

            {/* Video Keywords 섹션 */}
            {analytics.video_keywords.length > 0 && (
              <div style={{ marginBottom: "16px" }}>
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: "600",
                    color: "var(--gray)",
                    marginBottom: "8px",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <KeyIcon size={14} color={COLORS.primary} />
                  <span>키워드 (Video Keywords)</span>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {analytics.video_keywords.slice(0, 5).map((item, idx) => (
                    <div
                      key={`keyword-${idx}`}
                      style={{
                        padding: "4px 10px",
                        backgroundColor: "var(--jade)",
                        color: "var(--black)",
                        borderRadius: "12px",
                        fontSize: "11px",
                        fontWeight: "500",
                      }}
                    >
                      {item.keyword} ({item.count})
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tags 섹션 */}
            {analytics.tags.length > 0 && (
              <div>
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: "600",
                    color: "var(--gray)",
                    marginBottom: "8px",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <TagIcon size={14} color={COLORS.tag} />
                  <span>태그 (Tags)</span>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {analytics.tags.slice(0, 5).map((item, idx) => (
                    <div
                      key={`tag-${idx}`}
                      style={{
                        padding: "4px 10px",
                        backgroundColor: "var(--jade-light)",
                        color: "var(--black)",
                        borderRadius: "12px",
                        fontSize: "11px",
                        fontWeight: "500",
                      }}
                    >
                      {item.tag} ({item.count})
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default UserAnalytics;
