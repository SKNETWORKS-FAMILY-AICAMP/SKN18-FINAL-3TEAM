import { useState, useEffect } from "react";
import UserProfile from "../features/user/components/UserProfile";
import WatchHistory from "../features/user/components/WatchHistory";
import UserComments from "../features/user/components/UserComments";
import UserAnalytics from "../features/user/components/UserAnalytics";
import { getWatchHistory } from "../api/activityApi";
import { getMyActivity } from "../api/communityApi";

const MyPage = ({ onNavigate, user }) => {
  const [watchHistory, setWatchHistory] = useState([]);
  const [userComments, setUserComments] = useState([]);
  const [loading, setLoading] = useState(true);

  // 페이지 로드 시 스크롤을 맨 위로 이동
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);

        // 시청 기록 가져오기
        const watchResponse = await getWatchHistory();
        if (watchResponse?.data) {
          setWatchHistory(
            watchResponse.data.map((w) => ({
              id: w.id,
              title: w.video_title || "제목 없음",
              videoId: w.video,
            }))
          );
        }

        // 내 댓글 가져오기
        const activityResponse = await getMyActivity();
        if (activityResponse?.data?.comments) {
          console.log("댓글 데이터:", activityResponse.data.comments);
          setUserComments(
            activityResponse.data.comments.map((c) => ({
              id: c.id,
              text: c.comment_content,
              videoTitle: c.video_title || c.video?.title || "영상",
              createdAt: c.created_at,
            }))
          );
        }
      } catch (error) {
        console.error("마이페이지 데이터 로딩 실패:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <div
      style={{
        display: "flex",
        gap: "40px",
        padding: "60px 60px 40px 60px",
        minHeight: "calc(100vh - 76px)",
      }}
    >
      <UserProfile onEdit={() => onNavigate("profile-edit")} user={user} />

      <div style={{ flex: 1 }}>
        <WatchHistory items={watchHistory} loading={loading} />

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "40px",
            marginTop: "40px",
          }}
        >
          <UserComments
            comments={userComments}
            loading={loading}
            onViewAll={() => onNavigate("all-comments")}
          />
          <UserAnalytics />
        </div>
      </div>
    </div>
  );
};

export default MyPage;
