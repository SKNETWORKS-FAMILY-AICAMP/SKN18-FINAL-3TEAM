# ⚠️ Activity & Community API 파일 복구 시 발생할 문제

## 📋 현재 수정된 파일들

1. **`backend/django/activity/views.py`** (수정됨)
   - 변경사항: `context={'request': request}` 추가
   - 영향: Serializer에서 request context를 사용하는 경우 문제 발생

2. **`backend/django/community/serializers.py`** (수정됨)
   - 주요 변경사항:
     - `CommentUserSerializer` 추가 (사용자 정보 객체화)
     - `user_email`, `user_nickname` → `user` 객체로 변경
     - `replies` 필드 추가 (댓글에 답글 포함)
     - `is_liked` 필드 추가 (좋아요 여부)
     - `child_replies` 필드 추가 (답글의 중첩 답글)
     - `likes_count` 필드 추가 (답글 좋아요 수)

3. **`backend/django/community/views.py`** (수정됨)
   - 주요 변경사항:
     - `prefetch_related('replies__user', 'likes')` 추가 (성능 최적화)
     - `context={'request': request}` 추가 (Serializer에 request 전달)
     - 답글 조회 시 `parent_reply__isnull=True` 필터 추가 (최상위 답글만)

## 🚨 복구 시 발생할 문제

### 1. **댓글/답글 데이터 구조 불일치 (치명적)**

#### 문제: 사용자 정보 필드 변경
- **현재**: `user` 객체 (`{id, nickname, email, profile_image, display_name}`)
- **복구 후**: `user_email`, `user_nickname` (평면 구조)

**영향받는 컴포넌트:**
- `Comment.jsx` (라인 595-598)
- `CommentSection.jsx` (라인 36-37)
- `VideoDetailPage.jsx` (라인 95)

**증상:**
```javascript
// 현재 코드 (정상 작동)
comment.user?.nickname || comment.user?.display_name

// 복구 후 (에러 발생)
comment.user_email  // undefined - user 객체가 없음
comment.user_nickname  // undefined - user 객체가 없음
```

**에러 메시지:**
- 콘솔: `Cannot read property 'nickname' of undefined`
- 화면: 댓글 작성자 이름이 "사용자"로만 표시됨
- 프로필 이미지가 표시되지 않음

#### 문제: 답글 중첩 구조 변경
- **현재**: `comment.replies` 배열에 답글이 포함됨
- **복구 후**: `replies` 필드가 없음

**영향받는 컴포넌트:**
- `Comment.jsx` (라인 428, 732-755)
- `VideoDetailPage.jsx` (라인 93)

**증상:**
```javascript
// 현재 코드 (정상 작동)
const [replies, setReplies] = useState(comment.replies || []);

// 복구 후 (문제 발생)
comment.replies  // undefined - 필드가 없음
// 답글이 전혀 표시되지 않음
```

#### 문제: 좋아요 상태 필드 변경
- **현재**: `is_liked` 필드로 좋아요 여부 확인
- **복구 후**: `is_liked` 필드가 없음

**영향받는 컴포넌트:**
- `Comment.jsx` (라인 429, 468-482)
- `ReplyItem` (라인 65, 121-124)

**증상:**
```javascript
// 현재 코드 (정상 작동)
const [liked, setLiked] = useState(comment.is_liked || false);

// 복구 후 (문제 발생)
comment.is_liked  // undefined - 필드가 없음
// 좋아요 상태가 항상 false로 표시됨
```

#### 문제: 답글 중첩 구조 (child_replies)
- **현재**: `reply.child_replies` 배열로 중첩 답글 지원
- **복구 후**: `child_replies` 필드가 없음

**영향받는 컴포넌트:**
- `ReplyItem` (라인 64, 386-410)

**증상:**
```javascript
// 현재 코드 (정상 작동)
const [childReplies, setChildReplies] = useState(reply.child_replies || []);

// 복구 후 (문제 발생)
reply.child_replies  // undefined - 필드가 없음
// 중첩 답글이 표시되지 않음 (답글의 답글 기능 작동 불가)
```

#### 문제: 답글 좋아요 수 필드
- **현재**: `reply.likes_count` 필드로 좋아요 수 표시
- **복구 후**: `likes_count` 필드가 없음

**영향받는 컴포넌트:**
- `ReplyItem` (라인 66, 312)

**증상:**
```javascript
// 현재 코드 (정상 작동)
const [likesCount, setLikesCount] = useState(reply.likes_count || 0);

// 복구 후 (문제 발생)
reply.likes_count  // undefined - 필드가 없음
// 답글 좋아요 수가 항상 0으로 표시됨
```

### 2. **API 응답 구조 불일치**

#### 문제: Serializer Context 누락
- **현재**: `context={'request': request}` 전달
- **복구 후**: context가 없음

**영향:**
- `is_liked` 필드 계산 불가 (request.user 필요)
- 좋아요 상태가 항상 false로 표시됨

#### 문제: 답글 조회 필터 변경
- **현재**: `parent_reply__isnull=True` (최상위 답글만)
- **복구 후**: 모든 답글 반환

