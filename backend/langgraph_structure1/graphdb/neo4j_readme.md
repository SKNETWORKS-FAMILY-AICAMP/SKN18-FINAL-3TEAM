노드:
1. 공통영역
    - article_id : CSV row 기반 내부 ID (int)

    - category : 원본 카테고리 문자열(인물/사건/제도…)

    - title : 표제어 (항목 이름)

    - summary : 요약 텍스트

    - main_year : summary/contents에서 뽑은 첫 번째 연도 (대표 연도, 없으면 없음)

    - period_text : 조선 전기, 조선 후기, 세종 대 같은 시기 텍스트(있을 때만)

    - 즉, 어떤 라벨이든 최소 이 정도 “공통 메타데이터”는 다 들어가 있음.

++++++++++++++++

| Category       | Label          | 전용 필드 |
|----------------|----------------|-----------|
| 인물           | Person         | birth_year, death_year |
| 사건           | Event          | start_year, end_year |
| 제도           | System         | established_year, abolished_year |
| 정책           | Policy         | established_year, abolished_year |
| 문헌           | Document       | created_year |
| 작품           | Work           | created_year |
| 유적           | Heritage       | build_year, rebuild_year |
| 의례·행사      | Ritual         | start_year, end_year |
| 물품           | Object         | period_start, period_end |
| 의복           | Clothing       | period_start, period_end |
| 단체           | Organization   | founded_year, dissolved_year |
| 지명           | Place          | exist_start_year, exist_end_year |
| 개념           | Concept        | (없음 — 공통 필드만) |


엣지:
