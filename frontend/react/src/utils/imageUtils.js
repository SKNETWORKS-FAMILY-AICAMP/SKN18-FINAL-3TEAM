/**
 * 이미지 URL 유틸리티 함수들
 */

const BACKEND_URL = window.ENV?.API_URL || "http://localhost:8000";
const MEDIA_URL = `${BACKEND_URL}/media/`;

/**
 * 프로필 이미지 URL 생성 (상대 경로를 절대 URL로 변환)
 * @param {string} profileImage - 프로필 이미지 경로
 * @returns {string|null} - 절대 URL 또는 null
 */
export const getProfileImageUrl = (profileImage) => {
  if (!profileImage) return null;

  // 이미 절대 URL이면 그대로 반환
  if (
    profileImage.startsWith("http://") ||
    profileImage.startsWith("https://")
  ) {
    return profileImage;
  }

  // 상대 경로면 백엔드 URL과 조합
  return `${MEDIA_URL}${profileImage}`;
};

/**
 * 썸네일 이미지 URL 생성 (상대 경로를 절대 URL로 변환)
 * @param {string} thumbnailUrl - 썸네일 이미지 경로
 * @returns {string|null} - 절대 URL 또는 null
 */
export const getThumbnailUrl = (thumbnailUrl) => {
  if (!thumbnailUrl) return null;

  // 이미 절대 URL이면 그대로 반환
  if (
    thumbnailUrl.startsWith("http://") ||
    thumbnailUrl.startsWith("https://")
  ) {
    return thumbnailUrl;
  }

  // 상대 경로면 백엔드 URL과 조합
  return `${MEDIA_URL}${thumbnailUrl}`;
};

/**
 * 비디오 URL 생성 (상대 경로를 절대 URL로 변환)
 * @param {string} videoUrl - 비디오 URL 경로
 * @returns {string|null} - 절대 URL 또는 null
 */
export const getVideoUrl = (videoUrl) => {
  if (!videoUrl) return null;

  // 이미 절대 URL이면 그대로 반환
  if (videoUrl.startsWith("http://") || videoUrl.startsWith("https://")) {
    return videoUrl;
  }

  // /videos/ 로 시작하면 public 폴더의 영상
  // Vite는 public 폴더를 루트로 제공하므로 상대 경로 그대로 사용
  if (videoUrl.startsWith("/videos/")) {
    return videoUrl;
  }

  // 상대 경로면 백엔드 미디어 URL과 조합
  const fullUrl = `${MEDIA_URL}${videoUrl}`;
  return fullUrl;
};
