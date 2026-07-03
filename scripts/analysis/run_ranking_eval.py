#!/usr/bin/env python3
"""Solvent-ranking evaluation (the actual screening task).

Absolute ln x2 MAE is the wrong success metric for solvent selection and is
sensitive to label noise / systematic offsets. What matters operationally is
whether the model RANKS candidate solvents correctly for a given solute. Ranking
metrics are invariant to monotone per-solute shifts, so a physics-structured
model can win here even when its MAE does not.

For each (solute, temperature) group with >=k solvents we rank solvents by
predicted vs measured ln x2 and report Spearman rho, Kendall tau, best-solvent
top-1 accuracy, and NDCG@k, aggregated (mean) over groups.

Model-agnostic: consumes any predictions CSV with columns solute_smiles,
solvent_smiles, T (or temperature), ln_x2_true, ln_x2_pred.

    python scripts/analysis/run_ranking_eval.py \
        --predictions-csv results/e0_compensation/tgnn_mpnn_test_predictions.csv \
        --out-json results/ranking/tgnn_mpnn_ranking.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--predictions-csv", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--min-solvents", type=int, default=3,
                   help="Minimum solvents per (solute, T) group to score it.")
    p.add_argument("--t-tol", type=float, default=1.0, help="Temperature rounding [K].")
    p.add_argument("--ndcg-k", type=int, default=3)
    p.add_argument("--true-col", default="ln_x2_true")
    p.add_argument("--pred-col", default="ln_x2_pred")
    return p.parse_args()


def _ndcg(true: np.ndarray, pred: np.ndarray, k: int) -> float:
    """NDCG@k with relevance = rank of the true value (higher solubility better)."""
    n = len(true)
    k = min(k, n)
    rel = true.argsort().argsort().astype(float)  # 0..n-1, higher=more soluble
    order_pred = np.argsort(-pred)[:k]
    gains = (2.0 ** rel[order_pred] - 1.0)
    discounts = 1.0 / np.log2(np.arange(2, k + 2))
    dcg = float((gains * discounts).sum())
    order_ideal = np.argsort(-rel)[:k]
    idcg = float(((2.0 ** rel[order_ideal] - 1.0) * discounts).sum())
    return dcg / idcg if idcg > 0 else float("nan")


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.predictions_csv, low_memory=False)
    if "T" not in df.columns and "temperature" in df.columns:
        df = df.rename(columns={"temperature": "T"})
    if "has_solubility" in df.columns:
        raw = df["has_solubility"].astype(str).str.lower()
        df = df[raw.isin({"true", "1", "1.0", "yes"}) | (pd.to_numeric(df["has_solubility"], errors="coerce") > 0)]
    df = df.dropna(subset=["solute_smiles", "solvent_smiles", "T", args.true_col, args.pred_col])
    df["Tr"] = (pd.to_numeric(df["T"], errors="coerce") / args.t_tol).round() * args.t_tol

    spearmans, kendalls, top1, ndcgs, sizes = [], [], [], [], []
    for _, grp in df.groupby(["solute_smiles", "Tr"]):
        # one row per solvent (average duplicate measurements)
        g = grp.groupby("solvent_smiles").agg(
            t=(args.true_col, "mean"), p=(args.pred_col, "mean")
        )
        if len(g) < args.min_solvents:
            continue
        t = g["t"].to_numpy(float)
        p = g["p"].to_numpy(float)
        if np.std(t) == 0 or np.std(p) == 0:
            continue
        rho, _ = spearmanr(t, p)
        tau, _ = kendalltau(t, p)
        if np.isfinite(rho):
            spearmans.append(float(rho))
        if np.isfinite(tau):
            kendalls.append(float(tau))
        top1.append(float(np.argmax(p) == np.argmax(t)))
        ndcgs.append(_ndcg(t, p, args.ndcg_k))
        sizes.append(int(len(g)))

    def _agg(x: list[float]) -> dict[str, Any]:
        a = np.array([v for v in x if np.isfinite(v)], dtype=float)
        return {"mean": float(a.mean()) if a.size else None,
                "median": float(np.median(a)) if a.size else None, "n": int(a.size)}

    summary = {
        "predictions_csv": str(Path(args.predictions_csv).resolve()),
        "n_groups_scored": len(sizes),
        "mean_solvents_per_group": float(np.mean(sizes)) if sizes else None,
        "spearman": _agg(spearmans),
        "kendall_tau": _agg(kendalls),
        "best_solvent_top1_accuracy": _agg(top1),
        f"ndcg_at_{args.ndcg_k}": _agg(ndcgs),
        "interpretation": (
            "Ranking is the screening-relevant metric and is invariant to per-solute "
            "offsets/label noise; report alongside MAE. High Spearman / top-1 with "
            "mediocre MAE means the model still selects solvents correctly."
        ),
    }
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "interpretation"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
