import { useState, useEffect } from "react";
import { getVideos, getPopularVideos } from "../api/videoApi";
import { getRecommendedVideos } from "../api/activityApi";

const MainPage = ({ isLoggedIn, onVideoClick }) => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState(isLoggedIn ? "accuracy" : "popular");

  useEffect(() => {
    setFilter(isLoggedIn ? "accuracy" : "popular");
  }, [isLoggedIn]);

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        setLoading(true);
        let response;

        if (isLoggedIn) {
          if (filter === "accuracy") {
            response = await getRecommendedVideos("accuracy");
            if (response?.data && response.data.length === 0) {
              console.log("정확도순 결과가 없어 인기 영상으로 대체합니다.");
              response = await getPopularVideos();
            }
          } else {
            response = await getVideos("latest");
          }
        } else {
          response =
            filter === "popular"
              ? await getPopularVideos()
              : await getVideos("latest");
        }

        if (response?.data) {
          const formattedVideos = response.data.map((video) => ({
            id: video.id,
            title: video.title,
            tags: video.tags || [],
            video_keyword: video.video_keyword || null,
            likes_count: video.likes_count || 0,
            comments_count: video.comments_count || 0,
            thumbnail_url: video.thumbnail_url,
            duration: video.duration || "0:00",
          }));
          setVideos(formattedVideos);
        }
      } catch (error) {
        console.error("영상 목록 로딩 실패:", error);
        setVideos([]);
      } finally {
        setLoading(false);
      }
    };

    fetchVideos();
  }, [isLoggedIn, filter]);

  const formatLikes = (count) => {
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}천`;
    }
    return count.toString();
  };

  return (
    <div className="page active">
      <section className="home-hero">
        <div className="home-hero-left">
          <div className="title-vertical">
            <h1 className="title-main">이야기</h1>
            <div className="title-sub">
              <span className="title-accent">조선</span>
              <span className="title-en">Joseon Dynasty Stories</span>
            </div>
          </div>
        </div>
        <div className="home-hero-right">
          <div className="hero-intro">
            <h2>
              <span className="accent">조선</span>의 양반집 아가씨가
              <br />
              들려주는 오백 년의 이야기
            </h2>
            <p>
              역사 속 인물이 직접 전하는 생생한 조선의 일상.
              <br />
              시간을 거슬러 그녀의 공간으로 초대합니다.
            </p>
            <div
              className="hero-cta"
              onClick={() => {
                window.location.hash = "about";
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            >
              아가씨를 만나보세요
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </div>
          </div>
          <div className="hero-footer">
            <span>SCROLL</span>
            <div className="scroll-indicator">
              <div className="scroll-line"></div>
            </div>
            <span>2025</span>
          </div>
        </div>
      </section>

      <section className="videos-section">
        <div className="section-header">
          <div className="section-header-left">
            <span className="section-number">01</span>
            <h2 className="section-title">
              {isLoggedIn ? "당신을 위한 이야기" : "많이 본 이야기"}
            </h2>
            <span className="section-title-en">
              {isLoggedIn ? "Recommended for You" : "Popular Stories"}
            </span>
          </div>
          <div className="filter-group">
            {isLoggedIn ? (
              <>
                <button
                  className={`filter-btn ${
                    filter === "accuracy" ? "active" : ""
                  }`}
                  onClick={() => setFilter("accuracy")}
                >
                  정확도순
                </button>
                <button
                  className={`filter-btn ${
                    filter === "latest" ? "active" : ""
                  }`}
                  onClick={() => setFilter("latest")}
                >
                  최신순
                </button>
              </>
            ) : (
              <>
                <button
                  className={`filter-btn ${
                    filter === "popular" ? "active" : ""
                  }`}
                  onClick={() => setFilter("popular")}
                >
                  인기순
                </button>
                <button
                  className={`filter-btn ${
                    filter === "latest" ? "active" : ""
                  }`}
                  onClick={() => setFilter("latest")}
                >
                  최신순
                </button>
              </>
            )}
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: "60px", color: "#888" }}>
            로딩 중...
          </div>
        ) : videos.length > 0 ? (
          <div className="video-grid">
            {videos.map((video) => (
              <div
                key={video.id}
                className="video-card"
                onClick={() => onVideoClick(video)}
              >
                <div className="video-thumbnail">
                  {video.thumbnail_url ? (
                    <img
                      src={video.thumbnail_url}
                      alt={video.title}
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                      }}
                    />
                  ) : null}
                  <div className="video-thumbnail-overlay"></div>
                  <div className="video-play-btn">
                    <svg viewBox="0 0 24 24">
                      <polygon points="5,3 19,12 5,21" />
                    </svg>
                  </div>
                </div>
                <div className="video-info">
                  {video.video_keyword && (
                    <div className="video-keyword">{video.video_keyword}</div>
                  )}
                  <h3 className="video-title">{video.title}</h3>
                  {video.tags && video.tags.length > 0 && (
                    <div className="video-tags">
                      {video.tags.slice(0, 3).map((tag, idx) => (
                        <span key={idx} className="video-tag">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="video-meta">
                    <span>{video.duration}</span>
                    <span>좋아요 {formatLikes(video.likes_count)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: "60px", color: "#888" }}>
            영상이 없습니다.
          </div>
        )}
      </section>

      <footer className="footer">
        <div className="footer-logo">HisToK</div>
        <div className="footer-links">
          <a href="#">About</a>
          <a href="#">Contact</a>
          <a href="#">Terms</a>
        </div>
        <div className="footer-copy">© 2025 HisToK</div>
      </footer>
    </div>
  );
};

export default MainPage;
