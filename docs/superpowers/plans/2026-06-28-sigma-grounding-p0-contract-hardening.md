# P0 — σ-grounding Contract/Correctness Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the σ-profile aux apparatus contractually safe and correctly balanced — without changing the science — so later phases (P1 manifold learning, P2 combinatorial, P3 experiment harness) build on a sound base.

**Architecture:** Six independent, no-regret fixes to the existing COSMO-SAC σ-profile path: rebalance the supervision loss (SUM-EMD + separate component logging), enforce a grid/bin contract at data load, make the data builder read the grid from config, interleave the aux dosing across the epoch, harden the acyclic scaffold-leak guard, and pin down train/eval segment-iteration consistency with a convergence regression test.

**Tech Stack:** Python ≥3.10, PyTorch, pandas, RDKit, pytest. Package `tgnn_solv` under `src/`.

## Global Constraints

- **Env gotcha:** RDKit+PyTorch+sklearn each ship libomp; importing >1 aborts. Prefix any ad-hoc `python -c`/`python - <<EOF` that imports torch+rdkit with `KMP_DUPLICATE_LIB_OK=TRUE`. The test suite already sets this via `tests/conftest.py`.
- **Test command:** `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/ -q` (full suite, ~280 tests, must stay green). Single test: `... python -m pytest tests/path::name -q`.
- **Lint:** `ruff check src tests scripts` (no committed config; defaults).
- **Do NOT flip the dCp / Prausnitz sign** in the ideal term — it is CORRECT. Out of scope here regardless.
- **No science change in P0.** Absolute metrics are meaningless locally (CPU/MPS smoke). Do not report smoke numbers as results.
- **Branch:** work on `sigma-grounded-cosmosac` (already created; the design spec is committed there at `docs/superpowers/specs/2026-06-28-sigma-grounded-cosmosac-design.md`).
- **σ-grid (verified):** `cosmo_sac_n_bins=51`, `sigma_min=-0.025`, `sigma_max=0.025` e/Å² (`config.py:172-174`). Profile columns are `sigma_p_0 .. sigma_p_50`; aux rows are self-solvent (`solvent_smiles==solute_smiles`), `has_solubility=False`, `has_sigma_profile=True`.
- **`SigmaProfileHead` output dict keys (verified):** `sig["p_shape"]` (softmax, sums to 1) and `sig["area"]` (Å²) — used by `loss.py` and `trainer._train_sigma_aux_batch`.

---

## File Structure

| File | Responsibility | Tasks |
|------|----------------|-------|
| `src/tgnn_solv/loss.py` | `sigma_profile_emd_loss` — supervision loss math + component reporting | 1 |
| `src/tgnn_solv/config.py` | `TGNNSolvConfig` σ fields (area scale, shape weight) | 1 |
| `src/tgnn_solv/trainer.py` | `_train_sigma_aux_batch` caller + epoch dosing loop | 1, 4 |
| `src/tgnn_solv/data/dataset.py` | `TGNNSolvDataset` — σ-bin contract assert + missing-area hard error | 2 |
| `src/tgnn_solv/data/utils.py` | `scaffold_key` helper (acyclic-safe) | 5 |
| `scripts/data/build_sigma_profile_aux_stream.py` | builder — read n_bins from cfg, write grid metadata, acyclic-safe guard | 3, 5 |
| `tests/test_sigma_loss.py` | loss rebalance + components | 1 |
| `tests/test_sigma_dataset_contract.py` | bin-count assert + missing-area error | 2 |
| `tests/test_sigma_aux_builder.py` | builder n_bins-from-cfg + metadata | 3 |
| `tests/test_sigma_dosing.py` | interleaving helper | 4 |
| `tests/test_scaffold_key.py` | acyclic-safe scaffold key | 5 |
| `tests/test_cosmo_sac_iter_convergence.py` | train/eval iter convergence | 6 |

**Sequencing:** Tasks 1–6 are independent and may be done in any order; the order below is the recommended one (cheapest/highest-value first). Each ends with a green suite and a commit.

---

### Task 1: Rebalance σ-profile supervision loss (SUM-EMD) + per-component logging

**Why:** EMD currently uses `mean` over 51 bins (~0.02–0.05), while area MSE uses `area_scale=200` against a pool whose `sigma_area` std is ~75 — so the single area scalar dominates the 51-dim shape that defines the activity manifold (review H3). Fix: SUM-over-bins EMD (W1 in bin units, ~50× larger), an explicit `shape_weight`, an area scale matched to the pool std, and separate logging of the two terms.

