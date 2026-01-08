import { useState, useEffect } from "react";
import { getWatchHistory } from "../api/activityApi";
import { getMyActivity } from "../api/communityApi";
import { getProfileImageUrl } from "../utils/imageUtils";
import UserAnalytics from "../features/user/components/UserAnalytics";
import "../styles/histok.css";

const MyPage = ({ onNavigate, user }) => {
  const [watchHistory, setWatchHistory] = useState([]);
  const [userComments, setUserComments] = useState([]);
  const [analytics, setAnalytics] = useState({
    watchedCount: 0,
    commentsCount: 0,
    interestTopic: "궁중",
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);

        const watchResponse = await getWatchHistory();
        if (watchResponse?.data) {
          const uniqueVideos = new Map();
          watchResponse.data.forEach((w) => {
            if (!uniqueVideos.has(w.video)) {
              uniqueVideos.set(w.video, {
                id: w.id,
                title: w.video_title || "제목 없음",
                videoId: w.video,
                thumbnail_url: w.video_thumbnail || null,
              });
            }
          });
          const history = Array.from(uniqueVideos.values());
          setWatchHistory(history);
          setAnalytics((prev) => ({ ...prev, watchedCount: history.length }));
        }

        const activityResponse = await getMyActivity();
        if (activityResponse?.data?.comments) {
          const comments = activityResponse.data.comments.map((c) => ({
            id: c.id,
            text: c.comment_content,
            videoTitle: c.video_title || c.video?.title || "영상",
            createdAt: c.created_at,
            replies: c.replies || [],
            repliesCount: c.replies?.length || 0,
            user: c.user || null,
          }));
          setUserComments(comments);
          setAnalytics((prev) => ({ ...prev, commentsCount: comments.length }));
        }
      } catch (error) {
        console.error("마이페이지 데이터 로딩 실패:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const formatDate = (dateString) => {
    if (!dateString) return "";
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      });
    } catch (error) {
      return "";
    }
  };

  return (
    <div className="page active">
      <div className="mypage">
        <div className="mypage-header">
          <h1 className="mypage-title">나의 공간</h1>
          <p className="mypage-subtitle">My Space</p>
        </div>
        <div className="mypage-grid">
          <div className="profile-card">
            <div className="profile-avatar">
              {user?.profile_image ? (
                <img
                  src={getProfileImageUrl(user.profile_image)}
                  alt="Profile"
                  style={{
                    width: "100%",
                    height: "100%",
                    borderRadius: "50%",
                    objectFit: "cover",
                  }}
                />
              ) : (
                (
                  user?.nickname ||
                  user?.display_name ||
                  user?.email?.charAt(0) ||
                  "김"
                ).charAt(0)
              )}
            </div>
            <h2 className="profile-name">
              {user?.nickname || user?.display_name || "사용자"}
            </h2>
            <p className="profile-email">
              {user?.email || "email@example.com"}
            </p>
            <button
              className="profile-edit-btn"
              onClick={() => onNavigate("profile-edit")}
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              프로필 수정
            </button>
          </div>
          <div className="mypage-content">
            <section className="mypage-section">
              <div className="mypage-section-header">
                <h3 className="mypage-section-title">본 이야기</h3>
                <span
                  className="mypage-section-more"
                  onClick={() => onNavigate("all-watch-history")}
                >
                  전체보기 →
                </span>
              </div>
              {loading ? (
                <div
                  style={{
                    padding: "20px",
                    textAlign: "center",
                    color: "#888",
                  }}
                >
                  로딩 중...
                </div>
              ) : watchHistory.length > 0 ? (
                <div className="watch-history-scroll">
                  {watchHistory.slice(0, 5).map((item) => (
                    <div
                      key={item.id}
                      className="watch-history-item"
                      onClick={() => onNavigate("video", item.videoId)}
                    >
                      <div
                        className="watch-history-thumb"
                        style={{
                          backgroundImage: item.thumbnail_url
                            ? `url(${getProfileImageUrl(item.thumbnail_url)})`
                            : "none",
                          backgroundColor: item.thumbnail_url
                            ? "transparent"
                            : "var(--jade-pale)",
                        }}
                      />
                      <div className="watch-history-title">{item.title}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div
                  style={{
                    padding: "20px",
                    textAlign: "center",
                    color: "#888",
                  }}
                >
                  본 이야기가 없습니다.
                </div>
              )}
            </section>
            <section className="mypage-section">
              <div className="mypage-section-header">
                <h3 className="mypage-section-title">남긴 이야기</h3>
                <span
                  className="mypage-section-more"
                  onClick={() => onNavigate("all-comments")}
                >
                  전체보기 →
                </span>
              </div>
              {loading ? (
                <div
                  style={{
                    padding: "20px",
                    textAlign: "center",
                    color: "#888",
                  }}
                >
                  로딩 중...
                </div>
              ) : userComments.length > 0 ? (
                <div className="my-comments-list">
                  {userComments.slice(0, 5).map((comment) => (
                    <div key={comment.id} className="my-comment-item">
                      <div className="my-comment-video">
                        {comment.videoTitle}
                      </div>
                      <p className="my-comment-text">{comment.text}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div
                  style={{
                    padding: "20px",
                    textAlign: "center",
                    color: "#888",
                  }}
                >
                  남긴 이야기가 없습니다.
                </div>
              )}
            </section>
            <section className="mypage-section">
              <div className="mypage-section-header">
                <h3 className="mypage-section-title">취향 분석</h3>
              </div>
              <UserAnalytics />
            </section>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MyPage;
