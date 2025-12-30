import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  withCredentials: true,
  timeout: 200000, // 2000초 (LangGraph 실행 시간 고려)
});

// ============================================
// 요청 인터셉터: API 요청 시 Authorization 헤더에 토큰 자동 추가
// ============================================
api.interceptors.request.use(
  (config) => {
    // localStorage에서 access 토큰 가져오기
    const token = localStorage.getItem("access_token");

    if (token) {
      // Authorization 헤더에 Bearer 토큰 추가
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ============================================
// 로그아웃 처리 함수 (인터셉터 정의 전에 선언)
// ============================================
const handleLogout = () => {
  // 모든 토큰 및 사용자 데이터 삭제
  localStorage.clear();

  // 강제 새로고침하여 상태 초기화 (비동기로 처리하여 진행 중인 요청이 완료될 시간 제공)
  setTimeout(() => {
    window.location.href = "/";
    window.location.reload();
  }, 100);
};

// ============================================
// 응답 인터셉터: 토큰 만료 시 자동으로 리프레시
// ============================================
api.interceptors.response.use(
  // 성공 응답은 그대로 반환
  (response) => {
    return response;
  },

  // 에러 응답 처리
  async (error) => {
    const originalRequest = error.config;

    // 네트워크 에러인 경우 (백엔드 서버가 실행되지 않은 경우)
    if (error.code === "ERR_NETWORK" || error.message === "Network Error") {
      // 네트워크 에러는 그대로 전달 (상위에서 처리)
      return Promise.reject(error);
    }

    // 401 또는 403 에러 (인증/권한 실패) && 아직 재시도하지 않은 경우
    // 단, 시청 기록 저장 API는 403이 정상일 수 있으므로 제외
    const isWatchLogsRequest = originalRequest.url?.includes(
      "/api/activity/watch-logs/"
    );

    if (
      (error.response?.status === 401 || error.response?.status === 403) &&
      !originalRequest._retry &&
      !isWatchLogsRequest
    ) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem("refresh_token");

      if (refreshToken) {
        try {
          // Refresh 토큰으로 새로운 Access 토큰 요청
          const response = await axios.post(
            "http://localhost:8000/api/token/refresh/",
            {
              refresh: refreshToken,
            }
          );

          const newAccessToken = response.data.access;

          // 새 토큰 저장
          localStorage.setItem("access_token", newAccessToken);

          // 원래 요청에 새 토큰 적용 후 재시도
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh 토큰도 만료된 경우
          handleLogout();
          return Promise.reject(refreshError);
        }
      } else {
        // Refresh 토큰이 없는 경우
        handleLogout();
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
