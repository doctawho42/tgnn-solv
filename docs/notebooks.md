# Notebooks and Tutorials

The repository ships a maintained notebook set that mirrors the main code
paths. These notebooks are tutorial-style companions to the documentation, not
separate experimental branches.

## How to Use Them

- read the corresponding site page first if you want the conceptual overview
- open the notebook locally in Jupyter or your IDE
- treat the notebook as the interactive version of the same maintained workflow

Start Jupyter from the repo root with:

```bash
jupyter lab
```

## Notebook Map

| Notebook | Focus | When to use it | Link |
| --- | --- | --- | --- |
| `01_prepare_data.ipynb` | dataset construction, split logic, external `IDAC` ingestion, and aqueous-supervision policy | when you want to inspect the processed CSV pipeline interactively, including `Zenodo idac.csv -> aux_only_gamma`, the `include_water_solubility` switch, and the underlying `ThermoML` regeneration path | [Open on GitHub](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/01_prepare_data.ipynb) |
| `02_train.ipynb` | TGNN-Solv training, optional Stage 0 pretraining, and encoder/config variants | when you want to step through the curriculum, `--pretrain`, and tuned TGNN follow-up configs | [Open on GitHub](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/02_train.ipynb) |
| `03_inference.ipynb` | single-point inference, temperature scan, and AD/OOD checks | when you want to inspect one system manually and keep solver-side `γ₂` separate from auxiliary `γ∞` labels | [Open on GitHub](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/03_inference.ipynb) |
| `04_evaluation.ipynb` | metrics, uncertainty, calibration, and error analysis | when you want richer post-hoc analysis than the quick CLI | [Open on GitHub](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/04_evaluation.ipynb) |
| `05_baselines.ipynb` | DirectGNN, descriptor baselines, RF, and external baselines | when you are comparing TGNN against non-physics alternatives | [Open on GitHub](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/05_baselines.ipynb) |
| `06_ablations.ipynb` | ablation reading and architectural comparisons | when you want to isolate which component is helping | [Open on GitHub](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/06_ablations.ipynb) |
| `07_temperature.ipynb` | temperature dependence, ideal solubility, and van't Hoff analysis | when you want to inspect thermal trends rather than aggregate metrics, while keeping `γ₂(T)` distinct from external `IDAC` supervision | [Open on GitHub](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/07_temperature.ipynb) |
| `08_optuna_tuning.ipynb` | Optuna-based hyperparameter tuning | when you want interactive tuning for TGNN, GPS TGNN, descriptor-augmented TGNN, and DirectGNN families | [Open on GitHub](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/08_optuna_tuning.ipynb) |

## How They Map to the Site

| Site page | Notebook companion |
| --- | --- |
| [Data Preparation](data_preparation.md) | `01_prepare_data.ipynb` |
| [Training](training.md) | `02_train.ipynb` |
| [Evaluation & Inference](evaluation.md) | `03_inference.ipynb`, `04_evaluation.ipynb` |
| [Baselines](baselines.md) | `05_baselines.ipynb` |
| [Experiments & Benchmarks](experiments.md) | `06_ablations.ipynb`, `07_temperature.ipynb`, `08_optuna_tuning.ipynb` |

## Recommended Reading Order

For a first pass through the project:

1. `01_prepare_data.ipynb`
2. `02_train.ipynb`
3. `03_inference.ipynb`
4. `04_evaluation.ipynb`

Then move on to the experiment notebooks depending on your question:

- architecture choices: `06_ablations.ipynb`
- temperature behavior: `07_temperature.ipynb`
- tuning: `08_optuna_tuning.ipynb`

## Important Scope Note

The notebooks are kept aligned with the maintained implementation, but the
reproducible default remains the grouped CLI surface under:

- `scripts/data/`
- `scripts/training/`
- `scripts/evaluation/`
- `scripts/experiments/`

Use notebooks for inspection and explanation, and the CLIs for reproducible
batch runs.

Current alignment notes:

- `02_train.ipynb` now covers both notebook-driven Stage 0 and the maintained
  CLI path through `scripts/training/train.py --pretrain` /
  `scripts/training/train_with_pretrain.py`
- `01_prepare_data.ipynb` now also documents the published Zenodo starter
  corpus (`idac.csv`, `idac_seed_dois.txt`), the maintained `ThermoML` helper
  path through `scripts/data/extract_idac_from_thermoml.py`, the default
  inclusion of supervised water-solubility rows via
  `include_water_solubility`, and the resulting `aux_only_gamma`
  supervision route
- `08_optuna_tuning.ipynb` mirrors the current `OptunaTuner` model aliases,
  including GPS and descriptor-augmented TGNN variants

Current scope note:

- the formal benchmark-adapter API
- checksum-based benchmark-release freezing
- the thermodynamic stress suite

are currently CLI-first rather than notebook-first surfaces.

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Quick Start Workflow](getting_started/quick_start.md)
- [Training](training.md)
- [Evaluation & Inference](evaluation.md)
- [Experiments & Benchmarks](experiments.md)

</div>
