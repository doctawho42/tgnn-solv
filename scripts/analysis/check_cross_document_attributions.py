#!/usr/bin/env python
"""Every numeral the Supporting Information attributes to an article section must print there.

THE BLIND SPOT THIS CLOSES.  check_number_conservation.py compares the SUBMISSION against itself,
so a value that stops printing in the article while still printing in the Supporting Information
is not a loss and is not reported.  But the Supporting Information does not merely repeat values,
it ATTRIBUTES them -- "the $+0.18$ and $+0.27$ of \\S\\ref{sec:paradox}" -- and an attribution to a
section that no longer prints the number sends a referee to a page where it is not.

Found on 2026-08-20, immediately after the pass that deleted the co-adaptation controls from
Sec. 3.1: three such attributions survived the deletion, in the run-family table, the
stream-provenance paragraph and the uncertified-value inventory.  Nothing else could have caught
them.  The values still printed, every cross-reference still resolved, and `make check` was green.

WHAT IS CHECKED.  Each `$value$ ... of \\S\\ref{sec:x}` in the Supporting Information, for the
article sections named below, against the text that section actually prints.  Comments are
ignored on both sides.

WHAT IS NOT.  Attribution to SI sections, and prose that names a section without a numeral.  A
tighter rule would flag the many legitimate sentences that discuss an article section's subject
without quoting a figure from it.

Usage
-----
    python scripts/analysis/check_cross_document_attributions.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTICLE = ROOT / "paper/grounding_paradox.tex"
METHODS = ROOT / "paper/sections/methods.tex"
SI = ROOT / "paper/sections/SI.tex"

#: article label -> (file, the heading it starts at, the heading that ends it)
SECTIONS = {
    "sec:paradox": (ARTICLE, r"\\subsection\{Supervising the intermediate",
                    r"\\subsection\{What the substitution costs"),
    "sec:discussion": (ARTICLE, r"\\subsection\{Scope, accuracy", r"\\section\{Conclusions\}"),
    "sec:surrogate": (ROOT / "paper/sections/compensation-surrogate.tex",
                      r"\\subsection\{What moved inside", r"\Z"),
    "sec:data": (METHODS, r"\\subsection\{Data curation", r"\\subsection\{Model, closure"),
}
#: a numeral, then up to four words, then the reference it is attributed to
PATTERN = re.compile(r"\$([+\-]?\d[\d.]*)\$(?:[^$\\]{0,40}?)of \\S\\ref\{([a-z:0-9-]+)\}")


def uncommented(path: Path) -> str:
    return re.sub(r"(?m)^%.*$", "", path.read_text())


def main() -> None:
    bodies = {}
    for label, (path, start, end) in SECTIONS.items():
        t = uncommented(path)
        i = re.search(start, t)
        if i is None:
            raise SystemExit(f"{label}: heading {start!r} not found in {path.name}; "
                             f"the section was renamed and this gate cannot locate it")
        j = re.search(end, t[i.start():])
        bodies[label] = t[i.start():i.start() + (j.start() if j else len(t))]

    bad = []
    for n, line in enumerate(uncommented(SI).split("\n"), 1):
        for m in PATTERN.finditer(line):
            value, label = m.group(1), m.group(2)
            if label in bodies and value not in bodies[label]:
                bad.append((n, value, label, line.strip()[:76]))

    print(f"checked {len(SECTIONS)} article sections against every attribution in {SI.name}")
    for n, v, lab, ctx in bad:
        print(f"  FAIL  SI.tex:{n}  ${v}$ attributed to {lab}, which does not print it\n"
              f"        {ctx}")
    print(f"\n{len(bad)} dangling attribution(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
