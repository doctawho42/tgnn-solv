#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Count the words in the manuscript's abstract, under a stated rule.

WHY THIS EXISTS
---------------
JCIM's ceiling is 250 words.  The source comment above ``\\begin{abstract}`` in
``paper/grounding_paradox.tex`` recorded that count in prose, and twice it was
carried forward across an editing pass without being re-taken: it said "at it"
when the abstract was 261 words, and later "eight over" without the eight having
been re-checked.  A number that nobody re-runs is a number that goes stale, so
the count is a script and the comment names the script.

THE RULE, and why two numbers are printed
-----------------------------------------
``words``  split on whitespace; a math atom ``$...$`` counts as one word,
           whatever is inside it; tokens carrying neither letter nor digit are
           dropped.  This is the arithmetic ``check_number_conservation.py``
           uses for its own tokenisation and it matches what a human counts.

``em-dash split``  the same, after also splitting on the em dash.  LaTeX's
           ``---`` renders as a dash with no surrounding spaces, so ``word---word``
           is one whitespace token; some counters (and ``pdftotext`` through some
           extractors) treat it as two.  Referees on this manuscript reported
           counts spread over five words for one unchanged abstract, and the
           spread is exactly the number of em-dash joins, so this is the reading
           to hold under.

Usage
-----
    python scripts/analysis/wc_abstract.py [TEX ...]

with no argument, ``paper/grounding_paradox.tex``.  ``--print`` echoes the
tokenised abstract so a disagreement with another counter can be localised.
Exit status is 1 if the em-dash-split count exceeds ``--ceiling`` (default 250),
so the script can gate a build.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_TEX = Path(__file__).resolve().parents[2] / "paper" / "grounding_paradox.tex"


def extract_abstract(source: str) -> str:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", source, re.S)
    if match is None:
        raise SystemExit("no \\begin{abstract} ... \\end{abstract} in that file")
    body = match.group(1)
    # comment lines never reach the reader
    return "\n".join(l for l in body.split("\n") if not l.lstrip().startswith("%"))


def tokenise(body: str, split_em_dash: bool = False) -> list[str]:
    # a math atom is one word, whatever is inside it; the placeholder carries a
    # digit so the "must contain a letter or digit" filter keeps it, and no
    # space is introduced, so `$59$-fold` stays one token.
    text = re.sub(r"\$[^$]*\$", "0", body)
    text = re.sub(r"\\emph\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = text.replace("{", "").replace("}", "")
    if split_em_dash:
        text = text.replace("---", " ").replace("\u2014", " ")
    return [t for t in text.split() if re.search(r"[A-Za-z0-9]", t)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tex", nargs="*", type=Path, default=[DEFAULT_TEX])
    ap.add_argument("--ceiling", type=int, default=250)
    ap.add_argument("--print", dest="echo", action="store_true",
                    help="echo the tokenised abstract")
    args = ap.parse_args()

    status = 0
    for path in args.tex:
        body = extract_abstract(path.read_text(encoding="utf-8"))
        plain = tokenise(body)
        dashed = tokenise(body, split_em_dash=True)
        joins = len(dashed) - len(plain)
        verdict = "OVER" if len(dashed) > args.ceiling else "under"
        print(f"{path}")
        print(f"  words            {len(plain)}")
        print(f"  em-dash split    {len(dashed)}   ({joins} em-dash-joined tokens)")
        print(f"  ceiling {args.ceiling}: {verdict}")
        if args.echo:
            print()
            print(" ".join(plain))
        if len(dashed) > args.ceiling:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
