# TGNN-Solv

A controlled study of what a thermodynamic bottleneck costs and buys in a solubility model, and
the code that produced it.

The model predicts crystal and interaction parameters, passes them through a differentiable
solid–liquid-equilibrium solver, and trains end-to-end through that physics bottleneck. A matched
control — the same graph encoder with the solver removed — is trained beside it, because the
difference between the two is the measurement. This repository is the apparatus for that
comparison, not a solubility product: **no arm here is competitive with current solubility models
and none is offered as one.**

## Start here

| If you want to | Read |
|---|---|
| the result | `paper/grounding_paradox.pdf` (article) and `paper/grounding_paradox_si.pdf` (supporting information), or the [project page](https://doctawho42.github.io/tgnn-solv/) |
| to check a number the paper prints | [`DEPOSITS.md`](DEPOSITS.md) — every printed value, the artifact it came from, and the script that regenerates it |
| to re-run the checks | `./verify.sh` |
| to reproduce the pipeline | [Reproduction](#reproduction) below |
| the theory and the empirical state | `PROJECT_DESCRIPTION.md` |
| to work on the code | `AGENTS.md` (layout, CLI catalogue, config families) and `CLAUDE.md` (the traps that cost time) |
| what happened and when | `PROJECT_MEMORY.md` (dated operational log; read in slices) |

## Verification

One command certifies the repository: the package imports, the test suite, the eight gates that
bind every hand-transcribed number in the manuscript to its artifact, and both LaTeX builds to a
cross-document fixed point.

```bash
./verify.sh
```

`./verify.sh fast` skips the test suite and the LaTeX builds. The gates are the part worth knowing
about: each one re-reads a deposit and compares it against what the manuscript prints, so a
regenerated artifact that moves a value fails the build rather than shipping quietly.

## Installation

Python ≥ 3.10.

```bash
pip install -e .
```

RDKit, PyTorch and scikit-learn each ship their own libomp, and importing more than one aborts the
process. The test suite sets `KMP_DUPLICATE_LIB_OK=TRUE` for you; ad-hoc snippets that import torch
and rdkit together need it set explicitly.

## Reproduction

`reproduce.sh` drives the pipeline end to end. The data preparation step rebuilds the processed
splits from the cached raw sources:

```bash
python scripts/prepare_data.py --config configs/paper_config_tuned.yaml \
    --split-mode solute_scaffold --seed 42 --skip-download
```

**A regenerated split is a new split.** The seeded `solute_scaffold` partition is not stable across
pipeline versions — a rebuild has been observed to turn over ~76% of which scaffolds land in test —
so every checkpoint and every metric computed on the previous split is orphaned by it. Recompute
downstream artifacts, and never compare a metric across a regeneration.

Training runs through `scripts/train.py` (or the grouped `scripts/training/train.py`). Everything
is driven by one dataclass, `config.TGNNSolvConfig`; `--set key=value` overrides any field.

Local runs are smoke configs and produce meaningless metrics. Real numbers need a GPU run on the
full corpus; `scripts/kaggle/README.md` records what an arm actually costs and why the outstanding
GPU arms were not run.

## Layout

```
paper/          the manuscript, its sections, and the generated tables
src/tgnn_solv/  the package: model, solver, layers, losses, trainer
scripts/        CLI surface, grouped by purpose (data, training, evaluation,
                experiments, analysis, external, kaggle)
configs/        config families; paper_config*.yaml are the published ones
results/        deposits behind printed numbers (curated — see .gitignore,
                which explains why each tracked artifact is tracked)
tests/          the suite verify.sh runs
```

`scripts/analysis/check_*.py` are the manuscript gates. `scripts/analysis/run_*.py` are the
analyses behind the paper's claims; each writes a deposit under `results/`.

The two models that matter:

- `TGNNSolv` (`src/tgnn_solv/model.py`) — crystal head and activity head feeding
  `solver.SLESolver`, which solves `ln x2 = -Φ(T) - ln γ2`.
- `DirectGNN` (`src/tgnn_solv/baselines/direct_gnn.py`) — the same encoder with no solver. This is
  the control, not a throwaway baseline.

## Docker

```bash
docker compose up lab        # the experiment lab
docker compose up train      # a training run
docker compose up evaluate   # evaluation
```

## Data

Solubility is BigSolDB 2.0, partitioned by Bemis–Murcko scaffold. Crystal `T_m`/`ΔH_fus` come from
an open melting-point pool plus a group-contribution prior. Reference σ-profiles are the VT-2005
tabulation. Sources are public; the per-row prediction files and the larger analysis artifacts are
deposited separately (see `DEPOSITS.md`).

## The public page

One hand-written file, `web/index.html`, deployed by `.github/workflows/docs.yml` on any push to
`main` that touches it. The deploy blocks if the page's abstract has drifted from the manuscript's.
See `web/README.md` for why it is not generated, and for the trap that kept the previous site alive
and stale for five months.

## Licence

MIT. See `LICENSE`.
