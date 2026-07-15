#!/usr/bin/env python3
"""The Picard kill-test: is the learned latent's compensating drift PREDICTABLE, a priori,
from the fixed closure's linear response?  (Decides the "spectral compensation law".)

The claim (candidate top-ML nugget C2, upgraded): when a sigma-profile head is trained
end-to-end through the fixed, misspecified COSMO-SAC closure g, the drift it develops,
d = sigma_hat - sigma_target, is the minimum-norm first-order compensation of the closure's
own model discrepancy:

        d_hat_i  =  argmin_{delta}  sum_{pairs p ni i} ( r_p - J_{p->i} . delta )^2  +  lam ||delta||^2
        r_p      =  m_p - g(sigma*_p)                       (closure residual on the pair)
        J_{p->i} =  d g_p / d shape_i   (autograd through CosmoSacLayer, SHAPE space)

i.e. d_hat = J^+ r, solved GLOBALLY (both molecules of a pair share each residual, min-norm
ridge).  If the MEASURED drift matches d_hat, the drift is a mechanistic consequence of the
closure geometry, predictable before any solubility training -- a law, not a description.

This SUPERSEDES the crude A3 test (run_local_closure_fix.py: corr(|Delta|-marginal,
|sigma_hat-sigma|-marginal) = -0.095, a scalar sigma-grid correlation).  Here we predict the
per-molecule VECTOR and gate it against the confound both reviewers flagged.

THE SMOOTHNESS CONFOUND (why a naive positive is worthless): sigma-profiles are smooth /
low-frequency, and a smooth closure's Jacobian is smooth too, so d_hat and d can align just
from shared smoothness.  Every headline is therefore gated against a SMOOTHNESS-MATCHED null:
  * wrong-molecule control -- cos(d_i, d_hat_j) for j != i: every d_hat_j is equally smooth,
    so a diagonal >> off-diagonal can only be molecule-specific mechanism.
  * row-space concentration -- fraction of d_i energy inside molecule i's own Jacobian
    subspace vs the SAME fraction for every OTHER molecule's drift (dimension- AND
    smoothness-matched).
  * residual permutation -- shuffle r_p across pairs and rebuild d_hat.

Kill switch (stated up front):
  STRONG  (mechanistic law)  : median per-molecule cos > 0.35 AND wrong-molecule perm p < 0.05
                               AND row-space own >> others.  -> spend GPU on the closure-swap.
  MODERATE (suggestive)      : positive and null-beating but weak (cos ~ 0.15-0.35).
  NULL    (smoothness only)  : cos ~ 0 or diagonal ~ off-diagonal.  -> fall back to the
                               descriptive two-axis map already in hand.  No loss.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_picard_compensation_test.py \
        --sle-checkpoint  /path/to/sle_model.pt \
        --grounded-checkpoint /path/to/grounded_base.pt \
        --out-json results/compensation/picard_test.json --fig-dir paper/figs
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
import torch
from rdkit import Chem

N_BINS = 51
SIGMA_GRID = np.linspace(-0.025, 0.025, N_BINS)
T_REF = 298.15
_SCRATCH_SLE = ("/private/tmp/claude-501/-Users-nikitapolomosnov-PycharmProjects-tgnn-solv/"
                "d8c57c82-2aba-4a38-b6f5-83d49a35e42a/scratchpad/kaggle_results/results/"
                "compensation/ckpt/sle_model.pt")
_SCRATCH_GND = _SCRATCH_SLE.replace("sle_model.pt", "grounded_base.pt")


def _canon(smi: str):
    m = Chem.MolFromSmiles(str(smi))
    return Chem.MolToSmiles(m) if m is not None else None


def _load_module(name):
    p = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def load_raw_profiles(csv_path: str) -> dict:
    """canonical SMILES -> (p_sigma[51] raw, area).  Same canonicalization as the drift path."""
    df = pd.read_csv(csv_path)
    cols = [f"sigma_p_{i}" for i in range(N_BINS)]
    smi_col = "smiles" if "smiles" in df.columns else df.columns[0]
    has_area = "sigma_area" in df.columns
    table = {}
    for _, d in df.iterrows():
        key = _canon(d[smi_col])
        if key is None or key in table:
            continue
        p = np.array([float(d[c]) for c in cols], dtype=float)
        if p.sum() <= 0:
            continue
        area = float(d["sigma_area"]) if has_area else float(p.sum())
        table[key] = (p, area)
    return table


def zero_mean(x, axis=-1):
    return x - x.mean(axis=axis, keepdims=True)


def closure_g_and_jacobian(layer, pairs, raw, eps=1e-4, use_fd=True):
    """Return (g_true[n], residual r[n], J_solute[n,51], J_solvent[n,51]) in SHAPE space.

    CRITICAL: the closure runs an unrolled fixed-point (`_segment_ln_gamma`), so the AUTOGRAD
    Jacobian explodes (||dg/dp1|| ~ 1e15 at infinite dilution, where the solvent enters only
    through the bulk segment-activity iterate). The physically meaningful object is the linear
    response of the CONVERGED closure, so we default to central FINITE DIFFERENCES in SHAPE
    space (perturb one bin, hold the rest; project to sum-zero afterward). use_fd=False falls
    back to the (numerically unreliable) autograd path for diagnostics only."""
    keys_s = list(pairs["solute_key"])
    keys_v = list(pairs["solvent_key"])
    n = len(pairs)
    totals_s = np.array([raw[k][0].sum() for k in keys_s])
    totals_v = np.array([raw[k][0].sum() for k in keys_v])
    shape_s = np.stack([raw[k][0] / raw[k][0].sum() for k in keys_s])
    shape_v = np.stack([raw[k][0] / raw[k][0].sum() for k in keys_v])
    A2 = torch.tensor([raw[k][1] for k in keys_s], dtype=torch.float)
    A1 = torch.tensor([raw[k][1] for k in keys_v], dtype=torch.float)
    T = torch.full((n,), T_REF)
    tot_s = torch.tensor(totals_s, dtype=torch.float).unsqueeze(1)
    tot_v = torch.tensor(totals_v, dtype=torch.float).unsqueeze(1)
    ts = torch.tensor(shape_s, dtype=torch.float)
    tv = torch.tensor(shape_v, dtype=torch.float)

    def g_of(s2, s1):
        with torch.no_grad():
            return layer.ln_gamma_inf(s2 * tot_s, s1 * tot_v, A2, A1, None, None, T).numpy()

    g_true = g_of(ts, tv)
    m = pairs["m"].to_numpy()
    r = m - g_true

    if not use_fd:
        s2 = ts.clone().requires_grad_(True); s1 = tv.clone().requires_grad_(True)
        g = layer.ln_gamma_inf(s2 * tot_s, s1 * tot_v, A2, A1, None, None, T)
        J2, J1 = torch.autograd.grad(g.sum(), [s2, s1])
        return g_true, r, zero_mean(J2.numpy()), zero_mean(J1.numpy())

    # central finite differences in shape space, one bin at a time (converged-closure Jacobian)
    J2 = np.zeros((n, N_BINS)); J1 = np.zeros((n, N_BINS))
    for j in range(N_BINS):
        e = torch.zeros(N_BINS); e[j] = eps
        J2[:, j] = (g_of(ts + e, tv) - g_of(ts - e, tv)) / (2 * eps)
        J1[:, j] = (g_of(ts, tv + e) - g_of(ts, tv - e)) / (2 * eps)
    return g_true, r, zero_mean(J2), zero_mean(J1)


def predict_drift(sle_ckpt, grounded_ckpt, sigma_csv, mol_keys, device):
    """Return dict key -> (d_iso, d_total, sigma_hat_sle) in SHAPE space, for keys we can predict."""
    comp = _load_module("run_compensation_surrogate.py")
    from tgnn_solv.inference import load_model
    true_shapes = comp.load_true_shapes(sigma_csv)
    keep = [(k, _canon(k)) for k in mol_keys]
    keep = [(k, c) for k, c in keep if c is not None and c in true_shapes]
    smiles = [k for k, _ in keep]
    sig_true = np.stack([true_shapes[c] for _, c in keep])

    sle, _ = load_model(sle_ckpt, device=device)
    sig_sle = comp.predict_sigma_hat(sle, smiles, device)
    out = {}
    if grounded_ckpt:
        gnd, _ = load_model(grounded_ckpt, device=device)
        sig_gnd = comp.predict_sigma_hat(gnd, smiles, device)
        for i, (k, _) in enumerate(keep):
            out[k] = (sig_sle[i] - sig_gnd[i], sig_sle[i] - sig_true[i], sig_sle[i])
    else:
        for i, (k, _) in enumerate(keep):
            out[k] = (None, sig_sle[i] - sig_true[i], sig_sle[i])
    return out, {k: c for k, c in keep}


def ridge_min_norm(design, r, lam):
    """Underdetermined min-norm ridge: delta = A^T (A A^T + lam I)^-1 r."""
    G = design @ design.T
    lam_eff = lam * (np.trace(G) / max(G.shape[0], 1) + 1e-12)
    sol = np.linalg.solve(G + lam_eff * np.eye(G.shape[0]), r)
    return design.T @ sol


def cos_rows(A, B):
    an = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
    bn = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
    return np.sum(an * bn, axis=1)


def rowspace_fraction(basis, d):
    """Fraction of ||d||^2 inside the subspace spanned by `basis` rows (orthonormalized)."""
    if basis.shape[0] == 0 or np.linalg.norm(d) < 1e-12:
        return np.nan
    q, _ = np.linalg.qr(basis.T)              # (51, k) orthonormal cols
    proj = q.T @ d
    return float((proj @ proj) / (d @ d))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matched-csv", default="results/b_insuff/matched_pairs.csv")
    ap.add_argument("--sigma-profiles", default="results/sigma_profile_artifact/sigma_profiles.csv")
    ap.add_argument("--sle-checkpoint", default=_SCRATCH_SLE)
    ap.add_argument("--grounded-checkpoint", default=_SCRATCH_GND)
    ap.add_argument("--target", choices=["iso", "total"], default="iso",
                    help="drift target: iso = sigma_hat_SLE - sigma_hat_grounded (confound-free); "
                         "total = sigma_hat_SLE - sigma_true")
    ap.add_argument("--lam", type=float, default=1e-2)
    ap.add_argument("--n-perm", type=int, default=2000)
    ap.add_argument("--out-json", type=Path, default=Path("results/compensation/picard_test.json"))
    ap.add_argument("--fig-dir", type=Path, default=Path("paper/figs"))
    args = ap.parse_args()

    from tgnn_solv.config import TGNNSolvConfig
    from tgnn_solv.layers import CosmoSacLayer

    rng = np.random.default_rng(0)
    device = torch.device("cpu")

    raw = load_raw_profiles(args.sigma_profiles)
    pairs = pd.read_csv(args.matched_csv, low_memory=False)
    # canonical-key the pair table into the same space as the raw/drift tables
    pairs["solute_key"] = pairs["solute_key"].map(_canon)
    pairs["solvent_key"] = pairs["solvent_key"].map(_canon)
    pairs = pairs[pairs["solute_key"].isin(raw) & pairs["solvent_key"].isin(raw)].reset_index(drop=True)
    n_pairs = len(pairs)
    print(f"matched pairs with true profiles: {n_pairs}")

    # fixed (rank-0) residual-only closure -- the DEPLOYED convention
    layer = CosmoSacLayer(cfg=TGNNSolvConfig(activity_model="cosmo_sac", cosmo_sac_kernel_residual_rank=0))
    layer.eval()
    g_true, r, J2, J1 = closure_g_and_jacobian(layer, pairs, raw)
    # sanity: recomputed g should match stored residual-only g_res
    if "g_res" in pairs.columns:
        dev = float(np.mean(np.abs(g_true - pairs["g_res"].to_numpy())))
        print(f"closure recompute vs stored g_res: mean |diff| = {dev:.4f}")

    # measured drift (per molecule)
    mol_keys = sorted(set(pairs["solute_key"]) | set(pairs["solvent_key"]))
    drift, _ = predict_drift(args.sle_checkpoint, args.grounded_checkpoint or None,
                             args.sigma_profiles, mol_keys, device)
    tgt_idx = 0 if args.target == "iso" else 1
    have = [k for k in mol_keys if k in drift and drift[k][tgt_idx] is not None]
    idx = {k: i for i, k in enumerate(have)}
    M = len(have)
    print(f"molecules with predicted drift ({args.target}): {M} / {len(mol_keys)}")

    D_meas = np.stack([zero_mean(drift[k][tgt_idx]) for k in have])       # (M,51) measured

    # ---- global min-norm ridge Picard prediction ----
    design = np.zeros((n_pairs, M * N_BINS))
    row_blocks = {k: [] for k in have}          # per-molecule Jacobian rows (for row-space test)
    for p in range(n_pairs):
        a = idx[pairs["solute_key"][p]]
        b = idx[pairs["solvent_key"][p]]
        design[p, a * N_BINS:(a + 1) * N_BINS] += J2[p]
        design[p, b * N_BINS:(b + 1) * N_BINS] += J1[p]
        row_blocks[pairs["solute_key"][p]].append(J2[p])
        row_blocks[pairs["solvent_key"][p]].append(J1[p])
    delta = ridge_min_norm(design, r, args.lam).reshape(M, N_BINS)
    D_hat = zero_mean(delta)

    # molecules actually constrained (appear in >=1 pair) -- all of `have` by construction
    constrained = [k for k in have if len(row_blocks[k]) > 0]
    ci = [idx[k] for k in constrained]
    dm, dh = D_meas[ci], D_hat[ci]

    # ---- metric 1: per-molecule cosine ----
    cos_diag = cos_rows(dm, dh)
    # ---- metric 2: wrong-molecule control (smoothness-matched) ----
    C = (dm / (np.linalg.norm(dm, axis=1, keepdims=True) + 1e-12)) @ \
        (dh / (np.linalg.norm(dh, axis=1, keepdims=True) + 1e-12)).T   # cos(d_i, d_hat_j)
    off = C[~np.eye(len(ci), dtype=bool)]
    diag_mean = float(np.mean(np.diag(C)))
    off_mean = float(np.mean(off))
    # permutation p: is the diagonal mean beaten by random molecule<->prediction matchings?
    perm_means = np.empty(args.n_perm)
    k = len(ci)
    for t in range(args.n_perm):
        perm_means[t] = np.mean(C[np.arange(k), rng.permutation(k)])
    p_wrongmol = float((np.sum(perm_means >= diag_mean) + 1) / (args.n_perm + 1))

    # ---- metric 3: row-space concentration (dimension + smoothness matched) ----
    own_frac, other_frac = [], []
    for k_ in constrained:
        basis = np.stack(row_blocks[k_])
        own = rowspace_fraction(basis, D_meas[idx[k_]])
        others = [rowspace_fraction(basis, D_meas[idx[o]]) for o in constrained if o != k_]
        own_frac.append(own)
        other_frac.append(np.nanmean(others))
    own_frac = np.array(own_frac); other_frac = np.array(other_frac)
    rowspace_p = float((np.sum(other_frac >= own_frac) + 1) / (len(own_frac) + 1))  # paired sign-ish

    # ---- metric 4: residual-permutation null on pooled cosine ----
    real_pooled = float(np.mean(cos_diag))
    null_pooled = np.empty(min(args.n_perm, 1000))
    for t in range(len(null_pooled)):
        dh_t = zero_mean(ridge_min_norm(design, r[rng.permutation(n_pairs)], args.lam).reshape(M, N_BINS)[ci])
        null_pooled[t] = np.mean(cos_rows(dm, dh_t))
    p_residperm = float((np.sum(null_pooled >= real_pooled) + 1) / (len(null_pooled) + 1))

    # ---- pooled R^2 with optimal global scale ----
    flat_m, flat_h = dm.ravel(), dh.ravel()
    alpha = float(flat_m @ flat_h / (flat_h @ flat_h + 1e-12))
    ss_res = float(np.sum((flat_m - alpha * flat_h) ** 2))
    ss_tot = float(np.sum((flat_m - flat_m.mean()) ** 2))
    r2_scaled = 1.0 - ss_res / (ss_tot + 1e-12)

    med_cos = float(np.median(cos_diag))
    if med_cos > 0.35 and p_wrongmol < 0.05 and float(np.nanmean(own_frac - other_frac)) > 0.05:
        verdict = "STRONG"
    elif med_cos > 0.15 and (p_wrongmol < 0.05 or p_residperm < 0.05):
        verdict = "MODERATE"
    else:
        verdict = "NULL"

    res = {
        "target": args.target, "n_pairs": n_pairs, "n_molecules": M, "n_constrained": len(ci),
        "lambda": args.lam,
        "per_molecule_cosine": {
            "median": med_cos, "mean": float(np.mean(cos_diag)),
            "frac_positive": float(np.mean(cos_diag > 0)),
            "q25": float(np.quantile(cos_diag, 0.25)), "q75": float(np.quantile(cos_diag, 0.75)),
        },
        "wrong_molecule_control": {
            "diag_mean_cos": diag_mean, "offdiag_mean_cos": off_mean,
            "gap": diag_mean - off_mean, "perm_p_value": p_wrongmol, "n_perm": args.n_perm,
        },
        "rowspace_concentration": {
            "own_mean": float(np.nanmean(own_frac)), "other_mean": float(np.nanmean(other_frac)),
            "gap": float(np.nanmean(own_frac - other_frac)),
            "median_subspace_dim": float(np.median([len(row_blocks[k]) for k in constrained])),
            "sign_p_value": rowspace_p,
        },
        "residual_permutation": {"real_pooled_cos": real_pooled,
                                 "null_mean": float(np.mean(null_pooled)),
                                 "p_value": p_residperm, "n_perm": len(null_pooled)},
        "pooled_r2_optimal_scale": r2_scaled, "optimal_scale_alpha": alpha,
        "verdict": verdict,
    }

    print(f"\n=== PICARD COMPENSATION TEST ({args.target} drift) ===")
    print(f"per-molecule cos(d, d_hat): median {med_cos:+.3f}  mean {np.mean(cos_diag):+.3f}  "
          f"frac>0 {np.mean(cos_diag>0):.0%}")
    print(f"wrong-molecule control:  diag {diag_mean:+.3f}  vs off-diag {off_mean:+.3f}  "
          f"(gap {diag_mean-off_mean:+.3f}, perm p={p_wrongmol:.3f})")
    print(f"row-space concentration: own {np.nanmean(own_frac):.2f}  vs others {np.nanmean(other_frac):.2f}  "
          f"(median subspace dim {np.median([len(row_blocks[k]) for k in constrained]):.0f}/50, p={rowspace_p:.3f})")
    print(f"residual-permutation:    real {real_pooled:+.3f}  vs null {np.mean(null_pooled):+.3f}  (p={p_residperm:.3f})")
    print(f"pooled R^2 (optimal scale): {r2_scaled:+.3f}")
    print(f"\nVERDICT: {verdict}")

    # ---- figure ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from pathlib import Path as _Path
        _st = _Path.home() / ".claude/skills/repo-to-paper/assets/softpastel.mplstyle"
        if _st.exists():
            plt.style.use(str(_st))
        fig, ax = plt.subplots(1, 3, figsize=(13.5, 4.0))
        ax[0].hist(cos_diag, bins=15, color="#8FB3DA", alpha=0.85)
        ax[0].axvline(0, color="0.6", lw=0.8); ax[0].axvline(med_cos, color="#E8A98C", lw=2, label=f"median {med_cos:+.2f}")
        ax[0].set_xlabel(r"cos($d_i$, $\hat d_i$)"); ax[0].set_ylabel("molecules")
        ax[0].set_title("Per-molecule drift alignment"); ax[0].legend(fontsize=8)
        ax[1].hist(perm_means, bins=30, color="0.75", label="wrong-molecule null")
        ax[1].axvline(diag_mean, color="#E8A98C", lw=2, label=f"real diag {diag_mean:+.2f}")
        ax[1].set_xlabel("mean cos over matching"); ax[1].set_title(f"Smoothness-matched null (p={p_wrongmol:.3f})")
        ax[1].legend(fontsize=8)
        # exemplar: the best-aligned constrained molecule
        best = ci[int(np.argmax(cos_diag))]
        ax[2].plot(SIGMA_GRID, D_meas[best], color="#E8A98C", lw=2, label="measured drift")
        sc = (D_meas[best] @ D_hat[best]) / (D_hat[best] @ D_hat[best] + 1e-12)
        ax[2].plot(SIGMA_GRID, sc * D_hat[best], color="#8FB3DA", lw=2, ls="--", label=r"Picard $\hat d$ (scaled)")
        ax[2].axhline(0, color="0.7", lw=0.6); ax[2].set_xlabel(r"$\sigma$"); ax[2].set_ylabel("drift (shape)")
        ax[2].set_title(f"Best exemplar (cos {np.max(cos_diag):+.2f})"); ax[2].legend(fontsize=8)
        fig.tight_layout()
        args.fig_dir.mkdir(parents=True, exist_ok=True)
        for ext in ("pdf", "png"):
            fig.savefig(args.fig_dir / f"fig_picard_test.{ext}", dpi=150)
        res["figure"] = str(args.fig_dir / "fig_picard_test.pdf")
        plt.close(fig)
    except Exception as e:  # noqa: BLE001
        res["figure_error"] = str(e)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(res, indent=2))
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
