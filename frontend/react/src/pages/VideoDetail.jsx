/**
 * VideoDetail.jsx
 *
 * 영상 상세 페이지
 * - 영상 정보 표시
 * - 좋아요 기능
 * - 댓글/답글 표시 및 작성
 * - 시청 기록 저장
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getVideo } from '../api/videoApi';
import {
  getVideoComments,
  createComment,
  getCommentReplies,
  createReply,
  likeVideo,
  unlikeVideo,
  likeComment,
  unlikeComment,
  likeReply,
  unlikeReply,
} from '../api/communityApi';
import { createWatchHistory } from '../api/activityApi';
import './VideoDetail.css';

function VideoDetail() {
  const { videoId } = useParams();
  const navigate = useNavigate();

  const [video, setVideo] = useState(null);
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [newComment, setNewComment] = useState('');
  const [replyInputs, setReplyInputs] = useState({}); // {commentId: replyText}
  const [showReplies, setShowReplies] = useState({}); // {commentId: boolean}
  const [replies, setReplies] = useState({}); // {commentId: [replies]}

  const [isLiked, setIsLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);

  useEffect(() => {
    loadVideoData();
  }, [videoId]);

  const loadVideoData = async () => {
    try {
      setLoading(true);

      // 영상 정보 로드
      const videoResponse = await getVideo(videoId);
      setVideo(videoResponse.data);
      setLikeCount(videoResponse.data.likes_count || 0);

      // 댓글 목록 로드
      const commentsResponse = await getVideoComments(videoId);
      setComments(commentsResponse.data || []);

      // 시청 기록 저장 (백그라운드)
      try {
        await createWatchHistory(videoId, 0, videoResponse.data.tags || []);
      } catch (err) {
        console.log('시청 기록 저장 실패 (무시):', err);
      }

      setError(null);
    } catch (err) {
      console.error('영상 데이터 로드 실패:', err);
      setError('영상을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 좋아요 토글
  const handleLikeVideo = async () => {
    try {
      if (isLiked) {
        await unlikeVideo(videoId);
        setLikeCount((prev) => prev - 1);
        setIsLiked(false);
      } else {
        await likeVideo(videoId);
        setLikeCount((prev) => prev + 1);
        setIsLiked(true);
      }
    } catch (err) {
      console.error('좋아요 처리 실패:', err);
      alert(err.response?.data?.error?.message || '좋아요 처리에 실패했습니다.');
    }
  };

  // 댓글 작성
  const handleSubmitComment = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    try {
      const response = await createComment(videoId, newComment);
      setComments([response.data, ...comments]);
      setNewComment('');
    } catch (err) {
      console.error('댓글 작성 실패:', err);
      alert('댓글 작성에 실패했습니다.');
    }
  };

  // 답글 목록 토글
  const toggleReplies = async (commentId) => {
    if (showReplies[commentId]) {
      // 답글 숨기기
      setShowReplies({ ...showReplies, [commentId]: false });
    } else {
      // 답글 표시
      if (!replies[commentId]) {
        // 답글 로드
        try {
          const response = await getCommentReplies(commentId);
          setReplies({ ...replies, [commentId]: response.data || [] });
        } catch (err) {
          console.error('답글 로드 실패:', err);
        }
      }
      setShowReplies({ ...showReplies, [commentId]: true });
    }
  };

  // 답글 작성
  const handleSubmitReply = async (commentId) => {
    const replyText = replyInputs[commentId];
    if (!replyText?.trim()) return;

    try {
      const response = await createReply(commentId, replyText);
      const updatedReplies = [...(replies[commentId] || []), response.data];
      setReplies({ ...replies, [commentId]: updatedReplies });
      setReplyInputs({ ...replyInputs, [commentId]: '' });
    } catch (err) {
      console.error('답글 작성 실패:', err);
      alert('답글 작성에 실패했습니다.');
    }
  };

  // 댓글 좋아요
  const handleLikeComment = async (commentId) => {
    try {
      await likeComment(commentId);
      setComments(
        comments.map((c) =>
          c.id === commentId ? { ...c, comment_likes_count: c.comment_likes_count + 1 } : c
        )
      );
    } catch (err) {
      console.error('댓글 좋아요 실패:', err);
    }
  };

  if (loading) {
    return <div className="video-detail-container"><div className="loading">로딩 중...</div></div>;
  }

  if (error || !video) {
    return (
      <div className="video-detail-container">
        <div className="error">{error || '영상을 찾을 수 없습니다.'}</div>
        <button onClick={() => navigate('/videos')}>목록으로</button>
      </div>
    );
  }

  return (
    <div className="video-detail-container">
      <button className="back-button" onClick={() => navigate('/videos')}>
        ← 목록으로
      </button>

      {/* 영상 정보 */}
      <div className="video-section">
        <div className="video-player">
          <div className="placeholder-player">🎬 영상 플레이어</div>
        </div>

        <div className="video-header">
          <h1>{video.title}</h1>
          <div className="video-actions">
            <button
              className={`like-button ${isLiked ? 'liked' : ''}`}
              onClick={handleLikeVideo}
            >
              👍 {likeCount}
            </button>
          </div>
        </div>

        <div className="video-metadata">
          <span>업로드: {new Date(video.upload_date).toLocaleDateString('ko-KR')}</span>
          <span>댓글: {comments.length}개</span>
        </div>

        {video.tags && video.tags.length > 0 && (
          <div className="video-tags">
            {video.tags.map((tag, index) => (
              <span key={index} className="tag">#{tag}</span>
            ))}
          </div>
        )}
      </div>

      {/* 댓글 섹션 */}
      <div className="comments-section">
        <h2>댓글 {comments.length}개</h2>

        {/* 댓글 작성 */}
        <form className="comment-form" onSubmit={handleSubmitComment}>
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="댓글을 입력하세요..."
            rows="3"
          />
          <button type="submit">댓글 작성</button>
        </form>

        {/* 댓글 목록 */}
        <div className="comments-list">
          {comments.map((comment) => (
            <div key={comment.id} className="comment-item">
              <div className="comment-header">
                <strong>{comment.user_nickname || comment.user_email}</strong>
                <span className="comment-date">
                  {new Date(comment.created_at).toLocaleString('ko-KR')}
                </span>
              </div>

              <p className="comment-content">{comment.comment_content}</p>

              <div className="comment-actions">
                <button onClick={() => handleLikeComment(comment.id)}>
                  👍 {comment.comment_likes_count || 0}
                </button>
                <button onClick={() => toggleReplies(comment.id)}>
                  💬 답글 {comment.replies_count || 0}개
                </button>
              </div>

              {/* 답글 섹션 */}
              {showReplies[comment.id] && (
                <div className="replies-section">
                  {/* 답글 목록 */}
                  {replies[comment.id]?.map((reply) => (
                    <div key={reply.id} className="reply-item">
                      <div className="reply-header">
                        <strong>{reply.user_nickname || reply.user_email}</strong>
                        <span className="reply-date">
                          {new Date(reply.created_at).toLocaleString('ko-KR')}
                        </span>
                      </div>
                      <p className="reply-content">{reply.reply_content}</p>
                    </div>
                  ))}

                  {/* 답글 작성 */}
                  <div className="reply-form">
                    <input
                      type="text"
                      value={replyInputs[comment.id] || ''}
                      onChange={(e) =>
                        setReplyInputs({ ...replyInputs, [comment.id]: e.target.value })
                      }
                      placeholder="답글을 입력하세요..."
                    />
                    <button onClick={() => handleSubmitReply(comment.id)}>답글 작성</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default VideoDetail;
