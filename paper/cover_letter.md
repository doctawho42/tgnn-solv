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

This manuscript has not been published elsewhere and is not under consideration by any other
journal. All authors have read and approved the final version of the manuscript. We declare no
conflicts of interest. This study was supported by the Russian Science Foundation, project
No. 25-25-00148.

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
6. **Reviewer suggestions or exclusions.** Seven suggestions and two alternates are in Part 4,
   with the one name that is a judgment call and why.
7. **Funder Registry Tool.** The grant must be entered there as well as in the manuscript; the
   manuscript statement alone does not satisfy the requirement.

---

## Part 4 — Suggested reviewers

Every name below is drawn from the manuscript's own bibliography or from work directly on its
question, and each affiliation was checked against the institution's or the group's current page
rather than taken from the citation.

**On the addresses.** Each is marked with where it comes from, because two of the first five that
were collected for this list were real addresses at the wrong institution — a researcher's earlier
post and a doctoral student account — and an editor cannot reach a reviewer at either:

| mark | meaning |
|---|---|
| *listed* | printed on the institution's own staff page, quoted from it |
| *supplied* | provided by the authors; consistent with that institution's pattern, not independently confirmed |
| *inferred* | matches the institution's confirmed convention but is not printed anywhere reachable; confirm before use |

Two corrections carried into the list below. **Ian Bell** was collected as `ian.bell@ulg.ac.be`,
which is the Université de Liège, where he worked before NIST; his papers through 2025 give the
Applied Chemicals and Materials Division at NIST Boulder. **Chieh-Ming Hsieh** was collected as
`f93524068@ntu.edu.tw` — a National Taiwan University student account from his doctorate, not the
National Central University address he has held as a professor since.

**Conflicts.** Neither author appears as a co-author of any work in the manuscript's bibliography,
and no cited work shares their institutions, so none of the people below is a collaborator of ours.
Note that the COSMO-SAC literature is a small field and Shiang-Tai Lin co-authors much of it: he is
on both the reference-implementation paper cited for Bell and the 2010 paper cited for Hsieh. That
is ordinary in a field this size and is not a conflict with this manuscript's authors, but it is
why the last section exists.

### First choices

