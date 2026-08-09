#!/usr/bin/env python3
"""Table-of-contents graphic for the ACS submission.

ACS asks for one image that conveys the paper at a glance, printed small, and it is
the one image the journal places beside the article.  It therefore has to carry a
claim the paper still makes.

WHAT IT USED TO SAY, AND WHY THAT IS GONE
-----------------------------------------
Until 2026-08-02 the bottom line read "On 477 activity measurements over 185 molecule
pairs, the fixed model and not the input is the likelier ceiling (margin +0.51)".
That is the aggregate verdict, and the aggregate is retired: an aggregate margin is a
composition-weighted average of a term that moves 25-fold across chemistries against a
bound that barely moves, so it reports the composition of the set and not a property of
the closure (Sec. 3.2.1).  The graphic may not restate it.

WHAT IT SAYS NOW
----------------
The finding that survives and is stated in the title: "grounding" names two opposite
operations on one reference database, and they carry opposite signs.  Supervising the
learned profile against the database during training improves solubility MAE; substituting
the same database's profile for the learned one at prediction time degrades it.  Both are
three-seed test-split results of Sec. 3.1, and the scope (solubility MAE, held-out
scaffolds, three seeds) prints in the image.

THE MAGNITUDES ARE GONE, 2026-08-05, AND MAY NOT COME BACK
----------------------------------------------------------
Until 2026-08-05 the two arrows were labelled "MAE -0.20" and "MAE +0.41", and printing
that pair in one image asserts a two-fold asymmetry the design does not support.  The
+0.41 is the evaluation-only substitution and carries the ordinary cost of swapping an
input distribution at test time; the arm that removes that cost, injecting the reference
during training so the model co-adapts, is by design the confound-free one and costs +0.18
-- at one seed, so Sec. S3.1 states that neither +0.18 nor the channel swap's +0.27 can be
ordered against the -0.20, whose own per-seed values (0.237/0.075/0.281) straddle +0.18.
There is no pair of magnitudes this image can print side by side without asserting an
ordering the paper withholds, and at 3.25 x 1.75 in there is no room for the three
sentences that would license one.  So the arrows carry the signs, which are established at
every seed, and the caption sends the reader to the text for the magnitudes.  Do not
restore either number here, and do not "fix" this by printing +0.18 instead of +0.41: that
juxtaposes -0.20 with a one-seed number, which is the same error.

THE LEFT ARROW CARRIES A CAVEAT, 2026-08-07, AND IT MAY NOT BE DROPPED
----------------------------------------------------------------------
Two referees reported that this was the one display in the submission printing the
supervision direction without it.  "Train on it -> MAE improves" is the grounded arm
against the ungrounded one, and it is exactly the contrast Sec. 2.2's disclosure says a
sigma-stream leak could inflate: the ungrounded arm carries no stream, so the only arm a
leak can reach is the grounded one, and the gain stays uncertified until the leak-free
re-run.  The substitution arrow is untouched by this -- it is one checkpoint evaluated two
ways, which no stream build can reach -- so the caveat attaches to the left arrow alone and
the bottom line says which.  It prints NO magnitude, which is the standing decision above.
The wording matches the abstract's ("not certified leak-free") and Sec. 2.2's on purpose.

THE BOTTOM LINES ARE DERIVED, 2026-08-10, AND NO LONGER LITERALS
----------------------------------------------------------------
Until today the three bottom lines were a string literal, which made this the one enrolled
display in ``results/e5_sigma_grounding_leakfree/DISCHARGE_SHEET.md`` (its row 26) that
re-running its own generator does NOT discharge: the script reads no data file, so it
reproduced the caveat verbatim however many seeds had landed and whatever the certificate
said.  Both moving parts now come from the run tree instead -- ``toc_lines()`` counts the
seed directories that carry a deposit and reads
``<root>/provenance_certificate.json`` -- so the graphic cannot be regenerated with a stale
claim standing.  Two things move, not one, and the sheet's WATCH section records why that
matters: the caveat is on line THREE and the seed count is on line TWO, the enrolment names
the caveat, and a pass that reached only line three would leave "three seeds" printed under
a five-seed figure.

The caveat drops when, and only when, the certificate for the tree being drawn exists and
says ``certified: true``.  An absent certificate keeps it, which is the conservative
direction and the state today: the published tree carries no certificate, so the line
prints exactly as it did when it was a literal.

The stratified map is the paper's other deliverable and does not go here: at 3.25 x 1.75
in nothing legible can carry fifteen strata with their margins and intervals, and a
drawn map reduced to one bar per class would be an aggregate again.  The map is a table
in the article (Table 3).

ACS specifies the TOC graphic fits a 3.25 in x 1.75 in slot.

    MPLBACKEND=Agg python scripts/analysis/make_toc_figure.py
    MPLBACKEND=Agg python scripts/analysis/make_toc_figure.py \
        --e5-dir results/e5_sigma_grounding_leakfree
"""
import argparse
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DEFAULT_E5_DIR = REPO / "results" / "e5_sigma_grounding"

