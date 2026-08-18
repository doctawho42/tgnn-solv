#!/usr/bin/env python3
"""fig_donor_window -- the learned sigma-profile's area in the window COSMO-SAC's hydrogen-bond
term reads, against the reference tabulation's.

WHY THIS FIGURE EXISTS
----------------------
Sec. 3.3 carries the manuscript's most chemistry-legible result and carried it in prose alone:
cyclohexane, acetone, toluene and tetrahydrofuran each hold EXACTLY zero area in the donor window
of the reference tabulation, and the learned profile puts 24 to 51 A^2 there -- between 23% and 36%
of each molecule's total surface.  Because the 2002 kernel assigns a segment to the donor side by
the threshold |sigma| > sigma_hb alone, with no atom typing, that mass makes the hydrogen-bond term
live on every pair of the scored set regardless of chemistry.

A reader can check "exactly zero against a third of the surface" in one glance and cannot check it
in a sentence, which is what the figure is for.  The manuscript ran three numbered figures against a
JCIM median of seven, and Sec. 3.3 had none.

WHAT IS DRAWN
-------------
One row per solvent, ordered by how many scored rows it carries, so the solvents the substitution
contrast actually rests on are at the top.

  left of the axis   the REFERENCE tabulation's donor-window area, drawn in teal.  For 29 of the 31
                     solvents this is exactly 0.000 A^2 and the bar has no length at all; the two
                     that are non-zero are drawn and labelled, because "the reference is empty" is
                     a claim about this corpus and not a law.
  right of the axis  the LEARNED profile's area in the same window, in salmon, with the fraction of
                     that molecule's total surface printed at the bar end.

Everything is read from results/closure_ladder/placebo_profile_diagnosis.csv, the same deposit
Sec. 3.3 quotes.  Nothing is hard-coded, including which solvents are non-zero on the reference
side.

SCOPE, WHICH THE CAPTION MUST CARRY.  These areas are read off the one trained COSMO-SAC head the
tree retains -- a retired run trained at 8 segment iterations and scored at 30, scoring MAE 2.61 at
R^2 = -0.31 on the scaffold split.  They price the quantity and not the arms of Fig. 2.

Usage
-----
    MPLBACKEND=Agg python scripts/analysis/make_donor_window_figure.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

# House palette, shared with make_parity_figure.py and make_paradox_figures.py.
SALMON = "#E8A98C"   # the learned profile -- the arm the substitution replaces
TEAL = "#7FB5A6"     # the reference tabulation
INK = "#4D4D4D"
_STYLE = Path.home() / ".claude/skills/repo-to-paper/assets/softpastel.mplstyle"

#: Common names for the solvents the manuscript names in prose, so the figure reads as chemistry
#: rather than as SMILES.  Anything absent falls back to its SMILES, which is the honest default.
NAMES = {
    "C1CCCCC1": "cyclohexane", "CC(C)=O": "acetone", "Cc1ccccc1": "toluene",
    "C1CCOC1": "tetrahydrofuran", "O": "water", "CCO": "ethanol", "CC#N": "acetonitrile",
    "CN(C)C=O": "N,N-dimethylformamide", "CCOC(C)=O": "ethyl acetate", "C1COCCO1": "1,4-dioxane",
    "CO": "methanol", "CS(C)=O": "dimethyl sulfoxide", "CC(C)O": "propan-2-ol",
    "CCCCO": "butan-1-ol", "CCCO": "propan-1-ol", "ClCCl": "dichloromethane",
    "ClC(Cl)Cl": "chloroform", "CCCCCC": "hexane", "CC(=O)N(C)C": "N,N-dimethylacetamide",
    "c1ccccc1": "benzene", "CCCCCCC": "heptane", "CC(C)(C)O": "tert-butanol",
    "COC(C)=O": "methyl acetate", "CN1CCCC1=O": "N-methyl-2-pyrrolidone",
    "CCCOC(C)=O": "propyl acetate", "ClC(Cl)(Cl)Cl": "carbon tetrachloride",
    "CCOCC": "diethyl ether", "CC(C)=CC": "2-methyl-2-butene",
}


def load(path: Path, top: int) -> pd.DataFrame:
    d = pd.read_csv(path)
    d = d.sort_values("n_rows", ascending=False).head(top).copy()
    d["name"] = [NAMES.get(s, s) for s in d["solvent_smiles"]]
    return d.iloc[::-1].reset_index(drop=True)   # bottom-up for barh


def draw(d: pd.DataFrame, out_dir: Path, stem: str) -> list[str]:
    if _STYLE.exists():
        plt.style.use(str(_STYLE))
    n = len(d)
    fig, ax = plt.subplots(figsize=(7.0, 0.22 * n + 1.05))
    y = range(n)
    ax.barh(y, -d["reference_donor_window_area"], color=TEAL, height=0.62,
            label="reference tabulation", zorder=3)
    ax.barh(y, d["learned_donor_window_area"], color=SALMON, height=0.62,
            label="learned profile", zorder=3)
    ax.axvline(0, color=INK, lw=0.9, zorder=4)

    for i, r in d.iterrows():
        ax.text(r["learned_donor_window_area"] + 1.4, i,
                f"{100 * r['learned_donor_fraction']:.0f}%", va="center", ha="left",
                fontsize=6.8, color=INK)
        if r["reference_donor_window_area"] > 0:
            ax.text(-r["reference_donor_window_area"] - 1.4, i,
                    f"{r['reference_donor_window_area']:.2f}", va="center", ha="right",
                    fontsize=6.8, color=INK)

    ax.set_yticks(list(y))
    ax.set_yticklabels(d["name"], fontsize=7.4)
    ax.set_xlabel(r"donor-window area, $\AA^2$   "
                  r"($\leftarrow$ reference tabulation $\;|\;$ learned profile $\rightarrow$)",
                  fontsize=8.2)
    ax.tick_params(axis="x", labelsize=7.2)
    lo = -max(4.0, float(d["reference_donor_window_area"].max()) * 1.9)
    ax.set_xlim(lo, float(d["learned_donor_window_area"].max()) * 1.20)
    ax.set_ylim(-0.8, n - 0.2)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.legend(loc="lower right", fontsize=7.4, frameon=False)

    n_zero = int((d["reference_donor_window_area"] == 0).sum())
    ax.set_title(f"The window the hydrogen-bond term reads is empty in the reference "
                 f"for {n_zero} of these {n} solvents",
                 fontsize=8.6, color=INK, pad=7)
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in ("pdf", "png"):
        p = out_dir / f"{stem}.{ext}"
        fig.savefig(p)
        written.append(str(p))
    plt.close(fig)
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", type=Path,
                    default=Path("results/closure_ladder/placebo_profile_diagnosis.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("paper/figs"))
    ap.add_argument("--stem", default="fig_donor_window")
    ap.add_argument("--top", type=int, default=16, help="solvents to draw, by scored-row count")
    a = ap.parse_args()

    d = load(a.table, a.top)
    print(f"{len(d)} solvents drawn, of {len(pd.read_csv(a.table))} in the deposit")
    print(f"reference exactly zero in {(d['reference_donor_window_area'] == 0).sum()} of them; "
          f"learned fraction spans "
          f"{100 * d['learned_donor_fraction'].min():.0f}-{100 * d['learned_donor_fraction'].max():.0f}%")
    for p in draw(d, a.out_dir, a.stem):
        print("wrote", p)


if __name__ == "__main__":
    main()
