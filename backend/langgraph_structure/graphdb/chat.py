# chat.py
"""
Neo4j 그래프DB + OpenAI 질의응답 (지속 대화형)

- 그래프 스키마(노드 + 관계)를 적극적으로 활용해서 Cypher 생성
- 질문을 계속 입력할 수 있는 REPL 모드
- 종료: exit / quit / q / 종료 / 끝
"""

import os
import sys
import json
import argparse

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship
from openai import OpenAI

# ===== .env 로드 =====
load_dotenv()   # OPENAI_API_KEY, NEO4J_* 등 로드

# ===== Neo4j 설정 =====
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "skn183final")

# ===== OpenAI 클라이언트 =====
client = OpenAI()  # OPENAI_API_KEY 필요


# ===== Neo4j 헬퍼 =====

def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def run_cypher(driver, query: str, params: dict | None = None):
    params = params or {}
    with driver.session() as session:
        result = session.run(query, **params)
        return list(result)


def serialize_value(v):
    """Neo4j Node/Relationship/리스트를 LLM-friendly dict로 변환"""
    if isinstance(v, Node):
        return {
            "_type": "node",
            "labels": list(v.labels),
            "props": dict(v),
        }
    if isinstance(v, Relationship):
        return {
            "_type": "relationship",
            "type": v.type,
            "props": dict(v),
        }
    # 리스트(places, objects 같은 컬럼)에 Node들이 들어있을 수 있으니 재귀적으로 처리
    if isinstance(v, (list, tuple)):
        return [serialize_value(item) for item in v]
    # dict 안에 Node가 들어갈 가능성까지 케어하고 싶으면 아래 한 줄 추가 가능
    if isinstance(v, dict):
        return {k: serialize_value(val) for k, val in v.items()}
    return v


def serialize_records(records):
    out = []
    for r in records:
        item = {}
        for key, value in r.items():
            item[key] = serialize_value(value)
        out.append(item)
    return out


# ===== 스키마 설명 (Cypher 생성용) =====

SCHEMA_DESCRIPTION = """
노드 라벨:
- Person, Event, Document, System, Heritage, Concept, Object,
  Organization, Place, Work, Ritual, Clothing, Policy, Year

공통 속성:
- article_id (int), title (string), summary (string), category (string)

연도 속성 예시:
- Person: birth_year, death_year, main_year
- Event: start_year, end_year, main_year
- System/Policy: established_year, abolished_year
- Document/Work: created_year
- Heritage: build_year, rebuild_year
- Object/Clothing: period_start, period_end
- Place: exist_start_year, exist_end_year

Year 노드:
- :Year { value: 1592 }

연도 관계:
- (n)-[:MAIN_YEAR]->(y:Year)
- (p:Person)-[:BORN_IN]->(y:Year)
- (p:Person)-[:DIED_IN]->(y:Year)
- (e:Event)-[:STARTED_IN]->(y:Year)
- (e:Event)-[:ENDED_IN]->(y:Year)
- (s:System|p:Policy)-[:ESTABLISHED_IN]->(y:Year)
- (s:System|p:Policy)-[:ABOLISHED_IN]->(y:Year)
- (d:Document|w:Work)-[:CREATED_IN]->(y:Year)
- (h:Heritage)-[:BUILT_IN]->(y:Year)
- (h:Heritage)-[:REBUILT_IN]->(y:Year)
- (o:Object|c:Clothing)-[:PERIOD_START_IN]->(y:Year)
- (o:Object|c:Clothing)-[:PERIOD_END_IN]->(y:Year)
- (pl:Place)-[:EXIST_START_IN]->(y:Year)
- (pl:Place)-[:EXIST_END_IN]->(y:Year)

엔티티 네트워크 관계 (방향 중요):

[참여 / 소속]
- (p:Person)-[:PARTICIPATED_IN]->(e:Event)
- (o:Organization)-[:INVOLVED_IN]->(e:Event)
- (p:Person)-[:MEMBER_OF]->(o:Organization)

[위치]
- (e:Event)-[:OCCURRED_IN]->(pl:Place)
- (h:Heritage)-[:LOCATED_IN]->(pl:Place)
- (pl1:Place)-[:IN_REGION]->(pl2:Place)

[사건에서 사용하는 것들]
- (e:Event)-[:USED_OBJECT]->(obj:Object)
- (e:Event)-[:APPLIED_CONCEPT]->(c:Concept)

[유적 / 사건 / 인물]
- (h:Heritage)-[:RELATED_EVENT]->(e:Event)
- (p:Person)-[:RELATED_SITE]->(h:Heritage)

[제도 / 정책]
- (o:Organization)-[:OPERATES_SYSTEM]->(s:System)
- (o:Organization)-[:ENFORCES_POLICY]->(p:Policy)

[문헌 / 작품 (자료 → 대상)]
- (d:Document)-[:ABOUT_EVENT]->(e:Event)
- (d:Document)-[:ABOUT_PERSON]->(p:Person)
- (w:Work)-[:DEPICTS_EVENT]->(e:Event)
- (w:Work)-[:DEPICTS_PERSON]->(p:Person)

[인물 ↔ 개념/물품]
- (p:Person)-[:RELATED_CONCEPT]->(c:Concept)
- (p:Person)-[:RELATED_OBJECT]->(obj:Object)

[네트워크(대칭 관계지만 단방향만 저장)]
- (p1:Person)-[:ASSOCIATED_WITH]->(p2:Person)
- (o1:Organization)-[:ASSOCIATED_WITH]->(o2:Organization)

[기타 자동 생성된 연관 관계]
- (a)-[:RELATED_TO]->(b)
"""


