# P1 — σ-manifold Learning (solvent symmetrization + sigma-warmup + freeze) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the COSMO-SAC σ-profile head learn the *right* σ-manifold from external VT-2005 data — ground both roles (solute + solvent), pretrain the head to convergence before the SLE curriculum, and freeze it during SLE so the curriculum can't pull it off-manifold.

**Architecture:** Five coordinated changes on top of P0. (1) Carve a scaffold-disjoint σ-TRAIN/VAL split from the VT-2005 pool. (2) Factor the σ forward+loss into a reusable `_sigma_forward_loss` helper. (3) Add solvent-role grounding (D2 symmetrization) inside that helper. (4) Add a `validate_sigma` no-grad eval and thread a σ-VAL loader. (5) Add a dedicated **sigma-warmup** pretraining routine (aux-VAL early-stop + area-anchor gate, its own optimizer + checkpoint) and freeze `head_sigma` during SLE phases 2/3.

**Tech Stack:** Python ≥3.10, PyTorch, pandas, RDKit, pytest. Package `tgnn_solv` under `src/`.

## Global Constraints

- **Env gotcha:** prefix any ad-hoc python that imports torch+rdkit with `KMP_DUPLICATE_LIB_OK=TRUE` (the suite sets this via `tests/conftest.py`).
- **Test interpreter / command:** `KMP_DUPLICATE_LIB_OK=TRUE /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest <path> -q`. Full suite is currently **305 passing** and must stay green. Single test: append `::test_name`.
- **Lint:** `ruff check src tests scripts` must pass (use the system `ruff`; it is not in the conda env).
- **Branch:** continue on `sigma-grounded-cosmosac` (P0 already merged into it: `_train_sigma_aux_batch` returns a component dict, `cosmo_sac_gamma_iter_train=16`, `sigma_area_scale=75.0`, `scaffold_key` exists in `data/utils.py`).
- **NAMING — do NOT call this "Stage 0".** `run_stage0_pretraining` / `--pretrain` is already the ZINC250k encoder contrastive pretrain (`pretrain_pipeline.py:187`, `scripts/train.py` "Stage 0" banner). The new σ pretrain is **"sigma-warmup"**: routine `run_sigma_warmup_pretraining`, config prefix `sigma_warmup_*`.
- **Defaults off:** every new config field defaults to the no-op value (`0`/`False`/`None`) so existing training and the NRTL path are unchanged. All new code must guard `if self.model.head_sigma is not None` (it is `None` for non-`cosmo_sac` models, `model.py:170`).
- **σ grid (verified):** 51 bins, `[-0.025, 0.025]` e/Å². Aux rows are self-solvent (`solvent_smiles==solute_smiles`), `has_solubility=False`, `has_sigma_profile=True`, columns `sigma_p_0..50` + `sigma_area` (raw cavity area Å²: water 43.27, ethanol 88.41, hexane 157.19).
- **No science change to existing behavior:** the symmetrization/warmup/freeze only take effect when their flags are enabled.

---

## File Structure

| File | Responsibility | Tasks |
|------|----------------|-------|
| `scripts/data/build_sigma_profile_aux_stream.py` | builder — emit a scaffold-disjoint σ-TRAIN/VAL split | 1 |
| `tests/sigma_fixtures.py` | shared test helper: tiny `cosmo_sac` model + synthetic σ batch/loader | 2 (create) |
| `src/tgnn_solv/trainer.py` | `_sigma_forward_loss` helper; solvent symmetrization; `validate_sigma`; σ-VAL threading; freeze `head_sigma` | 2,3,4,5 |
| `src/tgnn_solv/config.py` | new `sigma_aux_symmetrize`, `sigma_val_data`, `freeze_sigma_head_during_sle`, `sigma_warmup_*`, `sigma_area_anchor_*` fields | 3,4,5,6 |
| `src/tgnn_solv/pretrain_pipeline.py` | `run_sigma_warmup_pretraining` + checkpoint payload/apply extended with `sigma_head_state_dict` | 6 |
| `scripts/train.py` | CLI flags + build σ-VAL loader + invoke sigma-warmup + thread σ-VAL loader | 7 |
| `tests/test_sigma_val_split.py` | split is scaffold-disjoint, fraction, area preserved | 1 |
| `tests/test_sigma_forward_loss.py` | refactor parity + symmetrization grad flow | 2,3 |
| `tests/test_sigma_validate.py` | `validate_sigma` no-grad metrics | 4 |
| `tests/test_sigma_freeze.py` | freeze toggling per phase | 5 |
| `tests/test_sigma_warmup.py` | warmup reduces EMD, checkpoint carries σ head, area gate | 6 |

**Dependency order:** Task 1 (data, standalone) → Task 2 (refactor + fixtures) → Tasks 3,4,5 (build on the helper/fixtures) → Task 6 (warmup, uses helper + split + config) → Task 7 (CLI integration). Do them in this order.

---

### Task 1: Scaffold-disjoint σ-TRAIN/VAL split in the builder

**Why:** Stage-0 sigma-warmup needs an aux-VAL set for early-stop, and it must be scaffold-disjoint from σ-TRAIN (and already disjoint from the solubility test/val via the existing leak guard). The VT-2005 pool is mostly acyclic, so `data/split.py:scaffold_split` (uses `get_scaffold` → `""` for acyclic → dumps all into train) is WRONG here; use the acyclic-safe `scaffold_key`.

**Files:**
- Modify: `scripts/data/build_sigma_profile_aux_stream.py` (`parse_args` ~line 50; after `out = pd.DataFrame(...)` ~line 192; summary block ~197-206)
- Test: `tests/test_sigma_val_split.py` (new)

**Interfaces:**
- Produces: builder gains `--val-fraction FLOAT` (default 0.0 = no split), `--split-seed INT` (default 0), `--output-val-csv PATH` (default `notebooks/data/processed_sigma_aux_stream/sigma_val.csv`). When `--val-fraction>0`, whole `scaffold_key` groups go to VAL until the fraction is met; TRAIN/VAL `scaffold_key` sets are provably disjoint; `sigma_area` preserved on both sides. A new module-level helper `split_by_scaffold(df, val_fraction, seed) -> tuple[DataFrame, DataFrame]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sigma_val_split.py`:

