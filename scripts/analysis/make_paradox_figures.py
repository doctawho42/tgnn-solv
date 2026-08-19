#!/usr/bin/env python3
"""Regenerate the three grounding-paradox figures from COMMITTED artifacts.

All numbers are read from tracked files -- nothing is hard-coded -- so the
figures always reflect the corrected n=60 keystone:

  fig_paradox.pdf       6-arm controlled comparison (MAE + R2, mean+/-sd over the
                        3 e5 seeds) from results/e5_sigma_grounding/seed_{42,43,44}/
                        comparison.json. The sigma-oracle (reference-input) arm is salmon.
  fig_parity.pdf        ln gamma_inf parity on the n=60 matched pairs: the reference-
                        sigma COSMO-SAC closure g(z*) (full convention) vs the
                        diagonal, from results/b_insuff/matched_pairs.csv. (The CSV
                        has no free-head prediction, so only the closure is drawn.)
  fig_bounds_inventory.pdf
                        RETIRED AS A MANUSCRIPT FIGURE, 2026-08-02, and renamed off the
                        fig_decomposition stem so a rerun cannot overwrite what took its
                        place.  The aggregate it draws does not survive the manuscript's
                        two robustness operations applied together and is carried by one
                        publication; the figure the SI now sets at that stem is the
                        stratified map, scripts/analysis/make_stratified_map_figure.py.
                        What it drew: one-sided bounds (deployed residual-only convention) from
                        results/b_insuff/decomposition.json: the load-bearing,
                        leakage-immune LOTV B_closure lower bound vs the cluster of
                        B_insuff upper bounds (LOTV / RF / Ridge / kNN), against total
                        MSE. (The convention-specific Jensen constant-offset bound,
                        which inverts under this convention, is reported in the SI.)
                        One inclusion rule governs BOTH panels -- see the docstrings of
                        _lotv_coarse_bounds and _decomposition_panels. It keeps every
                        bound that threatens the ordering, including the broad IDAC set's
                        4-bin LOTV cell (0.948 against a 0.951 threshold, the tightest
                        margin anywhere on that set) and the corner's 3- and 4-bin cells,
                        which sit ABOVE the corner's threshold. Bin cells for the broad
                        set are read from convention_audit.json, whose 56-cell grid is the
                        only one on disk that contains the 4-bin cell.
                        Colour convention for the two error terms is shared with
                        fig_overview panel (b) (make_overview_figure.py), which shows the
                        same split: SALMON = model misspecification, TEAL = input
                        insufficiency. Do not invert one without the other.

                        2026-07-28: the bounds are DRAWN BUT NO LONGER NAMED in the
                        figure -- ten labelled rows per panel could not be read at the
                        printed column width. Every bound the rule keeps is still there,
                        one mark each; its name and value belong in a Supporting
                        Information table, and the caption must point at that table.
                        `--dump-bounds` prints exactly the inventory the figure plots, so
                        the table cannot drift away from the marks.

Does NOT touch fig_dial.pdf (separate synthetic generator) and edits no .tex.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/make_paradox_figures.py \
        --e5-dir results/e5_sigma_grounding \
        --matched-csv results/b_insuff/matched_pairs.csv \
        --decomposition-json results/b_insuff/decomposition.json \
        --out-dir paper/figs

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/make_paradox_figures.py --dump-bounds
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
HURT = "#B5654A"     # a bound that crosses the separation threshold

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
    """Six-arm controlled comparison plus the two co-adaptation controls.

    2026-07-28 declutter. Removed from the axes and moved to the caption: the two
    multi-line annotation blocks with arrows crossing the bars (the +0.41 eval-only
    substitution cost and the +0.18 co-adapted cost against seed 42's own 1.803), the
    title's parenthetical legend (solid = 3 seeds n=5608, hatched = seed 42 only), and
    the two "not computed" notes in the right panel. The long rotated tick phrases became
    scannable names -- "ref. sigma (eval)" and "ref. sigma (train)" for what used to read
    "sigma-oracle, eval-only" and "reference sigma injected at training (co-adapted)".
    The two arms whose R2 is not on disk keep their slot in the right panel, shaded and
    empty, so the reader sees a missing measurement rather than a zero.
    """
    arms = ["nrtl", "directgnn", "ungrounded", "grounded_a", "grounded_b", "oracle"]
    labels = ["NRTL", "DirectGNN", "ungrounded", "grounded", "grounded +comb.",
              "ref. $\\sigma$ (eval)"]
    mae = {a: [] for a in arms}
    r2 = {a: [] for a in arms}
    for s in seeds:
        d = json.load(open(e5_dir / f"seed_{s}" / "comparison.json"))["per_arm"]
        for a in arms:
            mae[a].append(d[a]["mae"])
            r2[a].append(d[a]["r2"])
    # ddof=0.  The SI fixes a single convention for every +/- in the paper -- a POPULATION
    # standard deviation over the three seeds -- and prints ddof=0 values for these same arms in
    # tab:si-arms.  ddof=1 here would draw bars sqrt(3/2) = 22% longer than the table beside them.
    mae_mean = [np.mean(mae[a]) for a in arms]
    mae_sd = [np.std(mae[a], ddof=0) for a in arms]
    r2_mean = [np.mean(r2[a]) for a in arms]
    r2_sd = [np.std(r2[a], ddof=0) for a in arms]
    n_seeded = len(arms)  # arms appended below are single-seed and get no error bar at all

    # THE TWO CO-ADAPTATION CONTROLS ARE NO LONGER DRAWN, 2026-08-20 (supervisory ruling).
    # Each was one seed against a comparator that gives two readings, which is an illustration and
    # not a result; drawn beside six five-seed arms they read as the same kind of evidence, which
    # is the reading the ruling removes. They keep their numbers in the Supporting Information's
    # arms table, marked as single-seed. _seed42_controls() stays: that table is built from it.
    # oracle (true-input) salmon; learned-representation arms teal; NRTL baseline gray
    colors = [GRAY, TEAL, BLUE, TEAL, TEAL, SALMON]
    hatch = [None] * len(labels)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.4, 2.95))
    x = np.arange(len(labels))
    # Error bars are drawn as a SEPARATE artist over the seeded arms only.  Passing yerr=0 for the
    # single-seed arms (as this figure once did) draws a zero-length bar whose caps are visible at
    # the bar top -- a mark the caption says is not there.  bar(..., yerr=None) draws no errorbar
    # artist at all, so there is nothing to hide later.
    b1 = ax1.bar(x, mae_mean, color=colors)
    ax1.errorbar(x[:n_seeded], mae_mean[:n_seeded], yerr=mae_sd, fmt="none",
                 ecolor=INK, elinewidth=0.9, capsize=2.5)
    for bar, h in zip(b1, hatch):
        if h:
            bar.set_hatch(h)
            bar.set_edgecolor(INK)
            bar.set_linewidth(0.7)
    # 9.0 pt, not 8.6: the "2" is a mathtext subscript set at 0.7x the base, and this
    # figure prints at 0.98x, so an 8.6 pt base puts it on the page at 5.9 pt.
    ax1.set_ylabel("solubility MAE  (ln $x_2$)", fontsize=9.0)
    ax1.set_title("Prediction error (lower better)", fontsize=9.4)
    ax1.axhline(mae_mean[1], ls="--", lw=1.0, color=INK, alpha=0.6)  # directgnn ref
    ax1.set_ylim(0, max(mae_mean) * 1.12)
    b2 = ax2.bar(x, np.nan_to_num(r2_mean, nan=0.0), color=colors)
    ax2.errorbar(x[:n_seeded], r2_mean[:n_seeded], yerr=r2_sd, fmt="none",
                 ecolor=INK, elinewidth=0.9, capsize=2.5)
    for bar, h, v in zip(b2, hatch, r2_mean):
        if h:
            bar.set_hatch(h)
            bar.set_edgecolor(INK)
            bar.set_linewidth(0.7)
        if not np.isfinite(v):
            bar.set_alpha(0.0)
    # A missing measurement is drawn, not written: the slot stays, shaded and empty, so it
    # cannot be read as R2 = 0.  What the shading means is the caption's business.
    for i, v in enumerate(r2_mean):
        if not np.isfinite(v):
            ax2.axvspan(i - 0.42, i + 0.42, color=GRAY, alpha=0.16, lw=0, zorder=0)
    ax2.set_ylabel("solubility $R^2$", fontsize=9.0)
    ax2.set_title("Variance explained (higher better)", fontsize=9.4)
    ax2.axhline(0.0, ls="-", lw=0.8, color=INK, alpha=0.7)
    for ax in (ax1, ax2):
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7.6, rotation=26, ha="right")
        ax.tick_params(axis="y", labelsize=8.0)
        ax.margins(x=0.02)
    # "reference", not "true": the VT-2005 profiles are quantum chemistry, not experiment
    # (main text, "The reference is itself imperfect"), and SI Fig. fig:parity's caption
    # already calls this arm the reference-sigma closure.
    fig.suptitle("The grounding paradox: reference $\\sigma$-profiles give the worst arm",
                 fontsize=10.6)
    fig.tight_layout(rect=(0, 0, 1, 0.972))
    return _save(fig, out_dir, "fig_paradox")


def _seed42_controls(e5_dir: Path) -> dict:
    """MAE of the two single-seed oracle-application controls on the same n=5608 lock.

    Recomputed from the released per-row prediction files rather than hard-coded, so the
    figure and the SI paragraph cannot drift apart.
    """
    p = e5_dir / "seed_42"
    arms = ["nrtl", "directgnn", "ungrounded", "grounded_a", "grounded_b", "oracle"]
    frames = {a: pd.read_csv(p / f"{a}_predictions.csv") for a in arms}
    mask = None
    for d in frames.values():
        ok = (d["has_solubility"].astype(bool) & np.isfinite(d["ln_x2_pred"])
              & np.isfinite(d["ln_x2_true"]))
        mask = ok if mask is None else (mask & ok)
    out = {"lock_n": int(mask.sum()),
           "grounded_a": float(np.mean(np.abs(frames["grounded_a"]["ln_x2_pred"]
                                              - frames["grounded_a"]["ln_x2_true"])[mask]))}
    for f, lab in (("grounded_a_truetrain_predictions.csv", "truetrain"),
                   ("channel_swap_predictions.csv", "channel_swap")):
        d = pd.read_csv(p / f)
        out[lab] = float(np.mean(np.abs(d["ln_x2_pred"] - d["ln_x2_true"])[mask]))
    return out


def fig_parity(matched_csv: Path, out_dir: Path) -> list[str]:
    df = pd.read_csv(matched_csv)
    m = df["m"].to_numpy(float)
    g = df["g_full"].to_numpy(float)
    mse = float(np.mean((m - g) ** 2))
    # Canvas = the width this figure is SET at (\columnwidth, 240.7 pt = 3.34 in), so it
    # prints at 1:1.  It used to be a 4.55 in canvas set at 0.72\columnwidth -- a 0.53x
    # reduction that put the tick labels on the page at 5.3 pt and the legend at 4.8 pt.
    fig, ax = plt.subplots(figsize=(3.80, 3.72))
    lo = min(m.min(), g.min()) - 0.4
    hi = max(m.max(), g.max()) + 0.4
    ax.plot([lo, hi], [lo, hi], ls="--", lw=1.2, color=INK, alpha=0.7, zorder=1)
    ax.scatter(m, g, s=20, color=SALMON, edgecolor="white", linewidth=0.4,
               alpha=0.9, zorder=2,
               label=f"reference-$\\sigma$ COSMO-SAC $g(z^\\ast)$\n(MSE {mse:.2f}, full convention)")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("experimental $\\ln\\gamma^\\infty$  (IDAC, 298 K)", fontsize=8.2)
    ax.set_ylabel("closure $g(z^\\ast)$  (full COSMO-SAC)", fontsize=8.2)
    ax.set_title(f"Activity parity on the $n{{=}}{len(df)}$ matched pairs", fontsize=8.6)
    ax.tick_params(labelsize=7.6)
    ax.legend(loc="upper left", fontsize=7.0)
    ax.text(0.97, 0.05, "closure under-predicts $\\ln\\gamma^\\infty$\n(systematic decoder bias)",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7.0, color=INK)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_parity")


def _lotv_res_cells(cells: list[dict]) -> list[dict]:
    """Normalise a LOTV grid to {n_bins, b_insuff_up} for the DEPLOYED res/unbiased cells.

    The two grids on disk disagree on key names (representative_decomposition.json and
    estimator_grid.json use n_bins/within_bin_variance; convention_audit.json uses
    bins/variance), so normalise before applying the shared inclusion rule.
    """
    out = []
    for c in cells:
        nb = c.get("n_bins", c.get("bins"))
        var = c.get("within_bin_variance", c.get("variance"))
        if c.get("convention") == "res" and var == "Bessel" and nb is not None:
            out.append({"n_bins": int(nb), "b_insuff_up": float(c["b_insuff_up"])})
    return sorted(out, key=lambda c: c["n_bins"])


def _lotv_coarse_bounds(cells: list[dict], mse: float, headline_bins: int = 8) -> list[dict]:
    """The bin-count cells the shared inclusion rule keeps, besides the headline.

    ONE rule, applied to both panels: within the deployed residual-only convention under
    the unbiased within-bin variance, keep (a) the coarsest reported cell, (b) the LEAST
    FAVOURABLE (largest) reported cell, and (c) every reported cell whose bound exceeds
    that panel's separation threshold MSE/2.  (a) and (b) coincide on the corner and do
    NOT on the representative set, where the coarsest cell (3 bins, 0.90) is the weaker
    threat and the largest (4 bins, 0.948 against a threshold of 0.951) is the strongest;
    an earlier version of this figure drew only the former and labelled it "coarsest".
    """
    res = _lotv_res_cells(cells)
    if not res:
        return []
    keep: dict[int, list] = {}

    def mark(c, tag):
        entry = keep.setdefault(c["n_bins"], [c, []])
        if tag and tag not in entry[1]:
            entry[1].append(tag)

    mark(min(res, key=lambda c: c["n_bins"]), "coarsest")
    mark(max(res, key=lambda c: c["b_insuff_up"]), "least favourable")
    for c in res:
        if c["b_insuff_up"] > mse / 2:
            mark(c, None)
    keep.pop(headline_bins, None)           # already drawn as the headline row
    out = []
    for nb in sorted(keep):
        c, tags = keep[nb]
        suffix = f" ({', '.join(tags)})" if tags else ""
        out.append({"name": f"LOTV {nb} bins{suffix}", "value": c["b_insuff_up"],
                    "family": "lotv"})
    return out


def _decomposition_panels(decomp_json: Path,
                          rep_json: Path | None = None, grid_json: Path | None = None,
                          keystone_json: Path | None = None,
                          robustness_json: Path | None = None) -> list[dict]:
    """The two panels' contents: total MSE, headline bound, and the full bound inventory.

    Separated from the drawing so the same inventory that the figure plots can be dumped
    verbatim for the Supporting Information table (`--dump-bounds`); the figure and the
    table cannot then disagree about what was included.

    ONE inclusion rule in both panels, and it is stated in `_lotv_coarse_bounds`: the
    headline LOTV cell (8 equal-count bins, UNBIASED/Bessel within-bin variance), its
    maximum-likelihood variant, the same cell under the other combinatorial convention,
    the coarsest / least favourable / above-threshold cells of that set's reported bin
    grid, and every out-of-fold estimator that set's audit artifact records, in every fold
    design it records -- random-fold AND molecule-blocked, never one without the other.

    The LOTV part of that rule is SELECTIVE and is meant to be: the reported bin grids hold
    72 cells on the corner and 56 on the broad set, and drawing all of them would bury the
    threshold in a rug.  What is selected is the worst case -- coarsest, least
    favourable, and everything above the threshold -- so no cell that threatens the ordering
    can be left out.  The estimator part is EXHAUSTIVE, and mechanically so: each panel
    reads its artifact's estimator keys against a name table and raises on anything the
    table does not name, so a new estimator stops the figure instead of being dropped, and
    no value has a numeric fallback that could stand in for a key that went missing.  Both
    guarantees have to be said this way round; the captions say them this way round too.

    Each bound carries a `family`: "lotv" for the variance-decomposition bounds, which fit
    no model to the data, and "fit" for the out-of-fold regression estimators, whose value
    depends on the fold design.  That is the only distinction the figure draws by marker;
    the names live in the SI table.
    """
    d = json.load(open(decomp_json))
    # NOTE: `d["b_insuff_convention_independent"]` also carries corner ridge/RF/kNN values and
    # used to be the source of those three marks.  It is a standalone fit, not the audit the
    # inclusion rule names, and its forest disagreed with the audit (0.565 against 0.621) while
    # its ridge and kNN agreed -- so the panel drew one estimator from a third file.  The corner's
    # fitted marks now come from the audit artifacts only; the disagreement is reported in the SI.
    grid = json.load(open(grid_json))["grid"] if grid_json and Path(grid_json).exists() else []

    def cell(conv, nb, var):
        for c in grid:
            if (c["convention"], c["n_bins"], c["within_bin_variance"]) == (conv, nb, var):
                return c
        return None

    corner_res = d["conventions"]["res"]
    corner_mse = corner_res["mse_total"]

    def required_cell(conv, nb, var):
        """A grid cell the inventory names, with no numeric fallback.

        This used to read ``cell(...) or <literal>``: when the grid moved, the figure went
        on drawing a number no artifact contained.  A missing cell is now a stop.
        """
        c = cell(conv, nb, var)
        if c is None:
            raise KeyError(f"the estimator grid has no {nb}-bin {var}-variance cell under the "
                           f"{conv} convention; the inventory names it, so it cannot be drawn "
                           f"from a fallback")
        return float(c["b_insuff_up"])

    corner_headline = required_cell("res", 8, "Bessel")

    # ---- the corner's out-of-fold estimators, on the SAME mechanical rule as the broad
    # panel below: a name table covering the artifact, a raise for anything it does not
    # name, and no numeric fallback anywhere.  The corner list used to be hard-coded with
    # literal defaults, so a new estimator in the artifact was dropped in silence and a
    # deleted one was replaced by a literal -- the two failures the SI table's completeness
    # sentence says cannot happen.  They now cannot.
    ks = json.load(open(keystone_json)) if keystone_json and Path(keystone_json).exists() else {}
    dpe = ks.get("distinct_pair_estimators", {})
    rb_json = json.load(open(robustness_json)) if robustness_json and Path(robustness_json).exists() else {}

    corner_oof_names = {
        "knn_raw": "$k$NN-in-$\\zstar$ (convention-independent; least conservative)",
        "knn_distinct_solute": "$k$NN, neighbour from a distinct solute",
        "knn_distinct_solvent": "$k$NN, neighbour from a distinct solvent",
        "knn_distinct_pair": "$k$NN, neighbour from a distinct pair",
        "rf_oof_random5fold": "RF out-of-fold, random folds (deflated)",
        "ridge_oof_random5fold": "ridge out-of-fold, random folds",
        "rf_oof_blocked": "RF out-of-fold, folds blocked on both molecules",
        "ridge_oof_blocked": "ridge out-of-fold, folds blocked on both molecules",
    }
    # `lotv_binning6` is a cell of the corner's reported bin grid -- deployed convention,
    # maximum-likelihood within-bin variance, six bins -- and not a fitted estimator.  It
    # reaches the panel through the LOTV rule or not at all, exactly as the broad set's
    # `threshold_mse_over_2_full` is a threshold and not a bound.  Excluded BY NAME, so it
    # cannot hide an estimator behind it.
    corner_oof_skip = {"lotv_binning6"}
    unnamed = set(dpe) - set(corner_oof_names) - corner_oof_skip
    if unnamed:
        raise KeyError(f"unnamed estimator(s) in the corner's audit artifact: "
                       f"{sorted(unnamed)}; the inclusion rule draws every one of them")

    def _corner_oof(key):
        if key not in dpe:
            raise KeyError(f"the corner's audit artifact no longer records '{key}', which the "
                           f"inventory names; a bound may not be replaced by a literal")
        v = dpe[key].get("binsuff_up")
        # the blocked ridge does not converge on the corner; report it as such, not as a number
        return float("inf") if v is None or float(v) > 1e6 else float(v)

    # The corner's second audit artifact.  Its `ridge_oof` is the deliberately aggressive
    # out-of-fold ridge and is a design of its own; the other three entries repeat estimators
    # the keystone artifact already records, and that claim is CHECKED here rather than
    # asserted, so a silent divergence between the two artifacts stops the figure instead of
    # picking one of them.  `_most_conservative` is a maximum over the four, not an estimator.
    rb_est = rb_json.get("estimator_sensitivity", {})
    rb_duplicates = {"rf_oof": "rf_oof_random5fold", "knn": "knn_raw",
                     "binning6": "lotv_binning6"}
    rb_named = {"ridge_oof"} | set(rb_duplicates) | {"_most_conservative"}
    unnamed_rb = set(rb_est) - rb_named
    if unnamed_rb:
        raise KeyError(f"unnamed estimator(s) in the corner's robustness artifact: "
                       f"{sorted(unnamed_rb)}; name it or the panel is not complete")
    for here, there in rb_duplicates.items():
        if here in rb_est and there in dpe:
            a, b_ = float(rb_est[here]["binsuff_up"]), float(dpe[there]["binsuff_up"])
            if abs(a - b_) > 5e-4:
                raise ValueError(f"the corner's two audit artifacts disagree on {here}: "
                                 f"{a} vs {b_} for {there}; one mark cannot stand for both")
    if "ridge_oof" not in rb_est:
        raise KeyError("the corner's robustness artifact no longer records the aggressive "
                       "out-of-fold ridge, which the inventory names")
    aggressive_ridge = float(rb_est["ridge_oof"]["binsuff_up"])

    panels = []
    if rep_json and Path(rep_json).exists():
        r = json.load(open(rep_json))
        rg = {(c["n_bins"], c["within_bin_variance"], c["convention"]): c for c in r["lotv_grid_2002"]}
        # ONE convention rule across both panels -- the DEPLOYED residual-only one.
        rb = rg[(8, "Bessel", "res")]
        rep_mse = r["mse"]["2002_res"]
        aud_path = Path(rep_json).with_name("representative_audit.json")
        aud = json.load(open(aud_path)) if aud_path.exists() else {}
        oof = aud.get("oof_estimators", {})
        r3_path = Path(rep_json).with_name("convention_audit.json")
        r3 = json.load(open(r3_path)) if r3_path.exists() else {}
        # the 56-cell convention-audit grid is the one that carries the 4-bin cell; the 32-cell
        # inside representative_decomposition.json does not, which is how it went missing.
        rep_cells = r3.get("representative_grid") or list(r["lotv_grid_2002"])
        bounds = [{"name": "LOTV 8 bins, unbiased (headline)", "value": rb["b_insuff_up"],
                   "family": "lotv"},
                  {"name": "LOTV 8 bins, maximum-likelihood",
                   "value": rg[(8, "ML", "res")]["b_insuff_up"], "family": "lotv"}]
        bounds += _lotv_coarse_bounds(rep_cells, rep_mse)
        bounds += [{"name": "LOTV 8 bins, full convention (also valid)",
                    "value": rg[(8, "Bessel", "full")]["b_insuff_up"], "family": "lotv"}]
        # EVERY out-of-fold estimator the artifact records, none hand-picked.  A previous version
        # hard-listed four of the six and dropped `rf_folds_blocked_on_solute` (2.04) -- a
        # molecule-blocked design that is VACUOUS on this set, exactly as three of the corner's
        # blocked designs are vacuous on theirs.  Dropping it here while drawing them there made
        # the two panels disagree about what counts, and made blocked designs look as though they
        # blow up only on the corner.  The one non-estimator key (`threshold_mse_over_2_full`) is
        # a threshold, not a bound, and is excluded by name.
        if oof:
            oof_names = {
                "rf_folds_blocked_on_pair": "RF out-of-fold, folds blocked on pair",
                "ridge_folds_blocked_on_pair": "ridge out-of-fold, folds blocked on pair",
                "rf_blocked_on_pair_zstar_plus_T":
                    "RF out-of-fold, folds blocked on pair, conditioning on $(z^\\ast,T)$",
                "rf_folds_blocked_on_solute": "RF out-of-fold, folds blocked on solute",
                "rf_random_folds": "RF out-of-fold, random folds (leaky)",
                "ridge_random_folds": "ridge out-of-fold, random folds (leaky)",
            }
            skip = {"threshold_mse_over_2_full"}
            missing = set(oof) - set(oof_names) - skip
            if missing:
                raise KeyError(f"unnamed out-of-fold estimator(s) in the broad-set audit: "
                               f"{sorted(missing)}; the inclusion rule draws every one of them")
            bounds += [{"name": oof_names[k], "value": float(oof[k]), "family": "fit"}
                       for k in oof_names if k in oof]
        if r3:
            bounds += [{"name": "E[Var(m|pair)], binning-free (359 rows)",
                        "value": r3["pair_conditional_bound"]["E_Var_m_given_pair_on_those_rows"],
                        "family": "lotv"}]
        panels.append({
            # 2026-07-28: the panel title used to read "representative set"; that name states a
            # coverage claim S4.2(i) retracts, so the panel now carries the set's actual name.
            # The convention ("deployed residual-only") used to ride along in the title and is
            # now the caption's, which is the only place a shared rule can be stated once.
            "title": f"broad IDAC set  ($n{{=}}{r['n']}$, UD profiles)",
            "mse": rep_mse, "headline": rb["b_insuff_up"], "bounds": bounds,
        })
    corner_bounds = [{"name": "LOTV 8 bins, unbiased (headline)",
                      "value": corner_headline, "family": "lotv"},
                     {"name": "LOTV 8 bins, maximum-likelihood",
                      "value": required_cell("res", 8, "ML"), "family": "lotv"}]
    # The corner's own coarse-bin cells -- 3 bins 1.00 and 4 bins 0.87, BOTH above
    # this panel's threshold and bolded as negative-margin cells in the SI grid -- were
    # omitted while the representative panel drew its coarsest cell.  Same rule now.
    corner_bounds += _lotv_coarse_bounds(grid, corner_mse)
    corner_bounds += [{"name": "LOTV 8 bins, full convention (also valid)",
                       "value": required_cell("full", 8, "Bessel"), "family": "lotv"}]
    # Every out-of-fold design the corner's audit artifact records, in the artifact's own
    # order, plus the aggressive ridge the robustness artifact adds.  Vacuous and divergent
    # designs included: the figure draws them off-scale rather than omitting them.
    corner_bounds += [{"name": corner_oof_names[k], "value": _corner_oof(k), "family": "fit"}
                      for k in corner_oof_names]
    corner_bounds += [{"name": "ridge out-of-fold, deliberately aggressive",
                       "value": aggressive_ridge, "family": "fit"}]
    panels.append({
        "title": "corner  ($n{=}60$, VT-2005)",
        "mse": corner_mse,
        "headline": corner_headline,
        "bounds": corner_bounds,
    })
    return panels


def _swarm_rows(values: np.ndarray, min_sep: float) -> np.ndarray:
    """Row index per value so that markers closer than `min_sep` in x stack instead of overlap.

    Ten bounds on one axis is a rug, not a scatter: several of them differ by 0.02 and would
    print as one blob.  Stacking is what lets the reader count them.
    """
    rows = np.zeros(len(values), dtype=int)
    last: dict[int, float] = {}
    for i in np.argsort(values):
        r = 0
        while r in last and values[i] - last[r] < min_sep:
            r += 1
        last[r] = values[i]
        rows[i] = r
    return rows


MARK_AREA = 26.0          # `s` of a bound mark, pt^2 -> a disc sqrt(26) = 5.10 pt across
THRESH_LW = 1.2           # linewidth of the dashed separation threshold, pt
NEAR_FS = 6.4             # type size of a near-threshold mark's printed value, pt


def _x_pt_per_unit(ax) -> float:
    """Printed points per data unit on x.  Only valid once the layout is final."""
    (x0, _), (x1, _) = ax.transData.transform([(0.0, 0.0), (1.0, 0.0)])
    return abs(x1 - x0) * 72.0 / ax.figure.dpi


def _y_unit_per_pt(ax) -> float:
    """Data units per printed point on y.  Only valid once the layout is final."""
    (_, y0), (_, y1) = ax.transData.transform([(0.0, 0.0), (0.0, 1.0)])
    return ax.figure.dpi / (abs(y1 - y0) * 72.0)


def _near_threshold_and_connector(ax, mse, b, vals, rows, y0, pitch, ybar, h) -> None:
    """Print the value of any mark that touches the threshold, then tie the bar's cut to
    the mark it was taken from.

    BOTH decisions are made in PRINTED POINTS, not in data units.  The two panels carry
    different total errors and therefore different axis scales, so the same data-unit gap is
    a different gap on the page: the corner's headline mark stands 0.023 units off its
    threshold and the broad set's four-bin cell 0.003 off its own, and on the page those are
    3.1 pt and 0.3 pt -- both inside the 2.55 pt radius of the disc that is supposed to show
    which side of the line the bound falls on.  A data-unit rule fires on one panel and not
    the other; a points rule fires on both.  The threshold's own label is a separate
    question and is decided where it is drawn.

    This runs after the layout is final, because that is when `ax.transData` knows how many
    points a data unit is worth.
    """
    ppu = _x_pt_per_unit(ax)
    upp = _y_unit_per_pt(ax)
    radius = np.sqrt(MARK_AREA) / 2.0
    reach = radius + THRESH_LW / 2.0 + 1.0        # disc, half the line, 1 pt of daylight
    touches = np.abs(vals - mse / 2) * ppu < reach
    for v, r, near in zip(vals, rows, touches):
        if near:
            ax.annotate(f"{v:.3f}", (v, y0 - r * pitch), xytext=(0, 5),
                        textcoords="offset points", ha="center", va="bottom",
                        fontsize=NEAR_FS, color=INK, zorder=8,
                        bbox=dict(facecolor="white", edgecolor="none", pad=0.6))
    hi = int(np.argmin(np.abs(vals - b)))          # the mark the bar's cut was taken from
    # start the connector above the headline mark, and above its printed value if it has one
    gap = (5.0 + NEAR_FS * 1.2 + 1.0) if touches[hi] else radius + 1.8
    ax.plot([b, b], [y0 - rows[hi] * pitch + gap * upp, ybar - h / 2],
            ls=":", lw=0.9, color=GRAY, zorder=2)


def fig_decomposition(decomp_json: Path, out_dir: Path,
                      rep_json: Path | None = None, grid_json: Path | None = None,
                      keystone_json: Path | None = None,
                      robustness_json: Path | None = None) -> list[str]:
    """Two panels of one-sided bounds: the broad IDAC set (n=477, UD profiles) and the
    corner (n=60, VT-2005), both under the deployed residual-only convention.

    2026-07-28 rebuild.  The previous version drew each panel's ten-odd bounds as labelled
    rows; the labels collided with each other, with the threshold line and with the axis,
    four of them ran off the plotting area, and nothing was legible at the printed column
    width.  What the figure is FOR is the two-sided split against the total error and the
    position of every reported bound relative to the separation threshold -- so that is all
    it now draws:

      * one bar per panel, cut at the headline bound: teal = the input term's upper bound,
        salmon = the model-misspecification lower bound it implies, the two contiguous and
        summing to the total error;
      * the threshold MSE/2, which every bound must fall below for the ordering to hold;
      * EVERY bound the inclusion rule keeps, as one mark each on a shared axis -- circle
        if it fits no model, diamond if it is an out-of-fold regression, threat-coloured if
        it sits above the threshold, and a right-pointing mark at the axis edge if it is
        vacuous or divergent.  Marks that would overlap stack (`_swarm_rows`) so that the
        count is readable.

    Nothing was dropped: the inventory is drawn mark-for-mark and its NAMES and VALUES move
    to the Supporting Information table, which the caption must point at.  The unfavourable
    bounds -- the broad set's pair-blocked ridge (1.47) and its 4-bin LOTV cell (0.948
    against a threshold of 0.951), the corner's 3- and 4-bin cells above its own threshold,
    and the corner's four vacuous/divergent molecule-blocked estimators -- are all still
    here, now as marks the eye can count rather than as text it cannot read.
    """
    panels = _decomposition_panels(decomp_json, rep_json, grid_json,
                                   keystone_json, robustness_json)

    fig, axes = plt.subplots(1, len(panels), figsize=(7.1, 2.85))
    axes = np.atleast_1d(axes)
    deferred = []
    for ax, P in zip(axes, panels):
        mse, b = P["mse"], P["headline"]
        vals = np.array([x["value"] for x in P["bounds"]], dtype=float)
        fam = [x["family"] for x in P["bounds"]]
        xmax = mse * 1.12

        # ---- the split, as one bar whose full width IS the total error ----
        ybar, h = 0.82, 0.24
        ax.barh(ybar, b, height=h, left=0.0, color=TEAL, edgecolor=INK, linewidth=0.9, zorder=3)
        ax.barh(ybar, mse - b, height=h, left=b, color=SALMON, edgecolor=INK, linewidth=0.9,
                zorder=3)
        # The line has to cross the bar to be compared with the cut, and it must pass BEHIND the
        # two labels.  zorder alone does not achieve that: matplotlib text has no background, so a
        # line at lower zorder still shows through the gaps between the glyph strokes and reads as
        # a strikethrough.  Each label therefore carries an opaque patch in its own block's colour.
        ax.text(b / 2, ybar, f"inputs\n$\\leq {b:.2f}$", ha="center", va="center",
                fontsize=7.8, color=INK, zorder=7,
                bbox=dict(facecolor=TEAL, edgecolor="none", pad=1.4))
        ax.text(b + (mse - b) / 2, ybar, f"model misspecified\n$\\geq {mse - b:.2f}$",
                ha="center", va="center", fontsize=8.2, color=INK, fontweight="bold", zorder=7,
                bbox=dict(facecolor=SALMON, edgecolor="none", pad=1.4))
        ax.annotate(f"total error $= {mse:.2f}$", (mse, ybar + h / 2), xytext=(0, 4),
                    textcoords="offset points", ha="right", va="bottom", fontsize=7.6,
                    color=INK)

        # ---- the threshold ----
        # Two decimals, unless a mark would print the SAME two-decimal string as the
        # threshold; then both go to three, because the panel must not show a bound and the
        # line it has to clear as the same number.  (Broad set: 0.948 and 0.9517 both read
        # 0.95.)  How CLOSE a mark is on the page is a different question, decided in
        # `_near_threshold_and_connector`.
        thr2 = f"{mse / 2:.2f}"
        thr_txt = (f"{mse / 2:.3f}"
                   if any(np.isfinite(v) and f"{v:.2f}" == thr2 for v in vals) else thr2)
        ax.plot([mse / 2, mse / 2], [0.215, 0.96], ls="--", lw=1.2, color=HURT, zorder=5)
        ax.text(mse / 2, 0.185, f"threshold\n$\\mathrm{{MSE}}/2 = {thr_txt}$", ha="center",
                va="top", fontsize=7.0, color=HURT)

        # ---- every reported bound, one mark each ----
        # The top mark row sits 0.20 of the axis below the bar, which is 21 pt on the page:
        # enough for a near-threshold mark to print its value AND still leave a visible stub
        # of the connector above it.  At the old 0.58 the two wanted the same 13 pt and the
        # connector came out with NEGATIVE length on the corner panel, where the mark the bar
        # is cut at is also the mark that prints its value.
        finite = np.isfinite(vals) & (vals <= xmax)
        rows_on = _swarm_rows(vals[finite], 0.030 * xmax)
        y0, pitch = 0.50, 0.082
        for (v, f_, r) in zip(vals[finite], np.array(fam)[finite], rows_on):
            ax.scatter(v, y0 - r * pitch, s=MARK_AREA, marker=("o" if f_ == "lotv" else "D"),
                       color=(HURT if v > mse / 2 else TEAL), edgecolor=INK, linewidth=0.5,
                       zorder=6)
        for k in range(int((~finite).sum())):        # vacuous or divergent: at the edge
            ax.scatter(xmax * 0.985, y0 - k * pitch, s=30, marker=">", color=HURT,
                       edgecolor=INK, linewidth=0.5, zorder=6, clip_on=False)
        # The near-threshold values and the bar-cut connector are drawn once the layout is
        # final, so that "too close to the threshold to read" is a distance on the page and
        # comes out the same on two panels with different axis scales.
        deferred.append(dict(ax=ax, mse=mse, b=b, vals=vals[finite], rows=rows_on,
                             y0=y0, pitch=pitch, ybar=ybar, h=h))

        ax.set_xlim(0, xmax)
        ax.set_ylim(0.0, 1.02)
        ax.set_yticks([])
        # 8.8 pt, not 8.2: the "2" is a mathtext superscript set at 0.7x the base, and this
        # figure prints at 1.01x, so an 8.2 pt base puts it on the page at 5.8 pt.
        ax.set_xlabel("error magnitude  ($\\ln\\gamma$ units$^2$)", fontsize=8.8)
        ax.tick_params(axis="x", labelsize=7.6)
        ax.set_title(P["title"], fontsize=8.8)
        ax.grid(False)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)

    key = [plt.Line2D([], [], ls="", marker="o", ms=4.6, mfc=TEAL, mec=INK, mew=0.5,
                      label="fits no model"),
           plt.Line2D([], [], ls="", marker="D", ms=4.2, mfc=TEAL, mec=INK, mew=0.5,
                      label="fitted out-of-fold"),
           plt.Line2D([], [], ls="", marker="o", ms=4.6, mfc=HURT, mec=INK, mew=0.5,
                      label="above the threshold"),
           plt.Line2D([], [], ls="", marker=">", ms=4.6, mfc=HURT, mec=INK, mew=0.5,
                      label="beyond the axis"),
           # the dotted connector was the only line style in the figure with no key
           plt.Line2D([], [], ls=":", lw=0.9, color=GRAY,
                      label="the bound the bar is cut at")]
    # The descriptor rides on the legend rather than inside an axis, where it would have sat
    # across the threshold line in both panels.
    leg = fig.legend(handles=key, loc="lower center", ncol=5, fontsize=7.2, frameon=False,
                     handletextpad=0.4, columnspacing=1.3, bbox_to_anchor=(0.5, -0.005),
                     # No completeness phrase here.  "every fitted estimator" over-claimed: the
                     # LOTV half is a selection from two bin grids and the stratified bounds are
                     # not drawn at all.  The inclusion rule is note a of the bounds table, which
                     # is the one place it is stated.
                     title="upper bounds on the input term (inclusion rule: bounds table, note a)")
    leg.get_title().set_fontsize(7.6)
    leg.get_title().set_color(GRAY)
    fig.tight_layout(rect=(0, 0.125, 1, 1))
    for D in deferred:
        _near_threshold_and_connector(**D)
    # NOT fig_decomposition any more.  That stem now belongs to the stratified map
    # (scripts/analysis/make_stratified_map_figure.py), which retires the aggregate this
    # function draws; leaving the old stem here would let a rerun of this script silently
    # overwrite the map with the figure it replaced.
    return _save(fig, out_dir, "fig_bounds_inventory")


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--e5-dir", default="results/e5_sigma_grounding")
    ap.add_argument("--matched-csv", default="results/b_insuff/matched_pairs.csv")
    ap.add_argument("--decomposition-json", default="results/b_insuff/decomposition.json")
    ap.add_argument("--representative-json",
                    default="results/b_insuff/representative_decomposition.json")
    ap.add_argument("--grid-json", default="results/b_insuff/estimator_grid.json")
    ap.add_argument("--keystone-json", default="results/b_insuff/keystone_robustness.json",
                    help="corner molecule-blocked estimators (RF / kNN / divergent ridge).")
    ap.add_argument("--robustness-json", default="results/b_insuff/robustness.json",
                    help="corner estimator sensitivity (the aggressive out-of-fold ridge).")
    ap.add_argument("--out-dir", default="paper/figs")
    ap.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    ap.add_argument("--style", default=None,
                    help="Path to a matplotlib style (default: repo-to-paper softpastel).")
    ap.add_argument("--dump-bounds", action="store_true",
                    help="Print the fig_decomposition bound inventory (the SI table's rows) "
                         "and exit without drawing anything.")
    args = ap.parse_args()

    if args.dump_bounds:
        for P in _decomposition_panels(Path(args.decomposition_json),
                                       Path(args.representative_json), Path(args.grid_json),
                                       Path(args.keystone_json), Path(args.robustness_json)):
            print(f"\n{P['title']}   MSE={P['mse']:.3f}  threshold={P['mse'] / 2:.3f}  "
                  f"headline={P['headline']:.3f}  margin={P['mse'] - 2 * P['headline']:+.3f}")
            for x in P["bounds"]:
                v = x["value"]
                flag = "  ABOVE THRESHOLD" if v > P["mse"] / 2 else ""
                if not np.isfinite(v):
                    print(f"    {x['name']:<52s} divergent   [{x['family']}]{flag}")
                else:
                    vac = "  vacuous (>MSE)" if v > P["mse"] else ""
                    print(f"    {x['name']:<52s} {v:>8.3f}   [{x['family']}]{flag}{vac}")
        return

    apply_style(args.style)
    out_dir = Path(args.out_dir)
    written = []
    written += fig_paradox(Path(args.e5_dir), args.seeds, out_dir)
    written += fig_parity(Path(args.matched_csv), out_dir)
    written += fig_decomposition(Path(args.decomposition_json), out_dir,
                                 Path(args.representative_json), Path(args.grid_json),
                                 Path(args.keystone_json), Path(args.robustness_json))
    print("wrote:")
    for w in written:
        print("  " + w)


if __name__ == "__main__":
    main()
