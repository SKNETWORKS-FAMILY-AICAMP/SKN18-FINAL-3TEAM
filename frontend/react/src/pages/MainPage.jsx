import { useState, useEffect } from "react";
import { COLORS } from "../constants/theme";
import VideoGrid from "../features/video/components/VideoGrid";
import { getVideos, getPopularVideos } from "../api/videoApi";
import { getRecommendedVideos } from "../api/activityApi";
import IntroVideo from "../components/intro/IntroVideo";

const MainPage = ({ isLoggedIn, onVideoClick }) => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  // 로그인 회원: 'accuracy', 'latest'
  // 비회원: 'popular', 'latest'
  const [filter, setFilter] = useState(isLoggedIn ? "accuracy" : "popular");

  // 로그인 상태가 변경되면 필터 초기화
  useEffect(() => {
    setFilter(isLoggedIn ? "accuracy" : "popular");
  }, [isLoggedIn]);

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        setLoading(true);
        let response;

        if (isLoggedIn) {
          // 로그인 회원: 정확도순 또는 최신순
          if (filter === "accuracy") {
            response = await getRecommendedVideos("accuracy");
            // 정확도순이 빈 값이면 인기 영상으로 폴백
            if (response?.data && response.data.length === 0) {
              console.log("정확도순 결과가 없어 인기 영상으로 대체합니다.");
              response = await getPopularVideos();
            }
          } else {
            response = await getVideos("latest");
          }
        } else {
          // 비회원: 인기 영상 또는 최신순
          response = filter === "popular"
            ? await getPopularVideos()
            : await getVideos("latest");
        }

        if (response?.data) {
          // 백엔드 데이터를 프론트엔드 형식으로 변환
          const formattedVideos = response.data.map((video) => ({
            id: video.id,
            title: video.title,
            tags: video.tags || [],
            video_keyword: video.video_keyword || null,
            likes_count: video.likes_count,
            comments_count: video.comments_count,
            thumbnail_url: video.thumbnail_url,
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
  }, [isLoggedIn, filter]);

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
      {/* 새로 추가한 인트로 비디오 로직 */}
      <IntroVideo />

      {/* 타이틀과 필터 라디오 버튼 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
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

        {/* 토글 버튼 필터 */}
        <div
          style={{
            display: "flex",
            backgroundColor: COLORS.lightGray || "#f0f0f0",
            borderRadius: "24px",
            padding: "4px",
          }}
        >
          {isLoggedIn ? (
            <>
              <button
                onClick={() => setFilter("accuracy")}
                style={{
                  padding: "8px 20px",
                  borderRadius: "20px",
                  border: "none",
                  backgroundColor: filter === "accuracy" ? COLORS.primary : "transparent",
                  color: filter === "accuracy" ? COLORS.dark : COLORS.gray,
                  fontWeight: filter === "accuracy" ? "700" : "500",
                  fontSize: "14px",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                정확도순
              </button>
              <button
                onClick={() => setFilter("latest")}
                style={{
                  padding: "8px 20px",
                  borderRadius: "20px",
                  border: "none",
                  backgroundColor: filter === "latest" ? COLORS.primary : "transparent",
                  color: filter === "latest" ? COLORS.dark : COLORS.gray,
                  fontWeight: filter === "latest" ? "700" : "500",
                  fontSize: "14px",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                최신순
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setFilter("popular")}
                style={{
                  padding: "8px 20px",
                  borderRadius: "20px",
                  border: "none",
                  backgroundColor: filter === "popular" ? COLORS.primary : "transparent",
                  color: filter === "popular" ? COLORS.dark : COLORS.gray,
                  fontWeight: filter === "popular" ? "700" : "500",
                  fontSize: "14px",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                인기도순
              </button>
              <button
                onClick={() => setFilter("latest")}
                style={{
                  padding: "8px 20px",
                  borderRadius: "20px",
                  border: "none",
                  backgroundColor: filter === "latest" ? COLORS.primary : "transparent",
                  color: filter === "latest" ? COLORS.dark : COLORS.gray,
                  fontWeight: filter === "latest" ? "700" : "500",
                  fontSize: "14px",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                최신순
              </button>
            </>
          )}
        </div>
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
