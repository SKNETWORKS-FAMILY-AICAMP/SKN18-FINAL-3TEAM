# DB 컬럼 추가 안내

영상 키워드 및 추천 키워드 기능을 활성화하려면 `video` 테이블에 2개의 컬럼을 추가해야 합니다.

---

## 1. DB 스키마 변경 (init.sql)

`infra/init.sql` 파일에서 `video` 테이블에 다음 컬럼 추가:

```sql
-- video 테이블에 컬럼 추가
ALTER TABLE video
ADD COLUMN video_keywords TEXT DEFAULT '',
ADD COLUMN recommended_keywords TEXT DEFAULT '';

-- 또는 CREATE TABLE 시점에 포함:
CREATE TABLE IF NOT EXISTS video (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    video_url TEXT,
    upload_date TIMESTAMP DEFAULT NOW(),
    tags TEXT[],
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    thumbnail_url TEXT,

    -- 🆕 추가할 컬럼
    video_keywords TEXT DEFAULT '',          -- 영상 제목에서 추출한 키워드 (콤마 구분)
    recommended_keywords TEXT DEFAULT ''       -- 추천 키워드 (콤마 구분)
);
```

---

## 2. Django 모델 수정

`backend/django/video/models.py` 파일 수정:

```python
class Video(models.Model):
    # ... 기존 필드 ...

    # 🆕 추가할 필드
    video_keywords = models.TextField(
        blank=True,
        default='',
        verbose_name='영상 키워드',
        help_text='영상 제목에서 추출한 키워드 (콤마 구분)'
    )
    recommended_keywords = models.TextField(
        blank=True,
        default='',
        verbose_name='추천 키워드',
        help_text='관계 기반 추천 키워드 (콤마 구분)'
    )
```

---

## 3. Celery Task 주석 해제

`backend/langgraph_recommendation/tasks.py` 파일에서 주석 해제:

### 위치 1: 정상 실행 시 DB 업데이트 (41-43번째 줄)

```python
Video.objects.filter(id=video_id).update(
    video_keywords=video_keywords,              # ⬅️ 주석 해제
    recommended_keywords=recommended_keywords       # ⬅️ 주석 해제
)
```

### 위치 2: 에러 시 빈 문자열 업데이트 (62-64번째 줄)

```python
Video.objects.filter(id=video_id).update(
    video_keywords="",              # ⬅️ 주석 해제
    recommended_keywords=""           # ⬅️ 주석 해제
)
```

---

## 4. 마이그레이션 (Django managed=True인 경우)

만약 Django에서 테이블을 관리한다면 (`managed=True`):

```bash
# 마이그레이션 파일 생성
python manage.py makemigrations video

# 마이그레이션 실행
python manage.py migrate video
```

---

## 5. Celery Worker 실행

Celery Worker가 실행 중이 아니라면 시작:

```bash
# 터미널에서 실행 (Django 프로젝트 루트에서)
celery -A backend.django.config worker --loglevel=info
```

Docker 환경이라면 `docker-compose.yml`에 celery worker 서비스 추가:

```yaml
celery-worker:
  build:
    context: ..
    dockerfile: backend/Dockerfile
  container_name: celery_worker
  env_file:
    - ../.env
  command: celery -A backend.django.config worker --loglevel=info
  depends_on:
    - redis
    - postgres
  volumes:
    - ../backend:/app/backend
```

---

## 6. 테스트

### 로컬 테스트 (graph.py 직접 실행)

```bash
cd backend/langgraph_recommendation
python graph.py
```

예상 출력:

```
[Stage 1] Video Keyword Extraction
  영상 제목: '경복궁을 지은 왕'
  Kiwi 추출 키워드: ['경복궁', '왕']
  최종 video_keywords: 경복궁,왕

[Stage 2] Recommend Keyword Generation
  Thread 병렬 실행...
  최종 추천: ['태조', '창덕궁', '세종']

결과:
video_keywords: 경복궁,왕
recommended_keywords: 태조,창덕궁,세종
```

### 프론트엔드 통합 테스트

1. 프론트엔드에서 영상 생성 요청
2. Django 콘솔에서 확인:
   ```
   ✓ 키워드 생성 Task 등록 완료: video_id=123, task_id=abc-def-ghi
   ```
3. Celery Worker 콘솔에서 실행 로그 확인
4. DB에서 `video_keywords`, `recommended_keywords` 컬럼 확인

---

## 7. 데이터 형식

### video_keywords

```
"경복궁,태조,창덕궁"
```

### recommended_keywords

```
"이성계,정도전,한양"
```

### 사용 예시 (프론트엔드)

```javascript
// DB에서 조회한 영상 데이터
const video = {
  id: 123,
  title: "경복궁을 지은 왕",
  video_keywords: "경복궁,태조,창덕궁",
  recommended_keywords: "이성계,정도전,한양",
};

// 추천 키워드를 배열로 변환
const recommendTags = video.recommended_keywords.split(",");
// ["이성계", "정도전", "한양"]

// 검색창 드롭다운에 표시
recommendTags.forEach((tag) => {
  // 실제 DB에 해당 태그를 가진 영상이 있는지 확인 후 표시
});
```

---

## 문제 해결

### Celery Task가 실행되지 않음

1. Redis 실행 확인:

   ```bash
   redis-cli ping  # PONG 응답 확인
   ```

2. Celery Worker 실행 확인:

   ```bash
   ps aux | grep celery
   ```

3. Celery 로그 확인:
   ```bash
   tail -f celery_worker.log
   ```

### TTL 파일 로드 실패

- `backend/langgraph_fuseki/ontology/instances/korean_history_instances.ttl` 파일 존재 확인
- 파일 경로가 올바른지 확인

### LLM API 에러

- `.env` 파일에 `OPENAI_API_KEY` 설정 확인
- `OPENAI_MODEL` 환경변수 확인 (예: `gpt-4o-mini`)

---

## 컬럼명 변경 시 수정 필요 파일

만약 컬럼명을 `video_keywords` / `recommended_keywords`가 아닌 다른 이름으로 정하면:

1. `backend/langgraph_recommendation/tasks.py` (2곳)
2. `backend/django/video/models.py`
3. `infra/init.sql`

---

## 담당자 인수인계 체크리스트

- [ ] `infra/init.sql`에 컬럼 추가 완료
- [ ] `backend/django/video/models.py`에 필드 추가 완료
- [ ] `backend/langgraph_recommendation/tasks.py` 주석 해제 완료
- [ ] Celery Worker 실행 중
- [ ] Redis 실행 중
- [ ] 로컬 테스트 성공 (graph.py 직접 실행)
- [ ] 프론트엔드 통합 테스트 성공
- [ ] DB에서 키워드 데이터 확인 완료
