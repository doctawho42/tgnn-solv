#!/usr/bin/env python
"""Build the ACS submission package: one self-contained .tex, its .bib, its figures, zipped.

WHAT THIS EXISTS TO PREVENT.  The article gets its Supporting Information numbers through
`xr-hyper`, which reads `grounding_paradox_si.aux` **at compile time**.  That file is a build
product of a document ACS never receives: the SI is uploaded as a PDF.  Compile the manuscript on
their system and every cross-document reference silently becomes `??` -- ninety-five of them, in a
paper whose argument leans on pointing at the SI for the evidence.  Nothing warns you, because on
the author's own machine the .aux is always sitting there.

So the submitted file carries the SI's labels FROZEN into its preamble as `\\newlabel`
declarations, harvested from that .aux, and does not load xr-hyper at all.  It compiles standalone
and prints the same numbers.

The rest follows ACS's LaTeX guidelines, which ask for one file with everything in it:

  * `\\input{preamble}` and `\\input{sections/methods}` are inlined -- "Include all sections of the
    article in a single file".
  * The fifteen no-argument notation macros are expanded and their definitions dropped -- "Avoid
    extensive use of \\newcommand".  The three that take arguments stay; three is not extensive.
  * Figures are flattened out of `figs/` and referenced by bare filename, so the archive unpacks
    into one directory.
  * The `.bbl` ships beside the `.bib`, so the reference list typesets without running BibTeX.

THE BUILD IS NOT TRUSTED, IT IS CHECKED.  The package is compiled in an empty temporary directory
containing nothing but its own contents -- no SI, no repository, no aux files -- and the text of
the resulting PDF is compared against the reference build page for page.  A mismatch fails the
build and prints the first difference.  That comparison is the whole warrant for the macro
expansion and the frozen labels being harmless.

    python scripts/release/build_acs_submission.py
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
ARTICLE = PAPER / "grounding_paradox.tex"
SI_AUX = PAPER / "grounding_paradox_si.aux"
REFERENCE_PDF = PAPER / "grounding_paradox.pdf"

#: Notation macros with no arguments: expanded into the text, definitions dropped.  Longest name
#: first at substitution time, or \lng eats the head of \lngi.
EXPAND = ["lnx", "Phicry", "lngi", "lng", "Tm", "dHfus", "Rgas", "zstar", "Bclos", "Binsuf",
          "Ex", "Var", "Ggap", "hammett", "pmsd"]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf8")


def _inline_inputs(text: str) -> str:
    """Replace \\input{x} with the contents of x.tex, once, for the two files the article uses."""
    def sub(m: re.Match) -> str:
        name = m.group(1)
        src = PAPER / (name if name.endswith(".tex") else name + ".tex")
        if not src.exists():
            raise SystemExit(f"\\input{{{name}}} names a file that does not exist: {src}")
        body = _read(src)
        return (f"%% ---- inlined from {src.relative_to(PAPER)} "
                f"(ACS asks for a single file) ----\n{body}\n"
                f"%% ---- end {src.relative_to(PAPER)} ----\n")
    return re.sub(r"^\\input\{([^}]+)\}\s*$", sub, text, flags=re.M)


def _freeze_si_labels(text: str) -> tuple[str, int]:
    """Drop xr-hyper and carry the SI's labels in as literal \\newlabel declarations."""
    if not SI_AUX.exists():
        raise SystemExit(f"{SI_AUX} is missing -- build the SI first; its labels are the input here")
    aux = SI_AUX.read_text(encoding="utf8", errors="ignore")
    labels = re.findall(r"^\\newlabel\{[^}]+\}\{.*\}$", aux, flags=re.M)
    # NO \nocite HERE, and the reason is a misreading worth recording.  The article writes
    # \externaldocument[][nocite]{grounding_paradox_si}, which looks like it imports the SI's
    # citations.  It does not: xr-hyper's second optional argument is a URL for the hyperlinks,
    # so "nocite" is being passed as a URL and the citation lists of the two documents are
    # independent.  Adding the SI's 42 keys here put 42 undefined citations into the package,
    # because the article's .bbl has no entries for works only the SI cites.

    block = [
        "%% ---- Supporting Information cross-references, frozen -------------------------------",
        "%% The SI is submitted as a PDF, so its .aux is not available at compile time and",
        "%% xr-hyper cannot be used here.  These are its labels as of the build named in the",
        "%% manuscript's Data and Software Availability statement.  Regenerate with",
        "%% scripts/release/build_acs_submission.py rather than editing by hand.",
        "\\makeatletter",
        *labels,
        "\\makeatother",
        "%% ---- end frozen cross-references ---------------------------------------------------",
    ]
    text = re.sub(r"^\\usepackage\{xr-hyper\}\s*$", "", text, flags=re.M)
    frozen = "\n".join(l for l in block if l)
    # lambda, not a string: the replacement is full of backslashes and re reads \m as an escape
    text, n = re.subn(r"^\\externaldocument(?:\[[^]]*\])*\{[^}]+\}\s*$",
                      lambda _m: frozen, text, flags=re.M)
    if n != 1:
        raise SystemExit(f"expected exactly one \\externaldocument, found {n}")
    return text, len(labels)


