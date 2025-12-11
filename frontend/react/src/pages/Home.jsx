import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

function Home() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/api/check-auth/')
      .then(res => {
        console.log('Auth check response:', res.data);
        if (res.data.isAuthenticated) {
          console.log('User data:', res.data.user);
          setUser(res.data.user);
        } else {
          navigate('/login');
        }
        setLoading(false);
      })
      .catch(error => {
        console.error('Auth check error:', error);
        navigate('/login');
        setLoading(false);
      });
  }, [navigate]);

  const handleLogout = () => {
    // localStorage에서 토큰 삭제
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');

    // Django 세션 삭제 (선택사항)
    api.post('/api/logout/')
      .then(() => {
        console.log('✅ 로그아웃 성공!');
        navigate('/login');
      })
      .catch(error => {
        console.error('Logout error:', error);
        // 에러가 나도 로그인 페이지로 이동
        navigate('/login');
      });
  };

  const handleDeleteAccount = () => {
    // 회원탈퇴 확인
    const confirmed = window.confirm(
      '정말로 회원탈퇴 하시겠습니까?\n\n' +
      '탈퇴 시 다음 사항이 처리됩니다:\n' +
      '- Google 계정 연동 해제\n' +
      '- 모든 사용자 데이터 삭제\n' +
      '- 복구 불가능\n\n' +
      '계속 하시겠습니까?'
    );

    if (!confirmed) {
      return;
    }

    // 재확인
    const doubleConfirm = window.confirm(
      '마지막 확인입니다.\n정말로 탈퇴하시겠습니까?'
    );

    if (!doubleConfirm) {
      return;
    }

    // 회원탈퇴 API 호출
    api.delete('/api/delete-account/')
      .then(response => {
        console.log('✅ 회원탈퇴 성공:', response.data.message);
        alert('회원탈퇴가 완료되었습니다.\nGoogle 연동도 해제되었습니다.');

        // localStorage에서 토큰 삭제
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        // 로그인 페이지로 이동
        navigate('/login');
      })
      .catch(error => {
        console.error('❌ 회원탈퇴 실패:', error);
        if (error.response?.data?.error) {
          alert(`회원탈퇴 실패: ${error.response.data.error}`);
        } else {
          alert('회원탈퇴 처리 중 오류가 발생했습니다.');
        }
      });
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', marginTop: '100px' }}>
        로딩 중...
      </div>
    );
  }

  return (
    <div style={{
      textAlign: 'center',
      marginTop: '50px',
      fontFamily: 'Arial, sans-serif'
    }}>
      <h1>환영합니다!</h1>
      {user && (
        <div>
          <p><strong>이메일:</strong> {user.email || '정보 없음'}</p>
          <p><strong>사용자명:</strong> {user.username || '정보 없음'}</p>
          {user.first_name && <p><strong>이름:</strong> {user.first_name}</p>}
          {user.last_name && <p><strong>성:</strong> {user.last_name}</p>}
          <p><strong>사용자 ID:</strong> {user.id}</p>

          <div style={{ marginTop: '20px' }}>
            {/* 마이페이지 버튼 */}
            <button
              onClick={() => navigate('/profile')}
              style={{
                padding: '10px 20px',
                fontSize: '14px',
                backgroundColor: '#667eea',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer',
                marginRight: '10px',
              }}
            >
              마이페이지
            </button>
            
            {/* 로그아웃 버튼 */}
            <button
              onClick={handleLogout}
              style={{
                padding: '10px 20px',
                fontSize: '14px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer',
                marginRight: '10px',
              }}
            >
              로그아웃
            </button>

            {/* 회원탈퇴 버튼 */}
            <button
              onClick={handleDeleteAccount}
              style={{
                padding: '10px 20px',
                fontSize: '14px',
                backgroundColor: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer',
              }}
            >
              회원탈퇴
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Home;
