/**
 * VideoForm.jsx
 *
 * 영상 업로드/수정 페이지 (관리자 전용)
 * - 영상 생성
 * - 영상 수정
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getVideo, createVideo, updateVideo, deleteVideo } from '../api/videoApi';
import './VideoForm.css';

function VideoForm() {
  const { videoId } = useParams(); // 수정 모드일 때만 존재
  const navigate = useNavigate();
  const isEditMode = Boolean(videoId);

  const [formData, setFormData] = useState({
    title: '',
    tags: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isEditMode) {
      loadVideo();
    }
  }, [videoId]);

  const loadVideo = async () => {
    try {
      setLoading(true);
      const response = await getVideo(videoId);
      const video = response.data;
      setFormData({
        title: video.title,
        tags: video.tags ? video.tags.join(', ') : '',
      });
      setError(null);
    } catch (err) {
      console.error('영상 로드 실패:', err);
      setError('영상을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.title.trim()) {
      alert('영상 제목을 입력해주세요.');
      return;
    }

    try {
      setLoading(true);

      // 태그를 배열로 변환 (콤마로 구분)
      const tagsArray = formData.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter((tag) => tag.length > 0);

      const videoData = {
        title: formData.title,
        tags: tagsArray,
      };

      if (isEditMode) {
        // 수정
        await updateVideo(videoId, videoData);
        alert('영상이 수정되었습니다.');
        navigate(`/videos/${videoId}`);
      } else {
        // 생성
        const response = await createVideo(videoData);
        alert('영상이 업로드되었습니다.');
        navigate(`/videos/${response.data.id}`);
      }
    } catch (err) {
      console.error('영상 저장 실패:', err);
      alert(err.response?.data?.error?.message || '영상 저장에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('정말로 이 영상을 삭제하시겠습니까?')) {
      return;
    }

    try {
      setLoading(true);
      await deleteVideo(videoId);
      alert('영상이 삭제되었습니다.');
      navigate('/videos');
    } catch (err) {
      console.error('영상 삭제 실패:', err);
      alert('영상 삭제에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  if (loading && isEditMode) {
    return (
      <div className="video-form-container">
        <div className="loading">로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="video-form-container">
        <div className="error">{error}</div>
        <button onClick={() => navigate('/admin')}>관리자 페이지로</button>
      </div>
    );
  }

  return (
    <div className="video-form-container">
      <header className="form-header">
        <h1>{isEditMode ? '영상 수정' : '영상 업로드'}</h1>
        <button onClick={() => navigate('/admin')}>관리자 페이지로</button>
      </header>

      <form className="video-form" onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="title">영상 제목 *</label>
          <input
            type="text"
            id="title"
            name="title"
            value={formData.title}
            onChange={handleInputChange}
            placeholder="영상 제목을 입력하세요"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="tags">태그</label>
          <input
            type="text"
            id="tags"
            name="tags"
            value={formData.tags}
            onChange={handleInputChange}
            placeholder="태그를 콤마로 구분하여 입력하세요 (예: 역사, 조선시대, 세종대왕)"
          />
          <small className="form-hint">
            태그는 콤마(,)로 구분하여 입력해주세요.
          </small>
        </div>

        <div className="form-actions">
          <button type="submit" className="submit-btn" disabled={loading}>
            {loading ? '저장 중...' : isEditMode ? '수정하기' : '업로드하기'}
          </button>

          {isEditMode && (
            <button
              type="button"
              className="delete-btn"
              onClick={handleDelete}
              disabled={loading}
            >
              삭제하기
            </button>
          )}

          <button
            type="button"
            className="cancel-btn"
            onClick={() => navigate(-1)}
            disabled={loading}
          >
            취소
          </button>
        </div>
      </form>
    </div>
  );
}

export default VideoForm;
