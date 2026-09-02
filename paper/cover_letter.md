# Cover letter — *Journal of Chemical Information and Modeling*

> **How to use this file.** JCIM asks authors to upload its own *Submission Cover Letter and Author
> Checklist* form (`jcisd8_checklist.pdf`) **in lieu of** a free-form cover letter, while the general
> author guidelines still say a letter must accompany every submission. Part 1 below is the letter;
> Part 2 gives the text for the form's free-text fields, so the same words serve both. Part 3 lists
> what only the authors can settle. Nothing here should be uploaded before Part 3 is closed.

---

## Part 1 — The letter

To the Editors, *Journal of Chemical Information and Modeling*

Dear Editors,

We submit for consideration as an **Article** the manuscript **"Ground Truth That Does Not Ground:
Substituting Reference Solvent σ-Profiles Degrades COSMO-SAC Solubility Prediction"** by
N. L. Polomoshnov and A. V. Rudik.

Physics-informed models are built so that a prediction passes through a quantity chemistry already
tabulates, and the design carries an assumption that is rarely tested: that handing the model the
tabulated value, in place of the one it learned, should improve it. We test that assumption
directly. A graph neural network predicts the σ-profiles a fixed COSMO-SAC layer consumes, and
quantum chemistry tabulates the same profiles independently, so the substitution can be made
without retraining anything.

It makes the model worse. Over five seeds the mean absolute error on solid–liquid solubility rises
from 1.93 to 2.34 in ln *x*₂, about 21%, with no overlap between the per-seed values of the two
arms, and the mean per-solute Spearman correlation over solvents falls by 0.185 — a loss in the
ranking that solvent selection actually uses. Supervising the same network against the same
database during training, the other operation the word "grounding" covers, gives gains that straddle
zero, and we report it as having no established sign rather than as a benefit. The operation that
fails is the one available in practice, because it is the one that needs no retraining.

The constructive half of the paper is a way to tell in advance where this will happen. Using
infinite-dilution activity coefficients we separate a deployed thermodynamic model's own error from
what its inputs leave unresolved, search fifty-nine chemical strata, and find the model's own error
dominant on one solvent chemistry. We state plainly which of those bounds are established and which
are the instrument's output on a set too small to certify — including one that an independent set
reproduces at half its size without meeting our own stability rule.

We think this belongs in JCIM for two reasons. It concerns how a widely used cheminformatics
construction behaves when a learned component meets a fixed physical map, which is a modelling
question rather than a chemistry-specific one; and it is written to the standard of the Journal's
editorial on method and data sharing (*J. Chem. Inf. Model.* **2015**, *55*, 719). Every number in
the manuscript and the Supporting Information is produced by a deposited script from a deposited
artifact; the code, checkpoints, processed splits and per-arm predictions are released; and the two
decomposition sets are deposited as row-level machine-readable tables so a reader can recompute the
central claim without running our code. Twelve defects and limits of the work are disclosed by us,
each where its numbers print, and none of them is reported by anyone else.

The manuscript is original, is not under consideration elsewhere, and all authors have approved the
submission. We declare no competing financial interest. This study was supported by the Russian
Science Foundation, project No. 25-25-00148.

We would be glad to answer any questions.

Sincerely,
Nikita L. Polomoshnov (corresponding author) — nikitapol@fbb.msu.ru
Faculty of Bioengineering and Bioinformatics, Lomonosov Moscow State University

---

## Part 2 — Text for the JCIM form

**Title.** Ground Truth That Does Not Ground: Substituting Reference Solvent σ-Profiles Degrades
COSMO-SAC Solubility Prediction

**Corresponding Author Name.** Nikita L. Polomoshnov

**Corresponding Author Email.** nikitapol@fbb.msu.ru

**Reason for submission (importance to field and major findings).**
Physics-informed predictors are justified by the claim that their intermediate quantities can be
supplied from reference tables, and the claim is rarely tested. We test it on solid–liquid
solubility, where a learned σ-profile feeds a fixed COSMO-SAC closure and the same profiles are
tabulated from quantum chemistry. Substituting the tabulated profile at prediction time — the
operation available without retraining — degrades accuracy at every one of five seeds, from 1.93 to
2.34 mean absolute error in ln *x*₂ (about 21%), and degrades the per-solute ranking of solvents by
0.185 in mean Spearman correlation. Training-time supervision against the same database, the other
sense of "grounding", produces gains that straddle zero and is reported with no established sign.
Using infinite-dilution activity coefficients we then separate the closure's own error from what its
inputs leave unresolved across fifty-nine chemical strata, which is what tells a practitioner where
a better input can help and where it can only expose the map's misspecification. The finding
matters to anyone building a hybrid model around a fixed physical layer: reference data are a
diagnostic for locating a model's limits, not a remedy that can be assumed to work.

**Data and Software Availability section present?** Yes. It names the code repository and licence,
the Zenodo deposit for checkpoints, processed splits, per-arm predictions and larger artifacts, and
every public data source (BigSolDB 2.0; VT-2005 and UD σ-profile databases; ThermoML and the PGL
6th-edition IDAC database; the OPERA pKa compilation). All software used is open source and
obtainable; none of the data are proprietary.

**New biological activity of compounds?** Not applicable.

**Bad-actor compound validation (PAINS, aggregators)?** Not applicable — no compounds are proposed
as bioactive.

**SMILES for compounds in the manuscript.** Provided: Data Set S1 (477 rows) and Data Set S2 (60
rows) both carry solute and solvent SMILES, deposited as CSV with the Supporting Information.

**Table of Contents graphic.** Included, labelled "Table of Contents graphic".

---

## Part 3 — What only the authors can settle before upload

1. **Preprint status.** JCIM requires any use of ChemRxiv/arXiv/bioRxiv to be declared, with a note
   on how the manuscript changed between deposition and submission. If no preprint was posted, say
   so on the form; if one was, add the server, the date and the differences.
2. **Previous submissions.** The form's "previous submissions" question must be answered accurately,
   with any earlier critique attached if the manuscript was considered elsewhere.
3. **Author contributions.** The CRediT roles in the manuscript are currently inferred from the work
   as recorded and are not yet an agreed statement between both authors.
4. **The AI-use disclosure** in the Acknowledgement must be confirmed by both authors, and any tool
   used outside what is described there added to it.
5. **The two submission placeholders** in the Data and Software Availability section: the repository
   commit hash the reported numbers were produced from, and the Zenodo DOI.
6. **Reviewer suggestions or exclusions**, if any. None are proposed here.
7. **Funder Registry Tool.** The grant must be entered there as well as in the manuscript; the
   manuscript statement alone does not satisfy the requirement.
