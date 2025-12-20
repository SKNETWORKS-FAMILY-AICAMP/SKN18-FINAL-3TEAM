import { useState, useEffect } from "react";
import { COLORS } from "../../constants/theme";
import { getVideos } from "../../api/videoApi";
import { getThumbnailUrl } from "../../utils/imageUtils";

const VideoListPage = ({ onVideoClick }) => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        setLoading(true);
        const response = await getVideos("latest");
        if (response?.data) {
          setVideos(response.data);
        }
      } catch (error) {
        console.error("영상 목록 로딩 실패:", error);
        setVideos([]);
      } finally {
        setLoading(false);
      }
    };

    fetchVideos();
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

  if (loading) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>로딩 중...</div>
    );
  }

  return (
    <div>
      <div
        style={{
          backgroundColor: "transparent",
          padding: "24px",
        }}
      >
        {videos.length === 0 ? (
          <div
            style={{ textAlign: "center", padding: "40px", color: COLORS.gray }}
          >
            업로드된 영상이 없습니다.
          </div>
        ) : (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            {videos.map((video) => (
              <div
                key={video.id}
                onClick={(e) => {
                  e.stopPropagation();
                  if (onVideoClick) {
                    onVideoClick(video.id);
                  }
                }}
                style={{
                  display: "flex",
                  gap: "16px",
                  padding: "16px",
                  borderRadius: "12px",
                  border: "1px solid #eee",
                  cursor: "pointer",
                  transition: "background 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = COLORS.lightGray;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "transparent";
                }}
              >
                <div
                  style={{
                    width: "200px",
                    aspectRatio: "16/9",
                    backgroundColor: COLORS.lightGray,
                    borderRadius: "8px",
                    overflow: "hidden",
                    flexShrink: 0,
                    backgroundImage: video.thumbnail_url
                      ? `url(${getThumbnailUrl(video.thumbnail_url)})`
                      : "none",
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                  }}
                />
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontSize: "18px",
                      fontWeight: "600",
                      color: COLORS.dark,
                      marginBottom: "8px",
                    }}
                  >
                    {video.title}
                  </div>
                  <div
                    style={{
                      fontSize: "13px",
                      color: COLORS.gray,
                      marginBottom: "8px",
                    }}
                  >
                    {video.tags ? video.tags.map((t) => `#${t}`).join(" ") : ""}
                  </div>
                  <div
                    style={{
                      fontSize: "12px",
                      color: COLORS.gray,
                      display: "flex",
                      gap: "16px",
                    }}
                  >
                    <span>업로드일: {formatDate(video.upload_date)}</span>
                    <span>좋아요: {video.likes_count || 0}</span>
                    <span>댓글: {video.comments_count || 0}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoListPage;
