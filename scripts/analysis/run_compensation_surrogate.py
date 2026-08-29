#!/usr/bin/env python3
"""Analysis #2, Tier A (A1+A2): is the learned sigma-profile a closure-compensating
surrogate rather than the physical quantity?

On the keystone matched set we have, per molecule, both the TRUE VT-2005 sigma-profile
(sigma) and the model's predicted profile (sigma_hat). We test whether the deviation
r = sigma_hat - sigma is SYSTEMATIC (not noise) and TRANSFERABLE (a single distortion
operator, not per-molecule fitting) -- the signature of a closure-inverse compensation.

  A1  structure:   ||r||/||sigma||, PCA spectrum of {r_i} (systematic => low-rank),
                   the dominant deviation mode on the sigma-grid.
  A2  transferable: fit a distortion D (ridge, sigma_hat ~ sigma) on a train half; on the
                   held-out half compare MSE(D(sigma), sigma_hat) vs MSE(sigma, sigma_hat).
                   D << identity out-of-sample => the compensation is a consistent,
                   generalizable transform (dodges the tautological in-distribution trap).

Kill switch: if the PCA spectrum is flat (A1) or D does not beat identity out-of-sample
(A2), the deviation is noise / bespoke and the "compensating surrogate" claim is not
supported -- report that honestly.

CONFOUND (read before interpreting): if the model had NO sigma grounding (no sigma-warmup,
no sigma aux), a sigma_hat that deviates from the true sigma is only weakly surprising --
it was never asked to be physical. The AIRTIGHT claim ("grounding gives illusory
interpretability -- SLE pulls sigma_hat off physical truth DESPITE grounding") needs a
GROUNDED baseline. Pass --baseline-checkpoint <grounded model> to run the ISOLATION: the
SLE-induced distortion sigma_hat_SLE - sigma_hat_grounded, with A1/A2 run on THAT. A
systematic, transferable isolation is the airtight signature; it separates real
compensation from "never grounded".

    # basic (sigma_hat vs true sigma):
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_compensation_surrogate.py \
        --checkpoint checkpoints/cosmo_sac/tgnn_cosmo.pt \
        --sigma-profiles results/sigma_profile_artifact/sigma_profiles.csv \
        --matched-csv results/b_insuff/matched_pairs.csv \
        --out-json results/compensation/surrogate.json --fig-dir paper/figs
    # airtight isolation (needs a grounded baseline, e.g. the Tier-3 Stage-A base):
    #   ... --checkpoint <SLE model> --baseline-checkpoint <grounded model>
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
import torch
from rdkit import Chem

from tgnn_solv.device import resolve_device

N_BINS = 51
SIGMA_GRID = np.linspace(-0.025, 0.025, N_BINS)


def _canon(smi: str):
    m = Chem.MolFromSmiles(str(smi))
    return Chem.MolToSmiles(m) if m is not None else None


def load_true_shapes(csv_path: str) -> dict:
    """canonical SMILES -> true sigma SHAPE (p_sigma normalized to sum 1)."""
    df = pd.read_csv(csv_path)
    cols = [f"sigma_p_{i}" for i in range(N_BINS)]
    smi_col = "smiles" if "smiles" in df.columns else df.columns[0]
    table = {}
    for _, d in df.iterrows():
        key = _canon(d[smi_col])
        if key is None:
            continue
        p = np.array([float(d[c]) for c in cols], dtype=float)
        s = p.sum()
        if s > 0:
            table[key] = p / s
    return table


def predict_sigma_hat(model, smiles_list, device) -> np.ndarray:
    """Per-molecule predicted sigma SHAPE (n, 51) via the canonical sigma-aux path."""
    from torch_geometric.data import Batch
    from tgnn_solv.inference import _smiles_to_graph_for_model

    graphs = [_smiles_to_graph_for_model(s, model) for s in smiles_list]
    out = []
    model.eval()
    with torch.no_grad():
        for i in range(0, len(graphs), 64):
            batch = Batch.from_data_list(graphs[i:i + 64]).to(device)
            _, payload, _, _ = model._encode_and_readout(batch, "solute", temp_feat=None)
            g = payload["value"]
            sig = model.head_sigma(g)
            out.append(sig["p_shape"].detach().cpu().numpy())
    return np.concatenate(out, axis=0)


def ridge_fit(X, Y, lam):
    d = X.shape[1]
    A = X.T @ X + lam * np.eye(d)
    return np.linalg.solve(A, X.T @ Y)  # (d_in, d_out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", default="checkpoints/cosmo_sac/tgnn_cosmo.pt",
                    help="the SLE-trained model whose sigma_hat we probe")
    ap.add_argument("--baseline-checkpoint", default=None,
                    help="a GROUNDED model (sigma-warmup): enables the airtight isolation "
                         "sigma_hat_SLE - sigma_hat_grounded")
    ap.add_argument("--sigma-profiles", default="results/sigma_profile_artifact/sigma_profiles.csv")
    ap.add_argument("--matched-csv", default="results/b_insuff/matched_pairs.csv")
    # Deliberately "cpu" rather than default_device(): this script produces numbers that
    # are deposited under results/ and quoted in the manuscript, and moving the device moves
    # the last digits. It is not the wish that default_device() exists to remove -- that one
    # names an accelerator the box may not have; this one names the backend the deposited
    # figures were computed on. Pass --device explicitly to score somewhere else.
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--lam", type=float, default=1e-3)
    ap.add_argument("--out-json", type=Path, default=Path("results/compensation/surrogate.json"))
    ap.add_argument("--fig-dir", type=Path, default=Path("paper/figs"))
    ap.add_argument(
        "--exclude-smiles", nargs="*", default=None,
        help="Drop these molecules from the matched set before A1/A2, matched on "
             "canonical SMILES. Used to re-run the probe with the one molecule a "
             "grounding-stream leak touched removed, so the reported departure and "
             "its top-two share are read on a set no leak can reach.",
    )
    args = ap.parse_args()

    from tgnn_solv.inference import load_model
    # This is step 3 of kaggle_run.do_onemodel, behind a warm-up and a full SLE training.
    # Building torch.device(args.device) raw meant --allow-cpu bought the two children a
    # TGNN_ALLOW_CPU_FALLBACK this step never read: they warned, ran to completion, and
    # then the scoring died in torch.load with both checkpoints on disk unscored.
    device = resolve_device(args.device)
    model, cfg = load_model(args.checkpoint, device=device)

    true = load_true_shapes(args.sigma_profiles)
    md = pd.read_csv(args.matched_csv, low_memory=False)
    mols = set()
    for col in ("solute_key", "solvent_key"):
        if col in md.columns:
            mols |= set(md[col].dropna().astype(str))
    excluded_canon = {c for c in ( _canon(s) for s in (args.exclude_smiles or []) ) if c}
    # keep molecules for which we have a TRUE profile (canonical match)
    keep = []
    dropped: list[str] = []
    for s in sorted(mols):
        c = _canon(s)
        if c is not None and c in true:
            if c in excluded_canon:
                dropped.append(s)
                continue
            keep.append((s, c))
    if args.exclude_smiles:
        print(f"excluded on request: {len(dropped)} molecule(s) {dropped}")
    print(f"matched molecules with true VT-2005 profile: {len(keep)} / {len(mols)}")
    if len(keep) < 10:
        raise SystemExit("too few matched molecules with true profiles for A1/A2")

    smiles = [s for s, _ in keep]
    sig_true = np.stack([true[c] for _, c in keep])             # (n, 51)
    sig_hat = predict_sigma_hat(model, smiles, device)          # SLE-model sigma_hat

    def a1a2(target, ref, tag):
        """A1 (PCA of target-ref) + A2 (does a distortion ref->target transfer out-of-sample)."""
        r = target - ref
        rel = float(np.linalg.norm(r, axis=1).mean() / (np.linalg.norm(ref, axis=1).mean() + 1e-12))
        rc = r - r.mean(0, keepdims=True)
        _, S, Vt = np.linalg.svd(rc, full_matrices=False)
        ev = (S ** 2) / (S ** 2).sum()
        a1 = {"tag": tag, "n": len(keep), "rel_deviation": rel,
              "pca_evr_top5": [float(x) for x in ev[:5]],
              "top1_evr": float(ev[0]), "top2_cum_evr": float(ev[:2].sum()),
              "mean_shift_norm": float(np.linalg.norm(r.mean(0)))}
        rng = np.random.default_rng(0)
        idx = rng.permutation(len(keep)); half = len(keep) // 2
        tr, te = idx[:half], idx[half:]
        D = ridge_fit(np.column_stack([ref[tr], np.ones(len(tr))]), target[tr], args.lam)
        pred_D = np.column_stack([ref[te], np.ones(len(te))]) @ D
        mse_D = float(np.mean((pred_D - target[te]) ** 2))
        mse_id = float(np.mean((ref[te] - target[te]) ** 2))
        a2 = {"oos_mse_distortion_D": mse_D, "oos_mse_identity": mse_id,
              "improvement_ratio": float(mse_id / (mse_D + 1e-12)),
              "systematic_transferable": mse_D < 0.9 * mse_id}
        return a1, a2, r, Vt, S, ev

    # primary path: sigma_hat_SLE vs true sigma
    vt_a1, vt_a2, r, Vt, S, ev = a1a2(sig_hat, sig_true, "sigma_hat_SLE_vs_true")
    out = {"checkpoint": args.checkpoint, "vs_true": {"A1": vt_a1, "A2": vt_a2}}
    primary = ("vs_true", vt_a1, vt_a2, r, Vt, S, ev)

    # airtight isolation: SLE-induced distortion sigma_hat_SLE - sigma_hat_grounded
    if args.baseline_checkpoint:
        base_model, _ = load_model(args.baseline_checkpoint, device=device)
        sig_grounded = predict_sigma_hat(base_model, smiles, device)
        ground_rel = float(np.linalg.norm(sig_grounded - sig_true, axis=1).mean()
                           / (np.linalg.norm(sig_true, axis=1).mean() + 1e-12))
        iso = a1a2(sig_hat, sig_grounded, "SLE_minus_grounded")
        out["isolation"] = {"baseline_checkpoint": args.baseline_checkpoint,
                            "grounded_vs_true_rel_deviation": ground_rel,
                            "A1": iso[0], "A2": iso[1]}
        primary = ("isolation", *iso)

    tag, a1, a2, r, Vt, S, ev = primary
    verdict = ("SUPPORTED [%s]: deviation low-rank (top-2 EVR %.0f%%) AND distortion transfers "
               "out-of-sample (x%.1f) => sigma_hat is a systematic closure-compensating surrogate"
               % (tag, 100 * a1["top2_cum_evr"], a2["improvement_ratio"])
               if a1["top2_cum_evr"] > 0.5 and a2["systematic_transferable"]
               else "NOT supported [%s]: spectrum diffuse or distortion non-transferable" % tag)
    if tag == "vs_true":
        verdict += "  (CAVEAT: no grounded baseline -- conflates 'never grounded' with SLE compensation)"
    out["primary_analysis"] = tag
    out["verdict"] = verdict

    # ---- figure: dominant deviation mode + mean shift on the sigma-grid ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        # the journal's graphics specification; see scripts/analysis/acs_figure_style.py
        import sys as _s; _s.path.insert(0, str(Path(__file__).resolve().parent))
        from acs_figure_style import apply as _acs
        _style = Path.home() / ".claude/skills/repo-to-paper/assets/softpastel.mplstyle"
        if _style.exists():
            plt.style.use(str(_style))
        # AFTER style.use, NOT BEFORE: the shared style file resets rcParams wholesale, so a
        # typeface set earlier is silently discarded. The specification has to be applied last,
        # and outside the `if` so it applies whether or not that optional style file is present.
        _acs()
        SALMON, BLUE, PURPLE = "#E8A98C", "#8FB3DA", "#B7A5DC"   # shared soft-pastel palette
        fig, ax = plt.subplots(1, 2, figsize=(9.5, 4.0))
        ax[0].plot(SIGMA_GRID, r.mean(0), color=SALMON, lw=2.2, label="mean deviation")
        top_mode = Vt[0] * np.sign(Vt[0][np.argmax(np.abs(Vt[0]))])
        ax[0].plot(SIGMA_GRID, top_mode * S[0] / np.sqrt(len(keep)), color=BLUE, lw=2.2,
                   ls="--", label=f"top PC (EVR {ev[0]:.0%})")
        ax[0].axvline(0, color="0.8", lw=0.7, zorder=0); ax[0].axhline(0, color="0.8", lw=0.7, zorder=0)
        ax[0].set_xlabel(r"$\sigma$  (e/Å$^2$)"); ax[0].set_ylabel(r"$\hat\sigma_{\mathrm{SLE}}-\hat\sigma_{\mathrm{grounded}}$  (shape)")
        ax[0].set_title("Drift of the learned profile under solubility fine-tuning")
        ax[0].legend(fontsize=8, frameon=False)
        ax[0].spines[["top", "right"]].set_visible(False)
        ax[1].bar(range(1, 6), ev[:5], color=PURPLE, edgecolor="white", linewidth=0.8)
        ax[1].set_xlabel("principal component"); ax[1].set_ylabel("explained variance ratio")
        ax[1].set_title(f"Drift spectrum (top-2 = {a1['top2_cum_evr']:.1%})")
        ax[1].spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        args.fig_dir.mkdir(parents=True, exist_ok=True)
        for ext in ("pdf", "png"):
            fig.savefig(args.fig_dir / f"fig_compensation_surrogate.{ext}", dpi=150)
        out["figure"] = str(args.fig_dir / "fig_compensation_surrogate.pdf")
        plt.close(fig)
    except Exception as e:  # noqa: BLE001
        out["figure_error"] = str(e)

    out["checkpoint"] = str(args.checkpoint)
    out["baseline_checkpoint"] = str(args.baseline_checkpoint) if args.baseline_checkpoint else None
    out["excluded_smiles_requested"] = list(args.exclude_smiles or [])
    out["excluded_smiles_dropped"] = dropped
    out["n_matched"] = len(keep)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2))

    print(f"\n[primary analysis: {tag}]")
    if "isolation" in out:
        print(f"grounding quality: sigma_hat_grounded vs true rel-dev = "
              f"{out['isolation']['grounded_vs_true_rel_deviation']:.3f} (small => grounding worked)")
    print(f"A1  rel deviation = {a1['rel_deviation']:.3f}")
    print(f"A1  PCA top-1 EVR = {a1['top1_evr']:.2f}, top-2 cum = {a1['top2_cum_evr']:.2f}  "
          f"({'low-rank=systematic' if a1['top2_cum_evr']>0.5 else 'diffuse=noise-like'})")
    print(f"A2  out-of-sample  MSE(D) = {a2['oos_mse_distortion_D']:.5f}  vs  "
          f"MSE(identity) = {a2['oos_mse_identity']:.5f}  (x{a2['improvement_ratio']:.2f})  "
          f"-> transferable={a2['systematic_transferable']}")
    print(f"\nVERDICT: {verdict}")
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
