import api from './axios';

/**
 * 관리자 관련 API 함수들
 */

// 사용자 목록 조회 (관리자 전용)
export const getUsers = async () => {
  const response = await api.get('/api/users/admin/');
  return response.data;
};

// 사용자 상세 조회 (관리자 전용)
export const getUser = async (userId) => {
  const response = await api.get(`/api/users/admin/${userId}/`);
  return response.data;
};

// 사용자 권한 수정 (관리자 전용)
export const updateUserPermission = async (userId, permission) => {
  const response = await api.patch(`/api/users/admin/${userId}/update/`, {
    permission: permission
  });
  return response.data;
};

// 사용자 삭제 (관리자 전용)
export const deleteUser = async (userId) => {
  const response = await api.delete(`/api/users/admin/${userId}/delete/`);
  return response.data;
};
