#!/usr/bin/env python
"""Every pointer the article aims at the Supporting Information, and every section it promises.

WHAT THIS CLOSES, AND WHY THE OTHER GATES DO NOT.  check_cross_document_attributions.py runs the
other way: it checks that a numeral the SI attributes to an article section still prints there.
Nothing checked the article -> SI direction, and that is the direction a relocation breaks.  On
2026-08-31 Sec. 2.1.2 moved into the SI, which pushed every SI subsection after it down by one
(S6.9 -> S6.10, S6.11 -> S6.12).  LaTeX renumbered both sides of every \\ref, so the compile was
clean -- but a hard-coded "S6.9" in prose would have been left pointing at the wrong section, in
silence, and a reader following it lands on the wrong page with no way to tell.

Four checks, and each is a class that compiles clean:

  1. HARD-CODED S-NUMBERS.  Any "\\S S6.9" or "Table~S12" written as literal text rather than as a
     \\ref.  These do not follow a renumbering.  There are none today; the check is what keeps that
     true, because writing one is easier than writing the \\ref.
  2. UNRESOLVED POINTERS.  Every \\ref in the article whose label lives in the SI must resolve
     through the SI's .aux.  A compile reports these too, but only as a warning among hundreds of
     lines, and only when the .aux is current.
  3. TYPE MISMATCH.  "\\S\\ref{tab:...}" sends a reader to a section for a table; "Table~\\ref{sec:...}"
     the other way.  The reference resolves, the number prints, and the noun is wrong.
  4. AN UNPROMISED SECTION.  The suppinfo note is the contents list a reader is given, and ACS asks
     for it as a brief description of what each file holds.  A top-level SI section that the note
     never mentions is material no reader is told exists.  PROMISED below maps every top-level SI
     section to the phrase that promises it; adding a section to the SI without adding it to the
     note fails here.

Usage
-----
    python scripts/analysis/check_supplement_pointers.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
ARTICLE_FILES = [PAPER / "grounding_paradox.tex", PAPER / "sections/methods.tex"]
SI_TEX = PAPER / "sections/SI.tex"
SI_AUX = PAPER / "grounding_paradox_si.aux"

#: top-level SI section label -> a phrase from the suppinfo note that promises it.  The phrase is
#: matched against the note with whitespace flattened, so it may be broken across lines there.
PROMISED = {
    "sec:si-methods":     "Supplementary methods",
    "sec:si-proofs":      "proofs of Lemma",
    "sec:si-tables":      "per-arm tables and decomposition robustness",
    "sec:si-baselines":   "further external ablations",
    "sec:si-mech":        "supplementary mechanism results",
    "sec:si-diagnostics": "supplementary diagnostics and broad negatives",
    "sec:si-pka":         "second-domain pKa construction",
    "sec:si-repro":       "data provenance and reproducibility",
    "sec:si-blackbox":    "black-box probe tables",
    "sec:dial":           "synthetic closure-fidelity family",
    "sec:si-positioning": "positioning against adjacent literatures",
}

#: label prefix -> what a pointer to it must be called in the running text
KIND = {"sec": "section", "app": "section", "tab": "table", "fig": "figure", "eq": "equation"}


def _uncommented(path: Path) -> str:
    return "\n".join(l for l in path.read_text(encoding="utf8").split("\n")
                     if not l.lstrip().startswith("%"))


def main() -> int:
    if not SI_AUX.exists():
        print(f"FAIL: {SI_AUX} is missing -- build the SI first (it is what xr reads)")
        return 1

    aux = SI_AUX.read_text(encoding="utf8", errors="ignore")
    si_num = {m.group(1): m.group(2)
              for m in re.finditer(r"\\newlabel\{([^}]+)\}\{\{([^}]*)\}\{", aux)}
    article = "\n".join(_uncommented(p) for p in ARTICLE_FILES)
    flat = re.sub(r"\s+", " ", article)
    bad: list[str] = []

    # 1 -- hard-coded S-numbers, in the article and in the SI's own prose
    literal = re.compile(r"(?<!\\)(?:§|\\S)\s*~?\s*S\d+(?:\.\d+)*"
                         r"|(?:Table|Figure|Fig\.|Eq\.)~?\s*S\d+(?:\.\d+)*")
    for path in ARTICLE_FILES + [SI_TEX]:
        for hit in sorted(set(literal.findall(_uncommented(path)))):
            bad.append(f"{path.name}: hard-coded {hit!r} -- write it as a \\ref, or a renumbering "
                       f"strands it")

    # 2 and 3 -- resolution and the noun each pointer is given
    si_labels = set(re.findall(r"\\label\{([^}]+)\}", _uncommented(SI_TEX)))
    n_pointers = 0
    for m in re.finditer(r"(\S{0,26})\\ref\{([^}]+)\}", flat):
        lead, label = m.group(1), m.group(2)
        if label not in si_labels:
            continue
        n_pointers += 1
        if label not in si_num:
            bad.append(f"article points at {label!r}, which the SI declares but does not resolve")
            continue
        kind = KIND.get(label.split(":")[0])
        low = lead.lower()
        called = ("section" if ("\\s" in low or "§" in lead) else
                  "table" if "table" in low else
                  "figure" if "fig" in low else
                  "equation" if "eq" in low else None)
        if kind and called and kind != called:
            bad.append(f"{label!r} is a {kind} but the article calls it a {called}: "
                       f"...{flat[max(0, m.start() - 60):m.end()]}")

    # 4 -- every top-level SI section is promised in the note
    note = re.search(r"\\begin\{suppinfo\}(.*?)\\end\{suppinfo\}",
                     _uncommented(ARTICLE_FILES[0]), re.S)
    if not note:
        bad.append("no suppinfo block in the article: the SI has no contents description at all")
    else:
        note_flat = re.sub(r"\s+", " ", note.group(1))
        for label, phrase in PROMISED.items():
            if phrase not in note_flat:
                bad.append(f"the suppinfo note does not promise {label!r} "
                           f"(looked for {phrase!r})")
    declared = set(re.findall(r"\\section\{[^}]*\}\s*(?:%[^\n]*\n\s*)*\\label\{([^}]+)\}",
                              SI_TEX.read_text(encoding="utf8")))
    top_level = {l for l in declared if si_num.get(l, "").count(".") == 0}
    for label in sorted(top_level - set(PROMISED)):
        bad.append(f"SI section {si_num.get(label, '?')} ({label}) is in neither PROMISED nor the "
                   f"note: a reader is never told it exists")

    print(f"article -> SI pointers checked: {n_pointers}")
    print(f"top-level SI sections promised in the note: {len(PROMISED)}")
    if bad:
        print(f"\nFAIL: {len(bad)} problem(s)\n")
        for b in bad:
            print(f"  {b}")
        return 1
    print("ok: every pointer resolves, is called by the right noun, and every SI section is promised")
    return 0


if __name__ == "__main__":
    sys.exit(main())
