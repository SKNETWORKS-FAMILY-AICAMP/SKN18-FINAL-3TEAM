/**
 * ProtectedRoute.jsx
 * 
 * 인증이 필요한 페이지를 보호하는 컴포넌트입니다.
 * 로그인하지 않은 사용자가 접근하면 로그인 페이지로 리다이렉트합니다.
 * 
 * 사용 예시:
 * <Route path="/profile" element={
 *   <ProtectedRoute>
 *     <Profile />
 *   </ProtectedRoute>
 * } />
 */

import { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import api from '../api/axios';

/**
 * ProtectedRoute 컴포넌트
 * 
 * @param {Object} props
 * @param {React.ReactNode} props.children - 보호할 자식 컴포넌트
 * @returns {React.ReactNode} - 인증된 경우 children, 아니면 로그인 페이지로 리다이렉트
 */
function ProtectedRoute({ children }) {
  // ============================================
  // 상태 관리
  // ============================================
  
  // 인증 확인 중인지 여부 (API 호출 중)
  const [isLoading, setIsLoading] = useState(true);
  
  // 사용자 인증 여부
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  
  // 현재 URL 정보 (리다이렉트 후 돌아올 때 사용)
  const location = useLocation();

  // ============================================
  // 인증 상태 확인
  // ============================================
  useEffect(() => {
    /**
     * 서버에 인증 상태를 확인하는 함수
     * - localStorage에 토큰이 있어도 서버에서 유효성 검증 필요
     * - 토큰이 만료되었을 수 있기 때문
     */
    const checkAuth = async () => {
      // localStorage에 토큰이 없으면 바로 미인증 처리
      const token = localStorage.getItem('access_token');
      if (!token) {
        console.log('🔒 ProtectedRoute: 토큰 없음 → 로그인 필요');
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      try {
        // 서버에 인증 상태 확인 요청
        // axios 인터셉터가 자동으로 Authorization 헤더 추가
        const response = await api.get('/api/check-auth/');
        
        if (response.data.isAuthenticated) {
          console.log('✅ ProtectedRoute: 인증됨');
          setIsAuthenticated(true);
        } else {
          console.log('❌ ProtectedRoute: 인증 안됨 (서버 응답)');
          setIsAuthenticated(false);
        }
      } catch (error) {
        // 401 에러 등 인증 실패
        console.error('❌ ProtectedRoute: 인증 확인 실패', error);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  // ============================================
  // 렌더링
  // ============================================

  // 1. 인증 확인 중: 로딩 표시
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '18px',
        color: '#666',
      }}>
        인증 확인 중...
      </div>
    );
  }

  // 2. 인증 안됨: 로그인 페이지로 리다이렉트
  //    - state에 현재 경로 저장 → 로그인 후 원래 페이지로 돌아올 수 있음
  if (!isAuthenticated) {
    console.log('🔀 ProtectedRoute: 로그인 페이지로 리다이렉트');
    return (
      <Navigate 
        to="/login" 
        state={{ from: location.pathname }} 
        replace 
      />
    );
  }

  // 3. 인증됨: 자식 컴포넌트 렌더링
  return children;
}

export default ProtectedRoute;

