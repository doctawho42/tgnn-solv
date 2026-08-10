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

THE RULE, and why three numbers are printed
-------------------------------------------
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

``as rendered``  the em-dash split, and additionally the spacing LaTeX itself
           puts into a math atom.  TWO things space an atom, and for eight days
           this rule modelled only the first:

             * a comma inside ``$...$`` is punctuation and is followed by a thin
               space, so ``$[+1.27,+2.83]$`` reaches the page as
               ``[+1.27, +2.83]``: two tokens where the source has one atom;
             * an OPERATOR NAME is set upright and followed by a thin space, so
               ``$\\ln x_2$`` reaches the page as ``ln x2``: two tokens again.
               Missing this made the script read 249 for an abstract the page
               read 250, i.e. report a block AT its ceiling as one word under
               it.  ``pdftotext -f 1 -l 1`` on the built article is the check,
               and it is what caught it.

           Explicit spacing commands (``\\,``, ``\\quad``) do the same and are
           modelled with them.  The first two rules count the SOURCE; this one
           counts what the production editor's tool will count, so it is the
           strictest of the three and the one the budget is set against.

Usage
-----
    python scripts/analysis/wc_abstract.py [TEX ...] [--reserve N]

with no argument, ``paper/grounding_paradox.tex``.  ``--print`` echoes the
tokenised abstract so a disagreement with another counter can be localised.
``--reserve N`` lowers the effective ceiling by N words: the manuscript
pre-commits (\\S 2.2, "What the leak-free re-run reports") to reprinting two of
the abstract's magnitudes as per-seed values once the five-seed re-run lands,
and those words have to exist before the numbers do.  Exit status is 1 if the
strictest count exceeds ``--ceiling`` minus ``--reserve`` (default 250 and 0),
so the script can gate a build.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_TEX = Path(__file__).resolve().parents[2] / "paper" / "grounding_paradox.tex"

#: Macros that reach the page as a word of their own.  TeX sets an operator name upright and
#: follows it with a thin space, so ``$\ln x_2$`` is two page tokens ("ln x2") where the source
#: is one math atom.  This is the list of the ones the manuscript uses plus the rest of TeX's
#: standard log-like operators, so that adding one to the abstract does not silently under-count.
#: The boundary is ``(?![A-Za-z])`` and NOT ``\b``: ``_`` is a word character to ``re``, so ``\b``
#: does not fire in ``\log_{10}`` and that atom was being counted as one token where the page has
#: two.  A letter after the name means a DIFFERENT macro -- ``\lnx`` is this manuscript's own --
#: and must not match.
_MATH_OPERATOR = re.compile(
    r"\\(?:ln|log|lg|exp|sin|cos|tan|cot|sec|csc|sinh|cosh|tanh|coth|arcsin|arccos|arctan"
    r"|min|max|inf|sup|lim|liminf|limsup|det|dim|arg|deg|gcd|hom|ker|Pr|operatorname)"
    r"(?![A-Za-z])"
)
#: The manuscript's own shorthands for the quantities it names most, from ``paper/preamble.tex``.
#: They expand to math atoms, so a block that writes ``\lnx`` reaches the page as the same two
#: tokens as ``$\ln x_2$`` -- and the generic "strip every control sequence" rule below would
#: otherwise delete them and count NOTHING.  Expanded before tokenising, in every rule, so the
#: three counts stay comparable.
_MANUSCRIPT_MACROS = {
    r"\lnx": r"$\ln x_2$",
    r"\lng": r"$\ln\gamma_2$",
    r"\lngi": r"$\ln\gamma_2^\infty$",
    r"\Phicry": r"$\Phi$",
}
#: Explicit spacing commands put a space on the page just as certainly.
_MATH_SPACE = re.compile(r"\\[,;:!>]|\\quad\b|\\qquad\b|\\ ")
_SPLIT = "\x00"


def rendered_atom(atom: str) -> str:
    """One placeholder per token ``atom`` reaches the PAGE as; ``$...$`` included.

    A single-part atom yields exactly one placeholder and introduces no space, which is what
    keeps ``$59$-fold`` one token: the page has no space there either.
    """
    inner = atom[1:-1]
    inner = _MATH_OPERATOR.sub(lambda m: m.group(0) + _SPLIT, inner)
    inner = _MATH_SPACE.sub(_SPLIT, inner)
    inner = inner.replace(",", _SPLIT)
    parts = [p for p in inner.split(_SPLIT) if p.strip()]
    return " ".join("0" for _ in parts) if parts else "0"


def extract_abstract(source: str) -> str:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", source, re.S)
    if match is None:
        raise SystemExit("no \\begin{abstract} ... \\end{abstract} in that file")
    body = match.group(1)
    # comment lines never reach the reader
    return "\n".join(ln for ln in body.split("\n") if not ln.lstrip().startswith("%"))


def tokenise(body: str, split_em_dash: bool = False, math_spacing: bool = False) -> list[str]:
    # a math atom is one word, whatever is inside it; the placeholder carries a
    # digit so the "must contain a letter or digit" filter keeps it, and no
    # space is introduced, so `$59$-fold` stays one token.  Under `math_spacing`
    # the atom is replaced by one placeholder per token it reaches the PAGE as
    # (`rendered_atom`), which is what LaTeX's punctuation and operator spacing
    # put there.
    for macro, expansion in sorted(_MANUSCRIPT_MACROS.items(), key=lambda kv: -len(kv[0])):
        body = re.sub(re.escape(macro) + r"(?![A-Za-z])", expansion.replace("\\", "\\\\"), body)
    if math_spacing:
        text = re.sub(r"\$[^$]*\$", lambda m: rendered_atom(m.group(0)), body)
    else:
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
    ap.add_argument("--reserve", type=int, default=0,
                    help="words held back for the five-seed substitution of Sec. 2.2")
    ap.add_argument("--print", dest="echo", action="store_true",
                    help="echo the tokenised abstract")
    args = ap.parse_args()

    budget = args.ceiling - args.reserve
    status = 0
    for path in args.tex:
        body = extract_abstract(path.read_text(encoding="utf-8"))
        plain = tokenise(body)
        dashed = tokenise(body, split_em_dash=True)
        page = tokenise(body, split_em_dash=True, math_spacing=True)
        joins = len(dashed) - len(plain)
        splits = len(page) - len(dashed)
        # AT the ceiling is not under it: a block with no words left to spend behaves like one
        # over budget the moment anything is added, and calling it "under" is how the note in
        # the manuscript came to say "both under the ceiling" of a 250-word block.
        verdict = ("OVER" if len(page) > budget
                   else "AT (no words left)" if len(page) == budget
                   else "under")
        print(f"{path}")
        print(f"  words            {len(plain)}")
        print(f"  em-dash split    {len(dashed)}   ({joins} em-dash-joined tokens)")
        print(f"  as rendered      {len(page)}   ({splits} extra tokens from spaced math atoms)")
        if args.reserve:
            print(f"  ceiling {args.ceiling} less {args.reserve} reserved = {budget}: {verdict}")
        else:
            print(f"  ceiling {args.ceiling}: {verdict}")
        if args.echo:
            print()
            print(" ".join(plain))
        if len(page) > budget:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
