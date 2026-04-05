# Quick Start Workflow

This is the shortest maintained path from a fresh clone to a trained model and
one evaluated checkpoint.

If the environment is not ready yet, start with the
[installation guide](installation.md).

## 1. Prepare the processed split

Build the canonical full scaffold split under `notebooks/data/processed/`:

```bash
python scripts/data/prepare_data.py \
    --output-dir notebooks/data/processed \
    --split-mode solute_scaffold \
    --seed 42
```

This writes:

- `train.csv`
- `val.csv`
- `test.csv`
- additional `_solute` and `_solvent` split variants
- `split_manifest.json`

## 2. Train the maintained tuned TGNN baseline

Use the tuned TGNN config for the current architecture-comparison baseline:

```bash
python scripts/training/train.py \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_solv_tuned.pt \
    --device cuda
```

If CUDA is unavailable, replace `--device cuda` with `--device mps` or
`--device cpu`.

### Resume-safe variant

For long or preemptible runs:

```bash
python scripts/training/train.py \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_solv_tuned.pt \
    --checkpoint-every 5 \
    --device cuda
```

Resume later with:

```bash
python scripts/training/train.py \
    --resume checkpoints/tgnn_solv_tuned.pt \
    --checkpoint checkpoints/tgnn_solv_tuned.pt \
    --device cuda
```

## 3. Run one inference query

```python
from tgnn_solv.inference import load_model, predict_solubility

model, cfg = load_model("checkpoints/tgnn_solv_tuned.pt")
result = predict_solubility(
    model,
    solute_smiles="CC(=O)Nc1ccc(O)cc1",
    solvent_smiles="CCO",
    T=298.15,
)
print(result["ln_x2"], result["T_m"], result["tau_12"])
```

See the full maintained inference surface in
[Evaluation & Inference](../evaluation.md).

## 4. Evaluate the checkpoint

Use the lightweight maintained evaluation CLI:

```bash
python scripts/evaluation/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_tuned.pt \
    --output results/full_evaluation.json \
    --verbose
```

This gives you:

- test-set regression metrics
- figure-ready arrays
- error slices such as aqueous and top-solvent subsets
- a canonical report payload that can be opened directly in `Results & Plots`
  and `Benchmark Studio` inside the lab
- report sidecars:
  - `full_evaluation.manifest.json`
  - `full_evaluation.card.json`

## 5. Run a matched no-physics baseline

To compare TGNN-Solv against the maintained matched backbone:

```bash
python scripts/training/train_directgnn.py \
    --config configs/paper_config_directgnn_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn_tuned.pt \
    --device cuda
```

That is the main ablation used to test whether the explicit physics bottleneck
is helping.

## 6. Optional: launch the GUI workbench

```bash
python scripts/launch_lab.py
```

Useful first places in the UI:

- `Inference`
  - draw/edit structures, run TGNN or DirectGNN inference, inspect uncertainty
    and OOD
- `Results & Plots -> Benchmark studio`
  - compare canonical benchmark bundles, including external, custom, and
    adapter-based models
- `Reproduce`
  - launch the maintained `core`, `article`, or `full` reproduction profile

## 7. Go deeper

After the first end-to-end run, the most useful next pages are:

- [Experiment Lab](../experiment_lab.md)
  - launch the maintained GUI for visual training, inference, uncertainty, and lineage workflows
- [Architecture](../architecture.md)
  - understand TGNN-Solv, DirectGNN, GC priors, and Stage 0 pretraining
- [Training](../training.md)
  - curriculum phases, pair-aware batching, oracle injection, and resume
- [Experiments & Benchmarks](../experiments.md)
  - medium-budget comparison, full-budget diagnostic run, split studies, and external baselines
- [Reproducing the Paper](../reproducing_paper.md)
  - structured `core`, `article`, and `full` workflows
- [Notebooks & Tutorials](../notebooks.md)
  - interactive walk-throughs that mirror the maintained code paths
