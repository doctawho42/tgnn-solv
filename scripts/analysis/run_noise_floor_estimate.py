#!/usr/bin/env python3
"""Estimate the irreducible label-noise floor of solubility (ln x2).

The processed splits collapse the per-reference attribution into a single
``source`` value, so the noise floor MUST be estimated on the RAW BigSolDB file,
which keeps the per-measurement ``Source`` (mostly a DOI/reference). We find
rows that report the SAME (solute, solvent, T within tolerance) from >=2 distinct
sources and measure their disagreement in ln x2 -- a lower bound on the
irreducible noise that no model can beat.

Two variants are reported:
  * raw   : disagreement across all rows in a multi-source group;
  * dedup : after collapsing exact-duplicate ln x2 values (likely the same
            measurement re-tabulated across compilations), which would otherwise
            deflate the floor toward zero.

If the floor is well below the model error (scaffold MAE ~1.65), accuracy is
winnable and the bottleneck is the model/representation, not the labels.

    python scripts/analysis/run_noise_floor_estimate.py \
        --raw-csv notebooks/data/raw/BigSolDBv2.1.csv \
        --out-dir results/noise_floor
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tgnn_solv.data.source_uncertainty import looks_like_doi
from tgnn_solv.diagnostics.compensation import canonical_smiles


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--raw-csv", default="notebooks/data/raw/BigSolDBv2.1.csv")
    p.add_argument("--out-dir", default="results/noise_floor")
    p.add_argument("--t-tol", type=float, default=1.0, help="Temperature rounding [K].")
    p.add_argument("--dedup-decimals", type=int, default=4,
                   help="Round ln x2 to this many decimals to detect re-tabulated duplicates.")
    p.add_argument("--n-bootstrap", type=int, default=2000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--solute-col", default="SMILES_Solute")
    p.add_argument("--solvent-col", default="SMILES_Solvent")
    p.add_argument("--temp-col", default="Temperature_K")
    p.add_argument("--molefrac-col", default="Solubility(mole_fraction)")
    p.add_argument("--source-col", default="Source")
    return p.parse_args()


def _json_safe(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): _json_safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_json_safe(x) for x in v]
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def _canon_cached(series: pd.Series) -> pd.Series:
    cache: dict[str, str] = {}
    def c(s: object) -> str:
        key = str(s)
        if key not in cache:
            cache[key] = canonical_smiles(s)
        return cache[key]
    return series.map(c)


def _group_disagreement(values: np.ndarray) -> dict[str, float]:
    """Within-group spread statistics for one (solute, solvent, T) group."""
    mean_abs_dev = float(np.mean(np.abs(values - values.mean())))
    return {
        "mean_abs_dev": mean_abs_dev,
        "range": float(values.max() - values.min()),
        "std": float(values.std(ddof=0)),
    }


def _aggregate(per_group: pd.DataFrame, metric: str) -> dict[str, Any]:
    vals = per_group[metric].to_numpy(dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return {"n_groups": 0}
    return {
        "n_groups": int(vals.size),
        "mean": float(vals.mean()),
        "median": float(np.median(vals)),
        "p90": float(np.percentile(vals, 90)),
        "p99": float(np.percentile(vals, 99)),
        "max": float(vals.max()),
    }


def _bootstrap_median_ci(vals: np.ndarray, n: int, seed: int) -> tuple[float | None, float | None]:
    vals = vals[np.isfinite(vals)]
    if vals.size < 2:
        return (None, None)
    rng = np.random.default_rng(seed)
    meds = [float(np.median(vals[rng.integers(0, vals.size, vals.size)])) for _ in range(n)]
    return (float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5)))


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.raw_csv, low_memory=False)
    df = df.rename(columns={
        args.solute_col: "solute_smiles",
        args.solvent_col: "solvent_smiles",
        args.temp_col: "T",
        args.molefrac_col: "x2",
        args.source_col: "source",
    })
    df["x2"] = pd.to_numeric(df["x2"], errors="coerce")
    df["T"] = pd.to_numeric(df["T"], errors="coerce")
    df = df.dropna(subset=["solute_smiles", "solvent_smiles", "T", "x2", "source"])
    df = df[df["x2"] > 0.0]
    df["lnx2"] = np.log(df["x2"].to_numpy(dtype=float))
    df["csolute"] = _canon_cached(df["solute_smiles"])
    df["csolvent"] = _canon_cached(df["solvent_smiles"])
    df["Tr"] = (df["T"] / args.t_tol).round() * args.t_tol

    keys = ["csolute", "csolvent", "Tr"]
    g = df.groupby(keys)
    n_src = g["source"].nunique()
    multi_keys = n_src[n_src >= 2].index
    multi = df.set_index(keys).loc[multi_keys].reset_index()

    rows: list[dict[str, Any]] = []
    for key, grp in multi.groupby(keys):
        vals = grp["lnx2"].to_numpy(dtype=float)
        n_sources = int(grp["source"].nunique())
        # dedup: collapse exact-duplicate (re-tabulated) ln x2 values.
        dedup_vals = np.unique(np.round(vals, args.dedup_decimals))
        all_doi = bool(grp["source"].map(looks_like_doi).all())
        rec = {
            "csolute": key[0], "csolvent": key[1], "T": float(key[2]),
            "n_rows": int(len(grp)), "n_sources": n_sources,
            "n_distinct_values": int(dedup_vals.size),
            "all_sources_doi": all_doi,
            **{f"raw_{k}": v for k, v in _group_disagreement(vals).items()},
        }
        if dedup_vals.size >= 2:
            for k, v in _group_disagreement(dedup_vals).items():
                rec[f"dedup_{k}"] = v
        else:
            rec["dedup_mean_abs_dev"] = np.nan
            rec["dedup_range"] = np.nan
            rec["dedup_std"] = np.nan
        rows.append(rec)

    pg = pd.DataFrame(rows)
    pg.to_csv(out_dir / "per_group_disagreement.csv", index=False)

    n_collapsed = int((pg["n_distinct_values"] < 2).sum())
    raw_ci = _bootstrap_median_ci(pg["raw_mean_abs_dev"].to_numpy(float), args.n_bootstrap, args.seed)
    dedup_ci = _bootstrap_median_ci(
        pg["dedup_mean_abs_dev"].dropna().to_numpy(float), args.n_bootstrap, args.seed
    )

    summary = {
        "raw_csv": args.raw_csv,
        "t_tol_K": args.t_tol,
        "n_total_rows": int(len(df)),
        "n_distinct_sources": int(df["source"].nunique()),
        "n_groups_total": int(g.ngroups),
        "n_multi_source_groups": int(len(pg)),
        "n_groups_all_duplicates_collapsed": n_collapsed,
        "raw": {
            **_aggregate(pg, "raw_mean_abs_dev"),
            "median_ci95": raw_ci,
            "range_p90": _aggregate(pg, "raw_range").get("p90"),
        },
        "dedup": {
            **_aggregate(pg.dropna(subset=["dedup_mean_abs_dev"]), "dedup_mean_abs_dev"),
            "median_ci95": dedup_ci,
        },
        "by_n_sources": {
            str(k): _aggregate(sub, "raw_mean_abs_dev")
            for k, sub in pg.assign(
                bucket=pd.cut(pg["n_sources"], [1, 2, 3, 5, np.inf],
                             labels=["2", "3", "4-5", "6+"])
            ).groupby("bucket", observed=True)
        },
        "doi_only_vs_mixed": {
            "doi_only": _aggregate(pg[pg["all_sources_doi"]], "raw_mean_abs_dev"),
            "has_non_doi": _aggregate(pg[~pg["all_sources_doi"]], "raw_mean_abs_dev"),
        },
        "interpretation": (
            "Compare the dedup median/mean to the scaffold model MAE (~1.65). If the "
            "floor is far below it, label noise does NOT explain model error and "
            "accuracy is winnable; the bottleneck is model/representation/activity."
        ),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True), encoding="utf-8"
    )

    print(f"multi-source groups: {summary['n_multi_source_groups']} "
          f"(of {summary['n_groups_total']}; {n_collapsed} all-duplicate)")
    print(f"RAW   ln x2 disagreement: median={summary['raw'].get('median')} "
          f"mean={summary['raw'].get('mean')} p90={summary['raw'].get('p90')} "
          f"CI95(median)={raw_ci}")
    print(f"DEDUP ln x2 disagreement: median={summary['dedup'].get('median')} "
          f"mean={summary['dedup'].get('mean')} p90={summary['dedup'].get('p90')} "
          f"CI95(median)={dedup_ci}")
    print(f"Wrote {out_dir/'summary.json'}")


if __name__ == "__main__":
    main()