```python
import importlib

import numpy as np
import pandas as pd

mod = importlib.import_module("scripts.data.build_sigma_profile_aux_stream")
from tgnn_solv.data.utils import scaffold_key


def _pool(n_bins=51):
    # mix of acyclic (alkanes/alcohols) and ring-bearing molecules
    smis = ["CCO", "CCCCCC", "CC(C)O", "CCCCCCCC", "c1ccccc1", "c1ccccc1O",
            "c1ccncc1", "C1CCCCC1", "CCN", "CCCCO", "c1ccc2ccccc2c1", "CC(=O)O"]
    rows = []
    shape = np.full(n_bins, 1.0 / n_bins)
    for i, s in enumerate(smis):
        r = {"solute_smiles": s, "solvent_smiles": s, "has_sigma_profile": True,
             "sigma_area": 40.0 + i}
        for b in range(n_bins):
            r[f"sigma_p_{b}"] = float(shape[b])
        rows.append(r)
    return pd.DataFrame(rows)


def test_split_is_scaffold_disjoint_and_preserves_area():
    df = _pool()
    train, val = mod.split_by_scaffold(df, val_fraction=0.3, seed=0)
    assert len(val) > 0 and len(train) > 0
    train_keys = {scaffold_key(s) for s in train["solute_smiles"]}
    val_keys = {scaffold_key(s) for s in val["solute_smiles"]}
    assert train_keys.isdisjoint(val_keys)  # no scaffold leak
    # area column survives the split untouched
    assert set(train["sigma_area"]).union(val["sigma_area"]) == set(df["sigma_area"])


def test_split_deterministic_under_seed():
    df = _pool()
    a = mod.split_by_scaffold(df, val_fraction=0.3, seed=7)[1]["solute_smiles"].tolist()
    b = mod.split_by_scaffold(df, val_fraction=0.3, seed=7)[1]["solute_smiles"].tolist()
    assert a == b


def test_val_fraction_zero_returns_empty_val():
    df = _pool()
    train, val = mod.split_by_scaffold(df, val_fraction=0.0, seed=0)
    assert len(val) == 0 and len(train) == len(df)
```

> If `import scripts.data...` fails at collection, the P0 task already added `scripts/__init__.py` + `scripts/data/__init__.py`; confirm they exist.

- [ ] **Step 2: Run test to verify it fails**

Run: `KMP_DUPLICATE_LIB_OK=TRUE /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/test_sigma_val_split.py -q`
Expected: FAIL — `split_by_scaffold` does not exist (AttributeError).

- [ ] **Step 3: Implement `split_by_scaffold`**

In `scripts/data/build_sigma_profile_aux_stream.py`, add a module-level helper (near the other helpers, after `_empty_row_template`):

```python
def split_by_scaffold(
    df: pd.DataFrame, val_fraction: float, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Whole-scaffold-group TRAIN/VAL split so the two sides share no scaffold_key.

    Groups by the acyclic-safe ``scaffold_key`` (Murcko, or canonical SMILES for
    acyclic molecules) and assigns entire groups to VAL until ``val_fraction`` of
    rows is reached. Deterministic under ``seed``. ``val_fraction<=0`` -> empty VAL.
    """
    if val_fraction <= 0.0 or len(df) == 0:
        return df.copy(), df.iloc[0:0].copy()
    keys = df["solute_smiles"].astype(str).map(scaffold_key)
    groups: dict[str, list[int]] = {}
    for idx, k in zip(df.index, keys):
        groups.setdefault(str(k), []).append(idx)
    unique = sorted(groups)  # stable base order before the seeded shuffle
    rng = np.random.RandomState(seed)
    rng.shuffle(unique)
    target = val_fraction * len(df)
    val_idx: list[int] = []
    for k in unique:
        if len(val_idx) >= target:
            break
        val_idx.extend(groups[k])
    val_set = set(val_idx)
    val = df.loc[df.index.isin(val_set)].copy()
    train = df.loc[~df.index.isin(val_set)].copy()
    return train, val
```

- [ ] **Step 4: Wire it into `parse_args` + `main`**

In `parse_args` add:

```python
    p.add_argument("--val-fraction", type=float, default=0.0)
    p.add_argument("--split-seed", type=int, default=0)
    p.add_argument("--output-val-csv",
                   default="notebooks/data/processed_sigma_aux_stream/sigma_val.csv")
```

In `main`, after `out = pd.DataFrame(rows, columns=out_cols)` and before writing, replace the single-write with:

```python
    train_out, val_out = split_by_scaffold(out, args.val_fraction, args.split_seed)
    Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)
    train_out.to_csv(args.output_csv, index=False)
    if len(val_out) > 0:
        Path(args.output_val_csv).parent.mkdir(parents=True, exist_ok=True)
        val_out.to_csv(args.output_val_csv, index=False)
        # fail-closed disjointness guard (mirrors _excluded_scaffolds style)
        tr = {scaffold_key(s) for s in train_out["solute_smiles"]}
        va = {scaffold_key(s) for s in val_out["solute_smiles"]}
        if not tr.isdisjoint(va):
            raise SystemExit("sigma TRAIN/VAL scaffold leak detected; aborting.")
```

Add to the summary dict: `"n_train": int(len(train_out)), "n_val": int(len(val_out)), "val_fraction_actual": (len(val_out) / max(len(out), 1))`.

- [ ] **Step 5: Run tests + suite**

Run: `KMP_DUPLICATE_LIB_OK=TRUE ... -m pytest tests/test_sigma_val_split.py -q` → PASS (3).
Then `... -m pytest tests/ -q` → green.

- [ ] **Step 6: Commit**

```bash
git add scripts/data/build_sigma_profile_aux_stream.py tests/test_sigma_val_split.py
git commit -m "feat(sigma): scaffold-disjoint TRAIN/VAL split in aux builder (P1 prereq)"
```

---

### Task 2: Factor `_sigma_forward_loss` + shared test fixtures

**Why:** The σ forward+loss currently lives inline in `_train_sigma_aux_batch`. Stage-0 warmup (Task 6) and `validate_sigma` (Task 4) must reuse the exact same forward so they ground the SAME embedding the SLE path sees. Factor it once; this task is a pure refactor (no behavior change).

**Files:**
- Modify: `src/tgnn_solv/trainer.py` (`_train_sigma_aux_batch` body, ~884-911)
- Create: `tests/sigma_fixtures.py` (shared minimal model + batch)
- Test: `tests/test_sigma_forward_loss.py` (new)

