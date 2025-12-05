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
    api.post('/api/logout/')
      .then(() => {
        navigate('/login');
      })
      .catch(error => {
        console.error('Logout error:', error);
        // 에러가 나도 로그인 페이지로 이동
        navigate('/login');
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
          <button
            onClick={handleLogout}
            style={{
              padding: '10px 20px',
              fontSize: '14px',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer',
              marginTop: '20px',
            }}
          >
            로그아웃
          </button>
        </div>
      )}
    </div>
  );
}

export default Home;
