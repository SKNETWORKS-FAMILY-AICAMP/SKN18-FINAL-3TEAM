/**
 * Admin.jsx
 *
 * 관리자 페이지
 * - 사용자 목록 관리
 * - 사용자 권한 수정
 * - 사용자 삭제
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getUsers, updateUserPermission, deleteUser } from '../api/adminApi';
import './Admin.css';

function Admin() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await getUsers();
      setUsers(response.data || []);
      setError(null);
    } catch (err) {
      console.error('사용자 목록 로드 실패:', err);
      setError('사용자 목록을 불러올 수 없습니다. 관리자 권한이 필요합니다.');
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionChange = async (userId, newPermission) => {
    if (!window.confirm(`권한을 ${newPermission}으로 변경하시겠습니까?`)) {
      return;
    }

    try {
      await updateUserPermission(userId, newPermission);
      setUsers(
        users.map((user) =>
          user.id === userId ? { ...user, permission: newPermission } : user
        )
      );
      alert('권한이 변경되었습니다.');
    } catch (err) {
      console.error('권한 변경 실패:', err);
      alert('권한 변경에 실패했습니다.');
    }
  };

  const handleDeleteUser = async (userId, userEmail) => {
    if (!window.confirm(`${userEmail} 사용자를 삭제하시겠습니까?`)) {
      return;
    }

    try {
      await deleteUser(userId);
      setUsers(users.filter((user) => user.id !== userId));
      alert('사용자가 삭제되었습니다.');
    } catch (err) {
      console.error('사용자 삭제 실패:', err);
      alert('사용자 삭제에 실패했습니다.');
    }
  };

  if (loading) {
    return (
      <div className="admin-container">
        <div className="loading">로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-container">
        <div className="error">{error}</div>
        <button onClick={() => navigate('/')}>홈으로</button>
      </div>
    );
  }

  return (
    <div className="admin-container">
      <header className="admin-header">
        <h1>🔧 관리자 페이지</h1>
        <div className="header-buttons">
          <button onClick={() => navigate('/admin/video-upload')}>영상 업로드</button>
          <button onClick={() => navigate('/')}>홈으로</button>
        </div>
      </header>

      <div className="users-section">
        <h2>사용자 관리 ({users.length}명)</h2>

        <div className="users-table">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>이메일</th>
                <th>닉네임</th>
                <th>권한</th>
                <th>가입일</th>
                <th>활성화</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.id}</td>
                  <td>{user.email}</td>
                  <td>{user.nickname || '-'}</td>
                  <td>
                    <select
                      value={user.permission}
                      onChange={(e) => handlePermissionChange(user.id, e.target.value)}
                      className={`permission-select ${user.permission}`}
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td>{new Date(user.sign_up_date).toLocaleDateString('ko-KR')}</td>
                  <td>
                    <span className={`status ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? '활성' : '비활성'}
                    </span>
                  </td>
                  <td>
                    <button
                      className="delete-btn"
                      onClick={() => handleDeleteUser(user.id, user.email)}
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default Admin;
