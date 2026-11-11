#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard the two-document submission against silently broken cross-references.

WHY THIS EXISTS
---------------
Since 2026-08-02 the manuscript is two documents -- by default
``paper/learned_sigma_profile.tex`` (the article) and
``paper/learned_sigma_profile_si.tex`` (the Supporting Information); the retired
``grounding_paradox`` pair is checked with ``--retired`` -- and their
cross-references point from one into the other.  They resolve
through ``xr-hyper``, which reads the other document's ``.aux``.  That mechanism
has one failure mode and it is quiet: if the other ``.aux`` is missing or stale,
the reference prints ``??`` and LaTeX records

    LaTeX Warning: Reference `sec:si-repro' on page 7 undefined

as a WARNING.  ``xelatex`` still exits 0, ``make`` still succeeds, and a PDF full
of ``??`` is produced.  Building only one of the two documents from a clean
directory does exactly this.  So the exit status of the build is not evidence
that the submission is sound, and this script is what is.

WHAT IT CHECKS
--------------
  1. Both documents built, and both PDFs exist.
  2. Neither log carries an undefined reference or an undefined citation.
  3. Neither log carries a LaTeX error line.
  4. No ``??`` in the extracted text of either PDF (the belt to the log's braces:
     it catches a reference that was undefined on an earlier pass and whose
     warning a later pass no longer repeats).
  5. No label name is defined in BOTH documents.  ``\\externaldocument`` is used
     with an empty prefix, so the two label namespaces are merged; a name used
     twice would resolve to whichever was read last, silently and wrongly.
  6. Every deposited file the Supporting Information names is present.

Item 5 is the one that cannot be seen in a build at all: LaTeX does not warn when
an imported external label shadows a local one.

USAGE
-----
    python scripts/analysis/check_split_refs.py            # paper/, as built
    python scripts/analysis/check_split_refs.py --dir DIR  # some other build dir

Exit status 0 if everything above holds, 1 otherwise.  Needs the documents to
have been built already (``make'' in paper/); it does not build them itself, so
that it can be run on a build directory produced any way at all.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

#: ЖИВАЯ ПАРА. До 2026-11-11 здесь стояла отозванная `grounding_paradox`, так что
#: `make check` проверял документы, которые никто больше не правит, и о живой рукописи
#: молчал. Отозванная пара достаётся флагом `--retired` и остаётся проверяемой.
MAIN = "learned_sigma_profile"
SI = "learned_sigma_profile_si"
#: Файлы, которые отозванная пара кладёт рядом со своим SI. Живая пара депонирует через
#: репозиторий, названный в её разделе о доступности, и рядом с собой не несёт ничего,
#: поэтому по умолчанию список пуст.
DEPOSITED: list[str] = []
RETIRED = ("grounding_paradox", "grounding_paradox_si",
           ["si_tables/broad_idac_set_477.csv", "si_tables/vt2005_matched_set_60.csv"])

_UNDEF = re.compile(
    r"LaTeX Warning: (Reference|Citation) `([^']*)' on page (\S+) undefined")
_LABEL = re.compile(r"\\newlabel\{([^}]*)\}")
_PDFTOTEXT = "pdftotext"


def _log_findings(path: Path) -> tuple[list[str], list[str]]:
    """(errors, undefined) read out of a LaTeX log."""
    if not path.exists():
        return [f"no log: {path}"], []
    text = path.read_text(encoding="utf-8", errors="replace")
    errors = [ln.strip() for ln in text.splitlines() if ln.startswith("!")]
    undef = sorted({f"{kind} `{key}' (p. {page})"
                    for kind, key, page in _UNDEF.findall(text)})
    return errors, undef


def _labels(aux: Path) -> set[str]:
    if not aux.exists():
        return set()
    text = aux.read_text(encoding="utf-8", errors="replace")
    # @cref entries are hyperref/cleveref shadows of a real label, not labels.
    return {n for n in _LABEL.findall(text) if not n.endswith("@cref")}


def _question_marks(pdf: Path) -> int:
    """Count `??' in the PDF's extracted text; -1 if pdftotext is unavailable."""
    if not pdf.exists():
        return -1
    proc = subprocess.run([_PDFTOTEXT, "-q", str(pdf), "-"],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          text=True, errors="replace")
    if proc.returncode != 0:
        return -1
    return proc.stdout.count("??")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", default=None, metavar="DIR",
                   help="build directory (default: the paper/ beside this script)")
    p.add_argument("--main", default=MAIN, metavar="STEM",
                   help=f"article stem without .tex (default: {MAIN})")
    p.add_argument("--si", default=SI, metavar="STEM",
                   help=f"Supporting Information stem (default: {SI})")
    p.add_argument("--deposited", nargs="*", default=None, metavar="REL",
                   help="files that must sit beside the SI (default: none)")
    p.add_argument("--retired", action="store_true",
                   help="check the retired grounding_paradox pair instead of the live one")
    args = p.parse_args(argv)

    main_stem, si_stem = args.main, args.si
    deposited = DEPOSITED if args.deposited is None else list(args.deposited)
    if args.retired:
        main_stem, si_stem, deposited = RETIRED

    here = Path(__file__).resolve()
    paper = Path(args.dir) if args.dir else here.parents[2] / "paper"
    problems: list[str] = []
    notes: list[str] = []

    for stem in (main_stem, si_stem):
        pdf = paper / f"{stem}.pdf"
        if not pdf.exists():
            problems.append(f"{stem}.pdf was not built (run `make' in {paper})")
            continue
        errors, undef = _log_findings(paper / f"{stem}.log")
        for e in errors:
            problems.append(f"{stem}: LaTeX error: {e[:120]}")
        for u in undef:
            problems.append(f"{stem}: undefined {u}")
        qm = _question_marks(pdf)
        if qm > 0:
            problems.append(f"{stem}.pdf prints `??' {qm} time(s): a "
                            f"cross-reference did not resolve")
        elif qm < 0:
            notes.append(f"{stem}: pdftotext unavailable, `??' not checked")
        else:
            notes.append(f"{stem}: built, no undefined references, no `??'")

    a, b = _labels(paper / f"{main_stem}.aux"), _labels(paper / f"{si_stem}.aux")
    if a and b:
        clash = sorted(a & b)
        if clash:
            problems.append(
                "label name(s) defined in BOTH documents, which \\externaldocument "
                "with an empty prefix cannot tell apart: " + ", ".join(clash))
        else:
            notes.append(f"labels: {len(a)} in the article, {len(b)} in the SI, "
                         f"no name in both")

    for rel in deposited:
        if not (paper / rel).exists():
            problems.append(f"deposited file missing: paper/{rel}")
    if deposited and all((paper / r).exists() for r in deposited):
        notes.append(f"deposited with the SI: {', '.join(deposited)}")

    for n in notes:
        print(f"  ok   {n}")
    for pr in problems:
        print(f"  FAIL {pr}")
    print("-" * 72)
    if problems:
        print(f"VERDICT: {len(problems)} problem(s) in the split submission.")
        return 1
    print("VERDICT: both documents build, every cross-reference resolves, "
          "no label collides.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
