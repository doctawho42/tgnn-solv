# The public page

One hand-written HTML file, no build step and no generator, deployed to the `gh-pages` branch.

## Why it is shaped like this

The previous site was MkDocs: twenty-odd pages, auto-deployed from a commit in April, still live in
August describing a project that had since rebuilt its data split, repaired a systematic error in
its crystal labels and reversed one of its headline claims. Nobody noticed, because a generated
site regenerates only when someone remembers to regenerate it, and the cost of *checking* it was
twenty pages.

A single page costs one read to check. That is the whole design.

## Deploying

Automatically, by `.github/workflows/docs.yml`, on any push to `main` that touches `web/`, either
compiled PDF, or the workflow itself. Nothing to run by hand.

**This repository's Pages source is `build_type: workflow`.** Pushing to the `gh-pages` branch does
not publish anything — the workflow artifact is what gets served, and the branch is ignored. A
hand-rolled publisher that pushed to `gh-pages` was written first and was silently a no-op, which
is worth knowing before writing another one.

The workflow blocks on two things before it deploys: `scripts/analysis/check_site_abstract.py` must
find the manuscript's abstract on the page, and both PDFs must be present, since the page links
them by name and a 404 behind a link is worse than no link.

## How the old site failed, since it is the same trap twice

The previous workflow ran `mkdocs build` over a `docs/` tree. When that tree was deleted the
workflow started failing on every push — and **a failed Pages deploy does not take the site down.**
It leaves the last successful build serving. So the site went on publishing an April snapshot for
months while the repository moved past it, and the only symptom was a red tick nobody was looking
at.

## What to update, and when

- **at submission** — the Zenodo DOI, once registered.
- **if a headline claim changes** — the lede and the abstract, which are copied from
  `paper/grounding_paradox.tex` and must not drift from it.
- **never** — anything that duplicates `DEPOSITS.md`. The page links to it instead, because two
  copies of a mapping is one copy and one lie waiting to happen.
