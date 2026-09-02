# Zenodo deposit: what goes in, and how to mint the DOI

The manuscript's Data-availability statement points at two things: this repository under the MIT
licence, and a Zenodo archive for what is too large for git. This file is the recipe for the
archive. Only the upload and the DOI minting need a Zenodo account; everything else is prepared.

## Why the archive is needed

The paper names the **instrument** as its contribution, and a referee who cannot obtain it cannot
assess it. That objection survived every round of internal review. The repository carries the code
and the small JSON artifacts; the archive carries the weights and the per-row predictions that
every reported number is computed from.

## What to upload

Do not maintain the list by hand. Build it:

```bash
python scripts/release/build_zenodo_bundle.py --dry-run   # the plan and the total size
python scripts/release/build_zenodo_bundle.py             # stage it under dist/zenodo
```

The analysis half of the deposit is **derived from `DEPOSITS.md`**, the file that maps every
printed claim to the artifact it was computed from; the weights and the processed split are named
explicitly in the script, each with the reason it is there. Today that comes to about **685 MB in
385 files**, well inside Zenodo's 50 GB per-record limit. `MANIFEST.sha256` and a `README.md`
describing the contents are written into the staging tree, so a reader can check a download rather
than trust its byte count.

**The hand-written table that used to live here was wrong, and that is why it is gone.** Written on
2026-07-27, it named `results/e5_sigma_grounding/seed_4{2,3,4}` — the three-seed family — as the
per-arm predictions to deposit. Every headline number in the manuscript had since moved to the
five-seed leak-free family in `results/e5_sigma_grounding_leakfree/`. Uploading from that table
would have archived arms the paper's numbers are not computed from, and a referee who downloaded
it would have found a different run behind the number. A list that has to be remembered rots; a
list derived from the claims does not.

**Do not upload** the raw solubility corpus or the VT-2005 profile database; the builder excludes
them by name. Both are third-party and the paper cites them instead. The **processed split** is a
different case and *is* deposited: it is derived from BigSolDB 2.0
([10.5281/zenodo.15094979](https://doi.org/10.5281/zenodo.15094979)), which is released under
CC-BY-4.0, so redistribution is permitted with attribution. The archive's description must
therefore credit BigSolDB, and the record's licence field must say that the split carries CC-BY-4.0
even though the code is MIT. The split cannot simply be regenerated instead: the seeded
`solute_scaffold` split is not stable across pipeline versions, so the files themselves are the
only way for a reader to land on the same rows.

## Metadata to enter

- **Title.** Same as the manuscript, with "— code and data" appended.
- **Authors.** N. L. Polomoshnov (ORCID 0009-0001-4342-8539; Lomonosov Moscow State University;
  V. N. Orekhovich Institute of Biomedical Chemistry); A. V. Rudik (V. N. Orekhovich Institute of
  Biomedical Chemistry).
- **Upload type.** Dataset. (Use *Software* instead only if the code is deposited here rather than
  linked to GitHub.)
- **Licence.** MIT for the code and the derived artifacts, matching `LICENSE` at the repository
  root, with the BigSolDB-derived split attributed under CC-BY-4.0 as above.
- **Related identifiers.** `isSupplementTo` the article DOI once ACS issues it, and
  `isSupplementedBy` / `isDerivedFrom` `https://github.com/doctawho42/tgnn-solv` at the frozen
  commit.
- **Version.** `v1.0.0`, matching the git tag cut for submission.
- **Funding.** Russian Science Foundation, project No. 25-25-00148,
  <https://rscf.ru/project/25-25-00148/>. Zenodo has an RSF funder entry; use it rather than free
  text so the grant is machine-readable. This line previously read "None", which the manuscript
  agreed with until the grant was added on 2026-09-03; the two records must not diverge again.

`.zenodo.json` at the repository root carries the machine-readable form of the above, and is what
the GitHub–Zenodo integration reads when a release is cut. `CITATION.cff` carries the same
identity for anyone citing the software directly.

## Order of operations

The commit hash and the DOI are mutually entangled, so the sequence matters:

1. Freeze the repository: `git tag -a v1.0.0 -m "submission to JCIM"` and push the tag.
2. Take the hash **that tag points at** and put it in the manuscript's `\pending[hash]`. This lands
   in a commit *after* the tag, which is correct and intended: the tag freezes the analysis code —
   the tree the reported numbers were produced from, which is what the sentence in the manuscript
   claims — and not the manuscript text.
3. Build the archive from that commit, upload, publish, and take the DOI.
4. Put the DOI in the manuscript's `\pending[Zenodo DOI]` sites.
5. Recompile, confirm no `\pending` remains, and only then submit.

## GitHub's Zenodo integration

Enabling the Zenodo–GitHub webhook and cutting a release mints a DOI automatically, which is the
least error-prone route for the code half. **It will not carry the archive this file describes.**
A release archives the git tree only — 22 MB, against the deposit's 685 MB — because the
checkpoints, the processed split and the bulk of `results/` are gitignored. The large files
therefore need a manual upload, either as extra files on the same record or as a second record.
If a second record is used, the manuscript's sentence must name the one that actually holds the
checkpoints and predictions, since that is what it promises a reader.
