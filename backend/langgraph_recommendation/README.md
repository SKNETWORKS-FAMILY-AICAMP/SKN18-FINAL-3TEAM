# LangGraph Recommendation

영상 키워드 및 추천 키워드 자동 생성 시스템

---

## 개요

프론트엔드에서 영상 생성 → DB 저장 → Celery로 비동기 키워드 생성 → DB 업데이트

**출력:**
- `video_keywords`: "경복궁,태조,창덕궁"
- `recommend_keywords`: "이성계,정도전,한양"

---

## 디렉토리 구조

```
backend/langgraph_recommendation/
├── README.md                    # 본 문서
├── DB_SETUP_GUIDE.md           # DB 컬럼 추가 안내 (상세)
├── state.py                    # State 정의
├── graph.py                    # 그래프 정의
├── tasks.py                    # Celery Task
└── nodes/
    ├── video_keyword_node.py   # Stage 1: Kiwi + TTL 매칭
    └── recommend_keyword_node.py # Stage 2: 의도파악 + Thread 병렬
```

---

## 작동 방식

### Stage 1: video_keyword 추출
1. Kiwi 형태소 분석 → 명사 추출
2. TTL 데이터 매칭
3. 결과: "키워드1,키워드2"

### Stage 2: recommend_keyword 추출
1. LLM 의도파악 (자동)
2. LLM 키워드 확장
3. TTL 엔티티 추출
4. Thread 병렬 실행 (outgoing/incoming/connected)
5. LLM이 상위 3-4개 선택
6. 결과: "추천1,추천2,추천3"

---

## 설치 및 설정

### 1. DB 컬럼 추가 (필수)

`infra/init.sql` 수정:
```sql
ALTER TABLE video
ADD COLUMN video_keywords TEXT DEFAULT '',
ADD COLUMN recommend_keywords TEXT DEFAULT '';
```

`backend/django/video/models.py` 수정:
```python
video_keywords = models.TextField(blank=True, default='')
recommend_keywords = models.TextField(blank=True, default='')
```

### 2. tasks.py 주석 해제 (필수)

`backend/langgraph_recommendation/tasks.py` 41-43줄, 62-64줄 주석 해제

### 3. Celery Worker 실행

```bash
celery -A backend.django.config worker --loglevel=info
```

---

## 테스트

### 로컬 테스트
```bash
cd backend/langgraph_recommendation
python graph.py
```

### 프론트엔드 통합
영상 생성 → Django 콘솔에서 "✓ 키워드 생성 Task 등록 완료" 확인 → DB 확인

---

## 주의사항

- DB 컬럼 추가 전까지 Celery Task는 DB 업데이트 안 함 (주석 처리됨)
- Celery Worker 미실행 시 키워드 생성 안 됨
- Redis 필수 (Celery broker)

---

## 문제 해결

**Celery Task 실행 안 됨:** Redis 및 Worker 실행 확인
**TTL 로드 실패:** `backend/langgraph_fuseki/ontology/instances/korean_history_instances.ttl` 경로 확인
**LLM 에러:** `.env`의 `OPENAI_API_KEY`, `OPENAI_MODEL` 확인

상세 가이드: [DB_SETUP_GUIDE.md](./DB_SETUP_GUIDE.md)
