# Contributing

This page is the public-site summary of the contributor workflow. The full
repository guide remains in
[CONTRIBUTING.md on GitHub](https://github.com/doctawho42/tgnn-solv/blob/main/CONTRIBUTING.md).

## Development Setup

```bash
git clone https://github.com/doctawho42/tgnn-solv.git
cd tgnn-solv

conda create -n tgnn-solv-dev python=3.11
conda activate tgnn-solv-dev

pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
pip install -e ".[dev]"
```

## Minimum Expectations

Before opening a PR:

1. add or update tests for behavior changes
2. update docs when changing configs, scripts, dataset payloads, or outputs
3. preserve backward compatibility where practical for configs, checkpoints,
   and report formats
4. keep optional dependency paths optional
5. if you change the benchmark contract, update the sidecar story too
   (`run_manifest.json`, `benchmark_card.json`, checkpoint `*.model_card.json`)

## Useful Checks

Run the full suite:

```bash
pytest tests/ -v
```

Useful targeted checks:

```bash
pytest tests/test_physics.py -v
pytest tests/test_integration.py -v
pytest tests/test_dataset.py -v
pytest tests/test_loss.py -v
```

Useful repo-integration checks:

```bash
python scripts/experiments/reproduce_paper.py --profile core --list-steps
python scripts/experiments/reproduce_paper.py --profile core --step prepare_data --dry-run
mkdocs build
```

If you changed a broad Python surface, also run:

```bash
ruff check src/ scripts/
```

## Project-Specific Constraints

- keep the solver and core thermodynamic layers free of learnable parameters
- if you add new model inputs, wire them through dataset, training, inference,
  evaluation, and scripts consistently
- if you add new config flags, document them in the relevant site page and the
  repository guides
- preserve the grouped `scripts/` layout for user-facing entry points
- keep legacy compatibility wrappers unless you are intentionally removing a
  compatibility layer and have audited downstream usage

## Where to Put New Things

| Change type | Preferred location |
| --- | --- |
| data-preparation CLI | `scripts/data/` |
| training CLI | `scripts/training/` |
| evaluation CLI | `scripts/evaluation/` |
| experiment runner | `scripts/experiments/` |
| optional external baseline wrapper | `scripts/external/` |
| baseline implementation | `src/tgnn_solv/baselines/` |

## Documentation Policy

When you change any of the following, update the corresponding documentation:

- CLI arguments
- config fields or defaults
- checkpoint contents
- evaluation outputs
- experiment result layouts
- notebook workflows

The site is intended to stay synchronized with the maintained implementation.
If behavior changes in code, the docs should change in the same PR.

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Script Reference](script_reference.md)
- [Architecture](architecture.md)
- [Training](training.md)
- [Repository Audit](repository_audit.md)

</div>