def _expand_macros(text: str) -> tuple[str, int]:
    """Substitute the no-argument notation macros. NOT USED -- kept for the record of why not.

    ACS asks authors to avoid extensive use of \\newcommand, so this expanded the fifteen
    no-argument notation macros into the text.  It cannot be done safely, and the isolated-build
    comparison is what proved it rather than an opinion:

      * Bare substitution breaks argument grabbing.  The source writes \\tfrac1\\Tm and means
        \\tfrac{1}{\\Tm}, because a control word is a single token; substituting the body turns it
        into \\tfrac{1}{\\ensuremath} plus a stray group.  A hundred errors from one macro.
      * Braced substitution fixes that and breaks the typesetting instead.  2\\Binsuf^{\\mathrm{up}}
        becomes 2{B_{insuff}}^{up}, and the superscript now sits on the group rather than on the
        B, so the formula renders differently.  The text comparison caught it at line 379.

    Fifteen notation macros is not "extensive use" on any fair reading, and matching the reference
    build matters more than the macro count.  The manuscript ships with its macros intact.
    """
    bodies: dict[str, str] = {}
    for name in EXPAND:
        m = re.search(r"\\newcommand\{\\" + name + r"\}\{(.*)\}\s*$", text, flags=re.M)
        if not m:
            raise SystemExit(f"macro \\{name} has no single-line definition to expand")
        bodies[name] = m.group(1)
        text = text.replace(m.group(0), f"%% \\{name} expanded in place for submission")
    # BRACED, ALWAYS.  A control word is one token, so the source writes \tfrac1\Tm and means
    # \tfrac{1}{\Tm}.  Substituting the body bare turns that into \tfrac1\ensuremath{T_m},
    # which TeX reads as \tfrac{1}{\ensuremath} followed by a stray group -- a hundred errors
    # from one expansion.  Wrapping the body in a group keeps it a single argument everywhere.
    # Longest name first: \lng must not eat the head of \lngi.
    for name in sorted(bodies, key=len, reverse=True):
        body = "{" + bodies[name] + "}"
        text = re.sub(r"\\" + name + r"(?![A-Za-z])\s?", lambda _m, b=body: b, text)
    return text, len(bodies)


def _figures(text: str) -> list[str]:
    return sorted({m for m in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", text)})


def _compile_and_compare(stage: Path, tex_name: str) -> None:
    """Compile in isolation and require the text to match the reference build exactly."""
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        for f in stage.iterdir():
            shutil.copy2(f, work / f.name)
        for _ in range(3):
            subprocess.run(["xelatex", "-interaction=nonstopmode", tex_name],
                           cwd=work, capture_output=True)
        out = work / (tex_name.replace(".tex", ".pdf"))
        if not out.exists():
            log = (work / tex_name.replace(".tex", ".log")).read_text(errors="ignore")
            print("\n".join(l for l in log.splitlines() if l.startswith("!"))[:2000])
            raise SystemExit("FAIL: the package does not compile on its own")
        log = (work / tex_name.replace(".tex", ".log")).read_text(errors="ignore")
        undefined = len(re.findall(r"undefined on input", log))
        pages = re.search(r"Output written on \S+ \((\d+) pages", log)
        print(f"  standalone compile: {pages.group(1) if pages else '?'} pages, "
              f"{undefined} undefined references")
        if undefined:
            for m in sorted(set(re.findall(r"Reference `([^']+)' on page", log)))[:10]:
                print(f"      undefined: {m}")
            raise SystemExit("FAIL: references break when the package is compiled on its own")

        got = subprocess.run(["pdftotext", str(out), "-"], capture_output=True, text=True).stdout
        want = subprocess.run(["pdftotext", str(REFERENCE_PDF), "-"],
                              capture_output=True, text=True).stdout
        norm = lambda s: [l.strip() for l in s.split("\n") if l.strip()]
        g, w = norm(got), norm(want)
        if g != w:
            print(f"  FAIL: text differs from the reference build ({len(g)} vs {len(w)} lines)")
            for i, (a, b) in enumerate(zip(g, w)):
                if a != b:
                    print(f"      first difference at line {i}:")
                    print(f"        package  : {a[:100]}")
                    print(f"        reference: {b[:100]}")
                    break
            raise SystemExit(1)
        print(f"  text identical to the reference build ({len(g)} lines)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "dist/acs_submission")
    args = ap.parse_args()

    text = _read(ARTICLE)
    text = _inline_inputs(text)
    text, n_labels = _freeze_si_labels(text)
    # NOT EXPANDED, and the check is why.  See _expand_macros' docstring.
    n_macros = 0

    figs = _figures(text)
    for f in figs:
        text = text.replace("{" + f + "}", "{" + Path(f).name + "}")

    stage = args.out
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    tex_name = "grounding_paradox.tex"
    (stage / tex_name).write_text(text, encoding="utf8")
    for f in figs:
        shutil.copy2(PAPER / f, stage / Path(f).name)
    for extra in ("references_verified.bib", "grounding_paradox.bbl"):
        src = PAPER / extra
        if not src.exists():
            raise SystemExit(f"{extra} is missing -- run bibtex on the article first")
        shutil.copy2(src, stage / extra)

    print(f"staged {stage}")
    print(f"  {tex_name}: one file, {len(text.splitlines())} lines")
    print(f"  SI labels frozen in: {n_labels}")
    print(f"  notation macros: kept ({n_macros} expanded) -- expansion changes the "
          f"typesetting, see _expand_macros")
    print(f"  figures: {len(figs)} ({', '.join(Path(f).name for f in figs)})")
    print(f"  bibliography: references_verified.bib + grounding_paradox.bbl")

    _compile_and_compare(stage, tex_name)

    zip_path = stage.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(stage.iterdir()):
            if f.suffix in {".aux", ".log", ".out", ".pdf"} and f.name != tex_name:
                if f.suffix != ".pdf" or f.name not in {Path(x).name for x in figs}:
                    continue
            z.write(f, f.name)
    names = zipfile.ZipFile(zip_path).namelist()
    print(f"\nwrote {zip_path}  ({zip_path.stat().st_size/1e6:.1f} MB, {len(names)} files)")
    for n in sorted(names):
        print(f"    {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
