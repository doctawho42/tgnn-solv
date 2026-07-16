# Digital Discovery (RSC) submission checklist

Target journal: **Digital Discovery** (RSC), fully open-access, APC £2,200 (check waiver eligibility).
Panel verdict: one-cycle **major revision**, science sound — remaining work is packaging.

## Status of the manuscript now
- All referee content revisions (#2–#7) are done and committed; `grounding_paradox.tex` compiles clean (XeLaTeX).
- The four RSC-mandated end-matter sections are inserted **in the required order** with `\pending[...]` placeholders:
  Conclusion → **Author contributions** → **Conflicts of interest** → **Data availability** → **Acknowledgements** → references.
- `\pending[...]` renders as red bracketed text; search the source for `\pending` to find every blank (14 currently).

## What still needs YOUR information (fill the `\pending` blanks)
- [ ] **Author line + affiliation + corresponding email** (`\author{...}`, line ~64).
- [ ] **Co-author names + affiliations.**
- [ ] **Author contributions** — CRediT roles per author. Use only the 14 official role names
      (Conceptualization; Data curation; Formal analysis; Funding acquisition; Investigation; Methodology;
      Project administration; Resources; Software; Supervision; Validation; Visualization;
      Writing – original draft; Writing – review & editing).
- [ ] **Data availability** — repository name + **DOI-bearing URL** + commit hash + license (e.g. MIT for code, CC-BY-4.0 for data),
      and the **Zenodo DOI** for checkpoints + per-arm prediction files.
      *RSC rejects "available on request" as the sole statement — a persistent-identifier deposit is required for DD.*
- [ ] **Freeze the exact Bemis–Murcko scaffold split** into the deposit (the split is unstable across pipeline versions).
- [ ] **Acknowledgements** — all funding sources + grant numbers (also entered separately at submission via Crossref Funding Data),
      compute providers, and — per RSC policy — **any generative-AI-tool use** in preparing the manuscript.
- [ ] **Conflicts of interest** — keep "There are no conflicts to declare." only if true; otherwise state them.

## Mechanical format conversion (do on Overleaf, at the end)
There is **no `rsc.cls`** — the RSC "Paper" template is the standard `article` class configured by hand (pdfLaTeX, not XeLaTeX).

- [ ] **Preamble swap** → `\documentclass[8.5pt,twoside,twocolumn]{article}` (or `[twoside,twocolumn,9pt]{article}` + `extsizes`).
      Remove all `fontspec`/`polyglossia` (XeLaTeX-only) lines; add `\usepackage{times,mathptmx}`.
      Add the RSC stack: `natbib[super,sort&compress,comma]`, `mhchem`, `sectsty`, `balance`, `graphicx`, `lastpage`,
      the RSC `caption` setup, `fancyhdr`; plus `\renewcommand{\thefootnote}{\fnsymbol{footnote}}`,
      `\setcounter{secnumdepth}{5}`, `\sectionfont{\large}`, `\subsectionfont{\normalsize}`.
      **Compile with `pdflatex` + `bibtex`, not XeLaTeX.**
- [ ] **References** → copy `rsc.bst` into the project (not on CTAN); set `\bibliographystyle{rsc}`,
      `\renewcommand\refname{Notes and references}`, wrap the bibliography in `\footnotesize{...}`, `\setlength\bibsep{1pt}`.
      Keep the existing `references_verified.bib`; citations stay `\cite{...}` (now superscript numeric).
- [ ] **Title/author block** → delete `\title/\author/\date/\maketitle`; hand-build the
      `\twocolumn[\begin{@twocolumnfalse}...\end{@twocolumnfalse}]` block: `\LARGE` bold title (+ `$^\dag$` if ESI ships),
      `\large` bold author line with italic superscript affiliation letters and `$^{\ast}$` on the corresponding author,
      the fixed Received/Accepted line, the `\textbf{DOI: 10.1039/...}` line (do not edit its wording),
      then the abstract as a plain `\noindent\normalsize` paragraph (NOT an `abstract` environment).
- [ ] **Affiliation footnotes** → `\footnotetext{...}` (address + email + ESI dagger + equal-contribution) right after the first `\section`.
- [ ] **Copy** `headers/*.eps` RSC logo files into the project; add `\balance` in the last page's first column and `\pageref{LastPage}`.

## ESI (our SI) — becomes a SEPARATE file
- [ ] Split `sections/SI.tex` (+ its `\input`ed sub-sections) into a **standalone ESI `.tex`** with its own preamble
      and **its own reference list** (separate `\bibliography`).
- [ ] Renumber all SI floats with an **S prefix**: `\setcounter{figure}{0}\renewcommand{\thefigure}{S\arabic{figure}}`
      (and likewise table/equation). In-text: "Fig. S1, ESI†".
- [ ] Add a short **table of contents** at the top of the ESI; supply data in open formats where applicable.
- [ ] If ESI ships: add `$^\dag$` to the title and the `\footnotetext{\dag~Electronic Supplementary Information ...}` note.

## Final checks
- [ ] Translate any remaining Russian/Cyrillic (RSC is English-only).
- [ ] Run the **RSC Submission Checker** (submission-checker.rsc.org) before upload.
- [ ] Re-read the current DD author guidelines (statement wording is periodically updated).

## References
- DD author guidelines: https://www.rsc.org/publishing/publish-with-us/publish-a-journal-article/digital-discovery
- RSC article template (Overleaf): https://www.overleaf.com/latex/templates/royal-society-of-chemistry-article-template/vffpnxpmxdfz
- CRediT taxonomy: https://credit.niso.org/