**Interfaces:**
- Produces: `TGNNSolvTrainer._sigma_forward_loss(self, batch, *, role: str = "solute") -> tuple[Tensor, dict[str, float]]` — encodes `sol_batch` with `role`, applies the matching FP adapter, runs `model.head_sigma`, returns `(weighted_emd_tensor_without_phase_weight, {"sigma_profile","sigma_shape","sigma_area"})`. Raises nothing; returns `(zero_tensor, {...0})` if the mask is empty. `_train_sigma_aux_batch` consumes it.
- `tests/sigma_fixtures.py` produces `make_tiny_cosmo_trainer_and_batch() -> tuple[TGNNSolvTrainer, batch]`.

- [ ] **Step 1: Create the shared fixture helper**

Create `tests/sigma_fixtures.py`. Mirror the construction used in the existing `tests/test_sigma_aux_stream.py` and `tests/test_cosmo_sac.py` (read them first for the exact dataset/loader/model construction in this repo), then expose:

```python
"""Shared helpers for sigma-grounding tests: a tiny cosmo_sac trainer + batch."""
import numpy as np
import pandas as pd
import torch

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.model import TGNNSolv
from tgnn_solv.trainer import TGNNSolvTrainer
from tgnn_solv.data.dataset import TGNNSolvDataset
from torch_geometric.loader import DataLoader


def tiny_cosmo_config() -> TGNNSolvConfig:
    cfg = TGNNSolvConfig()
    cfg.activity_model = "cosmo_sac"
    cfg.hidden_dim = 32
    cfg.num_layers = 2
    return cfg


def _sigma_pool_df(n=4, n_bins=51) -> pd.DataFrame:
    smis = ["CCO", "CCCCCC", "c1ccccc1", "CC(C)O"][:n]
    rows = []
    shape = np.random.RandomState(0).dirichlet(np.ones(n_bins), size=n)
    for i, s in enumerate(smis):
        r = {"solute_smiles": s, "solvent_smiles": s, "temperature": 298.15,
             "has_solubility": False, "has_sigma_profile": True,
             "sigma_area": 40.0 + 10.0 * i}
        for b in range(n_bins):
            r[f"sigma_p_{b}"] = float(shape[i, b])
        rows.append(r)
    return pd.DataFrame(rows)


def make_tiny_cosmo_trainer_and_loader():
    cfg = tiny_cosmo_config()
    model = TGNNSolv(cfg)
    trainer = TGNNSolvTrainer(model, cfg, device=torch.device("cpu"))
    ds = TGNNSolvDataset(_sigma_pool_df(), cache=False,
                         expected_sigma_bins=cfg.cosmo_sac_n_bins)
    loader = DataLoader(ds, batch_size=2, shuffle=False,
                        collate_fn=getattr(ds, "collate_fn", None))
    return trainer, loader


def first_batch(loader):
    return next(iter(loader))
```

> Adapt the exact `TGNNSolvDataset`/`DataLoader`/`collate_fn` construction to match how `tests/test_sigma_aux_stream.py` builds its loader in THIS repo (the collate and batch tuple shape must match what `_train_sigma_aux_batch` expects: `(sol_batch, slv_batch, targets)`). If the existing test exposes a builder, import and reuse it instead of duplicating.

- [ ] **Step 2: Write the failing refactor-parity test**

Create `tests/test_sigma_forward_loss.py`:

```python
import torch

from tests.sigma_fixtures import make_tiny_cosmo_trainer_and_loader, first_batch


def test_sigma_forward_loss_returns_tensor_and_components():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    batch = first_batch(loader)
    loss, comps = trainer._sigma_forward_loss(batch, role="solute")
    assert isinstance(loss, torch.Tensor) and loss.requires_grad
    assert torch.isfinite(loss)
    assert set(comps) >= {"sigma_profile", "sigma_shape", "sigma_area"}


def test_train_sigma_aux_batch_still_works_after_refactor():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    batch = first_batch(loader)
    trainer.cfg.sigma_aux_phase1_weight = 1.0  # ensure weight>0 so it runs
    loss_val, d = trainer._train_sigma_aux_batch(batch, trainer._build_optimizer(1), phase=1)
    assert loss_val is None or (isinstance(loss_val, float) and loss_val >= 0.0)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `KMP_DUPLICATE_LIB_OK=TRUE ... -m pytest tests/test_sigma_forward_loss.py -q`
Expected: FAIL — `_sigma_forward_loss` does not exist.

- [ ] **Step 4: Implement the helper and call it from `_train_sigma_aux_batch`**

Add the method to `TGNNSolvTrainer` (place it just above `_train_sigma_aux_batch`):

```python
    def _sigma_forward_loss(
        self, batch, *, role: str = "solute"
    ) -> tuple[Tensor, dict[str, float]]:
        """Encode the pure component (in sol_batch) under ``role`` and score its
        predicted sigma-profile against the external label. Returns the unscaled
        EMD loss tensor (grad-bearing) and a component dict. Empty mask -> zero."""
        model = self.model
        sol_batch, _slv_batch, targets = self._move_batch_to_device(batch)
        mask = targets.get("sigma_profile_mask")
        target_shape = targets.get("sigma_profile_target")
        target_area = targets.get("sigma_area_target")
        if (not isinstance(mask, Tensor) or not bool(mask.any().item())
                or not isinstance(target_shape, Tensor)
                or not isinstance(target_area, Tensor)):
            zero = torch.zeros((), device=self.device)
            return zero, {"sigma_profile": 0.0, "sigma_shape": 0.0, "sigma_area": 0.0}
        enc_t_feat = model._encoder_temp_features(make_temperature_features(targets["T"]))
        _, g_payload, _, _ = model._encode_and_readout(sol_batch, role, temp_feat=enc_t_feat)
        g = g_payload["value"]
        if model.cfg.use_morgan_features:
            fp = targets.get("solute_morgan_fp")
            if isinstance(fp, Tensor):
                adapter = model.solute_fp_adapter if role == "solute" else model.solvent_fp_adapter
                g = g + model.fp_pre_scale * adapter(fp.to(g))
        sig = model.head_sigma(g)
        loss_val, comps = sigma_profile_emd_loss(
            sig["p_shape"], target_shape, sig["area"], target_area, mask,
            mode=self.cfg.sigma_profile_loss, area_scale=self.cfg.sigma_area_scale,
            shape_weight=self.cfg.sigma_shape_weight, return_components=True,
        )
        return loss_val, comps