_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
          6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


def discover_seeds(root: Path) -> list[int]:
    """Seeds of `root` that actually carry a deposit, not merely a directory."""
    seeds = []
    for path in sorted(root.glob("seed_*")):
        m = re.fullmatch(r"seed_(\d+)", path.name)
        if not m or not path.is_dir():
            continue
        if any(path.glob("*_predictions.csv")) or any(path.glob("*_predictions.summary.json")):
            seeds.append(int(m.group(1)))
    return sorted(seeds)


def certificate_state(path: Path) -> tuple[bool, str]:
    """(is the re-run certified leak-free, why) for the tree this graphic draws."""
    if not path.exists():
        return False, f"no certificate at {path}"
    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return False, f"{path} is not readable JSON ({exc})"
    if doc.get("certified") is True:
        return True, f"{path} certifies the re-run"
    problems = doc.get("problems") or []
    return False, f"{path} does not certify: {len(problems)} problem(s)"


def toc_lines(root: Path | str = DEFAULT_E5_DIR,
              certificate: Path | str | None = None) -> list[str]:
    """The bottom lines of the graphic, derived from the run tree it describes.

    Line 1 is the finding and never moves.  Line 2 carries the seed count.  Line 3 is the
    leak-free caveat and is present exactly when the certificate does not certify.
    """
    root = Path(root)
    if not root.is_absolute():
        root = REPO / root
    cert = Path(certificate) if certificate else root / "provenance_certificate.json"
    if not cert.is_absolute():
        cert = REPO / cert
    n = len(discover_seeds(root))
    seed_word = _WORDS.get(n, str(n))
    lines = [
        "Grounding is two operations on one database, with opposite signs",
        f"(solubility MAE on held-out scaffolds, {seed_word} seeds; magnitudes in the text).",
    ]
    certified, _why = certificate_state(cert)
    if not certified:
        lines.append("Training on it is not certified leak-free; a re-run is pre-committed.")
    return lines

SALMON = "#E8A98C"
TEAL = "#7FB5A6"
INK = "#4D4D4D"
HURT = "#B5654A"
HELP = "#4E8C7A"
OUT = Path(__file__).resolve().parents[2] / "paper" / "figs" / "fig_toc"

# savefig pad_inches: the default 0.1 in adds 14.4 pt of white to a 234 pt-wide canvas, so
# \includegraphics[width=\linewidth] then scales the whole graphic by 0.946 and every point
# size set below prints 5.4% smaller than it reads here.  0.02 in keeps the margin without
# the reduction: at pad 0.1 the 6.0 pt sentence printed at 5.67 pt.
plt.rcParams.update({
    "font.family": "serif", "text.usetex": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "savefig.dpi": 600, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "figure.dpi": 150,
})


def box(ax, x, y, w, h, text, fc, ec=INK, fs=7.0, tc=INK, lw=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.005,rounding_size=0.02",
                                fc=fc, ec=ec, lw=lw, mutation_aspect=0.5, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, zorder=4)


