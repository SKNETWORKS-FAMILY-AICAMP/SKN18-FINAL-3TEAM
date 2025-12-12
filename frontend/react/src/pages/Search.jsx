/**
 * Search.jsx
 *
 * 검색 페이지
 * - 영상 검색
 * - 검색 기록 저장
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getVideos } from '../api/videoApi';
import { createSearchHistory } from '../api/activityApi';
import './Search.css';

function Search() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearched, setIsSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    try {
      setLoading(true);

      // 검색 수행 (현재는 전체 영상에서 title 필터링)
      const response = await getVideos();
      const videos = response.data || [];

      const results = videos.filter((video) =>
        video.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        video.tags?.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
      );

      setSearchResults(results);
      setIsSearched(true);

      // 검색 기록 저장 (백그라운드)
      try {
        await createSearchHistory(searchQuery);
      } catch (err) {
        console.log('검색 기록 저장 실패 (무시):', err);
      }
    } catch (err) {
      console.error('검색 실패:', err);
      alert('검색에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="search-container">
      <header className="search-header">
        <h1>영상 검색</h1>
        <button onClick={() => navigate('/')}>홈으로</button>
      </header>

      <form className="search-form" onSubmit={handleSearch}>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="영상 제목이나 태그를 검색하세요..."
          className="search-input"
        />
        <button type="submit" disabled={loading}>
          {loading ? '검색 중...' : '🔍 검색'}
        </button>
      </form>

      {isSearched && (
        <div className="search-results">
          <h2>검색 결과: {searchResults.length}개</h2>

          {searchResults.length === 0 ? (
            <p className="no-results">검색 결과가 없습니다.</p>
          ) : (
            <div className="results-grid">
              {searchResults.map((video) => (
                <div
                  key={video.id}
                  className="result-card"
                  onClick={() => navigate(`/videos/${video.id}`)}
                >
                  <div className="result-thumbnail">🎬</div>
                  <div className="result-info">
                    <h3>{video.title}</h3>
                    <div className="result-meta">
                      <span>👍 {video.likes_count}</span>
                      <span>💬 {video.comments_count}</span>
                    </div>
                    {video.tags && video.tags.length > 0 && (
                      <div className="result-tags">
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
      )}
    </div>
  );
}

export default Search;
