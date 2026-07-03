#!/usr/bin/env python3
"""Ingest the VT-2005 (or Mullins) sigma-profile database into a flat artifact.

Produces ``results/sigma_profile_artifact/sigma_profiles.csv`` with columns
``smiles, sigma_area, sigma_p_0 .. sigma_p_<n-1>`` (resampled onto the COSMO-SAC
grid used by the model). That artifact feeds
``scripts/data/build_sigma_profile_aux_stream.py``.

The VT-2005 DB is NOT shipped with this repo (it requires QM-derived COSMO files).
Download it separately and point this script at:
  * ``--profiles-dir``: a directory of per-compound profile files, each containing
    numeric rows whose first two columns are (sigma, p(sigma));
  * ``--index-csv``: a CSV mapping each profile file to a SMILES, with columns
    ``file`` and ``smiles`` (CAS/name->SMILES resolution is left to the user).

The grid is taken from the model config (cosmo_sac_sigma_min/max/n_bins); DB
profiles on a different grid are linearly resampled and clipped to >=0.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from tgnn_solv.config import TGNNSolvConfig


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--profiles-dir", required=True, help="Directory of VT-2005 profile files.")
    p.add_argument("--index-csv", required=True, help="CSV with columns: file, smiles.")
    p.add_argument("--out-csv", default="results/sigma_profile_artifact/sigma_profiles.csv")
    p.add_argument("--summary-json", default="results/sigma_profile_artifact/summary.json")
    return p.parse_args()


def _read_profile_file(path: Path) -> tuple[np.ndarray, np.ndarray] | None:
    sig, prof = [], []
    for line in path.read_text(errors="ignore").splitlines():
        parts = line.replace(",", " ").split()
        if len(parts) < 2:
            continue
        try:
            s, p = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        sig.append(s)
        prof.append(p)
    if len(sig) < 2:
        return None
    return np.asarray(sig, dtype=float), np.asarray(prof, dtype=float)


def main() -> None:
    args = parse_args()
    cfg = TGNNSolvConfig()
    grid = np.linspace(cfg.cosmo_sac_sigma_min, cfg.cosmo_sac_sigma_max, cfg.cosmo_sac_n_bins)
    bin_cols = [f"sigma_p_{i}" for i in range(cfg.cosmo_sac_n_bins)]

    index = pd.read_csv(args.index_csv, low_memory=False)
    if not {"file", "smiles"} <= set(index.columns):
        raise ValueError("--index-csv must have columns 'file' and 'smiles'.")

    rows, n_fail = [], 0
    pdir = Path(args.profiles_dir)
    for rec in index.itertuples(index=False):
        fpath = pdir / str(rec.file)
        if not fpath.exists():
            n_fail += 1
            continue
        parsed = _read_profile_file(fpath)
        if parsed is None:
            n_fail += 1
            continue
        sig, prof = parsed
        prof = np.clip(np.interp(grid, sig, prof, left=0.0, right=0.0), 0.0, None)
        if prof.sum() <= 0:
            n_fail += 1
            continue
        row = {"smiles": str(rec.smiles), "sigma_area": float(prof.sum())}
        row.update({c: float(prof[i]) for i, c in enumerate(bin_cols)})
        rows.append(row)

    out = pd.DataFrame(rows, columns=["smiles", "sigma_area", *bin_cols])
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out_csv, index=False)
    summary = {
        "profiles_dir": args.profiles_dir, "index_csv": args.index_csv,
        "out_csv": args.out_csv, "n_ingested": int(len(out)),
        "n_failed": int(n_fail), "n_bins": int(cfg.cosmo_sac_n_bins),
    }
    Path(args.summary_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary_json).write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
