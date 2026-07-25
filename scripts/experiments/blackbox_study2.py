#!/usr/bin/env python
"""Black-box Study 2: does the model's temperature response carry crystal thermodynamics?

The pre-registration asks whether d(ln x2)/d(1/T) recovers -dH_fus/R. Taken literally that
test is unanswerable, because the DATA do not carry that much crystal signal either: the SLE
identity is

    d(ln x2)/d(1/T) = -dH_fus/R - d(ln gamma2)/d(1/T)

and the activity term dominates. Measured on this corpus, the empirical slope correlates with
-dH_fus/R at only r = +0.239 (train, 1353 pairs / 151 solutes) and +0.126 (held out). A model
that reproduced the data perfectly would score exactly that, not 1.0. So the ceiling is
measured first and every model number is read against it:

  2b-fair    corr(model slope, EMPIRICAL slope)   -- ceiling 1.0; did it learn the T-response?
  2b-crystal corr(model slope, -dH_fus/R)         -- ceiling is the data's own r, not 1.0
  2a         curvature of ln x2 in 1/T            -- pure van't Hoff is linear; compare to data

Slopes are taken at FIXED (solute, solvent); a slope pooled across solvents would confound
activity differences with temperature.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/experiments/blackbox_study2.py \
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

from blackbox_study1a import build_oracle  # noqa: E402

R_GAS = 8.314462618
MIN_T_POINTS = 3


def fit_slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Slope of y on x, its standard error, and the quadratic coefficient (curvature)."""
    b, a = np.polyfit(x, y, 1)
    resid = y - (b * x + a)
    dof = len(x) - 2
    sxx = ((x - x.mean()) ** 2).sum()
    se = float(np.sqrt((resid ** 2).sum() / dof / sxx)) if dof > 0 and sxx > 0 else np.nan
    curv = float(np.polyfit(x, y, 2)[0]) if len(x) >= 4 else np.nan
    return float(b), se, curv


def predict_lnx2(ckpt: Path, rows: pd.DataFrame, device) -> np.ndarray:
    from tgnn_solv.baselines.direct_gnn import DirectGNN
    from tgnn_solv.config import TGNNSolvConfig
    from train import load_data

    ck = torch.load(ckpt, map_location="cpu", weights_only=False)
    cfg = TGNNSolvConfig(**dict(ck["config"]))
    model = DirectGNN(cfg=cfg).to(device)
    missing, _ = model.load_state_dict(
        ck.get("model_state_dict") or ck.get("model_state"), strict=False)
    if missing:
        raise SystemExit(f"incomplete state_dict: {missing[:5]}")
    model.eval()

    tmp = Path("/tmp/_bb_study2_rows.csv")
    rows.to_csv(tmp, index=False)
    cfg.num_workers = 0
    out = []
    loader = load_data(str(tmp), cfg, shuffle=False, seed=0, batch_size=64)
    with torch.no_grad():
        for sol, slv, tgt in loader:
            T = tgt["T"] if "T" in tgt else tgt.get("temperature")
            o = model(sol, slv, T,
                      solvent_type=tgt.get("solvent_type"),
                      solute_morgan_fp=tgt.get("solute_morgan_fp"),
                      solvent_morgan_fp=tgt.get("solvent_morgan_fp"),
                      solute_descriptors=tgt.get("solute_descriptors"),
                      solvent_descriptors=tgt.get("solvent_descriptors"))
            v = o["ln_x2"] if isinstance(o, dict) else o
            out.append(np.asarray(v.squeeze(-1).cpu()))
    p = np.concatenate(out)
    if len(p) != len(rows):
        raise SystemExit(f"predictions {len(p)} != rows {len(rows)}")
    return p


def per_pair_table(rows: pd.DataFrame, ycol: str, pred: np.ndarray | None) -> pd.DataFrame:
    rows = rows.copy()
    if pred is not None:
        rows["_pred"] = pred
    recs = []
    for (sol, slv), g in rows.groupby(["solute_smiles", "solvent_smiles"]):
        if g["temperature"].nunique() < MIN_T_POINTS:
            continue
        x = 1.0 / g["temperature"].to_numpy()
        b_e, se_e, c_e = fit_slope(x, g[ycol].to_numpy())
        rec = {"solute": sol, "solvent": slv, "n_T": len(g),
               "span": float(g["temperature"].max() - g["temperature"].min()),
               "emp_slope": b_e, "emp_se": se_e, "emp_curv": c_e,
               "target": -float(g["dH_fus_oracle"].iloc[0]) / R_GAS}
        if pred is not None:
            b_m, se_m, c_m = fit_slope(x, g["_pred"].to_numpy())
            rec.update(model_slope=b_m, model_se=se_m, model_curv=c_m)
        recs.append(rec)
    return pd.DataFrame(recs)