**Files:**
- Modify: `src/tgnn_solv/loss.py:59-88` (`sigma_profile_emd_loss`)
- Modify: `src/tgnn_solv/config.py:186-194` (add `sigma_shape_weight`, change `sigma_area_scale` default)
- Modify: `src/tgnn_solv/trainer.py:875-887` (caller logs components)
- Test: `tests/test_sigma_loss.py` (new)

**Interfaces:**
- Produces: `sigma_profile_emd_loss(pred_shape, target_shape, pred_area, target_area, mask, *, mode="emd", area_scale=75.0, shape_weight=1.0, eps=1e-8, return_components=False)` → `Tensor` when `return_components=False`, else `tuple[Tensor, dict[str, float]]` with keys `"sigma_shape"`, `"sigma_area"`.
- Consumes (later phases): `cfg.sigma_shape_weight: float = 1.0`, `cfg.sigma_area_scale: float = 75.0`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sigma_loss.py`:

```python
import torch

from tgnn_solv.loss import sigma_profile_emd_loss


def test_emd_is_sum_over_bins_and_returns_components():
    # pred mass entirely in bin 0, target mass entirely in bin 2 (3-bin toy grid).
    pred_shape = torch.tensor([[1.0, 0.0, 0.0]])
    target_shape = torch.tensor([[0.0, 0.0, 1.0]])
    pred_area = torch.tensor([100.0])
    target_area = torch.tensor([100.0])
    mask = torch.tensor([True])

    total, comps = sigma_profile_emd_loss(
        pred_shape, target_shape, pred_area, target_area, mask,
        mode="emd", area_scale=75.0, shape_weight=1.0, return_components=True,
    )
    # cumsum(pred)=[1,1,1], cumsum(target)=[0,0,1]; |diff|=[1,1,0]; SUM=2.0
    # (mean-over-bins would give 0.667 — this asserts the SUM behaviour).
    assert abs(comps["sigma_shape"] - 2.0) < 1e-6
    assert abs(comps["sigma_area"] - 0.0) < 1e-6
    assert abs(float(total) - 2.0) < 1e-6


def test_area_term_uses_scale_and_shape_weight_applies():
    pred_shape = torch.tensor([[0.5, 0.5]])
    target_shape = torch.tensor([[0.5, 0.5]])  # zero shape loss
    pred_area = torch.tensor([150.0])
    target_area = torch.tensor([75.0])  # diff 75, scale 75 -> (1.0)^2 = 1.0
    mask = torch.tensor([True])

    total, comps = sigma_profile_emd_loss(
        pred_shape, target_shape, pred_area, target_area, mask,
        mode="emd", area_scale=75.0, shape_weight=3.0, return_components=True,
    )
    assert abs(comps["sigma_shape"] - 0.0) < 1e-6
    assert abs(comps["sigma_area"] - 1.0) < 1e-6
    assert abs(float(total) - 1.0) < 1e-6  # shape_weight*0 + 1.0


def test_empty_mask_returns_zero_with_components():
    z = torch.zeros(1, 3, requires_grad=True)
    total, comps = sigma_profile_emd_loss(
        z, z.detach(), torch.zeros(1), torch.zeros(1), torch.tensor([False]),
        return_components=True,
    )
    assert float(total) == 0.0
    assert comps == {"sigma_shape": 0.0, "sigma_area": 0.0}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_sigma_loss.py -q`
Expected: FAIL — `test_emd_is_sum_over_bins...` asserts 2.0 but current `mean` gives ~0.667; `return_components` is not yet a parameter (TypeError).

- [ ] **Step 3: Implement the loss change**

Replace `sigma_profile_emd_loss` body (`src/tgnn_solv/loss.py:59-88`) with:

```python
def sigma_profile_emd_loss(
    pred_shape: Tensor,
    target_shape: Tensor,
    pred_area: Tensor,
    target_area: Tensor,
    mask: Tensor,
    *,
    mode: str = "emd",
    area_scale: float = 75.0,
    shape_weight: float = 1.0,
    eps: float = 1e-8,
    return_components: bool = False,
) -> Tensor | tuple[Tensor, dict[str, float]]:
    """Masked sigma-profile supervision loss (shape + cavity area).

    The shape term is the 1-D Wasserstein/EMD distance on the ordered sigma grid,
    SUMMED over bins (``sum|cumsum(pred) - cumsum(target)|``) so the 51-dim shape
    that defines the activity manifold is not crushed by a per-bin mean and cannot
    be dominated by the single area scalar; ``mode="mse"`` falls back to per-bin
    MSE. The area term is a scaled MSE on the cavity surface area; ``area_scale``
    should track the pool's sigma_area std (~75 Å²). Both are averaged over the
    masked single-component rows. With ``return_components=True`` also returns the
    detached scalar shape/area terms for logging.
    """
    m = mask.bool()
    if not bool(m.any()):
        zero = pred_shape.sum() * 0.0
        if return_components:
            return zero, {"sigma_shape": 0.0, "sigma_area": 0.0}
        return zero
    ps = pred_shape[m]
    ts = target_shape[m]
    if mode == "mse":
        shape_loss = ((ps - ts) ** 2).sum(dim=-1).mean()
    else:
        shape_loss = (
            torch.cumsum(ps, dim=-1) - torch.cumsum(ts, dim=-1)
        ).abs().sum(dim=-1).mean()
    area_loss = (((pred_area[m] - target_area[m]) / area_scale) ** 2).mean()
    total = shape_weight * shape_loss + area_loss
    if return_components:
        return total, {
            "sigma_shape": float(shape_loss.item()),
            "sigma_area": float(area_loss.item()),
        }
    return total
