import { useState, useEffect, useRef } from "react";
import VideoPlayer from "../features/video/components/VideoPlayer";
import VideoInfo from "../features/video/components/VideoInfo";
import CommentSection from "../features/video/components/CommentSection";
import { getVideo } from "../api/videoApi";
import { getVideoComments, likeVideo, unlikeVideo } from "../api/communityApi";
import { createWatchHistory } from "../api/activityApi";
import { getVideoUrl } from "../utils/imageUtils";

const VideoDetailPage = ({ videoId, isLoggedIn = false, user = null }) => {
  // videoId가 없으면 기본값 1 사용
  const actualVideoId = videoId || 1;

  const [video, setVideo] = useState(null);
  const [comments, setComments] = useState([]);
  const [isLiked, setIsLiked] = useState(false);
  const [likesCount, setLikesCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const watchHistorySaved = useRef(false);

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
        watchHistorySaved.current = false;

        // videoId가 없으면 조기 종료
        if (!actualVideoId) {
          console.error("videoId가 없습니다.");
          setLoading(false);
          return;
        }

        // 비디오 정보 로드
        try {
          const videoResponse = await getVideo(actualVideoId);
          if (videoResponse?.data) {
            const processedUrl = videoResponse.data.video_url
              ? getVideoUrl(videoResponse.data.video_url)
              : "/videos/selected_scene_1_video.mp4";
            setVideo(videoResponse.data);
            setLikesCount(videoResponse.data.likes_count || 0);

            // 백엔드에서 받은 좋아요 상태 설정
            if (isLoggedIn) {
              setIsLiked(videoResponse.data.is_liked || false);
            }
          } else {
            console.warn("비디오 데이터가 없습니다.");
            setVideo(null);
          }
        } catch (error) {
          console.error("비디오 정보 로드 실패:", error);
          // 비디오 로드 실패해도 페이지는 표시 (에러 메시지와 함께)
          setVideo(null);
        }

        // 댓글 로드 (로그인한 경우만)
        if (isLoggedIn) {
          try {
            const commentsResponse = await getVideoComments(actualVideoId);
            if (commentsResponse?.data) {
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
              setComments(formattedComments);
            }
          } catch (error) {
            console.error("댓글 로드 실패:", error);
            setComments([]);
          }
        }
      } catch (error) {
        console.error("데이터 로딩 실패:", error);
        // 에러 발생 시에도 로딩 상태 해제
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [actualVideoId, isLoggedIn]);

  // 영상 재생 시 시청 기록 저장 (한 번만)
  const handleVideoPlay = async () => {
    if (!watchHistorySaved.current && isLoggedIn && video && actualVideoId) {
      try {
        await createWatchHistory(actualVideoId, 0, video.tags || []);
        watchHistorySaved.current = true;
        console.log("✓ 시청 기록 저장 완료:", actualVideoId);
      } catch (error) {
        // 에러 발생해도 재시도 방지
        watchHistorySaved.current = true;
        console.warn("⚠️ 시청 기록 저장 실패:", error);
      }
    }
  };

  const handleLikeClick = async () => {
    if (!isLoggedIn) {
      alert("로그인이 필요합니다.");
      return;
    }

    try {
      if (isLiked) {
        // 좋아요 취소
        await unlikeVideo(actualVideoId);
        setIsLiked(false);
        setLikesCount((prev) => Math.max(0, prev - 1));
      } else {
        // 좋아요 추가
        await likeVideo(actualVideoId);
        setIsLiked(true);
        setLikesCount((prev) => prev + 1);
      }
    } catch (error) {
      console.error("좋아요 처리 실패:", error);
      // 에러 발생 시 상태 롤백
      if (
        error.response?.status === 400 &&
        error.response?.data?.error?.code === "ALREADY_LIKED"
      ) {
        // 이미 좋아요가 있는 경우
        setIsLiked(true);
      } else if (error.response?.status === 404) {
        // 좋아요가 없는 경우
        setIsLiked(false);
      }
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
        minHeight: "calc(100vh - 76px)",
        boxSizing: "border-box",
      }}
    >
      <div style={{ flex: 1 }}>
        <VideoPlayer
          videoUrl={
            video?.video_url
              ? getVideoUrl(video.video_url)
              : "/videos/selected_scene_1_video.mp4"
          }
          onPlay={handleVideoPlay}
        />
        <VideoInfo
          tags={video?.tags ? video.tags.map((t) => `#${t}`).join(" ") : ""}
          title={video?.title || "제목 없음"}
          date={formatKoreanDate(video?.upload_date)}
          isLiked={isLiked}
          onLikeClick={handleLikeClick}
          likesCount={likesCount}
        />
      </div>

      {isLoggedIn && (
        <CommentSection
          comments={comments}
          videoId={actualVideoId}
          user={user}
          isLoggedIn={isLoggedIn}
          onCommentDelete={handleCommentDelete}
        />
      )}
    </div>
  );
};

export default VideoDetailPage;
