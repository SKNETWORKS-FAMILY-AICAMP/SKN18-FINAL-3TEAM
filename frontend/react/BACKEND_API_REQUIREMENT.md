# 백엔드 API 요구사항

## 1. 영상 좋아요 상태 확인

**프론트엔드 구현 완료:**

- 영상 상세 페이지에서 좋아요 하트 클릭 시 색상 표시/토글
- 좋아요 개수 실시간 업데이트
- localStorage로 상태 유지 (임시)

**백엔드 추가 필요:**

- `GET /api/video/{video_id}/` 응답에 `is_liked: boolean` 필드 추가
- 로그인한 사용자의 경우 해당 영상에 좋아요를 눌렀는지 여부 반환
- 비로그인 사용자는 `false` 반환

**연결 위치:**

- `frontend/react/src/pages/VideoDetailPage.jsx` - 비디오 정보 로드 시 `is_liked` 사용
