# P3 — Experiment Harness (decisive lever-C test) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the harness that runs the decisive lever-C comparison — NRTL, DirectGNN-h64, ungrounded/grounded-A/grounded-B COSMO-SAC, and an oracle-profile ceiling — on one corrected split with metrics locked to a shared converged row-set and machine-checked pre-registered criteria.

**Architecture:** Code + config only; the full GPU runs are the execution step (local = smoke). Five deliverables: (1) pinned configs; (2) a σ-profile oracle-injection eval path; (3) an export that also emits per-row ln γ₂; (4) a `run_e5_comparison.py` aggregator that intersection-locks `n_supervised` across arms, computes the pre-registered criteria + std(ln γ) band + ring/acyclic stratification; (5) a `run_e5` bash orchestrator (σ-VAL prep + 6 arms × ≥3 seeds + export + aggregate).

**Tech Stack:** Python ≥3.10, PyTorch, RDKit, pandas, numpy, pytest, bash. Package `tgnn_solv` under `src/`.

## Global Constraints

- **Env:** prefix python that imports torch+rdkit with `KMP_DUPLICATE_LIB_OK=TRUE` (suite sets it via `tests/conftest.py`). Test interpreter: `/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python`. Test cmd: `KMP_DUPLICATE_LIB_OK=TRUE <py> -m pytest <path> -q`. Suite currently **327 passing**, must stay green. Lint: `ruff check <changed files>` clean (system ruff; repo has ~140 pre-existing errors — only keep changed files clean).
- **Branch:** continue on `sigma-grounded-cosmosac` (P0+P1+P2 landed).
- **Compute reality (spec §8/§9):** real COSMO-SAC metrics require GPU; local CPU/MPS gives meaningless numbers (MAE 3+, R²~0). Every full-run command in this plan is the EXECUTION step — run it on GPU. Local pytest covers code paths only (unit + tiny smoke). Do NOT report smoke numbers as results.
- **Data paths (verified):** corrected split = `notebooks/data/processed/{train,val,test}.csv`. σ aux stream = `notebooks/data/processed_sigma_aux_stream/sigma_train.csv` (1319 rows). σ-VAL (`sigma_val.csv`) does NOT exist yet — build it first (Task 5 prereq). IGNORE `split_manifest.json` (points at a non-existent `processed_fixed/`).
- **Pre-registered criteria (spec §5, lock before runs):** *rescue* = grounded cosmo_sac R² ≥ matched DirectGNN-h64 R² (NRTL R²≈0.32 = weaker milestone only); *keeps-constraint* = std(ln γ) within a fixed band; area-anchor gate passed; **`n_supervised` locked to the cross-arm intersection** and reported first-class; rescue stratified by aux regime (ring-bearing ~421 vs acyclic). Ungrounded reference: `results/cosmo_sac/test_predictions.summary.json` (n_supervised 5608/8103, R² −0.310).
- **Matched references (verified):** TGNN h64L3 reference R²=0.3202 (`results/proxy_corrected_cpu/test_predictions.summary.json`). The orphaned DirectGNN R²=0.48 was h128 on the OLD split — DISCARD it.
- **VT-2005 artifact:** `results/sigma_profile_artifact/sigma_profiles.csv` (cols `smiles, sigma_area, sigma_p_0..50`) — already on the model grid (51 bins, [-0.025,0.025]); `sigma_p_*` == `p_sigma` (area-weighted), `sigma_area` == `area`. NO transform at injection.
- **Canonical bundle:** `external_benchmarking.build_benchmark_artifacts` + `write_benchmark_artifacts` → `report.json/predictions.csv/summary.csv/run_manifest.json/benchmark_card.json`.

---

## File Structure

| File | Responsibility | Tasks |
|------|----------------|-------|
| `configs/cosmo_sac.yaml` | pinned grounded COSMO-SAC recipe (h64/3L, warmup+freeze, n_iter 16/30) | 1 |
| `configs/paper_config_directgnn_h64L3.yaml` | DirectGNN matched-capacity baseline | 1 |
| `src/tgnn_solv/model.py` | σ-profile oracle injection seam (`force_sigma_oracle`) | 2 |
| `src/tgnn_solv/sigma_oracle.py` | SMILES→(p_sigma, area) loader + per-batch oracle-tensor builder | 2 |
| `scripts/analysis/export_checkpoint_predictions.py` | per-row `ln_gamma2_pred` column + `--sigma-oracle` flag + masked-subset summary | 3 |
| `scripts/analysis/run_e5_comparison.py` | intersection-lock aggregator + criteria + std(lnγ) band + stratification | 4 |
| `scripts/experiments/run_e5_sigma_grounding.sh` | σ-VAL prep + 6-arm × seed orchestration → bundles → aggregate | 5 |
| `tests/test_sigma_oracle.py` | oracle loader + injection unit tests | 2 |
| `tests/test_export_lngamma.py` | export emits ln_gamma2_pred + oracle masked subset | 3 |
| `tests/test_e5_comparison.py` | aggregator intersection lock + criteria on synthetic CSVs | 4 |

**Dependency order:** Task 1 (configs) → Task 2 (oracle seam) → Task 3 (export emits γ + oracle CLI) → Task 4 (aggregator) → Task 5 (orchestrator, ties it together). Tasks 1–4 are code-only and locally testable; Task 5 ends with a CPU smoke.

---

### Task 1: Pinned configs (grounded COSMO-SAC + matched DirectGNN-h64)

**Why:** The decisive comparison must be reproducible and matched-capacity. Pin one grounded COSMO-SAC recipe and one DirectGNN-h64 baseline (the orphaned h128 config is discarded).

**Files:**
- Create: `configs/cosmo_sac.yaml`, `configs/paper_config_directgnn_h64L3.yaml`
- Test: `tests/test_e5_configs.py` (new)

