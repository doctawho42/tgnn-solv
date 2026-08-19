#!/usr/bin/env python
"""Sentence-length and opening-word statistics for the article's RUNNING PROSE, by section.

WHY THIS EXISTS.  A readability claim about a LaTeX manuscript is only as good as what it counted.
Word counts taken off the whole file are dominated by tables, math, captions and preamble; counts
taken off the PDF re-join hyphenated line breaks and superscript footnote marks into the following
word.  Either way the number moves without the prose moving, which is exactly the failure this
project has already had once with stale values in running prose.

WHAT IS COUNTED
---------------
Running prose only: the body text of \\section/\\subsection/\\paragraph blocks, after removing
comments, display math, tabular/table/figure/tikz environments, captions, itemize labels and the
preamble.  Inline math is collapsed to a single token (a formula is one thing a reader takes in,
not seven), \\cite/\\ref to nothing, and macro names to their expansion where it is a word.

WHAT IS REPORTED, per section and overall
-----------------------------------------
  mean sentence length          the headline
  share of sentences > 40 words the tail that makes a paragraph hard to hold
  abstraction openers           sentences beginning What/That/Where/Which/Whether/Why -- a
                                nominal clause standing in for the thing's name
  "the one ..." per 1000 words  the same evasion in the middle of a sentence
  private vocabulary            arm/cell/row set/stratum/convention/admissible/deposit per 1000

Usage
-----
    python scripts/analysis/measure_prose_readability.py
    python scripts/analysis/measure_prose_readability.py --list-long   # every sentence > 40 words
    python scripts/analysis/measure_prose_readability.py --list-openers
    python scripts/analysis/measure_prose_readability.py --rev HEAD~6  # the same file at a revision
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
MAIN = "grounding_paradox.tex"

#: environments whose contents are not running prose
DROP_ENVS = ("equation", "equation*", "align", "align*", "gather", "gather*", "eqnarray",
             "multline", "multline*", "split", "table", "table*", "tabular", "tabularx",
             "figure", "figure*", "tikzpicture", "verbatim", "lstlisting", "abstract",
             "tcolorbox", "longtable", "threeparttable", "center", "adjustbox")
OPENERS = ("What", "That", "Where", "Which", "Whether", "Why")
PRIVATE = ("arm", "arms", "cell", "cells", "row set", "row sets", "stratum", "strata",
           "convention", "conventions", "admissible", "deposit", "deposits")
#: things that end in a period and are not the end of a sentence
NOT_END = (r"e\.g", r"i\.e", r"cf", r"vs", r"et al", r"Fig", r"Eq", r"Eqs", r"Sec", r"Tab",
           r"Ref", r"Refs", r"approx", r"resp", r"Dr", r"Prof", r"St", r"No", r"al")


def read(rel: str, rev: str | None) -> str:
    if rev is None:
        return (PAPER / rel).read_text()
    out = subprocess.run(["git", "show", f"{rev}:paper/{rel}"], cwd=ROOT,
                         capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else ""


def strip_comments(text: str) -> str:
    out = []
    for line in text.split("\n"):
        i, esc = 0, False
        cut = None
        while i < len(line):
            if line[i] == "\\":
                esc = not esc
            elif line[i] == "%" and not esc:
                cut = i
                break
            else:
                esc = False
            i += 1
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


def strip_envs(text: str) -> str:
    for env in DROP_ENVS:
        text = re.sub(r"\\begin\{" + re.escape(env) + r"\}.*?\\end\{" + re.escape(env) + r"\}",
                      " ", text, flags=re.S)
    return text


def clean(text: str) -> str:
    # RUN-IN HEADINGS ARE TITLES, NOT SENTENCES.  \paragraph{What the departure is, and what it is
    # not.} reads as an abstraction-opening sentence to any splitter and is not one; counting them
    # put six phantom openers in Sec. 3.3 alone.  Heading style is a separate question.
    text = re.sub(r"\\(sub)?paragraph\*?\{[^{}]*\}", " ", text)
    text = re.sub(r"\\\[.*?\\\]", " MATH ", text, flags=re.S)
    text = re.sub(r"(?<!\\)\$\$.*?\$\$", " MATH ", text, flags=re.S)
    text = re.sub(r"(?<!\\)\$[^$]*\$", "MATH", text)
    text = re.sub(r"\\(cite[a-zA-Z]*|ref|eqref|label|nocite)\s*(\[[^\]]*\])?\{[^}]*\}", "", text)
    text = re.sub(r"\\(footnote|marginpar)\{", " (", text)
    text = re.sub(r"\\(emph|textit|textbf|texttt|mbox|text)\{([^{}]*)\}", r"\2", text)
    text = re.sub(r"\\(begin|end)\{[^{}]*\}(\[[^\]]*\])?(\{[^{}]*\})*", " ", text)
    text = re.sub(r"\\S(?![a-zA-Z])", "SECT", text)
    text = re.sub(r"\\item\b", " ", text)
    text = re.sub(r"\\[a-zA-Z@]+\s*(\[[^\]]*\])?", " ", text)   # remaining macros
    text = text.replace("---", " ").replace("--", " ").replace("~", " ")
    text = re.sub(r"[{}]", " ", text)
    return re.sub(r"[ \t]+", " ", text)


def split_sentences(text: str) -> list[str]:
    guard = re.compile(r"\b(" + "|".join(NOT_END) + r")\.")
    text = guard.sub(lambda m: m.group(1) + "\x00", text)
    text = re.sub(r"(?<=\d)\.(?=\d)", "\x00", text)
    parts = re.split(r"(?<=[.!?])[\"')\]]*\s+", text)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


def words(s: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9'\u2019/-]*", s) if w]


class Section:
    def __init__(self, name: str, kind: str, number: str):
        self.name, self.kind, self.number = name, kind, number
        self.chunks: list[tuple[str, str, int]] = []   # (text, file, line)

    def sentences(self):
        out = []
        for text, f, ln in self.chunks:
            for s in split_sentences(text):
                out.append((s, f, ln))
        return out


def collect(rev: str | None) -> list[Section]:
    sections: list[Section] = []
    counters = [0, 0, 0]
    cur = Section("(front matter)", "front", "0")
    sections.append(cur)

    def walk(rel: str):
        nonlocal cur
        raw = strip_comments(read(rel, rev))
        # \input expansion, line-accurate for the top level
        lines = raw.split("\n")
        buf: list[str] = []
        start = 1
        depth = 0
        for i, line in enumerate(lines, 1):
            for b in re.findall(r"\\begin\{([a-zA-Z*]+)\}", line):
                depth += b in DROP_ENVS
            closing = [e for e in re.findall(r"\\end\{([a-zA-Z*]+)\}", line) if e in DROP_ENVS]
            if depth:
                depth -= len(closing)
                continue
            m = re.match(r"\s*\\input\{([^}]*)\}", line)
            if m:
                cur.chunks.append((clean(strip_envs("\n".join(buf))), rel, start))
                buf, start = [], i + 1
                sub = m.group(1)
                walk(sub if sub.endswith(".tex") else sub + ".tex")
                continue
            h = re.match(r"\s*\\(section|subsection|subsubsection)\*?\{(.*)\}\s*$", line)
            if h:
                cur.chunks.append((clean(strip_envs("\n".join(buf))), rel, start))
                buf, start = [], i + 1
                kind = h.group(1)
                lvl = {"section": 0, "subsection": 1, "subsubsection": 2}[kind]
                counters[lvl] += 1
                for k in range(lvl + 1, 3):
                    counters[k] = 0
                num = ".".join(str(c) for c in counters[:lvl + 1])
                cur = Section(re.sub(r"\\[a-zA-Z]+|[{}$]", "", h.group(2)).strip(), kind, num)
                sections.append(cur)
                continue
            buf.append(line)
        cur.chunks.append((clean(strip_envs("\n".join(buf))), rel, start))

    walk(MAIN)
    return sections


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rev", default=None, help="measure the file as of a git revision")
    ap.add_argument("--long", type=int, default=40)
    ap.add_argument("--min-words", type=int, default=4,
                    help="below this a 'sentence' is a fragment left by a stripped environment")
    ap.add_argument("--list-long", action="store_true")
    ap.add_argument("--list-openers", action="store_true")
    ap.add_argument("--only", default=None, help="restrict to section numbers with this prefix")
    a = ap.parse_args()

    sections = collect(a.rev)
    if a.only:
        sections = [s for s in sections
                    if s.number == a.only or s.number.startswith(a.only + ".")]

    print(f"{'sec':>6}  {'sentences':>9} {'words':>7} {'mean':>6} {f'>{a.long}w':>7} "
          f"{'openers':>8}   title")
    tot_s, tot_w, tot_long, tot_open = 0, 0, 0, 0
    long_all, open_all = [], []
    for sec in sections:
        sents = [(s, f, ln) for s, f, ln in sec.sentences() if len(words(s)) >= a.min_words]
        if not sents:
            continue
        lens = [len(words(s)) for s, _, _ in sents]
        longs = [(s, f, ln) for (s, f, ln), n in zip(sents, lens) if n > a.long]
        opens = [(s, f, ln) for s, f, ln in sents
                 if re.match(r"(" + "|".join(OPENERS) + r")\b", s)]
        long_all += [(sec.number, s, f, ln) for s, f, ln in longs]
        open_all += [(sec.number, s, f, ln) for s, f, ln in opens]
        tot_s += len(sents)
        tot_w += sum(lens)
        tot_long += len(longs)
        tot_open += len(opens)
        print(f"{sec.number:>6}  {len(sents):>9} {sum(lens):>7} {sum(lens) / len(lens):>6.1f} "
              f"{100 * len(longs) / len(sents):>6.0f}% {100 * len(opens) / len(sents):>7.0f}%   "
              f"{sec.name[:52]}")
    print(f"\n{'ALL':>6}  {tot_s:>9} {tot_w:>7} {tot_w / max(tot_s, 1):>6.1f} "
          f"{100 * tot_long / max(tot_s, 1):>6.0f}% {100 * tot_open / max(tot_s, 1):>7.0f}%")
    print(f"\n{tot_long} sentences over {a.long} words; {tot_open} opening on an abstraction")

    body = " ".join(s for _, s, _, _ in [(0, x, 0, 0) for sec in sections
                                         for x, _, _ in sec.sentences()])
    nw = max(len(words(body)), 1)
    per_k = 1000.0 / nw
    the_one = len(re.findall(r"\bthe one\b", body))
    priv = sum(len(re.findall(r"\b" + p + r"\b", body)) for p in PRIVATE)
    print(f"'the one ...'          {the_one * per_k:.1f} /1000 words")
    print(f"private vocabulary     {priv * per_k:.1f} /1000 words")

    if a.list_long:
        print(f"\n{'=' * 100}\nSENTENCES OVER {a.long} WORDS\n{'=' * 100}")
        for num, s, f, ln in long_all:
            print(f"\n[{num}] {f}:~{ln}  ({len(words(s))} words)\n  {s}")
    if a.list_openers:
        print(f"\n{'=' * 100}\nABSTRACTION OPENERS\n{'=' * 100}")
        for num, s, f, ln in open_all:
            print(f"\n[{num}] {f}:~{ln}  ({len(words(s))} words)\n  {s}")


if __name__ == "__main__":
    main()
