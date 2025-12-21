import { useState, useEffect } from "react";
import { COLORS } from "../../constants/theme";
import { getVideos, deleteVideo } from "../../api/videoApi";
import { getThumbnailUrl } from "../../utils/imageUtils";

const VideoListPage = ({ onVideoClick }) => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openMenuId, setOpenMenuId] = useState(null);

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

  const handleEdit = (videoId) => {
    window.location.hash = `admin/video/edit/${videoId}`;
  };

  const handleDelete = async (videoId) => {
    if (!window.confirm("정말 이 영상을 삭제하시겠습니까?")) {
      return;
    }

    try {
      await deleteVideo(videoId);
      alert("영상이 삭제되었습니다.");
      // 목록 새로고침
      const response = await getVideos("latest");
      if (response?.data) {
        setVideos(response.data);
      }
      setOpenMenuId(null);
    } catch (error) {
      console.error("영상 삭제 실패:", error);
      alert("영상 삭제에 실패했습니다.");
    }
  };

  const toggleMenu = (e, videoId) => {
    e.stopPropagation();
    setOpenMenuId(openMenuId === videoId ? null : videoId);
  };

  // 메뉴 외부 클릭 시 닫기
  useEffect(() => {
    const handleClickOutside = () => {
      if (openMenuId !== null) {
        setOpenMenuId(null);
      }
    };

    document.addEventListener("click", handleClickOutside);
    return () => {
      document.removeEventListener("click", handleClickOutside);
    };
  }, [openMenuId]);

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
                  position: "relative",
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

                {/* 점 3개 메뉴 버튼 */}
                <div style={{ position: "relative" }}>
                  <button
                    onClick={(e) => toggleMenu(e, video.id)}
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "6px",
                      border: "none",
                      backgroundColor: "transparent",
                      color: COLORS.gray,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "20px",
                      fontWeight: "700",
                      lineHeight: "1",
                      padding: 0,
                      transition: "background-color 0.2s",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = COLORS.lightGray;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = "transparent";
                    }}
                  >
                    ⋮
                  </button>

                  {/* 드롭다운 메뉴 */}
                  {openMenuId === video.id && (
                    <div
                      style={{
                        position: "absolute",
                        top: "40px",
                        right: "0",
                        backgroundColor: COLORS.white,
                        border: "1px solid #ddd",
                        borderRadius: "8px",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                        zIndex: 1000,
                        minWidth: "120px",
                        overflow: "hidden",
                      }}
                    >
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEdit(video.id);
                        }}
                        style={{
                          width: "100%",
                          padding: "12px 16px",
                          border: "none",
                          backgroundColor: "transparent",
                          color: COLORS.dark,
                          fontSize: "14px",
                          fontWeight: "500",
                          textAlign: "left",
                          cursor: "pointer",
                          transition: "background-color 0.2s",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = COLORS.lightGray;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = "transparent";
                        }}
                      >
                        편집
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(video.id);
                        }}
                        style={{
                          width: "100%",
                          padding: "12px 16px",
                          border: "none",
                          backgroundColor: "transparent",
                          color: "#ff4444",
                          fontSize: "14px",
                          fontWeight: "500",
                          textAlign: "left",
                          cursor: "pointer",
                          transition: "background-color 0.2s",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = "#fff0f0";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = "transparent";
                        }}
                      >
                        삭제
                      </button>
                    </div>
                  )}
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
