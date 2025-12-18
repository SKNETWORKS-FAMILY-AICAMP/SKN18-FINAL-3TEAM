import { useState, useEffect } from "react";
import { COLORS } from "../constants/theme";
import VideoGrid from "../features/video/components/VideoGrid";
import { getVideos, getPopularVideos } from "../api/videoApi";

const MainPage = ({ isLoggedIn, onVideoClick }) => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        setLoading(true);
        // 로그인 사용자는 추천 영상, 비로그인은 인기 영상
        const response = isLoggedIn
          ? await getVideos("latest")
          : await getVideos(); //비로그인은 인기 영상이 되어야 하므로 나중에 getPopularVideos()로 변경


        if (response?.data) {
          // 백엔드 데이터를 프론트엔드 형식으로 변환
          const formattedVideos = response.data.map((video) => ({
            id: video.id,
            title: video.title,
            tags: video.tags ? video.tags.map((t) => `#${t}`).join(" ") : "",
            likes_count: video.likes_count,
            comments_count: video.comments_count,
          }));
          setVideos(formattedVideos);
        }
      } catch (error) {
        console.error("영상 목록 로딩 실패:", error);
        // API 실패시 빈 배열 유지
        setVideos([]);
      } finally {
        setLoading(false);
      }
    };

    fetchVideos();
  }, [isLoggedIn]);

  return (
    <main
      style={{
        padding: "80px 60px 40px 60px",
        backgroundColor: COLORS.background,
        minHeight: "100vh",
        width: "100%",
        margin: 0,
        boxSizing: "border-box",
        overflowX: "hidden",
      }}
    >
      <div
        style={{
          marginBottom: "40px",
        }}
      >
        <h1
          style={{
            fontFamily: "'Space Mono', monospace",
            fontSize: "clamp(48px, 8vw, 120px)",
            fontWeight: "700",
            color: "#effd9a",
            margin: 0,
            lineHeight: "1.1",
            letterSpacing: "-0.01em",
            transform: "scaleX(1.03)",
            transformOrigin: "left",
          }}
        >
          {isLoggedIn ? "RECOMMEND" : "POPULAR"}
        </h1>
      </div>

      {loading ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px",
            color: COLORS.dark,
          }}
        >
          로딩 중...
        </div>
      ) : videos.length > 0 ? (
        <VideoGrid videos={videos} onVideoClick={onVideoClick} />
      ) : (
        <div
          style={{
            textAlign: "center",
            padding: "60px",
            color: COLORS.dark,
          }}
        >
          영상이 없습니다.
        </div>
      )}
    </main>
  );
};

export default MainPage;
