# Data Pipeline / ETL

데이터 수집·정제·적재(ETL) 작업은 이 디렉터리에 정리하는 것을 권장합니다. 권장 구조:

- `ingest/`: 외부 원천(위키, CSV 등) 수집 스크립트
- `transform/`: 정규화 및 품질 검증 코드 (Pandas, PySpark 등)
- `load/`: 결과물을 `knowledge_engineering/ontology/instances`나 Neo4j로 적재하는 파이프라인
- `jobs/`: Airflow/Prefect 등 오케스트레이션 정의
- `docs/`: 데이터 사양 및 스키마 매핑 문서

ETL로 생성된 산출물은 다음 위치에 반영하면 됩니다.

- 온톨로지 TTL/OWL: `knowledge_engineering/ontology/instances|schemas|rules`
- SPARQL 템플릿: `knowledge_engineering/ontology/queries`
- Neo4j 적재 스크립트: `knowledge_engineering/neo4j`

필요 시 `requirements.txt`에 데이터 파이프라인용 의존성을 추가하고, 여기에서 전용 가상환경 또는 Docker 이미지를 정의하세요.