**Interfaces:**
- Produces: two YAMLs loadable via `TGNNSolvConfig.from_yaml`. `cosmo_sac.yaml` → `activity_model="cosmo_sac"`, `hidden_dim=64`, `n_gnn_layers=3`, `cosmo_sac_gamma_iter_train=16`, `cosmo_sac_gamma_iter_eval=30`, `cosmo_sac_wire_volume=False`, `sigma_aux_symmetrize=True`, `freeze_sigma_head_during_sle=True`, `sigma_warmup_epochs>0`, `sigma_aux_steps_per_epoch>0`. DirectGNN config → `hidden_dim=64`, `n_gnn_layers=3`, `epochs_phase2=110`, `use_morgan_features=False`, `use_descriptor_augmentation=False`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_e5_configs.py`:

```python
from tgnn_solv.config import TGNNSolvConfig


def test_cosmo_sac_config_pins_grounded_recipe():
    c = TGNNSolvConfig.from_yaml("configs/cosmo_sac.yaml")
    assert c.activity_model == "cosmo_sac"
    assert c.hidden_dim == 64 and c.n_gnn_layers == 3
    assert c.cosmo_sac_gamma_iter_train == 16 and c.cosmo_sac_gamma_iter_eval == 30
    assert c.cosmo_sac_wire_volume is False          # arm A residual-only by default
    assert c.sigma_aux_symmetrize is True
    assert c.freeze_sigma_head_during_sle is True
    assert c.sigma_warmup_epochs > 0
    assert c.sigma_aux_steps_per_epoch > 0


def test_directgnn_h64_config_matches_capacity():
    c = TGNNSolvConfig.from_yaml("configs/paper_config_directgnn_h64L3.yaml")
    assert c.hidden_dim == 64 and c.n_gnn_layers == 3
    assert c.epochs_phase2 == 110          # = TGNN total budget 30+70+10
    assert c.use_morgan_features is False
    assert c.use_descriptor_augmentation is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `KMP_DUPLICATE_LIB_OK=TRUE /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/test_e5_configs.py -q`
Expected: FAIL — both YAMLs missing (`from_yaml` raises FileNotFoundError).

- [ ] **Step 3: Create `configs/cosmo_sac.yaml`**

