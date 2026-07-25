#!/usr/bin/env python
"""Black-box Study 4: if the pair representation is not organised by physics, by what?

Studies 1a and 2 came back KILL, both limited by the crystal oracle's 13 held-out solutes.
Study 4 escapes that bottleneck: 4a/4b need no oracle, so they run on the whole test split
(thousands of rows, hundreds of solutes and scaffolds). Only 4c consults the oracle.

Method. For each candidate organising factor we report the share of h_BB's total variance it
accounts for, always against a matched permutation null:

  categorical factor (solvent, scaffold, solute) -> eta^2 = between-group / total variance.
      Many categories inflate eta^2 mechanically, so the null permutes the labels across rows
      while PRESERVING group sizes; the reported figure is the excess over that null.
  continuous factor (temperature, logP, ...)     -> variance explained by ridge on that factor
      alone, with the same permutation discipline.

Reading eta^2 absolutely would be meaningless -- 200 solvent categories explain a lot of
variance by counting alone. Everything here is read as excess over its own null.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/experiments/blackbox_study4.py \
        --checkpoints checkpoints/e5_current_split/directgnn_seed4{2,3,4}.pt
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))
sys.path.insert(0, str(_REPO / "scripts" / "experiments"))

from blackbox_study1a import build_oracle, extract_hbb  # noqa: E402


def eta2(H: np.ndarray, labels: np.ndarray) -> float:
    """Between-group share of total multivariate variance."""
    total = float(((H - H.mean(0)) ** 2).sum())
    if total <= 0:
        return float("nan")
    between = 0.0
    for lab in np.unique(labels):
        m = labels == lab
        d = H[m].mean(0) - H.mean(0)
        between += m.sum() * float((d ** 2).sum())
    return between / total


def _block_permute(values: np.ndarray, blocks: np.ndarray | None, rng) -> np.ndarray:
    """Permute a factor while respecting the level at which it varies.

    Scaffold, logP, TPSA, MolWt and Phi* are constant WITHIN a solute. Permuting them across
    rows destroys that block structure, which makes the null far too easy and turns any
    solute-level signal into 'p = 0.000'. When `blocks` is given the value is permuted among
    blocks and then broadcast back, so the null preserves how the factor actually varies.
    """
    if blocks is None:
        return rng.permutation(values)
    uniq = np.unique(blocks)
    per_block = {b: values[blocks == b][0] for b in uniq}
    shuffled = rng.permutation(uniq)
    mapping = dict(zip(uniq, shuffled))
    return np.array([per_block[mapping[b]] for b in blocks])


def eta2_with_null(H: np.ndarray, labels: np.ndarray, n_perm: int = 200,
                   blocks: np.ndarray | None = None) -> tuple:
    obs = eta2(H, labels)
    null = np.array([eta2(H, _block_permute(labels, blocks, np.random.default_rng(i)))
                     for i in range(n_perm)])
    return obs, float(null.mean()), obs - float(null.mean()), float((null >= obs).mean())


def var_explained_continuous(H: np.ndarray, x: np.ndarray, n_perm: int = 200,
                             blocks: np.ndarray | None = None) -> tuple:
    """Share of h_BB variance linearly explained by a single continuous factor."""
    Hc = H - H.mean(0)
    tot = float((Hc ** 2).sum())

    def ve(xv):
        xc = xv - xv.mean()
        denom = float((xc ** 2).sum())
        if denom <= 0 or tot <= 0:
            return float("nan")
        beta = (xc[:, None] * Hc).sum(0) / denom
        return float(((xc[:, None] * beta[None, :]) ** 2).sum()) / tot

    obs = ve(x)
    null = np.array([ve(_block_permute(x, blocks, np.random.default_rng(i)))
                     for i in range(n_perm)])
    return obs, float(null.mean()), obs - float(null.mean()), float((null >= obs).mean())


def murcko(smiles: list[str]) -> np.ndarray:
    from rdkit import Chem
    from rdkit.Chem.Scaffolds import MurckoScaffold
    out = []
    for s in smiles:
        try:
            m = Chem.MolFromSmiles(s)
            out.append(MurckoScaffold.MurckoScaffoldSmiles(mol=m) if m else "?")
        except Exception:
            out.append("?")
    return np.asarray(out)


def descriptors(smiles: list[str]) -> pd.DataFrame:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    rows = []
    for s in smiles:
        m = Chem.MolFromSmiles(s)
        if m is None:
            rows.append((np.nan,) * 3)
            continue
        rows.append((Descriptors.MolLogP(m), Descriptors.TPSA(m), Descriptors.MolWt(m)))
    return pd.DataFrame(rows, columns=["logP", "TPSA", "MolWt"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoints", nargs="+", required=True)
    ap.add_argument("--data-dir", default="notebooks/data/processed")
    ap.add_argument("--oracle", default="results/open_crystal_artifact/open_crystal_solute.csv")
    ap.add_argument("--n-perm", type=int, default=200)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    dd = _REPO / args.data_dir
    device = torch.device(args.device)

    rows = pd.read_csv(dd / "test.csv", low_memory=False)
    if "has_solubility" in rows.columns:
        rows = rows[rows["has_solubility"].astype(bool)].reset_index(drop=True)
    print(f"test rows {len(rows)} | solutes {rows.solute_smiles.nunique()} "
          f"| solvents {rows.solvent_smiles.nunique()}")

    scaf = murcko(list(rows.solute_smiles))
    desc = descriptors(list(rows.solute_smiles))
    print(f"unique Murcko scaffolds: {len(np.unique(scaf))}")

    # oracle overlay for 4c (only where measured)
    orc_rows = build_oracle(dd / "test.csv", args.oracle if Path(args.oracle).is_absolute()
                            else _REPO / args.oracle)
    key = rows.solute_smiles.astype(str) + "|" + rows.solvent_smiles.astype(str) + "|" + \
        rows.temperature.round(4).astype(str)
    okey = orc_rows.solute_smiles.astype(str) + "|" + orc_rows.solvent_smiles.astype(str) + \
        "|" + orc_rows.temperature.round(4).astype(str)
    phi = pd.Series(orc_rows.phi_star.to_numpy(), index=okey).reindex(key).to_numpy()
    print(f"rows with a measured Phi*: {int(np.isfinite(phi).sum())} "
          f"({rows.solute_smiles[np.isfinite(phi)].nunique()} solutes)")

    results = {"n_rows": int(len(rows)), "n_solutes": int(rows.solute_smiles.nunique()),
               "n_solvents": int(rows.solvent_smiles.nunique()),
               "n_scaffolds": int(len(np.unique(scaf))), "seeds": {}}

    for ck in args.checkpoints:
        ck = Path(ck)
        print(f"\n=== {ck.name} ===")
        H = extract_hbb(ck, rows, device).astype(np.float64)
        H = H - H.mean(0)
        print(f"h_BB {H.shape}")

        sol_blocks = rows.solute_smiles.to_numpy()   # factors constant within a solute
        slv_blocks = rows.solvent_smiles.to_numpy()

        # Choosing the null level is not cosmetic. eta^2 is invariant to RELABELLING groups, so
        # permuting an identity factor at its own level is a no-op: the null equals the
        # observation and the excess is identically zero. Identity factors therefore take the
        # ROW-level null ("is this partition better than a random one of the same shape?"),
        # while factors DERIVED from identity (scaffold, descriptors, Phi*) take the
        # solute-level null ("is this particular labelling better than an arbitrary
        # solute-level one?"). Scaffold gets both, because both questions are interesting.
        out = {}
        print("  factor                       eta2/VE    null    excess    p   null level")
        cats = [("solvent identity", slv_blocks, None, "row"),
                ("solute identity", sol_blocks, None, "row"),
                ("solute scaffold", scaf, None, "row"),
                ("solute scaffold | solute-level null", scaf, sol_blocks, "solute")]
        for name, lab, blk, lvl in cats:
            o, nl, ex, p = eta2_with_null(H, lab, args.n_perm, blocks=blk)
            out[name] = {"stat": o, "null": nl, "excess": ex, "p": p, "kind": "eta2",
                         "n_levels": int(len(np.unique(lab))), "null_level": lvl}
            print(f"  {name:26s} {o:7.3f} {nl:7.3f} {ex:+8.3f} {p:7.3f}   {lvl}"
                  f" ({len(np.unique(lab))} levels)")

        conts = [("temperature", rows.temperature.to_numpy(float), None, "row"),
                 ("logP(solute)", desc.logP.to_numpy(float), sol_blocks, "solute"),
                 ("TPSA(solute)", desc.TPSA.to_numpy(float), sol_blocks, "solute"),
                 ("MolWt(solute)", desc.MolWt.to_numpy(float), sol_blocks, "solute")]
        for name, x, blk, lvl in conts:
            if not np.isfinite(x).all():
                x = np.nan_to_num(x, nan=float(np.nanmean(x)))
            o, nl, ex, p = var_explained_continuous(H, x, args.n_perm, blocks=blk)
            out[name] = {"stat": o, "null": nl, "excess": ex, "p": p, "kind": "VE",
                         "null_level": lvl}
            print(f"  {name:26s} {o:7.3f} {nl:7.3f} {ex:+8.3f} {p:7.3f}   {lvl}")

        # --- solute-level factors cannot exceed the solute-identity ceiling -------------
        # scaffold, logP, TPSA, MolWt and Phi* are all constant within a solute, so each is
        # bounded above by the variance solute identity itself explains. Reading them against
        # the total is misleading; reading them as a share of that ceiling is the real question
        # ("of the molecular structure the box has, how much is X?").
        ceil_solute = out["solute identity"]["excess"]
        print(f"\n  share of the solute-identity ceiling ({ceil_solute:+.3f}):")
        for name in ("solute scaffold", "logP(solute)", "TPSA(solute)", "MolWt(solute)"):
            sh = out[name]["excess"] / ceil_solute if ceil_solute > 0 else float("nan")
            out[name]["share_of_solute_ceiling"] = sh
            print(f"    {name:24s} {sh:6.1%}")

        # 4c: the physical fraction, on the subset carrying a measured Phi*, with its OWN
        # solute-identity ceiling computed on that same subset.
        m = np.isfinite(phi)
        if m.sum() > 30:
            o, nl, ex, p = var_explained_continuous(H[m], phi[m], args.n_perm,
                                                    blocks=rows.solute_smiles.to_numpy()[m])
            c_o, c_nl, c_ex, _ = eta2_with_null(H[m], rows.solute_smiles.to_numpy()[m],
                                                args.n_perm)
            sh = ex / c_ex if c_ex > 0 else float("nan")
            out["Phi* (measured, subset)"] = {
                "stat": o, "null": nl, "excess": ex, "p": p, "kind": "VE",
                "n_rows": int(m.sum()),
                "solute_ceiling_on_subset": c_ex, "share_of_subset_ceiling": sh}
            print(f"\n  4c on the Phi* subset ({int(m.sum())} rows, "
                  f"{rows.solute_smiles[m].nunique()} solutes):")
            print(f"    Phi* variance explained      {o:7.3f} (excess {ex:+.3f}, p {p:.3f})")
            print(f"    solute-identity ceiling here {c_o:7.3f} (excess {c_ex:+.3f})")
            print(f"    Phi* as share of that ceiling: {sh:.1%}")

        results["seeds"][ck.name] = out

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(results, indent=2))
        print(f"\nwrote {args.out_json}")


if __name__ == "__main__":
    main()
