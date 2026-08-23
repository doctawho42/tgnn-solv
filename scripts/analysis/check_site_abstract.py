#!/usr/bin/env python
"""The public page's abstract must still be the manuscript's.

The page copies the abstract as prose. Prose does not recompile when the source changes, so the one
drift worth blocking a deployment on is this one: a page that states an older version of the claim
is worse than no page, because a reader who does not open the PDF has no way to know.

Compared on normalised text -- case, punctuation and whitespace stripped -- so a reflow or a
typographic quote does not trip it, and only a change in wording does.

    python scripts/analysis/check_site_abstract.py
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TEX = REPO / "paper" / "grounding_paradox.tex"
PAGE = REPO / "web" / "index.html"
#: How much of each end of the abstract must appear verbatim. Long enough that a real edit is
#: caught, short enough that the page may keep its own paragraph breaks.
WINDOW = 180


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.lower())).strip()


def main() -> int:
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", TEX.read_text(encoding="utf8"),
                  re.S)
    if m is None:
        print(f"FAIL: no abstract environment in {TEX.relative_to(REPO)}")
        return 1
    body = re.sub(r"%.*", "", m.group(1))
    body = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", body)
    abstract = _norm(re.sub(r"\\[a-zA-Z]+", "", body))
    page = _norm(re.sub(r"<[^>]+>", " ", PAGE.read_text(encoding="utf8")))

    missing = [(w, s) for w, s in (("opening", abstract[:WINDOW]), ("close", abstract[-WINDOW:]))
               if s not in page]
    if missing:
        print("FAIL: the page's abstract has drifted from the manuscript's.")
        for where, snippet in missing:
            print(f"\n  the {where} of the manuscript abstract is not on the page:\n    ...{snippet}...")
        print(f"\n  update {PAGE.relative_to(REPO)} to match {TEX.relative_to(REPO)}.")
        return 1
    print(f"ok: the page's abstract matches the manuscript ({len(abstract.split())} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