1. **Fabian Jirasek** — `fabian.jirasek@rptu.de` *(supplied; matches the pattern printed on the
   department's own staff page for Hasse below)* — Laboratory of Engineering Thermodynamics, RPTU Kaiserslautern-Landau,
   Germany. Builds machine-learning models for activity coefficients under thermodynamic
   constraints: HANNA, matrix completion for activity coefficients, UNIFAC 2.0. He is the closest
   match to what this manuscript actually asks — what a fixed physical structure buys or costs a
   learned model. *Chem. Sci.* 2024, [10.1039/D4SC05115G](https://doi.org/10.1039/D4SC05115G).

2. **André Bardow** — `abardow@ethz.ch` *(supplied; ETH does not print addresses on its people
   pages, so this one could not be checked against a primary source)* — Energy and Process Systems Engineering, ETH Zürich, Switzerland. Co-author of
   the SMILES/language-model predictor for limiting activity coefficients cited in the manuscript,
   and of SPT-NRTL, a physics-guided model constrained to thermodynamic consistency. Expert in
   precisely the split the paper draws between learning the coefficient and learning the fixed
   model's input. *Digital Discovery* 2022,
   [10.1039/D2DD00058J](https://doi.org/10.1039/D2DD00058J).

3. **Ian H. Bell** — `ian.bell@nist.gov` *(inferred: this is the convention printed for ten
   colleagues on NIST's own group page, but he has no reachable staff page of his own — confirm it,
   or take the address from the corresponding-author line of the paper below)* — Applied Chemicals and Materials Division, NIST, Boulder, Colorado, USA. Author
   of the open-source reference COSMO-SAC implementation that this manuscript validates its own
   layer against and quotes the dispersion-on runs from. Well placed to check the closure's
   numerics and the reproducibility apparatus, which is a large part of what is being submitted.
   *J. Chem. Theory Comput.* 2020,
   [10.1021/acs.jctc.9b01016](https://doi.org/10.1021/acs.jctc.9b01016).

4. **Chieh-Ming Hsieh** — `hsiehcm@ncu.edu.tw` *(listed on the NCU faculty page, with office E-201
   and +886-3-4227151#34220)* — Department of Chemical and Materials Engineering, National Central
   University, Taoyuan City, Taiwan. Author of COSMO-SAC-2010 and of the dispersion term the
   manuscript implements, and co-author of the benchmark open-source implementation. See the note
   at the end: he is a frequent co-author of Shiang-Tai Lin, though not of the paper this work is
   contrasted with. *Fluid Phase Equilib.* 2010,
   [10.1016/j.fluid.2010.06.011](https://doi.org/10.1016/j.fluid.2010.06.011).

5. **William H. Green** — `whgreen@mit.edu` *(listed on the MIT ChemE profile page, office E17-504H)*
   — Department of Chemical Engineering, MIT, Cambridge, Massachusetts, USA.
   SolProp and FastSolv, the two external points of comparison the manuscript uses for solubility
   prediction and the source of its statement about where the field's accuracy actually sits.
   *Nat. Commun.* 2025,
   [10.1038/s41467-025-62717-7](https://doi.org/10.1038/s41467-025-62717-7).

6. **Hans Hasse** — `hans.hasse@rptu.de` *(listed on the RPTU staff page, with +49 631 205-3497)* —
   Laboratory of Engineering Thermodynamics, RPTU Kaiserslautern-Landau, Germany.
   Senior thermodynamicist and HANNA co-author; would read the thermodynamic claims rather than the
   machine learning, which is the half a referee is most likely to skip.
   *Chem. Sci.* 2024, [10.1039/D4SC05115G](https://doi.org/10.1039/D4SC05115G).

7. **Kai Sundmacher** — `sundmacher@mpi-magdeburg.mpg.de` *(supplied; matches the surname-only
   pattern the institute uses)* — Chair for Process Systems Engineering, Otto-von-Guericke University
   Magdeburg, and Max Planck Institute for Dynamics of Complex Technical Systems, Germany.
   Gibbs–Helmholtz graph network for the temperature dependence of activity coefficients, cited in
   the manuscript. *Digital Discovery* 2023,
   [10.1039/D2DD00142J](https://doi.org/10.1039/D2DD00142J).

### Alternates

No address found yet for either; both have public pages that carry one.

8. **Edgar Ivan Sanchez Medina** — Otto-von-Guericke University Magdeburg / Max Planck Institute,
   Magdeburg, Germany. His 2025 dissertation is on hybrid graph neural networks for activity
   coefficients, which is the nearest thesis-length match to this manuscript's construction. Early
   career, so better as a second reviewer than a first.

9. **Chau-Chyun Chen** — Department of Chemical Engineering, Texas Tech University, Lubbock, Texas,
   USA. Activity-coefficient models, and a co-author of the VT-2005 σ-profile database this
   manuscript substitutes from. *Ind. Eng. Chem. Res.* 2006,
   [10.1021/ie060370h](https://doi.org/10.1021/ie060370h).

### The one judgment call: Shiang-Tai Lin

The manuscript contrasts its result with TeNNet-SAC — Yue Yang and Shiang-Tai Lin, *J. Chem. Inf.
Model.* **2025**, [10.1021/acs.jcim.5c01804](https://doi.org/10.1021/acs.jcim.5c01804) — published
in this journal. Lin is also the author of COSMO-SAC itself. He is by some distance the most
qualified reader of this manuscript, and he has a direct stake in one of its comparisons.

**Recommendation: neither suggest him nor exclude him.** Suggesting a reviewer whose headline
result the paper qualifies reads as courting a verdict. Excluding the field's leading expert from a
paper about his own model reads worse, and would be hard to justify: the manuscript's treatment of
TeNNet-SAC is a reconciliation and not a refutation — it argues the two works score different
operations, that his construction leaves the segment-activity kernel free to move while this one
does not, and that the chemical scopes differ. An editor of this journal will very likely route the
manuscript past him regardless, and the paper is written to survive that reading. Leave the field
blank and let the editor decide.
