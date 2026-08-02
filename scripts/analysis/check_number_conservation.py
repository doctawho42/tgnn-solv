#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report numbers that the compiled manuscript stopped printing.

WHY THIS EXISTS
---------------
Editing passes over ``paper/grounding_paradox.tex`` have repeatedly shortened a
sentence and taken a number out with it -- a confidence interval, a bound, a
stratified re-estimate.  Each loss so far was caught by a human happening to
diff against ``git HEAD``.  This script is the mechanical version of that
check: it compiles two revisions of the manuscript, extracts every number the
*compiled PDF prints*, and reports the ones the baseline printed and the target
does not.

It is a REPORT, not a verdict.  A number legitimately disappears when a claim is
corrected, when a value is superseded, or when a duplicated restatement is
deleted.  Nothing here can tell those apart from an accident, so the output is
grouped by how alarming the disappearance is and every entry carries the
baseline sentence that contained it, so a reader can judge in one glance.

WHAT IT COMPARES
----------------
Compiled text, not LaTeX source.  Source-level extraction misses numbers that
macros build (``\\num``, ``\\Kfmt``, table generators, everything inside the
figures) and it counts numbers sitting in commented-out paragraphs that the
reader never sees.  So both revisions are built with xelatex + bibtex and read
back with ``pdftotext -bbox-layout``, which yields every word together with its
bounding box; the geometry is what makes superscript citation markers and
scientific-notation exponents separable from ordinary digits (see below).

    baseline   a git revision (default ``HEAD``), extracted with ``git archive``
               into a scratch directory and built there.
    target     the working tree by default (copied to scratch, so the user's
               own build products are never touched), or another git revision.

