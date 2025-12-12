/**
 * App.jsx
 *
 * 애플리케이션의 메인 컴포넌트입니다.
 * 라우팅 설정과 전역 컴포넌트를 관리합니다.
 *
 * 라우트 구조:
 *
 * [공개 라우트]
 * - /                           : 홈 페이지 (로그인 버튼 포함)
 * - /videos                     : 영상 목록
 * - /videos/:videoId            : 영상 상세
 * - /search                     : 검색
 *
 * [보호된 라우트 - 로그인 필요]
 * - /profile                    : 마이페이지
 * - /watch-history              : 시청 기록
 * - /my-activity                : 내 활동
 *
 * [관리자 라우트 - 관리자 권한 필요]
 * - /admin                      : 관리자 페이지
 * - /admin/video-upload         : 영상 업로드
 * - /admin/video-edit/:videoId  : 영상 수정
 */

import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';

// 페이지 컴포넌트
import Home from './pages/Home';
import Profile from './pages/Profile';
import VideoList from './pages/VideoList';
import VideoDetail from './pages/VideoDetail';
import Search from './pages/Search';
import WatchHistory from './pages/WatchHistory';
import MyActivity from './pages/MyActivity';
import Admin from './pages/Admin';
import VideoForm from './pages/VideoForm';

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
  const navigate = useNavigate();

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

      // React Router로 홈으로 이동 (쿼리 파라미터 제거됨)
      navigate('/', { replace: true });
    }
  }, [navigate]);

  // 이 컴포넌트는 UI를 렌더링하지 않음
  return null;
}

/**
 * App 컴포넌트
 *
 * 라우트 설정:
 * - 공개 라우트: 누구나 접근 가능 (/)
 * - 보호된 라우트: 로그인한 사용자만 접근 가능 (/profile 등)
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

        {/* 영상 목록 */}
        <Route path="/videos" element={<VideoList />} />

        {/* 영상 상세 */}
        <Route path="/videos/:videoId" element={<VideoDetail />} />

        {/* 검색 */}
        <Route path="/search" element={<Search />} />

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

        {/* 시청 기록 */}
        <Route
          path="/watch-history"
          element={
            <ProtectedRoute>
              <WatchHistory />
            </ProtectedRoute>
          }
        />

        {/* 내 활동 */}
        <Route
          path="/my-activity"
          element={
            <ProtectedRoute>
              <MyActivity />
            </ProtectedRoute>
          }
        />

        {/* ========== 관리자 라우트 (관리자 권한 필요) ========== */}

        {/* 관리자 페이지 */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <Admin />
            </ProtectedRoute>
          }
        />

        {/* 영상 업로드 */}
        <Route
          path="/admin/video-upload"
          element={
            <ProtectedRoute>
              <VideoForm />
            </ProtectedRoute>
          }
        />

        {/* 영상 수정 */}
        <Route
          path="/admin/video-edit/:videoId"
          element={
            <ProtectedRoute>
              <VideoForm />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