Read `configs/paper_config_tuned.yaml` first to copy its `model:`/`training:`/`data:` structure and key names exactly (from_yaml flattens nested sections). Then write `configs/cosmo_sac.yaml` with the same structure but these values (place each key under the section `paper_config_tuned.yaml` uses for it — `activity_model`/`hidden_dim`/`n_gnn_layers`/`cosmo_sac_*`/`sigma_*` under `model:` if that's where the tuned config groups model fields; otherwise top-level — match the tuned file):

```yaml
# Pinned grounded COSMO-SAC recipe for the decisive lever-C run (P3).
# Matched capacity h64/3L; sigma-warmup + freeze; converged solver (n_iter 16/30).
model:
  activity_model: cosmo_sac
  hidden_dim: 64
  n_gnn_layers: 3
  cosmo_sac_gamma_iter_train: 16
  cosmo_sac_gamma_iter_eval: 30
  cosmo_sac_wire_volume: false        # arm A (residual-only); arm B flips via --set
  cosmo_sac_use_combinatorial: true
  sigma_aux_symmetrize: true
  freeze_sigma_head_during_sle: true
  sigma_warmup_epochs: 40
  sigma_warmup_min_epochs: 5
  sigma_aux_steps_per_epoch: 21       # >= one full pass over the ~1319-row pool at batch 64
  sigma_area_anchor_mae_tol: 30.0
training:
  # copy lr_phase*/epochs_phase*/patience/weight_decay from paper_config_tuned.yaml verbatim
data:
  # copy the data: block (split_mode solute_scaffold, fractions, seed) from paper_config_tuned.yaml verbatim
```

> Critical: `from_yaml` silently ignores unknown keys, so a misspelled field is dropped without error — verify via the test that each value lands. Copy the `training:`/`data:` blocks verbatim from `paper_config_tuned.yaml` so only the model/cosmo/sigma fields differ. If the tuned config puts these fields at top level (not under `model:`), match that — the test reading them back is the source of truth.

- [ ] **Step 4: Create `configs/paper_config_directgnn_h64L3.yaml`**

Read `configs/paper_config_directgnn_tuned.yaml` (the orphaned h128). Clone it, changing only `hidden_dim: 128` → `hidden_dim: 64`, ADD `n_gnn_layers: 3`, set `epochs_phase2: 110`, and ensure `use_morgan_features: false` + `use_descriptor_augmentation: false`. Keep `interaction_mode`/`n_cross_attn_layers`/`use_solvent_moe` as in the tuned file (to mirror the h64L3 backbone).

- [ ] **Step 5: Run tests + suite**

Run: `... -m pytest tests/test_e5_configs.py -q` → PASS (2).
Then `... -m pytest tests/ -q` → green (config-only addition; nothing else touched).

- [ ] **Step 6: Commit**

```bash
git add configs/cosmo_sac.yaml configs/paper_config_directgnn_h64L3.yaml tests/test_e5_configs.py
git commit -m "feat(e5): pinned cosmo_sac + matched DirectGNN-h64 configs (P3)"
```

---

### Task 2: σ-profile oracle injection seam

**Why:** Measure the *ceiling* of lever C — feed the TRUE VT-2005 σ-profile into COSMO-SAC for test solutes (and optionally solvents) that have an entry, instead of `head_sigma`'s prediction. The seam is `_build_sigma_activity_params`; the solver and layer downstream need no change.

**Files:**
- Create: `src/tgnn_solv/sigma_oracle.py` (loader + per-batch tensor builder)
- Modify: `src/tgnn_solv/model.py` (`forward` kwarg + `_build_sigma_activity_params` override + call site)
- Test: `tests/test_sigma_oracle.py` (new)

**Interfaces:**
- Produces:
  - `sigma_oracle.load_sigma_profiles(csv_path, n_bins=51) -> dict[str, tuple[np.ndarray, float]]` — maps canonical SMILES → (p_sigma[51], area). Uses `tgnn_solv.data.utils.canonicalize`.
  - `sigma_oracle.build_oracle_tensors(smiles_list, table, n_bins=51) -> tuple[Tensor (B,51), Tensor (B,), Tensor (B,) bool]` — per-row p_sigma, area, matched-mask (zeros + False for unmatched).
  - `TGNNSolv.forward(..., force_sigma_oracle: bool = False)`; `_build_sigma_activity_params(self, g_solute, g_solvent, *, targets=None, force_sigma_oracle=False)`. When `force_sigma_oracle and not self.training and targets is not None`, override `p_solute`/`A_solute` (and `p_solvent`/`A_solvent` if `targets` carry the solvent-side keys) via `torch.where` on the per-row mask. Keys read from `targets`: `sigma_oracle_p_solute`,`sigma_oracle_area_solute`,`sigma_oracle_mask_solute` (and `_solvent` variants).

- [ ] **Step 1: Write the failing test**

Create `tests/test_sigma_oracle.py`:

```python
import numpy as np
import torch

from sigma_fixtures import make_tiny_cosmo_trainer_and_loader
from tgnn_solv.sigma_oracle import load_sigma_profiles, build_oracle_tensors


def test_load_and_build_oracle_tensors(tmp_path):
    import pandas as pd
    n = 51
    row = {"smiles": "CCO", "sigma_area": 88.0}
    shape = np.full(n, 88.0 / n)
    for i in range(n):
        row[f"sigma_p_{i}"] = float(shape[i])
    csv = tmp_path / "sig.csv"
    pd.DataFrame([row]).to_csv(csv, index=False)
    table = load_sigma_profiles(str(csv), n_bins=n)
    assert len(table) == 1
    p, A, mask = build_oracle_tensors(["CCO", "c1ccccc1"], table, n_bins=n)
    assert p.shape == (2, n) and A.shape == (2,) and mask.dtype == torch.bool
    assert bool(mask[0]) is True and bool(mask[1]) is False   # CCO matched, benzene not
    assert abs(float(A[0]) - 88.0) < 1e-4
    assert torch.all(p[1] == 0) and float(A[1]) == 0.0          # unmatched -> zeros (masked out)


def test_forward_uses_oracle_profile_for_matched_rows():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    model = trainer.model
    model.eval()
    sol_b, slv_b, targets = trainer._move_batch_to_device(next(iter(loader)))
    B = len(targets["solute_smiles"])
    n = model.cfg.cosmo_sac_n_bins
    # craft a distinctive oracle profile for ALL rows, mask all True
    oracle_p = torch.zeros(B, n); oracle_p[:, 0] = 100.0  # mass entirely in bin 0
    oracle_A = torch.full((B,), 100.0)
    mask = torch.ones(B, dtype=torch.bool)
    targets["sigma_oracle_p_solute"] = oracle_p
    targets["sigma_oracle_area_solute"] = oracle_A
    targets["sigma_oracle_mask_solute"] = mask
    # encode to get readouts, then build params with oracle on vs off
    enc_t = model._encoder_temp_features(
        __import__("tgnn_solv.layers", fromlist=["make_temperature_features"]).make_temperature_features(targets["T"]))
    _, gp_s, _, _ = model._encode_and_readout(sol_b, "solute", temp_feat=enc_t)
    _, gp_v, _, _ = model._encode_and_readout(slv_b, "solvent", temp_feat=enc_t)
    p_off = model._build_sigma_activity_params(gp_s["value"], gp_v["value"])["p_solute"]
    p_on = model._build_sigma_activity_params(
        gp_s["value"], gp_v["value"], targets=targets, force_sigma_oracle=True)["p_solute"]
    assert not torch.allclose(p_off, p_on)            # oracle changed the profile
    assert torch.allclose(p_on, oracle_p.to(p_on))    # matched rows use the oracle exactly
```

- [ ] **Step 2: Run test to verify it fails**

Run: `... -m pytest tests/test_sigma_oracle.py -q`
Expected: FAIL — `tgnn_solv.sigma_oracle` missing; `_build_sigma_activity_params` has no `targets`/`force_sigma_oracle`.

- [ ] **Step 3: Implement `src/tgnn_solv/sigma_oracle.py`**

```python
"""VT-2005 sigma-profile oracle: SMILES -> (p_sigma, area) for eval-time injection."""
from __future__ import annotations

import numpy as np
import pandas as pd
import torch

from .data.utils import canonicalize


def load_sigma_profiles(csv_path: str, n_bins: int = 51) -> dict[str, tuple[np.ndarray, float]]:
    """Map canonical SMILES -> (p_sigma[n_bins] area-weighted, area). Skips unparseable."""
    df = pd.read_csv(csv_path)
    cols = [f"sigma_p_{i}" for i in range(n_bins)]
    table: dict[str, tuple[np.ndarray, float]] = {}
    for rec in df.itertuples(index=False):
        d = rec._asdict()
        key = canonicalize(str(d.get("smiles", "")))
        if key is None:
            continue
        p = np.array([float(d[c]) for c in cols], dtype=float)
        area = float(d.get("sigma_area", p.sum()))
        table[key] = (p, area)
    return table


def build_oracle_tensors(
    smiles_list, table: dict[str, tuple[np.ndarray, float]], n_bins: int = 51
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Per-row (p_sigma (B,n_bins), area (B,), mask (B,) bool). Unmatched -> zeros + False."""
    B = len(smiles_list)
    p = torch.zeros(B, n_bins)
    A = torch.zeros(B)
    mask = torch.zeros(B, dtype=torch.bool)
    for i, smi in enumerate(smiles_list):
        key = canonicalize(str(smi))
        hit = table.get(key) if key is not None else None
        if hit is not None:
            p[i] = torch.tensor(hit[0], dtype=torch.float)
            A[i] = float(hit[1])
            mask[i] = True
    return p, A, mask
```

- [ ] **Step 4: Add the override seam in `model.py`**

Add `force_sigma_oracle: bool = False` to `forward(...)` (beside `force_oracle_injection`, model.py:925), and change the cosmo call site (model.py:1208) to:

```python
        if self.is_cosmo_sac:
            nrtl_params = self._build_sigma_activity_params(
                g_sol_pre, g_slv_pre, targets=targets, force_sigma_oracle=force_sigma_oracle)
```

Change `_build_sigma_activity_params` signature to `(self, g_solute, g_solvent, *, targets=None, force_sigma_oracle=False)` and, right after `sol = self.head_sigma(g_solute)` / `slv = self.head_sigma(g_solvent)`, insert:

```python
        p_sol, a_sol = sol["p_sigma"], sol["area"]
        p_slv, a_slv = slv["p_sigma"], slv["area"]
        if force_sigma_oracle and not self.training and targets is not None:
            op = targets.get("sigma_oracle_p_solute")
            oa = targets.get("sigma_oracle_area_solute")
            om = targets.get("sigma_oracle_mask_solute")
            if isinstance(op, torch.Tensor) and isinstance(om, torch.Tensor):
                m = om.to(p_sol.device).bool()
                p_sol = torch.where(m.unsqueeze(-1), op.to(p_sol), p_sol)
                a_sol = torch.where(m, oa.to(a_sol), a_sol)
            sp = targets.get("sigma_oracle_p_solvent")
            sa = targets.get("sigma_oracle_area_solvent")
            sm = targets.get("sigma_oracle_mask_solvent")
            if isinstance(sp, torch.Tensor) and isinstance(sm, torch.Tensor):
                m = sm.to(p_slv.device).bool()
                p_slv = torch.where(m.unsqueeze(-1), sp.to(p_slv), p_slv)
                a_slv = torch.where(m, sa.to(a_slv), a_slv)
```

Then use `p_sol/a_sol/p_slv/a_slv` for the returned `p_solute`/`A_solute`/`p_solvent`/`A_solvent` (and keep `sigma_shape_solute=sol["p_shape"]` etc. unchanged; the V-wiring from P2 stays). The second caller `trainer.py:1149` uses keyword defaults so it is unaffected.

- [ ] **Step 5: Run tests + suite**

Run: `... -m pytest tests/test_sigma_oracle.py -q` → PASS (2).
Then `... -m pytest tests/ -q` → green (default `force_sigma_oracle=False` keeps the path identical).

- [ ] **Step 6: Commit**

```bash
git add src/tgnn_solv/sigma_oracle.py src/tgnn_solv/model.py tests/test_sigma_oracle.py
git commit -m "feat(e5): sigma-profile oracle injection seam for the lever-C ceiling (P3)"
```

---

### Task 3: Export per-row ln γ₂ + `--sigma-oracle` flag

**Why:** The aggregator (Task 4) needs per-row `ln_gamma2_pred` (for the std-band) and an oracle-vs-learned comparison on the covered subset. Extend the existing export script (which already runs the forward and mirrors a crystal `--oracle` precedent).

**Files:**
- Modify: `scripts/analysis/export_checkpoint_predictions.py` (add `ln_gamma2_pred` column; add `--sigma-oracle` / `--sigma-oracle-side` / `--sigma-artifact`; per-row `sigma_oracle_applied`; masked-subset summary)
- Test: `tests/test_export_lngamma.py` (new)

**Interfaces:**
- Consumes: `sigma_oracle.load_sigma_profiles`/`build_oracle_tensors` (Task 2); `force_sigma_oracle` forward kwarg (Task 2).
- Produces: predictions CSV gains `ln_gamma2_pred` (float, from `output["physics"]["ln_gamma_2"]`, NaN for non-cosmo) and `sigma_oracle_applied` (bool). CLI `--sigma-oracle` (+ `--sigma-oracle-side {solute,solvent,both}` default solute, `--sigma-artifact` default `results/sigma_profile_artifact/sigma_profiles.csv`) injects oracle tensors per batch and sets `__force_sigma_oracle__`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_lngamma.py`. Because the export script is a CLI over a checkpoint, test the two new UNIT-LEVEL pieces it relies on rather than a full CLI run: (a) the forward exposes `ln_gamma_2`; (b) the per-batch oracle wiring marks the matched rows. Use the fixture model.

```python
import torch
from sigma_fixtures import make_tiny_cosmo_trainer_and_loader
from tgnn_solv.sigma_oracle import build_oracle_tensors


def test_forward_exposes_ln_gamma_2():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    model = trainer.model; model.eval()
    sol_b, slv_b, targets = trainer._move_batch_to_device(next(iter(loader)))
    with torch.no_grad():
        out = model(sol_b, slv_b, targets["T"], targets=targets)
    assert "physics" in out and "ln_gamma_2" in out["physics"]
    assert out["physics"]["ln_gamma_2"].shape[0] == len(targets["solute_smiles"])


def test_oracle_tensors_match_only_known_smiles():
    table = {"CCO": ( [0.0] * 51, 88.0)}
    # build_oracle_tensors canonicalizes; CCO is already canonical
    import numpy as np
    table = {"CCO": (np.zeros(51), 88.0)}
    p, A, mask = build_oracle_tensors(["CCO", "CCCCCC"], table, n_bins=51)
    assert bool(mask[0]) and not bool(mask[1])
```

- [ ] **Step 2: Run test to verify it fails/passes**

Run: `... -m pytest tests/test_export_lngamma.py -q`
Expected: `test_oracle_tensors_match_only_known_smiles` may PASS (Task 2 code); `test_forward_exposes_ln_gamma_2` should PASS once the cosmo forward output carries `physics.ln_gamma_2` (it does per recon model.py:1267). If both pass, they are regression locks for the export's data source — proceed to wire the script.

- [ ] **Step 3: Add the `ln_gamma2_pred` column to the export**

In `scripts/analysis/export_checkpoint_predictions.py`, where it builds per-row dicts (the `row = {...}` block, ~line 191), after running the forward extract gamma once per batch and add it. The forward output for cosmo carries `output["physics"]["ln_gamma_2"]`; for `--model-type direct` there is no physics → write `float("nan")`. Concretely, in `forward_batch` / the row loop, compute:

```python
        gamma = None
        if isinstance(output, dict) and "physics" in output:
            g = output["physics"].get("ln_gamma_2")
            if g is not None:
                gamma = g.detach().cpu().numpy()
        ...
        row["ln_gamma2_pred"] = float(gamma[i]) if gamma is not None else float("nan")
```

(Match the script's actual output-dict access — read how it currently gets `pred`/`true` and mirror it.)

- [ ] **Step 4: Add the `--sigma-oracle` flag + injection + masked summary**

Add argparse (mirror the existing `--oracle` at ~line 134): `--sigma-oracle` (store_true), `--sigma-oracle-side` (choices solute/solvent/both, default solute), `--sigma-artifact` (default `results/sigma_profile_artifact/sigma_profiles.csv`). Before the batch loop, when `args.sigma_oracle`: `table = load_sigma_profiles(args.sigma_artifact, n_bins=cfg.cosmo_sac_n_bins)`. Inside the loop, build oracle tensors from `targets["solute_smiles"]` (and `targets["solvent_smiles"]` when side in {solvent,both}) via `build_oracle_tensors`, write them into `targets` under the `sigma_oracle_*_solute`/`_solvent` keys, and set `targets["__force_sigma_oracle__"] = True`; pass `force_sigma_oracle=targets.get("__force_sigma_oracle__", False)` into the `model(...)` call. Add per-row `row["sigma_oracle_applied"] = bool(mask_solute[i])` (or solvent/both). In the summary block, add a masked-subset metrics dict (mae/rmse/bias over rows where `sigma_oracle_applied`) and `n_oracle = int(mask.sum())`.

- [ ] **Step 5: Run tests + suite + a CPU smoke**

Run: `... -m pytest tests/test_export_lngamma.py -q` → PASS.
Then `... -m pytest tests/ -q` → green.
Smoke (optional, needs a cosmo checkpoint): `... export_checkpoint_predictions.py --checkpoint <any cosmo ckpt> --data notebooks/data/processed/test.csv --output /tmp/p.csv --model-type tgnn --device cpu --sigma-oracle` → confirms the column + flag wire without error (metrics meaningless on CPU).

- [ ] **Step 6: Commit**

```bash
git add scripts/analysis/export_checkpoint_predictions.py tests/test_export_lngamma.py
git commit -m "feat(e5): export per-row ln_gamma2_pred + --sigma-oracle injection (P3)"
```

---

### Task 4: `run_e5_comparison.py` — intersection-locked aggregator + pre-registered criteria

**Why:** This is the analytical heart. Each arm's `predictions.csv` is computed on its own supervised rows; a fair verdict requires locking all arms to the SAME converged row-set, then machine-checking the pre-registered criteria. No existing code does cross-arm intersection or encodes the criteria.

**Files:**
- Create: `scripts/analysis/run_e5_comparison.py`
- Test: `tests/test_e5_comparison.py` (new)

**Interfaces:**
- Produces: CLI `--run LABEL=predictions.csv` (repeatable), `--direct-label` (the DirectGNN arm label, default `directgnn`), `--lngamma-band LO HI` (keeps-constraint band), `--out-json PATH`. Pure helpers (unit-tested): `intersection_mask(frames: dict[str, DataFrame]) -> pd.Index` (rows supervised AND finite `ln_x2_pred` in EVERY arm, keyed on `(solute_smiles, solvent_smiles, T)`); `r2(true, pred) -> float`; `is_ring_bearing(smiles) -> bool`; `evaluate_criteria(per_arm_metrics, direct_label, lngamma_band) -> dict` returning `{rescue: {arm: bool}, keeps_constraint: {arm: bool}, n_locked: int}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_e5_comparison.py`:

```python
import numpy as np
import pandas as pd
import importlib

m = importlib.import_module("scripts.analysis.run_e5_comparison")


def _frame(pairs, true, pred, lng, has=True):
    return pd.DataFrame({
        "solute_smiles": [p[0] for p in pairs],
        "solvent_smiles": [p[1] for p in pairs],
        "T": [p[2] for p in pairs],
        "ln_x2_true": true, "ln_x2_pred": pred,
        "ln_gamma2_pred": lng,
        "has_solubility": [has] * len(pairs),
    })


def test_intersection_mask_keeps_common_supervised_finite_rows():
    pairs = [("A", "W", 298.0), ("B", "W", 298.0), ("C", "W", 298.0)]
    a = _frame(pairs, [0, 1, 2], [0.1, 1.1, 2.1], [0.5, 0.5, 0.5])
    b = _frame(pairs, [0, 1, 2], [0.2, np.nan, 2.2], [0.4, 0.4, 0.4])  # row B non-finite in arm b
    keys = m.intersection_keys({"a": a, "b": b})
    assert set(keys) == {("A", "W", 298.0), ("C", "W", 298.0)}  # B dropped


def test_ring_bearing_detection():
    assert m.is_ring_bearing("c1ccccc1") is True
    assert m.is_ring_bearing("CCCCCC") is False


def test_rescue_and_constraint_criteria():
    # grounded R2 0.35 >= directgnn 0.30 -> rescue True; std(lng) in band -> keeps True
    per_arm = {
        "directgnn": {"r2": 0.30, "lngamma_std": float("nan")},
        "grounded_a": {"r2": 0.35, "lngamma_std": 1.5},
        "ungrounded": {"r2": -0.31, "lngamma_std": 1.4},
    }
    crit = m.evaluate_criteria(per_arm, direct_label="directgnn", lngamma_band=(1.0, 2.0))
    assert crit["rescue"]["grounded_a"] is True
    assert crit["rescue"]["ungrounded"] is False
    assert crit["keeps_constraint"]["grounded_a"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `... -m pytest tests/test_e5_comparison.py -q`
Expected: FAIL — module/functions missing.

- [ ] **Step 3: Implement `scripts/analysis/run_e5_comparison.py`**

```python
"""Aggregate run_e5 arms: lock metrics to the cross-arm n_supervised intersection,
compute pre-registered criteria (rescue, keeps-constraint), and stratify by aux regime."""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from rdkit import Chem

_KEY = ["solute_smiles", "solvent_smiles", "T"]


def _supervised_finite(df: pd.DataFrame) -> pd.DataFrame:
    sup = df["has_solubility"].fillna(False).astype(bool)
    fin = np.isfinite(df["ln_x2_pred"].to_numpy(dtype=float))
    return df[sup & fin]


def intersection_keys(frames: dict[str, pd.DataFrame]):
    """Keys (solute,solvent,T) supervised AND finite-pred in EVERY arm."""
    common = None
    for df in frames.values():
        keys = set(map(tuple, _supervised_finite(df)[_KEY].itertuples(index=False, name=None)))
        common = keys if common is None else (common & keys)
    return sorted(common or set())


def r2(true: np.ndarray, pred: np.ndarray) -> float:
    true = np.asarray(true, float); pred = np.asarray(pred, float)
    ss_res = float(np.sum((true - pred) ** 2))
    ss_tot = float(np.sum((true - true.mean()) ** 2))
    return float(1.0 - ss_res / (ss_tot + 1e-12))


def is_ring_bearing(smiles: str) -> bool:
    mol = Chem.MolFromSmiles(str(smiles))
    return bool(mol is not None and mol.GetRingInfo().NumRings() > 0)


def _metrics_on_keys(df: pd.DataFrame, keys) -> dict:
    idx = df.set_index(_KEY)
    sub = idx.loc[[k for k in keys if k in idx.index]]
    true = sub["ln_x2_true"].to_numpy(float); pred = sub["ln_x2_pred"].to_numpy(float)
    lng = sub["ln_gamma2_pred"].to_numpy(float) if "ln_gamma2_pred" in sub else np.array([np.nan])
    lng = lng[np.isfinite(lng)]
    return {
        "r2": r2(true, pred),
        "mae": float(np.mean(np.abs(true - pred))),
        "lngamma_std": float(np.std(lng, ddof=1)) if lng.size > 1 else float("nan"),
        "n": int(len(true)),
    }


def evaluate_criteria(per_arm: dict, *, direct_label: str, lngamma_band) -> dict:
    lo, hi = lngamma_band
    direct_r2 = per_arm.get(direct_label, {}).get("r2", float("nan"))
    rescue, keeps = {}, {}
    for label, mtr in per_arm.items():
        rescue[label] = bool(np.isfinite(direct_r2) and mtr["r2"] >= direct_r2)
        std = mtr.get("lngamma_std", float("nan"))
        keeps[label] = bool(np.isfinite(std) and lo <= std <= hi)
    return {"rescue": rescue, "keeps_constraint": keeps,
            "matched_direct_r2": direct_r2}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="append", required=True, help="LABEL=predictions.csv")
    ap.add_argument("--direct-label", default="directgnn")
    ap.add_argument("--lngamma-band", nargs=2, type=float, default=[1.0, 2.0])
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    frames = {}
    for spec in args.run:
        label, path = spec.split("=", 1)
        frames[label] = pd.read_csv(path)
    keys = intersection_keys(frames)
    per_arm = {label: _metrics_on_keys(df, keys) for label, df in frames.items()}
    # ring/acyclic stratification of the locked key set
    ring_keys = [k for k in keys if is_ring_bearing(k[0])]
    acyc_keys = [k for k in keys if not is_ring_bearing(k[0])]
    strat = {
        label: {
            "ring_bearing": _metrics_on_keys(df, ring_keys),
            "acyclic": _metrics_on_keys(df, acyc_keys),
        } for label, df in frames.items()
    }
    criteria = evaluate_criteria(per_arm, direct_label=args.direct_label,
                                 lngamma_band=tuple(args.lngamma_band))
    out = {"n_locked": len(keys), "n_ring_bearing": len(ring_keys),
           "n_acyclic": len(acyc_keys), "per_arm": per_arm,
           "stratified": strat, "criteria": criteria,
           "lngamma_band": list(args.lngamma_band)}
    with open(args.out_json, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(criteria, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests + suite**

Run: `... -m pytest tests/test_e5_comparison.py -q` → PASS (3).
Then `... -m pytest tests/ -q` → green.

- [ ] **Step 5: Commit**

```bash
git add scripts/analysis/run_e5_comparison.py tests/test_e5_comparison.py
git commit -m "feat(e5): intersection-locked comparison aggregator + pre-registered criteria (P3)"
```

---

### Task 5: `run_e5` orchestrator + σ-VAL prerequisite + smoke

**Why:** Tie it together: build the σ-VAL split (front-load prerequisite), then for each seed run the 6 arms (subprocess `train.py` / `train_directgnn.py`), export each arm's predictions (with γ; oracle for the oracle arm), and call the aggregator. Mirrors `run_e4_ablations.sh` (label loop) + `run_corrected_split_reproduction.sh` (header/guard) + a seed loop.

**Files:**
- Create: `scripts/experiments/run_e5_sigma_grounding.sh`
- Test: a CPU smoke invocation (documented; bash isn't unit-tested) + `tests/test_e5_smoke.py` (a tiny function-level smoke of the aggregator on two real exported CSVs is already covered by Task 4; here add a shell `bash -n` syntax check)

**Interfaces:**
- Consumes: configs (Task 1), oracle export (Task 3), aggregator (Task 4), the σ-VAL builder (`build_sigma_profile_aux_stream.py --val-fraction`, P1).
- Produces: `scripts/experiments/run_e5_sigma_grounding.sh` with env-overridable `DEVICE/DATA_DIR/OUT_DIR/CKPT_DIR/SEEDS/SIGMA_STEPS/WARMUP_EPOCHS/EXTRA_TRAIN_ARGS`, a T_m-corruption guard, a σ-VAL prep step, a per-seed × per-arm loop, and a final `run_e5_comparison.py` call per seed + across seeds.

- [ ] **Step 1: Write the bash syntax-check test**

Create `tests/test_e5_smoke.py`:

```python
import subprocess


def test_run_e5_script_parses():
    # bash -n: syntax check without executing (no GPU/training needed)
    r = subprocess.run(["bash", "-n", "scripts/experiments/run_e5_sigma_grounding.sh"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `... -m pytest tests/test_e5_smoke.py -q`
Expected: FAIL — the script does not exist.

- [ ] **Step 3: Write the orchestrator**

Create `scripts/experiments/run_e5_sigma_grounding.sh` (clone the header/guard idiom from `run_corrected_split_reproduction.sh` and the label-loop from `run_e4_ablations.sh`). Read both first to match their exact conventions, then:

```bash
#!/usr/bin/env bash
# P3 run_e5: decisive lever-C comparison — NRTL / DirectGNN-h64 / cosmo {ungrounded,
# grounded-A residual-only, grounded-B +SG} / oracle — on the corrected split, >=3 seeds,
# metrics intersection-locked by run_e5_comparison.py. REAL metrics need GPU; CPU = smoke.
set -euo pipefail
cd "$(dirname "$0")/../.."
export KMP_DUPLICATE_LIB_OK=TRUE
PY="${PY:-$HOME/anaconda3/envs/tgnn-solv/bin/python}"
DEVICE="${DEVICE:-cuda}"
DATA_DIR="${DATA_DIR:-notebooks/data/processed}"
SIGMA_DIR="${SIGMA_DIR:-notebooks/data/processed_sigma_aux_stream}"
OUT_DIR="${OUT_DIR:-results/e5_sigma_grounding}"
CKPT_DIR="${CKPT_DIR:-checkpoints/e5}"
SEEDS="${SEEDS:-42 43 44}"
SIGMA_STEPS="${SIGMA_STEPS:-21}"
WARMUP_EPOCHS="${WARMUP_EPOCHS:-40}"
EXTRA_TRAIN_ARGS="${EXTRA_TRAIN_ARGS:-}"   # e.g. --epochs-phase2 1 for a CPU smoke
TRAIN="${DATA_DIR}/train.csv"; VAL="${DATA_DIR}/val.csv"; TEST="${DATA_DIR}/test.csv"
mkdir -p "${OUT_DIR}" "${CKPT_DIR}"

# T_m-corruption guard (mirror run_corrected_split_reproduction.sh)
"${PY}" - "$TEST" <<'PYG'
import sys, pandas as pd
df = pd.read_csv(sys.argv[1])
if "T_m" in df.columns:
    med = float(df["T_m"].dropna().median())
    assert med < 560, f"T_m median {med} looks +273 K corrupted"
print("T_m guard ok")
PYG

# Prereq: build the scaffold-disjoint sigma-VAL split if missing
if [ ! -f "${SIGMA_DIR}/sigma_val.csv" ]; then
  "${PY}" scripts/data/build_sigma_profile_aux_stream.py \
    --output-csv "${SIGMA_DIR}/sigma_train.csv" --output-val-csv "${SIGMA_DIR}/sigma_val.csv" \
    --val-fraction 0.1 --split-seed 0 \
    --exclude-scaffolds-from "${TEST}" "${VAL}"
fi

# arm -> (train command builder). Cosmo arms share configs/cosmo_sac.yaml.
COSMO_GROUND=(--sigma-train-data "${SIGMA_DIR}/sigma_train.csv" --sigma-val-data "${SIGMA_DIR}/sigma_val.csv" \
              --sigma-steps-per-epoch "${SIGMA_STEPS}" --sigma-warmup-epochs "${WARMUP_EPOCHS}" --freeze-sigma-head-during-sle)

for SEED in ${SEEDS}; do
  SOUT="${OUT_DIR}/seed_${SEED}"; mkdir -p "${SOUT}"
  declare -a RUN_ARGS=()
  for arm in nrtl directgnn ungrounded grounded_a grounded_b oracle; do
    ckpt="${CKPT_DIR}/${arm}_seed${SEED}.pt"; pred="${SOUT}/${arm}_predictions.csv"
    case "${arm}" in
      nrtl)
        "${PY}" scripts/train.py --config configs/paper_config_tuned.yaml \
          --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
          --seed "${SEED}" --device "${DEVICE}" --checkpoint "${ckpt}" ${EXTRA_TRAIN_ARGS}
        "${PY}" scripts/analysis/export_checkpoint_predictions.py --checkpoint "${ckpt}" \
          --data "${TEST}" --output "${pred}" --model-type tgnn --device "${DEVICE}" ;;
      directgnn)
        "${PY}" scripts/train_directgnn.py --config configs/paper_config_directgnn_h64L3.yaml \
          --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
          --seed "${SEED}" --device "${DEVICE}" --checkpoint "${ckpt}"
        "${PY}" scripts/analysis/export_checkpoint_predictions.py --checkpoint "${ckpt}" \
          --data "${TEST}" --output "${pred}" --model-type direct --device "${DEVICE}" ;;
      ungrounded)
        "${PY}" scripts/train.py --config configs/cosmo_sac.yaml \
          --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
          --seed "${SEED}" --device "${DEVICE}" --checkpoint "${ckpt}" \
          --sigma-steps-per-epoch 0 --sigma-warmup-epochs 0 ${EXTRA_TRAIN_ARGS}
        "${PY}" scripts/analysis/export_checkpoint_predictions.py --checkpoint "${ckpt}" \
          --data "${TEST}" --output "${pred}" --model-type tgnn --device "${DEVICE}" ;;
      grounded_a)
        "${PY}" scripts/train.py --config configs/cosmo_sac.yaml \
          --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
          --seed "${SEED}" --device "${DEVICE}" --checkpoint "${ckpt}" \
          "${COSMO_GROUND[@]}" ${EXTRA_TRAIN_ARGS}
        "${PY}" scripts/analysis/export_checkpoint_predictions.py --checkpoint "${ckpt}" \
          --data "${TEST}" --output "${pred}" --model-type tgnn --device "${DEVICE}" ;;
      grounded_b)
        "${PY}" scripts/train.py --config configs/cosmo_sac.yaml \
          --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
          --seed "${SEED}" --device "${DEVICE}" --checkpoint "${ckpt}" \
          "${COSMO_GROUND[@]}" ${EXTRA_TRAIN_ARGS} --set cosmo_sac_wire_volume=true
        "${PY}" scripts/analysis/export_checkpoint_predictions.py --checkpoint "${ckpt}" \
          --data "${TEST}" --output "${pred}" --model-type tgnn --device "${DEVICE}" ;;
      oracle)
        # reuse the grounded_a checkpoint; only the eval path changes (oracle injection)
        "${PY}" scripts/analysis/export_checkpoint_predictions.py \
          --checkpoint "${CKPT_DIR}/grounded_a_seed${SEED}.pt" \
          --data "${TEST}" --output "${pred}" --model-type tgnn --device "${DEVICE}" \
          --sigma-oracle --sigma-oracle-side both ;;
    esac
    RUN_ARGS+=("--run" "${arm}=${pred}")
  done
  "${PY}" scripts/analysis/run_e5_comparison.py "${RUN_ARGS[@]}" \
    --direct-label directgnn --out-json "${SOUT}/comparison.json"
done
echo "run_e5 complete -> ${OUT_DIR} (per-seed comparison.json; aggregate across seeds for the verdict)"
```

> Note: the oracle arm reuses the `grounded_a` checkpoint and only changes the eval path (`--sigma-oracle`), so it measures the ceiling for the grounded model. `--set cosmo_sac_wire_volume=true` is LAST on the grounded_b line (argparse `nargs='*'` is greedy). For a CPU smoke set `DEVICE=cpu SEEDS=42 EXTRA_TRAIN_ARGS="--epochs-phase1 1 --epochs-phase2 1 --epochs-phase3 1" WARMUP_EPOCHS=1 SIGMA_STEPS=2`.

- [ ] **Step 4: Run the syntax test + suite**

Run: `... -m pytest tests/test_e5_smoke.py -q` → PASS (bash -n clean).
Then `... -m pytest tests/ -q` → green.

- [ ] **Step 5: Document the execution step**

Append to `docs/experiments.md` a "run_e5 — decisive lever-C comparison" section: the GPU command (`DEVICE=cuda bash scripts/experiments/run_e5_sigma_grounding.sh`), the 6 arms, the pre-registered criteria, where outputs land (`results/e5_sigma_grounding/seed_*/comparison.json`), and the caveats (oracle coverage ~5% of rows; real metrics need GPU; calibrate `--lngamma-band` from the ungrounded run before declaring keeps-constraint).

- [ ] **Step 6: Commit**

```bash
git add scripts/experiments/run_e5_sigma_grounding.sh tests/test_e5_smoke.py docs/experiments.md
git commit -m "feat(e5): run_e5 orchestrator (6 arms x seeds) + sigma-VAL prep + smoke (P3)"
```

---

## Self-Review

**Spec coverage (spec §5 matrix + §6/§7 P3):**
- σ-VAL split (P1 dep, finalized as run_e5 prereq) → Task 5 prereq step. ✓
- Oracle-profile control → Tasks 2+3 (seam + CLI). ✓
- DirectGNN h64 retrain on corrected split → Task 1 config + Task 5 arm. ✓
- run_e5 orchestrator (6 arms, ≥3 seeds, only-one-knob deltas) → Task 5. ✓
- Pinned cosmo_sac.yaml + seed → Task 1 + `--seed` in Task 5. ✓
- n_supervised intersection lock → Task 4 `intersection_keys`. ✓
- Pre-registered criteria (rescue ≥ matched DirectGNN; keeps-constraint band) → Task 4 `evaluate_criteria`. ✓
- Rescue stratified by ring/acyclic → Task 4 `stratified`. ✓
- Re-run ungrounded with n_iter=16 → the ungrounded arm uses `configs/cosmo_sac.yaml` (n_iter 16); the old R²−0.31 reference (n=8) is superseded. ✓
- std(ln γ) needs per-row γ → Task 3 adds `ln_gamma2_pred`. ✓

**Placeholder scan:** No "TBD/handle edge cases" — every code step has code. The "read X first / match the real access" notes are concrete read-before-edit verifications (the export script's row-dict access and the tuned config's section layout must be matched to the real files), not vague placeholders.

**Type consistency:** `load_sigma_profiles`/`build_oracle_tensors` (Task 2) signatures match their use in Task 3. `force_sigma_oracle` kwarg + `targets` keys (`sigma_oracle_{p,area,mask}_{solute,solvent}`) are consistent between Task 2 model code and Task 3 export. `intersection_keys`/`evaluate_criteria`/`is_ring_bearing`/`r2` names match between Task 4 impl and test. The aggregator consumes `ln_gamma2_pred`/`has_solubility`/`ln_x2_pred`/`ln_x2_true`/`solute_smiles`/`solvent_smiles`/`T` — all emitted by the Task 3 export.

**Compute boundary (explicit):** Tasks 1–4 are fully local-testable (unit). Task 5's deliverable is the orchestrator + a `bash -n` syntax test; its real output requires GPU and is the execution step (documented), NOT a TDD assertion. No smoke metric is treated as a result.

**Known adaptation points (read-before-edit):** the `paper_config_tuned.yaml` section layout (Task 1); the export script's exact output-dict access for `pred`/`true` (Task 3); the exact `forward` return-dict key path `output["physics"]["ln_gamma_2"]` (Task 3, verified at model.py:1267 in recon). Each is flagged inline.

**Scope note:** This plan stops at "harness ready + smoke-green." The decisive GPU runs + interpreting `comparison.json` against the pre-registered criteria are the execution/analysis step the user runs when GPU is available.