# ===== LLM: 질문 -> Cypher =====

def generate_cypher(question: str) -> str:
    """
    한국어 질문을 그래프 구조(노드 + 관계)를 적극 활용하는 Cypher로 변환.
    """
    system_prompt = """
너는 Neo4j Cypher와 그래프 질의 설계 전문가다.
아래 스키마 설명을 기반으로, 사용자의 한국어 역사 질문을 해결하기 위해
노드와 관계를 적극적으로 활용하는 단일 Cypher 쿼리를 생성하는 것이 너의 역할이다.

반드시 지켜야 할 규칙:

1. 출력 형식
- 오직 Cypher 쿼리만 출력한다.
- 설명, 자연어, 주석, ``` 같은 코드블록 표시는 절대 넣지 않는다.

2. 그래프 활용 원칙
- 가능하면 단일 노드를 반환하는 것이 아니라,
  그 노드와 직접 연결된 관련 노드(1-hop)를 함께 조회하되,
  각 관계 유형별로 collect(DISTINCT ...)로 묶어서 리스트로 반환하라.
- 인물/사건/지명/단체가 언급된 질문이라면,
  title을 이용해 해당 노드를 찾은 뒤, 다음과 같은 관계를 활용해 주변을 조회하라:
  - PERSON → EVENT:    :PARTICIPATED_IN
  - ORG → EVENT:        :INVOLVED_IN
  - EVENT → PLACE:      :OCCURRED_IN
  - HERITAGE → PLACE:   :LOCATED_IN
  - EVENT → OBJECT:     :USED_OBJECT
  - EVENT → CONCEPT:    :APPLIED_CONCEPT
  - HERITAGE → EVENT:   :RELATED_EVENT
  - PERSON → HERITAGE:  :RELATED_SITE
  - ORG → SYSTEM:       :OPERATES_SYSTEM
  - ORG → POLICY:       :ENFORCES_POLICY
  - DOCUMENT → EVENT/PERSON: :ABOUT_EVENT, :ABOUT_PERSON
  - WORK → EVENT/PERSON:     :DEPICTS_EVENT, :DEPICTS_PERSON
  - PERSON ↔ PERSON:    :ASSOCIATED_WITH
  - ORG ↔ ORG:          :ASSOCIATED_WITH
  - 그 외 자동 엣지는 :RELATED_TO

- 절대 `(e)-[r]-(n)` 같은 패턴으로 "모든 관계"를 한 번에 매칭하지 마라.
  특정 목적이 있을 때는 반드시 관계 타입을 명시해서 MATCH 하라.
  예: `(e)-[:OCCURRED_IN]->(pl:Place)` 처럼 사용하고,
  필요하면 collect(DISTINCT pl) AS places 처럼 리스트로 모아라.

- 여러 OPTIONAL MATCH 를 사용할 때는
  각 단계 사이에 WITH + collect(DISTINCT ...)를 사용하여
  카테시안 곱이 생기지 않도록 해라.

  예시 패턴:
  MATCH (e:Event {title: '임진왜란'})
  OPTIONAL MATCH (e)-[:OCCURRED_IN]->(pl:Place)
  WITH e, collect(DISTINCT pl) AS places
  OPTIONAL MATCH (e)-[:USED_OBJECT]->(obj:Object)
  WITH e, places, collect(DISTINCT obj) AS objects
  RETURN e AS main, places, objects

3. 연도/시기 관련 질문
- 연도(예: 1592년, 18세기, 조선 후기 등)가 언급된 질문이라면 Year 노드와
  연관된 Event, Person, Place 등을 함께 조회하되,
  역시 관계 타입을 명시하고 collect(DISTINCT ...)로 묶어라.

  예시:
  MATCH (y:Year {value:1592})
  MATCH (e:Event)-[:MAIN_YEAR|:STARTED_IN]->(y)
  OPTIONAL MATCH (e)-[:OCCURRED_IN]->(pl:Place)
  OPTIONAL MATCH (e)<-[:PARTICIPATED_IN]-(p:Person)
  WITH e,
       collect(DISTINCT pl) AS places,
       collect(DISTINCT p) AS participants
  RETURN e AS main,
         e.summary AS main_summary,
         places,
         participants
  LIMIT 50

4. 카테고리/직함/궁궐에 대한 규칙
- category 필드에는 다음 값들만 들어 있다:
  '인물','사건','문헌','제도','유적','개념','물품','단체','지명',
  '작품','의례·행사','의복','정책'
- 따라서 category = '조선시대 왕', category = '궁궐' 같은 식으로
  임의의 문자열을 넣으면 안 된다. category 비교는 반드시 위 값들 중 하나와
  = 로만 사용한다.
  예: WHERE p.category = '인물', WHERE h.category = '유적'
- 왕/임금/국왕/장군과 같은 직함은 category로 저장되지 않는다.
  따라서 직함을 찾으려면 Person.summary 또는 Person.title 텍스트를 사용해라.
  예:
  MATCH (p:Person)
  WHERE p.summary CONTAINS '조선' AND p.summary CONTAINS '왕'

- 궁궐 관련 질문(예: "제일 유명한 궁궐")에서는 보통 Heritage(유적)에
  '경복궁','창덕궁' 같은 제목으로 저장되어 있다.
  이 경우에는 다음과 같이 작성해라:
  MATCH (h:Heritage)
  WHERE h.category = '유적' AND h.title CONTAINS '궁'

5. 문법 규칙
- Neo4j 5 문법만 사용한다.
- exists(n.prop) 문법은 절대 쓰지 말고, n.prop IS NOT NULL 만 사용한다.
- APOC, 프로시저, 플러그인은 사용하지 않는다.
- 절대 size() 함수 안에 패턴을 넣지 마라.
  예: size((n)-[]-()) 는 절대 사용 금지다.
  관계 개수를 세고 싶다면 반드시 아래 형식을 사용해야 한다:

  OPTIONAL MATCH (n)-[r]-()
  WITH n, count(r) AS rel_count
  ORDER BY rel_count DESC

6. 결과 컬럼
- 항상 주요 노드를 main 으로, 그와 연결된 노드들은
  collect(DISTINCT ...) 로 모아서 반환한다.
- 예시:
  MATCH (p:Person {title: '이순신'})
  OPTIONAL MATCH (p)-[:PARTICIPATED_IN]->(e:Event)
  OPTIONAL MATCH (p)-[:ASSOCIATED_WITH]-(other:Person)
  WITH p,
       collect(DISTINCT e) AS events,
       collect(DISTINCT other) AS related_persons
  RETURN p AS main,
         p.summary AS main_summary,
         events,
         related_persons
  LIMIT 50

- 절대 "row 하나당 main, rel, neighbor 를 그대로 나열"하는 방식으로
  방대한 row 를 만들지 마라.
  항상 main 을 기준으로 리스트를 모아서 반환하는 구조로 설계해라.

7. 매칭 전략
- title 이 정확히 주어졌으면 =, 애매하면 CONTAINS 를 사용한다.
- 한국어 질문에서 인물/사건/장소/궁궐 이름을 추출해서 title 필터로 활용한다.
- 필요할 경우 OPTIONAL MATCH 로 관계를 붙이고, 그래프가 없으면 노드만 반환하게 한다.
- 질문이 특정 사건/인물 하나를 중심으로 상세 맥락을 묻는 경우
  (예: "임진왜란의 진행 과정", "세종대왕 주변 인물"),
  보통 해당 main 노드 1개 정도만 보면 충분하므로
  LIMIT 는 1~10 사이의 작은 값으로 설정하라.
  대량 리스트를 반환하는 검색형 질문(예: "조선 후기 대표 사건 5개")일 때만
  LIMIT 50~100 정도를 사용하라.

8. 여러 엔티티가 함께 언급될 때 (A와 B와 C ...)
- 질문에 "A와 B", "A랑 B", "A 그리고 B", "A와 B와 C" 같이
  서로 다른 여러 엔티티(인물, 사건, 물품 등)가 함께 등장하면,
  각 엔티티를 서로 독립적인 main 후보로 취급하라.
- 이때, 어느 한 엔티티가 그래프에 없더라도 다른 엔티티의 정보는
  반드시 나오도록 쿼리를 설계해야 한다.
- 가능한 경우, "가장 존재 가능성이 높은 엔티티"를 먼저 MATCH 하는
  앵커(anchor)를 잡고, 나머지는 OPTIONAL MATCH 로 처리하라.

  예시 (마패는 없을 수도 있지만 임진왜란은 거의 확실히 존재할 때):

  MATCH (e:Event {title: '임진왜란'})
  OPTIONAL MATCH (obj:Object {title: '마패'})
  OPTIONAL MATCH (obj)-[:RELATED_TO]->(related_obj:Object)
  WITH e,
       obj,
       collect(DISTINCT related_obj) AS related_objects
  OPTIONAL MATCH (e)-[:OCCURRED_IN]->(pl:Place)
  OPTIONAL MATCH (e)<-[:PARTICIPATED_IN]-(p:Person)
  WITH e, obj, related_objects,
       collect(DISTINCT pl) AS places,
       collect(DISTINCT p)  AS participants
  RETURN obj AS main_object,
         related_objects,
         e   AS main_event,
         e.summary AS main_event_summary,
         places,
         participants
  LIMIT 10

- 다음과 같은 패턴은 피해야 한다 (안티 패턴):
  MATCH (obj:Object {title: '마패'})
  ...
  MATCH (e:Event {title: '임진왜란'})
  ...
  위처럼 "존재하지 않을 수도 있는 노드"를 앞에서 MATCH 로 고정하면,
  해당 노드가 없을 때 전체 결과 레코드가 0개가 되어버리므로 이런 구조는 만들지 마라.

9. 같은 타입의 엔티티가 여러 개 등장할 때 (특히 사건 Event)
- 질문에 "임진왜란과 병자호란", "노량해전이랑 한산도 대첩",
  "정묘호란, 병자호란, 임진왜란을 비교해줘" 처럼
  **같은 라벨을 가진 여러 엔티티(특히 Event)** 가 함께 언급되면,
  각 이벤트를 e1, e2, e3 처럼 따로 MATCH 하지 말고
  하나의 MATCH + IN 조건으로 처리하라.

  선호하는 패턴 (좋은 예시):

  MATCH (e:Event)
  WHERE e.title IN ['임진왜란', '병자호란']
  OPTIONAL MATCH (e)-[:OCCURRED_IN]->(pl:Place)
  OPTIONAL MATCH (e)<-[:PARTICIPATED_IN]-(p:Person)
  OPTIONAL MATCH (e)-[:USED_OBJECT]->(obj:Object)
  OPTIONAL MATCH (e)-[:APPLIED_CONCEPT]->(c:Concept)
  OPTIONAL MATCH (e)<-[:RELATED_EVENT]-(h:Heritage)
  WITH e,
       collect(DISTINCT pl)  AS places,
       collect(DISTINCT p)   AS participants,
       collect(DISTINCT obj) AS objects,
       collect(DISTINCT c)   AS concepts,
       collect(DISTINCT h)   AS heritages
  RETURN e AS main_event,
         e.summary AS main_summary,
         places,
         participants,
         objects,
         concepts,
         heritages
  ORDER BY e.main_year
  LIMIT 20

- 아래와 같은 패턴은 사용하지 마라 (느리고 복잡해지는 안티 패턴):

  MATCH (e1:Event {title: '임진왜란'})
  OPTIONAL MATCH (e1)...   // 임진왜란용 OPTIONAL MATCH 세트
  ...
  MATCH (e2:Event {title: '병자호란'})
  OPTIONAL MATCH (e2)...   // 병자호란용 OPTIONAL MATCH 세트
  ...

  이렇게 동일한 OPTIONAL MATCH 블록을 e1, e2, e3 등 여러 번 반복하면
  쿼리가 매우 길어지고, 불필요한 카테시안 곱과 collect 연산으로 인해
  수행 시간이 크게 증가한다. 같은 타입의 여러 엔티티를 다뤄야 할 때는
  항상 하나의 변수(e) + IN [...] 패턴을 우선적으로 사용해라.

- Person 여러 명(예: "이순신, 권율, 원균을 비교해줘")이 나올 때도
  가능하면 같은 아이디어를 적용할 수 있다:

  MATCH (p:Person)
  WHERE p.title IN ['이순신', '권율', '원균']
  OPTIONAL MATCH (p)-[:PARTICIPATED_IN]->(e:Event)
  WITH p, collect(DISTINCT e) AS events
  RETURN p AS main_person,
         p.summary AS main_summary,
         events
  ORDER BY p.title

위 모든 규칙을 지키면서, 질문에 가장 잘 답할 수 있는 단일 Cypher 쿼리만 생성해라.
"""

    user_prompt = f"""
[스키마]
{SCHEMA_DESCRIPTION}

[질문]
{question}

위 질문에 최대한 잘 답할 수 있도록,
위 규칙을 따르는 단일 Cypher 쿼리만 생성해라.
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    cypher = resp.choices[0].message.content.strip()

    if cypher.startswith("```"):
        cypher = cypher.strip("`")
        lines = cypher.splitlines()
        if lines and lines[0].strip().lower().startswith("cypher"):
            lines = lines[1:]
        cypher = "\n".join(lines).strip()

    cleaned_lines: list[str] = []
    for line in cypher.splitlines():
        if "size(" in line:
            continue
        cleaned_lines.append(line)
    cypher = "\n".join(cleaned_lines).strip()

    return cypher



# ===== LLM: 그래프 결과 -> 최종 답변 =====

def generate_answer(question: str, cypher: str, records_json: str) -> str:
    """
    Cypher 실행 결과(JSON)를 기반으로 한국어 설명 답변 생성.

    - 그래프DB 정보 + 일반 역사 지식을 함께 사용해서 답변한다.
    - 질문에 '진행과정', '어떻게 진행', '타임라인' 등이 포함되어 있으면
      반드시 연대기/단계별로 정리해서 설명한다.
    """
    system_prompt = """
