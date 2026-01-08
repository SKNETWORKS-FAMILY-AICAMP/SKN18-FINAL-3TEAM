"""
LangGraph(app_ver1 / langgraph_structure1) -> 답변 생성 -> RAGAS 평가
저장: 질문/답변/시간/토큰/점수만 (contexts/cypher/retry/raw 저장 X)
1개 처리마다 results.csv 즉시 저장

✅ LangGraph는 건드리지 않고, 이 스크립트에서:
- 생성시간(perf_counter) 강제 측정
- total시간 = 생성 + 평가 시간
- 토큰은 (가능하면 tiktoken) 없으면 char//4 근사로 추정치 채움
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
import traceback
import time
import inspect
from typing import Any, Dict, List, Optional, Callable

import pandas as pd
from dotenv import load_dotenv


# ---------------- Token estimator (best-effort) ----------------
def _get_token_estimator():
    """
    1) tiktoken 있으면 cl100k_base로 계산
    2) 없으면 1 token ~= 4 chars 근사
    """
    try:
        import tiktoken  # type: ignore

        enc = tiktoken.get_encoding("cl100k_base")

        def est(text: str) -> int:
            text = text or ""
            return len(enc.encode(text))

        return est
    except Exception:

        def est(text: str) -> int:
            text = text or ""
            return max(0, (len(text) + 3) // 4)

        return est


_EST_TOKENS = _get_token_estimator()


# ---------------- Small utils ----------------
def _pick_first(d: Dict[str, Any], keys: List[str], default=None):
    for k in keys:
        if k in d and d[k] is not None and d[k] != "":
            return d[k]
    return default


def _import_attr(module_name: str, attr_name: str):
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, attr_name)
    except Exception:
        return None


def _find_graph_factory() -> Callable[[], Any]:
    """
    langgraph_structure1의 graph 생성 함수를 최대한 유연하게 찾는다.
    - backend.langgraph_structure1.graph 모듈에서 아래 이름들을 순서대로 탐색
    """
    module_candidates = [
        "backend.langgraph_structure1.graph",
        "backend.langgraph_structure1.graphpy",  # 혹시 모듈명이 다를 경우 대비(거의 안씀)
    ]
    factory_names = [
        "create_graph_flow",
        "create_graph",
        "build_graph",
        "get_graph",
        "make_graph",
        "create_app",
        "build_app",
    ]

    last_err = None
    for m in module_candidates:
        try:
            mod = importlib.import_module(m)
        except Exception as e:
            last_err = e
            continue

        for fn in factory_names:
            f = getattr(mod, fn, None)
            if callable(f):
                return f

    raise RuntimeError(
        "Cannot find graph factory in backend.langgraph_structure1.graph "
        f"(tried: {factory_names}). last_err={last_err}"
    )


async def _run_app(app: Any, initial_state: Dict[str, Any]) -> Any:
    """
    app 실행을 최대한 호환되게 처리:
    - app.ainvoke 있으면 await app.ainvoke()
    - app.invoke 있으면 app.invoke()
    - app callable이면 app(initial_state)
    """
    if hasattr(app, "ainvoke") and callable(getattr(app, "ainvoke")):
        return await app.ainvoke(initial_state)
    if hasattr(app, "invoke") and callable(getattr(app, "invoke")):
        return app.invoke(initial_state)
    if callable(app):
        r = app(initial_state)
        # callable이 coroutine을 반환하면 await
        if inspect.isawaitable(r):
            return await r
        return r
    raise RuntimeError("Graph app is not invokable (no ainvoke/invoke/callable).")


# ---------------- LangGraph runner (app_ver1) ----------------
async def answer_with_appver1(question: str, tag: str = "chat") -> Dict[str, Any]:
    """
    langgraph_structure1의 그래프를 만들어 ainvoke로 실행.

    ✅ 여기서 채움
    - gen_elapsed_sec: perf_counter로 강제 측정
    - llm_meta_answer/total: 없으면 시간/토큰 추정치로 채움
    """
    # lazy import & factory discovery
    factory = _find_graph_factory()
    app = factory()

    # app_ver2와 동일하게 query/tag를 넣되,
    # 혹시 구조1이 question 키를 쓰는 경우도 대비해서 같이 넣음
    initial_state = {"query": question, "question": question, "tag": tag}

    # ✅ 생성 시간 강제 측정
    t0 = time.perf_counter()
    out = await _run_app(app, initial_state)
    gen_elapsed = time.perf_counter() - t0

    if out is None:
        out = {}

    # 답변 키 후보
    answer = _pick_first(out, ["answer", "final_answer", "response", "output"], default="")

    # contexts 키 후보 (RAGAS 평가용, 저장은 안 함)
    contexts = _pick_first(
        out,
        ["contexts", "retrieved_contexts", "rag_contexts", "graph_contexts", "neo4j_contexts"],
        default=[],
    )
    if contexts is None:
        contexts = []
    if isinstance(contexts, str):
        contexts = [contexts]

    # 시간/토큰 키 후보 (없으면 None)
    llm_a = _pick_first(out, ["llm_meta_answer", "answer_meta", "meta_answer"], default={}) or {}
    llm_t = _pick_first(out, ["llm_meta_total", "total_meta", "meta_total"], default={}) or {}

    # ✅ 시간 fallback 채우기
    if llm_a.get("elapsed_sec") is None:
        llm_a["elapsed_sec"] = gen_elapsed
    if llm_t.get("elapsed_sec") is None:
        llm_t["elapsed_sec"] = gen_elapsed  # main에서 eval 포함으로 덮어쓸 것

    # ✅ 토큰 fallback(추정치) 채우기
    q_text = question or ""
    a_text = (answer or "")
    ctx_text = "\n".join([str(c) for c in contexts]) if contexts else ""

    # answer_total_tokens: 질문+답변 기준
    est_answer_total = _EST_TOKENS(q_text) + _EST_TOKENS(a_text)
    # total_total_tokens: 질문+답변+컨텍스트 기준(대충)
    est_total_total = est_answer_total + _EST_TOKENS(ctx_text)

    if llm_a.get("total_tokens") is None:
        llm_a["total_tokens"] = est_answer_total
    if llm_t.get("total_tokens") is None:
        llm_t["total_tokens"] = est_total_total

    return {
        "answer": (answer or "").strip(),
        "contexts": contexts,
        "llm_meta_answer": llm_a,
        "llm_meta_total": llm_t,
        "raw_state": out,  # 디버그용(저장 X)
    }


# ---------------- RAGAS helpers ----------------
def load_ragas_evaluate():
    ev = _import_attr("ragas", "evaluate") or _import_attr("ragas.evaluation", "evaluate")
    if ev is None:
        raise RuntimeError("Cannot import ragas.evaluate")
    return ev


def _resolve_metric(module_name: str, names: List[str]):
    mod = importlib.import_module(module_name)
    for n in names:
        obj = getattr(mod, n, None)
        if obj is None:
            continue
        try:
            return obj() if isinstance(obj, type) else obj
        except Exception:
            continue
    return None


def load_metrics():
    specs = [
        ("ragas.metrics", ["context_relevance", "ContextRelevance", "nv_context_relevance", "NVContextRelevance"]),
        ("ragas.metrics", ["faithfulness", "Faithfulness", "nv_faithfulness", "NVFaithfulness"]),
        ("ragas.metrics", ["answer_relevancy", "AnswerRelevancy", "nv_answer_relevancy", "NVAnswerRelevancy"]),
        ("ragas.metrics", ["response_groundedness", "ResponseGroundedness", "nv_response_groundedness", "NVResponseGroundedness"]),
    ]
    ms = []
    for mod, names in specs:
        try:
            m = _resolve_metric(mod, names)
            if m is not None:
                ms.append(m)
        except Exception:
            pass
    if len(ms) < 2:
        raise RuntimeError("Need at least context_relevance & faithfulness")
    return ms


def build_ragas_dataset(samples: List[Dict[str, Any]]):
    for mod, name in [
        ("ragas.dataset", "EvaluationDataset"),
        ("ragas.dataset", "Dataset"),
        ("ragas.datasets", "EvaluationDataset"),
        ("ragas.datasets", "Dataset"),
        ("ragas", "EvaluationDataset"),
        ("ragas", "Dataset"),
    ]:
        cls = _import_attr(mod, name)
        if cls is None:
            continue
        for ctor in ("from_list", "from_dict", "from_pandas"):
            if hasattr(cls, ctor):
                try:
                    return getattr(cls, ctor)(samples)
                except Exception:
                    pass
        try:
            return cls(samples)
        except Exception:
            pass
    try:
        from datasets import Dataset as HFDataset  # type: ignore
        return HFDataset.from_list(samples)
    except Exception:
        return samples


def ragas_to_scores_dict(ragas_out) -> Dict[str, Any]:
    if hasattr(ragas_out, "to_pandas"):
        pdf = ragas_out.to_pandas()
        if len(pdf) > 0:
            return pdf.iloc[0].to_dict()
    if isinstance(ragas_out, dict):
        return ragas_out
    try:
        pdf = pd.DataFrame(ragas_out)
        if len(pdf) > 0:
            return pdf.iloc[0].to_dict()
    except Exception:
        pass
    return {}


def _norm(s: Any) -> str:
    return str(s or "").strip().lower().replace(" ", "").replace("-", "_")


def map_scores(scores: Dict[str, Any], metric_names: List[str]) -> Dict[str, Any]:
    ns = {_norm(k): v for k, v in (scores or {}).items()}
    out = {}
    for mn in metric_names:
        k = _norm(mn)
        if k in ns:
            out[mn] = ns[k]
            continue
        t = k[3:] if k.startswith("nv_") else "nv_" + k
        if t in ns:
            out[mn] = ns[t]
            continue
        out[mn] = None
    return out


def r3(x: Any):
    try:
        return None if x is None else round(float(x), 3)
    except Exception:
        return x


# ---------------- Questions ----------------
def read_questions_jsonl(path: Path) -> List[Dict[str, Any]]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            q = (
                obj.get("question")
                or obj.get("question_ko")
                or obj.get("question_en")
                or obj.get("q")
                or obj.get("query")
                or obj.get("prompt")
            )
            if not q:
                raise RuntimeError(f"Missing question at line {i}")
            out.append(
                {
                    "idx": int(obj.get("idx", i)),
                    "question": q,
                    "qtype": obj.get("qtype"),
                    "persona_id": obj.get("persona_id"),
                }
            )
    return out


def load_done_set(results_csv: Path) -> set:
    if not results_csv.exists():
        return set()
    try:
        df = pd.read_csv(results_csv)
        if "idx" not in df.columns or "done" not in df.columns:
            return set()
        return set(df.loc[df["done"] == True, "idx"].dropna().astype(int).tolist())  # noqa
    except Exception:
        return set()


# ---------------- Main ----------------
def main():
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(PROJECT_ROOT / "backend" / "ragas" / "questions.jsonl"))
    ap.add_argument("--outdir", default=str(PROJECT_ROOT / "backend" / "ragas" / "appver1" / "runs"))
    ap.add_argument("--run-name", default="appver1_results_only")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--tag", default="chat", help="initial_state['tag'] value (default: chat)")
    args = ap.parse_args()

    run_dir = Path(args.outdir) / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    results_csv = run_dir / "results.csv"

    items = read_questions_jsonl(Path(args.questions))
    if args.limit and args.limit > 0:
        items = items[: args.limit]

    done_set = load_done_set(results_csv) if args.resume else set()

    ragas_evaluate = load_ragas_evaluate()
    metrics = load_metrics()
    metric_names = [getattr(m, "name", None) or m.__class__.__name__ for m in metrics]

    cols = [
        "idx",
        "persona_id",
        "qtype",
        "question",
        "answer",
        *metric_names,
        "answer_elapsed_sec",
        "answer_total_tokens",
        "total_elapsed_sec",
        "total_total_tokens",
        "eval_ok",
        "eval_error",
        "done",
    ]

    # results.csv 로드/초기화
    if results_csv.exists():
        df = pd.read_csv(results_csv)
        for c in cols:
            if c not in df.columns:
                df[c] = pd.NA
    else:
        df = pd.DataFrame(columns=cols)

    # row 보장
    existing = set(df["idx"].dropna().astype(int).tolist()) if "idx" in df.columns else set()
    for it in items:
        idx = int(it["idx"])
        if idx not in existing:
            row = {c: pd.NA for c in cols}
            row.update(
                {
                    "idx": idx,
                    "persona_id": it.get("persona_id"),
                    "qtype": it.get("qtype"),
                    "question": it["question"],
                    "done": False,
                }
            )
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    df["idx"] = pd.to_numeric(df["idx"], errors="coerce")
    df = df.sort_values("idx").reset_index(drop=True)

    import asyncio

    for it in items:
        idx = int(it["idx"])
        if idx in done_set:
            if args.debug:
                print(f"[RESUME] skip idx={idx}")
            continue

        question = it["question"]
        mask = df["idx"] == idx

        try:
            # 1) 답변 생성 (LangGraph - app_ver1 구조)
            result = asyncio.run(answer_with_appver1(question, tag=args.tag))
            contexts = result.get("contexts") or []
            answer = (result.get("answer") or "").strip()

            llm_a = result.get("llm_meta_answer") or {}
            llm_t = result.get("llm_meta_total") or {}

            # 2) RAGAS 평가 (contexts는 메모리에서만 사용)
            eval_ok = True
            eval_error: Optional[str] = None
            scores_mapped = {mn: None for mn in metric_names}

            te0 = time.perf_counter()
            try:
                user_input = question
                samples = [
                    {
                        "user_input": user_input,
                        "response": answer,
                        "retrieved_contexts": contexts,
                        # 호환키
                        "question": user_input,
                        "answer": answer,
                        "contexts": contexts,
                    }
                ]
                ragas_dataset = build_ragas_dataset(samples)
                ragas_out = ragas_evaluate(ragas_dataset, metrics=metrics)
                scores_raw = ragas_to_scores_dict(ragas_out)
                scores_mapped = map_scores(scores_raw, metric_names)
            except Exception as e:
                eval_ok = False
                eval_error = f"{type(e).__name__}: {e}"
                if args.debug:
                    print(f"[EVAL-ERROR] idx={idx} {eval_error}")
            eval_elapsed = time.perf_counter() - te0

            # ✅ total elapsed = 생성 + 평가
            gen_elapsed = llm_a.get("elapsed_sec") or 0.0
            try:
                llm_t["elapsed_sec"] = float(gen_elapsed) + float(eval_elapsed)
            except Exception:
                llm_t["elapsed_sec"] = None

            # 3) 저장(질문/답변/시간/토큰/점수만)
            df.loc[mask, "persona_id"] = it.get("persona_id")
            df.loc[mask, "qtype"] = it.get("qtype")
            df.loc[mask, "question"] = question
            df.loc[mask, "answer"] = answer

            for mn in metric_names:
                df.loc[mask, mn] = scores_mapped.get(mn)

            df.loc[mask, "answer_elapsed_sec"] = r3(llm_a.get("elapsed_sec"))
            df.loc[mask, "answer_total_tokens"] = llm_a.get("total_tokens")
            df.loc[mask, "total_elapsed_sec"] = r3(llm_t.get("elapsed_sec"))
            df.loc[mask, "total_total_tokens"] = llm_t.get("total_tokens")

            df.loc[mask, "eval_ok"] = eval_ok
            df.loc[mask, "eval_error"] = eval_error
            df.loc[mask, "done"] = True

            df.to_csv(results_csv, index=False, encoding="utf-8-sig")
            if args.debug:
                print(f"[SAVE-1] idx={idx} results.csv updated (eval_ok={eval_ok})")

        except Exception as e:
            if args.debug:
                print(f"[ERROR] idx={idx} {type(e).__name__}: {e}")
                print(traceback.format_exc())
            df.to_csv(results_csv, index=False, encoding="utf-8-sig")

    print(f"[DONE] results: {results_csv}")


if __name__ == "__main__":
    main()
