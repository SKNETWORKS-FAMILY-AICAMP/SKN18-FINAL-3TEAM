import asyncio
import json
import time
from pathlib import Path

from backend.langgraph_structure1.graph import create_graph_flow
from langchain_openai import ChatOpenAI

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    ContextRelevance,
    answer_relevancy,
    faithfulness,
    ResponseGroundedness,
)

# ragas 메트릭 인스턴스
metrics = [
    ContextRelevance(),
    answer_relevancy,
    faithfulness,
    ResponseGroundedness(),
]


QUESTIONS_PATH = Path(__file__).resolve().parents[1] / "questions_sample.jsonl"
OUT_RAW = Path(__file__).resolve().parents[1] / "eval_raw.json"
OUT_JSON = Path(__file__).resolve().parents[1] / "eval_results.json"


def load_questions(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def pick_question(item: dict, use_lang: str = "ko") -> str:
    return item.get(f"question_{use_lang}") or item.get("question") or ""


# 비동기 실행
async def run_eval():
    items = load_questions(QUESTIONS_PATH)
    if not items:
        raise ValueError(f"질문 파일이 비어 있습니다: {QUESTIONS_PATH}")

    app = create_graph_flow()

    records = []
    raw_logs = []

    for idx, item in enumerate(items, start=1):
        q = pick_question(item)
        if not q:
            continue

        try:
            state = await app.ainvoke({"query": q, "t0": time.perf_counter()})
        except Exception as e:
            raw_logs.append({"idx": idx, "question": q, "error": repr(e)})
            continue

        qtype = item.get("qtype")

        contexts = []
        for ev in state.get("vector_evidences", []):
            content = ev.get("payload", {}).get("content")
            if content:
                contexts.append(content)

        records.append(
            {
                "question": q,
                "qtype": qtype,
                "answer": state.get("final_answer", ""),
                "contexts": contexts,
            }
        )
        raw_logs.append(
            {
                "idx": idx,
                "question": q,
                "qtype": qtype,
                "answer": state.get("final_answer", ""),
                "n_contexts": len(contexts),
                "answer_input_tokens": state.get("answer_input_tokens"),
                "answer_output_tokens": state.get("answer_output_tokens"),
                "answer_total_tokens": state.get("answer_total_tokens"),
                "retrieval_elapsed": state.get("retrieval_elapsed"),
                "final_answer_elapsed": state.get("final_answer_elapsed"),
            }
        )

        # 매 건 처리 후 바로 평가/저장 (append)
        OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
        with OUT_RAW.open("a", encoding="utf-8") as f:
            f.write(json.dumps(raw_logs[-1], ensure_ascii=False) + "\n")

        # 바로 직전 샘플 1건만 평가
        ds = Dataset.from_list([records[-1]])
        result = evaluate(
            dataset=ds,
            metrics=metrics,
            llm = ChatOpenAI(model_name="gpt-4o-mini")
        )

        df = result.to_pandas()
        row = df.iloc[0].to_dict()

        # JSONL: idx/question/qtype + 메트릭만 저장
        metrics_payload = {
            "context_relevance": row.get("context_relevance", row.get("nv_context_relevance")),
            "answer_relevancy": row.get("answer_relevancy", row.get("answer_relevance")),
            "faithfulness": row.get("faithfulness"),
            "response_groundedness": row.get("response_groundedness", row.get("nv_response_groundedness")),
        }
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        with OUT_JSON.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "idx": idx,
                        "question": q,
                        "qtype": qtype,
                        "metrics": metrics_payload,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

        print(f"[{idx}/{len(items)}] {q}")
        print(result)
        print(f"Appended raw log to {OUT_RAW}")
        print(f"Appended metrics json to {OUT_JSON}")


def main():
    asyncio.run(run_eval())


if __name__ == "__main__":
    main()