너는 외국인과 어린아이에게 한국 역사를 쉽게 설명해주는 선생님이다.
그래프DB 검색 결과와 너의 일반적인 한국사 지식을 함께 사용해서
질문에 대한 답변을 한국어로 친절하고 이해하기 쉽게 정리해라.

규칙:
- 그래프DB에서 전달된 정보(main 노드의 summary, 연도, 연결된 인물/단체/장소 등)를 우선 참고하되,
  필요하다면 너가 알고 있는 일반적인 역사 지식을 보충해서 사용해도 된다.
- 다만, 그래프DB 정보와 명백히 모순되는 내용은 말하지 않는다.
- 인물/사건/지명/연도 사이의 관계(누가 어떤 사건에 참여했고, 어느 곳에서
  일어났는지 등)를 중심으로 묶어서 설명한다.
- 너무 딱딱한 논문체 말고, 부드러운 설명체로 답한다.
- 필요하면 bullet 포맷을 사용해도 된다.

특히 다음과 같은 질문일 때에는 반드시 '진행 과정'을 중심으로 설명하라:
- 질문에 '진행과정', '진행 과정', '어떻게 진행', '어떻게 전개', '흐름', '타임라인' 같은 표현이 포함되어 있을 때
- 또한 질의에 대한 답변을 시간순서대로 설명해야 될 때, 반드시 연도에 흐름에 따라서 설명하라.

