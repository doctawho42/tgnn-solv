# Submitting to J. Chem. Inf. Model.

Four uploads, one form. Build the two that are build products first:

```bash
python scripts/release/build_acs_submission.py   # the LaTeX package, and checks it
cd paper && xelatex cover_letter.tex             # the cover letter PDF
```

| ACS file designation | what to upload | where it comes from |
|---|---|---|
| Manuscript File | `dist/acs_submission.zip` | `build_acs_submission.py` |
| Manuscript PDF File | `paper/grounding_paradox.pdf` | `./verify.sh` builds it |
| Supporting Information | `paper/grounding_paradox_si.pdf` | same |
| Cover Letter | `paper/cover_letter.pdf` | `paper/cover_letter.tex` |

JCIM also asks for its own *Submission Cover Letter and Author Checklist* form, uploaded in lieu of
a free-form letter. The text for its free-text fields is Part 2 of `paper/cover_letter.md`; Part 3
of that file is the list of things only the authors can settle, and none of this should go up
before that list is closed.

## The one thing that would break silently

The manuscript reads its Supporting Information numbers through `xr-hyper`, which loads
`grounding_paradox_si.aux` **at compile time**. ACS never receives that file: the SI goes up as a
PDF. Compiled on their system the manuscript would print `??` for ninety-five cross-references,
with no error and no warning, in a paper that leans on pointing at the SI for its evidence.

`build_acs_submission.py` freezes the SI's labels into the submitted file's preamble and drops
xr-hyper, then proves the result: it compiles the package in an empty directory holding nothing but
the package's own contents and requires the extracted text to match the reference build line for
line. Two things were caught that way and are worth knowing about before anyone "tidies" the
script:

- **Expanding the notation macros breaks the typesetting.** ACS asks authors to avoid extensive use
  of `\newcommand`, so an earlier version expanded the fifteen no-argument ones. Bare substitution
  breaks argument grabbing (`\tfrac1\Tm` means `\tfrac{1}{\Tm}`, and a control word is one token);
  braced substitution fixes that and moves superscripts onto the group instead of the symbol, so
  `2\Binsuf^{\mathrm{up}}` renders differently. Fifteen notation macros is not extensive use. The
  manuscript ships with its macros.
- **The article does not import the SI's citations.** `\externaldocument[][nocite]{...}` looks like
  it does, but xr-hyper's second optional argument is a URL, so `nocite` there is a URL and the two
  documents' citation lists are independent. Adding the SI's keys put 42 undefined citations into
  the package.

## Before uploading

Run `./verify.sh` (thirteen gates, both documents) and
`python scripts/analysis/check_zenodo_record.py`, which fails while the Zenodo record does not hold
the artifacts the Data and Software Availability statement promises. See `ZENODO_DEPOSIT.md`.
