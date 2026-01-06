import pandas as pd
from pathlib import Path

p = Path("backend/ragas/hybrid/runs/hybrid_full_1by1/results1.csv")

df = pd.read_csv(p)

drop_cols = [c for c in ["persona_id", "question", "answer"] if c in df.columns]
df = df.drop(columns=drop_cols)

# 🔹 새 파일명
out_path = p.with_name("results_score1.csv")

df.to_csv(out_path, index=False, encoding="utf-8-sig")

print(f"[OK] dropped={drop_cols}")
print(f"[SAVE] {out_path}")
