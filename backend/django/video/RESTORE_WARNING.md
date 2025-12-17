# ⚠️ Video API 파일 복구 시 발생할 문제

## 📋 현재 수정된 파일들

1. **`serializers.py`** (새로 추가됨)
   - `VideoSerializer`: 영상 목록용
   - `VideoDetailSerializer`: 영상 상세용
   - `VideoCreateSerializer`: 영상 생성용

2. **`urls.py`** (수정됨)
   - 추가된 엔드포인트:
     - `GET /api/video/list/` - 영상 목록 조회
     - `GET /api/video/<id>/` - 영상 상세 조회

3. **`views.py`** (수정됨)
   - 추가된 뷰 클래스:
     - `VideoListView`
     - `VideoDetailView`

## 🚨 복구 시 발생할 문제

### 1. **프론트엔드 영상 페이지 완전 작동 불가**

#### MainPage (메인 페이지)
- **영향**: 영상 목록이 표시되지 않음
- **사용 API**: 
  - `GET /api/video/list/` (로그인 사용자)
- **증상**: 
  - "로딩 중..." 상태에서 멈춤
  - 또는 "영상이 없습니다" 메시지 표시
  - 콘솔에 `404 Not Found` 또는 `500 Internal Server Error` 발생

#### VideoDetailPage (영상 상세 페이지)
- **영향**: 영상 상세 정보를 불러올 수 없음
- **사용 API**: `GET /api/video/<id>/`
- **증상**:
  - "로딩 중..." 상태에서 멈춤
  - 영상 정보가 표시되지 않음
  - 콘솔에 `404 Not Found` 에러 발생


### 2. **에러 메시지**

복구 후 프론트엔드에서 다음과 같은 에러가 발생합니다:

```javascript
// 브라우저 콘솔 에러 예시
GET http://localhost:8000/api/video/list/ 404 (Not Found)
GET http://localhost:8000/api/video/1/ 404 (Not Found)
```

### 3. **영향받는 컴포넌트 목록**

| 컴포넌트 | 파일 경로 | 영향도 |
|---------|----------|--------|
| MainPage | `frontend/react/src/pages/MainPage.jsx` | 🔴 **치명적** - 메인 페이지 작동 불가 |
| VideoDetailPage | `frontend/react/src/pages/VideoDetailPage.jsx` | 🔴 **치명적** - 영상 상세 페이지 작동 불가 |

### 4. **기능별 영향 요약**

| 기능 | 상태 | 비고 |
|------|------|------|
| 메인 페이지 영상 목록 | ❌ 작동 불가 | 로그인/비로그인 모두 영향 |
| 영상 상세 페이지 | ❌ 작동 불가 | 영상 클릭 시 페이지 진입 불가 |
| 유니티 시나리오 생성 | ✅ 정상 작동 | `generate_scenario`는 영향 없음 |

## 💡 복구 전 확인 사항

1. **영상 담당자가 언제까지 수정할 예정인가?**
   - 복구 전에 일정을 확인하고, 그 전까지는 현재 버전 유지 권장

2. **프론트엔드 개발 중인가?**
   - 프론트엔드 개발 중이라면 복구하면 개발이 중단됨

3. **대안이 있는가?**
   - 복구 후에도 프론트엔드가 작동하려면 최소한의 API 엔드포인트는 필요함

## 🔧 복구 후 필요한 작업

영상 담당자가 수정을 완료하면, 다음 엔드포인트들이 반드시 구현되어야 합니다:

1. ✅ `GET /api/video/list/` - 영상 목록 조회
2. ✅ `GET /api/video/<id>/` - 영상 상세 조회

각 API는 다음 응답 형식을 반환해야 합니다:
```json
{
  "data": [...],
  "message": "ok"
}
```

## 📝 복구 명령어

복구를 진행하려면 다음 명령어를 실행하세요:

```bash
# urls.py와 views.py 복구
git restore backend/django/video/urls.py
git restore backend/django/video/views.py

# serializers.py 삭제 (새로 추가된 파일)
rm backend/django/video/serializers.py
```

**⚠️ 주의**: 복구 후 프론트엔드의 영상 관련 기능이 모두 작동하지 않습니다.

