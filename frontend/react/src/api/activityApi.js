import api from './axios';

/**
 * 활동 기록 관련 API 함수들 (시청 기록, 검색 기록)
 */

// ============================================
// 시청 기록 API
// ============================================

// 시청 기록 목록 조회
export const getWatchHistory = async () => {
  const response = await api.get('/api/activity/watch-logs/');
  return response.data;
};

export const getWatchHistoryForVideo = async (videoId) => {
  const response = await api.get('/api/activity/watch-logs/', {
    params: { video_id: videoId }
  });
  return response.data;
};

// 시청 기록 적재
export const createWatchHistory = async (videoId, watchedSeconds, tags = [], videoKeyword = null, recommendedKeyword = null) => {
  const tagsValue = Array.isArray(tags) ? tags.join(",") : tags || null;
  const videoKeywordValue = Array.isArray(videoKeyword) ? videoKeyword.join(",") : videoKeyword || null;
  const recommendedKeywordValue = Array.isArray(recommendedKeyword) ? recommendedKeyword.join(",") : recommendedKeyword || null;

  const response = await api.post('/api/activity/watch-logs/', {
    video: videoId,
    watched_seconds: watchedSeconds,
    tags: tagsValue,
    video_keyword: videoKeywordValue,
    recommended_keyword: recommendedKeywordValue
  });
  return response.data;
};

// ============================================
// 검색 기록 API
// ============================================

// 검색 기록 목록 조회
export const getSearchHistory = async () => {
  const response = await api.get('/api/activity/search-logs/');
  return response.data;
};

// 검색 기록 적재
export const createSearchHistory = async (searchQuery) => {
  const response = await api.post('/api/activity/search-logs/', {
    search_query: searchQuery
  });
  return response.data;
};

// ============================================
// 추천 키워드 API
// ============================================

// 시청 기록 기반 추천 키워드 조회
export const getRecommendedKeyword = async () => {
  const response = await api.get('/api/activity/recommended-keyword/');
  return response.data;
};

// ============================================
// 추천 영상 API
// ============================================

// 최근 시청 기록 기반 추천 영상 조회
// filter: 'all' (전체, 기본값), 'keyword' (키워드 정확도), 'tag' (태그 정확도)
export const getRecommendedVideos = async (filter = 'all') => {
  const response = await api.get('/api/activity/recommended-videos/', {
    params: { filter }
  });
  return response.data;
};
