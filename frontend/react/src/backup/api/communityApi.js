import api from "./axios";

/**
 * 커뮤니티 관련 API 함수들 (댓글, 답글, 좋아요)
 */

// ============================================
// 댓글 API
// ============================================

// 영상의 댓글 목록 조회
export const getVideoComments = async (videoId) => {
  const response = await api.get(`/api/community/videos/${videoId}/comments/`);
  return response.data;
};

// 댓글 작성
export const createComment = async (videoId, commentContent) => {
  const response = await api.post(
    `/api/community/videos/${videoId}/comments/`,
    {
      comment_content: commentContent,
    }
  );
  return response.data;
};

// 댓글 수정 (작성자 본인만)
export const updateComment = async (commentId, commentContent) => {
  const response = await api.patch(`/api/community/comments/${commentId}/`, {
    comment_content: commentContent,
  });
  return response.data;
};

// 댓글 삭제 (작성자 본인 또는 관리자)
export const deleteComment = async (commentId) => {
  const response = await api.delete(`/api/community/comments/${commentId}/delete/`);
  return response.data;
};

// ============================================
// 답글 API
// ============================================

// 댓글의 답글 목록 조회
export const getCommentReplies = async (commentId) => {
  const response = await api.get(
    `/api/community/comments/${commentId}/replies/`
  );
  return response.data;
};

// 답글 작성
export const createReply = async (
  commentId,
  replyContent,
  parentReplyId = null
) => {
  const data = {
    reply_content: replyContent,
  };
  if (parentReplyId) {
    data.parent_reply = parentReplyId;
  }
  const response = await api.post(
    `/api/community/comments/${commentId}/replies/`,
    data
  );
  return response.data;
};

// 답글 수정 (작성자 본인만)
export const updateReply = async (replyId, replyContent) => {
  const response = await api.patch(`/api/community/replies/${replyId}/update/`, {
    reply_content: replyContent,
  });
  return response.data;
};

// 답글 삭제 (작성자 본인 또는 관리자)
export const deleteReply = async (replyId) => {
  const response = await api.delete(`/api/community/replies/${replyId}/`);
  return response.data;
};

// ============================================
// 좋아요 API
// ============================================

// 영상 좋아요 추가
export const likeVideo = async (videoId) => {
  const response = await api.post(`/api/community/videos/${videoId}/like/`);
  return response.data;
};

// 영상 좋아요 삭제
export const unlikeVideo = async (videoId) => {
  const response = await api.delete(`/api/community/videos/${videoId}/like/`);
  return response.data;
};

// 댓글 좋아요 추가
export const likeComment = async (commentId) => {
  const response = await api.post(`/api/community/comments/${commentId}/like/`);
  return response.data;
};

// 댓글 좋아요 삭제
export const unlikeComment = async (commentId) => {
  const response = await api.delete(
    `/api/community/comments/${commentId}/like/`
  );
  return response.data;
};

// 답글 좋아요 추가
export const likeReply = async (replyId) => {
  const response = await api.post(`/api/community/replies/${replyId}/like/`);
  return response.data;
};

// 답글 좋아요 삭제
export const unlikeReply = async (replyId) => {
  const response = await api.delete(`/api/community/replies/${replyId}/like/`);
  return response.data;
};

// ============================================
// 내 활동 API
// ============================================

// 내 커뮤니티 활동 내역 조회
export const getMyActivity = async () => {
  const response = await api.get("/api/community/me/activities/");
  return response.data;
};


// ============================================
// Celery Task 상태 확인 API
// ============================================

// Celery task 상태 확인
export const checkTaskStatus = async (taskId) => {
  const response = await api.get(`/api/community/tasks/${taskId}/status/`);
  return response.data;
};
