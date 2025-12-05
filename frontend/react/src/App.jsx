import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useEffect } from 'react';
import Login from './pages/Login';
import Home from './pages/Home';

function App() {
  // URL 파라미터에서 JWT 토큰 추출 및 localStorage에 저장
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

      // URL에서 토큰 파라미터 제거 (보안)
      // 예: http://localhost:3000/?access=xxx&refresh=yyy
      // → http://localhost:3000/
      window.history.replaceState({}, document.title, '/');

      // 페이지 새로고침하여 홈으로 이동
      console.log('✅ 토큰 저장 완료! 페이지 리로드...');
      window.location.href = '/';
    }
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
