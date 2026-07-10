#!/usr/bin/env python3
"""Backfill the true COSMO cavity volume (VT-2005 ``Vcosmo, A3``) into an existing
``sigma_profiles.csv`` artifact as a trailing ``v_cosmo`` column.

Why: the Staverman-Guggenheim combinatorial size factor r_i = V_i/r0 must use the
COSMO cavity volume (same cavity as the sigma-profile area A_i), NOT an RDKit
gas-phase molar volume. The sigma-profile artifact was ingested before the
``v_cosmo`` column existed; this backfills it deterministically so the ``full``
COSMO-SAC convention in ``run_b_insuff_decomposition.py`` uses a consistent
geometric basis. (New ingests emit ``v_cosmo`` directly via
``ingest_vt2005_sigma_profiles.py --volume-index``.)

The join is POSITIONAL: the ingest wrote one artifact row per ``index-csv`` row
in order with zero failures, so artifact row i corresponds to index row i. We
assert row-count and per-row SMILES agreement before writing.
"""
from __future__ import annotations

import argparse
import re

import pandas as pd


def _vt_index(fname: str) -> int | None:
    # "VT2005-0001-PROF.txt" -> 1 (skip the "2005" catalogue prefix)
    nums = re.findall(r"\d+", str(fname))
    return next((int(t) for t in nums if t != "2005"), None)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--artifact", default="results/sigma_profile_artifact/sigma_profiles.csv")
    ap.add_argument("--index-csv", default="notebooks/data/raw/vt2005/index_smiles.csv",
                    help="Same file/order used by ingest_vt2005_sigma_profiles.py (columns: file, smiles).")
    ap.add_argument("--volume-index", default="notebooks/data/raw/vt2005/index_v2.txt",
                    help="VT-2005 master index (tab-separated) carrying the 'Vcosmo, A3' column.")
    args = ap.parse_args()

    sig = pd.read_csv(args.artifact)
    idx = pd.read_csv(args.index_csv)
    if len(sig) != len(idx):
        raise SystemExit(
            f"row-count mismatch: artifact {len(sig)} vs index {len(idx)} — positional "
            "join invalid (ingest had failures?). Re-ingest with --volume-index instead.")
    # confirm positional alignment on the shared SMILES column
    if not (sig["smiles"].astype(str).values == idx["smiles"].astype(str).values).all():
        n_bad = int((sig["smiles"].astype(str).values != idx["smiles"].astype(str).values).sum())
        raise SystemExit(f"SMILES misalignment on {n_bad} rows — positional join invalid.")

    v2 = pd.read_csv(args.volume_index, sep="\t")
    vcol = next(c for c in v2.columns if "Vcosmo" in c)
    icol = next(c for c in v2.columns if "Index" in c)
    idx2vol = {int(r[icol]): float(r[vcol]) for _, r in v2.iterrows()}

    vols, n_missing = [], 0
    for f in idx["file"]:
        i = _vt_index(f)
        v = idx2vol.get(i)
        if v is None:
            n_missing += 1
            vols.append(float("nan"))
        else:
            vols.append(v)

    sig["v_cosmo"] = vols  # trailing column; name-based readers are unaffected
    sig.to_csv(args.artifact, index=False)
    print(f"backfilled v_cosmo into {args.artifact}: {len(sig)} rows, {n_missing} missing "
          f"(Vcosmo range {min(v for v in vols if v==v):.2f}..{max(v for v in vols if v==v):.2f} A^3)")


if __name__ == "__main__":
    main()
