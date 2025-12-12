import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true,
});

// ============================================
// 요청 인터셉터: API 요청 시 Authorization 헤더에 토큰 자동 추가
// ============================================
api.interceptors.request.use(
  (config) => {
    // localStorage에서 access 토큰 가져오기
    const token = localStorage.getItem('access_token');

    if (token) {
      // Authorization 헤더에 Bearer 토큰 추가
      config.headers.Authorization = `Bearer ${token}`;
      console.log('📤 API 요청:', config.url, '| 토큰 첨부:', token.substring(0, 20) + '...');
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

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

    // 401 에러 (인증 실패) && 아직 재시도하지 않은 경우
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');

      if (refreshToken) {
        try {
          console.log('🔄 Access 토큰 만료! Refresh 토큰으로 갱신 시도...');

          // Refresh 토큰으로 새로운 Access 토큰 요청
          const response = await axios.post('http://localhost:8000/api/token/refresh/', {
            refresh: refreshToken
          });

          const newAccessToken = response.data.access;

          // 새 토큰 저장
          localStorage.setItem('access_token', newAccessToken);
          console.log('✅ 토큰 갱신 성공!');

          // 원래 요청에 새 토큰 적용 후 재시도
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          return api(originalRequest);

        } catch (refreshError) {
          // Refresh 토큰도 만료된 경우
          console.error('❌ Refresh 토큰 만료! 로그아웃 처리...');

          // 토큰 삭제
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');

          // 홈 페이지로 리다이렉트 (로그인 버튼 표시됨)
          window.location.href = '/';

          return Promise.reject(refreshError);
        }
      } else {
        // Refresh 토큰이 없는 경우 홈 페이지로
        console.warn('⚠️ Refresh 토큰 없음. 로그인 필요.');
        window.location.href = '/';
      }
    }

    return Promise.reject(error);
  }
);

export default api;
