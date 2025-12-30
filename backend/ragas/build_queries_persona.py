# build_queries_persona.py
# 위치(예시): backend/ragas/build_queries_persona.py  또는 backend/langgraph_structure1/graphdb/build_queries_persona.py
#
# 기능 (최종 요구사항 반영):
# 1) CSV(encykorea_cleaned6.csv)에서 '조선' 관련 재료 샘플링
# 2) 페르소나 2개:
#    - foreigner_culture_history (EN 질문 + KO 질문형 번역)
#    - kids_child (KO 질문)
# 3) 질의유형 2개:
#    - SIMPLE: 단편/정의/누구-뭐-어디
#    - CONNECTIVE: 인과/관계/맥락 연결이 필요한 질문
# 4) persona별 qtype당 10개씩 생성 (persona당 20개)
# 5) CONNECTIVE는 "기본 LLM(검색/그래프/문서 없이)"이 단독으로 답변하기 어려운 것만 생성하도록 강제 + 2차 rule 필터
# 6) "조선시대에는" 같은 과잉 명시 문구는 비교 질문이 아니면 금지(프롬프트 강제 + 후처리로 제거)
# 7) 결과를 data/questions.jsonl 저장 (persona 순서 + qtype 순서 정렬)
#
# 실행:
#   python .\build_queries_persona.py
#
# 요구:
#   pip install openai python-dotenv pandas tqdm

import json
import re
from pathlib import Path
from collections import defaultdict

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

# =====================
# ENV / CLIENT
# =====================
load_dotenv()
client = OpenAI()

BASE_DIR = Path(__file__).resolve().parent

# ---------------------
# CSV PATH (robust)
# - 스크립트가 어디 있든 repo 내 backend/db_pipeline/data/... 를 우선적으로 찾음
# ---------------------
def find_csv_path() -> Path:
    # __file__ 기준 위로 올라가며 backend/db_pipeline/data를 탐색
    for p in [BASE_DIR, *BASE_DIR.parents]:
        cand = p / "backend" / "db_pipeline" / "data" / "encykorea_cleaned6.csv"
        if cand.exists():
            return cand.resolve()
        cand2 = p / "db_pipeline" / "data" / "encykorea_cleaned6.csv"
        if cand2.exists():
            return cand2.resolve()
    # 마지막 fallback: BASE_DIR 기준으로 backend/db_pipeline 가정
    return (BASE_DIR / ".." / "db_pipeline" / "data" / "encykorea_cleaned6.csv").resolve()

CSV_PATH = find_csv_path()

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
OUT_PATH = DATA_DIR / "questions.jsonl"

# =====================
# CONFIG
# =====================
PER_PERSONA_PER_TYPE = 10       # qtype당 10개
BATCH_SIZE = 20                 # 너무 크면 JSON 깨짐 -> 10~20 권장
MAX_RETRY_PER_BATCH = 3
MATERIALS_SAMPLE_N = 80

PERSONA_ORDER = ["foreigner_culture_history", "kids_child"]
QTYPE_ORDER = ["SIMPLE", "CONNECTIVE"]

MODEL_GENERATE = "gpt-5-mini"
MODEL_TRANSLATE = "gpt-5-mini"

# =====================
# PERSONAS
# =====================
PERSONAS = [
    {
        "persona_id": "foreigner_culture_history",
        "lang": "en",
        "desc": (
            "A foreigner who is very interested in Korean culture and history. "
            "They ask casual questions in English about Joseon-era history, people, places, events, and daily life."
        ),
        "rules": [
            "Use simple English",
            "1–2 sentences per question",
            "Casual, curious tone (tourist/learner vibe)",
            "No answers, only questions",
            "Do NOT ask for a full essay; keep it concise",
        ],
    },
    {
        "persona_id": "kids_child",
        "lang": "ko",
        "desc": (
            "역사를 배우려는 유아/아동(6~10세) 한국인. "
            "아주 쉬운 한국어로 짧게 질문한다."
        ),
        "rules": [
            "1문장",
            "'누구야/뭐야/왜/어떻게' 형태 자주 사용",
            "어려운 정치/학술 용어 금지",
            "답변/설명 금지, 질문만",
        ],
    },
]

