# P2 — Combinatorial (Staverman–Guggenheim) Term Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate the dead Staverman–Guggenheim combinatorial (size/shape) term in the differentiable COSMO-SAC layer behind a flag, fed by a unit-corrected, grounded molar volume — so the decisive experiment can ablate residual-only vs residual+combinatorial.

**Architecture:** The SG term (`CosmoSacLayer._combinatorial_ln_gamma2`) is already implemented and correct, and the solver already threads `V_solute`/`V_solvent` to the layer; it is inert only because `model._build_sigma_activity_params` passes `V=None`. P2 computes per-molecule molar volume from the existing `AuxPropsHead` (cm³/mol), converts it to Å³/molecule, and wires it into the activity-param dict **detached** behind a new default-off flag.

**Tech Stack:** Python ≥3.10, PyTorch, RDKit, pytest. Package `tgnn_solv` under `src/`.

## Global Constraints

- **Env gotcha:** prefix ad-hoc python that imports torch+rdkit with `KMP_DUPLICATE_LIB_OK=TRUE` (suite sets it via `tests/conftest.py`).
- **Test interpreter / command:** `KMP_DUPLICATE_LIB_OK=TRUE /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest <path> -q`. Full suite is currently **321 passing** and must stay green.
- **Lint:** `ruff check <changed files>` must be clean (system `ruff`; not in the conda env). NOTE: the repo has ~140 pre-existing repo-wide ruff errors (E402 from the `sys.path` pattern) unrelated to this work — only keep the *changed* files clean.
- **Branch:** continue on `sigma-grounded-cosmosac` (P0+P1 already landed: `_sigma_forward_loss`, `validate_sigma`, `run_sigma_warmup_pretraining`, freeze, `cosmo_sac_gamma_iter_train=16`).
- **Defaults off:** the new flag defaults to the current behavior (residual-only, `V=None`). Existing training and the NRTL/non-cosmo path are unchanged; guard `head_sigma`/`head_aux` `is None` where relevant.
- **Verified facts (recon):**
  - `AuxPropsHead.forward(g) -> {"V_m", ...}`; `V_m` is molar volume in **cm³/mol** (heads.py:981-1057). `model.head_aux` (model.py:180) is always present.
  - `CosmoSacLayer._combinatorial_ln_gamma2(A2, A1, V2, V1, x2)` (layers.py:1545-1569): `r=V/r0`, `q=A/q0`, `z=coord_z`; x2-cancelled ratios → finite at infinite dilution.
  - `CosmoSacLayer.ln_gamma_2(...)` gates the term: `if self.use_combinatorial and V2 is not None and V1 is not None` (layers.py:1586). `cosmo_sac_use_combinatorial=True` already (config.py:183); `cosmo_sac_r0=66.69` (Å³), `cosmo_sac_q0=79.53` (Å²).
  - Solver already reads `nrtl_params.get("V_solute"/"V_solvent")` and threads them to `ln_gamma_2`/`ln_gamma_inf` (solver.py:464-473). The ONLY inert point is `model._build_sigma_activity_params` (model.py:509-533) returning `V_solute=None, V_solvent=None`.
  - Unit conversion: 1 cm³/mol = `1e24/N_A` Å³/molecule ≈ **1.660539** Å³/molecule (so `r = V_m·1.66054 / 66.69`; e.g. water V_m≈18 → ≈30 Å³ → r≈0.45).
- **Test fixture:** `tests/sigma_fixtures.py`; import as `from sigma_fixtures import make_tiny_cosmo_trainer_and_loader, tiny_cosmo_config, first_batch`. `TGNNSolvTrainer(model, cfg)` has **no** `device=` kwarg.

---

## File Structure

| File | Responsibility | Tasks |
|------|----------------|-------|
| `src/tgnn_solv/config.py` | new `cosmo_sac_wire_volume` flag | 1 |
| `src/tgnn_solv/model.py` | unit-conversion constant + wire detached V into `_build_sigma_activity_params` | 1 |
| `tests/test_cosmo_combinatorial.py` | wiring (flag on/off, units, detach) + SG correctness + ablation effect | 1, 2 |
| `docs/config_cookbook.md` (or `docs/experiments.md`) | document the residual-only vs +SG ablation arms | 2 |

**Dependency order:** Task 1 (wire V) → Task 2 (correctness + ablation verification + docs).

---

### Task 1: Wire unit-corrected, detached molar volume into the COSMO-SAC activity params

**Why:** Activate the combinatorial term by supplying `V_solute`/`V_solvent`. Use the existing `AuxPropsHead` molar volume (cm³/mol), convert to Å³/molecule, and pass it **detached** (the size factor is grounded by `head_aux`, not trainable by the solubility loss — same principle as the P1 σ-head freeze). Default-off preserves residual-only behavior.

