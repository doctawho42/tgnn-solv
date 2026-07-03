#!/usr/bin/env python3
"""E3 aggregator: same-pair temperature-extrapolation leaderboard (tests T4).

Combines the classical baselines from
``scripts/evaluation/run_temperature_extrapolation_baselines.py`` (pair van't
Hoff, pair linear-T, RF(Morgan+T), pair mean/last) with the two GNN runs
(structured analytic physics curve vs unstructured DirectGNN), all evaluated on
the held-out high-temperature rows of the same pairs.

T4 is supported if the structured physics curve extrapolates better than
DirectGNN (lower high-T MAE, closer to the pair van't Hoff oracle) and recovers
the correct sign of d ln x2 / d(1/T).

    python scripts/analysis/run_e3_temperature_comparison.py \
        --baselines-metrics results/temperature_extrapolation_baselines/metrics_by_model.csv \
        --physics-summary  results/e3/physics/predictions.summary.json \
        --directgnn-summary results/e3/directgnn/predictions.summary.json \
        --vant-hoff-json    results/e3/physics/vant_hoff_slopes.json \
        --out-json          results/e3/leaderboard.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def _load_summary(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--baselines-metrics", required=True,
                        help="metrics_by_model.csv from the temperature-baselines bundle.")
    parser.add_argument("--physics-summary", default=None,
                        help="export summary JSON for the physics analytic-curve run.")
    parser.add_argument("--directgnn-summary", default=None,
                        help="export summary JSON for the DirectGNN run.")
    parser.add_argument("--vant-hoff-metrics", default=None,
                        help="optional check_vant_hoff_slopes metrics CSV for the physics run.")
    parser.add_argument("--out-json", required=True)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []

    # Classical baselines (high-T test split).
    bm = pd.read_csv(args.baselines_metrics)
    if "eval_split" in bm.columns:
        bm = bm[bm["eval_split"].astype(str) == "test"]
    for r in bm.itertuples(index=False):
        d = r._asdict()
        rows.append({
            "model": str(d.get("model")),
            "family": "classical_baseline",
            "mae": float(d["mae"]) if d.get("mae") is not None else None,
            "r2": float(d["r2"]) if d.get("r2") is not None else None,
        })

    for label, summ in (
        ("physics_analytic_curve", _load_summary(args.physics_summary)),
        ("direct_gnn", _load_summary(args.directgnn_summary)),
    ):
        if summ is not None:
            rows.append({
                "model": label,
                "family": "gnn",
                "mae": summ.get("mae"),
                "r2": summ.get("r2"),
            })

    leaderboard = sorted(
        [r for r in rows if r["mae"] is not None], key=lambda r: r["mae"]
    )

    vh_sign_acc: float | None = None
    if args.vant_hoff_metrics and Path(args.vant_hoff_metrics).exists():
        vh_df = pd.read_csv(args.vant_hoff_metrics)
        sign_cols = [c for c in vh_df.columns if "sign_accuracy" in c]
        if sign_cols:
            vals = pd.to_numeric(vh_df[sign_cols[0]], errors="coerce").dropna()
            if len(vals):
                vh_sign_acc = float(vals.mean())

    physics = next((r for r in rows if r["model"] == "physics_analytic_curve"), None)
    direct = next((r for r in rows if r["model"] == "direct_gnn"), None)
    pair_vh = next((r for r in rows if "vant_hoff" in r["model"].lower()), None)
    headline = {
        "physics_minus_directgnn_mae": (
            (physics["mae"] - direct["mae"])
            if physics and direct and physics["mae"] is not None and direct["mae"] is not None
            else None
        ),
        "physics_minus_pair_vanthoff_mae": (
            (physics["mae"] - pair_vh["mae"])
            if physics and pair_vh and physics["mae"] is not None and pair_vh["mae"] is not None
            else None
        ),
        "physics_vant_hoff_slope_sign_accuracy": vh_sign_acc,
    }

    out = {
        "headline": headline,
        "leaderboard": leaderboard,
        "interpretation": (
            "T4 supported if physics_minus_directgnn_mae < 0 (structured curve "
            "beats the unstructured T-encoder) and physics sits close to the pair "
            "van't Hoff oracle (small positive physics_minus_pair_vanthoff_mae)."
        ),
    }
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
