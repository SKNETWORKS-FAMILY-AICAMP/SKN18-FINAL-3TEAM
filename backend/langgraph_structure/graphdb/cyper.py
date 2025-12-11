# cyper.py
"""
질문 → (필요시 영어→한국어 번역) → Cypher 쿼리 생성

LangGraph 노드 안에서는 이 파일의
    question_to_cypher(question: str)  # 하나만
함수만 호출하면 됨.

return 값(dict):
{
    "ko_question": str,   # 한국어 질문 (번역/원문)
    "translated": bool,   # 영어 → 한국어 번역이 일어났는지 여부
    "cypher": str         # 최종 Cypher 쿼리 문자열
}
"""

import re
import os
from dotenv import load_dotenv
from openai import OpenAI

# ===== .env & OpenAI =====
load_dotenv()
client = OpenAI()

# ===== 키워드 추출용 불용어 =====
STOPWORDS = {
    "은", "는", "이", "가", "을", "를", "과", "와",
    "에서", "으로", "로", "에게", "한테",
    "도", "만", "까지", "부터",
    "뭐", "뭐야", "뭔데", "왜", "어떻게",
    "알려줘", "설명", "대해", "대해서",
    "에", "의", "것", "거", "관계",
}


def question_to_cypher(question: str) -> dict:
    """
    LangGraph 노드에서 호출할 단일 엔트리 함수.

    Args:
        question (str): 원본 사용자 질의 (한/영 혼합 가능)

    Returns:
        dict: {
            "ko_question": str,   # 한국어 질문
            "translated": bool,   # 영어 → 한국어 번역 여부
            "cypher": str         # 최종 Cypher 쿼리
        }
    """

    # -------------------------------------------------
    # 1) 영어 → 한국어 변환 (필요할 때만)
    # -------------------------------------------------
    text = question.strip()

    # 한글이 하나라도 있으면 그대로 사용
    if re.search(r"[가-힣]", text):
        ko_question = text
        translated = False
    # 알파벳이 있으면 영어 질문으로 보고 번역
    elif re.search(r"[A-Za-z]", text):
        system = (
            "You are a translator who converts English questions about Korean history "
            "into natural Korean. Answer ONLY with the translated Korean sentence."
        )
        user = (
            "다음 문장을 자연스러운 한국어 '질문' 형태로 번역해줘. "
            "불필요한 설명은 쓰지 말고 번역문만 출력해.\n\n"
            f"{text}"
        )
        r = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        ko_question = r.choices[0].message.content.strip()
        translated = True
    else:
        # 한글/영어 둘 다 없으면(숫자/특수문자 위주) 그냥 사용
        ko_question = text
        translated = False

    q = ko_question.strip()

    # -------------------------------------------------
    # 2) 이미 Cypher를 직접 입력한 경우 그대로 리턴
    # -------------------------------------------------
    if re.match(r"(?i)^(match|with|call|create|merge|return)\s", q):
        cypher = q
        return {
            "ko_question": ko_question,
            "translated": translated,
            "cypher": cypher,
        }

    # -------------------------------------------------
    # 3) 연도 기반 질의: "XXXX년"
    # -------------------------------------------------
    year = re.findall(r"(\d{3,4})\s*년", q)
    if year:
        y = int(year[0])
        cypher = f"""
MATCH (y:Year {{value: {y}}})
OPTIONAL MATCH (e:Event)-[:MAIN_YEAR|:STARTED_IN|:ENDED_IN]->(y)
RETURN y AS main_year, collect(e) AS events
"""
        return {
            "ko_question": ko_question,
            "translated": translated,
            "cypher": cypher,
        }

    # -------------------------------------------------
    # 4) 키워드 기반 질의 (명사/핵심 단어 추출)
    # -------------------------------------------------
    clean = re.sub(r"[^가-힣0-9A-Za-z\s]", " ", q)
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
        return {
            "ko_question": ko_question,
            "translated": translated,
            "cypher": cypher,
        }

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

    return {
        "ko_question": ko_question,
        "translated": translated,
        "cypher": cypher,
    }


# -----------------------------------------------------
# 단독 테스트용
# -----------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="*")
    args = parser.parse_args()

    q0 = " ".join(args.question) if args.question else input("질문: ").strip()
    result = question_to_cypher(q0)

    print(f"\n[원본 질문] {q0}")
    if result["translated"]:
        print(f"[번역된 한국어 질문] {result['ko_question']}")
    else:
        print("[번역 불필요] 한국어 또는 혼합 질의로 판단")
        print(f"→ 사용 질문: {result['ko_question']}")
    print("\n[생성된 Cypher]")
    print(result["cypher"])
