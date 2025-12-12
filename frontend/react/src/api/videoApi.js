import api from './axios';

/**
 * 영상 관련 API 함수들
 */

// 영상 목록 조회
export const getVideos = async () => {
  const response = await api.get('/api/video/videos/');
  return response.data;
};

// 영상 상세 조회
export const getVideo = async (videoId) => {
  const response = await api.get(`/api/video/videos/${videoId}/`);
  return response.data;
};

// 영상 생성 (관리자 전용)
export const createVideo = async (videoData) => {
  const response = await api.post('/api/video/videos/', videoData);
  return response.data;
};

// 영상 수정 (관리자 전용)
export const updateVideo = async (videoId, videoData) => {
  const response = await api.put(`/api/video/videos/${videoId}/`, videoData);
  return response.data;
};

// 영상 삭제 (관리자 전용)
export const deleteVideo = async (videoId) => {
  const response = await api.delete(`/api/video/videos/${videoId}/`);
  return response.data;
};
