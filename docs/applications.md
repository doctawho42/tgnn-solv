# Applications

TGNN-Solv remains a solubility model first. The application layer is therefore
kept deliberately close to questions where solvent choice, temperature windows,
and formulation media are central variables. The maintained goal is decision
support for chemistry, process, and preformulation work, not a claim that the
repository has become a full retrosynthesis or mechanistic PK/PD platform.

The current maintained `Applications` surface in `Experiment Lab` exposes four
families of workflows:

- solvent screening and green replacement
- process optimization for crystallization, extraction, and reaction media
- drug developability and BCS-style classification
- PK-relevant solubility profiling in GI and formulation-relevant media

The same capabilities are also available through Python APIs and grouped CLIs
under `src/tgnn_solv/applications/` and `scripts/applications/`.

## 1. Solvent Screening

`tgnn_solv.applications.solvent_screening.SolventScreener` turns single-system
solubility prediction into a ranked solvent-library workflow.

Main capabilities:

- rank a built-in common-solvent panel by predicted `ln(x2)`, `x2`, and
  approximate `mg/mL`
- attach solvent metadata such as green score, boiling point, ICH class, and
  water miscibility
- inspect crystallization windows from `T_hot` to `T_cold`
- suggest antisolvents and solvent-swap paths
- search for greener replacements that preserve a configurable fraction of the
  current solvent performance

The `mg/mL` conversion is explicitly approximate. The implementation assumes the
solvent dominates liquid volume and uses solvent density together with the
predicted mole fraction to estimate dissolved mass concentration. That is
useful for ranking and screening, but it is not a substitute for measured
solution density or exact formulation mass-balance calculations.

CLI:

```bash
python scripts/applications/screen_solvents.py --help
```

## 2. Process Optimization

`tgnn_solv.applications.process_optimization.ProcessOptimizer` builds on solvent
screening and temperature scans to search operating windows rather than only
single points.

Maintained modes:

- `optimize_crystallization`
  - finds `(solvent, T_hot, T_cold)` combinations that maximize predicted yield
- `optimize_extraction`
  - ranks extraction solvents by partition leverage, immiscibility, and
    operability
- `optimize_reaction_medium`
  - scores solvents where reactants stay soluble while the product tends to
    crash out
- `design_solvent_system`
  - explores approximate binary solvent systems using Hansen-space interpolation

The crystallization workflow should be read as a screening optimizer, not as a
CFD or kinetics model. Yield, supersaturation, and metastable-zone heuristics
are computed from equilibrium predictions and local solubility slopes rather
than from nucleation and growth kinetics.

CLI:

```bash
python scripts/applications/optimize_process.py --help
```

## 3. Drug Developability and BCS-Like Classification

`tgnn_solv.applications.drug_properties.DrugPropertyPredictor` exposes the
current drug-facing workflow.

What it does:

- predicts aqueous intrinsic solubility at `37 °C`
- applies heuristic pH correction across gastric and intestinal conditions when
  an ionization estimate is available
- computes a BCS-style high/low solubility decision through the dose number
  <span>\(D_0 = \frac{\text{dose}}{V \cdot S}\)</span>
- uses RDKit proxy descriptors such as `LogP` and `TPSA` for a conservative
  high-/low-permeability heuristic
- assembles a composite developability score from aqueous solubility, crystal
  stability, lipophilicity balance, solvent diversity, and temperature
  sensitivity
- screens approximate salt/cocrystal counterion ideas, clearly marked as lower
  confidence because the base model is not trained on full ionic chemistry

This is more explicit than the earlier "oral dose proxy" phrasing. The workflow
now produces a BCS-style class, formulation recommendations, caveats, and a
structured developability report. It is still not a replacement for measured
biorelevant-media data or transport experiments.

CLI:

```bash
python scripts/applications/drug_developability.py --help
```

## 4. PK-Relevant Solubility Profiling

`tgnn_solv.applications.pk_profiling.PKSolubilityProfiler` extends the
developability layer into GI and dosage-form contexts.

Maintained outputs:

- GI-tract compartment profile
  - stomach fasted/fed, duodenum, jejunum/ileum, colon
- dissolved-fraction and dose-number heuristics along the tract
- biorelevant media screen
  - `FaSSGF`, `FeSSGF`, `FaSSIF`, `FeSSIF`
- food-effect heuristic from fasted vs fed intestinal media
- IV vehicle screening across water, co-solvents, surfactant surrogates, and
  cyclodextrin-like systems
- topical vehicle screening with a thermodynamic-activity proxy

The PK wording is intentionally narrow. These workflows estimate how solubility
pressure changes across media and compartments; they do **not** model full
absorption, transport, metabolism, clearance, or pharmacodynamics.

CLI:

```bash
python scripts/applications/pk_profile.py --help
```

## 5. Scope and Limitations

The correct interpretation of the application layer is:

- useful for solvent choice, isolation strategy, and preformulation triage
- useful upstream of richer PK, dissolution, and process-development models
- useful for comparing `TGNN-Solv` and `DirectGNN` on the same downstream task

It does **not** directly predict:

- permeability from first principles
- dissolution kinetics or precipitation kinetics
- exposure, clearance, tissue distribution, or PD
- retrosynthetic disconnections or reaction mechanisms

Whenever pH correction, food-effect factors, salt/cocrystal surrogates, or
binary-mixture interpolation are used, the UI and CLIs surface those steps as
approximations rather than hiding them.

## 6. GUI and Model-Family Support

Everything above is available in `Experiment Lab -> Applications`.

The page uses the same checkpoint selection and inference-family routing as the
rest of the lab:

- `TGNN-Solv`
- `DirectGNN`

That means application workflows remain comparable across the maintained model
families without inventing a second inference stack for the GUI.

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Evaluation & Inference](evaluation.md)
- [Experiment Lab](experiment_lab.md)
- [Architecture](architecture.md)
- [Results](results.md)

</div>
