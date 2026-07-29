#!/usr/bin/env python3
"""Re-render the drift figure (paper Fig.~\\ref{fig:surrogate}) with corrected labels.

The plotted quantity is the drift of the learned sigma-profile under solubility fine-tuning,
i.e. sigma_hat(SLE) - sigma_hat(grounded) on the same model -- NOT sigma_hat minus the external
VT-2005 reference. The original panels were labelled with the latter and titled with an inference
(``low-rank => systematic'') that sec:surrogate declines to license against the shrinkage
alternative; both are corrected here.

Data. The model checkpoints of the companion isolation run were not retained, so the two curves
are read from results/compensation/drift_mode_curves.csv, recovered losslessly from the vector
paths of the previously deposited figure and verified against the 51-bin sigma grid to 1.6e-10 and
against the sum-to-zero constraint a difference of two normalised shapes must satisfy. The spectrum
is read from results/compensation/isolation_gpu.json (the same run).

    MPLBACKEND=Agg python scripts/analysis/make_surrogate_figure.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CURVES = ROOT / "results" / "compensation" / "drift_mode_curves.csv"
SPEC = ROOT / "results" / "compensation" / "isolation_gpu.json"
OUT = ROOT / "paper" / "figs" / "fig_compensation_surrogate"
# The drift spectrum was demoted out of the main-text float (relocation move 19, 2026-07-28): it is
# the panel the caption itself declines to draw an inference from, and it is read against the
# spectral null in App. E.  It is written as its own single-column figure for that appendix.
OUT_SPEC = ROOT / "paper" / "figs" / "fig_drift_spectrum"
SALMON, BLUE, PURPLE = "#E8A98C", "#8FB3DA", "#B7A5DC"


def main() -> int:
    df = pd.read_csv(CURVES)
    iso = json.load(open(SPEC))["isolation"]["A1"]
    ev = np.array(iso["pca_evr_top5"])

    # A principal component is defined only up to sign. Fix it, once and explicitly, so the mode
    # is drawn in the same direction as the mean drift it accompanies; without this the deposited
    # vector path happens to carry the opposite sign and the panel reads as the mirror image of
    # what sec:surrogate says the dominant mode does.
    top_pc = df["top_pc_scaled"].to_numpy()
    if float(top_pc @ df["mean_drift"].to_numpy()) < 0:
        top_pc = -top_pc

    # Canvas is sized so that each figure prints at ~1:1 inside \columnwidth (240.1 pt) in the
    # two-column layout; type set here in points is therefore type on the page.
    #
    # axes.labelsize is 9 and not 8 because the y-label carries mathtext SUBSCRIPTS
    # (fine-tuned, grounded) and the x-label a superscript, and matplotlib shrinks those by
    # 0.7.  At labelsize 8 they set at 5.6 pt, and the ~1.02 scale to \columnwidth leaves them
    # at 5.71 pt on the page -- under the 6 pt floor every other figure clears.  9 x 0.7 x 1.02
    # is 6.4 pt.  Raise the other sizes with it whenever this one moves, or the label outgrows
    # the tick labels it sits beside.
    plt.rcParams.update({"font.family": "serif", "savefig.dpi": 300,
                         "savefig.bbox": "tight", "figure.facecolor": "white",
                         "font.size": 8.5, "axes.labelsize": 9, "axes.titlesize": 9,
                         "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5})
    fig, ax0 = plt.subplots(1, 1, figsize=(3.34, 2.7))
    ax0.plot(df["sigma"], df["mean_drift"], color=SALMON, lw=1.8, label="mean drift")
    ax0.plot(df["sigma"], top_pc, color=BLUE, lw=1.8, ls="--",
             label=f"top PC (EVR {ev[0]:.0%}, sign aligned)")
    ax0.axvline(0, color="0.8", lw=0.7, zorder=0)
    ax0.axhline(0, color="0.8", lw=0.7, zorder=0)
    ax0.set_xlabel(r"$\sigma$  (e/$\AA^2$)")
    ax0.set_ylabel(r"$\hat\sigma_{\mathrm{fine\!-\!tuned}}-\hat\sigma_{\mathrm{grounded}}$"
                   "\n(profile shape, same model)")
    ax0.set_title("Drift under solubility fine-tuning")
    # The legend is frameon=False, so a curve that runs under it reads as a strikethrough
    # rather than as an overlap.  loc="best" has no free corner here: the mean drift peaks
    # at the upper left and troughs at the lower centre, and the second entry is wide enough
    # to reach either.  Open a band above the data instead and put the legend in it, so the
    # placement does not depend on the label lengths.
    lo = float(min(df["mean_drift"].min(), top_pc.min()))
    hi = float(max(df["mean_drift"].max(), top_pc.max()))
    span = hi - lo
    ax0.set_ylim(lo - 0.06 * span, hi + 0.40 * span)
    ax0.legend(frameon=False, loc="upper left", borderaxespad=0.2)
    ax0.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}.{ext}")

    figs, ax1 = plt.subplots(1, 1, figsize=(3.34, 2.7))
    ax1.bar(range(1, 6), ev, color=PURPLE, edgecolor="white", linewidth=0.8)
    ax1.set_xlabel("principal component")
    ax1.set_ylabel("explained variance ratio")
    ax1.set_title(f"Drift spectrum (top-2 = {iso['top2_cum_evr']:.1%}, one run)")
    ax1.spines[["top", "right"]].set_visible(False)
    figs.tight_layout()
    for ext in ("pdf", "png"):
        figs.savefig(f"{OUT_SPEC}.{ext}")
    print(f"wrote {OUT}.pdf / .png and {OUT_SPEC}.pdf / .png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
