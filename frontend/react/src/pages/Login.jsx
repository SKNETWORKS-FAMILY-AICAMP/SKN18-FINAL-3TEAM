import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

function Login() {
  const navigate = useNavigate();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    api.get('/api/check-auth/')
      .then(res => {
        if (res.data.isAuthenticated) {
          navigate('/');
        }
        setChecking(false);
      })
      .catch(() => setChecking(false));
  }, [navigate]);

  const handleGoogleLogin = () => {
    window.location.href = 'http://localhost:8000/accounts/google/login/';
  };

  if (checking) {
    return (
      <div style={{ textAlign: 'center', marginTop: '100px' }}>
        확인 중...
      </div>
    );
  }

  return (
    <div style={{
      textAlign: 'center',
      marginTop: '100px',
      fontFamily: 'Arial, sans-serif'
    }}>
      <h1>로그인</h1>
      <button
        onClick={handleGoogleLogin}
        style={{
          padding: '15px 30px',
          fontSize: '16px',
          backgroundColor: '#4285f4',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: 'pointer',
          marginTop: '20px',
        }}
      >
        Continue with Google
      </button>
    </div>
  );
}

export default Login;