이 경우에는:
- 전쟁이나 사건을 3~7단계 정도의 흐름으로 나누어,
  1단계, 2단계, 3단계… 혹은 '① ~ ② ~ ③ ~' 형식으로 설명한다.
- 각 단계마다 '언제(연도/시기) - 어디서 - 어떤 일이 일어났는지 - 어떤 인물들이 중요한 역할을 했는지'
  를 중심으로 간단히 정리한다.
- 필요하면 마지막에 '요약' 섹션으로 한 번 더 정리해도 좋다.
"""

    user_prompt = f"""
[질문]
{question}

[사용한 Cypher]
{cypher}

[그래프DB 검색 결과(JSON)]
{records_json}

위 정보를 참고해서 질문에 대한 한국어 답변을 작성해줘.
특히, 질문에 '진행과정', '진행 과정', '어떻게 진행', '어떻게 전개', '타임라인'이 포함되어 있다면
반드시 연대기/단계별(1단계, 2단계, 3단계...) 형식으로 설명해줘.
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )

    return resp.choices[0].message.content.strip()


# ===== 메인 QA 로직 =====

def answer_question(question: str, driver):
    print(f"\n[질문] {question}\n")

    # 1) 질문 -> Cypher
    cypher = generate_cypher(question)
    print("[생성된 Cypher 쿼리]")
    print(cypher)
    print("-" * 80)

    # 2) Cypher 실행
    try:
        raw_records = run_cypher(driver, cypher)
    except Exception as e:
        print("[Neo4j 에러 발생]")
        print(e)
        return

    print(f"[레코드 수] {len(raw_records)}")
    serialized = serialize_records(raw_records)
    records_json = json.dumps(serialized, ensure_ascii=False, indent=2)

    # 디버그용 일부만 출력
    print("[그래프 검색 결과(요약)]")
    print(records_json[:1000] + ("...\n" if len(records_json) > 1000 else "\n"))
    print("-" * 80)

    # 3) LLM으로 최종 답변 생성
    answer = generate_answer(question, cypher, records_json)
    print("[최종 답변]")
    print(answer)
    print("=" * 80)


# ===== CLI 진입점 (지속 대화 모드) =====

def main():
    parser = argparse.ArgumentParser(description="Neo4j 그래프 질의응답")
    parser.add_argument(
        "question",
        nargs="*",
        help="첫 질문 (옵션, 없으면 대화 모드로 바로 진입)",
    )
    args = parser.parse_args()

    driver = get_driver()
    try:
        # 실행 시 인자로 첫 질문이 들어온 경우 한 번 먼저 처리
        if args.question:
            q0 = " ".join(args.question).strip()
            if q0:
                answer_question(q0, driver)

        # 이후 인터랙티브 루프
        print("그래프DB 질의응답 모드입니다.")
        print("질문을 계속 입력하세요. 종료하려면 exit / quit / q / 종료 / 끝 입력.\n")

        while True:
            try:
                q = input("질문을 입력하세요: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n종료합니다.")
                break

            if not q:
                continue

            if q.lower() in {"exit", "quit", "q"} or q in {"종료", "끝"}:
                print("종료합니다.")
                break

            answer_question(q, driver)

    finally:
        driver.close()


if __name__ == "__main__":
    main()
