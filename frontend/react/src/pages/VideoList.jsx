/**
 * VideoList.jsx
 *
 * 영상 목록 페이지
 * - 모든 영상 목록 표시
 * - 각 영상 클릭 시 상세 페이지로 이동
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getVideos } from '../api/videoApi';
import './VideoList.css';

function VideoList() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // 컴포넌트 마운트 시 영상 목록 불러오기
  useEffect(() => {
    loadVideos();
  }, []);

  const loadVideos = async () => {
    try {
      setLoading(true);
      const response = await getVideos();
      setVideos(response.data || []);
      setError(null);
    } catch (err) {
      console.error('영상 목록 로드 실패:', err);
      setError('영상 목록을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleVideoClick = (videoId) => {
    navigate(`/videos/${videoId}`);
  };

  if (loading) {
    return (
      <div className="video-list-container">
        <div className="loading">영상 목록을 불러오는 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="video-list-container">
        <div className="error">{error}</div>
        <button onClick={loadVideos}>다시 시도</button>
      </div>
    );
  }

  return (
    <div className="video-list-container">
      <header className="video-list-header">
        <h1>영상 목록</h1>
        <button onClick={() => navigate('/')}>홈으로</button>
      </header>

      {videos.length === 0 ? (
        <div className="empty-message">
          <p>등록된 영상이 없습니다.</p>
        </div>
      ) : (
        <div className="video-grid">
          {videos.map((video) => (
            <div
              key={video.id}
              className="video-card"
              onClick={() => handleVideoClick(video.id)}
            >
              <div className="video-thumbnail">
                {/* 썸네일이 있다면 여기에 표시 */}
                <div className="placeholder-thumbnail">🎬</div>
              </div>

              <div className="video-info">
                <h3 className="video-title">{video.title}</h3>

                <div className="video-meta">
                  <span className="upload-date">
                    {new Date(video.upload_date).toLocaleDateString('ko-KR')}
                  </span>
                </div>

                <div className="video-stats">
                  <span className="likes">👍 {video.likes_count || 0}</span>
                  <span className="comments">💬 {video.comments_count || 0}</span>
                </div>

                {video.tags && video.tags.length > 0 && (
                  <div className="video-tags">
                    {video.tags.slice(0, 3).map((tag, index) => (
                      <span key={index} className="tag">#{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default VideoList;