```

Then replace the inline forward+loss in `_train_sigma_aux_batch` (current ~884-902) so it calls the helper, keeping the existing guard/weight/backward/step:

```python
        weight = self._sigma_aux_weight(phase)
        if weight <= 0.0:
            return None, {}
        optimizer.zero_grad()
        loss_val, comps = self._sigma_forward_loss(batch, role="solute")
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

> Note: the head/mask early-returns that used to live before the forward now live inside `_sigma_forward_loss` (empty mask → zero). Keep the `head_sigma is None` and coordinate-descent `phase==2` early-returns at the TOP of `_train_sigma_aux_batch` (they were ~862-868 in P0) — those are phase gating that must NOT move into the shared helper.

- [ ] **Step 5: Run tests + suite**

Run: `... -m pytest tests/test_sigma_forward_loss.py -q` → PASS.
Then `... -m pytest tests/ -q` → green (existing `test_sigma_aux_stream.py` must still pass — the refactor is behavior-preserving).

- [ ] **Step 6: Commit**

```bash
git add src/tgnn_solv/trainer.py tests/sigma_fixtures.py tests/test_sigma_forward_loss.py
git commit -m "refactor(sigma): factor _sigma_forward_loss for reuse by warmup+validate (P1)"
```

---

### Task 3: Solvent-role grounding (D2 symmetrization)

**Why:** Today only the solute-role embedding is grounded. At low x2 the SLE residual is dominated by the *solvent* profile, produced by the same head through the separate `solvent_adapter` (`layers.py:275-278`), which VT-2005 never supervises. Ground both roles against the same target.

**Files:**
- Modify: `src/tgnn_solv/config.py` (add `sigma_aux_symmetrize`)
- Modify: `src/tgnn_solv/trainer.py` (`_train_sigma_aux_batch` to average solute+solvent passes)
- Test: `tests/test_sigma_forward_loss.py` (extend)

**Interfaces:**
- Consumes: `_sigma_forward_loss(batch, role=...)` (Task 2).
- Produces: `cfg.sigma_aux_symmetrize: bool = True`. When true, `_train_sigma_aux_batch` averages the solute-role and solvent-role EMD losses in a single backward; grad reaches BOTH `solute_adapter` and `solvent_adapter`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sigma_forward_loss.py`:

```python
def _grad_norm(module):
    import torch
    g = [p.grad.detach().abs().sum() for p in module.parameters() if p.grad is not None]
    return float(torch.stack(g).sum()) if g else 0.0


def test_symmetrization_grounds_both_role_adapters():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    trainer.cfg.sigma_aux_symmetrize = True
    trainer.cfg.sigma_aux_phase1_weight = 1.0
    batch = first_batch(loader)
    opt = trainer._build_optimizer(1)
    trainer._train_sigma_aux_batch(batch, opt, phase=1)
    enc = trainer.model.gnn
    # both role adapters must receive gradient when symmetrize is on
    assert _grad_norm(enc.solute_adapter) > 0.0
    assert _grad_norm(enc.solvent_adapter) > 0.0


def test_no_symmetrization_skips_solvent_adapter():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    trainer.cfg.sigma_aux_symmetrize = False
    trainer.cfg.sigma_aux_phase1_weight = 1.0
    batch = first_batch(loader)
    opt = trainer._build_optimizer(1)
    trainer._train_sigma_aux_batch(batch, opt, phase=1)
    enc = trainer.model.gnn
    assert _grad_norm(enc.solute_adapter) > 0.0
    assert _grad_norm(enc.solvent_adapter) == 0.0
```

> `enc.solute_adapter`/`solvent_adapter` exist on `GNNEncoder` (`layers.py:202-207`) in the default `shared_residual` mode. If `tiny_cosmo_config` ends up with a non-default encoder, set `cfg.encoder_role_mode = "shared_residual"` in the fixture.

- [ ] **Step 2: Run test to verify it fails**

Run: `... -m pytest tests/test_sigma_forward_loss.py -k symmetri -q`
Expected: FAIL — `sigma_aux_symmetrize` not a config field (AttributeError) and solvent adapter gets no grad.

- [ ] **Step 3: Add the config field**

In `src/tgnn_solv/config.py`, in the sigma block (after `sigma_shape_weight`):

```python
    sigma_aux_symmetrize: bool = True  # ground solute AND solvent role embeddings
```

- [ ] **Step 4: Average both role passes in `_train_sigma_aux_batch`**

Replace the single `_sigma_forward_loss` call in `_train_sigma_aux_batch` (from Task 2) with:

```python
        optimizer.zero_grad()
        loss_sol, comps = self._sigma_forward_loss(batch, role="solute")
        if self.cfg.sigma_aux_symmetrize:
            loss_slv, comps_slv = self._sigma_forward_loss(batch, role="solvent")
            loss_val = 0.5 * (loss_sol + loss_slv)
            comps = {k: 0.5 * (comps[k] + comps_slv[k]) for k in comps}
        else:
            loss_val = loss_sol
        loss = weight * loss_val
```

(keep the `torch.isfinite` check, `loss.backward()`, clip, `optimizer.step()`, and the return dict from Task 2 unchanged below this.)

- [ ] **Step 5: Run tests + suite**

Run: `... -m pytest tests/test_sigma_forward_loss.py -q` → PASS (4).
Then `... -m pytest tests/ -q` → green.

- [ ] **Step 6: Commit**

```bash
git add src/tgnn_solv/config.py src/tgnn_solv/trainer.py tests/test_sigma_forward_loss.py
git commit -m "feat(sigma): D2 solvent-role grounding (symmetrized aux) (P1)"
```

---

### Task 4: `validate_sigma` no-grad eval + σ-VAL loader threading

**Why:** Sigma-warmup (Task 6) needs an aux-VAL EMD metric for early-stop and the area-anchor gate. Add a no-grad validate that reuses `_sigma_forward_loss`, and thread a `sigma_val_loader` through the public training entry points.

**Files:**
- Modify: `src/tgnn_solv/config.py` (`sigma_val_data`)
- Modify: `src/tgnn_solv/trainer.py` (`validate_sigma`; add `sigma_val_loader` kwarg to `train_phase` ~1764 and `train_full` ~1991)
- Test: `tests/test_sigma_validate.py` (new)

**Interfaces:**
- Produces: `TGNNSolvTrainer.validate_sigma(self, loader) -> dict[str, float]` (no_grad) returning aggregated `{"sigma_profile","sigma_shape","sigma_area","sigma_area_mae"}` over the loader's masked rows, where `sigma_area_mae` is the mean absolute area error in **raw Å²** (for the anchor gate). `cfg.sigma_val_data: Optional[str] = None`. `train_phase`/`train_full` accept `sigma_val_loader: DataLoader | None = None` (stored on `self` or passed through; not consumed yet beyond storage in this task).

- [ ] **Step 1: Write the failing test**

Create `tests/test_sigma_validate.py`:

```python
import torch

