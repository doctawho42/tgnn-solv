#!/usr/bin/env python
"""The pre-declared out-of-sample margin for the glycol-ether stratum, on ThermoML rows.

This is the producer PRE_DECLARATION.md names.  It runs the estimator that file fixes, on the row
set build_glycol_oos_thermoml.py assembled, and reports which of the three declared outcomes
obtains.  It refuses to run if either declaration's sha256 has moved, because a pre-declaration
that can be edited after the number is seen is not one.

THE ESTIMATOR, as declared and amended
---------------------------------------
  rows        the 95 net-new rows: pairs the broad IDAC set does not carry, one source DOI
  m           the measured ln gamma^inf
  g           the deployed CosmoSacLayer on UD sigma-profiles (InChIKey, exact), at each row's
              own temperature, residual-only convention (V = None) -- amendment 1
  cell        eight equal-count bins of g, unbiased (ddof=1) within-bin variance, row unit
  margin      MSE - 2 * B_insuff^up
  interval    90% percentile bootstrap over PAIRS, the only clustering a single-source set supports

WHAT IT CANNOT BE.  One source DOI, so the map's leave-one-source-out clause cannot be applied and
this is a DESCRIPTIVE out-of-sample reading, not an admissible one.  Declared before the number
existed, and it is not renegotiated by the number.

Usage
-----
    python scripts/analysis/run_glycol_oos_margin.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402

HOME_UD = Path.home() / "COSMOSAC/profiles/UD"
SET = ROOT / "results/b_insuff/glycol_oos_thermoml"
#: The declarations, and the digests they were committed under.  Both are checked.
DECLARATIONS = {
    "PRE_DECLARATION.md": "8744f9e1b7311cfc82dcc247b4406b9e4c4c339187cd90342dd519750a580fba",
    "PRE_DECLARATION_AMENDMENT_1.md":
        "5e9ac5ee873ab741002aa4b22f65822ea0bd06eef6156c6d5250192ac4af5dc5",
}
N_BINS, DDOF = 8, 1


def check_declarations() -> None:
    for name, want in DECLARATIONS.items():
        got = hashlib.sha256((SET / name).read_bytes()).hexdigest()
        if got != want:
            raise SystemExit(
                f"{name} has changed since it was committed ({got[:16]} against {want[:16]}). "
                f"A pre-declaration that moves after the fact is not one; nothing is computed.")
    print("both declarations verified against their committed digests")


def ud_profiles() -> dict[str, tuple[np.ndarray, float]]:
    """{InChIKey: (51-bin profile, cavity area)} from the untyped sigma/ directory (2002 kernel)."""
    out: dict[str, tuple[np.ndarray, float]] = {}
    for path in (HOME_UD / "sigma").glob("*.sigma"):
        meta, vals = {}, []
        for line in path.read_text().splitlines():
            line = line.strip()
            if line.startswith("# meta:"):
                meta = json.loads(line[len("# meta:"):].strip())
            elif line and not line.startswith("#"):
                vals.append(float(line.split()[1]))
        p = np.asarray(vals, float)[:51]
        if len(p) == 51:
            out[path.stem] = (p, float(meta.get("area [A^2]", p.sum())))
    return out


def inchikey(smiles: str) -> str | None:
    from rdkit import Chem, RDLogger
    from rdkit.Chem import inchi
    RDLogger.DisableLog("rdApp.*")
    mol = Chem.MolFromSmiles(smiles)
    try:
        return inchi.MolToInchiKey(mol) if mol is not None else None
    except Exception:
        return None


def binsuff(g: np.ndarray, m: np.ndarray, n_bins: int = N_BINS, ddof: int = DDOF) -> float:
    q = np.quantile(g, np.linspace(0.0, 1.0, n_bins + 1))
    q[0] -= 1e-9
    q[-1] += 1e-9
    idx = np.digitize(g, q[1:-1])
    total = 0.0
    for b in range(n_bins):
        mm = m[idx == b]
        if len(mm) > ddof:
            total += (len(mm) / len(m)) * float(mm.var(ddof=ddof))
    return total


def margin(g: np.ndarray, m: np.ndarray) -> float:
    return float(np.mean((m - g) ** 2)) - 2.0 * binsuff(g, m)


def _closure(sol_keys, slv_keys, temps, table) -> np.ndarray:
    """g = CosmoSacLayer.ln_gamma_inf on UD profiles, residual-only, at each row's own T."""
    layer = CosmoSacLayer(cfg=None)
    layer.eval()
    p2 = torch.tensor(np.stack([table[k][0] for k in sol_keys]), dtype=torch.float)
    A2 = torch.tensor([table[k][1] for k in sol_keys], dtype=torch.float)
    p1 = torch.tensor(np.stack([table[k][0] for k in slv_keys]), dtype=torch.float)
    A1 = torch.tensor([table[k][1] for k in slv_keys], dtype=torch.float)
    T = torch.tensor(np.asarray(temps, dtype=float), dtype=torch.float)
    with torch.no_grad():
        return layer.ln_gamma_inf(p2, p1, A2, A1, None, None, T).numpy()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--draws", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=SET / "margin.json")
    ap.add_argument("--check-article", action="store_true",
                    help="bind Sec. 3.2.1's out-of-sample numerals to this run and fail on drift")
    ap.add_argument("--validate", action="store_true",
                    help="first reproduce the PUBLISHED in-sample margin with this script's own g "
                         "construction. A number from an unvalidated estimator is not a result.")
    a = ap.parse_args()

    check_declarations()
    table = ud_profiles()
    if a.validate:
        # THE ESTIMATOR IS VALIDATED BEFORE IT IS POINTED AT NEW DATA.  Same discipline as
        # run_e5_cluster_bootstrap.py: reproduce the published value, then move.
        ins = pd.read_csv(ROOT / "paper/si_tables/broad_idac_set_477.csv")
        ins = ins[ins.solvent_smiles.isin({"OCCO", "OCCOCCO", "OCCOCCOCCO", "OCCOCCOCCOCCO"})]
        gi = _closure(ins.solute_ud_key, ins.solvent_ud_key, ins.T_K, table)
        mi = ins.m_ln_gamma_inf.to_numpy(float)
        dep = ins.g_2002_res.to_numpy(float)
        print(f"validation on the {len(ins)}-row in-sample stratum:")
        print(f"  my g vs deposited g_2002_res   max|diff| {np.abs(gi - dep).max():.3e}")
        print(f"  margin, my g                   {margin(gi, mi):+.4f}")
        print(f"  margin, deposited g            {margin(dep, mi):+.4f}   (published +2.04)")
        if abs(margin(gi, mi) - 2.04) > 0.05:
            raise SystemExit("this script does not reproduce the published in-sample margin; "
                             "its out-of-sample number would mean nothing")
        print("  reproduces\n")

    d = pd.read_csv(SET / "net_new_rows.csv")
    print(f"\nrow set: {len(d)} rows, "
          f"{d.groupby(['solute_can', 'solvent_can']).ngroups} pairs, "
          f"{d.solute_can.nunique()} solutes, {d.solvent_can.nunique()} solvents, "
          f"{d.doi.nunique()} source DOI")

    d["sol_ik"] = [inchikey(s) for s in d.solute_can]
    d["slv_ik"] = [inchikey(s) for s in d.solvent_can]
    have = d.sol_ik.isin(table) & d.slv_ik.isin(table)
    if not have.all():
        raise SystemExit(f"{(~have).sum()} rows lack a UD profile; amendment 1 says all 95 have "
                         f"one, so the set or the deposit has moved")
    d = d[have].copy()

    g = _closure(d.sol_ik, d.slv_ik, d.temperature, table)
    m = d.ln_gamma_inf.to_numpy(float)

    mse = float(np.mean((m - g) ** 2))
    b_up = binsuff(g, m)
    point = mse - 2.0 * b_up

    rng = np.random.default_rng(a.seed)
    pairs = d.groupby(["solute_can", "solvent_can"]).indices
    keys = list(pairs)
    vals = []
    for _ in range(a.draws):
        drawn = rng.integers(0, len(keys), len(keys))
        idx = np.concatenate([pairs[keys[i]] for i in drawn])
        vals.append(margin(g[idx], m[idx]))
    lo, hi = float(np.percentile(vals, 5)), float(np.percentile(vals, 95))

    verdict = ("HOLDS" if point > 0 and lo > 0 else
               "FAILS" if point <= 0 else "UNRESOLVED")

    print(f"\n{'=' * 68}")
    print(f"  MSE              {mse:+.4f}")
    print(f"  B_insuff^up      {b_up:+.4f}   (8 equal-count bins, unbiased)")
    print(f"  margin           {point:+.4f}   90% [{lo:+.4f}, {hi:+.4f}]   ({len(keys)} pair clusters)")
    print("  in-sample margin +2.04         90% [+1.25, +2.87]   (182 rows, 43 pairs, 3 sources)")
    print(f"\n  DECLARED OUTCOME: {verdict}")
    print(f"{'=' * 68}")
    print("  Descriptive, not admissible: one source DOI, so the leave-one-source-out clause")
    print("  cannot be applied. Declared before the number existed.")

    a.out.write_text(json.dumps({
        "what": "pre-declared out-of-sample margin, glycol-ether stratum, ThermoML net-new rows",
        "declarations": DECLARATIONS, "n_rows": int(len(d)), "n_pairs": len(keys),
        "n_solutes": int(d.solute_can.nunique()), "n_solvents": int(d.solvent_can.nunique()),
        "n_source_dois": int(d.doi.nunique()),
        "cell": {"bins": N_BINS, "ddof": DDOF, "unit": "row", "convention": "residual-only",
                 "profiles": "UD, exact InChIKey", "temperature": "each row's own"},
        "mse": round(mse, 4), "b_insuff_up": round(b_up, 4),
        "margin": round(point, 4), "ci90": [round(lo, 4), round(hi, 4)],
        "verdict": verdict, "draws": a.draws, "boot_seed": a.seed,
        "admissible": False,
        "why_not_admissible": "one source DOI; the map's leave-one-source-out clause cannot be "
                              "applied to a single-source set",
    }, indent=2) + "\n")
    print(f"\nwrote {a.out}")

    if a.check_article:
        import re
        tex = (ROOT / "paper/grounding_paradox.tex").read_text()
        # The sentence was split in the 2026-08-19 readability pass ("..., and there the margin
        # is" -> ". There the margin is"), and this gate reported it as reworded, which is what it
        # is for.  The numerals and their order are unchanged.
        pat = (r"supplies \$(\d+)\$ rows over \$(\d+)\$ pairs the broad set does not carry,\s+"
               r"\$(\d+)\$ solutes in diethylene and triethylene glycol at three temperatures\.\s+"
               r"There the margin is\s+\$\+([\d.]+)\$ \$\[\+([\d.]+),\+([\d.]+)\]\$")
        mm = re.search(pat, tex)
        if mm is None:
            raise SystemExit("the out-of-sample sentence is not in the article in the form this "
                             "gate reads; it was reworded or removed")
        want = (str(len(d)), str(len(keys)), str(d.solute_can.nunique()),
                f"{point:.2f}", f"{lo:.2f}", f"{hi:.2f}")
        bad = sum(g != w for g, w in zip(mm.groups(), want))
        print("\narticle bind:")
        for label, got, w in zip(("rows", "pairs", "solutes", "margin", "ci lo", "ci hi"),
                                 mm.groups(), want):
            print(f"  {'ok  ' if got == w else 'FAIL'}  {label:8s} paper {got:>7s}   "
                  f"deposit {w:>7s}")
        if bad:
            raise SystemExit(f"{bad} numerals disagree with the deposit")


if __name__ == "__main__":
    main()
