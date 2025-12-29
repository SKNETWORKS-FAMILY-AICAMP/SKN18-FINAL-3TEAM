"""
질문(한국어) → Cypher 쿼리 생성
- KIWI 명사추출
- REL_MAP 기반 관계 타입만 탐색
- hop2/hop3를 한 번에 같이 반환
- OOM 방지: path collect 금지, 노드 제한 기반, hop3는 hop2 frontier에서 1-hop 확장
- allowed_labels 스코프 유지 버그 해결
"""

import re
from kiwipiepy import Kiwi
from backend.langgraph_structure1.state import GraphState

# ===== 사용자 스키마 =====
REL_MAP = {
    ("Place", "Event"): "PLACE_OF_EVENT",
    ("Event", "Person"): "PARTICIPANT",
    ("Event", "Object"): "USED_OBJECT",
    ("Event", "Concept"): "RELATED_CONCEPT",
    ("Heritage", "Place"): "LOCATED_IN",
    ("Organization", "Event"): "INVOLVED_IN",
    ("Organization", "System"): "OPERATES",
    ("Organization", "Policy"): "ENFORCES",
    ("Document", "Organization"): "ABOUT_ORG",
    ("Person", "Person"): "ASSOCIATED_WITH",
    ("Person", "Work"): "CREATED_WORK",
}
ALLOWED_REL_TYPES = sorted(set(REL_MAP.values()))
ALLOWED_LABELS = [
    "Person", "Event", "Place", "Organization", "Heritage",
    "Concept", "Object", "System", "Document", "Work", "Ritual",
    "Clothing", "Policy",
]

# ===== 터짐 방지 상수 =====
MAIN_LIMIT = 5
SEED_EVENT_LIMIT = 30
HOP2_NODE_LIMIT = 100
HOP3_NODE_LIMIT = 100

# ===== 키워드 추출 =====
_KIWI = Kiwi()
STOPWORDS = {
    "은", "는", "이", "가", "을", "를", "과", "와",
    "에서", "으로", "로", "에게", "한테",
    "도", "만", "까지", "부터",
    "뭐", "뭐야", "뭔데", "왜", "어떻게",
    "알려줘", "설명", "대해", "대해서",
    "에", "의", "것", "거", "관계",
}


def _extract_keywords_kiwi(q: str) -> list[str]:
    out = []
    analyzed = _KIWI.analyze(q, top_n=1)
    if not analyzed:
        return out
    for tok in analyzed[0][0]:
        if tok.tag in ("NNG", "NNP"):
            w = tok.form.strip()
            if len(w) < 2:
                continue
            if w in STOPWORDS:
                continue
            out.append(w)
    return list(dict.fromkeys(out))


def _rel_union(rels: list[str]) -> str:
    # -[:A|B|C*1..2]- 형태로 쓸 거라 콜론은 바깥 1번만
    if not rels:
        raise ValueError("ALLOWED_REL_TYPES가 비었습니다. REL_MAP 확인 필요")
    return "|".join(rels)


def create_cypher(state: GraphState) -> str:
    question = state.get("query")
    if not question:
        raise ValueError("create_cypher: state['query']가 필요합니다.")

    rel_union = _rel_union(ALLOWED_REL_TYPES)
    labels_literal = "[" + ", ".join(f"'{l}'" for l in ALLOWED_LABELS) + "]"

    # -------------------------------------------------
    # 1) 연도 케이스: "XXXX년"
    # -------------------------------------------------
    year = re.findall(r"(\d{3,4})\s*년", question)
    if year:
        y = int(year[0])
        return f"""
        WITH {labels_literal} AS allowed_labels
        MATCH (y:Year {{value: {y}}})
        OPTIONAL MATCH (e:Event)-[:MAIN_YEAR|:STARTED_IN|:ENDED_IN]->(y)
        WITH y, collect(DISTINCT e)[0..{SEED_EVENT_LIMIT}] AS seed_events, allowed_labels

        CALL {{
          WITH seed_events, allowed_labels
          UNWIND seed_events AS s
          MATCH (s)-[:{rel_union}*1..2]-(m)
          WHERE any(l IN labels(m) WHERE l IN allowed_labels)
          WITH DISTINCT m
          LIMIT {HOP2_NODE_LIMIT}
          RETURN collect(m) AS hop2_nodes
        }}

        CALL {{
          WITH hop2_nodes, allowed_labels
          UNWIND hop2_nodes AS h
          MATCH (h)-[:{rel_union}]-(m)
          WHERE any(l IN labels(m) WHERE l IN allowed_labels)
          WITH DISTINCT m
          LIMIT {HOP3_NODE_LIMIT}
          RETURN collect(m) AS hop3_nodes
        }}

        RETURN
          y AS main,
          y.value AS main_year,
          seed_events,
          hop2_nodes,
          hop3_nodes
        """

    # -------------------------------------------------
    # 2) 키워드 케이스
    # -------------------------------------------------
    keywords = _extract_keywords_kiwi(question)

    if not keywords:
        return f"""
        WITH {labels_literal} AS allowed_labels
        MATCH (n)
        WHERE any(l IN labels(n) WHERE l IN allowed_labels)
        WITH DISTINCT n, allowed_labels
        LIMIT {MAIN_LIMIT}

        CALL {{
          WITH n, allowed_labels
          MATCH (n)-[:{rel_union}*1..2]-(m)
          WHERE any(l IN labels(m) WHERE l IN allowed_labels)
          WITH DISTINCT m
          LIMIT {HOP2_NODE_LIMIT}
          RETURN collect(m) AS hop2_nodes
        }}

        CALL {{
          WITH hop2_nodes, allowed_labels
          UNWIND hop2_nodes AS h
          MATCH (h)-[:{rel_union}]-(m)
          WHERE any(l IN labels(m) WHERE l IN allowed_labels)
          WITH DISTINCT m
          LIMIT {HOP3_NODE_LIMIT}
          RETURN collect(m) AS hop3_nodes
        }}

        RETURN
          n AS main,
          n.summary AS main_summary,
          hop2_nodes,
          hop3_nodes
        """

    literal = "[" + ", ".join(f"'{k}'" for k in keywords) + "]"

    return f"""
    WITH {literal} AS keywords, {labels_literal} AS allowed_labels
    MATCH (n)
    WHERE any(l IN labels(n) WHERE l IN allowed_labels)
      AND any(kw IN keywords WHERE
            coalesce(n.title,'') CONTAINS kw
         OR coalesce(n.summary,'') CONTAINS kw
      )
    WITH DISTINCT n, allowed_labels
    LIMIT {MAIN_LIMIT}

    CALL {{
      WITH n, allowed_labels
      MATCH (n)-[:{rel_union}*1..2]-(m)
      WHERE any(l IN labels(m) WHERE l IN allowed_labels)
      WITH DISTINCT m
      LIMIT {HOP2_NODE_LIMIT}
      RETURN collect(m) AS hop2_nodes
    }}

    CALL {{
      WITH hop2_nodes, allowed_labels
      UNWIND hop2_nodes AS h
      MATCH (h)-[:{rel_union}]-(m)
      WHERE any(l IN labels(m) WHERE l IN allowed_labels)
      WITH DISTINCT m
      LIMIT {HOP3_NODE_LIMIT}
      RETURN collect(m) AS hop3_nodes
    }}

    RETURN
      n AS main,
      n.summary AS main_summary,
      hop2_nodes,
      hop3_nodes
    """
