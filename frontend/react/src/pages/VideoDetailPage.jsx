import { useState, useEffect, useRef } from "react";
import VideoPlayer from "../features/video/components/VideoPlayer";
import CommentSection from "../features/video/components/CommentSection";
import { getVideo } from "../api/videoApi";
import {
  getVideoComments,
  likeVideo,
  unlikeVideo,
} from "../api/communityApi";
import {
  createWatchHistory,
  getWatchHistoryForVideo,
} from "../api/activityApi";
import { getVideoUrl } from "../utils/imageUtils";

const VideoDetailPage = ({ videoId, isLoggedIn = false, user = null }) => {
  const actualVideoId = videoId || 1;

  const [video, setVideo] = useState(null);
  const [comments, setComments] = useState([]);
  const [isLiked, setIsLiked] = useState(false);
  const [likesCount, setLikesCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const watchHistoryStarted = useRef(false);
  const lastSavedSeconds = useRef(0);
  const currentSeconds = useRef(0);
  const [resumeSeconds, setResumeSeconds] = useState(0);

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


  const formatDuration = (seconds) => {
    if (!seconds) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${String(secs).padStart(2, "0")}`;
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        watchHistoryStarted.current = false;
        lastSavedSeconds.current = 0;
        currentSeconds.current = 0;
        setResumeSeconds(0);

        if (!actualVideoId) {
          console.error("videoId가 없습니다.");
          setLoading(false);
          return;
        }

        try {
          const videoResponse = await getVideo(actualVideoId);
          const videoData = videoResponse?.data ?? videoResponse;
          if (videoData) {
            setVideo(videoData);
            setLikesCount(videoData.likes_count || 0);
            if (isLoggedIn) {
              setIsLiked(videoData.is_liked || false);
            }
          } else {
            setVideo(null);
          }
        } catch (error) {
          console.error("비디오 정보 로드 실패:", error);
          setVideo(null);
        }

        if (isLoggedIn) {
          try {
            const commentsResponse = await getVideoComments(actualVideoId);
            const commentsData = commentsResponse?.data ?? commentsResponse;
            if (Array.isArray(commentsData)) {
              setComments(commentsData);
            } else {
              setComments([]);
            }
          } catch (error) {
            console.error("댓글 로드 실패:", error);
            setComments([]);
          }
        }

        setResumeSeconds(0);
        currentSeconds.current = 0;
        lastSavedSeconds.current = 0;
      } catch (error) {
        console.error("데이터 로딩 실패:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [actualVideoId, isLoggedIn]);

  const saveWatchProgress = async (seconds) => {
    if (!isLoggedIn || !video || !actualVideoId) return;
    if (seconds <= 0) return;
    try {
      await createWatchHistory(
        actualVideoId,
        seconds,
        video.tags || [],
        video.video_keyword || null,
        video.recommended_keyword || null
      );
    } catch (error) {
      // 조용히 처리
    }
  };

  const handlePlayStart = async () => {
    if (!isLoggedIn || !video || !actualVideoId) return;
    watchHistoryStarted.current = true;
    const seconds = Math.floor(currentSeconds.current);
    if (seconds > lastSavedSeconds.current) {
      lastSavedSeconds.current = seconds;
      await saveWatchProgress(seconds);
    }
  };

  const handleTimeUpdate = (seconds) => {
    currentSeconds.current = seconds;
  };

  const handlePause = async () => {
    if (!watchHistoryStarted.current) return;
    const seconds = Math.floor(currentSeconds.current);
    if (seconds <= lastSavedSeconds.current) return;
    lastSavedSeconds.current = seconds;
    await saveWatchProgress(seconds);
  };

  const handleEnded = async () => {
    await handlePause();
  };

  const handleLikeClick = async () => {
    if (!isLoggedIn) {
      alert("로그인이 필요합니다.");
      return;
    }

    try {
      if (isLiked) {
        await unlikeVideo(actualVideoId);
        setIsLiked(false);
        setLikesCount((prev) => Math.max(0, prev - 1));
      } else {
        await likeVideo(actualVideoId);
        setIsLiked(true);
        setLikesCount((prev) => prev + 1);
      }
    } catch (error) {
      console.error("좋아요 처리 실패:", error);
    }
  };

  const handleCommentDelete = (commentId) => {
    setComments(comments.filter((c) => c.id !== commentId));
  };

  const formatLikes = (count) => {
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}천`;
    }
    return count.toString();
  };

  if (loading) {
    return (
      <div className="video-detail-page">
        <div style={{ padding: "60px", textAlign: "center", color: "#888" }}>
          로딩 중...
        </div>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="video-detail-page">
        <div style={{ padding: "60px", textAlign: "center", color: "#888" }}>
          영상을 찾을 수 없습니다.
        </div>
      </div>
    );
  }

  return (
    <div className="page active">
      <div className="video-detail-page">
        <div className="video-detail-container">
          <div className="video-player-area">
            <div className="video-player">
              <VideoPlayer
                initialTime={resumeSeconds}
                onPlayStart={handlePlayStart}
                onTimeUpdate={handleTimeUpdate}
                onPause={handlePause}
                onEnded={handleEnded}
                videoUrl={
                  video?.video_url
                    ? getVideoUrl(video.video_url)
                    : "/videos/selected_scene_1_video.mp4"
                }
              />
            </div>
            <div className="video-detail-info">
              <div className="video-detail-info-left">
                {video.video_keyword && (
                  <div className="video-detail-keyword">
                    {video.video_keyword}
                  </div>
                )}
                <h1 className="video-detail-title">
                  {video.title || "제목 없음"}
                </h1>
                <div className="video-detail-meta">
                  <span>{formatDuration(video.duration)}</span>
                  <span>조회 {video.views_count || 0}</span>
                  <span>{formatKoreanDate(video.upload_date)}</span>
                </div>
                {video.tags && video.tags.length > 0 && (
                  <div className="video-detail-tags">
                    {video.tags.map((tag, idx) => (
                      <span key={idx} className="video-detail-tag">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="video-detail-info-right">
                <button
                  className={`video-like-btn ${isLiked ? "liked" : ""}`}
                  onClick={handleLikeClick}
                >
                  <svg viewBox="0 0 24 24" strokeWidth="1.5">
                    <path d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                  <span>좋아요 {formatLikes(likesCount)}</span>
                </button>
              </div>
            </div>
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
      </div>
    </div>
  );
};

export default VideoDetailPage;
