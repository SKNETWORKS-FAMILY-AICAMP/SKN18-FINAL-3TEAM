"""
질문(한국어) → Cypher 쿼리 생성

LangGraph 노드 안에서는 이 파일의
    question_to_cypher(question: str)  # 하나만
함수만 호출하면 됨.

"""
import re
from dotenv import load_dotenv
from backend.langgraph_structure1.state import GraphState


def create_cypher(state: GraphState) -> GraphState:
    """
    Docstring for create_cypher
    """

    # ===== 키워드 추출용 불용어 =====
    STOPWORDS = {
        "은", "는", "이", "가", "을", "를", "과", "와",
        "에서", "으로", "로", "에게", "한테",
        "도", "만", "까지", "부터",
        "뭐", "뭐야", "뭔데", "왜", "어떻게",
        "알려줘", "설명", "대해", "대해서",
        "에", "의", "것", "거", "관계",
    }

    question = state.get("query")
    if not question:
        raise ValueError("retrieval_node: 'query' 값이 state에 없습니다.")

    # -------------------------------------------------
    # 1) 연도 기반 질의: "XXXX년"
    # -------------------------------------------------
    year = re.findall(r"(\d{3,4})\s*년", question)
    if year:
        y = int(year[0])
        cypher = f"""
        MATCH (y:Year {{value: {y}}})
        OPTIONAL MATCH (e:Event)-[:MAIN_YEAR|:STARTED_IN|:ENDED_IN]->(y)
        RETURN y AS main_year, collect(e) AS events
        """
        return cypher

    # -------------------------------------------------
    # 2) 키워드 기반 질의 (명사/핵심 단어 추출)
    # -------------------------------------------------
    clean = re.sub(r"[^가-힣0-9A-Za-z\s]", " ", question)
    raw = clean.split()
    keywords = []
    for t in raw:
        t = re.sub(r"(은|는|이|가|을|를|과|와|에서|에|때|으로|의|로|에게)$", "", t)
        if len(t) < 2:
            continue
        if t in STOPWORDS:
            continue
        keywords.append(t)

    # 중복 제거
    uniq_keywords = []
    for t in keywords:
        if t not in uniq_keywords:
            uniq_keywords.append(t)

    # 키워드가 하나도 없으면 걍 랜덤 노드 10개
    if not uniq_keywords:
        cypher = """
            MATCH (n)
            RETURN n AS main
            LIMIT 10
            """
        return cypher

    literal = "[" + ", ".join(f"'{k}'" for k in uniq_keywords) + "]"

    cypher = f"""
    WITH {literal} AS keywords
    MATCH (n)
    WHERE any(l IN labels(n) WHERE l IN [
    'Person','Event','Place','Organization','Heritage',
    'Concept','Object','System','Document','Work','Ritual',
    'Clothing','Policy'
    ])
    AND any(kw IN keywords WHERE n.title CONTAINS kw OR n.summary CONTAINS kw)
    WITH n LIMIT 10

    OPTIONAL MATCH (n)-[r1]->(o)
    WITH n, collect(DISTINCT o) AS out_nodes
    OPTIONAL MATCH (i)-[r2]->(n)
    WITH n, out_nodes, collect(DISTINCT i) AS in_nodes

    RETURN n AS main, n.summary AS main_summary, out_nodes, in_nodes
    """

    return cypher