```

Then in `src/tgnn_solv/config.py`, change the area-scale default and add the shape weight (the COSMO-SAC block, currently lines 186-194):

```python
    # Sigma-profile head output scaling (cavity surface area, Å²).
    sigma_area_scale: float = 75.0  # ~pool sigma_area std; see P0 loss rebalance
    sigma_area_min: float = 20.0
    sigma_shape_weight: float = 1.0  # weight on the SUM-EMD shape term
    # Sigma-profile external aux supervision stream.
    sigma_aux_steps_per_epoch: int = 0
    sigma_aux_phase1_weight: Optional[float] = None
    sigma_aux_phase2_weight: Optional[float] = None
    sigma_aux_phase3_weight: Optional[float] = None
    sigma_profile_loss: str = "emd"  # "emd" (1-D Wasserstein) or "mse"
```

- [ ] **Step 4: Update the trainer caller to log components**

In `src/tgnn_solv/trainer.py`, replace the loss call + return in `_train_sigma_aux_batch` (lines 876-887):

```python
        loss_val, comps = sigma_profile_emd_loss(
            sig["p_shape"], target_shape, sig["area"], target_area, mask,
            mode=self.cfg.sigma_profile_loss, area_scale=self.cfg.sigma_area_scale,
            shape_weight=self.cfg.sigma_shape_weight, return_components=True,
        )
        loss = weight * loss_val
        if not torch.isfinite(loss):
            LOGGER.warning("Skipping non-finite sigma-profile auxiliary loss: %s", loss)
            return None, {}
        loss.backward()
        torch.nn.utils.clip_grad_norm_(list(self.model.parameters()), self.cfg.grad_clip)
        optimizer.step()
        self._maybe_release_device_cache()
        return float(loss.item()), {
            "sigma_profile": float(loss.item()),
            "sigma_shape": comps["sigma_shape"],
            "sigma_area": comps["sigma_area"],
        }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_sigma_loss.py -q`
Expected: PASS (3 tests).
Then the suite: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/ -q` → all green (existing `test_loss.py` / cosmo tests unaffected; the loss is additive-compatible).

- [ ] **Step 6: Commit**

```bash
git add src/tgnn_solv/loss.py src/tgnn_solv/config.py src/tgnn_solv/trainer.py tests/test_sigma_loss.py
git commit -m "fix(sigma): SUM-EMD shape loss + component logging + area_scale~75 (P0 H3)"
```

---

### Task 2: σ-bin contract assert + missing-area hard error in the dataset

**Why:** `dataset.__getitem__` infers the bin count from `sigma_p_*` columns and never validates it against `cfg.cosmo_sac_n_bins`; supervision and `delta_w` registration are purely positional, so any grid change is silently mis-registered (review M1). Also a missing `sigma_area` silently defaults to `0.0` (review L1). Make both loud.

**Files:**
- Modify: `src/tgnn_solv/data/dataset.py:188-213` (`__init__` — add `expected_sigma_bins`)
- Modify: `src/tgnn_solv/data/dataset.py:891-907` (`__getitem__` — assert + hard error)
- Modify: construction sites to thread `expected_sigma_bins` — `src/tgnn_solv/data/dataset.py:1002` and the loader builders in `scripts/train.py`
- Test: `tests/test_sigma_dataset_contract.py` (new)

