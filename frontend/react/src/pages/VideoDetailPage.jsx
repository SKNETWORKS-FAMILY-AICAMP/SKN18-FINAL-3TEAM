import { useState, useEffect, useRef } from "react";
import VideoPlayer from "../features/video/components/VideoPlayer";
import { getVideo } from "../api/videoApi";
import {
  getVideoComments,
  likeVideo,
  unlikeVideo,
  createComment,
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
  const [commentText, setCommentText] = useState("");
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);
  const [showReplyForm, setShowReplyForm] = useState({});
  const [replyTexts, setReplyTexts] = useState({});
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
                replies: c.replies || [],
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

  const handleCommentSubmit = async () => {
    if (!isLoggedIn || !commentText.trim() || isSubmittingComment) return;

    setIsSubmittingComment(true);
    try {
      const response = await createComment(actualVideoId, commentText.trim());
      if (response?.data) {
        const newComment = {
          id: response.data.id,
          username: user?.nickname || user?.display_name || "사용자",
          text: response.data.comment_content,
          comment_content: response.data.comment_content,
          profileImage: user?.profile_image,
          likes: 0,
          comment_likes_count: 0,
          created_at: response.data.created_at || new Date().toISOString(),
          timeAgo: "방금 전",
          replies: [],
          user: user,
          is_liked: false,
        };
        setComments([newComment, ...comments]);
        setCommentText("");
      }
    } catch (error) {
      console.error("댓글 작성 실패:", error);
      alert("댓글 작성에 실패했습니다.");
    } finally {
      setIsSubmittingComment(false);
    }
  };

  const toggleReplyForm = (commentId) => {
    setShowReplyForm((prev) => ({
      ...prev,
      [commentId]: !prev[commentId],
    }));
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

          {isLoggedIn && (
            <div className="comments-area">
              <div className="comments-header">
                <h3 className="comments-title">
                  이야기를 나누다 <span>{comments.length}</span>
                </h3>
              </div>
              <div className="comments-list">
                {comments.map((comment) => (
                  <div key={comment.id} className="comment-item">
                    <div className="comment-main">
                      <div className="comment-avatar">
                        {comment.user?.nickname?.[0] ||
                          comment.user?.display_name?.[0] ||
                          comment.username?.[0] ||
                          "사용자"}
                      </div>
                      <div className="comment-body">
                        <div className="comment-header">
                          <span className="comment-author">
                            {comment.username}
                          </span>
                          <span className="comment-date">
                            {comment.timeAgo}
                          </span>
                        </div>
                        <p className="comment-text">{comment.text}</p>
                        <div className="comment-actions">
                          <button
                            className="comment-action-btn"
                            onClick={() => toggleReplyForm(comment.id)}
                          >
                            <svg
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.5"
                            >
                              <path d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                            </svg>
                            답글
                          </button>
                          <button className="comment-action-btn">
                            <svg
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.5"
                            >
                              <path d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                            </svg>
                            {comment.comment_likes_count || 0}
                          </button>
                        </div>
                      </div>
                    </div>
                    {comment.replies && comment.replies.length > 0 && (
                      <div className="comment-replies">
                        {comment.replies.map((reply) => (
                          <div key={reply.id} className="reply-item">
                            <div className="reply-main">
                              <div className="reply-avatar">
                                {reply.user?.nickname?.[0] ||
                                  reply.user?.display_name?.[0] ||
                                  "사용자"}
                              </div>
                              <div className="reply-body">
                                <div className="reply-header">
                                  <span className="reply-author">
                                    {reply.user?.nickname ||
                                      reply.user?.display_name ||
                                      "사용자"}
                                  </span>
                                  <span className="reply-date">
                                    {formatTimeAgo(reply.created_at)}
                                  </span>
                                </div>
                                <p className="reply-text">
                                  {reply.reply_content}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {showReplyForm[comment.id] && (
                      <div className="reply-form show">
                        <div className="reply-input-wrapper">
                          <input
                            type="text"
                            className="reply-input"
                            placeholder="답글을 입력하세요..."
                            value={replyTexts[comment.id] || ""}
                            onChange={(e) =>
                              setReplyTexts({
                                ...replyTexts,
                                [comment.id]: e.target.value,
                              })
                            }
                          />
                          <button className="reply-submit">등록</button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <div className="comment-input-area">
                <textarea
                  className="comment-input"
                  rows="3"
                  placeholder="이야기를 남겨주세요..."
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                />
                <button
                  className="comment-submit"
                  onClick={handleCommentSubmit}
                  disabled={!commentText.trim() || isSubmittingComment}
                >
                  등록
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoDetailPage;
