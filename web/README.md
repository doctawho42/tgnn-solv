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

```bash
scripts/publish_site.sh          # shows what would change
scripts/publish_site.sh --push   # publishes
```

The script copies `web/index.html` and the two compiled PDFs onto the `gh-pages` branch. Build the
PDFs first (`./verify.sh` does, among other things) — the script refuses to publish a page whose
PDF links would 404.

## What to update, and when

- **at submission** — the Zenodo DOI, once registered.
- **if a headline claim changes** — the lede and the abstract, which are copied from
  `paper/grounding_paradox.tex` and must not drift from it.
- **never** — anything that duplicates `DEPOSITS.md`. The page links to it instead, because two
  copies of a mapping is one copy and one lie waiting to happen.