**Interfaces:**
- Produces: `TGNNSolvDataset(..., expected_sigma_bins: int | None = None)`. When set and a row has `sigma_p_*` columns, `__getitem__` raises `ValueError` on a count mismatch or a missing/NaN `sigma_area`.
- Consumes: `cfg.cosmo_sac_n_bins` at construction.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sigma_dataset_contract.py`:

```python
import numpy as np
import pandas as pd
import pytest

from tgnn_solv.data.dataset import TGNNSolvDataset


def _sigma_row(n_bins: int, with_area: bool = True) -> pd.DataFrame:
    row = {
        "solute_smiles": "CCO",
        "solvent_smiles": "CCO",
        "temperature": 298.15,
        "has_solubility": False,
        "has_sigma_profile": True,
    }
    if with_area:
        row["sigma_area"] = 88.0
    shape = np.full(n_bins, 1.0 / n_bins)
    for i in range(n_bins):
        row[f"sigma_p_{i}"] = float(shape[i])
    return pd.DataFrame([row])


def test_bin_count_mismatch_raises():
    ds = TGNNSolvDataset(_sigma_row(50), cache=False, expected_sigma_bins=51)
    with pytest.raises(ValueError, match="cosmo_sac_n_bins"):
        _ = ds[0]


def test_correct_bin_count_ok():
    ds = TGNNSolvDataset(_sigma_row(51), cache=False, expected_sigma_bins=51)
    sample = ds[0]
    assert sample[2]["sigma_profile_target"].shape[0] == 51


def test_missing_area_raises_when_profile_present():
    ds = TGNNSolvDataset(_sigma_row(51, with_area=False), cache=False, expected_sigma_bins=51)
    with pytest.raises(ValueError, match="sigma_area"):
        _ = ds[0]
```

> Note: `ds[i]` returns the dataset's `(solute_data, solvent_data, targets)` tuple; `targets` is index `[2]`. If the local tuple order differs, adjust the index — confirm against an existing dataset test (e.g. `tests/test_dataset*.py`).

- [ ] **Step 2: Run test to verify it fails**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_sigma_dataset_contract.py -q`
Expected: FAIL — `expected_sigma_bins` is not a parameter yet (TypeError), and no validation exists.

- [ ] **Step 3: Add the constructor parameter**

In `src/tgnn_solv/data/dataset.py`, add to `TGNNSolvDataset.__init__` keyword args (after `cache: bool = True`, alongside the other keyword-only options, ~line 192):

```python
        expected_sigma_bins: int | None = None,
```

and store it near the other assignments (~line 214):

```python
        self.expected_sigma_bins = expected_sigma_bins
```

- [ ] **Step 4: Add validation in `__getitem__`**

Replace the σ block (`src/tgnn_solv/data/dataset.py:897-907`) with:

```python
        if sig_cols:
            if (
                self.expected_sigma_bins is not None
                and len(sig_cols) != self.expected_sigma_bins
            ):
                raise ValueError(
                    f"sigma-profile row has {len(sig_cols)} sigma_p_* columns but "
                    f"cfg.cosmo_sac_n_bins={self.expected_sigma_bins}; the profile "
                    f"grid is mis-registered against the COSMO-SAC layer grid."
                )
            has_sig = bool(self._row_bool(r, ("has_sigma_profile",)) or False)
            if has_sig and not (
                "sigma_area" in r.index and pd.notna(r["sigma_area"])
            ):
                raise ValueError(
                    "sigma-profile row has has_sigma_profile=True but is missing a "
                    "valid 'sigma_area'; refusing to default it to 0.0."
                )
            t["sigma_profile_target"] = torch.tensor(
                [float(r[c]) for c in sig_cols], dtype=torch.float
            )
            t["sigma_area_target"] = torch.tensor(
                float(r["sigma_area"]) if has_sig else 0.0,
                dtype=torch.float,
            )
            t["sigma_profile_mask"] = torch.tensor(has_sig, dtype=torch.bool)
```

- [ ] **Step 5: Thread `expected_sigma_bins` at construction sites**

At `src/tgnn_solv/data/dataset.py:1002` (the `dataset = TGNNSolvDataset(` helper call): add the kwarg `expected_sigma_bins=getattr(cfg, "cosmo_sac_n_bins", None)` — if the helper does not receive a `cfg`, add a `expected_sigma_bins: int | None = None` parameter to the helper and forward it.