from tests.sigma_fixtures import make_tiny_cosmo_trainer_and_loader


def test_validate_sigma_no_grad_metrics():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    metrics = trainer.validate_sigma(loader)
    assert {"sigma_profile", "sigma_shape", "sigma_area", "sigma_area_mae"} <= set(metrics)
    assert all(isinstance(v, float) for v in metrics.values())
    assert metrics["sigma_area_mae"] >= 0.0
    # validate must not leave grad on parameters
    assert all(p.grad is None for p in trainer.model.head_sigma.parameters())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `... -m pytest tests/test_sigma_validate.py -q`
Expected: FAIL — `validate_sigma` does not exist.

- [ ] **Step 3: Implement `validate_sigma`**

Add to `TGNNSolvTrainer` (near `validate`, ~1633):

```python
    @torch.no_grad()
    def validate_sigma(self, loader) -> dict[str, float]:
        """Aggregate sigma EMD + raw-Å² area MAE over a sigma loader (for warmup
        early-stop and the area-anchor gate). No-grad; head_sigma must exist."""
        self.model.eval()
        tot = {"sigma_profile": 0.0, "sigma_shape": 0.0, "sigma_area": 0.0}
        area_abs, n_area, n = 0.0, 0, 0
        for batch in loader:
            loss_val, comps = self._sigma_forward_loss(batch, role="solute")
            if self.cfg.sigma_aux_symmetrize:
                _, comps_slv = self._sigma_forward_loss(batch, role="solvent")
                comps = {k: 0.5 * (comps[k] + comps_slv[k]) for k in comps}
            for k in tot:
                tot[k] += comps[k]
            n += 1
            # raw area MAE for the anchor gate
            sol_batch, _s, targets = self._move_batch_to_device(batch)
            mask = targets.get("sigma_profile_mask")
            if isinstance(mask, Tensor) and bool(mask.any().item()):
                enc_t = self.model._encoder_temp_features(
                    make_temperature_features(targets["T"]))
                _, gp, _, _ = self.model._encode_and_readout(sol_batch, "solute", temp_feat=enc_t)
                pred_area = self.model.head_sigma(gp["value"])["area"][mask.bool()]
                tgt_area = targets["sigma_area_target"][mask.bool()]
                area_abs += float((pred_area - tgt_area).abs().sum().item())
                n_area += int(mask.sum().item())
        out = {k: v / max(n, 1) for k, v in tot.items()}
        out["sigma_area_mae"] = area_abs / max(n_area, 1)
        return out
```

- [ ] **Step 4: Add config + thread the loader kwarg**

In `config.py` sigma block: `sigma_val_data: Optional[str] = None`.

