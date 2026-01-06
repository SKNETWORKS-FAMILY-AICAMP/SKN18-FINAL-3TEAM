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

// 영상 생성 요청
export const createVideo = async (description) => {
  const response = await api.post("/api/video/create/", {
    description: description,
  });
  return response.data;
};

// 영상 수정 (관리자 전용)
export const updateVideo = async (videoId, formData) => {
  const response = await api.patch(`/api/video/${videoId}/update/`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

// 영상 삭제 (관리자 전용)
export const deleteVideo = async (videoId) => {
  const response = await api.delete(`/api/video/${videoId}/delete/`);
  return response.data;
};