**Files:**
- Modify: `src/tgnn_solv/config.py` (sigma/cosmo block, after `cosmo_sac_use_combinatorial`)
- Modify: `src/tgnn_solv/model.py` (module constant + `_build_sigma_activity_params`, lines 509-533)
- Test: `tests/test_cosmo_combinatorial.py` (new)

**Interfaces:**
- Produces: `cfg.cosmo_sac_wire_volume: bool = False`. Module constant `model._CM3_PER_MOL_TO_A3 = 1.0e24 / 6.02214076e23`. When the flag is true, `_build_sigma_activity_params` sets `V_solute`/`V_solvent` to detached tensors `head_aux(g)["V_m"].detach() * _CM3_PER_MOL_TO_A3` (Å³/molecule); when false, they stay `None`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cosmo_combinatorial.py`:

```python
import torch

from sigma_fixtures import make_tiny_cosmo_trainer_and_loader
import tgnn_solv.model as model_mod


def _readouts(trainer, loader):
    """Run the encoder on one batch to get solute/solvent readout vectors."""
    model = trainer.model
    sol_batch, slv_batch, targets = trainer._move_batch_to_device(next(iter(loader)))
    enc_t = model._encoder_temp_features(
        model_mod.make_temperature_features(targets["T"])
        if hasattr(model_mod, "make_temperature_features") else targets["T"]
    )
    _, gp_sol, _, _ = model._encode_and_readout(sol_batch, "solute", temp_feat=enc_t)
    _, gp_slv, _, _ = model._encode_and_readout(slv_batch, "solvent", temp_feat=enc_t)
    return gp_sol["value"], gp_slv["value"]


def test_conversion_constant_value():
    assert abs(model_mod._CM3_PER_MOL_TO_A3 - 1.660539) < 1e-3


def test_wire_volume_off_passes_none():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    trainer.cfg.cosmo_sac_wire_volume = False
    g_sol, g_slv = _readouts(trainer, loader)
    params = trainer.model._build_sigma_activity_params(g_sol, g_slv)
    assert params["V_solute"] is None and params["V_solvent"] is None


def test_wire_volume_on_passes_detached_angstrom3():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    trainer.cfg.cosmo_sac_wire_volume = True
    g_sol, g_slv = _readouts(trainer, loader)
    params = trainer.model._build_sigma_activity_params(g_sol, g_slv)
    V2, V1 = params["V_solute"], params["V_solvent"]
    assert V2 is not None and V1 is not None
    # detached: the size factor must not carry grad into the solubility loss
    assert not V2.requires_grad and not V1.requires_grad
    # Å³/molecule magnitude sanity (V_m head floored at 30 cm³/mol -> ~50 Å³ min)
    assert float(V2.min()) > 40.0 and float(V2.max()) < 2000.0
    # equals head_aux V_m * conversion constant
    vm = trainer.model.head_aux(g_sol)["V_m"].detach() * model_mod._CM3_PER_MOL_TO_A3
    assert torch.allclose(V2, vm, atol=1e-4)
```

> The `_readouts` helper mirrors how `_train_sigma_aux_batch` obtains readouts. If `make_temperature_features` lives in `tgnn_solv.trainer` rather than `model`, import it from there (read where `_train_sigma_aux_batch` imports it). Adjust the call to match the real `_encode_and_readout` usage in this repo.

- [ ] **Step 2: Run test to verify it fails**

Run: `KMP_DUPLICATE_LIB_OK=TRUE /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/test_cosmo_combinatorial.py -q`
Expected: FAIL — `model._CM3_PER_MOL_TO_A3` and `cosmo_sac_wire_volume` do not exist; V is always None.

- [ ] **Step 3: Add the config flag**

In `src/tgnn_solv/config.py`, after `cosmo_sac_use_combinatorial: bool = True` (line 183):

```python
    cosmo_sac_wire_volume: bool = False  # feed (detached) molar volume so the SG combinatorial term is active