**영향:**
- 답글 중복 표시 가능성
- 답글 트리 구조가 깨질 수 있음

### 3. **성능 문제**

#### 문제: prefetch_related 누락
- **현재**: `prefetch_related('replies__user', 'likes')` 사용
- **복구 후**: prefetch_related 없음

**영향:**
- N+1 쿼리 문제 발생
- 댓글/답글 로딩 속도 저하
- 서버 부하 증가

### 4. **시청/검색 기록 API 문제**

#### 문제: Serializer Context 누락
- **현재**: `context={'request': request}` 전달
- **복구 후**: context가 없음

**영향:**
- Serializer에서 request를 사용하는 경우 에러 발생 가능
- 사용자 정보 관련 필드 처리 문제

## 📊 영향받는 기능 요약

| 기능 | 상태 | 비고 |
|------|------|------|
| 댓글 작성자 이름 표시 | ❌ 작동 불가 | user 객체가 없어서 undefined |
| 댓글 프로필 이미지 | ❌ 작동 불가 | user 객체가 없어서 undefined |
| 답글 표시 | ❌ 작동 불가 | replies 필드가 없음 |
| 중첩 답글 (답글의 답글) | ❌ 작동 불가 | child_replies 필드가 없음 |
| 댓글 좋아요 상태 | ❌ 작동 불가 | is_liked 필드가 없음 |
| 답글 좋아요 상태 | ❌ 작동 불가 | is_liked 필드가 없음 |
| 답글 좋아요 수 | ❌ 작동 불가 | likes_count 필드가 없음 |
| 댓글 좋아요 기능 | ⚠️ 부분 작동 | API는 작동하지만 상태 표시 불가 |
| 답글 좋아요 기능 | ⚠️ 부분 작동 | API는 작동하지만 상태 표시 불가 |
| 댓글 작성 | ✅ 정상 작동 | API는 정상 작동 |
| 답글 작성 | ✅ 정상 작동 | API는 정상 작동 |
| 댓글 삭제 | ✅ 정상 작동 | API는 정상 작동 |
| 답글 삭제 | ✅ 정상 작동 | API는 정상 작동 |

## 🔧 복구 후 필요한 수정사항

### 프론트엔드 수정 필요 (복구 후)

1. **Comment.jsx 수정 필요:**
```javascript
// 현재 (복구 후 작동 안 함)
comment.user?.nickname

// 수정 필요
comment.user_nickname || comment.user_email?.split("@")[0]
```

2. **Comment.jsx - replies 처리:**
```javascript
// 현재 (복구 후 작동 안 함)
const [replies, setReplies] = useState(comment.replies || []);

// 수정 필요
// replies 필드가 없으므로 별도 API 호출 필요
```

3. **ReplyItem - child_replies 처리:**
```javascript
// 현재 (복구 후 작동 안 함)
const [childReplies, setChildReplies] = useState(reply.child_replies || []);

// 수정 필요
// child_replies 필드가 없으므로 별도 처리 필요
```

4. **is_liked 처리:**
```javascript
// 현재 (복구 후 작동 안 함)
const [liked, setLiked] = useState(comment.is_liked || false);

// 수정 필요
// 항상 false로 초기화하거나 별도 API 호출 필요
```

## 💡 복구 전 확인 사항

1. **프론트엔드 댓글 기능이 현재 정상 작동 중인가?**
   - 복구하면 댓글/답글 표시가 완전히 깨집니다

2. **영상 담당자가 언제까지 수정할 예정인가?**
   - 복구 전에 일정을 확인하고, 그 전까지는 현재 버전 유지 권장

3. **대안이 있는가?**
   - 복구 후에도 프론트엔드가 작동하려면 최소한의 필드는 필요함

## 📝 복구 명령어

복구를 진행하려면 다음 명령어를 실행하세요:

```bash
# activity/views.py 복구
git restore backend/django/activity/views.py

# community/serializers.py 복구
git restore backend/django/community/serializers.py

# community/views.py 복구
git restore backend/django/community/views.py
```

**⚠️ 주의**: 복구 후 프론트엔드의 댓글/답글 관련 기능이 모두 작동하지 않습니다. 프론트엔드 코드도 함께 수정해야 합니다.

## 🔄 복구 후 예상 에러 메시지

### 브라우저 콘솔 에러:
```javascript
// 1. 사용자 정보 접근 에러
TypeError: Cannot read property 'nickname' of undefined
TypeError: Cannot read property 'display_name' of undefined
TypeError: Cannot read property 'profile_image' of undefined

// 2. 답글 필드 접근 에러
TypeError: Cannot read property 'replies' of undefined
TypeError: Cannot read property 'child_replies' of undefined

// 3. 좋아요 필드 접근 에러
// (에러는 없지만 기능이 작동하지 않음)
```

### 화면에서 보이는 문제:
- ✅ 댓글 작성/삭제는 작동
- ❌ 댓글 작성자 이름이 "사용자"로만 표시
- ❌ 프로필 이미지가 표시되지 않음
- ❌ 답글이 전혀 표시되지 않음
- ❌ 좋아요 상태가 항상 비활성화로 표시
- ❌ 좋아요 수가 표시되지 않음

