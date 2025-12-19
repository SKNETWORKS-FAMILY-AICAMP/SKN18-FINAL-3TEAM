# SKN18-FINAL-3TEAM
## AI 기반 인플루언서

## 프로젝트 구조

```text
SKN18-FINAL-3TEAM/
├─ backend/                    # 서버/데이터 파이프라인 코드
│  ├─ db_pipeline/             # 데이터 적재·임베딩 ETL (neo4j, vectordb)
│  ├─ django/                  # REST API (activity, community, search, users, video)
│  ├─ inference_engine/        # 규칙 기반 추론 엔진
│  ├─ langgraph_fuseki/        # KG+LangGraph 워크플로우
│  ├─ langgraph_structure1/    # LangGraph 실험 구조 1
│  ├─ langgraph_structure2/    # LangGraph 실험 구조 2
│  ├─ llm_fine_tuning/         # LLM 파인튜닝 산출물/실험
│  └─ ragas/                   # RAG 평가 스크립트
├─ frontend/                   # 클라이언트 자산
│  ├─ 3d_modeling/             # Unity 3D 프로젝트
│  ├─ react/                   # Vite+React 웹 앱
│  └─ video_pipeline/          # 영상 생성 파이프라인
├─ infra/                      # 로컬/배포 인프라
│  ├─ docker-compose.yml       # DB/서비스 컨테이너 오케스트레이션
│  ├─ init.sql                 # DB 초기화 스크립트
│  └─ nginx.conf               # 리버스 프록시 설정
├─ main.py                     # 로컬 실행/유틸 스크립트
├─ pyproject.toml              # 파이썬 프로젝트 설정
├─ requirements.txt            # 공용 파이썬 의존성
└─ .env.example                # 환경 변수 예시
```

# Frontend

## react (Vite)
- `/src/api` : `axios.js` 기반 공용 클라이언트, activity/admin/auth/community/video API 래퍼.
- `/src/components` : `common`(GlassSurface, Icons 등), `layout`(Header 등 전역 레이아웃).
- `/src/constants` : 테마/색상 상수(`theme.js`).
- `/src/features` : 도메인 묶음(search/user/video). 하위 `components`로 UI 구성.
- `/src/pages` : `MainPage`, `MyPage`, `VideoDetailPage`, `AllCommentsPage`, `ProfileEditPage`.
- `/src/shared` : 재사용 헤더(`Header.tsx`, 스타일) 등 공용 컴포넌트.
- `/src/utils` : 이미지 처리 유틸(`imageUtils.js`).
- 빌드/설정: `vite.config.js`, `eslint.config.js`, `package.json`.

# Backend

## django (REST API)
- 도메인 앱:
  - `activity` : 검색 기록·시청 기록 조회/적재(ListCreate API).
  - `community` : 영상 댓글/대댓글/좋아요, 작성자·관리자 삭제 권한 포함.
  - `search` : 스켈레톤(모델만 존재, 뷰 TODO).
  - `users` : 인증 상태 확인, 로그아웃/회원탈퇴, 프로필 조회·수정, 관리자용 회원 관리.
  - `video` : 영상 목록/상세 조회, OpenAI 기반 시나리오 생성 API(`generate_scenario`, 더미 응답 지원).
- 공통 설정: `config/settings.py`, `config/urls.py`; 관리 스크립트 `manage.py`.
- 각 앱별 `models.py`, `serializers.py`, `views.py`, `urls.py`로 CRUD/비즈니스 로직 구현.

### API 구현 현황 

- **회원/인증 (`users`)**
  - 인증 상태 확인 `GET /api/users/check-auth/`(JWT 또는 세션) → `check_auth`.
  - 로그아웃 `POST /api/users/logout/`(세션 로그아웃) → `logout_view`.
  - 회원탈퇴 `DELETE /api/users/delete-account/`(Google 토큰 revoke 후 삭제) → `delete_account`.
  - JWT 발급/리프레시/검증 `POST /api/users/token/`, `/token/refresh/`, `/token/verify/` (SimpleJWT 기본 뷰).
  - 프로필 조회/수정 `GET|PATCH /api/users/profile/`(Redis 캐시), 프로필 이미지 업로드/삭제 `POST|DELETE /api/users/profile/image/`.
  - 관리자: 회원 목록/상세/수정/삭제 `GET /api/users/admin/`, `GET /api/users/admin/<id>/`, `PATCH /api/users/admin/<id>/update/`, `DELETE /api/users/admin/<id>/delete/` (권한 `permission='admin'`).
- **활동 (`activity`)**
  - 검색 기록 조회/적재 `GET|POST /api/activity/search-logs/`(사용자별 `search_history`).
  - 시청 기록 조회/적재 `GET|POST /api/activity/watch-logs/`(비디오 FK, 태그, 시청 위치 포함).
