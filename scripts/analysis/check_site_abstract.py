#!/usr/bin/env python
"""The manuscript's title and abstract, wherever they are copied, must still agree.

Three copies of the title exist -- the article, the SI, and the public page -- and until 2026-08-24
the rule that they match was carried by a comment in the SI reading "keep the two \\title arguments
identical". A rule enforced by a comment is a rule that drifts, and this one governs the name the
work is deposited and cited under.

The page copies the abstract as prose. Prose does not recompile when the source changes, so the one
drift worth blocking a deployment on is this one: a page that states an older version of the claim
is worse than no page, because a reader who does not open the PDF has no way to know.

Compared on normalised text -- case, punctuation and whitespace stripped -- so a reflow or a
typographic quote does not trip it, and only a change in wording does.

    python scripts/analysis/check_site_abstract.py
"""
from __future__ import annotations

import html
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TEX = REPO / "paper" / "grounding_paradox.tex"
SI = REPO / "paper" / "grounding_paradox_si.tex"
PAGE = REPO / "web" / "index.html"
#: How much of each end of the abstract must appear verbatim. Long enough that a real edit is
#: caught, short enough that the page may keep its own paragraph breaks.
WINDOW = 180


def _norm(s: str) -> str:
    # HTML ENTITIES FIRST.  The page writes the profile symbol as &sigma; and the manuscript as
    # $\sigma$; without unescaping, one normalises to "sigmaprofiles" and the other to "profiles",
    # and the check reports a drift that is an encoding difference.
    s = unicodedata.normalize("NFKD", html.unescape(s))
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.lower())).strip()


def _title(path: Path) -> str:
    m = re.search(r"^\\title\{(.*?)\}", path.read_text(encoding="utf8"), re.S | re.M)
    if m is None:
        raise SystemExit(f"no \\title in {path.relative_to(REPO)}")
    return _norm(re.sub(r"\\[a-zA-Z]+|[${}]", " ", m.group(1)))


def main() -> int:
    art, si = _title(TEX), _title(SI)
    if art != si:
        print("FAIL: the article and the SI carry different titles.")
        print(f"  article: {art}\n  SI:      {si}")
        return 1
    page_all = _norm(re.sub(r"<[^>]+>", " ", PAGE.read_text(encoding="utf8")))
    if art not in page_all:
        print("FAIL: the public page does not carry the manuscript's title.")
        print(f"  expected: {art}")
        return 1
    print(f"ok: one title across the article, the SI and the page ({len(art.split())} words)")

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