def corr_with_null(a: np.ndarray, b: np.ndarray, groups: np.ndarray,
                   n_perm: int = 2000) -> tuple[float, float]:
    """Pearson r plus a null that permutes SOLUTE identity, keeping within-solute structure."""
    r = float(np.corrcoef(a, b)[0, 1])
    uniq = np.unique(groups)
    null = np.empty(n_perm)
    for i in range(n_perm):
        rng = np.random.default_rng(i)
        mapping = dict(zip(uniq, rng.permutation(uniq)))
        # reassign each solute's target to another solute's, keeping pair structure
        bmap = {s: b[groups == s][0] for s in uniq}
        bp = np.array([bmap[mapping[s]] for s in groups])
        null[i] = np.corrcoef(a, bp)[0, 1]
    p = float((np.abs(null) >= abs(r)).mean())
    return r, p


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoints", nargs="+", required=True)
    ap.add_argument("--oracle", default="results/open_crystal_artifact/open_crystal_solute.csv")
    ap.add_argument("--data-dir", default="notebooks/data/processed")
    ap.add_argument("--n-perm", type=int, default=2000)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    dd, oracle = _REPO / args.data_dir, _REPO / args.oracle
    device = torch.device(args.device)

    ho = pd.concat([build_oracle(dd / "val.csv", oracle),
                    build_oracle(dd / "test.csv", oracle)], ignore_index=True)
    tr = build_oracle(dd / "train.csv", oracle)
    ycol = "ln_x2"

    # ---- the ceiling, measured before any model is touched ----
    tr_tab = per_pair_table(tr, ycol, None)
    ho_tab = per_pair_table(ho, ycol, None)
    ceil_tr = float(np.corrcoef(tr_tab.emp_slope, tr_tab.target)[0, 1])
    ceil_ho, ceil_p = corr_with_null(ho_tab.emp_slope.to_numpy(), ho_tab.target.to_numpy(),
                                     ho_tab.solute.to_numpy(), args.n_perm)
    print("=== CEILING (data only, no model) ===")
    print(f"  train    : {len(tr_tab)} pairs / {tr_tab.solute.nunique()} solutes"
          f"   corr(emp slope, -dH/R) = {ceil_tr:+.3f}")
    print(f"  held out : {len(ho_tab)} pairs / {ho_tab.solute.nunique()} solutes"
          f"   corr = {ceil_ho:+.3f}  (permutation p = {ceil_p:.3f})")
    print(f"  slope resolution: median |slope|/SE = "
          f"{(ho_tab.emp_slope.abs()/ho_tab.emp_se).median():.1f}"
          f"   wrong-signed {int((ho_tab.emp_slope>0).sum())}/{len(ho_tab)}")
    print("  A model reproducing the data exactly scores the held-out ceiling, not 1.0.")

    results = {"ceiling_train": ceil_tr, "ceiling_holdout": ceil_ho,
               "ceiling_holdout_p": ceil_p,
               "pairs": int(len(ho_tab)), "solutes": int(ho_tab.solute.nunique()),
               "seeds": {}}

    for ck in args.checkpoints:
        ck = Path(ck)
        print(f"\n=== {ck.name} ===")
        pred = predict_lnx2(ck, ho, device)
        tab = per_pair_table(ho, ycol, pred)
        g = tab.solute.to_numpy()

        r_fair, p_fair = corr_with_null(tab.model_slope.to_numpy(),
                                        tab.emp_slope.to_numpy(), g, args.n_perm)
        r_cry, p_cry = corr_with_null(tab.model_slope.to_numpy(),
                                      tab.target.to_numpy(), g, args.n_perm)
        # "Fraction of ceiling" is only meaningful when the ceiling itself is distinguishable
        # from zero. Dividing by a non-significant ceiling manufactures large ratios out of
        # noise in the denominator -- report it as undefined instead.
        ceiling_real = ceil_p <= 0.05
        frac = (r_cry / ceil_ho) if (ceiling_real and abs(ceil_ho) > 1e-9) else None
        frac_s = f"{frac:+.2f}" if frac is not None else "undefined (ceiling not > 0)"
        print(f"  2b-fair    corr(model, empirical slope) = {r_fair:+.3f}  (p = {p_fair:.3f})"
              "   [ceiling 1.0]")
        print(f"  2b-crystal corr(model, -dH/R)           = {r_cry:+.3f}  (p = {p_cry:.3f})"
              f"   [held-out ceiling {ceil_ho:+.3f}, p={ceil_p:.3f}; fraction {frac_s}]")
        print(f"  model slope range {tab.model_slope.min():.0f} .. {tab.model_slope.max():.0f}"
              f"   vs empirical {tab.emp_slope.min():.0f} .. {tab.emp_slope.max():.0f}")
        print(f"  median |model - empirical| slope = "
              f"{(tab.model_slope - tab.emp_slope).abs().median():.0f}")
        # 2a: curvature. Pure van't Hoff is linear in 1/T.
        cm, ce = tab.model_curv.dropna(), tab.emp_curv.dropna()
        if len(cm) > 3:
            print(f"  2a curvature in 1/T: model median |c| = {cm.abs().median():.3g}, "
                  f"data {ce.abs().median():.3g}")
        results["seeds"][ck.name] = {
            "r_fair": r_fair, "p_fair": p_fair, "r_crystal": r_cry, "p_crystal": p_cry,
            "fraction_of_ceiling": frac,
            "ceiling_significant": bool(ceiling_real),
            "median_abs_slope_error": float((tab.model_slope - tab.emp_slope).abs().median()),
        }

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(results, indent=2))
        print(f"\nwrote {args.out_json}")


if __name__ == "__main__":
    main()