```

- [ ] **Step 4: Add the constant + wire V in the model**

In `src/tgnn_solv/model.py`, add a module-level constant near the top (after imports):

```python
# Molar volume unit conversion: 1 cm^3/mol = (1e24 / N_A) A^3 per molecule.
_CM3_PER_MOL_TO_A3 = 1.0e24 / 6.02214076e23  # ~= 1.660539
```

Replace the `V_solute`/`V_solvent` entries in `_build_sigma_activity_params` (model.py:528-529) so they are wired when the flag is set. The method body becomes:

```python
        sol = self.head_sigma(g_solute)
        slv = self.head_sigma(g_solvent)
        if getattr(self.cfg, "cosmo_sac_wire_volume", False):
            # Grounded size factor: use the aux-head molar volume (cm^3/mol),
            # converted to A^3/molecule, DETACHED so the combinatorial term cannot
            # be trained by the solubility loss (it is grounded by head_aux, mirroring
            # the P1 sigma-head freeze rationale).
            v_solute = self.head_aux(g_solute)["V_m"].detach() * _CM3_PER_MOL_TO_A3
            v_solvent = self.head_aux(g_solvent)["V_m"].detach() * _CM3_PER_MOL_TO_A3
        else:
            v_solute = None
            v_solvent = None
        return {
            "p_solute": sol["p_sigma"],
            "A_solute": sol["area"],
            "p_solvent": slv["p_sigma"],
            "A_solvent": slv["area"],
            "V_solute": v_solute,
            "V_solvent": v_solvent,
            "alpha_12": torch.full_like(sol["area"], 0.3),
            "sigma_shape_solute": sol["p_shape"],
            "sigma_shape_solvent": slv["p_shape"],
        }
```

Update the method docstring's "Volume is passed as None ... to avoid the ... unit ambiguity" sentence to note the conversion is now resolved and gated by `cosmo_sac_wire_volume`.

- [ ] **Step 5: Run tests + suite**

Run: `KMP_DUPLICATE_LIB_OK=TRUE ... -m pytest tests/test_cosmo_combinatorial.py -q` → PASS (4).
Then `... -m pytest tests/ -q` → green (default flag off keeps the cosmo path byte-identical; existing cosmo tests unaffected).

- [ ] **Step 6: Commit**

```bash
git add src/tgnn_solv/config.py src/tgnn_solv/model.py tests/test_cosmo_combinatorial.py
git commit -m "feat(cosmo): wire detached molar volume for SG combinatorial term behind flag (P2)"
```

---

### Task 2: Combinatorial correctness + ablation effect + docs

**Why:** Lock the SG math with a property test, prove the flag actually changes `ln γ₂` for a size-asymmetric pair (so the ablation is real), and document the two arms (residual-only vs +SG) so the P3 experiment harness can run them.

**Files:**
- Modify: `tests/test_cosmo_combinatorial.py` (add SG-correctness + ablation tests)
- Modify: `docs/config_cookbook.md` (document the ablation arms; if that file does not exist, add the note to `docs/experiments.md`)

**Interfaces:**
- Consumes: `CosmoSacLayer._combinatorial_ln_gamma2`, `CosmoSacLayer.ln_gamma_2` (layers.py); `cfg.cosmo_sac_wire_volume` (Task 1).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cosmo_combinatorial.py`:

```python
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer


def _layer():
    return CosmoSacLayer(TGNNSolvConfig())


def test_combinatorial_zero_for_identical_components():
    layer = _layer()
    A = torch.tensor([100.0]); V = torch.tensor([120.0]); x2 = torch.tensor([0.3])
    # solute == solvent (same r, q) -> no size/shape mismatch -> SG term ~ 0
    lng_c = layer._combinatorial_ln_gamma2(A, A, V, V, x2)
    assert torch.allclose(lng_c, torch.zeros_like(lng_c), atol=1e-5)


def test_combinatorial_finite_and_nonzero_for_asymmetric_pair():
    layer = _layer()
    A2 = torch.tensor([60.0]); A1 = torch.tensor([300.0])
    V2 = torch.tensor([50.0]); V1 = torch.tensor([400.0])
    x2 = torch.tensor([1e-4])  # near infinite dilution
    lng_c = layer._combinatorial_ln_gamma2(A2, A1, V2, V1, x2)
    assert torch.isfinite(lng_c).all()
    assert float(lng_c.abs().max()) > 1e-3  # a genuine size effect


def test_ln_gamma2_changes_when_volume_wired():
    layer = _layer()  # use_combinatorial defaults True
    n = layer.cosmo_sac_n_bins if hasattr(layer, "cosmo_sac_n_bins") else 51
    g = layer.sigma_grid
    p2 = torch.softmax(-((g - 0.005) ** 2) / 2e-5, dim=0).unsqueeze(0) * 60.0
    p1 = torch.softmax(-(g ** 2) / 2e-5, dim=0).unsqueeze(0) * 300.0
    A2 = p2.sum(-1); A1 = p1.sum(-1)
    V2 = torch.tensor([50.0]); V1 = torch.tensor([400.0])
    x2 = torch.tensor([1e-3]); x1 = 1.0 - x2; T = torch.tensor([298.15])
    res_only = layer.ln_gamma_2(x1, x2, p2, p1, A2, A1, None, None, T)
    with_sg = layer.ln_gamma_2(x1, x2, p2, p1, A2, A1, V2, V1, T)
    assert not torch.allclose(res_only, with_sg)  # SG term contributes
```

