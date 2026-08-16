#!/usr/bin/env python3
"""Mechanical guard on a prose rewrite: the words may move, the facts may not.

WHY THIS EXISTS. A style rewrite of this manuscript touches every sentence, and the one thing a
rewriter must not do is change what the sentences say. Reading a 28,000-word diff by eye to check
that is not a check. This compares an original LaTeX tree against a rewritten one on the things a
rewrite has no licence to move:

  * every NUMERAL, as a multiset. A number that appears three times must still appear three times.
  * every \\ref, \\eqref, \\cite key, as a multiset.
  * every \\label, as a set -- a lost label breaks a reference somewhere else.
  * every \\input path.
  * the section structure: the ordered list of \\section/\\subsection/\\paragraph titles.

It says nothing about whether the rewrite is good. It says only that it did not quietly drop a
citation, round a number differently, or delete a subsection.

    python scripts/analysis/check_rewrite_preserves_facts.py ORIGINAL_DIR REWRITE_DIR

Exit status is 0 when nothing moved and 1 otherwise, so it can gate a merge.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

NUMERAL = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)*(?![\w])")
REF = re.compile(r"\\(?:ref|eqref|autoref)\{([^}]*)\}")
CITE = re.compile(r"\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}")
LABEL = re.compile(r"\\label\{([^}]*)\}")
INPUT = re.compile(r"\\input\{([^}]*)\}")
HEADING = re.compile(r"\\(section|subsection|subsubsection|paragraph)\*?\{")


def strip_comments(text: str) -> str:
    """Drop comment lines and trailing comments, keeping escaped percent signs."""
    out = []
    for line in text.splitlines():
        s, esc = [], False
        for ch in line:
            if esc:
                s.append(ch)
                esc = False
                continue
            if ch == "\\":
                s.append(ch)
                esc = True
                continue
            if ch == "%":
                break
            s.append(ch)
        out.append("".join(s))
    return "\n".join(out)


def heading_titles(text: str) -> list[str]:
    """Ordered heading titles, brace-matched so nested braces do not truncate one."""
    titles = []
    for m in HEADING.finditer(text):
        i, depth, buf = m.end(), 1, []
        while i < len(text) and depth:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if not depth:
                    break
            buf.append(c)
            i += 1
        titles.append(re.sub(r"\s+", " ", "".join(buf)).strip())
    return titles


def collect(root: Path) -> dict:
    text = "\n".join(
        strip_comments(p.read_text(errors="replace"))
        for p in sorted(root.rglob("*.tex"))
    )
    keys = lambda rx: Counter(  # noqa: E731
        k.strip() for m in rx.findall(text) for k in m.split(","))
    return {
        "numerals": Counter(NUMERAL.findall(text)),
        "refs": keys(REF),
        "cites": keys(CITE),
        "labels": Counter(LABEL.findall(text)),
        "inputs": Counter(INPUT.findall(text)),
        "headings": heading_titles(text),
    }


def report(name: str, a: Counter, b: Counter, problems: list[str], show: int = 12) -> None:
    lost, gained = a - b, b - a
    if not lost and not gained:
        print(f"  ok    {name}: {sum(a.values())} occurrences, unchanged")
        return
    problems.append(name)
    print(f"  FAIL  {name}: {len(lost)} lost, {len(gained)} gained")
    for k, n in list(lost.items())[:show]:
        print(f"          lost   {k!r} x{n}")
    for k, n in list(gained.items())[:show]:
        print(f"          gained {k!r} x{n}")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    orig, new = collect(Path(sys.argv[1])), collect(Path(sys.argv[2]))
    print(f"original {sys.argv[1]}  ->  rewrite {sys.argv[2]}")
    problems: list[str] = []
    for key in ("numerals", "refs", "cites", "labels", "inputs"):
        report(key, orig[key], new[key], problems)

    if orig["headings"] == new["headings"]:
        print(f"  ok    headings: {len(orig['headings'])} in the same order")
    else:
        problems.append("headings")
        print(f"  FAIL  headings: {len(orig['headings'])} -> {len(new['headings'])}")
        for i, (a, b) in enumerate(zip(orig["headings"], new["headings"])):
            if a != b:
                print(f"          first divergence at {i}: {a!r} -> {b!r}")
                break

    print()
    if problems:
        print(f"VERDICT: the rewrite moved {', '.join(problems)}. A style pass may not.")
        return 1
    print("VERDICT: every numeral, reference, citation, label, input and heading is preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
