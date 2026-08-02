# Submission checklist

> **STALE IN PART, 2026-07-28.** The target journal changed after this file was written. The
> manuscript is now built for **J. Chem. Inf. Model.** with `achemso` (`journal=jcisd8`,
> `manuscript=article`, `layout=twocolumn`), compiled with **XeLaTeX**. Everything below under
> "Mechanical format conversion" and "ESI" describes the superseded RSC *Digital Discovery* route
> and applies only if the target reverts to it. The author-information items under "What still
> needs YOUR information" are live and unchanged.

Superseded target: **Digital Discovery** (RSC), fully open-access, APC £2,200 (check waiver eligibility).
Panel verdict: one-cycle **major revision**, science sound — remaining work is packaging.

## Status of the manuscript now
- **The submission is TWO documents since 2026-08-02**, which is what ACS deposits and what all
  three referees asked for. `paper/grounding_paradox.tex` is the article; `paper/grounding_paradox_si.tex`
  is the Supporting Information (`manuscript=suppinfo`, so pages S-1…, Tables S1…, Figures S1…,
  citations (S1)…, and sections S1… set in its own preamble). They share `paper/preamble.tex` and
  cross-reference each other through `xr-hyper`, so **both must be built, and each needs a pass after
  the other has written its `.aux`**: `make` (i.e. `make both`) in `paper/` does it. An undefined
  cross-reference is only a LaTeX *warning*, so the build's exit status does not prove the references
  resolved — run `make check` (`scripts/analysis/check_split_refs.py`), which fails on any undefined
  reference, any `??` in either PDF, and any label name defined in both documents.
- Both compile clean (XeLaTeX). Measured on the 2026-08-02 build: the article is 32 pages — main text
  1–28, back matter 28–29, References 29–32 — and the Supporting Information is 49, S-1 to S-46 of
  text plus References S-47 to S-49. No LaTeX errors, no undefined references. These counts move with
  every pass — read them off the build log, not off this line.
- `check_number_conservation.py` now builds **both** roots and pools their numbers before comparing,
  so a number that merely moved between the two documents does not read as a loss. Run it with its
  default `--tex` arguments; passing a single root compares the article against a baseline that
  contained the appendices and will report the whole Supporting Information as gone.
- The end-matter sections are inserted **in the required order** with `\pending[...]` placeholders:
  Conclusion → **Author contributions** → **Conflicts of interest** → **Data availability** → **Acknowledgements** → references.
- `\pending[...]` renders as red bracketed text; search the source for `\pending` to find every blank
  (**3** currently: the repository commit hash and the Zenodo DOI in Data availability, and the same
  Zenodo DOI in the SI compute ledger — these are limitation (x) of the Discussion).

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
- [x] Split `sections/SI.tex` (+ its `\input`ed sub-sections) into a **standalone ESI `.tex`** with its own preamble
      and **its own reference list** (separate `\bibliography`).
      *Done 2026-08-02 for the ACS route: `grounding_paradox_si.tex`. Under the RSC route the same
      wrapper needs its preamble converted with the article's, and `manuscript=suppinfo` replaced by
      the explicit S-counters below, which is what achemso was doing for it.*
- [x] Renumber all SI floats with an **S prefix**: `\setcounter{figure}{0}\renewcommand{\thefigure}{S\arabic{figure}}`
      (and likewise table/equation). In-text: "Fig. S1, ESI†".
      *Done: achemso's `manuscript=suppinfo` supplies figure/table/scheme/page/citation, and the
      wrapper adds section, subsection, equation and the theorem environments.*
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
