import { useState, useEffect } from "react";
import VideoPlayer from "../features/video/components/VideoPlayer";
import VideoInfo from "../features/video/components/VideoInfo";
import CommentSection from "../features/video/components/CommentSection";
import { getVideo } from "../api/videoApi";
import { getVideoComments, likeVideo, unlikeVideo } from "../api/communityApi";
import { getVideoUrl } from "../utils/imageUtils";

const VideoDetailPage = ({ videoId = 1, isLoggedIn = false, user = null }) => {
  const [video, setVideo] = useState(null);
  const [comments, setComments] = useState([]);
  const [isLiked, setIsLiked] = useState(false);
  const [loading, setLoading] = useState(true);

  // 한국 날짜 형식 포맷팅 함수 (YYYY. MM. DD.)
  const formatKoreanDate = (dateString) => {
    if (!dateString) return "";
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return "";

      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");

      return `${year}. ${month}. ${day}.`;
    } catch (error) {
      console.error("날짜 포맷 오류:", error, dateString);
      return "";
    }
  };

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
      return date.toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      });
    } catch (error) {
      console.error("날짜 포맷 오류:", error, dateString);
      return "";
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);

        // 비디오 정보 로드
        const videoResponse = await getVideo(videoId);
        if (videoResponse?.data) {
          console.log("영상 데이터:", videoResponse.data);
          console.log("영상 URL (원본):", videoResponse.data.video_url);
          const processedUrl = videoResponse.data.video_url
            ? getVideoUrl(videoResponse.data.video_url)
            : "/videos/selected_scene_1_video.mp4";
          console.log("영상 URL (처리 후):", processedUrl);
          setVideo(videoResponse.data);
        }

        // 댓글 로드 (로그인한 경우만)
        if (isLoggedIn) {
          const commentsResponse = await getVideoComments(videoId);
          if (commentsResponse?.data) {
            console.log("댓글 데이터:", commentsResponse.data);
            const formattedComments = commentsResponse.data.map((c) => ({
              id: c.id,
              username: c.user?.nickname || c.user?.display_name || "사용자",
              text: c.comment_content,
              comment_content: c.comment_content,
              profileImage: c.user?.profile_image,
              likes: c.comment_likes_count || 0,
              comment_likes_count: c.comment_likes_count || 0,
              created_at: c.created_at,
              timeAgo: formatTimeAgo(c.created_at),
              replies: c.replies || [], // 백엔드에서 받은 replies 사용
              user: c.user,
              is_liked: c.is_liked || false,
            }));
            console.log("포맷된 댓글:", formattedComments);
            setComments(formattedComments);
          }
        }
      } catch (error) {
        console.error("데이터 로딩 실패:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [videoId, isLoggedIn]);

  const handleLikeClick = async () => {
    if (!isLoggedIn) {
      alert("로그인이 필요합니다.");
      return;
    }

    try {
      if (isLiked) {
        await unlikeVideo(videoId);
        setIsLiked(false);
      } else {
        await likeVideo(videoId);
        setIsLiked(true);
      }
    } catch (error) {
      console.error("좋아요 처리 실패:", error);
    }
  };

  const handleCommentDelete = (commentId) => {
    setComments(comments.filter((c) => c.id !== commentId));
  };

  if (loading) {
    return (
      <div style={{ padding: "60px", textAlign: "center" }}>로딩 중...</div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        gap: "30px",
        padding: "60px 60px 30px 60px",
        height: "calc(100vh - 76px)",
        overflow: "hidden",
        boxSizing: "border-box",
      }}
    >
      <div style={{ flex: 1, overflow: "hidden" }}>
        <VideoPlayer
          videoUrl={
            video?.video_url
              ? getVideoUrl(video.video_url)
              : "/videos/selected_scene_1_video.mp4"
          }
        />
        <VideoInfo
          tags={video?.tags ? video.tags.map((t) => `#${t}`).join(" ") : ""}
          title={video?.title || "제목 없음"}
          date={formatKoreanDate(video?.upload_date)}
          isLiked={isLiked}
          onLikeClick={handleLikeClick}
        />
      </div>

      {isLoggedIn && (
        <CommentSection
          comments={comments}
          videoId={videoId}
          user={user}
          onCommentDelete={handleCommentDelete}
        />
      )}
    </div>
  );
};

export default VideoDetailPage;
