import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

function Home() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/api/users/check-auth/')
      .then(res => {
        console.log('Auth check response:', res.data);
        if (res.data.isAuthenticated) {
          console.log('User data:', res.data.user);
          setUser(res.data.user);
        }
        setLoading(false);
      })
      .catch(error => {
        console.error('Auth check error:', error);
        // 에러가 나도 로그인 페이지로 보내지 않음
        setLoading(false);
      });
  }, []);

  const handleLogout = () => {
    // localStorage에서 토큰 삭제
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');

    // Django 세션 삭제 (선택사항)
    api.post('/api/users/logout/')
      .then(() => {
        console.log('✅ 로그아웃 성공!');
        setUser(null);
        navigate('/');
      })
      .catch(error => {
        console.error('Logout error:', error);
        // 에러가 나도 홈으로 이동
        setUser(null);
        navigate('/');
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
    api.delete('/api/users/delete-account/')
      .then(response => {
        console.log('✅ 회원탈퇴 성공:', response.data.message);
        alert('회원탈퇴가 완료되었습니다.\nGoogle 연동도 해제되었습니다.');

        // localStorage에서 토큰 삭제
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        // 상태 초기화하고 홈으로 이동
        setUser(null);
        navigate('/');
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
      fontFamily: 'Arial, sans-serif',
      maxWidth: '800px',
      margin: '50px auto',
      padding: '20px'
    }}>
      <h1>🎬 영상 플랫폼</h1>

      {!user ? (
        // 로그인 안 한 사용자
        <div>
          <p style={{ fontSize: '1.2rem', marginBottom: '30px', color: '#666' }}>
            로그인하여 모든 기능을 이용하세요!
          </p>

          <div style={{ marginBottom: '40px' }}>
            <button
              onClick={() => window.location.href = 'http://localhost:8000/accounts/google/login/'}
              style={{
                padding: '15px 40px',
                fontSize: '18px',
                backgroundColor: '#4285f4',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                marginRight: '10px'
              }}
            >
              Continue with Google
            </button>
          </div>

          <div style={{
            background: '#f8f9fa',
            padding: '30px',
            borderRadius: '10px',
            marginTop: '40px'
          }}>
            <h2 style={{ marginBottom: '20px' }}>공개 콘텐츠</h2>
            <div style={{ display: 'flex', gap: '15px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => navigate('/videos')}
                style={{
                  padding: '12px 24px',
                  fontSize: '14px',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer',
                }}
              >
                📺 영상 둘러보기
              </button>

              <button
                onClick={() => navigate('/search')}
                style={{
                  padding: '12px 24px',
                  fontSize: '14px',
                  backgroundColor: '#17a2b8',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer',
                }}
              >
                🔍 영상 검색
              </button>
            </div>
          </div>
        </div>
      ) : (
        // 로그인한 사용자
        <div>
          <div style={{
            background: '#f8f9fa',
            padding: '20px',
            borderRadius: '10px',
            marginBottom: '30px'
          }}>
            <p><strong>이메일:</strong> {user.email || '정보 없음'}</p>
            <p><strong>사용자명:</strong> {user.username || '정보 없음'}</p>
            {user.first_name && <p><strong>이름:</strong> {user.first_name}</p>}
            {user.last_name && <p><strong>성:</strong> {user.last_name}</p>}
            <p><strong>사용자 ID:</strong> {user.id}</p>
          </div>

          {/* 메인 메뉴 */}
          <div style={{ marginBottom: '30px' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '15px' }}>메인 메뉴</h2>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => navigate('/videos')}
                style={{
                  padding: '12px 24px',
                  fontSize: '14px',
                  backgroundColor: '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer',
                }}
              >
                📺 영상 목록
              </button>

              <button
                onClick={() => navigate('/search')}
                style={{
                  padding: '12px 24px',
                  fontSize: '14px',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer',
                }}
              >
                🔍 검색
              </button>
            </div>
          </div>

          {/* 내 활동 메뉴 */}
          <div style={{ marginBottom: '30px' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '15px' }}>내 활동</h2>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => navigate('/profile')}
                style={{
                  padding: '12px 24px',
                  fontSize: '14px',
                  backgroundColor: '#667eea',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer',
                }}
              >
                👤 마이페이지
              </button>

              <button
                onClick={() => navigate('/watch-history')}
                style={{
                  padding: '12px 24px',
                  fontSize: '14px',
                  backgroundColor: '#17a2b8',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer',
                }}
              >
                📺 시청 기록
              </button>

              <button
                onClick={() => navigate('/my-activity')}
                style={{
                  padding: '12px 24px',
                  fontSize: '14px',
                  backgroundColor: '#ffc107',
                  color: '#333',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer',
                }}
              >
                💬 내 활동
              </button>
            </div>
          </div>

          {/* 관리자 메뉴 (permission이 admin일 때만 표시) */}
          {user.permission === 'admin' && (
            <div style={{ marginBottom: '30px' }}>
              <h2 style={{ fontSize: '1.5rem', marginBottom: '15px' }}>관리자 메뉴</h2>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
                <button
                  onClick={() => navigate('/admin')}
                  style={{
                    padding: '12px 24px',
                    fontSize: '14px',
                    backgroundColor: '#dc3545',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: 'pointer',
                  }}
                >
                  🔧 관리자 페이지
                </button>

                <button
                  onClick={() => navigate('/admin/video-upload')}
                  style={{
                    padding: '12px 24px',
                    fontSize: '14px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: 'pointer',
                  }}
                >
                  ⬆️ 영상 업로드
                </button>
              </div>
            </div>
          )}

          {/* 계정 관리 */}
          <div style={{ marginTop: '40px', paddingTop: '20px', borderTop: '1px solid #ddd' }}>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
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
                }}
              >
                로그아웃
              </button>

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
        </div>
      )}
    </div>
  );
}

export default Home;