A SUBMISSION, NOT A FILE
------------------------
``--tex`` may be given more than once, and the default gives it twice: the
manuscript is an article plus a separately-built Supporting Information, and a
number that moves from one to the other has not left the submission.  Every root
named is built in the same materialised directory (they share preamble.tex, the
figures and the .bib, and they read each other's .aux through xr-hyper), and the
numbers extracted from the resulting PDFs are pooled into ONE set per revision
before the comparison.  So the check is on the submission as a whole, and the
2026-08-02 split of the Supporting Information into its own document -- which
moved forty-odd pages out of one PDF and into a second one -- is invisible to it,
which is the point: a split is exactly the operation during which a lost number
would go unnoticed.

The two revisions need not have the same roots.  A root that does not exist in a
revision is skipped, and the skip is reported at the top of the output beside the
borrowed-file warnings.  That is what makes the comparison across the split work
at all: the baseline is a single document and the target is two, and pooling
handles the rest.  Page numbers in the report are continuous across a revision's
roots, in the order they were given, and the header prints where each root's
pages begin so a page number can be traced back to a document.

If the baseline revision cannot build because a file it ``\\input``s was never
committed, the missing file is copied in from the working tree and the fact is
reported at the top of the output.  A borrowed file's numbers count as baseline
numbers, which makes the comparison blind to numbers that file *introduced*;
that is why the borrow is reported rather than done quietly.

NORMALISATION
-------------
A numeric token is  ``[sign] digits [. digits] [%]`` with optional thousands
separators (``,``  U+2009  U+202F  U+00A0), which are stripped.  ``-`` counts as
a sign only when the character before it is not alphanumeric, so ``60-pair`` and
``1.70-1.85`` are not read as negatives; U+2212 (the math minus that LaTeX
actually emits) always counts.  A leading ``+`` is decoration and is dropped
from the value but kept in the printed form.  Values are compared as decimals,
so ``0.70`` and ``0.7`` are the same number, while the printed form of every
occurrence is preserved for the report.  ``%`` is part of the identity: ``+3%``
and ``3`` are different numbers, so a lost percentage is never explained away by
an unrelated bare ``3`` elsewhere.

Scientific notation is folded: the words ``1.9`` ``x`` ``10`` + superscript
``16`` become the single number 1.9e16 printed as ``1.9 x 10^16``, and a bare
``10`` + superscript ``-4`` becomes 0.0001.  Without this the exponent would be
thrown away as a superscript and a change from 10^3 to 10^5 would be invisible.

EXCLUSIONS, AND HOW EACH ONE IS DECIDED
---------------------------------------
Every exclusion is structural -- decided from the PDF's own geometry or from an
adjacent word -- never from the value itself.  Counts per rule are printed at
the top of the report so the exclusions themselves can be audited.

  bibliography      Blocks that are numbered reference entries -- text opening
                    "(12) Author, A.; ..." or, in the Supporting Information,
                    "(S12) Author, A.; ..." (achemso's suppinfo mode S-prefixes
                    the markers and the list) -- on a page in the document's tail
                    that is built of them (three or more, and at least 40% of
                    the page's blocks).  Within such a page only the span from
                    the first entry to the last is excluded, so text sharing the
                    heading's page is kept.  This is how reference years, volume
                    and page numbers, DOIs and arXiv identifiers are excluded:
                    as a region, not by pattern matching on plausible years.
                    NOT "everything after the References heading" -- in the
                    two-column measure LaTeX flushes deferred ``table*`` floats
                    at ``\end{document}``, so a revision that has not tamed its
                    float queue prints pages of real tables after the
                    bibliography, and the lazy rule would delete exactly those
                    numbers from the comparison.  (This manuscript's own HEAD
                    does that: fourteen pages of it.)
                    Four-digit numbers in the body are KEPT, deliberately -- in
                    this manuscript "COSMO-SAC 2002", "the 2010 kernel" and
                    "BigSolDB 2.0" name model variants and data versions and are
                    load-bearing.

  section-number    A line-initial "4.7" or "6" set in the heading face, which
                    the class makes at least a point larger than body text.
                    Section numbers move whenever a section moves.

  page-number       A number that is the entire content of the first or last
                    line on a page, that line holding nothing else.  That is the
                    running folio; no sentence ever consists of one number.

  equation-number   A word of the form ``(n)``, n <= 999, that is either alone on
                    its line or is the last word of its line and ends flush at a
                    column's right edge.  The right edges are found per page by
                    clustering line ``xMax`` values, so a parenthesised count in
                    running text -- ``broad IDAC (477)`` -- is not mistaken for
                    an equation tag: it does not sit at the margin.

  citation-marker   A number rendered as a superscript: its baseline (word
                    ``yMax``) sits above the line's median baseline by more than
                    15% of the line's median word height, and its glyphs are
                    smaller than that median.  In the achemso numeric style,
                    in-text citations and footnote marks are exactly this and
                    nothing else is, so citation numbers are removed by how they
                    are *typeset* rather than by guessing which small integers
                    look like reference indices.  The one exception is the
                    scientific-notation exponent, folded in beforehand.

  subscript-index   The mirror rule, below the baseline: variable indices such
                    as the 2 of ``x_2`` or ``ln gamma_2``.  These name a
                    quantity, they do not report one.

  cross-reference   An unsigned integer whose preceding word is a structural
                    noun -- Section, Fig., Figure, Table, Eq., Equation,
                    Appendix, Lemma, Theorem, Proposition, Corollary,
                    Definition, Remark, Step, Panel, Ref., page, p., pp.,
                    Chapter, Part, Note, item, S -- or which follows a letter or
                    a letter-dot inside its own word (``F.2`` of a section
                    label).  These renumber whenever the document is
                    reorganised, which is churn, not evidence.

TIERS
-----
  tier A ("measurement-like")  a number carrying a decimal point, an explicit
        sign, a percent sign, a thousands separator, or a folded exponent.
        Almost nothing LaTeX generates on its own looks like this, so these are
        clean, and only these decide the exit status.

  tier B ("bare integers")     unsigned integers that survived the exclusions:
        sample sizes, bin counts, seed counts -- mixed with whatever structural
        numerals the rules above did not catch.  Reported, never gating, unless
        --gate-integers is given.

  tier F ("figure text")       words that lie in a small block on a page that
        carries a "Figure n:" caption and whose glyph height does not match the
        page's body text.  Axis ticks and panel annotations churn whenever a
        figure is regenerated, so they are reported apart and never gate.

COMPARISON, AND GROUPING
------------------------
The unit is the OCCURRENCE, not the value.  For each value, every baseline
occurrence is matched to the most similar target occurrence of that same value
-- scored on the words immediately around the number and on the whole sentence,
whichever agrees better -- and the baseline occurrences left unmatched are the
ones the document stopped printing.

Counting alone would not do.  When a pass deleted "[+0.48, +1.85]" from one
sentence of this manuscript, an unrelated table gained another +0.48 in the same
revision: the count of 0.48 went UP, and only occurrence matching sees the loss.
Above a multiplicity of 25 the pairing stops meaning anything -- such a value is
a 0 or a 1 scattered through the mathematics -- so those fall back to plain
counting and say so in the report.

  section 1  the value is not printed ANYWHERE in the target: the group that
             matters most, and the one a count could also have found.
  section 2  the value survives elsewhere, but this statement no longer prints
             it.  Entries whose sentence is still in the document -- the pass
             shortened the sentence and the number went with it -- sort first
             and are labelled.
  sections 3-5  the same split for bare integers and for figure text, neither
             of which gates.
  sections 6-7  gained numbers: values the target prints more often than the
             baseline.  A number that appears from nowhere deserves the same
             look as one that vanished.

Every lost occurrence is printed with its baseline sentence and, when one can
be found, with the sentence the target now carries in its place -- which is
what lets a reader separate a corrected claim from an accident without opening
the PDF.

ALLOWLIST
---------
``--allowlist FILE`` retires numbers on purpose.  One entry per line::

    -2.25   superseded by the three-cluster re-estimate of 2026-07-2x

The first whitespace-separated field is the number (write ``%`` for a
percentage, the same way the manuscript printed it); the rest of the line is the
reason and is REQUIRED -- an entry without one is an error, not a silent pass.
Allowlisted losses are listed in their own section and do not affect the exit
status.

EXIT STATUS
-----------
    0   nothing missing (outside the allowlist)
    1   at least one tier-A number is missing
    2   a build, a tool or the allowlist failed

EXAMPLES
--------
    python scripts/analysis/check_number_conservation.py
    python scripts/analysis/check_number_conservation.py --baseline HEAD~3
    python scripts/analysis/check_number_conservation.py \\
        --baseline v1-submission --target HEAD --allowlist paper/retired_numbers.txt

    # the article alone, when that is really what is meant.  Note that against a
    # baseline that carried the appendices in the same file this reports every
    # number of the Supporting Information as gone; that is a true statement
    # about the article and a false one about the submission.
    python scripts/analysis/check_number_conservation.py \\
        --tex paper/grounding_paradox.tex

    # the null control: a revision against itself must report nothing at all.
    # Run it after changing any rule in this file -- it is the false-positive
    # floor, and it should stay at zero in every section.
    python scripts/analysis/check_number_conservation.py \\
        --baseline HEAD --target HEAD

Nothing here writes to the manuscript: both revisions are copied into a scratch
directory and built there, so the working tree's own PDF and aux files are left
alone.  Needs xelatex, bibtex and pdftotext on PATH (or in $XELATEX, $BIBTEX,
$PDFTOTEXT).
"""

from __future__ import annotations

import argparse
import difflib
import html
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Sequence

# --------------------------------------------------------------------------
# defaults
# --------------------------------------------------------------------------

# The submission, in reading order.  Both are built and their numbers pooled; see
# "A SUBMISSION, NOT A FILE" above.  A root absent from a revision is skipped and
# reported, which is how a baseline predating the 2026-08-02 split still compares.
DEFAULT_TEX = ["paper/grounding_paradox.tex", "paper/grounding_paradox_si.tex"]
XELATEX = os.environ.get("XELATEX", "xelatex")
BIBTEX = os.environ.get("BIBTEX", "bibtex")
PDFTOTEXT = os.environ.get("PDFTOTEXT", "pdftotext")

AUX_SUFFIXES = (
    ".aux", ".bbl", ".blg", ".log", ".out", ".toc", ".xdv", ".synctex.gz",
    ".fls", ".fdb_latexmk", ".lof", ".lot", ".nav", ".snm", ".vrb",
)

BIB_HEADINGS = {"references", "bibliography", "notes and references",
                "references and notes"}

XREF_WORDS = {
    "section", "sections", "sec", "sec.", "secs.", "§", "fig", "fig.", "figs",
    "figs.", "figure", "figures", "table", "tables", "tab.", "eq", "eq.",
    "eqs", "eqs.", "equation", "equations", "appendix", "appendices", "lemma",
    "theorem", "proposition", "corollary", "definition", "remark", "step",
    "panel", "panels", "ref", "ref.", "refs", "refs.", "page", "pages", "p.",
    "pp.", "chapter", "part", "note", "notes", "item", "line", "row", "column",
    "no.", "s", "si",
}

SENTENCE_ABBREV = {
    "fig.", "figs.", "eq.", "eqs.", "sec.", "secs.", "tab.", "ref.", "refs.",
    "no.", "vs.", "cf.", "ca.", "approx.", "e.g.", "i.e.", "al.", "et al.",
    "resp.", "st.", "dr.", "prof.", "inc.", "ltd.", "vol.", "ed.", "eds.",
    "pp.", "p.", "min.", "max.", "cal.", "mol.", "chem.", "phys.", "j.",
}

# --------------------------------------------------------------------------
# geometry / text model
# --------------------------------------------------------------------------


@dataclass
class Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    script: str = "base"          # "base" | "super" | "sub"
    line_idx: int = 0
    is_line_start: bool = False
    is_line_end: bool = False

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class Block:
    page: int
    lines: list[list[Word]] = field(default_factory=list)

    @property
    def words(self) -> list[Word]:
        return [w for ln in self.lines for w in ln]


@dataclass
class Page:
    number: int
    blocks: list[Block] = field(default_factory=list)
    width: float = 0.0
    height: float = 0.0


@dataclass
class Occurrence:
    """One printed number, with everything needed to report it."""
    value: str                  # canonical decimal string; carries the sign
    percent: bool
    printed: str                # the form the PDF actually shows
    page: int
    tier: str                   # "A" | "B" | "F"
    context: str                # the sentence that printed it
    local: str                  # the few words either side of it
    flags: tuple[str, ...] = ()

    @property
    def key(self) -> tuple[str, bool]:
        return (self.value, self.percent)

    @property
    def shown(self) -> str:
        return self.value + ("%" if self.percent else "")


# --------------------------------------------------------------------------
# pdftotext -bbox-layout parsing
# --------------------------------------------------------------------------

_WORD_RE = re.compile(
    r'<word xMin="([-\d.eE]+)" yMin="([-\d.eE]+)" '
    r'xMax="([-\d.eE]+)" yMax="([-\d.eE]+)">(.*)</word>\s*$'
)
_PAGE_RE = re.compile(r'<page width="([-\d.eE]+)" height="([-\d.eE]+)">')


def parse_bbox_layout(path: Path) -> list[Page]:
    """Parse ``pdftotext -bbox-layout`` output.

    Deliberately line-oriented rather than an XML parse: poppler does not escape
    control characters that some embedded figure fonts emit, so a strict XML
    parser dies on real manuscripts.
    """
    pages: list[Page] = []
    page: Page | None = None
    block: Block | None = None
    line: list[Word] | None = None
    line_no = 0

    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            s = raw.strip()
            if s.startswith("<page"):
                m = _PAGE_RE.match(s)
                page = Page(number=len(pages) + 1)
                if m:
                    page.width, page.height = float(m.group(1)), float(m.group(2))
                pages.append(page)
            elif s.startswith("<block"):
                block = Block(page=page.number if page else 0)
            elif s.startswith("</block>"):
                if block is not None and block.lines and page is not None:
                    page.blocks.append(block)
                block = None
            elif s.startswith("<line"):
                line = []
                line_no += 1
            elif s.startswith("</line>"):
                if line and block is not None:
                    _tag_scripts(line)
                    line[0].is_line_start = True
                    line[-1].is_line_end = True
                    for w in line:
                        w.line_idx = line_no
                    block.lines.append(line)
                line = None
            else:
                m = _WORD_RE.match(s)
                if m and line is not None:
                    text = html.unescape(m.group(5))
                    if text.strip():
                        line.append(Word(
                            text=text,
                            x0=float(m.group(1)), y0=float(m.group(2)),
                            x1=float(m.group(3)), y1=float(m.group(4)),
                        ))
    return pages


def _tag_scripts(line: list[Word]) -> None:
    """Mark super/subscript words from the line's own typography.

    ``yMax`` is the glyph bottom, i.e. the baseline; the median over the line is
    the body baseline.  A word sitting clear of it, in smaller glyphs, is a
    superscript (citation marker, footnote mark, exponent) or a subscript
    (variable index).
    """
    if len(line) < 2:
        return
    heights = [w.height for w in line]
    baselines = [w.y1 for w in line]
    mh = statistics.median(heights)
    mb = statistics.median(baselines)
    if mh <= 0:
        return
    tol = 0.15 * mh
    for w in line:
        if w.height >= 0.95 * mh:
            continue                       # full-size glyphs are body text
        if w.y1 < mb - tol:
            w.script = "super"
        elif w.y1 > mb + tol:
            w.script = "sub"


# --------------------------------------------------------------------------
# structural regions
# --------------------------------------------------------------------------


# "(12) " in the article, "(S12) " in the Supporting Information: achemso's
# suppinfo mode sets \bibnumfmt to (S#), so without the optional S the SI's
# reference list would not be recognised as one and every year, volume and page
# number in it would count as a printed number of the manuscript.
_ENTRY_RE = re.compile(r"^\(S?\d{1,3}\)\s")


def bibliography_blocks(pages: Sequence[Page]) -> set[tuple[int, int]]:
    """Blocks holding the reference list, as ``(page number, block index)``.

    NOT simply "everything after the References heading": in the two-column
    measure LaTeX flushes its deferred float queue at ``\\end{document}``, so a
    revision that has not tamed its ``table*``s prints a dozen pages of real
    tables *after* the bibliography.  Treating the tail as bibliography there
    would silently delete those tables' numbers from the comparison -- which is
    a way to miss losses, the one failure this script exists to prevent.

    So a page is bibliographic only when it is actually built of numbered
    reference entries (blocks opening ``(12) Author, A.; ...``), and within such
    a page only the span from the first entry to the last is excluded, leaving
    any trailing body text on the heading's page intact.
    """
    out: set[tuple[int, int]] = set()
    floor = int(0.55 * len(pages))
    for page in pages:
        if page.number < floor:
            continue
        entry_idx = [i for i, b in enumerate(page.blocks)
                     if _ENTRY_RE.match(" ".join(w.text for w in b.lines[0]))]
        substantial = [b for b in page.blocks if len(b.lines) >= 2]
        if len(entry_idx) < 3 or len(entry_idx) < 0.4 * max(len(substantial), 1):
            continue
        for i in range(min(entry_idx), max(entry_idx) + 1):
            out.add((page.number, i))
    return out


def column_right_edges(page: Page) -> list[float]:
    """Right margins of the page's text columns.

    Body lines end flush at the margin, so the ``xMax`` values that recur are
    the margins.  Equation tags sit on one of them; a parenthesised count in
    running text does not.
    """
    counts = Counter()
    for block in page.blocks:
        for ln in block.lines:
            counts[round(max(w.x1 for w in ln), 0)] += 1
    return [x for x, n in counts.items() if n >= 3]


def figure_blocks(page: Page) -> set[int]:
    """Indices of blocks on ``page`` that look like text drawn inside a figure.

    Only considered on pages that carry a "Figure n:" caption.  Figure text
    arrives from an embedded graphic, so its glyph height does not match the
    page's body text, and it comes in small blocks (a tick label, a panel
    letter) rather than paragraphs.
    """
    has_caption = False
    body_heights: Counter = Counter()
    for block in page.blocks:
        first = " ".join(w.text for w in block.lines[0])
        if re.match(r"^Figure\s+\d+\s*[:.]", first):
            has_caption = True
        for ln in block.lines:
            for w in ln:
                body_heights[round(w.height, 1)] += 1
    if not has_caption or not body_heights:
        return set()
    modal = body_heights.most_common(1)[0][0]

    out: set[int] = set()
    for i, block in enumerate(page.blocks):
        if len(block.lines) > 5:
            continue
        hs = [w.height for ln in block.lines for w in ln]
        if not hs:
            continue
        if abs(statistics.median(hs) - modal) > 0.35:
            out.add(i)
    return out


# --------------------------------------------------------------------------
# number tokenisation
# --------------------------------------------------------------------------

_THOUSANDS = "[,   ]"
_NUM_RE = re.compile(
    r"(?P<sign>[+−-])?"
    r"(?P<int>\d{1,3}(?:" + _THOUSANDS + r"\d{3})+|\d+)"
    r"(?P<frac>\.\d+)?"
    r"(?P<pct>%)?"
)

_SUP_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷"
                            "⁸⁹⁺⁻", "0123456789+-")


@dataclass
class RawToken:
    """A numeric span found inside one word, before exclusions are applied."""
    word_index: int
    word: Word
    start: int
    end: int
    printed: str
    dec: Decimal
    percent: bool
    tierA: bool
    drop: str | None = None


def _canon(d: Decimal) -> str:
    try:
        s = format(d.normalize(), "f")
    except (InvalidOperation, ValueError):
        s = str(d)
    if s.startswith("+"):
        s = s[1:]
    if s in ("-0", "-0.0"):
        s = "0"
    return s


def _tokens_in_word(word: Word, index: int) -> list[RawToken]:
    text = word.text.translate(_SUP_DIGITS)
    out: list[RawToken] = []
    for m in _NUM_RE.finditer(text):
        sign = m.group("sign") or ""
        start = m.start()
        if sign == "-":
            # ASCII hyphen is a minus only when it does not glue two tokens
            # together: "60-pair" and "1.70-1.85" are not negative numbers.
            prev = text[start - 1] if start > 0 else ""
            if prev.isalnum() or prev == ".":
                sign = ""
                start = m.start("int")
        digits = re.sub(_THOUSANDS, "", m.group("int"))
        frac = m.group("frac") or ""
        try:
            dec = Decimal(("-" if sign in ("-", "−") else "")
                          + digits + frac)
        except InvalidOperation:
            continue
        percent = bool(m.group("pct"))
        tierA = bool(frac) or bool(sign) or percent or (
            re.search(_THOUSANDS, m.group("int")) is not None)
        out.append(RawToken(
            word_index=index, word=word, start=start, end=m.end(),
            printed=text[start:m.end()], dec=dec, percent=percent, tierA=tierA,
        ))
    return out


# --------------------------------------------------------------------------
# block text reconstruction (for context sentences)
# --------------------------------------------------------------------------


def block_text_with_offsets(block: Block) -> tuple[str, list[int]]:
    """Flatten a block to readable text; return the text and per-word offsets.

    Line-wrap hyphens are healed so that a context sentence reads normally.
    """
    parts: list[str] = []
    offsets: list[int] = []
    pos = 0
    pending_hyphen = False
    for ln in block.lines:
        for i, w in enumerate(ln):
            token = w.text
            if parts and not pending_hyphen:
                parts.append(" ")
                pos += 1
            pending_hyphen = False
            offsets.append(pos)
            parts.append(token)
            pos += len(token)
            if i == len(ln) - 1 and len(token) > 1 and token.endswith("-") \
                    and token[-2].isalpha():
                # strip the wrap hyphen and glue to the next line's first word
                parts[-1] = token[:-1]
                pos -= 1
                pending_hyphen = True
    return "".join(parts), offsets


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _is_sentence_end(text: str, i: int) -> bool:
    ch = text[i]
    if ch not in ".!?":
        return False
    if ch == "." and i and text[i - 1].isdigit() \
            and i + 1 < len(text) and text[i + 1].isdigit():
        return False
    j = i + 1
    while j < len(text) and text[j] in ")]}\"'’”":
        j += 1
    if j >= len(text):
        return True
    if not text[j].isspace():
        return False
    k = j
    while k < len(text) and text[k].isspace():
        k += 1
    if k < len(text) and not (text[k].isupper() or text[k] in "([“"):
        return False
    w_start = i
    while w_start > 0 and not text[w_start - 1].isspace():
        w_start -= 1
    if text[w_start:i + 1].lower() in SENTENCE_ABBREV:
        return False
    if i - w_start <= 1 and text[w_start:i].isupper():
        return False                      # single-capital initial
    return True


def _split_sentences(text: str) -> list[str]:
    out, start = [], 0
    for i in range(len(text)):
        if _is_sentence_end(text, i):
            piece = text[start:i + 1].strip()
            if len(piece) > 20:
                out.append(piece)
            start = i + 1
    tail = text[start:].strip()
    if len(tail) > 20:
        out.append(tail)
    return out


def _sentence_around(text: str, pos: int, max_chars: int) -> str:
    """The sentence containing ``pos``.

    Sentence ends are periods/question/exclamation marks followed by whitespace
    and a capital or an opening bracket, minus decimal points and the usual
    abbreviations.  Table rows have no sentence marks at all, so the result is
    clipped to ``max_chars`` around the token.
    """
    def is_end(i: int) -> bool:
        return _is_sentence_end(text, i)

    left = 0
    for i in range(pos - 1, -1, -1):
        if is_end(i):
            left = i + 1
            break
    right = len(text)
    for i in range(pos, len(text)):
        if is_end(i):
            right = i + 1
            break

    sent = text[left:right].strip()
    if len(sent) <= max_chars:
        return sent
    rel = pos - left
    half = max_chars // 2
    a = max(0, rel - half)
    b = min(len(sent), a + max_chars)
    a = max(0, b - max_chars)
    return ("..." if a > 0 else "") + sent[a:b].strip() + ("..." if b < len(sent) else "")


def _flags_for(text: str, pos: int, length: int) -> tuple[str, ...]:
    window = text[max(0, pos - 45):pos + length + 45]
    flags = []
    if "[" in window and "]" in window and "," in window:
        flags.append("interval")
    if "±" in window:
        flags.append("pm")
    low = window.lower()
    if "interval" in low or re.search(r"\bci\b", low) or "%" in window and "interval" in low:
        flags.append("ci")
    if re.search(r"\bp\s*[=≈<>]", low):
        flags.append("p-value")
    return tuple(dict.fromkeys(flags))


# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------


def extract_occurrences(pages: Sequence[Page], max_context: int,
                        page_offset: int = 0
                        ) -> tuple[list[Occurrence], Counter, list[str]]:
    """Every printed number, the per-rule exclusion tally, and every sentence.

    The sentence list is what later lets a lost number be shown next to the
    sentence the target now prints in its place.

    ``page_offset`` is added to the reported page number.  A revision may be
    several documents (article + Supporting Information); their pages are
    reported as one continuous run so that a page in the report identifies a
    place in the submission, and the header says where each document starts.
    The structural rules -- bibliography region, column edges, figure blocks --
    are all per-page or per-document and are applied before the offset, so
    pooling cannot change what any of them decides.
    """
    dropped: Counter = Counter()
    out: list[Occurrence] = []
    sentences: list[str] = []
    bib = bibliography_blocks(pages)

    for page in pages:
        edges = column_right_edges(page)
        figs = figure_blocks(page)
        first_line_ids, last_line_ids = _folio_lines(page)
        modal_h = _modal_height(page)

        for bi, block in enumerate(page.blocks):
            text, offsets = block_text_with_offsets(block)
            words = block.words
            toks: list[RawToken] = []
            for wi, w in enumerate(words):
                toks.extend(_tokens_in_word(w, wi))

            if (page.number, bi) in bib:
                dropped["bibliography"] += len(toks)
                continue

            sentences.extend(_split_sentences(text))
            _fold_scientific(words, toks)
            _apply_exclusions(words, toks, edges, first_line_ids,
                              last_line_ids, modal_h)

            for t in toks:
                if t.drop:
                    dropped[t.drop] += 1
                    continue
                pos = offsets[t.word_index] + t.start
                tier = "F" if bi in figs else ("A" if t.tierA else "B")
                out.append(Occurrence(
                    value=_canon(t.dec), percent=t.percent, printed=t.printed,
                    page=page.number + page_offset, tier=tier,
                    context=_sentence_around(text, pos, max_context),
                    local=_normalise(text[max(0, pos - 55):pos + len(t.printed) + 55]),
                    flags=_flags_for(text, pos, len(t.printed)),
                ))
    return out, dropped, sentences


def _modal_height(page: Page) -> float:
    hs = Counter(round(w.height, 1)
                 for b in page.blocks for ln in b.lines for w in ln)
    return hs.most_common(1)[0][0] if hs else 0.0


def _folio_lines(page: Page) -> tuple[set[int], set[int]]:
    ids = [ln[0].line_idx for block in page.blocks for ln in block.lines]
    if not ids:
        return set(), set()
    return {min(ids)}, {max(ids)}


def _fold_scientific(words: list[Word], toks: list[RawToken]) -> None:
    """Turn ``m x 10^e`` and ``10^e`` into one number.

    Runs before the superscript rule, so an exponent is never mistaken for a
    citation marker, and the mantissa is never left standing on its own.
    """
    by_word: dict[int, list[RawToken]] = defaultdict(list)
    for t in toks:
        by_word[t.word_index].append(t)

    for wi, w in enumerate(words):
        if w.script != "super":
            continue
        if wi == 0 or words[wi - 1].text.strip() != "10":
            continue
        exp_toks = by_word.get(wi, [])
        base_toks = by_word.get(wi - 1, [])
        if len(exp_toks) != 1 or len(base_toks) != 1:
            continue
        exp, base = exp_toks[0], base_toks[0]
        if exp.dec != exp.dec.to_integral_value():
            continue
        try:
            power = Decimal(10) ** int(exp.dec)
        except (ValueError, ArithmeticError):
            continue

        mant = None
        if wi >= 3 and words[wi - 2].text.strip() in {"×", "x", "⋅", "*", "·"}:
            cand = by_word.get(wi - 3, [])
            if len(cand) == 1 and cand[0].drop is None:
                mant = cand[0]

        exp.drop = "sci-exponent(folded)"
        if mant is not None:
            mant.dec = mant.dec * power
            mant.printed = f"{mant.printed} × 10^{exp.printed}"
            mant.tierA = True
            base.drop = "sci-base(folded)"
        else:
            base.dec = power
            base.printed = f"10^{exp.printed}"
            base.tierA = True


def _apply_exclusions(words: list[Word], toks: list[RawToken],
                      edges: Sequence[float],
                      first_lines: set[int], last_lines: set[int],
                      modal_height: float) -> None:
    for t in toks:
        if t.drop:
            continue
        w = t.word
        wi = t.word_index

        # section number: line-initial "4.7", set in the heading face, which is
        # a point or more larger than the page's body text
        if w.is_line_start and re.fullmatch(r"\d+(?:\.\d+)*", w.text.strip()) \
                and modal_height and w.height > modal_height + 1.0:
            t.drop = "section-number"
            continue

        # page folio: the whole line is this one number, at the top or bottom
        if w.is_line_start and w.is_line_end and \
                w.text.strip() == t.printed and t.dec == t.dec.to_integral_value() \
                and not t.percent and (w.line_idx in first_lines
                                       or w.line_idx in last_lines):
            t.drop = "page-number"
            continue

        # equation tag: "(n)" alone on its line, or flush at a column margin
        if re.fullmatch(r"\(\d{1,3}\)", w.text.strip()):
            alone = w.is_line_start and w.is_line_end
            flush = w.is_line_end and any(abs(w.x1 - e) <= 1.5 for e in edges)
            if alone or flush:
                t.drop = "equation-number"
                continue

        if w.script == "super":
            t.drop = "citation-marker"
            continue
        if w.script == "sub":
            t.drop = "subscript-index"
            continue

        # cross-reference numerals
        if not t.percent and t.dec == t.dec.to_integral_value() and t.dec >= 0:
            prev_word = words[wi - 1].text.strip().lower() if wi > 0 else ""
            prev_word = prev_word.strip("(),;:")
            if prev_word in XREF_WORDS:
                t.drop = "cross-reference"
                continue
            head = w.text[:t.start]
            if head and (head[-1].isalpha()
                         or (head[-1] == "." and len(head) > 1 and head[-2].isalpha())):
                # numeral glued to letters inside its own word: the 2 of a
                # section label "F.2", the 3a of "Fig.3a", the 2002 of a model
                # name.  These label things; they do not report measurements.
                t.drop = "label-numeral"
                continue


# --------------------------------------------------------------------------
# building the two revisions
# --------------------------------------------------------------------------


@dataclass
class DocResult:
    """One built document of a revision."""
    tex: Path                     # repo-relative root
    pdf: Path
    pages: int = 0
    first_page: int = 1           # its page 1 as numbered in the pooled report
    errors: list[str] = field(default_factory=list)


@dataclass
class BuildResult:
    label: str
    docs: list[DocResult]
    borrowed: list[str]
    skipped: list[str]            # roots this revision does not have
    pages: int = 0                # pooled, filled in after the PDFs are parsed

    @property
    def errors(self) -> list[str]:
        return [e for d in self.docs for e in d.errors]


def _run(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.setdefault("max_print_line", "1000")
    env.setdefault("error_line", "254")
    env.setdefault("half_error_line", "238")
    return subprocess.run(cmd, cwd=str(cwd), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, errors="replace")


def materialise(repo: Path, rev: str | None, tex_rels: Sequence[Path],
                dest: Path) -> None:
    """Put the manuscript's directory for ``rev`` (or the working tree) in dest.

    One directory for all the roots: they share preamble.tex, the figures, the
    .bib and -- through xr-hyper -- each other's .aux, so they have to be built
    side by side, exactly as ``make'' builds them.
    """
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    paper_rel = tex_rels[0].parent
    if rev is None:
        shutil.copytree(repo / paper_rel, dest / paper_rel,
                        symlinks=True, dirs_exist_ok=True)
    else:
        archive = subprocess.run(
            ["git", "archive", rev, "--", str(paper_rel)],
            cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if archive.returncode != 0:
            raise SystemExit(f"git archive {rev} failed: "
                             f"{archive.stderr.decode(errors='replace').strip()}")
        untar = subprocess.run(["tar", "-x", "-C", str(dest)],
                               input=archive.stdout, stderr=subprocess.PIPE)
        if untar.returncode != 0:
            raise SystemExit(f"tar failed: {untar.stderr.decode(errors='replace')}")

    for tex_rel in tex_rels:
        for suffix in AUX_SUFFIXES + (".pdf",):
            candidate = dest / paper_rel / (tex_rel.stem + suffix)
            if candidate.exists():
                candidate.unlink()


_MISSING_RE = re.compile(r"File [`'\"]([^'\"`]+)' not found")


def build(repo: Path, rev: str | None, tex_rels: Sequence[Path], workdir: Path,
          label: str, reuse: bool) -> BuildResult:
    """Build every root this revision has, in one directory, and report them.

    Roots the revision does not carry are skipped rather than fatal: comparing
    across the split means comparing a one-document revision with a two-document
    one, and refusing to would defeat the check.

    The pass order is the one paper/Makefile uses -- xelatex over all roots,
    bibtex over all roots, then two more xelatex sweeps -- because with xr-hyper
    each document reads the other's .aux at the start of its run, so a root has
    to be revisited after its neighbour has written one.  A single-root build
    degenerates to the familiar xelatex/bibtex/xelatex/xelatex.
    """
    dest = workdir / label
    paper_dir = dest / tex_rels[0].parent

    present, skipped = [], []
    for t in tex_rels:
        exists = (repo / t).exists() if rev is None else _in_rev(repo, rev, t)
        (present if exists else skipped).append(t)
    if not present:
        raise SystemExit(f"[{label}] none of the manuscript roots exist: "
                         + ", ".join(str(t) for t in tex_rels))

    docs = [DocResult(tex=t, pdf=paper_dir / (t.stem + ".pdf")) for t in present]
    if reuse and all(d.pdf.exists() for d in docs):
        for d in docs:
            d.pages = _page_count(d.pdf)
        return BuildResult(label, docs, [], [str(s) for s in skipped])

    materialise(repo, rev, tex_rels, dest)
    borrowed: list[str] = []

    # First sweep, with the missing-file repair loop the single-document version
    # had.  A file borrowed for one root is on disk for the others too.
    for d in docs:
        for _ in range(25):
            _run([XELATEX, "-interaction=nonstopmode", d.tex.name], paper_dir)
            logfile = paper_dir / (d.tex.stem + ".log")
            log = logfile.read_text(encoding="utf-8", errors="replace") \
                if logfile.exists() else ""
            fixed = False
            for name in _MISSING_RE.findall(log):
                for cand in (name, name + ".tex", name + ".pdf"):
                    src = repo / d.tex.parent / cand
                    if src.exists():
                        dst = paper_dir / cand
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                        borrowed.append(cand)
                        fixed = True
                        break
            if not fixed:
                break

    for d in docs:
        _run([BIBTEX, d.tex.stem], paper_dir)
    for _ in range(2):
        for d in docs:
            _run([XELATEX, "-interaction=nonstopmode", d.tex.name], paper_dir)

    for d in docs:
        logfile = paper_dir / (d.tex.stem + ".log")
        if logfile.exists():
            log = logfile.read_text(encoding="utf-8", errors="replace")
            d.errors = [ln.strip() for ln in log.splitlines()
                        if ln.startswith("!")][:10]
        if not d.pdf.exists():
            raise SystemExit(f"[{label}] {d.tex} produced no PDF; "
                             f"first errors: {d.errors}")
        d.pages = _page_count(d.pdf)
    return BuildResult(label, docs, sorted(set(borrowed)),
                       [str(s) for s in skipped])


def _in_rev(repo: Path, rev: str, path: Path) -> bool:
    """Does ``rev`` carry ``path``?  Used to skip a root the revision predates."""
    p = subprocess.run(["git", "cat-file", "-e", f"{rev}:{path}"],
                       cwd=str(repo), stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    return p.returncode == 0


def _page_count(pdf: Path) -> int:
    """Page count, for the report header only; refined later from the parse."""
    data = pdf.read_bytes()
    for tag, parent in ((b"/Type /Page", b"/Type /Pages"),
                        (b"/Type/Page", b"/Type/Pages")):
        n = data.count(tag) - data.count(parent)
        if n > 0:
            return n
    return 0


def read_pdf(pdf: Path, workdir: Path, label: str) -> list[Page]:
    xml = workdir / f"{label}.bbox.xml"
    proc = subprocess.run([PDFTOTEXT, "-q", "-bbox-layout", str(pdf), str(xml)],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
    if proc.returncode != 0 or not xml.exists():
        raise SystemExit(f"pdftotext failed on {pdf}: {proc.stdout}")
    return parse_bbox_layout(xml)


# --------------------------------------------------------------------------
# allowlist
# --------------------------------------------------------------------------


def load_allowlist(path: Path | None) -> dict[tuple[str, bool], str]:
    if path is None:
        return {}
    if not path.exists():
        raise SystemExit(f"allowlist not found: {path}")
    entries: dict[tuple[str, bool], str] = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        token = parts[0]
        reason = parts[1].strip() if len(parts) > 1 else ""
        if not reason:
            raise SystemExit(
                f"{path}:{lineno}: entry '{token}' has no reason. Every retired "
                f"number needs a one-line reason on the same line.")
        percent = token.endswith("%")
        body = token[:-1] if percent else token
        body = body.replace("−", "-")
        try:
            dec = Decimal(body)
        except InvalidOperation:
            raise SystemExit(f"{path}:{lineno}: '{token}' is not a number")
        entries[(_canon(dec), percent)] = reason
    return entries


# --------------------------------------------------------------------------
# comparison
# --------------------------------------------------------------------------


@dataclass
class LostOccurrence:
    """A baseline occurrence with no counterpart in the target."""
    occ: Occurrence
    best_score: float
    nearest_now: str | None          # the target sentence that replaced it
    nearest_score: float = 0.0

    @property
    def sentence_survived(self) -> bool:
        """The sentence is still in the document; only the number left it.

        This is the exact failure the script was written for -- a pass shortens
        a sentence and an interval goes with it -- so it sorts to the top.
        """
        return self.nearest_now is not None and self.nearest_score >= 0.55


@dataclass
class Finding:
    key: tuple[str, bool]
    shown: str
    printed_forms: list[str]
    base_count: int
    now_count: int
    entries: list[LostOccurrence]
    kept_pages: list[int]
    flags: tuple[str, ...]
    tier: str
    count_only: bool = False

    @property
    def worst(self) -> float:
        return min((e.best_score for e in self.entries), default=1.0)

    @property
    def sentence_survived(self) -> bool:
        return any(e.sentence_survived for e in self.entries)


MATCH_THRESHOLD = 0.60
PREFILTER_K = 12
# Above this multiplicity, pairing occurrences by context stops meaning
# anything -- a value printed a hundred times is a "0" or a "1" scattered
# through the mathematics, and any unmatched one is an artefact of rewording.
# Such values fall back to plain counting.
MATCH_MAX = 25


def _sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _score(b: Occurrence, t: Occurrence) -> float:
    """How strongly a target occurrence looks like the same printed statement.

    ``max`` of the immediate surroundings and the whole sentence, so a sentence
    that was merely rewritten around a surviving number still matches on its
    local neighbourhood, and a sentence that survived intact still matches even
    if the number moved within it.  Being generous here is deliberate: a missed
    match is a false alarm, and false alarms are what make a gate get ignored.
    """
    return max(_sim(b.local, t.local), _sim(b.context, t.context))


def _unmatched(base: list[Occurrence], now: list[Occurrence]
               ) -> list[tuple[Occurrence, float]]:
    """Baseline occurrences of one value with no counterpart among the target's.

    Occurrence-level, not count-level, and that is the whole point: when a pass
    deletes "[+0.48, +1.85]" from one sentence while some unrelated table gains
    another +0.48, the count is unchanged and only this comparison sees it.
    """
    if not now:
        return [(b, 0.0) for b in base]

    pairs: list[tuple[float, int, int]] = []
    for i, b in enumerate(base):
        rough = sorted(
            ((difflib.SequenceMatcher(None, b.local, t.local).quick_ratio(), j)
             for j, t in enumerate(now)), reverse=True)[:PREFILTER_K]
        for _, j in rough:
            pairs.append((_score(b, now[j]), i, j))
    pairs.sort(key=lambda t: -t[0])

    best: dict[int, float] = {}
    for s, i, _ in pairs:
        best[i] = max(best.get(i, 0.0), s)

    used_b: set[int] = set()
    used_n: set[int] = set()
    for s, i, j in pairs:
        if s < MATCH_THRESHOLD:
            break
        if i in used_b or j in used_n:
            continue
        used_b.add(i)
        used_n.add(j)
    return [(b, best.get(i, 0.0)) for i, b in enumerate(base) if i not in used_b]


def _by_count(base: list[Occurrence], now: list[Occurrence]
              ) -> list[tuple[Occurrence, float]]:
    """Count-only fallback for values printed too often to pair sensibly.

    Baseline occurrences are matched to target ones by an exact match of their
    immediate surroundings, and only the excess is reported -- so a value whose
    count did not drop yields nothing at all.
    """
    if len(base) <= len(now):
        return []
    pool = Counter(t.local for t in now)
    leftover: list[Occurrence] = []
    for o in base:
        if pool[o.local] > 0:
            pool[o.local] -= 1
        else:
            leftover.append(o)
    drop = len(base) - len(now)
    return [(o, 0.0) for o in (leftover or base)[:drop]]


class SentenceIndex:
    """Nearest surviving sentence, for showing what a lost number's claim became."""

    def __init__(self, sentences: Iterable[str]):
        self.sentences = [s for s in dict.fromkeys(sentences)]
        self.norm = [_normalise(s) for s in self.sentences]
        self.index: dict[str, list[int]] = defaultdict(list)
        for i, s in enumerate(self.norm):
            for tok in set(re.findall(r"[a-z]{5,}", s)):
                self.index[tok].append(i)

    def nearest(self, text: str) -> tuple[str, float] | None:
        norm = _normalise(text)
        hits: Counter = Counter()
        for tok in set(re.findall(r"[a-z]{5,}", norm)):
            bucket = self.index.get(tok, ())
            if len(bucket) > 120:            # too common to be informative
                continue
            hits.update(bucket)
        best, best_s = None, 0.0
        for i, _ in hits.most_common(25):
            s = _sim(norm, self.norm[i])
            if s > best_s:
                best, best_s = i, s
        return (self.sentences[best], best_s) if best is not None else None


def compare(base: Sequence[Occurrence], now: Sequence[Occurrence],
            now_index: SentenceIndex, max_contexts: int
            ) -> tuple[list[Finding], list[Finding]]:
    b_by: dict[tuple[str, bool], list[Occurrence]] = defaultdict(list)
    n_by: dict[tuple[str, bool], list[Occurrence]] = defaultdict(list)
    for o in base:
        b_by[o.key].append(o)
    for o in now:
        n_by[o.key].append(o)

    lost: list[Finding] = []
    for key, occ in b_by.items():
        cur = n_by.get(key, [])
        count_only = len(occ) > MATCH_MAX or len(cur) > MATCH_MAX
        gone = _by_count(occ, cur) if count_only else _unmatched(occ, cur)
        if not gone:
            continue
        entries = []
        for o, score in sorted(gone, key=lambda t: t[1])[:max_contexts]:
            near = now_index.nearest(o.context)
            entries.append(LostOccurrence(
                occ=o, best_score=score,
                nearest_now=near[0] if near and near[1] >= 0.55 else None,
                nearest_score=near[1] if near else 0.0))
        lost.append(Finding(
            key=key, shown=occ[0].shown,
            printed_forms=sorted({o.printed for o, _ in gone}),
            base_count=len(occ), now_count=len(cur), entries=entries,
            kept_pages=sorted({o.page for o in cur})[:8],
            flags=tuple(dict.fromkeys(f for o, _ in gone for f in o.flags)),
            tier=min((o.tier for o, _ in gone), key="ABF".index),
            count_only=count_only,
        ))

    gained: list[Finding] = []
    for key, occ in n_by.items():
        prev = b_by.get(key, [])
        if len(occ) <= len(prev):
            continue                      # only report numbers that multiplied
        new = (_by_count(occ, prev) if len(occ) > MATCH_MAX or len(prev) > MATCH_MAX
               else _unmatched(occ, prev))
        if not new:
            continue
        entries = [LostOccurrence(occ=o, best_score=s, nearest_now=None)
                   for o, s in sorted(new, key=lambda t: t[1])[:max_contexts]]
        gained.append(Finding(
            key=key, shown=occ[0].shown,
            printed_forms=sorted({o.printed for o, _ in new}),
            base_count=len(prev), now_count=len(occ), entries=entries,
            kept_pages=[],
            flags=tuple(dict.fromkeys(f for o, _ in new for f in o.flags)),
            tier=min((o.tier for o, _ in new), key="ABF".index),
        ))
    return lost, gained


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------


def _sort_key(f: Finding) -> tuple:
    """Most alarming first.

    A sentence that survived without its number outranks everything: that is
    the shortened-sentence failure this script exists to catch.  Then
    interval-shaped losses, then whatever had the least plausible counterpart.
    """
    return (0 if f.sentence_survived else 1,
            0 if f.flags else 1, f.worst, -len(f.entries), f.shown)


def _wrap(prefix: str, text: str, out: list[str], width: int = 96) -> None:
    import textwrap
    body = textwrap.wrap(text, width=width - len(prefix)) or [""]
    out.append(prefix + body[0])
    pad = " " * len(prefix)
    for line in body[1:]:
        out.append(pad + line)


def _render_group(title: str, findings: list[Finding], out: list[str],
                  show_kept: bool, side: str = "baseline") -> None:
    out.append("")
    out.append("=" * 78)
    out.append(f"{title}   [{len(findings)}]")
    out.append("=" * 78)
    if not findings:
        out.append("  (none)")
        return
    for f in sorted(findings, key=_sort_key):
        forms = ", ".join(f'"{p}"' for p in f.printed_forms[:4])
        marks = list(f.flags)
        if f.sentence_survived:
            marks.insert(0, "sentence survived, number did not")
        if f.count_only:
            marks.append("counted, not matched")
        flag = ("  <" + "; ".join(marks) + ">") if marks else ""
        out.append("")
        out.append(f"  {f.shown}   printed as {forms}   "
                   f"baseline x{f.base_count} -> target x{f.now_count}{flag}")
        for e in f.entries:
            _wrap(f"      {side} p.{e.occ.page}: ", e.occ.context, out)
            if e.nearest_now is not None:
                _wrap("        the target now reads: ", e.nearest_now, out)
            elif side == "baseline":
                out.append("        (no similar sentence found in the target"
                           f"; closest same-value context scored {e.best_score:.2f})")
        if show_kept and f.kept_pages:
            out.append("      the value is still printed on p. "
                       + ", ".join(str(p) for p in f.kept_pages))


def render(base_build: BuildResult, now_build: BuildResult,
           base_occ: Sequence[Occurrence], now_occ: Sequence[Occurrence],
           base_drop: Counter, now_drop: Counter,
           lost: list[Finding], gained: list[Finding],
           allow: dict[tuple[str, bool], str], args) -> tuple[str, int]:
    out: list[str] = []
    out.append("=" * 78)
    out.append("NUMBER-CONSERVATION REPORT  (compiled text, baseline vs target)")
    out.append("=" * 78)
    out.append(f"  baseline : {base_build.label}  ->  {base_build.pages} pages, "
               f"{len(base_occ)} numbers printed")
    out.append(f"  target   : {now_build.label}  ->  {now_build.pages} pages, "
               f"{len(now_occ)} numbers printed")
    # Which documents each revision is, and where each one's pages start in the
    # pooled numbering.  A revision may be one document or several; the numbers
    # are compared pooled, so this is how a reported page is traced to a file.
    for b in (base_build, now_build):
        if len(b.docs) > 1 or b.skipped:
            out.append(f"  {b.label} is {len(b.docs)} document(s):")
            for d in b.docs:
                out.append(f"      {str(d.tex):<38} pages "
                           f"{d.first_page}-{d.first_page + d.pages - 1}")
            for s in b.skipped:
                out.append(f"      {s:<38} not in this revision (skipped)")
    for b in (base_build, now_build):
        if b.borrowed:
            out.append("")
            out.append(f"  WARNING [{b.label}]: {len(b.borrowed)} file(s) had to be "
                       f"copied in from the working tree for this revision to build:")
            for name in b.borrowed:
                out.append(f"      {name}")
            out.append("      Their numbers count as this revision's own, so numbers "
                       "those files")
            out.append("      introduced cannot show up as gained.")
        if b.errors:
            out.append(f"  note [{b.label}]: LaTeX reported {len(b.errors)} error "
                       f"line(s), first: {b.errors[0][:88]}")

    out.append("")
    out.append("  numeric tokens excluded by rule (baseline / target):")
    for rule in sorted(set(base_drop) | set(now_drop)):
        out.append(f"      {rule:<24} {base_drop.get(rule, 0):>6} /"
                   f" {now_drop.get(rule, 0):>6}")
    tiers = Counter(o.tier for o in base_occ)
    out.append(f"  baseline tiers: A(measurement-like)={tiers['A']}  "
               f"B(bare integers)={tiers['B']}  F(figure text)={tiers['F']}")
    out.append("")
    out.append("  Read this as evidence, not as a verdict. A number may be gone "
               "because a claim")
    out.append("  was corrected or a restatement was deduplicated; the baseline "
               "sentence below")
    out.append("  is there so you can tell that from an accident.")

    allowed = [f for f in lost if f.key in allow]
    lost = [f for f in lost if f.key not in allow]

    a_gone = [f for f in lost if f.tier == "A" and f.now_count == 0]
    a_less = [f for f in lost if f.tier == "A" and f.now_count > 0]
    b_gone = [f for f in lost if f.tier == "B" and f.now_count == 0]
    b_less = [f for f in lost if f.tier == "B" and f.now_count > 0]
    f_any = [f for f in lost if f.tier == "F"]

    _render_group("1. TIER A -- GONE FROM THE DOCUMENT ENTIRELY "
                  "(the group that matters)", a_gone, out, False)
    _render_group("2. TIER A -- THIS STATEMENT NO LONGER PRINTS IT "
                  "(value survives elsewhere)", a_less, out, True)
    _render_group("3. TIER B -- BARE INTEGERS, GONE FROM THE DOCUMENT ENTIRELY",
                  b_gone, out, False)
    _render_group("4. TIER B -- BARE INTEGERS, STATEMENT NO LONGER PRINTS IT",
                  b_less, out, True)
    _render_group("5. FIGURE TEXT -- lost (regenerated figures churn here)",
                  f_any, out, True)

    g_a = [f for f in gained if f.tier == "A"]
    g_rest = [f for f in gained if f.tier != "A"]
    _render_group("6. GAINED -- tier-A numbers the target prints more often "
                  "than the baseline", g_a, out, False, side="target")
    _render_group("7. GAINED -- tier B / figure text", g_rest, out, False,
                  side="target")

    out.append("")
    out.append("=" * 78)
    out.append(f"ALLOWLISTED (deliberately retired)   [{len(allowed)}]")
    out.append("=" * 78)
    if not allowed:
        out.append("  (none)")
    for f in allowed:
        out.append(f"  {f.shown}  x{f.base_count} -> x{f.now_count}   "
                   f"reason: {allow[f.key]}")

    gating = list(a_gone) + list(a_less)
    if args.gate_integers:
        gating += b_gone + b_less
    out.append("")
    out.append("-" * 78)
    if gating:
        out.append(f"VERDICT: {len(gating)} value(s) lost an occurrence "
                   f"({len(a_gone)} no longer printed anywhere in the document). "
                   f"Read them.")
        status = 1
    else:
        out.append("VERDICT: no tier-A number lost an occurrence.")
        status = 0
    out.append("-" * 78)
    return "\n".join(out), status


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="check_number_conservation.py",
        description=("Report numbers the compiled manuscript printed at a "
                     "baseline revision and no longer prints. A report, not a "
                     "verdict: grouped by how alarming the loss is, with the "
                     "baseline sentence for every one."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("EXAMPLES\n--------\n")[-1],
    )
    p.add_argument("--baseline", default="HEAD", metavar="REV",
                   help="git revision to compare against (default: HEAD)")
    p.add_argument("--target", default=None, metavar="REV",
                   help="git revision to check; omit to check the working tree")
    p.add_argument("--tex", action="append", default=None, metavar="PATH",
                   help="manuscript root, repo-relative; repeatable, and the "
                        "numbers of all of them are pooled into one submission "
                        "before comparing. A root a revision does not have is "
                        "skipped and reported. Default: "
                        + " + ".join(DEFAULT_TEX))
    p.add_argument("--allowlist", default=None, metavar="FILE",
                   help="numbers deliberately retired; 'VALUE  one-line reason' per line")
    p.add_argument("--workdir", default=None, metavar="DIR",
                   help="scratch directory for the two builds (default: a temp dir)")
    p.add_argument("--reuse-build", action="store_true",
                   help="skip rebuilding when a PDF is already in the workdir")
    p.add_argument("--max-contexts", type=int, default=3, metavar="N",
                   help="baseline sentences to show per lost value (default: 3)")
    p.add_argument("--context-chars", type=int, default=260, metavar="N",
                   help="clip a context sentence to N characters (default: 260)")
    p.add_argument("--gate-integers", action="store_true",
                   help="let tier-B (bare integer) losses affect the exit status")
    p.add_argument("--report", default=None, metavar="FILE",
                   help="also write the report to FILE")
    p.add_argument("--quiet", action="store_true",
                   help="write only the verdict line to stdout")
    args = p.parse_args(argv)

    try:
        repo = Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True).strip())
    except subprocess.CalledProcessError:
        print("not inside a git repository", file=sys.stderr)
        return 2

    tex_rels = [Path(t) for t in (args.tex or DEFAULT_TEX)]
    if len({t.parent for t in tex_rels}) != 1:
        print("all --tex roots must sit in the same directory: they share a "
              "preamble, a .bib and each other's .aux", file=sys.stderr)
        return 2
    if args.target is None and not any((repo / t).exists() for t in tex_rels):
        print("no manuscript root found: "
              + ", ".join(str(repo / t) for t in tex_rels), file=sys.stderr)
        return 2

    try:
        allow = load_allowlist(Path(args.allowlist) if args.allowlist else None)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2

    workdir = Path(args.workdir) if args.workdir else \
        Path(tempfile.mkdtemp(prefix="numconserve-"))
    workdir.mkdir(parents=True, exist_ok=True)

    try:
        base_build = build(repo, args.baseline, tex_rels, workdir,
                           "baseline", args.reuse_build)
        now_build = build(repo, args.target, tex_rels, workdir,
                          "target", args.reuse_build)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2

    base_build.label = f"{args.baseline} ({_describe(repo, args.baseline)})"
    now_build.label = args.target or "working tree"

    def harvest(bres: BuildResult) -> tuple[list[Occurrence], Counter, list[str]]:
        """Pool one revision's documents into a single set of occurrences.

        Pages are renumbered continuously across the documents, in the order
        the roots were given, so that the report's page numbers address the
        submission rather than a file; the header records the boundaries.
        """
        occ: list[Occurrence] = []
        drop: Counter = Counter()
        sents: list[str] = []
        offset = 0
        side = "baseline" if bres is base_build else "target"
        for i, d in enumerate(bres.docs):
            pages = read_pdf(d.pdf, workdir, f"{side}-{i}-{d.tex.stem}")
            d.pages = len(pages) or d.pages
            d.first_page = offset + 1
            o, dr, se = extract_occurrences(pages, args.context_chars, offset)
            occ.extend(o)
            drop.update(dr)
            sents.extend(se)
            offset += d.pages
        bres.pages = offset
        return occ, drop, sents

    base_occ, base_drop, _ = harvest(base_build)
    now_occ, now_drop, now_sents = harvest(now_build)

    lost, gained = compare(base_occ, now_occ, SentenceIndex(now_sents),
                           args.max_contexts)

    text, status = render(base_build, now_build, base_occ, now_occ,
                          base_drop, now_drop, lost, gained, allow, args)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    if args.quiet:
        print(text.rsplit("-" * 78, 2)[-2].strip())
    else:
        print(text)
    print(f"\n(builds and extracted text kept in {workdir})", file=sys.stderr)
    return status


def _describe(repo: Path, rev: str | None) -> str:
    if rev is None:
        return "working tree"
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", rev],
                                       cwd=str(repo), text=True).strip()
    except subprocess.CalledProcessError:
        return rev


if __name__ == "__main__":
    sys.exit(main())
