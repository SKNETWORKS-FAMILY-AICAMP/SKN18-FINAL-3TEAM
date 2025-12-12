/**
 * App.jsx
 * 
 * 애플리케이션의 메인 컴포넌트입니다.
 * 라우팅 설정과 전역 컴포넌트를 관리합니다.
 * 
 * 라우트 구조:
 * - /          : 홈 페이지
 * - /login     : 로그인 페이지
 * - /profile   : 마이페이지 (로그인 필요)
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useEffect } from 'react';

// 페이지 컴포넌트
import Login from './pages/Login';
import Home from './pages/Home';
import Profile from './pages/Profile';

// 보호된 라우트 컴포넌트 (로그인 필요한 페이지용)
import ProtectedRoute from './components/ProtectedRoute';

/**
 * TokenHandler 컴포넌트
 * 
 * Google OAuth 로그인 후 리다이렉트될 때 URL에 포함된 토큰을 처리합니다.
 * - URL 파라미터에서 access, refresh 토큰 추출
 * - localStorage에 저장
 * - URL에서 토큰 파라미터 제거
 * 
 * 동작 흐름:
 * 1. Google 로그인 완료
 * 2. Django가 /?access=xxx&refresh=xxx 로 리다이렉트
 * 3. 이 컴포넌트가 토큰 저장
 * 4. 깔끔한 URL(/)로 이동
 */
function TokenHandler() {
  useEffect(() => {
    // 현재 URL에서 쿼리 파라미터 읽기
    const params = new URLSearchParams(window.location.search);
    const accessToken = params.get('access');
    const refreshToken = params.get('refresh');

    // 토큰이 URL에 있으면 localStorage에 저장
    if (accessToken && refreshToken) {
      console.log('✅ 토큰 받음! localStorage에 저장 중...');

      // localStorage에 토큰 저장
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);

      console.log('✅ 토큰 저장 완료! 홈으로 이동...');

      // URL에서 토큰 파라미터 제거하고 홈으로 이동
      // window.location.replace 사용 → React Router 경고 방지
      // replace는 브라우저 히스토리에 남기지 않음
      window.location.replace('/');
    }
  }, []);

  // 이 컴포넌트는 UI를 렌더링하지 않음
  return null;
}

/**
 * App 컴포넌트
 * 
 * 라우트 설정:
 * - 공개 라우트: 누구나 접근 가능 (/, /login)
 * - 보호된 라우트: 로그인한 사용자만 접근 가능 (/profile)
 *   → ProtectedRoute 컴포넌트로 감싸서 인증 체크
 */
function App() {
  return (
    <BrowserRouter>
      {/* TokenHandler: URL의 토큰 파라미터 처리 */}
      <TokenHandler />
      
      <Routes>
        {/* ========== 공개 라우트 ========== */}
        
        {/* 홈 페이지 */}
        <Route path="/" element={<Home />} />
        
        {/* 로그인 페이지 */}
        <Route path="/login" element={<Login />} />
        
        {/* ========== 보호된 라우트 (로그인 필요) ========== */}
        
        {/* 마이페이지 - 프로필 조회/수정 */}
        <Route 
          path="/profile" 
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          } 
        />
        
        {/* 
          향후 추가될 보호된 라우트 예시:
          
          <Route 
            path="/history" 
            element={
              <ProtectedRoute>
                <WatchHistory />
              </ProtectedRoute>
            } 
          />
        */}
      </Routes>
    </BrowserRouter>
  );
}

export default App;
