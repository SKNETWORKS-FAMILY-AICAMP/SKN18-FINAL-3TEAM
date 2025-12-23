# ragas_eval2.py
"""
RAGAS 평가 - 2hop (ragas_eval3 스타일)

✅ 요구사항 반영
- ✅ chat_2hop 사용 (hop 추가 없음)
- retry가 트리거만 돼도 retry_used=True 기록 (out["retry"]["used"])
- raw.json에 retry/제외 여부/사유/토큰/시간 모두 기록
- resume는 done=True만 스킵 (에러도 done 처리)
- ✅ no_info/의미없음도 RAGAS에서 제외하지 않고 "전부 평가"
- ✅ scores.csv 저장 양식: idx + 점수 4개만 저장
  (context_relevance, faithfulness, answer_relevancy, response_groundedness)
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
import re
from typing import List, Dict, Optional

import pandas as pd

from backend.ragas.neo4j.chat_2hop import get_driver, answer_question_structured


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

RAW_PATH = RUN_DIR / "graphdb_eval2.raw.json"
SAMPLES_PATH = RUN_DIR / "graphdb_eval2.samples.pkl"
SCORES_PATH = RUN_DIR / "graphdb_eval2.scores.csv"


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


# "no info" 판별은 ✅ 기록만 하고 "평가 제외 X"
_NOINFO_PATTERNS = [
    r"해당\s*주제에\s*대한\s*구체적\s*기록은\s*확인되지\s*않습니다",
    r"검색되지\s*않",
    r"알\s*수\s*없",
    r"확인할\s*수\s*없",
]


def is_noinfo_answer(answer: str, contexts: List[str]) -> bool:
    a = (answer or "").strip()
    if not a:
        return True
    if contexts and any(("검색되지 않았습니다" in c) for c in contexts):
        return True
    for p in _NOINFO_PATTERNS:
        if re.search(p, a):
            return True
    if len(a) < 15:
        return True
    return False


def load_checkpoint():
    if RAW_PATH.exists() and SAMPLES_PATH.exists():
        raw_logs = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        samples = pickle.loads(SAMPLES_PATH.read_bytes())
        done_idxs = {r["idx"] for r in raw_logs if "idx" in r and r.get("done") is True}
        print(f"[INFO] Resume from checkpoint: {len(done_idxs)} done items loaded")
        return raw_logs, samples, done_idxs
    return [], [], set()


def save_checkpoint(raw_logs, samples):
    RAW_PATH.write_text(json.dumps(raw_logs, ensure_ascii=False, indent=2), encoding="utf-8")
    SAMPLES_PATH.write_bytes(pickle.dumps(samples))
    print(f"[CHECKPOINT] saved ({len(samples)} samples)")


def safe_response_for_ragas(answer: str) -> str:
    a = (answer or "").strip()
    if a:
        return a
    # RAGAS가 빈 response에서 깨질 수 있어서 더미 문장으로 채움 (평가 대상 유지 목적)
    return "정보를 찾을 수 없습니다."


def pick_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


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

    # ✅ idx -> sample_pos (전부 평가이므로 1:1 매핑)
    sample_index_map: Dict[int, int] = {}

    try:
        for idx, item in enumerate(items, start=1):
            if idx in done_idxs:
                continue

            q = pick_question(item)
            if not q:
                raw_logs.append({
                    "idx": idx,
                    "question": "",
                    "error": "empty_question",
                    "done": True,
                })
                if idx % args.save_every == 0:
                    save_checkpoint(raw_logs, samples)
                continue

            try:
                out = answer_question_structured(q, driver)
            except Exception as e:
                if debug:
                    print("[PIPELINE ERROR]", repr(e))
                raw_logs.append({
                    "idx": idx,
                    "question": q,
                    "error": repr(e),
                    "done": True,  # ✅ 에러도 done 처리
                })
                if idx % args.save_every == 0:
                    save_checkpoint(raw_logs, samples)
                continue

            contexts = ensure_str_contexts(out.get("contexts"))
            answer_raw = (out.get("answer") or "").strip()
            answer_for_eval = safe_response_for_ragas(answer_raw)

            retry_obj = out.get("retry") or {}
            retry_used = bool(retry_obj.get("used"))  # ✅ 트리거만 돼도 true

            excluded = is_noinfo_answer(answer_raw, contexts)  # ✅ 기록만 (평가 제외 X)

            # ✅ 무조건 samples에 추가 (전부 평가)
            sample_pos = len(samples)
            sample_index_map[idx] = sample_pos
            samples.append(
                SingleTurnSample(
                    user_input=out.get("question_ko", q),
                    response=answer_for_eval,
                    retrieved_contexts=contexts,
                    reference=item.get("reference"),
                )
            )

            meta_ans = out.get("llm_meta_answer") or {}
            meta_total = out.get("llm_meta_total") or {}

            raw_logs.append({
                "idx": idx,
                "question": q,
                "cypher": out.get("cypher"),

                # ✅ retry 기록
                "retry_used": retry_used,
                "retry": retry_obj,
                "retry_strategy": retry_obj.get("strategy"),

                # ✅ answer / contexts
                "answer": answer_raw,
                "answer_for_eval": answer_for_eval,
                "n_contexts": len(contexts),

                # ✅ 평가 제외는 안 하지만, 상태/사유는 기록
                "excluded_from_eval": excluded,
                "exclude_reason": "no_info_answer" if excluded else None,

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

                "done": True,
            })

            if idx % args.save_every == 0:
                save_checkpoint(raw_logs, samples)

    finally:
        driver.close()

    save_checkpoint(raw_logs, samples)

    # raw 전체
    df_all = pd.DataFrame(raw_logs).sort_values("idx").reset_index(drop=True)

    metrics = [m for m in [
        metric_context_relevance,
        metric_faithfulness,
        metric_answer_relevancy,
        metric_groundedness
    ] if m is not None]

    if samples and metrics:
        dataset = EvaluationDataset(samples=samples)
        result = evaluate(dataset=dataset, metrics=metrics)
        df_scores = result.to_pandas().reset_index(drop=True)

        # scores row index == sample_pos -> idx 복원
        pos_to_idx = {pos: idx for idx, pos in sample_index_map.items()}
        df_scores["idx"] = df_scores.index.map(lambda i: pos_to_idx.get(i))
        df_scores = df_scores.dropna(subset=["idx"])
        df_scores["idx"] = df_scores["idx"].astype(int)

        df_merged = df_all.merge(df_scores, on="idx", how="left")
    else:
        df_merged = df_all.copy()

    # =====================================================
    # ✅ scores.csv 저장: idx + 점수 4개만
    # (ragas 버전에 따라 nv_* 로 바뀌어도 자동 대응)
    # =====================================================
    col_ctx = pick_col(df_merged, ["context_relevance", "nv_context_relevance", "context_relevancy", "nv_context_relevancy"])
    col_fai = pick_col(df_merged, ["faithfulness", "nv_faithfulness"])
    col_ans = pick_col(df_merged, ["answer_relevancy", "nv_answer_relevancy", "response_relevancy", "nv_response_relevancy"])
    col_grd = pick_col(df_merged, ["response_groundedness", "nv_response_groundedness", "groundedness", "nv_groundedness"])

    # 없으면 빈 컬럼 만들어서 "항상 4개" 형태 유지
    if col_ctx is None:
        df_merged["context_relevance"] = float("nan")
        col_ctx = "context_relevance"
    if col_fai is None:
        df_merged["faithfulness"] = float("nan")
        col_fai = "faithfulness"
    if col_ans is None:
        df_merged["answer_relevancy"] = float("nan")
        col_ans = "answer_relevancy"
    if col_grd is None:
        df_merged["response_groundedness"] = float("nan")
        col_grd = "response_groundedness"

    df_out = df_merged[["idx", col_ctx, col_fai, col_ans, col_grd]].copy()
    # 컬럼명 통일(분석 편하게)
    df_out = df_out.rename(columns={
        col_ctx: "context_relevance",
        col_fai: "faithfulness",
        col_ans: "answer_relevancy",
        col_grd: "response_groundedness",
    })

    df_out.to_csv(SCORES_PATH, index=False, encoding="utf-8-sig")

    print("\n=== DONE ===")
    print(f"[INFO] total items  : {len(df_all)}")
    print(f"[INFO] eval samples : {len(samples)}")
    print(f"[INFO] saved        : {SCORES_PATH}")


if __name__ == "__main__":
    main()
