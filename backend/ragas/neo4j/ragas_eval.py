# ragas_eval.py
"""
GraphDB (Neo4j) 기반 RAG 응답을 RAGAS로 평가 (중간저장/재개 포함)

- --debug : 디버그 로그
- --limit : 질문 수 제한
- --save-every : N개마다 중간 저장
"""

# ===== FORCE PROJECT ROOT INTO PYTHONPATH (MUST BE FIRST) =====
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve()                 # .../backend/ragas/neo4j/ragas_eval.py
PROJECT_ROOT = THIS_DIR.parents[3]                 # .../SKN18-FINAL-3TEAM

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import argparse
import importlib
import pickle
from typing import List

# ✅ chat 파일명이 chat_1hop.py 이므로 여기로 import
from backend.ragas.neo4j.chat_1hop import get_driver, answer_question_structured


# =====================================================
# RAGAS safe import
# =====================================================
def _import_attr(module_name: str, attr_name: str):
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, attr_name)
    except Exception:
        return None


def _resolve_metric(module_name: str, candidates: List[str], debug=False):
    mod = importlib.import_module(module_name)
    for name in candidates:
        obj = getattr(mod, name, None)
        if obj is None:
            continue
        if isinstance(obj, type):
            try:
                inst = obj()
                if debug:
                    print(f"[DEBUG] metric resolved: {name}()")
                return inst
            except Exception:
                continue
        if debug:
            print(f"[DEBUG] metric resolved: {name}")
        return obj
    return None


def _resolve_evaluate(debug=False):
    fn = _import_attr("ragas", "evaluate")
    if fn:
        if debug:
            print("[DEBUG] evaluate resolved: ragas.evaluate")
        return fn
    fn = _import_attr("ragas.evaluation", "evaluate")
    if fn:
        if debug:
            print("[DEBUG] evaluate resolved: ragas.evaluation.evaluate")
        return fn
    raise ImportError("Cannot resolve ragas.evaluate")


# =====================================================
# Path (✅ data 폴더는 backend/ragas/data)
# =====================================================
NEO4J_DIR = Path(__file__).resolve().parent         # .../backend/ragas/neo4j
RAGAS_DIR = NEO4J_DIR.parent                        # .../backend/ragas

DATA_DIR = RAGAS_DIR / "data"
RUN_DIR = DATA_DIR / "runs"
RUN_DIR.mkdir(parents=True, exist_ok=True)

QUESTIONS_PATH = DATA_DIR / "questions.jsonl"

RAW_PATH = RUN_DIR / "graphdb_eval.raw.json"
SAMPLES_PATH = RUN_DIR / "graphdb_eval.samples.pkl"


# =====================================================
# Utils
# =====================================================
def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def pick_question(item: dict) -> str:
    for k in ("question_en", "question_ko", "question"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def ensure_str_contexts(contexts):
    out = []
    for c in contexts or []:
        if isinstance(c, str):
            out.append(c)
        else:
            try:
                out.append(json.dumps(c, ensure_ascii=False))
            except Exception:
                out.append(str(c))
    return out


def load_checkpoint():
    if RAW_PATH.exists() and SAMPLES_PATH.exists():
        raw_logs = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        samples = pickle.loads(SAMPLES_PATH.read_bytes())
        done_idxs = {r["idx"] for r in raw_logs if "idx" in r}
        print(f"[INFO] Resume from checkpoint: {len(done_idxs)} samples loaded")
        return raw_logs, samples, done_idxs
    return [], [], set()


def save_checkpoint(raw_logs, samples):
    RAW_PATH.write_text(
        json.dumps(raw_logs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    SAMPLES_PATH.write_bytes(pickle.dumps(samples))
    print(f"[CHECKPOINT] saved ({len(samples)} samples)")


# =====================================================
# Main
# =====================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--save-every", type=int, default=20)
    args = parser.parse_args()

    debug = args.debug

    if not QUESTIONS_PATH.exists():
        print(f"[ERROR] questions file not found: {QUESTIONS_PATH}")
        return

    # ---- ragas resolve ----
    evaluate = _resolve_evaluate(debug)

    metric_context_relevance = _resolve_metric(
        "ragas.metrics", ["context_relevance", "ContextRelevance"], debug
    )
    metric_groundedness = _resolve_metric(
        "ragas.metrics",
        ["response_groundedness", "ResponseGroundedness", "faithfulness", "Faithfulness"],
        debug,
    )
    metric_answer_relevancy = _resolve_metric(
        "ragas.metrics",
        ["answer_relevancy", "AnswerRelevancy", "answer_relevance", "AnswerRelevance"],
        debug,
    )
    metric_answer_accuracy = _resolve_metric(
        "ragas.metrics",
        ["answer_accuracy", "AnswerAccuracy", "answer_correctness", "AnswerCorrectness"],
        debug,
    )

    SingleTurnSample = _import_attr("ragas.dataset_schema", "SingleTurnSample")
    EvaluationDataset = _import_attr("ragas.dataset_schema", "EvaluationDataset")

    if SingleTurnSample is None or EvaluationDataset is None:
        raise ImportError("Cannot resolve ragas.dataset_schema.SingleTurnSample / EvaluationDataset")

    # ---- load data ----
    items = load_jsonl(QUESTIONS_PATH)
    if args.limit:
        items = items[: args.limit]

    raw_logs, samples, done_idxs = load_checkpoint()

    driver = get_driver()

    try:
        for idx, item in enumerate(items, start=1):
            if idx in done_idxs:
                continue

            q = pick_question(item)
            if not q:
                continue

            try:
                out = answer_question_structured(q, driver)
            except Exception as e:
                raw_logs.append({
                    "idx": idx,
                    "error": repr(e),
                    "question": q,
                })
                continue

            contexts = ensure_str_contexts(out.get("contexts"))

            samples.append(
                SingleTurnSample(
                    user_input=out["question_ko"],
                    response=out["answer"],
                    retrieved_contexts=contexts,
                    reference=item.get("reference"),
                )
            )

            raw_logs.append({
                "idx": idx,
                "question": q,
                "answer": out["answer"],
                "n_contexts": len(contexts),
            })

            if idx % args.save_every == 0:
                save_checkpoint(raw_logs, samples)

    finally:
        driver.close()

    # ---- final save ----
    save_checkpoint(raw_logs, samples)

    if not samples:
        print("[ERROR] no samples generated")
        return

    dataset = EvaluationDataset(samples=samples)

    metrics = [metric_context_relevance, metric_groundedness]
    if metric_answer_relevancy:
        metrics.append(metric_answer_relevancy)
    if metric_answer_accuracy and any(getattr(s, "reference", None) for s in samples):
        metrics.append(metric_answer_accuracy)

    result = evaluate(dataset=dataset, metrics=metrics)

    df = result.to_pandas()
    df.to_csv(RUN_DIR / "graphdb_eval.scores.csv", index=False, encoding="utf-8-sig")

    print("\n=== DONE ===")
    print(df)


if __name__ == "__main__":
    main()
