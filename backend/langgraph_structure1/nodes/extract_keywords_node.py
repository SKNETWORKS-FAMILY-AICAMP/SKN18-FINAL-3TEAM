from kiwipiepy import Kiwi
from backend.langgraph_structure1.state import GraphState

def extract_keywords_node(state: GraphState) -> GraphState:
    """
    Retriever 노드 투입용 핵심 키워드 1개를 state['keywords']에 저장합니다.

    우선순위:
    1) 토픽+구조 phrase: 예) "정치 구조", "경제 체계"
    2) 인물/호칭 합성명사: 예) "광개토대왕", "이순신장군"
    3) 토픽 단일어: 예) "정치"

    전제:
    - DB가 조선시대사로 고정이므로 "조선", "조선시대" 같은 범위 컨텍스트는 제거/비선택 처리
    """

    query = state.get("query")
    if not query:
        raise ValueError("extract_retriever_core_keywords: 'query' 값이 state에 없습니다.")

    kiwi = Kiwi()

    QUESTION_STOPWORDS = {"누구", "뭐", "무엇", "언제", "어디", "왜", "어떻게"}

    # DB가 조선시대사로 고정이면 범위 컨텍스트는 제거
    DOMAIN_CONTEXT = {"조선", "조선시대"}

    TOPIC_KEYWORDS = {"정치", "경제", "사회", "문화", "외교", "군사", "행정", "제도", "법", "교육"}

    GENERIC_STOPWORDS = {
        "시대", "설명", "업적", "이유", "배경", "특징", "의미",
        "대해", "대한", "것", "수"
    }

    STRUCTURE_WORDS = {"구조", "체계", "기구", "정책", "운영", "원리"}

    # 인물/호칭/직함류: 합성명사(광개토+대왕)를 강하게 만들기 위한 룰
    PERSON_SUFFIX = {"대왕", "왕", "장군", "황제", "공", "선생", "대감"}

    tokens = kiwi.analyze(query, top_n=1)[0][0]

    # 1) 명사열(형태소 단위) 추출
    noun_seq = [t.form for t in tokens if t.tag in ("NNP", "NNG")]

    # 2) 토픽+구조 phrase 후보 생성 ("정치 구조" 등)
    phrase_candidates = []
    for a, b in zip(noun_seq, noun_seq[1:]):
        if a in TOPIC_KEYWORDS and b in STRUCTURE_WORDS:
            phrase_candidates.append(f"{a} {b}")

    # 3) 연속 명사 묶음을 합성 후보로 생성 (광개토대왕 복원)
    compound_candidates = []
    buf = []

    for t in tokens:
        if t.tag in ("NNP", "NNG"):
            buf.append(t.form)
        else:
            if buf:
                compound_candidates.append("".join(buf))
                buf = []
    if buf:
        compound_candidates.append("".join(buf))

    # 4) 단일 후보 정리
    def is_bad_single(w: str) -> bool:
        return (
            len(w) < 2
            or w in QUESTION_STOPWORDS
            or w in GENERIC_STOPWORDS
            or w in DOMAIN_CONTEXT
        )

    cleaned_singles = [w for w in noun_seq if not is_bad_single(w)]

    # 5) 합성 후보 필터링: "조선시대" 류는 무조건 버림
    #    - endswith("시대")는 범위성 컨텍스트로 간주하여 제거
    def is_bad_compound(w: str) -> bool:
        if len(w) < 2:
            return True
        if w in DOMAIN_CONTEXT:
            return True
        if w.endswith("시대"):
            return True
        return False

    filtered_compounds = [w for w in compound_candidates if not is_bad_compound(w)]

    # 6) 스코어링
    scored = {}

    # (1) phrase 최우선
    for p in phrase_candidates:
        scored[p] = max(scored.get(p, 0.0), 100.0)

    # (2) 인물/직함 합성 후보 우선
    for c in filtered_compounds:
        score = 10.0
        if any(c.endswith(suf) for suf in PERSON_SUFFIX):
            score += 50.0
        scored[c] = max(scored.get(c, 0.0), score)

    # (3) 토픽 단일어
    for w in cleaned_singles:
        score = 1.0
        if w in TOPIC_KEYWORDS:
            score += 20.0
        scored[w] = max(scored.get(w, 0.0), score)

    # 7) 최종 1개 선택
    keywords = [max(scored.items(), key=lambda x: x[1])[0]] if scored else []

    # 출력
    print(f"[DEBUG] 추출된 키워드: query={query!r}, keywords={keywords}")
    print("-" * 60)

    return {
        **state,
        "keywords": keywords,
    }


if __name__ == "__main__":
    questions = [
        "이순신이 누구야?",
        "광개토대왕의 업적은 무엇인가?",
        "조선 시대의 정치 구조를 설명해줘."
    ]

    for q in questions:
        state = {"query": q}
        result = extract_keywords_node(state)
        print(f"Q: {q} -> KW: {result['keywords']}")