In `scripts/train.py`, every `TGNNSolvDataset(...)` construction for train/val/test/aux loaders: add `expected_sigma_bins=cfg.cosmo_sac_n_bins`. (The σ stream only carries `sigma_p_*` columns, so the assert is a no-op for the main corpus but active for the aux stream.)

Verify the call sites: `KMP_DUPLICATE_LIB_OK=TRUE python -c "import ast,sys; [print(p) for p in ['done']]"` is not needed — instead grep them: `grep -rn "TGNNSolvDataset(" src/tgnn_solv scripts/train.py`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_sigma_dataset_contract.py -q` → PASS (3 tests).
Then: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/ -q` → all green.

- [ ] **Step 7: Commit**

```bash
git add src/tgnn_solv/data/dataset.py scripts/train.py tests/test_sigma_dataset_contract.py
git commit -m "fix(sigma): enforce bin-count==cfg.n_bins + missing-area hard error at load (P0 M1/L1)"
```

---

### Task 3: Builder reads `n_bins` from config + writes grid metadata

**Why:** `build_sigma_profile_aux_stream.py` hardcodes `--n-bins 51` independent of `cfg`, while `ingest` reads cfg — so the two can silently disagree (review M1). Make the default come from `TGNNSolvConfig`, and write grid endpoints into the summary so the artifact is self-describing.

**Files:**
- Modify: `scripts/data/build_sigma_profile_aux_stream.py:38-53` (argparse default) and the summary-writing block (after `out.to_csv`, ~line 183)
- Test: `tests/test_sigma_aux_builder.py` (new)

**Interfaces:**
- Produces: builder `--n-bins` default = `TGNNSolvConfig().cosmo_sac_n_bins`; summary JSON gains a `"grid"` object `{"n_bins", "sigma_min", "sigma_max"}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sigma_aux_builder.py`:

```python
import importlib

from tgnn_solv.config import TGNNSolvConfig


def test_builder_default_n_bins_matches_config():
    mod = importlib.import_module("scripts.data.build_sigma_profile_aux_stream")
    args = mod.parse_args.__wrapped__() if hasattr(mod.parse_args, "__wrapped__") else None
    # parse with no CLI args -> defaults
    import sys
    argv = sys.argv
    try:
        sys.argv = ["build_sigma_profile_aux_stream.py"]
        ns = mod.parse_args()
    finally:
        sys.argv = argv
    assert ns.n_bins == TGNNSolvConfig().cosmo_sac_n_bins


def test_grid_metadata_helper():
    mod = importlib.import_module("scripts.data.build_sigma_profile_aux_stream")
    grid = mod.grid_metadata(51)
    assert grid == {"n_bins": 51, "sigma_min": -0.025, "sigma_max": 0.025}
```

> If `scripts` is not importable as a package, the test runner needs `scripts/__init__.py` or a path shim. If `import scripts.data...` fails at collection, add an empty `scripts/__init__.py` and `scripts/data/__init__.py` (they are otherwise harmless) and re-run.

- [ ] **Step 2: Run test to verify it fails**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_sigma_aux_builder.py -q`
Expected: FAIL — default is hardcoded `51` literal (not config-derived) and `grid_metadata` does not exist.

- [ ] **Step 3: Implement config-derived default + metadata helper**

In `scripts/data/build_sigma_profile_aux_stream.py`, add an import near the top (with the existing `from tgnn_solv...` imports):

```python
from tgnn_solv.config import TGNNSolvConfig
```

Add a module-level helper above `parse_args`:

```python
def grid_metadata(n_bins: int) -> dict:
    """Self-describing sigma grid for the artifact summary."""
    cfg = TGNNSolvConfig()
    return {
        "n_bins": int(n_bins),
        "sigma_min": float(cfg.cosmo_sac_sigma_min),
        "sigma_max": float(cfg.cosmo_sac_sigma_max),
    }
```

Change the argparse default (line 46) from:

```python
    p.add_argument("--n-bins", type=int, default=51)
```

to:

```python
    p.add_argument("--n-bins", type=int, default=TGNNSolvConfig().cosmo_sac_n_bins)
```

- [ ] **Step 4: Write grid metadata into the summary**

Locate the summary-dict construction in `main()` (just before it is written to `args.summary_json`). Add the grid block to that dict:

```python
        "grid": grid_metadata(args.n_bins),
