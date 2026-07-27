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

| item | source | approx. size |
|---|---|---|
| trained checkpoints, current split | `checkpoints/e5_current_split/*.pt` | 3 x 22 MB |
| COSMO-SAC reference checkpoint | `checkpoints/cosmo_sac/tgnn_cosmo.pt` | 42 MB |
| closure-fix arm checkpoints | `results/closure_fix/ckpt/*.pt` | 2 x 21 MB |
| per-arm predictions, three seeds | `results/e5_sigma_grounding/seed_4{2,3,4}/*.csv` | ~60 MB |
| decomposition and robustness artifacts | `results/b_insuff/*.json` | < 1 MB |
| surrogate and compensation artifacts | `results/compensation/*.json`, `results/sur/` | < 1 MB |
| black-box probe artifacts | `results/blackbox/*` | < 1 MB |
| the matched sets | `results/b_insuff/matched_pairs.csv`, `results/sigma_profile_artifact/sigma_profiles.csv` | < 1 MB |

Total on the order of 200 MB, well inside Zenodo's 50 GB per-record limit.

**Do not upload** the raw solubility corpus or the VT-2005 profile database. Both are third-party
and redistributable only under their own terms; the paper cites them and the repository documents
how to fetch them.

## Metadata to enter

- **Title.** Same as the manuscript, with "— code and data" appended.
- **Authors.** N. L. Polomoshnov (ORCID 0009-0001-4342-8539; Lomonosov Moscow State University;
  V. N. Orekhovich Institute of Biomedical Chemistry); A. V. Rudik (V. N. Orekhovich Institute of
  Biomedical Chemistry).
- **Upload type.** Dataset. (Use *Software* instead only if the code is deposited here rather than
  linked to GitHub.)
- **Licence.** MIT, matching `LICENSE` at the repository root.
- **Related identifiers.** `isSupplementTo` the article DOI once ACS issues it, and
  `isSupplementedBy` / `isDerivedFrom` `https://github.com/doctawho42/tgnn-solv` at the frozen
  commit.
- **Version.** `v1.0.0`, matching the git tag cut for submission.
- **Funding.** None. The manuscript states no external funding, and the two records must agree.

## Order of operations

The commit hash and the DOI are mutually entangled, so the sequence matters:

1. Freeze the repository: `git tag -a v1.0.0 -m "submission to JCIM"` and push the tag.
2. Take the hash of that tag and put it in the manuscript's `\pending[hash]`.
3. Build the archive from **that** commit, upload, publish, and take the DOI.
4. Put the DOI in the manuscript's two `\pending[Zenodo DOI]` sites (main text and SI).
5. Recompile, confirm no `\pending` remains, and only then submit.

Step 4 changes the source after step 1's tag, which is expected: the tag freezes the *analysis*
code, not the manuscript text. If you would rather have one immutable object, cut a second tag
`v1.0.1` after step 4 and note in the archive description that it differs only in the DOI strings.

## GitHub's Zenodo integration

Enabling the Zenodo–GitHub webhook and cutting a release mints a DOI automatically, which is the
least error-prone route for the code half. It will not carry the checkpoints, since those are
gitignored, so the large files still need a manual upload — either as a second record or as extra
files on the same one.