- **커뮤니티 (`community`)**
  - 댓글 목록/작성 `GET|POST /api/community/videos/<video_id>/comments/`.
  - 댓글 수정/삭제 `PATCH /api/community/comments/<comment_id>/`, `DELETE /api/community/comments/<comment_id>/delete/` (작성자 또는 관리자).
  - 답글 목록/작성 `GET|POST /api/community/comments/<comment_id>/replies/`; 
  - 답글 삭제 `DELETE /api/community/replies/<reply_id>/` (작성자 또는 관리자).  
  - 답글 수정(`PATCH /api/community/replies/<reply_id>/update/`).
  - 좋아요: 영상 `POST|DELETE /api/community/videos/<video_id>/like/`, 댓글 `POST|DELETE /api/community/comments/<comment_id>/like/`, 답글 `POST|DELETE /api/community/replies/<reply_id>/like/`.
  - 내 활동 내역 `GET /api/community/me/activities/`(내 댓글·답글·좋아요 묶음).
- **영상 (`video`)**
  - 목록/상세 `GET /api/video/list/`(기본 최신순, `sort=comments` 지원, `tag` 필터) / `GET /api/video/<id>/`.
  - 시나리오 생성 `POST /api/video/generate/` → OpenAI(`gpt-4o-mini`) 호출 또는 `CHAT_USE_FAKE_COMPILE=True` 시 더미 JSON 저장·반환. GET은 허용하지 않음.
- **검색 (`search`)**
  - URL 스켈레톤만 존재, 실제 API 뷰는 아직 없음.

  ## 향후 계획 
  - 스케쥴러를 이용한 DB 적재 블랙리스트 토큰 관리 방식 구현
  - 검색 기능 추가 예정
  - 

## db_pipeline (ETL)
- `common/` : `config.py` 설정, `embedding_model.py`, `transform.py`, `load_raw_data.py`.
- `data/` : 전처리 데이터(`encykorea_cleaned6.csv`, `transformed_chunks.json`).
- `neo4j/`, `vectordb/` : 그래프/벡터 DB 적재 ETL 및 서비스 코드.

## inference_engine
- 규칙 기반 추론 엔진; `rules/`(all_rules.rules 등)와 `reasoner/` 자바 기반 실행(pom.xml, run_reasoner.sh).

## langgraph_fuseki
- LangGraph 워크플로우 + Fuseki KG.
- `nodes/` : classify, generate, semantic/entity expander 등 노드 구현.
- `docs/` : 온톨로지/쿼리 가이드, README, SETUP.
- `ontology/` : KG 스키마/인스턴스, 스크립트.
- `utils/` : triple generator 등 유틸.

## langgraph_structure1 / langgraph_structure2
- LangGraph 대안 구조 실험 (Neo4j, RAG). `graphdb/`, `nodes/`, `rag/`, `state.py` 등으로 구성.

## llm_fine_tuning
- LLM 말투/영어 파인튜닝 산출물/실험 공간.

## ragas
- RAG 품질 평가 스크립트(`build_queries_persona.py`, `neo4j/ragas_eval.py` 등).

# LangGraph
- Graph db를 보완하기 위해 vectordb 사용함
- Graph db를 탐색이 되면면 확실히 답변의 품질은 좋은데 잘 탐색이 잘 되지 않음

- 우리가 hybrid 구조를 택한 이유
Vectordb와 Graph db를 따로 사용해봤더니 
상호 보완적인 결과가 나와 하이브리드로 사용.

<img src="./제목 없음1.png"/>



## 전체적인 Langgrph 구조

- 각 그래프의 classify가 다름 
a = 병렬 그래프, hybrid 또는 end 로 가는 역할
b = vector로 갈지 graph, end 로 갈지 정하는 역할 - 간단한 질의에 대해서는 vector, 인물 관계, 연대기 등은 graph로 감 

a는 비동기 병렬로 가서 답변 생성 단계에서 유사도 점수로 sorting 하고
b는  vectordb 에서 filtered_k = 5 추출 후 cos 유사도 점수 기준으로 걸러낸 청크에서 top k=3만 추출 evaluation 단계에서 llm 으로 청크를 평가, 기준 미만시 graph db 노드로 이동

공통 : vector db 이전에 질의를 임베딩 하는데 kiwi로 키워드 추출 후에 함께 임베딩, 다중 키워드 추출 시 and 조건으로 둘 다 해당해야 답변 뽑히도록

graphdb로 가면 neo4j를 위한 cypher 생성, neo4j 테스트를 거쳐 2-3hop
5 hop 까지 테스트를 함 ,각 hop 마다 시간 평균/ 토큰 평균 이 나옴 

| hop 개수 | relevancy | faithfulness | Time_avg | Time_stv | Token_avg | Token_stv |
|----------|-----------|--------------|----------|----------|-----------|-----------|
| 1hop     | 0.842     | 0.879        | 34.706   | 46.07    | 3674.982  | 1358.303  |
| 2hop     | 0.915     | 0.835        | 24.924   | 9.672    | 3742.2    | 1076.428  |
| 3hop     | 0.859     | 0.845        | 21.87    | 8.68     | 4333.95   | 999.47    |
| 4hop     | 0.861     | 0.849        | 29.032   | 12.464   | 4101.725  | 1323.323  |
| 5hop     | 0.883     | 0.859        | 25.932   | 25.09    | 3970.9    | 1221.093  |