```

(If the summary dict is built inline at `json.dump(...)`, hoist it to a named `summary = {...}` first, then add the key.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_sigma_aux_builder.py -q` → PASS.
Then: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/ -q` → green.

- [ ] **Step 6: Commit**

```bash
git add scripts/data/build_sigma_profile_aux_stream.py tests/test_sigma_aux_builder.py
git commit -m "fix(sigma): builder n_bins from config + self-describing grid metadata (P0 M1)"
```

---

### Task 4: Interleave σ-aux dosing across the epoch

**Why:** The σ-aux steps fire on the *first* `sigma_steps_target` batches of each epoch (`trainer.py:1506`, `sigma_aux_steps < sigma_steps_target`), so the remaining SLE steps un-ground the head within the same epoch — the same front-loaded, under-dosed regime that left the crystal aux inconclusive (review H2). Spread the steps evenly with a stride.

**Files:**
- Create: a pure helper `_sigma_step_due(...)` in `src/tgnn_solv/trainer.py` (module-level function, above the trainer class)
- Modify: `src/tgnn_solv/trainer.py:1506-1515` (use the helper); compute `n_batches` available at loop start
- Test: `tests/test_sigma_dosing.py` (new)

**Interfaces:**
- Produces: `_sigma_step_due(batch_idx: int, n_batches: int, steps_done: int, steps_target: int) -> bool` — True at evenly spaced batch indices so that across `n_batches` batches exactly up to `steps_target` steps fire (one full interleaved pass, not a front burst).

- [ ] **Step 1: Write the failing test**

Create `tests/test_sigma_dosing.py`:

```python
from tgnn_solv.trainer import _sigma_step_due


def _fire_indices(n_batches: int, steps_target: int) -> list[int]:
    done = 0
    fired = []
    for i in range(n_batches):
        if _sigma_step_due(i, n_batches, done, steps_target):
            fired.append(i)
            done += 1
    return fired


def test_disabled_when_target_zero():
    assert _fire_indices(100, 0) == []


def test_fires_exactly_target_times():
    assert len(_fire_indices(100, 10)) == 10


def test_interleaved_not_frontloaded():
    fired = _fire_indices(100, 10)
    # front-loading would give [0..9]; interleaving spreads them out.
    assert fired != list(range(10))
    assert max(fired) >= 80  # last step lands near the end of the epoch


def test_more_target_than_batches_fires_every_batch():
    assert _fire_indices(5, 20) == [0, 1, 2, 3, 4]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_sigma_dosing.py -q`
Expected: FAIL — `_sigma_step_due` does not exist (ImportError).

- [ ] **Step 3: Implement the helper**

Add to `src/tgnn_solv/trainer.py` (module level, near the top after imports):

```python
def _sigma_step_due(
    batch_idx: int, n_batches: int, steps_done: int, steps_target: int
) -> bool:
    """Whether to run a sigma-aux step at this batch, interleaved across the epoch.

    Spreads ``steps_target`` steps evenly over ``n_batches`` (stride = n//target)
    rather than front-loading the first ``steps_target`` batches, so SLE steps do
    not un-ground the head within the same epoch.
    """
    if steps_target <= 0 or steps_done >= steps_target or n_batches <= 0:
        return False
    if steps_target >= n_batches:
        return True
    stride = n_batches // steps_target
    return batch_idx % stride == 0
```

- [ ] **Step 4: Wire it into the epoch loop**

The main loop iterates batches; ensure `n_batches` is known before it. If the loop is `for batch_idx, batch in enumerate(train_loader):`, add before the loop:

```python
        n_batches = len(train_loader)
```

Replace the front-loaded guard (`trainer.py:1506`):

```python
            if sigma_iter is not None and sigma_aux_steps < sigma_steps_target:
```

with:

```python
            if sigma_iter is not None and _sigma_step_due(
                batch_idx, n_batches, sigma_aux_steps, sigma_steps_target
            ):
```

(If the loop variable is not named `batch_idx`, rename via `for batch_idx, batch in enumerate(...)`; the crystal-aux block above uses the same loop — leave its behaviour unchanged.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_sigma_dosing.py -q` → PASS (4 tests).
Then: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/ -q` → green (trainer tests still pass; with `sigma_aux_steps_per_epoch=0` the path is inert).

- [ ] **Step 6: Commit**

```bash
git add src/tgnn_solv/trainer.py tests/test_sigma_dosing.py
git commit -m "fix(sigma): interleave aux dosing across epoch instead of front-loading (P0 H2)"
```

---

### Task 5: Acyclic-safe scaffold-leak guard

**Why:** `get_scaffold` returns `""` (empty) for acyclic molecules, and the builder's `if (scaf := get_scaffold(smi))` (build:100) treats empty as falsy, so acyclic solutes never enter the excluded set and bypass the "mandatory" leak guard (review L1). On current splits the test set is ring-bearing so it is latent, but it makes the scaffold-disjoint claim honest only for ring-bearing scaffolds and is a trap for future splits.

**Files:**
- Create: `scaffold_key` in `src/tgnn_solv/data/utils.py` (after `get_scaffold`, ~line 77)
- Modify: `scripts/data/build_sigma_profile_aux_stream.py:100,149` (use `scaffold_key`)
- Test: `tests/test_scaffold_key.py` (new)

**Interfaces:**
- Produces: `scaffold_key(smi: str) -> str | None` — the Murcko scaffold SMILES, or for acyclic molecules the canonical whole-molecule SMILES (so acyclic-vs-acyclic leakage is still caught); `None` only on RDKit failure.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scaffold_key.py`:

