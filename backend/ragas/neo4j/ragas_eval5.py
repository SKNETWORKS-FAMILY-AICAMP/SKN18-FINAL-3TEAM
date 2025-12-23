# ragas_eval5.py
"""
GraphDB (Neo4j) 기반 RAG 응답을 RAGAS로 평가 (중간저장/재개 포함) - 5hop 버전

- --debug : 디버그 로그
- --limit : 질문 수 제한
- --save-every : N개 처리마다 중간 저장 (idx 기준 아님: resume/skip 섞여도 안정)

✅ 변경점
- resume 시 "성공(answer 존재)"한 idx만 done 처리 (에러 idx는 재시도)
- OpenAI/파이프라인 에러를 raw.json에 기록 + debug 출력
- metrics: context_relevance, faithfulness (+있으면 answer_relevancy/groundedness도 추가)
- ✅ chat_5hop 사용
- ✅ raw.json에 답변 생성 시간/토큰(입력/출력/합계) 기록
"""

# ===== FORCE PROJECT ROOT INTO PYTHONPATH (MUST BE FIRST) =====
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve()
PROJECT_ROOT = THIS_DIR.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import argparse
import importlib
import pickle
from typing import List

# ✅ 5hop 모듈
from backend.ragas.neo4j.chat_5hop import get_driver, answer_question_structured

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
                    print(f"[DEBUG] metric resolved: {module_name}.{name}()")
                return inst
            except Exception:
                continue
        if debug:
            print(f"[DEBUG] metric resolved: {module_name}.{name}")
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
# Paths
# =====================================================
NEO4J_DIR = Path(__file__).resolve().parent
RAGAS_DIR = NEO4J_DIR.parent

DATA_DIR = RAGAS_DIR / "data"
RUN_DIR = DATA_DIR / "runs"
RUN_DIR.mkdir(parents=True, exist_ok=True)

QUESTIONS_PATH = DATA_DIR / "questions.jsonl"

RAW_PATH = RUN_DIR / "graphdb_eval5.raw.json"
SAMPLES_PATH = RUN_DIR / "graphdb_eval5.samples.pkl"
SCORES_PATH = RUN_DIR / "graphdb_eval5.scores.csv"

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
    """
    ✅ 질문은 무조건 한국어(question_ko)만 사용
    - 없으면 question(한국어일 가능성)로 fallback
    - 그래도 없으면 빈 문자열
    """
    v = item.get("question_ko")
    if isinstance(v, str) and v.strip():
        return v.strip()

    v = item.get("question")
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
        done_idxs = {r["idx"] for r in raw_logs if "idx" in r and "answer" in r}
        print(f"[INFO] Resume from checkpoint: {len(done_idxs)} success samples loaded")
        return raw_logs, samples, done_idxs
    return [], [], set()

def save_checkpoint(raw_logs, samples):
    RAW_PATH.write_text(json.dumps(raw_logs, ensure_ascii=False, indent=2), encoding="utf-8")
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

    evaluate = _resolve_evaluate(debug)

    METRIC_MODULES = ["ragas.metrics", "ragas.metrics.collections"]

    def resolve_from_any(modules, candidates):
        for m in modules:
            try:
                inst = _resolve_metric(m, candidates, debug)
                if inst is not None:
                    return inst
            except Exception:
                continue
        return None

    metric_context_relevance = resolve_from_any(
        METRIC_MODULES,
        ["context_relevance", "ContextRelevance", "context_relevancy", "ContextRelevancy"],
    )
    metric_faithfulness = resolve_from_any(
        METRIC_MODULES,
        ["faithfulness", "Faithfulness"],
    )
    metric_answer_relevancy = resolve_from_any(
        METRIC_MODULES,
        ["answer_relevancy", "AnswerRelevancy", "response_relevancy", "ResponseRelevancy"],
    )
    metric_groundedness = resolve_from_any(
        METRIC_MODULES,
        ["response_groundedness", "ResponseGroundedness", "groundedness", "Groundedness"],
    )

    SingleTurnSample = _import_attr("ragas.dataset_schema", "SingleTurnSample")
    EvaluationDataset = _import_attr("ragas.dataset_schema", "EvaluationDataset")
    if SingleTurnSample is None or EvaluationDataset is None:
        raise ImportError("Cannot resolve ragas.dataset_schema.SingleTurnSample / EvaluationDataset")

    items = load_jsonl(QUESTIONS_PATH)
    if args.limit:
        items = items[: args.limit]

    raw_logs, samples, done_idxs = load_checkpoint()
    driver = get_driver()

    processed = 0  # ✅ idx가 아니라 "처리된 개수" 기준 저장

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
                if debug:
                    print("[PIPELINE ERROR]", repr(e))
                raw_logs.append({"idx": idx, "error": repr(e), "question": q})
                processed += 1
                if processed % args.save_every == 0:
                    save_checkpoint(raw_logs, samples)
                continue

            contexts = ensure_str_contexts(out.get("contexts"))

            samples.append(
                SingleTurnSample(
                    user_input=out.get("question_ko", q),
                    response=out["answer"],
                    retrieved_contexts=contexts,
                    reference=item.get("reference"),
                )
            )

            meta_ans = out.get("llm_meta_answer") or {}
            meta_total = out.get("llm_meta_total") or {}

            raw_logs.append({
                "idx": idx,
                "question": q,
                "answer": out["answer"],
                "n_contexts": len(contexts),

                # ✅ 답변 생성만
                "answer_elapsed_sec": meta_ans.get("elapsed_sec"),
                "answer_input_tokens": meta_ans.get("input_tokens"),
                "answer_output_tokens": meta_ans.get("output_tokens"),
                "answer_total_tokens": meta_ans.get("total_tokens"),

                # ✅ 번역+답변 총합
                "total_elapsed_sec": meta_total.get("elapsed_sec"),
                "total_input_tokens": meta_total.get("input_tokens"),
                "total_output_tokens": meta_total.get("output_tokens"),
                "total_tokens": meta_total.get("total_tokens"),
            })

            processed += 1
            if processed % args.save_every == 0:
                save_checkpoint(raw_logs, samples)

    finally:
        driver.close()

    save_checkpoint(raw_logs, samples)

    if not samples:
        print("[ERROR] no samples generated")
        return

    dataset = EvaluationDataset(samples=samples)

    metrics = [m for m in [
        metric_context_relevance,
        metric_faithfulness,
        metric_answer_relevancy,
        metric_groundedness
    ] if m is not None]

    if not metrics:
        print("[ERROR] no valid metrics resolved")
        return

    result = evaluate(dataset=dataset, metrics=metrics)

    df = result.to_pandas()
    df.to_csv(SCORES_PATH, index=False, encoding="utf-8-sig")

    print("\n=== DONE ===")
    print(df)

if __name__ == "__main__":
    main()
