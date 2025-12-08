import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import Login from './pages/Login';
import Home from './pages/Home';

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

      // URL에서 토큰 파라미터 제거하고 홈으로 이동 (새로고침 없이)
      navigate('/', { replace: true });
    }
  }, [navigate]);

  return null;
}

function App() {
  return (
    <BrowserRouter>
      <TokenHandler />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
