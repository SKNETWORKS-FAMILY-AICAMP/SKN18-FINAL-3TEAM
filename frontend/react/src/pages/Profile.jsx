/**
 * Profile.jsx
 * 
 * 마이페이지 - 프로필 조회 및 수정 페이지입니다.
 * 
 * 기능:
 * 1. 프로필 정보 조회 (닉네임, 이메일, 프로필 이미지 등)
 * 2. 프로필 정보 수정 (닉네임, 성별, 나이)
 * 3. 프로필 이미지 업로드/삭제
 * 
 * 주의:
 * - 이 페이지는 ProtectedRoute로 감싸져 있어 로그인한 사용자만 접근 가능
 * - 이메일, 가입일은 수정 불가 (읽기 전용)
 */

import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import './Profile.css';

function Profile() {
  // ============================================
  // 상태 관리
  // ============================================
  
  // 프로필 데이터 (서버에서 받아온 원본)
  const [profile, setProfile] = useState(null);
  
  // 수정 중인 폼 데이터 (사용자 입력)
  const [formData, setFormData] = useState({
    nickname: '',
    gender: null,      // null: 미선택, true: 남성, false: 여성
    age: '',
  });
  
  // UI 상태
  const [isLoading, setIsLoading] = useState(true);      // 초기 로딩
  const [isSaving, setIsSaving] = useState(false);       // 저장 중
  const [isUploading, setIsUploading] = useState(false); // 이미지 업로드 중
  const [isEditing, setIsEditing] = useState(false);     // 편집 모드 여부
  
  // 메시지 상태
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  
  // 파일 input 참조 (프로그래밍 방식으로 클릭하기 위함)
  const fileInputRef = useRef(null);
  
  const navigate = useNavigate();

  // ============================================
  // 프로필 데이터 로드
  // ============================================
  useEffect(() => {
    fetchProfile();
  }, []);

  /**
   * 서버에서 프로필 정보를 가져오는 함수
   * GET /api/users/profile/
   */
  const fetchProfile = async () => {
    try {
      setIsLoading(true);
      
      // API 호출 (axios 인터셉터가 자동으로 토큰 추가)
      const response = await api.get('/api/users/profile/');
      
      console.log('📋 프로필 데이터:', response.data);
      
      // 서버 응답에서 프로필 데이터 추출
      const profileData = response.data.data;
      setProfile(profileData);
      
      // 폼 데이터 초기화 (편집 모드에서 사용)
      setFormData({
        nickname: profileData.nickname || '',
        gender: profileData.gender,
        age: profileData.age || '',
      });
      
    } catch (error) {
      console.error('❌ 프로필 로드 실패:', error);
      setErrorMessage('프로필을 불러오는데 실패했습니다.');
      
      // 401 에러면 로그인 페이지로 (인터셉터에서 처리하지만 안전장치)
      if (error.response?.status === 401) {
        navigate('/login');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // ============================================
  // 폼 입력 핸들러
  // ============================================
  
  /**
   * input 필드 변경 핸들러
   * @param {Event} e - input change 이벤트
   */
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  /**
   * 성별 선택 핸들러
   * @param {boolean|null} value - true: 남성, false: 여성, null: 미선택
   */
  const handleGenderChange = (value) => {
    setFormData(prev => ({
      ...prev,
      gender: value,
    }));
  };

  // ============================================
  // 프로필 수정 기능
  // ============================================
  
  /**
   * 편집 모드 시작
   */
  const handleEditStart = () => {
    setIsEditing(true);
    setSuccessMessage('');
    setErrorMessage('');
  };

  /**
   * 편집 취소 - 원래 데이터로 복원
   */
  const handleEditCancel = () => {
    // 폼 데이터를 원래 프로필 데이터로 복원
    setFormData({
      nickname: profile.nickname || '',
      gender: profile.gender,
      age: profile.age || '',
    });
    setIsEditing(false);
    setErrorMessage('');
  };

  /**
   * 프로필 수정 저장
   * PATCH /api/users/profile/
   */
  const handleSave = async () => {
    try {
      setIsSaving(true);
      setErrorMessage('');
      
      // 수정할 데이터 준비
      // - 빈 문자열은 null로 변환 (서버에서 처리 편하게)
      const updateData = {
        nickname: formData.nickname || null,
        gender: formData.gender,
        age: formData.age ? parseInt(formData.age, 10) : null,
      };
      
      console.log('📤 프로필 수정 요청:', updateData);
      
      // API 호출
      const response = await api.patch('/api/users/profile/', updateData);
      
      console.log('✅ 프로필 수정 성공:', response.data);
      
      // 프로필 데이터 업데이트
      setProfile(response.data.data);
      setIsEditing(false);
      setSuccessMessage('프로필이 수정되었습니다.');
      
      // 3초 후 성공 메시지 숨기기
      setTimeout(() => setSuccessMessage(''), 3000);
      
    } catch (error) {
      console.error('❌ 프로필 수정 실패:', error);
      
      // 서버에서 받은 에러 메시지 표시
      if (error.response?.data?.error?.fields) {
        // 필드별 에러 메시지
        const fields = error.response.data.error.fields;
        const messages = Object.entries(fields)
          .map(([key, value]) => `${key}: ${value}`)
          .join(', ');
        setErrorMessage(messages);
      } else if (error.response?.data?.error?.message) {
        setErrorMessage(error.response.data.error.message);
      } else {
        setErrorMessage('프로필 수정에 실패했습니다.');
      }
    } finally {
      setIsSaving(false);
    }
  };

  // ============================================
  // 프로필 이미지 기능
  // ============================================
  
  /**
   * 이미지 선택 버튼 클릭 핸들러
   * - 숨겨진 file input 클릭
   */
  const handleImageButtonClick = () => {
    fileInputRef.current?.click();
  };

  /**
   * 이미지 파일 선택 핸들러
   * POST /api/users/profile/image/
   * 
   * @param {Event} e - file input change 이벤트
   */
  const handleImageChange = async (e) => {
    const file = e.target.files?.[0];
    
    // 파일이 선택되지 않았으면 무시
    if (!file) return;
    
    // 파일 유효성 검사 (프론트에서도 체크)
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      setErrorMessage('지원하지 않는 이미지 형식입니다. (jpg, png, gif, webp만 가능)');
      return;
    }
    
    // 파일 크기 제한 (5MB)
    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
      setErrorMessage('이미지 크기는 5MB 이하여야 합니다.');
      return;
    }
    
    try {
      setIsUploading(true);
      setErrorMessage('');
      
      // FormData 생성 (파일 업로드용)
      const formData = new FormData();
      formData.append('image', file);
      
      console.log('📤 이미지 업로드 시작:', file.name);
      
      // API 호출
      // Content-Type은 axios가 자동으로 multipart/form-data로 설정
      const response = await api.post('/api/users/profile/image/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      console.log('✅ 이미지 업로드 성공:', response.data);
      
      // 프로필 데이터 업데이트
      setProfile(prev => ({
        ...prev,
        profile_image: response.data.data.profile_image,
      }));
      
      setSuccessMessage('프로필 이미지가 업로드되었습니다.');
      setTimeout(() => setSuccessMessage(''), 3000);
      
    } catch (error) {
      console.error('❌ 이미지 업로드 실패:', error);
      
      if (error.response?.data?.error?.message) {
        setErrorMessage(error.response.data.error.message);
      } else {
        setErrorMessage('이미지 업로드에 실패했습니다.');
      }
    } finally {
      setIsUploading(false);
      // file input 초기화 (같은 파일 다시 선택 가능하게)
      e.target.value = '';
    }
  };

  /**
   * 프로필 이미지 삭제 핸들러
   * DELETE /api/users/profile/image/
   */
  const handleImageDelete = async () => {
    // 삭제 확인
    if (!window.confirm('프로필 이미지를 삭제하시겠습니까?')) {
      return;
    }
    
    try {
      setIsUploading(true);
      setErrorMessage('');
      
      // API 호출
      await api.delete('/api/users/profile/image/');
      
      console.log('✅ 이미지 삭제 성공');
      
      // 프로필 데이터 업데이트
      setProfile(prev => ({
        ...prev,
        profile_image: null,
      }));
      
      setSuccessMessage('프로필 이미지가 삭제되었습니다.');
      setTimeout(() => setSuccessMessage(''), 3000);
      
    } catch (error) {
      console.error('❌ 이미지 삭제 실패:', error);
      
      if (error.response?.data?.error?.message) {
        setErrorMessage(error.response.data.error.message);
      } else {
        setErrorMessage('이미지 삭제에 실패했습니다.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  // ============================================
  // 유틸리티 함수
  // ============================================
  
  /**
   * 프로필 이미지 URL 생성
   * - 이미지가 있으면 서버 URL 반환
   * - 없으면 기본 아바타 URL 반환
   */
  const getProfileImageUrl = () => {
    if (profile?.profile_image) {
      // 절대 URL인지 확인
      if (profile.profile_image.startsWith('http')) {
        return profile.profile_image;
      }
      // 상대 경로면 서버 URL 붙이기
      return `http://localhost:8000/media/${profile.profile_image}`;
    }
    // 기본 아바타 (UI Avatars 서비스 사용)
    const name = profile?.display_name || profile?.email || 'User';
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random&size=200`;
  };

  /**
   * 성별 표시 텍스트
   */
  const getGenderText = () => {
    if (profile?.gender === true) return '남성';
    if (profile?.gender === false) return '여성';
    return '미설정';
  };

  /**
   * 가입일 포맷팅
   */
  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // ============================================
  // 렌더링
  // ============================================

  // 로딩 중
  if (isLoading) {
    return (
      <div className="profile-container">
        <div className="profile-loading">
          프로필을 불러오는 중...
        </div>
      </div>
    );
  }

  // 프로필 데이터 없음
  if (!profile) {
    return (
      <div className="profile-container">
        <div className="profile-error">
          프로필을 불러올 수 없습니다.
          <button onClick={fetchProfile}>다시 시도</button>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-container">
      {/* 상단 네비게이션 */}
      <nav className="profile-nav">
        <button 
          className="back-button"
          onClick={() => navigate('/')}
        >
          ← 홈으로
        </button>
        <h1>마이페이지</h1>
      </nav>

      {/* 메시지 영역 */}
      {successMessage && (
        <div className="message success-message">
          ✅ {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="message error-message">
          ❌ {errorMessage}
        </div>
      )}

      {/* 프로필 카드 */}
      <div className="profile-card">
        
        {/* ========== 프로필 이미지 섹션 ========== */}
        <div className="profile-image-section">
          <div className="profile-image-wrapper">
            {/* 프로필 이미지 */}
            <img
              src={getProfileImageUrl()}
              alt="프로필 이미지"
              className="profile-image"
            />
            
            {/* 이미지 업로드 오버레이 (hover 시 표시) */}
            <div className="profile-image-overlay">
              <button 
                onClick={handleImageButtonClick}
                disabled={isUploading}
              >
                {isUploading ? '업로드 중...' : '변경'}
              </button>
              {profile.profile_image && (
                <button 
                  onClick={handleImageDelete}
                  disabled={isUploading}
                  className="delete-button"
                >
                  삭제
                </button>
              )}
            </div>
          </div>
          
          {/* 숨겨진 파일 input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
            onChange={handleImageChange}
            style={{ display: 'none' }}
          />
          
          {/* 표시 이름 */}
          <h2 className="profile-display-name">
            {profile.display_name}
          </h2>
        </div>

        {/* ========== 프로필 정보 섹션 ========== */}
        <div className="profile-info-section">
          
          {/* 이메일 (읽기 전용) */}
          <div className="info-row">
            <label>이메일</label>
            <span className="info-value readonly">
              {profile.email}
            </span>
          </div>

          {/* 닉네임 */}
          <div className="info-row">
            <label>닉네임</label>
            {isEditing ? (
              <input
                type="text"
                name="nickname"
                value={formData.nickname}
                onChange={handleInputChange}
                placeholder="닉네임을 입력하세요"
                maxLength={30}
              />
            ) : (
              <span className="info-value">
                {profile.nickname || '미설정'}
              </span>
            )}
          </div>

          {/* 성별 */}
          <div className="info-row">
            <label>성별</label>
            {isEditing ? (
              <div className="gender-buttons">
                <button
                  type="button"
                  className={formData.gender === true ? 'active' : ''}
                  onClick={() => handleGenderChange(true)}
                >
                  남성
                </button>
                <button
                  type="button"
                  className={formData.gender === false ? 'active' : ''}
                  onClick={() => handleGenderChange(false)}
                >
                  여성
                </button>
                <button
                  type="button"
                  className={formData.gender === null ? 'active' : ''}
                  onClick={() => handleGenderChange(null)}
                >
                  미설정
                </button>
              </div>
            ) : (
              <span className="info-value">
                {getGenderText()}
              </span>
            )}
          </div>

          {/* 나이 */}
          <div className="info-row">
            <label>나이</label>
            {isEditing ? (
              <input
                type="number"
                name="age"
                value={formData.age}
                onChange={handleInputChange}
                placeholder="나이를 입력하세요"
                min={0}
                max={120}
              />
            ) : (
              <span className="info-value">
                {profile.age ? `${profile.age}세` : '미설정'}
              </span>
            )}
          </div>

          {/* 가입일 (읽기 전용) */}
          <div className="info-row">
            <label>가입일</label>
            <span className="info-value readonly">
              {formatDate(profile.sign_up_date)}
            </span>
          </div>

          {/* 권한 (읽기 전용) */}
          <div className="info-row">
            <label>권한</label>
            <span className="info-value readonly">
              {profile.permission === 'admin' ? '관리자' : '일반 사용자'}
            </span>
          </div>
        </div>

        {/* ========== 버튼 섹션 ========== */}
        <div className="profile-actions">
          {isEditing ? (
            <>
              <button
                className="save-button"
                onClick={handleSave}
                disabled={isSaving}
              >
                {isSaving ? '저장 중...' : '저장'}
              </button>
              <button
                className="cancel-button"
                onClick={handleEditCancel}
                disabled={isSaving}
              >
                취소
              </button>
            </>
          ) : (
            <button
              className="edit-button"
              onClick={handleEditStart}
            >
              프로필 수정
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default Profile;