> Confirm `_combinatorial_ln_gamma2` is the real method name/signature (layers.py:1545) and `ln_gamma_2(x1, x2, p2, p1, A2, A1, V2, V1, T)` is the real call order (layers.py:1571-1582). If the tiny-grid construction trips the `n_bins` attribute access, drop the unused `n` line — `layer.sigma_grid` already has the right length.

- [ ] **Step 2: Run tests to verify they fail/pass appropriately**

Run: `... -m pytest tests/test_cosmo_combinatorial.py -q`
Expected: the three new tests exercise EXISTING layer code (the SG math already exists), so they may PASS immediately — that is acceptable; they are regression locks. If `test_ln_gamma2_changes_when_volume_wired` FAILS, it means the SG term is not actually contributing — investigate (the layer's `use_combinatorial` must be True and V non-None).

- [ ] **Step 3: Document the ablation arms**

Add to `docs/config_cookbook.md` (create a short section; if the file is absent, append to `docs/experiments.md`) — plain prose, no code placeholders:

```markdown
## COSMO-SAC combinatorial (size) ablation

The differentiable COSMO-SAC activity model can run with or without the
Staverman–Guggenheim combinatorial (size/shape) term:

- **Arm A — residual-only (default):** `cosmo_sac_wire_volume: false`. Activity is
  the restoring/residual term only; molar volume is not used.
- **Arm B — residual + combinatorial:** `cosmo_sac_wire_volume: true` (with
  `cosmo_sac_use_combinatorial: true`, the default). The size term is fed by the
  `AuxPropsHead` molar volume (cm³/mol), converted to Å³/molecule
  (×1e24/N_A ≈ 1.66054) and passed **detached**, so the size factor is grounded
  by the volume head, not fit by the solubility loss.

Caveat: `AuxPropsHead` predicts a real molar volume, not a COSMO cavity volume,
so the `r = V/r0` normalization (r0 = 66.69 Å³) is approximate; arm B tests
whether a grounded size correction helps, not an exact COSMO cavity model.
Run both arms in the experiment harness (P3) to ablate the size term.
```

- [ ] **Step 4: Run tests + suite**

Run: `... -m pytest tests/test_cosmo_combinatorial.py -q` → PASS (7 total).
Then `... -m pytest tests/ -q` → green; `ruff check tests/test_cosmo_combinatorial.py src/tgnn_solv/model.py src/tgnn_solv/config.py` → clean.

- [ ] **Step 5: Commit**

```bash
git add tests/test_cosmo_combinatorial.py docs/config_cookbook.md
git commit -m "test+docs(cosmo): SG combinatorial correctness + ablation arms (P2)"
```

---

## Self-Review

**Spec coverage (spec §6 D6 / §7 P2):**
- "Resolve the V_m unit conversion (cm³/mol → Å³/molecule)" → Task 1 (`_CM3_PER_MOL_TO_A3`, tested). ✓
- "Wire SG through behind a flag (arm B)" → Task 1 (`cosmo_sac_wire_volume`, default off = arm A). ✓
- "Run residual-only vs +SG as an ablation" → Task 2 documents the two arms; the actual paired runs are P3 (experiment harness, GPU). ✓ (the run itself is P3, correctly out of scope here)
- "document residual-only as a stated limitation if not wired" → Task 2 docs note the real-vs-cavity-volume caveat. ✓

**Placeholder scan:** No "TBD/handle edge cases" — every code step has code. The "confirm the real method name / make_temperature_features location / sigma_grid length" notes are concrete read-before-edit verifications (with file:line), not vague placeholders.

**Type consistency:** `cosmo_sac_wire_volume` (config) and `_CM3_PER_MOL_TO_A3` (model) names are used identically in Task 1 impl and both tasks' tests. `_combinatorial_ln_gamma2(A2,A1,V2,V1,x2)` and `ln_gamma_2(x1,x2,p2,p1,A2,A1,V2,V1,T)` signatures in Task 2 tests match the verified layer signatures (layers.py:1545, 1571).

**Design decision (recorded):** V_m is wired **detached** — consistent with the P1 σ-head freeze rationale (single-component factors are grounded, not fit by solubility). A non-detached variant would let ln x2 train the volume head; if the harness later wants that, it's a one-line change (drop `.detach()`), but the default and recommended arm is detached.

**Scope:** Two tasks, code-only, locally testable (no GPU). The experiment that consumes both arms (paired runs, metrics) is P3.
