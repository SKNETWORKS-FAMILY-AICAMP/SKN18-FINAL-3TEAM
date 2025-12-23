"""
graphdb_eval.scores.csv 에서
본문 컬럼(user_input, retrieved_contexts, response)을 제거하고
점수 컬럼만 남긴 CSV를 새로 저장하는 스크립트
"""

from pathlib import Path
import pandas as pd


# =========================
# Paths
# =========================

BASE_DIR = Path(__file__).resolve().parents[1]
# backend/ragas

RUN_DIR = BASE_DIR / "data" / "runs"

IN_PATH = RUN_DIR / "graphdb_eval.scores.csv"
OUT_PATH = RUN_DIR / "graphdb_eval.scores.only_scores.csv"


# =========================
# Main
# =========================

def main():
    if not IN_PATH.exists():
        raise FileNotFoundError(f"input csv not found: {IN_PATH}")

    df = pd.read_csv(IN_PATH)

    # 🔥 본문 컬럼 전부 제거
    DROP_COLS = {"user_input", "retrieved_contexts", "response"}
    df = df[[c for c in df.columns if c not in DROP_COLS]]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    print(f"[SAVED] {OUT_PATH}")
    print("columns:", list(df.columns))
    print(df.head())


if __name__ == "__main__":
    main()
