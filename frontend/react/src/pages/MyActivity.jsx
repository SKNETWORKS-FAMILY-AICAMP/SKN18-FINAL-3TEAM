/**
 * MyActivity.jsx
 *
 * 내 활동 페이지
 * - 내가 작성한 댓글, 답글, 좋아요 목록
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMyActivity } from '../api/communityApi';
import './MyActivity.css';

function MyActivity() {
  const [activity, setActivity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('comments'); // comments, replies, likes
  const navigate = useNavigate();

  useEffect(() => {
    loadActivity();
  }, []);

  const loadActivity = async () => {
    try {
      setLoading(true);
      const response = await getMyActivity();
      setActivity(response.data);
      setError(null);
    } catch (err) {
      console.error('활동 내역 로드 실패:', err);
      setError('활동 내역을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="my-activity-container">
        <div className="loading">로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="my-activity-container">
        <div className="error">{error}</div>
        <button onClick={loadActivity}>다시 시도</button>
      </div>
    );
  }

  return (
    <div className="my-activity-container">
      <header className="activity-header">
        <h1>내 활동</h1>
        <button onClick={() => navigate('/')}>홈으로</button>
      </header>

      <div className="activity-tabs">
        <button
          className={activeTab === 'comments' ? 'active' : ''}
          onClick={() => setActiveTab('comments')}
        >
          댓글 ({activity?.comments?.length || 0})
        </button>
        <button
          className={activeTab === 'replies' ? 'active' : ''}
          onClick={() => setActiveTab('replies')}
        >
          답글 ({activity?.replies?.length || 0})
        </button>
        <button
          className={activeTab === 'likes' ? 'active' : ''}
          onClick={() => setActiveTab('likes')}
        >
          좋아요 ({activity?.likes?.length || 0})
        </button>
      </div>

      <div className="activity-content">
        {/* 댓글 탭 */}
        {activeTab === 'comments' && (
          <div className="comments-tab">
            {activity?.comments?.length === 0 ? (
              <p className="empty">작성한 댓글이 없습니다.</p>
            ) : (
              activity?.comments?.map((comment) => (
                <div key={comment.id} className="activity-item">
                  <div className="item-header">
                    <span className="video-title">
                      {comment.video_title}
                    </span>
                    <span className="date">
                      {new Date(comment.created_at).toLocaleDateString('ko-KR')}
                    </span>
                  </div>
                  <p className="content">{comment.comment_content}</p>
                  <div className="stats">
                    <span>👍 {comment.comment_likes_count}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* 답글 탭 */}
        {activeTab === 'replies' && (
          <div className="replies-tab">
            {activity?.replies?.length === 0 ? (
              <p className="empty">작성한 답글이 없습니다.</p>
            ) : (
              activity?.replies?.map((reply) => (
                <div key={reply.id} className="activity-item">
                  <div className="item-header">
                    <span className="comment-ref">댓글에 대한 답글</span>
                    <span className="date">
                      {new Date(reply.created_at).toLocaleDateString('ko-KR')}
                    </span>
                  </div>
                  <p className="content">{reply.reply_content}</p>
                </div>
              ))
            )}
          </div>
        )}

        {/* 좋아요 탭 */}
        {activeTab === 'likes' && (
          <div className="likes-tab">
            {activity?.likes?.length === 0 ? (
              <p className="empty">좋아요한 항목이 없습니다.</p>
            ) : (
              activity?.likes?.map((like) => (
                <div key={like.id} className="activity-item">
                  <div className="item-header">
                    <span className="like-target">
                      {like.target_type} 좋아요
                    </span>
                    <span className="date">
                      {new Date(like.created_at).toLocaleDateString('ko-KR')}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default MyActivity;
