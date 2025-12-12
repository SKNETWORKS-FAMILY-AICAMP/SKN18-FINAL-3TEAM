/**
 * WatchHistory.jsx
 *
 * 시청 기록 페이지
 * - 내 시청 기록 목록 표시
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getWatchHistory } from '../api/activityApi';
import './WatchHistory.css';

function WatchHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const response = await getWatchHistory();
      setHistory(response.data || []);
      setError(null);
    } catch (err) {
      console.error('시청 기록 로드 실패:', err);
      setError('시청 기록을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="watch-history-container">
        <div className="loading">로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="watch-history-container">
        <div className="error">{error}</div>
        <button onClick={loadHistory}>다시 시도</button>
      </div>
    );
  }

  return (
    <div className="watch-history-container">
      <header className="history-header">
        <h1>시청 기록</h1>
        <button onClick={() => navigate('/')}>홈으로</button>
      </header>

      {history.length === 0 ? (
        <div className="empty-message">
          <p>시청 기록이 없습니다.</p>
        </div>
      ) : (
        <div className="history-list">
          {history.map((item) => (
            <div
              key={item.id}
              className="history-item"
              onClick={() => navigate(`/videos/${item.video}`)}
            >
              <div className="history-thumbnail">🎬</div>

              <div className="history-info">
                <h3>{item.video_title}</h3>

                <div className="history-meta">
                  <span className="watch-date">
                    시청: {new Date(item.created_at).toLocaleString('ko-KR')}
                  </span>
                  {item.watched_seconds > 0 && (
                    <span className="watch-time">
                      {Math.floor(item.watched_seconds / 60)}분 {item.watched_seconds % 60}초
                    </span>
                  )}
                </div>

                {item.tags && item.tags.length > 0 && (
                  <div className="history-tags">
                    {item.tags.slice(0, 3).map((tag, index) => (
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

export default WatchHistory;