# =====================
# QTYPE SPECS (2 TYPES)
# =====================
QTYPE_SPEC_EN = f"""
Question types (qtype): {", ".join(QTYPE_ORDER)}

- SIMPLE:
  Standalone, short, single-entity questions.
  Examples: who/what/where/meaning/basic facts.

- CONNECTIVE:
  Questions that require connecting causes, effects, relationships, or context.
  Examples: why A led to B, relationship between A and B, how a policy changed society, comparison old vs modern.
"""

QTYPE_SPEC_KO = f"""
[질문 유형(qtype)] {", ".join(QTYPE_ORDER)}

- SIMPLE:
  단편/단일 대상 중심(누구/뭐/어디/뜻/기본 사실)

- CONNECTIVE:
  연결성이 필요한 질문(원인-결과/영향/관계/비교/맥락 연결)
"""

# =====================
# CSV LOADER (ROBUST)
# =====================
def read_csv_robust(path: Path):
    try:
        return pd.read_csv(path, encoding="utf-8", engine="python", on_bad_lines="skip")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", engine="python", on_bad_lines="skip")

def pick_col(cols, cands):
    for c in cands:
        if c in cols:
            return c
    return None

def load_materials(sample_n: int):
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    df = read_csv_robust(CSV_PATH)
    print(f"[csv] loaded rows={len(df)} cols={list(df.columns)}")
    print(f"[csv] CSV_PATH={CSV_PATH} exists={CSV_PATH.exists()}")

    cols = set(df.columns)
    title_col = pick_col(cols, ["title", "Title", "제목", "항목명", "name"])
    summary_col = pick_col(cols, ["summary", "Summary", "요약", "개요"])
    period_col = pick_col(cols, ["period", "Period", "시기", "시대", "연대"])

    if not title_col or not summary_col:
        raise ValueError(f"[csv] cannot find title/summary columns. cols={list(df.columns)}")

    if period_col:
        df2 = df[df[period_col].astype(str).str.contains("조선", na=False)]
        print(f"[csv] filter by period({period_col}) -> {len(df2)} rows")
    else:
        df2 = df[df[summary_col].astype(str).str.contains("조선", na=False)]
        print(f"[csv] filter by summary contains '조선' -> {len(df2)} rows")

    if len(df2) < 50:
        print("[csv] too few Joseon rows -> fallback to full df")
        df2 = df

    df2 = df2.sample(n=min(sample_n, len(df2)), random_state=42)

    mats = []
    for _, r in df2.iterrows():
        mats.append({
            "title": str(r.get(title_col, ""))[:200],
            "summary": str(r.get(summary_col, ""))[:700].replace("\n", " "),
        })

    print(f"[materials] prepared {len(mats)} items")
    return mats

# =====================
# JSON PARSE
# =====================
def safe_json_loads(text: str):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    m = re.search(r"\[\s*{.*}\s*\]|\[\s*\]", text, flags=re.DOTALL)
    if m:
        text = m.group(0)

    return json.loads(text)

# =====================
# QUESTION NORMALIZER (remove redundant "조선시대에는" etc.)
# - 비교(현대/오늘날/지금/요즘/근대/일제강점기/고려/삼국 등)일 때는 유지
# =====================
_COMPARE_HINTS_KO = ["오늘", "오늘날", "현대", "지금", "요즘", "근대", "일제", "고려", "삼국", "신라", "고구려", "백제", "대한제국"]
_COMPARE_HINTS_EN = ["today", "modern", "nowadays", "now", "present", "goryeo", "three kingdoms", "japanese colonial", "empire"]

def looks_like_compare(text: str) -> bool:
    t = (text or "").lower()
    if any(h in t for h in [x.lower() for x in _COMPARE_HINTS_KO]):
        return True
    if any(h in t for h in _COMPARE_HINTS_EN):
        return True
    if "vs" in t or "versus" in t:
        return True
    return False

