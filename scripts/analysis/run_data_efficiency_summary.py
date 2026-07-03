#!/usr/bin/env python3
"""Aggregate a data-efficiency sweep: accuracy/ranking vs training-data fraction.

The scientific claim is that physics grounding (external single-component crystal
and sigma-profile supervision) buys SAMPLE EFFICIENCY: the physics model should
beat the black-box DirectGNN in the LOW-DATA regime, where the black box is
data-hungry. This aggregates per-(model, fraction) metrics into a curve and the
physics-minus-direct delta at each fraction.

Each entry is ``model:fraction:summary_json:ranking_json`` where summary_json is
an export_checkpoint_predictions summary (has "mae", "r2") and ranking_json is a
run_ranking_eval output (has spearman, best-solvent top-1).

    python scripts/analysis/run_data_efficiency_summary.py \
        --entry physics:0.1:results/de/physics/frac_0.1/pred.summary.json:results/de/physics/frac_0.1/rank.json \
        --entry direct:0.1:results/de/direct/frac_0.1/pred.summary.json:results/de/direct/frac_0.1/rank.json \
        --out-json results/de/summary.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--entry", action="append", required=True,
                   metavar="MODEL:FRAC:SUMMARY_JSON:RANKING_JSON")
    p.add_argument("--out-json", required=True)
    return p.parse_args()


def _load(path: str) -> dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {}


def main() -> None:
    args = parse_args()
    # curve[model][frac] = {mae, r2, spearman, top1}
    curve: dict[str, dict[float, dict[str, Any]]] = {}
    for spec in args.entry:
        parts = spec.split(":")
        if len(parts) < 3:
            raise ValueError(f"--entry expects MODEL:FRAC:SUMMARY[:RANKING], got {spec!r}")
        model, frac_s, summ = parts[0], parts[1], parts[2]
        rank = parts[3] if len(parts) > 3 else ""
        frac = float(frac_s)
        s = _load(summ)
        r = _load(rank) if rank else {}
        curve.setdefault(model, {})[frac] = {
            "mae": s.get("mae"), "r2": s.get("r2"),
            "spearman": (r.get("spearman") or {}).get("mean"),
            "best_solvent_top1": (r.get("best_solvent_top1_accuracy") or {}).get("mean"),
        }

    fracs = sorted({f for m in curve.values() for f in m})
    deltas = []
    if "physics" in curve and "direct" in curve:
        for f in fracs:
            p = curve["physics"].get(f, {})
            d = curve["direct"].get(f, {})
            row: dict[str, Any] = {"fraction": f}
            if p.get("mae") is not None and d.get("mae") is not None:
                row["mae_physics_minus_direct"] = float(p["mae"] - d["mae"])  # <0 = physics better
            if p.get("spearman") is not None and d.get("spearman") is not None:
                row["spearman_physics_minus_direct"] = float(p["spearman"] - d["spearman"])  # >0 = physics better
            deltas.append(row)

    out = {
        "curve": {m: {str(f): v for f, v in sorted(fr.items())} for m, fr in curve.items()},
        "fractions": fracs,
        "physics_minus_direct": deltas,
        "interpretation": (
            "Physics grounding wins on sample efficiency if mae_physics_minus_direct < 0 "
            "(and/or spearman delta > 0) at SMALL fractions, even if it ties/loses at "
            "fraction 1.0. That low-data advantage is the headline data-efficiency claim."
        ),
    }
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"fractions": fracs, "physics_minus_direct": deltas}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