def draw(lines: list[str], out: Path) -> None:
    """Draw the graphic with `lines` as its bottom block."""
    fig = plt.figure(figsize=(3.25, 1.75))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # Point sizes here are printed point sizes (the canvas is the 3.25 in ACS slot and the
    # tocentry measure is 3.26 in).  Nothing below 6.0 pt, and a mathtext sub/superscript is
    # 0.7x its base, so a label carrying one needs a base of at least 8.6 pt.
    y = 0.755
    box(ax, 0.02, y, 0.18, 0.16, "solute\n+ solvent", "white", fs=6.4)
    box(ax, 0.245, y, 0.155, 0.16, "encoder", TEAL, fs=6.5, tc="white", lw=0)
    box(ax, 0.445, y, 0.095, 0.16, r"$\hat\sigma$", TEAL, fs=9.0, tc="white", lw=0)
    box(ax, 0.585, y, 0.245, 0.16, "fixed\nthermodynamics", SALMON, fs=6.4, tc=INK, lw=0)
    for p0, p1 in ((0.20, 0.245), (0.40, 0.445), (0.54, 0.585)):
        ax.add_patch(FancyArrowPatch((p0, y + 0.08), (p1, y + 0.08), arrowstyle="-|>",
                                     color=INK, lw=1.1, mutation_scale=8, zorder=2))
    ax.add_patch(FancyArrowPatch((0.83, y + 0.08), (0.858, y + 0.08), arrowstyle="-|>",
                                 color=INK, lw=1.1, mutation_scale=8, zorder=2))
    ax.text(0.868, y + 0.08, "$\\ln x_2$", ha="left", va="center", fontsize=9.0, color=INK)

    # The reference database, and the two operations on it.  The left arrow is training-time
    # supervision and the right one is the evaluation-time substitution; they end on different
    # boxes because they are different interventions, which is the whole point of the image.
    box(ax, 0.325, 0.375, 0.095, 0.16, r"$\sigma^\star$", SALMON, fs=9.0, tc=INK, lw=0)
    ax.text(0.3725, 0.305, "reference profile", ha="center", va="center", fontsize=6.4, color=INK)

    ax.add_patch(FancyArrowPatch((0.348, 0.545), (0.322, 0.745), arrowstyle="-|>",
                                 color=HELP, lw=1.4, mutation_scale=9, zorder=2))
    ax.add_patch(FancyArrowPatch((0.408, 0.545), (0.487, 0.745), arrowstyle="-|>",
                                 color=HURT, lw=1.4, mutation_scale=9, zorder=2))

    ax.text(0.245, 0.665, "train on it", ha="right", va="center", fontsize=6.8, color=HELP)
    ax.text(0.245, 0.575, "MAE improves", ha="right", va="center", fontsize=6.8, color=HELP)
    ax.text(0.505, 0.665, "feed it in instead", ha="left", va="center", fontsize=6.8, color=HURT)
    ax.text(0.505, 0.575, "MAE degrades", ha="left", va="center", fontsize=6.8, color=HURT)

    # The bottom block states the sign structure rather than a set-level verdict.  The pointer to
    # the text is where the magnitudes went; see the module docstring for why they may not print
    # here.  Both the seed count and the caveat come from toc_lines(), i.e. from the run tree.
    ax.text(0.5, 0.115, "\n".join(lines),
            ha="center", va="center", fontsize=6.0, color=INK, linespacing=1.35)

    for ext in ("pdf", "png"):
        fig.savefig(f"{out}.{ext}")
    plt.close(fig)
    print(f"wrote {out}.pdf / .png")


def main() -> None:
    ap = argparse.ArgumentParser(description="Table-of-contents graphic for the ACS submission.")
    ap.add_argument("--e5-dir", default=str(DEFAULT_E5_DIR),
                    help="results tree the graphic describes; its seed count and its certificate "
                         "are what the bottom lines are derived from "
                         "(default: results/e5_sigma_grounding)")
    ap.add_argument("--certificate", default=None,
                    help="provenance certificate (default: <e5-dir>/provenance_certificate.json)")
    ap.add_argument("--out", default=str(OUT), help="output stem (no extension)")
    args = ap.parse_args()

    root = Path(args.e5_dir)
    if not root.is_absolute():
        root = REPO / root
    lines = toc_lines(root, args.certificate)
    cert = Path(args.certificate) if args.certificate else root / "provenance_certificate.json"
    certified, why = certificate_state(cert if cert.is_absolute() else REPO / cert)
    print(f"seeds     {discover_seeds(root)} in {root}")
    print(f"certified {certified} ({why})")
    for line in lines:
        print(f"  | {line}")
    draw(lines, Path(args.out))


if __name__ == "__main__":
    main()
