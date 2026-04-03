# Internal Package Layout

The package now exposes two parallel internal layouts:

- legacy flat modules at `tgnn_solv.<module>`
- grouped namespaces for human-friendly navigation:
  - `tgnn_solv.core`
  - `tgnn_solv.chemistry`
  - `tgnn_solv.data`
  - `tgnn_solv.models`
  - `tgnn_solv.physics`
  - `tgnn_solv.training`
  - `tgnn_solv.evaluation`
  - `tgnn_solv.baselines`
  - `tgnn_solv.research`

## Why Both Exist

The flat modules remain the compatibility layer for:

- existing imports across the repo
- tests
- scripts and notebooks
- downstream users already importing `tgnn_solv.model`, `tgnn_solv.trainer`,
  and similar legacy paths

The grouped namespaces are the preferred navigation surface for contributors.
They re-export the legacy modules without changing behavior.

## Suggested Import Style

Preferred grouped imports for new code:

```python
from tgnn_solv.core.config import TGNNSolvConfig
from tgnn_solv.models.tgnn import TGNNSolv
from tgnn_solv.training.trainer import TGNNSolvTrainer
from tgnn_solv.evaluation.inference import load_model
```

Legacy imports remain supported:

```python
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.model import TGNNSolv
from tgnn_solv.trainer import TGNNSolvTrainer
from tgnn_solv.inference import load_model
```

## Namespace Map

### `tgnn_solv.core`

- configuration and runtime helpers

### `tgnn_solv.chemistry`

- molecular featurization and fixed chemical priors

### `tgnn_solv.models`

- TGNN-Solv model, DirectGNN, heads, and layers

### `tgnn_solv.physics`

- solver and thermodynamic layers

### `tgnn_solv.training`

- trainer, losses, pretraining, and tuning

### `tgnn_solv.evaluation`

- inference, evaluator/reporting, plotting, and analysis helpers

### `tgnn_solv.research`

- ablation helpers that remain more experimental than the canonical paths
