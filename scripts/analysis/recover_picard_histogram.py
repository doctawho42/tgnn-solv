#!/usr/bin/env python3
"""Recover fig_picard_test's histogram out of the committed figure into its results artifact.

WHY THIS EXISTS
---------------
``run_picard_compensation_test.py`` needs two training checkpoints.  When the figure had to be
redrawn at the right canvas size -- it was a 4.97 in canvas set in a 3.34 in column, which put
its tick labels on the page at 5.5 pt -- those checkpoints were not on the machine doing the
redraw, and the artifact recorded only summary statistics of the per-molecule cosine, not the
44 values.  So the bar geometry was read back out of the figure itself.

That is a one-time repair, and it is a script rather than a paragraph so the claim can be
checked.  From now on the test records ``histogram`` (edges + counts) directly from
``cos_diag`` on every run, and ``--redraw-from-json`` redraws from it with no checkpoints, so
this script should never be needed again.

HOW IT WORKS
------------
``pdftocairo -svg`` keeps every filled path with its coordinates.  The bars are the only paths
in the histogram's fill colour (#8FB3DA), their heights are exact integer multiples of the
one-molecule height, and the x axis is calibrated on the printed tick labels -- so the counts
come out exact (they must sum to ``n_molecules``, which is asserted) and the edges come out to
the precision of the tick positions.

    python scripts/analysis/recover_picard_histogram.py
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "paper" / "figs" / "fig_picard_test.pdf"
ART = ROOT / "results" / "compensation" / "picard_test.json"
BAR_RGB = "56.077576%"          # #8FB3DA, the histogram fill


def _pairs(d: str) -> list[tuple[float, float]]:
    return [(float(a), float(b)) for a, b in re.findall(r"(-?[\d.]+) (-?[\d.]+)", d)]


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        svg = Path(tmp) / "fig.svg"
        bbox = Path(tmp) / "fig.bbox.xml"
        subprocess.run(["pdftocairo", "-svg", str(PDF), str(svg)], check=True)
        subprocess.run(["pdftotext", "-bbox-layout", str(PDF), str(bbox)], check=True)
        svg_text, bbox_text = svg.read_text(), bbox.read_text()

    bars = []
    for elem in re.findall(r"<path\b[^>]*/>", svg_text, flags=re.S):
        if BAR_RGB not in elem:
            continue
        pts = _pairs(re.search(r'd="([^"]*)"', elem, flags=re.S).group(1))
        bars.append((min(p[0] for p in pts), max(p[0] for p in pts),
                     max(p[1] for p in pts) - min(p[1] for p in pts)))
    bars.sort()
    if not bars:
        raise SystemExit(f"no bar-coloured paths in {PDF}")
    width = bars[0][1] - bars[0][0]
    x_left = bars[0][0]
    unit = min(b[2] for b in bars)                       # the height of one molecule

    words = [(float(a), float(b), float(c), t) for a, b, c, _, t in re.findall(
        r'<word xMin="([\d.-]+)" yMin="([\d.-]+)" xMax="([\d.-]+)" '
        r'yMax="([\d.-]+)">([^<]*)</word>', bbox_text)
        if re.fullmatch(r"\d+\.\d+", t)]
    if not words:
        raise SystemExit(f"no numeric tick labels in {PDF}")
    # The x-axis tick row is the LOWEST row of numeric words (largest yMin).
    row_y = max(w[1] for w in words)
    row = sorted((w for w in words if abs(w[1] - row_y) < 1.0), key=lambda w: w[0])
    # The row reads e.g. 0.20 0.15 0.10 0.05 0.00 0.05 0.10 0.15: a negative label's leading
    # minus is drawn but is not inside its word box, which shifts those centres right.  So
    # calibrate on the ticks from the zero rightwards, which carry no sign.
    vals = [float(w[3]) for w in row]
    z = vals.index(min(vals))                            # the 0.00 tick
    pos = [((w[0] + w[2]) / 2, v) for w, v in zip(row[z:], vals[z:])]
    if len(pos) < 2:
        raise SystemExit("fewer than two non-negative x ticks; cannot calibrate the axis")
    per_unit = ((pos[-1][0] - pos[0][0]) / (pos[-1][1] - pos[0][1]))
    zero = pos[0][0] - pos[0][1] * per_unit

    n_bins = 15
    counts = [0] * n_bins
    for x0, _, h in bars:
        counts[int(round((x0 - x_left) / width))] = int(round(h / unit))
    edge0, wd = (x_left - zero) / per_unit, width / per_unit
    edges = [edge0 + k * wd for k in range(n_bins + 1)]

    art = json.loads(ART.read_text())
    if sum(counts) != art["n_molecules"]:
        raise SystemExit(f"recovered {sum(counts)} molecules, artifact says "
                         f"{art['n_molecules']}; the recovery is wrong, not the artifact")
    art["histogram"] = {
        "bin_edges": [round(e, 10) for e in edges],
        "counts": counts,
        "median": art["per_molecule_cosine"]["median"],
        "provenance": ("recovered from paper/figs/fig_picard_test.pdf by "
                       "scripts/analysis/recover_picard_histogram.py (bar paths + tick "
                       "calibration); every later run of run_picard_compensation_test.py "
                       "writes this block directly from cos_diag"),
    }
    ART.write_text(json.dumps(art, indent=2))
    print(f"counts {counts} (sum {sum(counts)}) -> {ART}")


if __name__ == "__main__":
    main()