In `trainer.py`, add `sigma_val_loader: DataLoader | None = None` to the signatures of `train_phase` (~1764) and `train_full` (~1991), and in `train_full` store it: `self._sigma_val_loader = sigma_val_loader` (so Task 6's warmup, called from `train_full`, can read it). Pass it through `train_full` → `train_phase` for symmetry even though only warmup consumes it now.

- [ ] **Step 5: Run tests + suite**

Run: `... -m pytest tests/test_sigma_validate.py -q` → PASS.
Then `... -m pytest tests/ -q` → green.

- [ ] **Step 6: Commit**

```bash
git add src/tgnn_solv/config.py src/tgnn_solv/trainer.py tests/test_sigma_validate.py
git commit -m "feat(sigma): validate_sigma no-grad eval + sigma_val_loader plumbing (P1)"
```

---

### Task 5: Freeze `head_sigma` during SLE phases 2/3

**Why:** During SLE, the solubility loss trains `head_sigma` every step and (per the project thesis) pulls it onto the wrong σ-manifold. After warmup grounds it, freeze it during phases 2/3 so the manifold is held; also skip the in-curriculum σ-aux stream when frozen (it would otherwise backprop only into the encoder with no head grad).

**Files:**
- Modify: `src/tgnn_solv/config.py` (`freeze_sigma_head_during_sle`)
- Modify: `src/tgnn_solv/trainer.py` (`_configure_phase_branch_training` ~319; the in-curriculum σ-step guard)
- Test: `tests/test_sigma_freeze.py` (new)

**Interfaces:**
- Produces: `cfg.freeze_sigma_head_during_sle: bool = False`. When true and `phase >= 2`, `head_sigma.parameters()` are `requires_grad=False` after the blanket unfreeze, in BOTH standard and coordinate_descent modes; and `_train_sigma_aux_batch` early-returns `(None, {})` for `phase >= 2` when the head is frozen.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sigma_freeze.py`:

```python
from tests.sigma_fixtures import tiny_cosmo_config
from tgnn_solv.model import TGNNSolv
from tgnn_solv.trainer import TGNNSolvTrainer
import torch


def _trainer():
    cfg = tiny_cosmo_config()
    cfg.freeze_sigma_head_during_sle = True
    model = TGNNSolv(cfg)
    return TGNNSolvTrainer(model, cfg, device=torch.device("cpu"))


def test_head_frozen_in_phase2_unfrozen_in_phase1():
    t = _trainer()
    t._configure_phase_branch_training(1)
    assert all(p.requires_grad for p in t.model.head_sigma.parameters())
    t._configure_phase_branch_training(2)
    assert all(not p.requires_grad for p in t.model.head_sigma.parameters())
    t._configure_phase_branch_training(3)
    assert all(not p.requires_grad for p in t.model.head_sigma.parameters())


def test_flag_off_keeps_head_trainable():
    cfg = tiny_cosmo_config()
    cfg.freeze_sigma_head_during_sle = False
    t = TGNNSolvTrainer(TGNNSolv(cfg), cfg, device=torch.device("cpu"))
    t._configure_phase_branch_training(2)
    assert all(p.requires_grad for p in t.model.head_sigma.parameters())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `... -m pytest tests/test_sigma_freeze.py -q`
Expected: FAIL — `freeze_sigma_head_during_sle` not a field; head stays trainable in phase 2.

- [ ] **Step 3: Add config + freeze logic**

In `config.py` sigma block: `freeze_sigma_head_during_sle: bool = False`.

In `trainer.py::_configure_phase_branch_training`, AFTER the blanket unfreeze (`for param in self.model.parameters(): param.requires_grad = True`, ~325-326) and BEFORE the `if self._resolved_branch_training_mode() != "coordinate_descent": return` early-return (~331), insert:

```python
        if (getattr(self.cfg, "freeze_sigma_head_during_sle", False)
                and phase >= 2 and self.model.head_sigma is not None):
            self._set_requires_grad(self.model.head_sigma, False)
```

- [ ] **Step 4: Skip the in-curriculum σ-stream when the head is frozen**

In `_train_sigma_aux_batch`, extend the existing top-of-method guards (the `head_sigma is None` / coordinate-descent `phase==2` early returns) with:

```python
        if (getattr(self.cfg, "freeze_sigma_head_during_sle", False) and phase >= 2):
            return None, {}
```

- [ ] **Step 5: Run tests + suite**

Run: `... -m pytest tests/test_sigma_freeze.py -q` → PASS.
Then `... -m pytest tests/ -q` → green.

- [ ] **Step 6: Commit**

```bash
git add src/tgnn_solv/config.py src/tgnn_solv/trainer.py tests/test_sigma_freeze.py
git commit -m "feat(sigma): freeze head_sigma during SLE phases 2/3 (P1 D3/H1)"
```

---

### Task 6: `run_sigma_warmup_pretraining` + area-anchor gate + checkpoint

**Why:** Pretrain `encoder + head_sigma` on the σ pool to convergence (aux-VAL early-stop) BEFORE the crystal curriculum, verify the predicted areas track VT-2005 anchors (area-gate), and persist the σ head so the SLE run starts from a grounded manifold. The existing `Pretrainer` cannot do this (wrong heads/data/loss), so this is a new routine reusing `_sigma_forward_loss` + `validate_sigma` + the checkpoint helpers.

**Files:**
- Modify: `src/tgnn_solv/config.py` (`sigma_warmup_*`, `sigma_area_anchor_*`)
- Modify: `src/tgnn_solv/pretrain_pipeline.py` (`run_sigma_warmup_pretraining`; extend `build_pretrain_checkpoint_payload`/`apply_pretrained_encoder_checkpoint` with `sigma_head_state_dict`)
- Test: `tests/test_sigma_warmup.py` (new)

**Interfaces:**
- Consumes: `TGNNSolvTrainer._sigma_forward_loss`, `validate_sigma` (Tasks 2,4); `scripts/train.py:load_data` for loaders (or build a loader directly in the test).
- Produces:
  - `run_sigma_warmup_pretraining(model, config, *, device, sigma_train_loader, sigma_val_loader=None, save_path=None) -> dict` — trains `head_sigma` (+ encoder `gnn`/`readout`) on its OWN `AdamW` at `cfg.sigma_warmup_lr` for up to `cfg.sigma_warmup_epochs` with aux-VAL early-stop (patience `cfg.sigma_warmup_patience`, min epochs `cfg.sigma_warmup_min_epochs`); restores best state; computes the area-anchor gate from `validate_sigma(...)["sigma_area_mae"]`; returns a metadata dict `{"history","best_val","area_mae","area_gate_passed","epochs_run"}`. Guards `head_sigma is None`.
  - Config: `sigma_warmup_epochs: int = 0`, `sigma_warmup_lr: float = 3e-4`, `sigma_warmup_patience: int = 20`, `sigma_warmup_min_epochs: int = 5`, `sigma_area_anchor_mae_tol: float = 30.0` (Å²), `sigma_area_anchor_strict: bool = False`.
  - Checkpoint payload gains `sigma_head_state_dict` (when `head_sigma is not None`); `apply_pretrained_encoder_checkpoint` loads it back (guarded, backward-compatible — old checkpoints without the key still load).

- [ ] **Step 1: Write the failing test**

Create `tests/test_sigma_warmup.py`:

```python
import torch

from tests.sigma_fixtures import make_tiny_cosmo_trainer_and_loader, tiny_cosmo_config
from tgnn_solv.pretrain_pipeline import (
    run_sigma_warmup_pretraining,
    build_pretrain_checkpoint_payload,
    apply_pretrained_encoder_checkpoint,
)


def test_warmup_reduces_train_emd_and_reports_gate():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    cfg = trainer.cfg
    cfg.sigma_warmup_epochs = 8
    cfg.sigma_warmup_min_epochs = 2
    before = trainer.validate_sigma(loader)["sigma_profile"]
    meta = run_sigma_warmup_pretraining(
        trainer.model, cfg, device=torch.device("cpu"),
        sigma_train_loader=loader, sigma_val_loader=loader)
    after = trainer.validate_sigma(loader)["sigma_profile"]
    assert after <= before  # warmup should not worsen the fit on the same data
    assert "area_mae" in meta and "area_gate_passed" in meta


def test_checkpoint_roundtrips_sigma_head():
    cfg = tiny_cosmo_config()
    from tgnn_solv.model import TGNNSolv
    model = TGNNSolv(cfg)
    payload = build_pretrain_checkpoint_payload(
        model=model, config=cfg, pretrain_history={}, pretrain_source="sigma_warmup",
        pretrain_epochs=0, pretrain_batch_size=0, pretrain_lr=0.0, smiles_count=0)
    assert "sigma_head_state_dict" in payload
    model2 = TGNNSolv(cfg)
    apply_pretrained_encoder_checkpoint(model2, payload, strict=False)
    for (k, a), (_, b) in zip(model.head_sigma.state_dict().items(),
                              model2.head_sigma.state_dict().items()):
        assert torch.allclose(a, b)
```

> `build_pretrain_checkpoint_payload`'s exact required kwargs may differ — read its current signature (`pretrain_pipeline.py:82`) and pass what it needs; the assertion that matters is that `sigma_head_state_dict` is present and round-trips.

- [ ] **Step 2: Run test to verify it fails**

Run: `... -m pytest tests/test_sigma_warmup.py -q`
Expected: FAIL — `run_sigma_warmup_pretraining` missing; payload has no `sigma_head_state_dict`.

- [ ] **Step 3: Add config fields**

In `config.py` sigma block:

```python
    sigma_warmup_epochs: int = 0
    sigma_warmup_lr: float = 3e-4
    sigma_warmup_patience: int = 20
    sigma_warmup_min_epochs: int = 5
    sigma_area_anchor_mae_tol: float = 30.0   # raw Å² mean abs area error gate
    sigma_area_anchor_strict: bool = False    # raise (vs warn) if gate fails
```

- [ ] **Step 4: Extend the checkpoint payload/apply**

In `pretrain_pipeline.py::build_pretrain_checkpoint_payload`, where it assembles the payload (after `readout_state_dict`):

```python
    if getattr(model, "head_sigma", None) is not None:
        payload["sigma_head_state_dict"] = model.head_sigma.state_dict()
```

In `apply_pretrained_encoder_checkpoint`, after loading gnn/readout:

```python
    if (getattr(model, "head_sigma", None) is not None
            and "sigma_head_state_dict" in checkpoint):
        model.head_sigma.load_state_dict(checkpoint["sigma_head_state_dict"])
```

Do NOT add `sigma_head_state_dict` to the strict required-key set in `load_pretrained_encoder_checkpoint` (keep old encoder-only checkpoints loadable).

- [ ] **Step 5: Implement `run_sigma_warmup_pretraining`**

Add to `pretrain_pipeline.py` (after `run_stage0_pretraining`):

```python
def run_sigma_warmup_pretraining(
    model, config, *, device, sigma_train_loader, sigma_val_loader=None, save_path=None
) -> dict:
    """Pretrain head_sigma (+ encoder) on the sigma pool with aux-VAL early-stop
    and an area-anchor gate, BEFORE the SLE curriculum. Returns metadata."""
    import logging
    import torch
    from .trainer import TGNNSolvTrainer

    log = logging.getLogger(__name__)
    if getattr(model, "head_sigma", None) is None:
        log.warning("sigma-warmup skipped: model has no head_sigma (non-cosmo).")
        return {"skipped": True}

    trainer = TGNNSolvTrainer(model, config, device=device)
    params = [p for p in model.head_sigma.parameters()] \
        + [p for p in model.gnn.parameters()] + [p for p in model.readout.parameters()]
    opt = torch.optim.AdamW(params, lr=float(config.sigma_warmup_lr),
                            weight_decay=float(config.weight_decay))

    best_val, best_state, patience, history = float("inf"), None, 0, []
    val_loader = sigma_val_loader or sigma_train_loader
    for epoch in range(int(config.sigma_warmup_epochs)):
        model.train()
        for batch in sigma_train_loader:
            opt.zero_grad()
            loss_sol, _ = trainer._sigma_forward_loss(batch, role="solute")
            if config.sigma_aux_symmetrize:
                loss_slv, _ = trainer._sigma_forward_loss(batch, role="solvent")
                loss = 0.5 * (loss_sol + loss_slv)
            else:
                loss = loss_sol
            if not torch.isfinite(loss):
                continue
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, config.grad_clip)
            opt.step()
        vmetrics = trainer.validate_sigma(val_loader)
        v = vmetrics["sigma_profile"]
        history.append(v)
        if v < best_val:
            best_val, best_state, patience = v, trainer._clone_model_state(), 0
        else:
            patience += 1
        if (epoch + 1 >= int(config.sigma_warmup_min_epochs)
                and patience >= int(config.sigma_warmup_patience)):
            break
    if best_state is not None:
        model.load_state_dict(best_state)

    area_mae = trainer.validate_sigma(val_loader)["sigma_area_mae"]
    passed = area_mae <= float(config.sigma_area_anchor_mae_tol)
    if not passed:
        msg = (f"sigma area-anchor gate FAILED: area MAE {area_mae:.1f} Å² > "
               f"tol {config.sigma_area_anchor_mae_tol} Å²")
        if config.sigma_area_anchor_strict:
            raise RuntimeError(msg)
        log.warning(msg)
    meta = {"history": history, "best_val": best_val, "area_mae": area_mae,
            "area_gate_passed": bool(passed), "epochs_run": len(history)}
    if save_path is not None:
        payload = build_pretrain_checkpoint_payload(
            model=model, config=config, pretrain_history={"sigma_warmup": history},
            pretrain_source="sigma_warmup", pretrain_epochs=len(history),
            pretrain_batch_size=0, pretrain_lr=float(config.sigma_warmup_lr),
            smiles_count=0)
        payload["sigma_warmup_meta"] = meta
        atomic_torch_save(payload, Path(save_path))
    return meta
```

> Read the real `_clone_model_state` (`trainer.py:913`) — confirm it returns a CPU state dict that `model.load_state_dict` accepts; if it clones only model weights (not optimizer), that's exactly right here. Confirm `build_pretrain_checkpoint_payload`'s required kwargs and adjust the call.

- [ ] **Step 6: Run tests + suite**

Run: `... -m pytest tests/test_sigma_warmup.py -q` → PASS.
Then `... -m pytest tests/ -q` → green.

- [ ] **Step 7: Commit**

```bash
git add src/tgnn_solv/config.py src/tgnn_solv/pretrain_pipeline.py tests/test_sigma_warmup.py
git commit -m "feat(sigma): sigma-warmup pretrain routine + area-anchor gate + ckpt (P1 D3)"
```

---

### Task 7: CLI wiring + end-to-end smoke

**Why:** Expose the new capability through `scripts/train.py`: build the σ-VAL loader, run sigma-warmup before `train_full`, and pass the σ-VAL loader through. Verify the whole path runs on a tiny smoke config.

**Files:**
- Modify: `scripts/train.py` (argparse ~253-274; loader build ~1108-1123; warmup call before `train_full` ~1295)
- Test: `tests/test_sigma_warmup.py` (extend with a CLI-path smoke, or a dedicated `tests/test_sigma_cli_smoke.py`)

**Interfaces:**
- Consumes: everything above.
- Produces: CLI flags `--sigma-val-data`, `--sigma-warmup-epochs`, `--freeze-sigma-head-during-sle`, `--sigma-aux-symmetrize/--no-sigma-aux-symmetrize` (or rely on `--set`); the script builds `sigma_val_loader` via `load_data(args.sigma_val_data, config, shuffle=False, seed=args.seed+31, ...)` and, when `cfg.sigma_warmup_epochs>0` and `sigma_train_loader is not None`, calls `run_sigma_warmup_pretraining(...)` after the model/trainer are built and before `trainer.train_full(...)`, passing `sigma_val_loader` into `train_full`.

- [ ] **Step 1: Write the failing smoke test**

Create `tests/test_sigma_cli_smoke.py` — call the wiring function path directly (avoid a full subprocess). Prefer a function-level smoke that mirrors what `main` does:

```python
import torch

from tests.sigma_fixtures import make_tiny_cosmo_trainer_and_loader
from tgnn_solv.pretrain_pipeline import run_sigma_warmup_pretraining


def test_warmup_then_one_sle_step_runs(tmp_path):
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    cfg = trainer.cfg
    cfg.sigma_warmup_epochs = 2
    cfg.sigma_warmup_min_epochs = 1
    cfg.freeze_sigma_head_during_sle = True
    # warmup grounds the head
    meta = run_sigma_warmup_pretraining(
        trainer.model, cfg, device=torch.device("cpu"),
        sigma_train_loader=loader, sigma_val_loader=loader,
        save_path=str(tmp_path / "warm.pt"))
    assert meta["epochs_run"] >= 1
    # freeze takes effect for SLE phases
    trainer._configure_phase_branch_training(2)
    assert all(not p.requires_grad for p in trainer.model.head_sigma.parameters())
    assert (tmp_path / "warm.pt").exists()
```

- [ ] **Step 2: Run test to verify it fails / passes**

Run: `... -m pytest tests/test_sigma_cli_smoke.py -q`
Expected: PASS once Tasks 1-6 are in (this is an integration smoke; if it fails, the failure pinpoints the broken seam). If it passes immediately, the integration holds — proceed to wire the actual CLI.

- [ ] **Step 3: Wire `scripts/train.py`**

Add argparse flags mirroring `--sigma-train-data` (~253-274):

```python
    p.add_argument("--sigma-val-data", default=None)
    p.add_argument("--sigma-warmup-epochs", type=int, default=None)
    p.add_argument("--freeze-sigma-head-during-sle", action="store_true")
```

After the existing `sigma_train_loader` build (~1108-1123), add:

```python
    sigma_val_loader = None
    if args.sigma_val_data:
        sigma_val_loader = load_data(args.sigma_val_data, config, shuffle=False,
                                     seed=args.seed + 31, batch_size=args.sigma_batch_size)
```

Apply CLI overrides to config (mirror how other args map to `config`): if `args.sigma_warmup_epochs is not None: config.sigma_warmup_epochs = args.sigma_warmup_epochs`; `if args.freeze_sigma_head_during_sle: config.freeze_sigma_head_during_sle = True`.

After the trainer is built and before `trainer.train_full(...)` (~1295), add:

```python
    if config.sigma_warmup_epochs > 0 and sigma_train_loader is not None:
        from tgnn_solv.pretrain_pipeline import run_sigma_warmup_pretraining
        print("Running sigma-warmup pretraining (head_sigma grounding)...")
        warm_meta = run_sigma_warmup_pretraining(
            model, config, device=device, sigma_train_loader=sigma_train_loader,
            sigma_val_loader=sigma_val_loader)
        print(f"sigma-warmup: {warm_meta}")
```

Pass `sigma_val_loader=sigma_val_loader` into the `trainer.train_full(...)` call.

- [ ] **Step 4: Run the smoke + suite**

Run: `... -m pytest tests/test_sigma_cli_smoke.py -q` → PASS.
Then `... -m pytest tests/ -q` → green, and `ruff check src tests scripts` → clean.

- [ ] **Step 5: Commit**

```bash
git add scripts/train.py tests/test_sigma_cli_smoke.py
git commit -m "feat(sigma): CLI wiring for sigma-warmup + sigma-val + freeze (P1)"
```

---

## Self-Review

**Spec coverage (P1 rows of the design spec §6/§7):**
- B1/D2 solvent grounding → Task 3 (symmetrized aux), built on the Task 2 helper. ✓
- D3 stage-0 pretrain + freeze → Task 6 (sigma-warmup, renamed to avoid the "Stage 0" clash) + Task 5 (freeze). ✓
- H1 weight schedule / head SLE-trained-but-ungrounded → Task 5 freezes the head in SLE and disables the in-curriculum stream when frozen. ✓
- H4 area-anchor gate → Task 6 (`sigma_area_mae` vs `sigma_area_anchor_mae_tol`, raw Å²). ✓
- σ-VAL split (P1 dependency, nominally P3) → Task 1. ✓
- L1 separate optimizer (deferred from P0) → addressed for warmup (its own `AdamW` in Task 6); the in-curriculum stream's separate optimizer is **intentionally dropped** because Task 5 freezes the head in phases 2/3 (so the in-curriculum σ-stream only runs in phase 1 where sharing the optimizer is harmless) — documented here rather than adding resume-serialization risk. ✓ (intentional)

**Placeholder scan:** No "TBD/handle edge cases" — every code step has code. The recurring "read the existing test / confirm the exact construction" notes are concrete verification actions (with file:line), required because the test fixtures must match this repo's dataset/loader/collate shapes, which the recon could not fully serialize — they are not vague placeholders.

**Type consistency:** `_sigma_forward_loss(batch, *, role) -> (Tensor, dict)` is defined in Task 2 and consumed identically in Tasks 3,4,6. `validate_sigma -> dict` keys (`sigma_profile/shape/area/sigma_area_mae`) match between Task 4 (producer) and Task 6 (consumer of `sigma_area_mae`). Config field names (`sigma_aux_symmetrize`, `sigma_val_data`, `freeze_sigma_head_during_sle`, `sigma_warmup_*`, `sigma_area_anchor_mae_tol/_strict`) are used consistently across tasks. `run_sigma_warmup_pretraining` signature matches between Task 6 (def) and Task 7 (call).

**Known adaptation points (read-before-edit, not placeholders):** the exact `TGNNSolvDataset`/`DataLoader`/`collate_fn` construction in `tests/sigma_fixtures.py` (Task 2) must mirror `tests/test_sigma_aux_stream.py`; `build_pretrain_checkpoint_payload`'s required kwargs (Task 6); `_clone_model_state`'s exact return (Task 6). Each is flagged inline.

**Scope note:** Task 6 is the largest (net-new routine). It is right-sized as one task because the routine, its config, its checkpoint extension, and its gate are one testable deliverable; splitting the checkpoint extension out would leave a half-wired warmup. If the implementer finds the routine too large mid-task, the natural sub-split is (6a) checkpoint payload/apply + config, (6b) the training loop + gate.
