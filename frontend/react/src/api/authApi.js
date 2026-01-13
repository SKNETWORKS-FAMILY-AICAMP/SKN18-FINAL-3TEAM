import api from "./axios";

/**
 * 인증 관련 API 함수들
 */

// 인증 상태 확인
export const checkAuth = async () => {
  const response = await api.get("/api/users/check-auth/");
  return response.data;
};

// Google 로그인 URL 가져오기
export const getGoogleLoginUrl = () => {
  return `${window.ENV?.API_URL || "http://localhost:8000"}/accounts/google/login/`;
};

// 로그아웃
export const logout = async () => {
  const response = await api.post("/api/users/logout/");
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  return response.data;
};

// JWT 토큰 저장
export const saveTokens = (accessToken, refreshToken) => {
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("refresh_token", refreshToken);
};

// JWT 토큰 제거
export const removeTokens = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
};

