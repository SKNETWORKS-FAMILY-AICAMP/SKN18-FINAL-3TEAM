# SKN18-FINAL-3TEAM
# AI 기반 인플루언서


## [프로젝트 구조]

```text  
SKN18-FINAL-3TEAM/  
├─ infra/                     # 로컬/배포 인프라 구성  
│  ├─ docker-compose.yml      # Postgres+pgvector+Django 컨테이너 오케스트레이션  
│  └─ nginx.conf              # 배포용 리버스 프록시 설정  
├─ scripts/                   # 데이터베이스/임베딩 파이프라인을 돌리는 독립 스크립트 모음  
│  └─ init_db.sql             # pgvector 확장 및 기본 스키마 생성  
├─ BackEnd/                   # LLM Answer Workflow
│  ├─ LangGraph               # LangGraph 기반 LLM Workflow 정의 
│  │  ├─ GraphDB              # Neo4j 적재flow 정의
│  │  └─ nodes                # LangGraph 각 nodes 역활정의
│  ├─ LLM_Fine_Tuning         # LLM 말투 및 영어 학습
│  └─ RAG                     # RAG 데이터 계층 + ETL 파이프라인
│     ├─ data                 # DB적재 데이터
│     ├─ ETL                  # extract/transform/embed/load 단계 스크립트
│     ├─ queries              # 검색·유지보수·통계 SQL
│     ├─ schema               # 문서/청크/임베딩 스키마 SQL 
│     └─ services             # embedder/retriever/vectorstore/DB
├─ FrontEnd/                  #
   ├─ 3D_Modeling             #
   │  ├─ Asserts              #
   │  ├─ Packages             #
   │  └─ ProjectSettings      #
   ├─ Django                  #
   └─ Videe_Pipeline          #






```


