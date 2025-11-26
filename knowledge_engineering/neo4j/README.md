# Neo4j Integration Notes

이 디렉터리는 온톨로지/추론 결과를 Neo4j 그래프 DB에 적재하고, LangGraph나 Django 백엔드에서 Cypher 쿼리로 활용하기 위한 스크립트와 설정을 위한 자리입니다.

추천 구조:

- `connectors/`: Python or Java 기반 커넥터
- `migrations/`: 그래프 스키마 초기화 스크립트
- `pipelines/`: TTL → Neo4j 변환 또는 동기화 파이프라인
- `docs/`: Neo4j 데이터 모델 및 운영 가이드

현재는 플레이스홀더 상태이며, Neo4j 관련 산출물이 준비되면 여기에 정리해주세요.
