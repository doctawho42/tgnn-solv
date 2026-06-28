#!/usr/bin/env python3
"""Build a standalone external sigma-profile auxiliary stream.

Grounds the COSMO-SAC activity branch on a pool of single-component sigma-profile
labels (e.g. VT-2005), exactly mirroring the crystal aux stream. The output is a
separate CSV in processed-dataset format, consumed via

    python scripts/train.py ... \
        --sigma-train-data <output.csv> --sigma-steps-per-epoch 8

Each row is a single-component sigma-profile label row: the solute is paired with
itself as the "solvent" (valid graph, no pair signal), ``has_solubility=False``,
all other masks off, ``has_sigma_profile=True``, plus the normalized 51-bin
profile (``sigma_p_0..sigma_p_50``, sums to 1) and cavity area ``sigma_area``.

Input artifact columns: ``smiles`` (or ``solute_smiles``), ``sigma_area``, and
either 51 ``sigma_p_*`` columns (already a shape or area-weighted profile) — they
are renormalized to a shape here.

CRITICAL GUARD: exclude pool solutes whose Bemis-Murcko scaffold appears in a
held-out split (``--exclude-scaffolds-from``) to keep scaffold evaluation honest.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.utils import get_scaffold


def grid_metadata(n_bins: int) -> dict:
    """Self-describing sigma grid for the artifact summary."""
    cfg = TGNNSolvConfig()
    return {
        "n_bins": int(n_bins),
        "sigma_min": float(cfg.cosmo_sac_sigma_min),
        "sigma_max": float(cfg.cosmo_sac_sigma_max),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--sigma-csv", default="results/sigma_profile_artifact/sigma_profiles.csv")
    p.add_argument("--template-csv", default="notebooks/data/processed/train.csv")
    p.add_argument("--output-csv", default="notebooks/data/processed_sigma_aux_stream/sigma_train.csv")
    p.add_argument("--summary-json", default="notebooks/data/processed_sigma_aux_stream/summary.json")
    p.add_argument("--n-bins", type=int, default=TGNNSolvConfig().cosmo_sac_n_bins)
    p.add_argument("--temperature", type=float, default=298.15)
    p.add_argument("--source-label", default="aux_only_sigma_profile_stream")
    p.add_argument(
        "--exclude-scaffolds-from",
        nargs="*",
        default=["notebooks/data/processed/test.csv", "notebooks/data/processed/val.csv"],
    )
    p.add_argument(
        "--allow-no-scaffold-exclusion",
        action="store_true",
        help="Override the fail-closed scaffold-leak guard. Only for pools that are "
        "intentionally NOT used in a scaffold-split evaluation.",
    )
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


def _excluded_scaffolds(paths: list[str], *, allow_missing: bool = False) -> set[str]:
    """Collect Murcko scaffolds to exclude. Fails CLOSED by default.

    A missing or empty/header-only split CSV would silently yield zero exclusions
    and emit the entire (non-split-aware) sigma-profile pool, leaking held-out
    scaffolds into the scaffold-extrapolation evaluation. So unless ``allow_missing``
    is set, a requested path that does not exist or yields zero scaffolds raises.
    """
    scaffolds: set[str] = set()
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            if allow_missing:
                continue
            raise FileNotFoundError(
                f"--exclude-scaffolds-from path does not exist: {path}. Refusing to "
                "build the aux stream without the mandatory scaffold-leak guard "
                "(pass --allow-no-scaffold-exclusion to override deliberately)."
            )
        df = pd.read_csv(path, usecols=lambda c: c == "solute_smiles", low_memory=False)
        path_scaffolds = {
            scaf
            for smi in df["solute_smiles"].dropna().astype(str).unique()
            if (scaf := get_scaffold(smi))
        }
        if not path_scaffolds and not allow_missing:
            raise ValueError(
                f"{path} yielded zero usable solute scaffolds; refusing to proceed "
                "(an empty/header-only split would silently leak the full pool into "
                "the evaluation). Pass --allow-no-scaffold-exclusion to override."
            )
        scaffolds |= path_scaffolds
    return scaffolds


def _empty_row_template(columns: list[str], temperature: float) -> dict[str, Any]:
    row = {col: "" for col in columns}
    numeric = {"temperature": temperature, "ln_x2": 0.0, "T_m": 0.0, "dH_fus": 0.0,
               "hansen_d": 0.0, "hansen_p": 0.0, "hansen_h": 0.0, "ln_gamma_inf": 0.0}
    booly = {"has_solubility": False, "has_T_m": False, "has_dH_fus": False,
             "has_hansen": False, "has_gamma_inf": False, "fda_approved": "No"}
    for k, v in numeric.items():
        if k in row:
            row[k] = v
    for k, v in booly.items():
        if k in row:
            row[k] = v
    return row


def main() -> None:
    args = parse_args()
    sigma = pd.read_csv(args.sigma_csv, low_memory=False)
    smiles_col = "smiles" if "smiles" in sigma.columns else "solute_smiles"
    bin_cols = [f"sigma_p_{i}" for i in range(args.n_bins)]
    missing = [c for c in bin_cols if c not in sigma.columns]
    if missing:
        raise ValueError(f"{args.sigma_csv} missing profile columns: {missing[:3]}... "
                         f"(expected sigma_p_0..sigma_p_{args.n_bins-1})")
    sigma = sigma.dropna(subset=[smiles_col]).copy()
    n_raw = len(sigma)

    requested_excludes = list(args.exclude_scaffolds_from or [])
    excluded = _excluded_scaffolds(
        requested_excludes, allow_missing=args.allow_no_scaffold_exclusion
    )
    if requested_excludes and not excluded and not args.allow_no_scaffold_exclusion:
        raise SystemExit(
            "Scaffold exclusion produced an empty set; aborting to prevent leakage "
            "of held-out scaffolds into the sigma-profile aux pool."
        )
    if excluded:
        sigma = sigma[~sigma[smiles_col].astype(str).map(lambda s: get_scaffold(s) in excluded)]
    n_after = len(sigma)

    template = pd.read_csv(args.template_csv, nrows=1, low_memory=False)
    out_cols = list(template.columns) + ["has_sigma_profile", "sigma_area"] + bin_cols
    tmpl = _empty_row_template(out_cols, args.temperature)

    rows: list[dict[str, Any]] = []
    for rec in sigma.itertuples(index=False):
        d = rec._asdict()
        smi = str(d[smiles_col])
        prof = np.array([float(d[c]) for c in bin_cols], dtype=float)
        prof = np.clip(prof, 0.0, None)
        total = prof.sum()
        if total <= 0:
            continue
        shape = prof / total  # normalize to a sum-1 shape
        area = float(d.get("sigma_area", total))
        row = dict(tmpl)
        row["solute_smiles"] = smi
        row["solvent_smiles"] = smi
        row["temperature"] = float(args.temperature)
        row["has_solubility"] = False
        row["has_sigma_profile"] = True
        row["sigma_area"] = area
        for i, c in enumerate(bin_cols):
            row[c] = float(shape[i])
        if "source" in row:
            row["source"] = args.source_label
        rows.append(row)

    out = pd.DataFrame(rows, columns=out_cols)
    Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary_json).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output_csv, index=False)

    summary = {
        "sigma_csv": args.sigma_csv, "template_csv": args.template_csv,
        "output_csv": args.output_csv, "n_pool_raw": int(n_raw),
        "n_after_scaffold_exclusion": int(n_after), "n_excluded_scaffolds": int(len(excluded)),
        "n_rows": int(len(out)), "n_bins": int(args.n_bins),
        "exclude_scaffolds_from": list(args.exclude_scaffolds_from or []),
        "grid": grid_metadata(args.n_bins),
    }
    Path(args.summary_json).write_text(json.dumps(_json_safe(summary), indent=2, sort_keys=True))
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
