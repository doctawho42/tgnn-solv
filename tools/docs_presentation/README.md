# Docs Presentation Build

This directory contains the React source for the interactive presentation mounted
on `docs/presentation.md`.

The presentation is a small React application rather than a static image dump.
It includes:

- slide-local interaction and speaker-style notes
- TeX rendering
- RDKit-backed molecule depictions and graph views where applicable
- build-time data injection from repository artifacts

The source of truth lives under `src/`. Generated assets are committed under
`docs/assets/` because MkDocs serves them directly.

## Rebuild

```bash
cd tools/docs_presentation
npm install
npm run build
```

Generated assets are written to:

- `docs/assets/javascripts/tgnn-presentation.bundle.js`
- `docs/assets/stylesheets/tgnn-presentation.css`

If benchmark summaries or processed-data-derived counts changed, rebuild before
running `mkdocs build` so the published site and the presentation stay in sync.
