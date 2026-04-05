# Free GPU Training

This note covers the preemption-safe training paths for TGNN-Solv and
DirectGNN in environments like Google Colab and SageMaker Studio Lab.

## What Changed

Both `scripts/training/train.py` and `scripts/training/train_directgnn.py` support:

- `--checkpoint-every N` to save a resumable training checkpoint every `N`
  epochs within each phase
- `--resume PATH` to continue from the latest saved training state

The helper wrapper `scripts/training/run_resume_safe_train.sh` targets the TGNN CLI. It
starts a fresh run when the checkpoint does not exist and automatically
resumes when it does.

## Recommended Usage

Activate your environment first. If the shell does not resolve the correct
Python interpreter automatically, set `PYTHON_BIN` explicitly.

```bash
export PYTHON_BIN="$CONDA_PREFIX/bin/python"
export CHECKPOINT="checkpoints/cloud_tgnn_solv.pt"
export CHECKPOINT_EVERY=5

bash scripts/training/run_resume_safe_train.sh \
  --config configs/paper_config_tuned.yaml \
  --train-data notebooks/data/processed/train.csv \
  --val-data notebooks/data/processed/val.csv \
  --test-data notebooks/data/processed/test.csv \
  --device cpu \
  --log-dir logs/cloud_runs
```

For Colab or Studio Lab, rerun the same command after reconnecting. The script
will reuse the existing checkpoint and continue from the saved phase/epoch.

## Notes

- The resumable checkpoint is stored at `CHECKPOINT`.
- The same checkpoint remains loadable for inference because it still contains
  `model_state_dict` and `config`.
- The training script also writes checkpoint sidecars:
  - `<checkpoint>.manifest.json`
  - `<checkpoint>.model_card.json`
- If a checkpoint already marks training as completed, `--resume` skips fitting
  and only reruns the final evaluation path.
- `scripts/experiments/run_full_budget_experiment.py` and
  `scripts/experiments/run_medium_budget_comparison.py` also pass through
  `--checkpoint-every` and resume from existing per-model checkpoints.

If you later benchmark or archive those checkpoints, the sidecars allow the
artifact layer to recover the originating config, data paths, and git context
without relying on notebook memory or shell history.

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Training](training.md)
- [Troubleshooting](troubleshooting.md)
- [Experiments & Benchmarks](experiments.md)
- [Quick Start Workflow](getting_started/quick_start.md)

</div>