```python
from tgnn_solv.data.utils import scaffold_key


def test_ring_molecule_returns_scaffold():
    key = scaffold_key("c1ccccc1CCO")  # 2-phenylethanol
    assert key and "c1ccccc1" in key.replace("C", "")  # benzene ring retained


def test_acyclic_falls_back_to_canonical_smiles():
    # hexane is acyclic -> Murcko scaffold is empty; key must be non-empty so the
    # guard can dedup it against held-out acyclic molecules.
    key = scaffold_key("CCCCCC")
    assert key  # non-empty
    # two spellings of hexane map to the same key
    assert scaffold_key("CCCCCC") == scaffold_key("C(CC)CCC")


def test_invalid_smiles_returns_none():
    assert scaffold_key("not_a_smiles") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_scaffold_key.py -q`
Expected: FAIL — `scaffold_key` does not exist (ImportError).

- [ ] **Step 3: Implement `scaffold_key`**

In `src/tgnn_solv/data/utils.py`, after `get_scaffold` (line 77):

```python
def scaffold_key(smi: str) -> Optional[str]:
    """Leak-guard key: Murcko scaffold, or canonical SMILES for acyclic molecules.

    ``get_scaffold`` returns an empty string for acyclic molecules (no ring
    system), which silently bypasses scaffold-exclusion. This returns a non-empty
    key for every parseable molecule so acyclic-vs-acyclic leakage is still
    caught; ``None`` only when RDKit cannot parse the SMILES.
    """
    scaf = get_scaffold(smi)
    if scaf:
        return scaf
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True)
```

- [ ] **Step 4: Use it in the builder**

In `scripts/data/build_sigma_profile_aux_stream.py`:
- Change the import (line 35): `from tgnn_solv.data.utils import get_scaffold, scaffold_key`
- Line ~100, the excluded-set construction `if (scaf := get_scaffold(smi))` → `if (scaf := scaffold_key(smi))`
- Line 149, the filter `get_scaffold(s) in excluded` → `scaffold_key(s) in excluded`

- [ ] **Step 5: Run tests to verify they pass**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_scaffold_key.py -q` → PASS (3 tests).
Then: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/ -q` → green.

- [ ] **Step 6: Commit**

```bash
git add src/tgnn_solv/data/utils.py scripts/data/build_sigma_profile_aux_stream.py tests/test_scaffold_key.py
git commit -m "fix(sigma): acyclic-safe scaffold leak-guard key (P0 L1)"
```

---

### Task 6: Train/eval segment-iteration convergence regression test

**Why:** The COSMO-SAC segment fixed point runs `cosmo_sac_gamma_iter_train=8` in train and `=30` in eval (`config.py:184-185`), so the head is trained against one operator and scored under another (review L2, ~0.012 ln-units gap estimated). Rather than blindly inflate train compute, lock in evidence: a regression test asserting the truncation gap is below a documented tolerance across the experimental temperature range. If it ever fails, the fix is to raise `cosmo_sac_gamma_iter_train`.

**Files:**
- Create: `tests/test_cosmo_sac_iter_convergence.py` (new)
- (No source change unless the test fails — then bump `config.py:184`.)

**Interfaces:**
- Consumes: `CosmoSacLayer` (the differentiable layer in `layers.py`) and `TGNNSolvConfig`. The test constructs a layer, feeds representative on-grid profiles, and compares `ln Γ` (segment) at `n_iter=8` vs `n_iter=30`.

- [ ] **Step 1: Write the test (this is the deliverable)**

Create `tests/test_cosmo_sac_iter_convergence.py`:

