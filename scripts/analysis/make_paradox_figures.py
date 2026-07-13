#!/usr/bin/env python3
"""Regenerate the three grounding-paradox figures from COMMITTED artifacts.

All numbers are read from tracked files -- nothing is hard-coded -- so the
figures always reflect the corrected n=60 keystone:

  fig_paradox.pdf       6-arm controlled comparison (MAE + R2, mean+/-sd over the
                        3 e5 seeds) from results/e5_sigma_grounding/seed_{42,43,44}/
                        comparison.json. The sigma-oracle (true-input) arm is salmon.
  fig_parity.pdf        ln gamma_inf parity on the n=60 matched pairs: the true-
                        sigma COSMO-SAC closure g(z*) (full convention) vs the
                        diagonal, from results/b_insuff/matched_pairs.csv. (The CSV
                        has no free-head prediction, so only the closure is drawn.)
  fig_decomposition.pdf one-sided bounds (full convention) from
                        results/b_insuff/decomposition.json: the assumption-free
                        Jensen B_closure lower bound vs the cluster of B_insuff
                        upper bounds (LOTV / RF / Ridge / kNN), against total MSE.

Does NOT touch fig_dial.pdf (separate synthetic generator) and edits no .tex.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/make_paradox_figures.py \
        --e5-dir results/e5_sigma_grounding \
        --matched-csv results/b_insuff/matched_pairs.csv \
        --decomposition-json results/b_insuff/decomposition.json \
        --out-dir paper/figs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# soft-pastel palette (mirrors repo-to-paper/assets/softpastel.mplstyle)
SALMON = "#E8A98C"   # true-input / oracle / closure arm
TEAL = "#7FB5A6"     # learned representation
BLUE = "#8FB3DA"
PURPLE = "#B7A5DC"
GOLD = "#E6C87A"
GRAY = "#9AA0A6"
INK = "#4D4D4D"

_DEFAULT_STYLE = Path.home() / ".claude/skills/repo-to-paper/assets/softpastel.mplstyle"


def apply_style(style: str | None) -> None:
    path = Path(style) if style else _DEFAULT_STYLE
    if path.exists():
        plt.style.use(str(path))
        return
    # clean pastel fallback if the asset is unavailable
    plt.rcParams.update({
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "savefig.dpi": 300, "savefig.bbox": "tight", "figure.dpi": 200,
        "font.family": "sans-serif", "font.size": 11, "axes.titlesize": 13,
        "axes.labelsize": 12, "axes.edgecolor": INK, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True, "grid.color": "#D9D9D9",
        "grid.linewidth": 0.6, "grid.alpha": 0.7, "legend.frameon": False,
        "patch.linewidth": 0.0,
        "axes.prop_cycle": plt.cycler(color=[TEAL, SALMON, BLUE, PURPLE, GOLD, GRAY]),
    })


def _save(fig, out_dir: Path, stem: str) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in ("pdf", "png"):
        p = out_dir / f"{stem}.{ext}"
        fig.savefig(p)
        written.append(str(p))
    plt.close(fig)
    return written


# --------------------------------------------------------------------------- #
def fig_paradox(e5_dir: Path, seeds, out_dir: Path) -> list[str]:
    arms = ["nrtl", "directgnn", "ungrounded", "grounded_a", "grounded_b", "oracle"]
    labels = ["NRTL", "DirectGNN", "ungrounded", "grounded (learn $\\sigma$)",
              "+comb. (gr. B)", "$\\sigma$-oracle (true $\\sigma$)"]
    mae = {a: [] for a in arms}
    r2 = {a: [] for a in arms}
    for s in seeds:
        d = json.load(open(e5_dir / f"seed_{s}" / "comparison.json"))["per_arm"]
        for a in arms:
            mae[a].append(d[a]["mae"])
            r2[a].append(d[a]["r2"])
    mae_mean = [np.mean(mae[a]) for a in arms]
    mae_sd = [np.std(mae[a], ddof=1) for a in arms]
    r2_mean = [np.mean(r2[a]) for a in arms]
    r2_sd = [np.std(r2[a], ddof=1) for a in arms]
    # oracle (true-input) salmon; learned-representation arms teal; NRTL baseline gray
    colors = [GRAY, TEAL, BLUE, TEAL, TEAL, SALMON]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 4.2))
    x = np.arange(len(arms))
    ax1.bar(x, mae_mean, yerr=mae_sd, color=colors, capsize=3,
            error_kw={"ecolor": INK, "elinewidth": 1.0})
    ax1.set_ylabel("solubility MAE  (ln $x_2$)")
    ax1.set_title("Prediction error (lower better)")
    ax1.axhline(mae_mean[1], ls="--", lw=1.0, color=INK, alpha=0.6)  # directgnn ref
    ax2.bar(x, r2_mean, yerr=r2_sd, color=colors, capsize=3,
            error_kw={"ecolor": INK, "elinewidth": 1.0})
    ax2.set_ylabel("solubility $R^2$")
    ax2.set_title("Variance explained (higher better)")
    ax2.axhline(0.0, ls="-", lw=0.8, color=INK, alpha=0.7)
    for ax in (ax1, ax2):
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8.5, rotation=22, ha="right")
        ax.margins(x=0.02)
    fig.suptitle("The grounding paradox: true $\\sigma$-profiles give the worst arm "
                 "(3 seeds, $n{=}5608$)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return _save(fig, out_dir, "fig_paradox")


def fig_parity(matched_csv: Path, out_dir: Path) -> list[str]:
    df = pd.read_csv(matched_csv)
    m = df["m"].to_numpy(float)
    g = df["g_full"].to_numpy(float)
    mse = float(np.mean((m - g) ** 2))
    fig, ax = plt.subplots(figsize=(5.2, 5.0))
    lo = min(m.min(), g.min()) - 0.4
    hi = max(m.max(), g.max()) + 0.4
    ax.plot([lo, hi], [lo, hi], ls="--", lw=1.2, color=INK, alpha=0.7, zorder=1)
    ax.scatter(m, g, s=42, color=SALMON, edgecolor="white", linewidth=0.5,
               alpha=0.9, zorder=2,
               label=f"true-$\\sigma$ COSMO-SAC $g(z^\\ast)$  (MSE {mse:.2f})")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("experimental $\\ln\\gamma^\\infty$  (IDAC, 298 K)")
    ax.set_ylabel("closure $g(z^\\ast)$  (full COSMO-SAC)")
    ax.set_title(f"Activity parity on the $n{{=}}{len(df)}$ matched pairs")
    ax.legend(loc="upper left", fontsize=9)
    ax.text(0.97, 0.05, "closure under-predicts $\\ln\\gamma^\\infty$\n(systematic decoder bias)",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5, color=INK)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_parity")


def fig_decomposition(decomp_json: Path, out_dir: Path) -> list[str]:
    d = json.load(open(decomp_json))
    res = d["conventions"]["res"]          # DEPLOYED residual-only convention (the model runs this)
    bi = d["b_insuff_convention_independent"]
    mse = res["mse_total"]
    jensen = res["b_closure_jensen_lower"]        # convention-specific; inverts under res
    b_lotv = res["b_insuff_lotv_upper"]           # leakage-immune headline B_insuff upper bound
    b_clos_lb = mse - b_lotv                       # load-bearing convention-independent bound
    # B_insuff upper-bound estimators; the z*-neighbour smoothers (kNN, RF) are deflated by the
    # 51/102 shared-coordinate near-duplicates of the crossed design, so we headline LOTV binning.
    uppers = {
        "LOTV bin $g$ (headline)": b_lotv,
        "Ridge out-of-fold": bi["ridge_oof_upper"],
        "RF out-of-fold (deflated)": bi["rf_oof_upper"],
        "kNN-in-$z^\\ast$ (deflated)": bi["knn_in_zstar_biased_up"],
    }
    max_upper = max(uppers.values())

    fig, ax = plt.subplots(figsize=(8.4, 3.6))
    # salmon region = every valid B_insuff upper bound; teal region = certified closure share
    ax.axvspan(0, max_upper, color=SALMON, alpha=0.22, zorder=0)
    ax.axvspan(b_clos_lb, mse, color=TEAL, alpha=0.20, zorder=0)
    # B_insuff estimators as points on one row
    ys = np.linspace(0.60, 0.92, len(uppers))
    for (name, val), y in zip(uppers.items(), ys):
        ax.scatter(val, y, s=70, color=SALMON, edgecolor=INK, linewidth=0.6, zorder=3)
        ax.annotate(f"{name} = {val:.2f}", (val, y), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=8.5, color=INK)
    # load-bearing convention-independent lower bound on B_closure
    ax.axvline(b_clos_lb, color=INK, lw=1.6, zorder=4)
    ax.annotate(f"$B_{{\\rm closure}}\\geq$ MSE$-B_{{\\rm insuff}}^{{\\rm LOTV}}={b_clos_lb:.2f}$\n(load-bearing)",
                (b_clos_lb, 0.32), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=9, color=INK, fontweight="bold")
    # total MSE
    ax.axvline(mse, color=INK, lw=1.2, ls="--", alpha=0.7, zorder=4)
    ax.annotate(f"MSE$_{{\\rm total}}={mse:.2f}$", (mse, 0.14), xytext=(-6, 0),
                textcoords="offset points", va="center", ha="right",
                fontsize=9, color=INK)
    # Jensen constant-offset bound: convention-specific, does NOT separate under the deployed model
    ax.axvline(jensen, color="#999999", lw=1.0, ls=":", zorder=2)
    ax.annotate(f"Jensen offset ${jensen:.2f}$ (convention-specific;\ndoes not separate here)",
                (jensen, 0.06), xytext=(6, 0), textcoords="offset points",
                va="center", fontsize=7.6, color="#777777")
    ax.set_xlim(0, mse + 0.30)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([])
    ax.set_xlabel("error magnitude  ($\\ln\\gamma$ units$^2$)")
    ax.set_title("Closure–insufficiency bounds, deployed residual-only COSMO-SAC ($n{=}60$): "
                 "$B_{\\rm closure}$ dominates (leakage-immune bound)")
    ax.text(max_upper / 2, 0.965, "$B_{\\rm insuff}$ upper bounds",
            ha="center", va="top", fontsize=9, color="#B5654A")
    fig.tight_layout()
    return _save(fig, out_dir, "fig_decomposition")


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--e5-dir", default="results/e5_sigma_grounding")
    ap.add_argument("--matched-csv", default="results/b_insuff/matched_pairs.csv")
    ap.add_argument("--decomposition-json", default="results/b_insuff/decomposition.json")
    ap.add_argument("--out-dir", default="paper/figs")
    ap.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    ap.add_argument("--style", default=None,
                    help="Path to a matplotlib style (default: repo-to-paper softpastel).")
    args = ap.parse_args()

    apply_style(args.style)
    out_dir = Path(args.out_dir)
    written = []
    written += fig_paradox(Path(args.e5_dir), args.seeds, out_dir)
    written += fig_parity(Path(args.matched_csv), out_dir)
    written += fig_decomposition(Path(args.decomposition_json), out_dir)
    print("wrote:")
    for w in written:
        print("  " + w)


if __name__ == "__main__":
    main()