def strip_redundant_joseon_prefix(q: str) -> str:
    if not q:
        return q
    if looks_like_compare(q):
        return q  # 비교면 유지
    # 과잉 명시 제거 (문장 어디에 있어도)
    patterns = [
        r"\b조선시대(에는|에|의|에서)?\b",
        r"\b조선(시대)?(에는|에|의|에서)?\b",
        r"\bin the Joseon( dynasty)?\b",
        r"\bduring the Joseon( dynasty)?\b",
        r"\bJoseon(-|\s)?era\b",
    ]
    out = q
    for p in patterns:
        out = re.sub(p, "", out, flags=re.IGNORECASE).strip()
    out = re.sub(r"\s{2,}", " ", out).strip()
    # 문장 시작이 어색하면 앞쪽 조사/쉼표 정리
    out = re.sub(r"^(에서는|에는|에서)\s*", "", out).strip()
    out = out.lstrip(" ,.-").strip()
    return out

# =====================
# CONNECTIVE "too easy" FILTER (rule-based)
# =====================
def looks_too_easy_connective(q: str, lang: str) -> bool:
    s = (q or "").strip()
    if not s:
        return True

    if lang == "ko":
        easy_patterns = [
            r"왜 .* (중요|유명|위대)",
            r"무엇(이|을) 했",
            r"어떤 업적",
            r"의미(는|가) 뭐",
            r"간단히 설명",
        ]
        if any(re.search(p, s) for p in easy_patterns):
            return True

        # 연결성 힌트가 너무 약하면 탈락
        connectors = ["때문", "원인", "결과", "영향", "관계", "연결", "바뀌", "변화", "비교", "어떻게"]
        if not any(c in s for c in connectors):
            return True

        # 너무 짧으면(대개 단편)
        if len(s) < 18:
            return True

    else:  # en
        easy_patterns = [
            r"why is .* (important|famous|great)",
            r"what did .* do",
            r"what is the meaning",
            r"explain briefly",
        ]
        if any(re.search(p, s, flags=re.IGNORECASE) for p in easy_patterns):
            return True

        connectors = ["because", "lead to", "result", "impact", "influence", "relationship", "connect", "change", "compare", "how did"]
        if not any(c in s.lower() for c in connectors):
            return True

        if len(s) < 22:
            return True

    return False