hop를 너무 늘리면 데이터가 많아서 할루시네이션도 생김
--> 일정 이상 늘리면 시간도 줄어듦
--> hop이 적어도 데이터가 너무 적어서 그 안에서 답을 내려고 시간이 걸림
--> hop이 너무 많으면 데이터가 많어서 요약하는 데에 시간이 걸림

테스트 결과가 2-3hop이 가장 좋아서 지금 1hop으로 랭그래프 구현되어있는 것을 2-3hop으로 변경 예정 

생성된 답변 바탕으로 llm 챗봇 답변과 영상 스크립트 생성 진행 
-> state 에 tag를 달아서 tag가 chat 일때 챗봇으로 , tag가 video일때 영상 스크립트 노드까지 진행


 


# Unity
## 2. 시스템 아키텍처 (System Architecture)

LLM 서버로부터 받은 비정형 텍스트 데이터를 구조화된 JSON으로 변환하여 유니티 클라이언트가 해석하는 구조입니다.

```
graph TD
    User[사용자 입력] -->|주제 전송| Client[LLMClient (Unity)]
    Client -->|API Request| Server[LangGraph Server]
    Server -->|Generate JSON| Client
    Client -->|Scenario Data| Director[Director Controller]
    
    subgraph "Unity Presentation Layer"
        Director -->|Action & Gaze| Actor[Actor Controller]
        Director -->|Pitch Variation| Audio[Audio Manager]
        Director -->|Camera Shot| Cam[Camera Manager]
    end
```

## 3. 핵심 기술 구현 (Core Technical Implementation)

A. 생성형 AI 연동 및 데이터 캐싱 (LLMClient)
서버 비용 절감과 사용자 경험(UX) 개선을 위해 스마트 캐싱 및 리플레이 시스템을 구축했습니다.

- 구현 내용: LLMClient는 서버로부터 받은 시나리오 JSON을 로컬 메모리에 캐싱합니다. 사용자가 내용을 다시 보고 싶을 때, 서버에 재요청하지 않고 캐싱된 데이터를 DirectorController에 즉시 주입하여 대기 시간 없는 리플레이를 구현했습니다.

- Context Injection: 현재 클라이언트가 보유한 에셋 정보(Context)를 요청 시 함께 전송하여, LLM이 존재하지 않는 리소스를 호출하는 환각 현상을 1차적으로 억제했습니다.

B. LLM 환각(Hallucination) 방지 알고리즘 (DirectorController)
LLM이 사전 정의된 태그(예: Joy) 대신 유사한 단어(예: Joyful, Happy)를 출력하거나 오타를 냈을 때, 연극이 멈추지 않도록 **이중 안전장치(Fail-safe)**를 구현했습니다.

- Levenshtein Distance (편집 거리 알고리즘): 입력된 태그와 가장 철자가 비슷한 애니메이션을 찾아 자동으로 연결합니다.

- Keyword Fallback: 유사도 검색도 실패할 경우, 단어에 포함된 감정 키워드(Smile, Angry 등)를 분석해 해당 감정의 대표 동작으로 매핑합니다.


C. 자연스러운 시선 처리를 위한 S-Curve IK (ActorController)
캐릭터가 로봇처럼 딱딱하게 고개를 돌리는 'Uncanny Valley' 현상을 해결하기 위해, AnimationCurve를 활용한 S-Curve 시선 제어 시스템을 개발했습니다.

- 구현 내용: 단순히 Lerp로 시선을 이동하는 대신, Slow-Fast-Slow 형태의 가속도가 적용된 커브를 사용하여 사람처럼 자연스러운 눈동자와 머리의 움직임을 구현했습니다. 또한 고개 회전 각도가 한계치(Clamp)를 넘으면 몸통(Body)이 함께 회전하도록 하여 사실감을 높였습니다.


D. "동물의 숲" 스타일 오디오 시스템 (AudioManager)
TTS(Text-to-Speech) 도입의 비용 문제와 어색함을 해결하고 게임적 허용(Game Feel)을 살리기 위해, 텍스트 출력 시 Pitch Randomization 기법을 적용했습니다.

- 구현 내용: 캐릭터별로 고유한 기본 음역대(Base Pitch)를 설정하고, 대사가 출력될 때마다 미세한 난수(Variance)를 더해 매번 조금씩 다른 톤의 비프음을 재생합니다. 이를 통해 지루하지 않고 리듬감 있는 대화 사운드를 구현했습니다.


## 4. 비주얼 및 에셋 파이프라인 (Visual Polish)
- Character Pipeline: Vroid Studio 모델링 → Blender (ShapeKey/Mesh 최적화) → Unity FBX 임포트

- Physics: UnityChan SpringBone을 적용하여 머리카락과 의복의 자연스러운 흔들림 구현 및 콜라이더 설정을 통한 클리핑 방지.

- Expression: AutoBlink 시스템을 통해 대기 상태에서도 눈을 깜빡이게 하여 생동감 부여. DirectorController에서 표정 레이어(Layer 1)와 동작 레이어(Layer 0)를 혼합(Mixing)하여 동작 중에도 표정이 유지되도록 구현.
