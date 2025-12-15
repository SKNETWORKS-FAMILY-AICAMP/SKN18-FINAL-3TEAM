import api from "./axios";

/**
 * 영상 관련 API 함수들
 */

// 영상 목록 조회
export const getVideos = async (sort = "latest", tag = "") => {
  const params = new URLSearchParams();
  if (sort) params.append("sort", sort);
  if (tag) params.append("tag", tag);

  const response = await api.get(`/api/video/list/?${params.toString()}`);
  return response.data;
};

// 영상 상세 조회
export const getVideo = async (videoId) => {
  const response = await api.get(`/api/video/${videoId}/`);
  return response.data;
};

// 인기 영상 조회
export const getPopularVideos = async () => {
  const response = await api.get("/api/video/popular/");
  return response.data;
};

// 인기 태그 조회
export const getPopularTags = async () => {
  const response = await api.get("/api/video/tags/popular/");
  return response.data;
};
