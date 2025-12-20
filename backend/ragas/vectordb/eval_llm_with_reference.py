"""
LLM-only 답변을 질문/참조 정답에 대해 RAGAS로 평가하는 스크립트.

- 외부 컨텍스트(벡터 검색 결과)를 사용하지 않는다.
- 컨텍스트 기반 메트릭을 포함하지 않는다.
- 평가 지표는 answer_relevancy, answer_correctness 두 가지뿐이다.

입력 파일
- questions.jsonl          : 질문 목록 (idx, qtype, question_ko/en 등)
- llm_answer_eval.json     : LLM이 생성한 답변(JSONL, idx/question/answer)
- reference_answers.jsonl  : 사람이 채운 참조 정답(JSONL, idx/question/reference_answer)

출력 파일
- eval_results.json        : 질문별 평가 점수 JSONL
- eval_raw.json            : 점수 계산에 쓴 레코드 + 점수 원본
"""

import json
from pathlib import Path

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    answer_correctness,
)
from backend.db_pipeline.common.config import OPENAI_API_KEY
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# 경로 설정 (backend/ragas 폴더 기준)
BASE = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = BASE / "questions.jsonl"
ANSWERS_PATH = BASE / "llm_answer_eval.json"
REFERENCE_PATH = BASE / "reference_answers.jsonl"
OUT_RESULTS = BASE / "eval_results.json"
OUT_RAW = BASE / "eval_raw.json"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def merge_records(questions: list[dict], answers: list[dict], refs: list[dict]) -> list[dict]:
    """idx 기준으로 질문/답변/참조 정답을 합쳐 평가 레코드를 만든다."""
    answers_by_idx = {int(a["idx"]): a for a in answers if "idx" in a}
    refs_by_idx = {int(r["idx"]): r for r in refs if "idx" in r}

    merged: list[dict] = []
    for q in questions:
        idx = int(q.get("idx") or len(merged) + 1)
        answer_rec = answers_by_idx.get(idx)
        ref_rec = refs_by_idx.get(idx)
        if not answer_rec or not ref_rec:
            continue

        question_text = q.get("question_ko") or q.get("question") or q.get("question_en") or ""
        llm_answer = answer_rec.get("answer", "")
        reference_answer = ref_rec.get("reference_answer", "")

        merged.append(
            {
                "idx": idx,
                "question": question_text,
                "qtype": q.get("qtype"),
                "answer": llm_answer,
                "ground_truth": reference_answer,
                # LLM-only: 컨텍스트 메트릭을 쓰지 않으므로 빈 리스트 유지
                "retrieved_contexts": [],
            }
        )
    return merged


def run():
    questions = load_jsonl(QUESTIONS_PATH)
    answers = load_jsonl(ANSWERS_PATH)
    refs = load_jsonl(REFERENCE_PATH)

    records = merge_records(questions, answers, refs)
    if not records:
        raise ValueError("병합된 레코드가 없습니다. idx/파일을 확인하세요.")

    metrics = [
        answer_relevancy,   # 질문 대비 답변 관련성
        answer_correctness, # 참조 정답 대비 정확도
    ]

    ds = Dataset.from_list(
        [
            {
                "question": r["question"],
                "answer": r["answer"],
                "ground_truth": r["ground_truth"],
                "retrieved_contexts": r["retrieved_contexts"],
            }
            for r in records
        ]
    )

    llm_client = ChatOpenAI(model_name="gpt-4o-mini", api_key=OPENAI_API_KEY)
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
    result = evaluate(dataset=ds, metrics=metrics, llm=llm_client, embeddings=embeddings)

    df = result.to_pandas()

    OUT_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_RESULTS.open("w", encoding="utf-8") as f:
        for rec, row in zip(records, df.to_dict(orient="records")):
            f.write(
                json.dumps(
                    {
                        "idx": rec["idx"],
                        "qtype": rec["qtype"],
                        "question": rec["question"],
                        "metrics": {
                            "answer_relevancy": row.get("answer_relevancy", row.get("answer_relevance")),
                            "answer_correctness": row.get("answer_correctness"),
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    with OUT_RAW.open("w", encoding="utf-8") as f:
        for row in df.to_dict(orient="records"):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Saved metrics to {OUT_RESULTS}")
    print(f"Saved raw result to {OUT_RAW}")


if __name__ == "__main__":
    run()