# =====================
# TRANSLATION (EN → KO) STRICT QUESTION ONLY
# =====================
def is_question_ko(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    if "?" in s:
        return True
    if re.search(r"(까$|나요$|니$|냐$|어떻게|왜|뭐|무엇|누구|어디|언제|어떤)", s):
        return True
    return False

def translate_en_question_to_ko_question(en_q: str) -> str:
    system = (
        "You are a strict translator.\n"
        "Translate the given English question into natural Korean.\n"
        "IMPORTANT:\n"
        "- Output MUST be a Korean QUESTION.\n"
        "- Do NOT answer.\n"
        "- Do NOT explain.\n"
        "- Output ONLY the translated question.\n"
    )
    user = (
        "Translate the following English question into ONE Korean question sentence.\n"
        "Only output the Korean question.\n\n"
        f"{en_q}"
    )

    last = ""
    for _ in range(3):
        r = client.chat.completions.create(
            model=MODEL_TRANSLATE,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        ko = (r.choices[0].message.content or "").strip()
        ko = ko.strip().strip('"').strip("'")
        ko = re.sub(r"^```.*?\n", "", ko, flags=re.DOTALL).strip()
        ko = re.sub(r"\n```$", "", ko, flags=re.DOTALL).strip()

        last = ko
        if is_question_ko(ko):
            if "?" not in ko:
                ko = ko.rstrip(" .!") + "?"
            return ko

    if not last:
        return "이 질문을 한국어로 어떻게 말해?"
    if "?" not in last:
        last = last.rstrip(" .!") + "?"
    return last

# =====================
# GENERATE QUESTIONS
# =====================
def generate_questions_batch(persona, materials, n: int, qtype: str):
    qtype = qtype.upper().strip()
    if qtype not in QTYPE_ORDER:
        raise ValueError(f"invalid qtype: {qtype}")

    # CONNECTIVE: "기본 LLM 단독으로 답변 어렵게" 강제 + 과잉 조선표현 금지(비교 제외)
    connective_guard_en = ""
    connective_guard_ko = ""
    if qtype == "CONNECTIVE":
        connective_guard_en = """
[CRITICAL CONSTRAINT — MUST FOLLOW]
Generate ONLY questions that a general-purpose LLM would likely FAIL to answer correctly
WITHOUT any retrieval/search/documents/graph.

Each question MUST satisfy ALL:
1) Must require connecting TWO OR MORE distinct Joseon-era entities
   (person/event/policy/institution/place/social practice).
2) Must require explicit causal/relational/context reasoning (not a single fact).
3) Must NOT be answerable by a short textbook/common-knowledge statement.
4) Avoid generic prompts like "Why is X important/famous/great?".

DO NOT explicitly add phrases like "in the Joseon dynasty" or "during Joseon"
unless it is a direct comparison with another period (e.g., modern Korea).
"""
        connective_guard_ko = """
[중요 제약 — 반드시 지켜라]
아래 질문은 '검색/문서/그래프 없이 기본 LLM 단독'으로는 정확히 답하기 어려운 질문만 생성하라.

각 질문은 반드시 모두 만족:
1) 서로 다른 조선 관련 엔티티 2개 이상(인물/사건/제도/기관/장소/생활문화)을 연결해야 함
2) 원인-결과/영향/관계/맥락 추론이 필요해야 함(단일 사실로 끝나면 탈락)
3) 교과서 수준의 흔한 상식 한 문장으로 답할 수 있으면 탈락
4) "왜 X가 중요/유명/위대해?" 같은 범용 질문 금지

"조선시대에는/조선에서는" 같은 과잉 명시 문구는
현대/다른 시대와 '비교' 질문이 아닐 경우 쓰지 마라.
"""

    if persona["lang"] == "en":
        prompt = f"""
Create {n} English questions about Joseon-related history and culture.

[Persona]
{persona["desc"]}

[Rules]
- """ + "\n- ".join(persona["rules"]) + f"""

{QTYPE_SPEC_EN}

[Target qtype]
Generate ONLY questions of qtype = "{qtype}".
- If SIMPLE: single-entity/standalone factual question.
- If CONNECTIVE: MUST require a meaningful connection (cause/effect/relationship/context/comparison).

{connective_guard_en}

[Materials]
Use these only as inspiration. Do NOT copy long text.
{json.dumps(materials, ensure_ascii=False, indent=2)}

[Output]
Return ONLY a JSON array.
Each item must have:
- persona_id: "{persona["persona_id"]}"
- qtype: "{qtype}"
- question: English question
"""
    else:
        prompt = f"""
조선 관련 배경의 한국어 질문 {n}개를 만들어라.

[페르소나]
{persona["desc"]}

[규칙]
- """ + "\n- ".join(persona["rules"]) + f"""

{QTYPE_SPEC_KO}

[목표 qtype]
qtype은 반드시 "{qtype}"만 생성.
- SIMPLE이면 단편/기본 사실 위주.
- CONNECTIVE이면 반드시 연결 추론(원인-결과/관계/영향/맥락/비교)이 필요.

{connective_guard_ko}

[참고 재료]
아래 자료에서 아이디어를 얻되, 긴 문장을 그대로 복사하지 마라.
{json.dumps(materials, ensure_ascii=False, indent=2)}

[출력]
JSON 배열만 출력.
각 원소는 반드시 포함:
- persona_id: "{persona["persona_id"]}"
- qtype: "{qtype}"
- question: 한국어 질문
"""

    r = client.chat.completions.create(
        model=MODEL_GENERATE,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = r.choices[0].message.content
    data = safe_json_loads(raw)

    if not isinstance(data, list):
        raise ValueError(f"model output not list: {type(data)}")

    out = []
    for item in data:
        if not isinstance(item, dict):
            continue

        q = (item.get("question") or "").strip()
        pid = item.get("persona_id") or persona["persona_id"]
        if not q:
            continue

        # qtype 강제
        qt = qtype

        # 과잉 "조선시대에는" 제거(비교면 유지)
        q = strip_redundant_joseon_prefix(q)

        # 질문 마침표/물음표 보정
        if persona["lang"] == "ko":
            if "?" not in q:
                q = q.rstrip(" .!") + "?"
        else:
            if "?" not in q:
                q = q.rstrip(" .!") + "?"

        out.append({"persona_id": pid, "qtype": qt, "question": q})

    # CONNECTIVE 2차 필터(보험)
    if qtype == "CONNECTIVE":
        lang = persona["lang"]
        out = [r for r in out if not looks_too_easy_connective(r["question"], lang)]

    return out

# =====================
# SORT (persona -> qtype order)
# =====================
def normalize_and_sort(rows):
    bucket = defaultdict(lambda: defaultdict(list))
    for r in rows:
        persona = r.get("persona_id", "unknown")
        qtype = (r.get("qtype") or "OTHER").strip().upper()
        r["qtype"] = qtype
        bucket[persona][qtype].append(r)

    ordered = []
    for persona in PERSONA_ORDER:
        for qt in QTYPE_ORDER:
            ordered.extend(bucket[persona].get(qt, []))
        for qt, items in bucket[persona].items():
            if qt not in QTYPE_ORDER:
                ordered.extend(items)

    for persona, qdict in bucket.items():
        if persona in PERSONA_ORDER:
            continue
        for qt in QTYPE_ORDER:
            ordered.extend(qdict.get(qt, []))
        for qt, items in qdict.items():
            if qt not in QTYPE_ORDER:
                ordered.extend(items)

    return ordered

# =====================
# MAIN
# =====================
def main():
    materials = load_materials(MATERIALS_SAMPLE_N)

    all_rows = []

    for p in PERSONAS:
        persona_rows = []

        for qt in QTYPE_ORDER:
            target = PER_PERSONA_PER_TYPE
            # target 채울 때까지 반복 생성
            batches = max(1, (target + BATCH_SIZE - 1) // BATCH_SIZE)
            print(f"[plan] persona={p['persona_id']} qtype={qt} target={target} batches~={batches} batch_size={BATCH_SIZE}")

            got_rows = []
            safety_loops = 0
            while len(got_rows) < target and safety_loops < 20:
                safety_loops += 1
                ok = False
                last_err = None
                for _ in range(MAX_RETRY_PER_BATCH):
                    try:
                        got = generate_questions_batch(p, materials, BATCH_SIZE, qt)
                        if len(got) == 0:
                            raise ValueError("empty batch")
                        got_rows.extend(got)
                        ok = True
                        break
                    except Exception as e:
                        last_err = e
                if not ok:
                    print(f"[warn] batch failed persona={p['persona_id']} qtype={qt} err={last_err}")
                    break

            # 중복 제거(질문 텍스트 기준) 후 target 컷
            seen = set()
            deduped = []
            for r in got_rows:
                key = (r["persona_id"], r["qtype"], r["question"].strip().lower())
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(r)

            deduped = deduped[:target]
            print(f"[gen] persona={p['persona_id']} qtype={qt} got={len(deduped)} (deduped)")
            persona_rows.extend(deduped)

        # ---- foreigner: 영어 + 질문형 한국어 번역 ----
        if p["lang"] == "en":
            for i, r in enumerate(tqdm(persona_rows, desc=f"translate:{p['persona_id']}"), 1):
                en_q = r["question"]
                r["question_en"] = en_q
                ko_q = translate_en_question_to_ko_question(en_q)

                # 번역도 과잉 조선문구 제거(비교면 유지)
                ko_q = strip_redundant_joseon_prefix(ko_q)

                if "?" not in ko_q:
                    ko_q = ko_q.rstrip(" .!") + "?"
                r["question_ko"] = ko_q

                r.pop("question", None)

                if i % 20 == 0:
                    print(f"[translate] {i}/{len(persona_rows)}")

        # ---- kids: 한국어 질문만 ----
        else:
            for r in persona_rows:
                ko_q = r["question"]
                ko_q = strip_redundant_joseon_prefix(ko_q)
                if "?" not in ko_q:
                    ko_q = ko_q.rstrip(" .!") + "?"
                r["question_ko"] = ko_q
                r.pop("question", None)

        all_rows.extend(persona_rows)

    # persona + qtype 정렬
    all_rows = normalize_and_sort(all_rows)

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"saved: {OUT_PATH} ({len(all_rows)} rows)")
    print("order: persona(foreigner_culture_history -> kids_child) / qtype(SIMPLE -> CONNECTIVE)")

if __name__ == "__main__":
    main()