```python
import torch

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer

TOL = 0.05  # ln-units; documents that n_iter=8 is converged for training


def _toy_profiles(cfg):
    n = cfg.cosmo_sac_n_bins
    grid = torch.linspace(cfg.cosmo_sac_sigma_min, cfg.cosmo_sac_sigma_max, n)
    # a polar-ish and a non-polar-ish on-grid profile (sum-1 shapes * area)
    polar = torch.softmax(-((grid - 0.012) ** 2) / 2e-5, dim=0)
    nonpolar = torch.softmax(-(grid ** 2) / 2e-5, dim=0)
    return polar.unsqueeze(0), nonpolar.unsqueeze(0)


def test_segment_fixed_point_converged_at_train_iters():
    cfg = TGNNSolvConfig()
    layer = CosmoSacLayer(cfg)
    p2, p1 = _toy_profiles(cfg)
    area = torch.tensor([100.0])
    x2 = torch.tensor([1e-3])
    # lowest experimental temperature is the hardest for convergence.
    for T in (273.15, 298.15, 373.15):
        Tt = torch.tensor([float(T)])
        g8 = layer.ln_gamma_2(p2 * area, p1 * area, area, area, x2, Tt, n_iter=8)
        g30 = layer.ln_gamma_2(p2 * area, p1 * area, area, area, x2, Tt, n_iter=30)
        assert torch.max((g8 - g30).abs()).item() < TOL, f"gap too large at T={T}"
```

> **Adapt to the real signature.** The exact `CosmoSacLayer` API (method name and how `n_iter` / profiles / area / x2 are passed) must be read from `src/tgnn_solv/layers.py:1447-1607` before finalizing this test — mirror what `model.py:520-533` / `tests/test_cosmo_sac.py` already do to call the layer. Keep the assertion (gap < `TOL` across the T-range); only the call shape changes.

- [ ] **Step 2: Run the test**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/test_cosmo_sac_iter_convergence.py -q`
Expected: PASS (the review estimates the gap ~0.012 ≪ 0.05).

- [ ] **Step 3: If it FAILS — bump train iters**

Only if the gap exceeds `TOL`: in `src/tgnn_solv/config.py:184` raise `cosmo_sac_gamma_iter_train` to the smallest value that passes (try 16, then 20). Re-run. Document the chosen value in the field comment.

- [ ] **Step 4: Run the suite**

Run: `KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/ -q` → green.

- [ ] **Step 5: Commit**

```bash
git add tests/test_cosmo_sac_iter_convergence.py src/tgnn_solv/config.py
git commit -m "test(sigma): segment fixed-point train/eval convergence regression (P0 L2)"
```

---

## Self-Review

**Spec coverage (P0 rows of the spec §6 table):**
- M1 (grid/bin contract) → Tasks 2 (dataset assert) + 3 (builder n_bins-from-cfg + metadata). ✓
- H2 (under-dosed/front-loaded) → Task 4 (interleave). ✓
- H3 (loss imbalance) → Task 1 (SUM-EMD + area_scale~75 + component logging). ✓
- H4 (area logging/rates) → partially Task 1 (separate area-term logging); the area-anchor **gate** is a P1 deliverable (stage-0), correctly deferred. ✓ (noted)
- L1 (acyclic guard; missing-area hard error) → Tasks 5 + 2. The **separate aux optimizer / Adam-state** part of L1 is deferred to P1 (freeze redesign) — documented in the spec's build sequence. ✓ (intentional deferral)
- L2 (train/eval iter) → Task 6. ✓
- M3 (pin config/seed), B1/B2/B3, H1, H5, M2, M4 → P1/P2/P3, not P0. ✓

**Placeholder scan:** No "TBD/handle edge cases" — every code step shows the code. Two tasks (2 step 5, 6 step 1) include an explicit *verify-the-call-shape* instruction with a concrete grep/file reference rather than a guess; these are verification actions, not placeholders, because the surrounding code is fully specified.

**Type consistency:** `sigma_profile_emd_loss` return type (`Tensor` vs `tuple[Tensor, dict]`) is consistent between Task 1's definition and its trainer caller; component keys `"sigma_shape"`/`"sigma_area"` match between loss and trainer. `expected_sigma_bins` name/type consistent between dataset `__init__`, `__getitem__`, and call sites. `_sigma_step_due` signature matches between helper, test, and loop wiring. `scaffold_key` signature matches between utils, builder, and test.

**Known adaptation points (read-before-edit, not placeholders):** dataset tuple index in Task 2 test; `scripts` package importability in Task 3 test; exact `CosmoSacLayer` call signature in Task 6 test. Each is flagged inline with what to check.
