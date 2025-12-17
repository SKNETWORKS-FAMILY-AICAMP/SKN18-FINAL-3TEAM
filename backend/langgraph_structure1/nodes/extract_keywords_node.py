from kiwipiepy import Kiwi
from backend.langgraph_structure2.state import GraphState

def extract_keywords_node(state: GraphState) -> GraphState:
    query = state.get("query")
    if not query:
        raise ValueError("extract_retriever_core_keywords: 'query' 값이 state에 없습니다.")

    kiwi = Kiwi()

    # (1) 사용자 사전 등록: 도메인 핵심어/행위어를 안정적으로 NNG로 인식시키기
    USER_NOUNS = ["의병", "의병장", "의병활동", "시해", "살인", "암살", "은폐"]
    for w in USER_NOUNS:
        kiwi.add_user_word(w, "NNG")

    QUESTION_STOPWORDS = {"누구", "뭐", "무엇", "언제", "어디", "왜", "어떻게"}
    DOMAIN_CONTEXT = {"조선", "조선시대"}
    TOPIC_KEYWORDS = {"정치", "경제", "사회", "문화", "외교", "군사", "행정", "제도", "법", "교육"}
    GENERIC_STOPWORDS = {"시대", "설명", "업적", "이유", "배경", "특징", "의미", "대해", "대한", "것", "수"}
    STRUCTURE_WORDS = {"구조", "체계", "기구", "정책", "운영", "원리"}
    PERSON_SUFFIX = {"대왕", "왕", "장군", "황제", "공", "선생", "대감"}
    EVENT_SUFFIX = {"사건"}

    # (2) 범용어 패널티 / 도메인 핵심어 보너스
    GENERIC_NOUN_PENALTY = {"군인", "사람", "인물"}   # 필요 시 확장
    DOMAIN_PRIORITY_TERMS = {"의병"}                 # 필요 시 확장

    # (3) “몇 명/몇” 같은 카운트 질문 감지 (예외 처리용)
    COUNT_MARKERS = {"몇", "몇명", "명", "수", "몇 명"}
    is_count_question = any(m in query.replace(" ", "") for m in COUNT_MARKERS)

    tokens = kiwi.analyze(query, top_n=1)[0][0]

    noun_seq = [t.form for t in tokens if t.tag in ("NNP", "NNG")]

    # 토픽+구조 phrase 후보
    phrase_candidates = []
    for a, b in zip(noun_seq, noun_seq[1:]):
        if a in TOPIC_KEYWORDS and b in STRUCTURE_WORDS:
            phrase_candidates.append(f"{a} {b}")

    # (4) 연속 명사 합성 후보 생성 개선:
    #     DOMAIN_CONTEXT(조선/조선시대)가 나오면 버퍼를 끊어서 "조선시대왕" 생성 방지
    compound_candidates = []
    buf = []
    prev_end = None
    for t in tokens:
        start = getattr(t, "start", None)
        end_pos = start + len(t.form) if start is not None else None

        if t.tag in ("NNP", "NNG"):
            # 토큰 간 공백이 있으면 합성하지 않고 버퍼를 끊는다.
            if prev_end is not None and start is not None and start > prev_end:
                if buf:
                    compound_candidates.append("".join(buf))
                    buf = []
            if t.form in DOMAIN_CONTEXT:
                if buf:
                    compound_candidates.append("".join(buf))
                    buf = []
                prev_end = end_pos
                continue
            buf.append(t.form)
        else:
            if buf:
                compound_candidates.append("".join(buf))
                buf = []
        prev_end = end_pos

    if buf:
        compound_candidates.append("".join(buf))

    # (5) 후보 정규화: 접두로 붙은 DOMAIN_CONTEXT 제거
    def strip_domain_prefix(w: str) -> str:
        for dc in sorted(DOMAIN_CONTEXT, key=len, reverse=True):
            if w.startswith(dc):
                return w[len(dc):]
        return w

    def is_bad_single(w: str) -> bool:
        return (
            len(w) < 2
            or w in QUESTION_STOPWORDS
            or w in GENERIC_STOPWORDS
            or w in DOMAIN_CONTEXT
        )

    cleaned_singles = [w for w in noun_seq if not is_bad_single(w)]

    def is_bad_compound(w: str) -> bool:
        if len(w) < 2:
            return True
        # 도메인 컨텍스트 단독/포함/접두로 붙은 경우 제거
        if w in DOMAIN_CONTEXT:
            return True
        if any(dc in w for dc in DOMAIN_CONTEXT):
            return True
        if w.endswith("시대"):
            return True
        # 지나치게 긴 사건류 합성어는 과감히 제거 (예: 명성황후시해사건)
        if w.endswith("사건") and len(w) > 6:
            return True
        return False

    normalized_compounds = [strip_domain_prefix(w) for w in compound_candidates]
    # 사건 접미사 제거한 변형도 추가 (예: '명성황후시해사건' -> '명성황후시해')
    extra_split = []
    for w in normalized_compounds:
        for suf in EVENT_SUFFIX:
            if w.endswith(suf) and len(w) > len(suf) + 1:
                extra_split.append(w[: -len(suf)])
    normalized_compounds.extend(extra_split)

    filtered_compounds = [w for w in normalized_compounds if w and not is_bad_compound(w)]

    scored = {}

    # (1) phrase 최우선
    for p in phrase_candidates:
        scored[p] = max(scored.get(p, 0.0), 100.0)

    # (2) 합성 후보 스코어링
    for c in filtered_compounds:
        score = 10.0
        if any(c.endswith(suf) for suf in PERSON_SUFFIX):
            score += 50.0
        if c in DOMAIN_PRIORITY_TERMS:
            score += 60.0
        if c in GENERIC_NOUN_PENALTY:
            score -= 15.0
        scored[c] = max(scored.get(c, 0.0), score)

    # (3) 단일 후보 스코어링
    for w in cleaned_singles:
        score = 1.0
        if w in TOPIC_KEYWORDS:
            score += 20.0
        if w in DOMAIN_PRIORITY_TERMS:
            score += 60.0
        if w in GENERIC_NOUN_PENALTY:
            score -= 15.0
        scored[w] = max(scored.get(w, 0.0), score)

    # (6) 예외 처리: "조선시대 왕이 몇 명" 류
    #     - 컨텍스트 제거로 "왕"만 남으면 너무 범용이므로 "조선 왕"을 허용
    compact = query.replace(" ", "")
    if is_count_question and ("왕" in compact) and ("조선" in compact or "조선시대" in compact):
        scored["조선 왕"] = max(scored.get("조선 왕", 0.0), 80.0)

    # 상위 N개 키워드(엔티티+행위) 반환
    TOP_N = 2
    keywords = []

    # 1) 엔티티 후보: 사건 접미사가 아닌 긴 명사 합성어 우선
    entity_sorted = [
        w for w, _ in sorted(scored.items(), key=lambda x: x[1], reverse=True)
        if not any(w.endswith(suf) for suf in EVENT_SUFFIX)
    ]
    for w in entity_sorted:
        if any((w in k and len(k) > len(w)) for k in keywords):
            continue
        keywords.append(w)
        break

    # 2) 행위어 후보: 토큰에서 용언/사건 분해 조각
    action_candidates = set()
    for t in tokens:
        if t.tag.startswith(("VV", "VA", "MAG")) and len(t.form) > 1:
            action_candidates.add(t.form)
    for c in normalized_compounds:
        for suf in EVENT_SUFFIX:
            if c.endswith(suf) and len(c) > len(suf) + 1:
                action_candidates.add(c[: -len(suf)])
    action_sorted = sorted(action_candidates, key=lambda w: scored.get(w, 0), reverse=True)
    for w in action_sorted:
        if w in keywords:
            continue
        keywords.append(w)
        break

    # 3) 부족하면 점수순으로 채우기
    if len(keywords) < TOP_N and scored:
        for w, _ in sorted(scored.items(), key=lambda x: x[1], reverse=True):
            if w in keywords:
                continue
            if any((w in k and len(k) > len(w)) for k in keywords):
                continue
            keywords.append(w)
            if len(keywords) >= TOP_N:
                break

    return {
        **state,
        "keywords": keywords
        }
