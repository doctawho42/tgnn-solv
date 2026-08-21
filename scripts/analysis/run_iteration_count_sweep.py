#!/usr/bin/env python
"""How far the segment fixed point's iteration count moves the second axis, on tabulated inputs.

WHAT THIS ANSWERS.  The deployed arms are fitted at sixteen segment iterations and scored at
thirty, and the convergence evidence for that pair is a regression test on hand-built Gaussian
profiles where the gap is 6e-5.  Sec. S1 says so and calls the exposure that carries to the
substitution contrast unmeasured.  On the LEARNED side it stays unmeasured, because the tree
retains no COSMO-SAC weights.  On the TABULATED side it need not: the sigma-oracle arm's closure
input is the tabulation itself, and the whole second axis is computed from tabulated profiles, so
the count's effect there is a CPU calculation over deposited files and no checkpoint is required.

WHAT IS MEASURED, and in the units of the claim rather than in a proxy.  The second axis is
expressed in squared ln gamma, so the count is swept through the estimator itself: MSE, the binning
bound and the margin are recomputed at each count, on the broad IDAC set and on the glycol-ether
stratum the finding rests on.  A sensitivity reported as a shift in ln gamma would have to be
converted before it could be compared with a margin; this needs no conversion.

WHAT IT DOES NOT DO.  It bounds one side.  The learned arm's profiles are not recoverable, so the
substitution contrast on the solubility axis keeps an unmeasured component, and the honest form of
the claim is conditional on the evaluation count -- which is what the article now says.

Usage
-----
    python scripts/analysis/run_iteration_count_sweep.py
    python scripts/analysis/run_iteration_count_sweep.py --counts 8 16 30 300
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

BROAD = ROOT / "paper/si_tables/broad_idac_set_477.csv"
HOME_UD = Path.home() / "COSMOSAC/profiles/UD"
GLYCOLS = {"OCCO", "OCCOCCO", "OCCOCCOCCO", "OCCOCCOCCOCCO"}
N_BINS, DDOF = 8, 1


def ud_profiles() -> dict:
    """{InChIKey: (51-bin profile, cavity area)} from the untyped sigma/ directory."""
    out: dict = {}
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


def binsuff(g: np.ndarray, m: np.ndarray) -> float:
    q = np.quantile(g, np.linspace(0.0, 1.0, N_BINS + 1))
    q[0] -= 1e-9
    q[-1] += 1e-9
    idx = np.digitize(g, q[1:-1])
    return float(sum((np.sum(idx == b) / len(m)) * m[idx == b].var(ddof=DDOF)
                     for b in range(N_BINS) if np.sum(idx == b) > DDOF))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--counts", type=int, nargs="+", default=[8, 16, 30, 300])
    ap.add_argument("--out", type=Path, default=ROOT / "results/b_insuff/iteration_count_sweep.json")
    ap.add_argument("--check-si", action="store_true",
                    help="bind the Supporting Information's sweep sentence to this run")
    a = ap.parse_args()

    import pandas as pd
    import torch
    from tgnn_solv.layers import CosmoSacLayer

    d = pd.read_csv(BROAD)
    table = ud_profiles()
    have = d.solute_ud_key.isin(table) & d.solvent_ud_key.isin(table)
    d = d[have].copy()
    m = d.m_ln_gamma_inf.to_numpy(float)
    gly = d.solvent_smiles.isin(GLYCOLS).to_numpy()
    print(f"broad IDAC set: {len(d)} rows with a UD profile on both sides, "
          f"{int(gly.sum())} of them glycol-ether\n")

    # DOUBLE PRECISION, because the deposit is: run_b_insuff_representative.py builds the layer as
    # CosmoSacLayer().double().eval() with n_iter_eval = 300. Sweeping in float32 would put a
    # numerical difference into a comparison whose whole point is the iteration count.
    p2 = torch.tensor(np.stack([table[k][0] for k in d.solute_ud_key]), dtype=torch.double)
    A2 = torch.tensor([table[k][1] for k in d.solute_ud_key], dtype=torch.double)
    p1 = torch.tensor(np.stack([table[k][0] for k in d.solvent_ud_key]), dtype=torch.double)
    A1 = torch.tensor([table[k][1] for k in d.solvent_ud_key], dtype=torch.double)
    T = torch.tensor(d.T_K.to_numpy(float), dtype=torch.double)

    layer = CosmoSacLayer(cfg=None).double()
    layer.eval()
    rows, gvals = [], {}
    print(f"{'n_iter':>7} | {'set: MSE':>10} {'bound':>8} {'margin':>9} "
          f"| {'glycol: MSE':>12} {'bound':>8} {'margin':>9}")
    for n in a.counts:
        layer.n_iter_eval = n
        with torch.no_grad():
            g = layer.ln_gamma_inf(p2, p1, A2, A1, None, None, T).numpy()
        gvals[n] = g
        rec = {"n_iter": n}
        for label, sel in (("set", np.ones(len(g), bool)), ("glycol", gly)):
            mse = float(np.mean((m[sel] - g[sel]) ** 2))
            b = binsuff(g[sel], m[sel])
            rec[label] = {"n": int(sel.sum()), "mse": round(mse, 4),
                          "b_insuff_up": round(b, 4), "margin": round(mse - 2 * b, 4)}
        rows.append(rec)
        print(f"{n:>7} | {rec['set']['mse']:>10.3f} {rec['set']['b_insuff_up']:>8.3f} "
              f"{rec['set']['margin']:>+9.3f} | {rec['glycol']['mse']:>12.3f} "
              f"{rec['glycol']['b_insuff_up']:>8.3f} {rec['glycol']['margin']:>+9.3f}")

    ref = max(a.counts)
    print(f"\nln gamma movement against the converged reference at {ref} iterations:")
    for n in a.counts:
        dv = np.abs(gvals[n] - gvals[ref])
        print(f"  {n:>3} vs {ref}: median |d ln gamma| {np.median(dv):.4f}, "
              f"90th pct {np.percentile(dv, 90):.4f}, max {dv.max():.4f}")

    span = {k: (min(r[k]["margin"] for r in rows), max(r[k]["margin"] for r in rows))
            for k in ("set", "glycol")}
    print(f"\nMargin span across the counts swept:")
    for k, (lo, hi) in span.items():
        print(f"  {k:<7} {lo:+.3f} to {hi:+.3f}   (width {hi - lo:.3f})")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({
        "what": "segment-iteration count swept through the estimator on TABULATED UD profiles",
        "counts": a.counts, "n_rows": int(len(d)), "n_glycol": int(gly.sum()),
        "cell": {"bins": N_BINS, "ddof": DDOF, "unit": "row", "convention": "residual-only"},
        "by_count": rows,
        "margin_span": {k: [round(v[0], 4), round(v[1], 4)] for k, v in span.items()},
    }, indent=2) + "\n")
    print(f"\nwrote {a.out}")

    if a.check_si:
        import re
        si = re.sub(r"\s+", " ", (ROOT / "paper/sections/SI.tex").read_text())
        by = {r["n_iter"]: r for r in rows}
        want = [("set margin, 8", f"{by[8]['set']['margin']:+.2f}"),
                ("set margin, 16", f"{by[16]['set']['margin']:+.2f}"),
                ("set margin, 30", f"{by[30]['set']['margin']:+.2f}"),
                ("set margin, 300", f"{by[300]['set']['margin']:+.2f}"),
                ("glycol margin, 8", f"{by[8]['glycol']['margin']:+.2f}"),
                ("glycol margin, 16", f"{by[16]['glycol']['margin']:+.2f}"),
                ("glycol margin, 30", f"{by[30]['glycol']['margin']:+.2f}"),
                ("glycol margin, 300", f"{by[300]['glycol']['margin']:+.2f}")]
        pat = (r"from \$\+([\d.]+)\$ at eight iterations to \$\+([\d.]+)\$ at sixteen, "
               r"\$\+([\d.]+)\$ at thirty and \$\+([\d.]+)\$ at three hundred, and the "
               r"glycol-ether stratum's from \$\+([\d.]+)\$ to \$\+([\d.]+)\$, \$\+([\d.]+)\$ "
               r"and \$\+([\d.]+)\$")
        mm = re.search(pat, si)
        if mm is None:
            raise SystemExit("FAIL: the sweep sentence is not in the SI in the form this gate "
                             "reads; it was reworded or removed")
        bad = 0
        print("\nSI bind:")
        for (what, truth), got in zip(want, mm.groups()):
            ok = got == truth.lstrip("+")
            bad += not ok
            print(f"  {'ok  ' if ok else 'FAIL'}  {what:<20} paper {got:>7}   run {truth:>7}")
        if bad:
            raise SystemExit(f"{bad} numeral(s) disagree with this run")


if __name__ == "__main__":
    main()
