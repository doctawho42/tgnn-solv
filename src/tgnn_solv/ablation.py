"""
Ablation study for TGNN-Solv.

Systematically removes or modifies one component at a time
to measure its contribution.  Each ablation is a (name, config_fn,
train_fn) triple that trains a full model and evaluates on test.

Ablations:
  full              — complete TGNN-Solv (reference)
  no_cross_attn     — remove cross-attention layers
  no_nrtl           — remove NRTL, predict ln(x₂) from Φ + MLP
  no_curriculum     — train all losses from epoch 0 (no phases)
  no_aux_losses     — only solubility loss, no T_m/ΔH/Hansen/γ∞
  no_correction     — remove gated residual correction
  no_implicit_diff  — use explicit successive substitution only
  small_model       — hidden_dim=128 (scaling)
  large_model       — hidden_dim=512 (scaling)

Usage::

    from tgnn_solv.ablation import run_ablation_study
    results = run_ablation_study(train_loader, val_loader, test_loader)
"""

import copy
import time
from dataclasses import replace
from typing import Callable, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import pandas as pd
from torch.utils.data import DataLoader

from .config import TGNNSolvConfig
from .model import TGNNSolv
from .trainer import TGNNSolvTrainer
from .evaluate import Evaluator


# ================================================================== #
#  Ablated model variants                                             #
# ================================================================== #

class TGNNSolvNoCrossAttn(TGNNSolv):
    """TGNN-Solv without cross-attention: solute and solvent
    are encoded independently."""

    def forward(self, solute_data, solvent_data, T):
        # Encode without cross-attention
        h_sol_atoms, g_sol_pre = self._encode_and_readout(
            solute_data, "solute"
        )
        h_slv_atoms, g_slv_pre = self._encode_and_readout(
            solvent_data, "solvent"
        )

        # Skip cross-attention entirely — use pre-cross readout
        g_sol_post = g_sol_pre
        g_slv_post = g_slv_pre

        # Auxiliary heads
        hansen_sol = self.head_hansen(g_sol_pre)
        hansen_slv = self.head_hansen(g_slv_pre)
        aux_sol = self.head_aux(g_sol_pre)
        aux_slv = self.head_aux(g_slv_pre)

        # Pair representation
        g_pair = self.pair_repr(g_sol_post, g_slv_post)

        # Prediction heads
        fusion_params = self.head_fusion(g_sol_pre)
        nrtl_params = self.head_nrtl(g_pair)

        # SLE solver
        with torch.cuda.amp.autocast(enabled=False):
            T_f32 = T.float()
            fus_f32 = {k: v.float() for k, v in fusion_params.items()}
            nrtl_f32 = {k: v.float() for k, v in nrtl_params.items()}
            physics_out = self.sle_solver(T_f32, fus_f32, nrtl_f32)

        Ra = self.sle_solver.hansen_layer(hansen_sol, hansen_slv)

        param_summary = torch.stack([
            (fusion_params["T_m"] - 400.0) / 200.0,
            (fusion_params["dH_fus"] - 20000.0) / 10000.0,
            nrtl_params["dg_12"] / self.cfg.S_g,
            nrtl_params["dg_21"] / self.cfg.S_g,
            (nrtl_params["alpha_12"] - 0.3) / 0.15,
            (T - 300.0) / 50.0,
        ], dim=-1)

        correction, gate = self.correction(g_pair, param_summary)
        ln_x2 = physics_out["ln_x2"] + correction

        return {
            "ln_x2": ln_x2,
            "x2": torch.exp(ln_x2).clamp(0, 1),
            "physics": physics_out,
            "fusion_params": fusion_params,
            "nrtl_params": nrtl_params,
            "hansen_sol": hansen_sol,
            "hansen_slv": hansen_slv,
            "aux_sol": aux_sol,
            "aux_slv": aux_slv,
            "Ra": Ra,
            "correction": correction,
            "gate": gate,
            "attn_maps": [],
        }


class TGNNSolvNoNRTL(TGNNSolv):
    """TGNN-Solv without NRTL: uses ideal solubility + learned
    correction only.  γ₂ is always 1."""

    def forward(self, solute_data, solvent_data, T):
        # Standard encoding with cross-attention
        out = super().forward(solute_data, solvent_data, T)

        # Override: use ideal solubility only (γ₂ = 1)
        Phi = out["physics"]["Phi"]
        ln_x2_ideal = -Phi

        # Correction still applied on top of ideal
        ln_x2 = ln_x2_ideal + out["correction"]

        out["ln_x2"] = ln_x2
        out["x2"] = torch.exp(ln_x2).clamp(0, 1)

        # Zero out NRTL outputs for consistency
        B = T.shape[0]
        out["physics"]["ln_gamma_2"] = torch.zeros(B, device=T.device)
        out["physics"]["ln_gamma_inf"] = torch.zeros(B, device=T.device)

        return out


class TGNNSolvNoCorrection(TGNNSolv):
    """TGNN-Solv without gated residual correction.
    ln(x₂) = physics only."""

    def forward(self, solute_data, solvent_data, T):
        out = super().forward(solute_data, solvent_data, T)

        # Remove correction
        out["ln_x2"] = out["physics"]["ln_x2"]
        out["x2"] = torch.exp(out["ln_x2"]).clamp(0, 1)
        out["correction"] = torch.zeros_like(out["correction"])
        out["gate"] = torch.tensor(0.0, device=T.device)

        return out


# ================================================================== #
#  Ablation trainer variants                                          #
# ================================================================== #

class NoCurriculumTrainer(TGNNSolvTrainer):
    """Train all losses from epoch 0 — no phase separation."""

    def train_full(self, train_loader, val_loader):
        # Single phase with all weights active from start
        self.phase_weights[1] = {
            "sol": 1.0, "T_m": 0.3, "dH": 0.3, "hansen": 0.2,
            "gamma_inf": 0.5, "mono": 0.1,
            "res": 0.05, "bridge": 0.05, "tau_reg": 0.001,
        }
        total_epochs = (
            self.cfg.epochs_phase1
            + self.cfg.epochs_phase2
            + self.cfg.epochs_phase3
        )
        # Unfreeze correction from start
        self._freeze_correction(False)
        self.train_phase(1, train_loader, val_loader, total_epochs)

        if self.best_state is not None:
            self.model.load_state_dict(self.best_state)
            print(f"\nRestored best model (val MAE = {self.best_val_loss:.4f})")


class NoAuxLossTrainer(TGNNSolvTrainer):
    """Train with solubility loss only — no auxiliary targets."""

    def __init__(self, model, cfg):
        super().__init__(model, cfg)
        # Override all phases: only solubility + minimal regularization
        no_aux = {
            "sol": 1.0, "T_m": 0.0, "dH": 0.0, "hansen": 0.0,
            "gamma_inf": 0.0, "mono": 0.0,
            "res": 0.05, "bridge": 0.0, "tau_reg": 0.001,
        }
        self.phase_weights = {1: no_aux, 2: no_aux, 3: no_aux}

    def train_full(self, train_loader, val_loader):
        # Skip phase 1 entirely (no aux targets to pretrain on)
        self._freeze_correction(True)
        total_epochs = (
            self.cfg.epochs_phase1
            + self.cfg.epochs_phase2
            + self.cfg.epochs_phase3
        )
        self.train_phase(2, train_loader, val_loader, total_epochs)

        if self.best_state is not None:
            self.model.load_state_dict(self.best_state)


# ================================================================== #
#  Ablation definitions                                               #
# ================================================================== #

def _define_ablations(
    base_cfg: TGNNSolvConfig,
) -> List[Tuple[str, TGNNSolvConfig, type, type]]:
    """
    Define all ablation experiments.

    Returns list of (name, config, model_class, trainer_class).
    """
    ablations = []

    # 1. Full model (reference)
    ablations.append((
        "full",
        base_cfg,
        TGNNSolv,
        TGNNSolvTrainer,
    ))

    # 2. No cross-attention
    ablations.append((
        "no_cross_attn",
        base_cfg,
        TGNNSolvNoCrossAttn,
        TGNNSolvTrainer,
    ))

    # 3. No NRTL (ideal + correction only)
    ablations.append((
        "no_nrtl",
        base_cfg,
        TGNNSolvNoNRTL,
        TGNNSolvTrainer,
    ))

    # 4. No curriculum (all losses from start)
    ablations.append((
        "no_curriculum",
        base_cfg,
        TGNNSolv,
        NoCurriculumTrainer,
    ))

    # 5. No auxiliary losses
    ablations.append((
        "no_aux_losses",
        base_cfg,
        TGNNSolv,
        NoAuxLossTrainer,
    ))

    # 6. No correction
    ablations.append((
        "no_correction",
        base_cfg,
        TGNNSolvNoCorrection,
        TGNNSolvTrainer,
    ))

    # 7. No implicit differentiation
    cfg_no_impl = replace(base_cfg, use_implicit_diff=False)
    ablations.append((
        "no_implicit_diff",
        cfg_no_impl,
        TGNNSolv,
        TGNNSolvTrainer,
    ))

    # 8. Small model (scaling)
    cfg_small = replace(
        base_cfg,
        hidden_dim=128,
        pair_dim=256,
        n_gnn_layers=4,
        n_cross_attn_layers=2,
    )
    ablations.append((
        "small_128",
        cfg_small,
        TGNNSolv,
        TGNNSolvTrainer,
    ))

    # 9. Large model (scaling)
    cfg_large = replace(
        base_cfg,
        hidden_dim=512,
        pair_dim=1024,
        n_gnn_layers=8,
        n_cross_attn_layers=4,
    )
    ablations.append((
        "large_512",
        cfg_large,
        TGNNSolv,
        TGNNSolvTrainer,
    ))

    return ablations


# ================================================================== #
#  Runner                                                             #
# ================================================================== #

def run_single_ablation(
    name: str,
    cfg: TGNNSolvConfig,
    model_class: type,
    trainer_class: type,
    train_loader: DataLoader,
    val_loader: DataLoader,
    test_loader: DataLoader,
    device: torch.device,
    test_df: Optional[pd.DataFrame] = None,
    seed: int = 42,
) -> Dict:
    """
    Run one ablation experiment: build, train, evaluate.

    Returns dict with name, metrics, timing, param count.
    """
    print(f"\n{'=' * 60}")
    print(f"  ABLATION: {name}")
    print(f"{'=' * 60}")

    torch.manual_seed(seed)

    t0 = time.time()

    # Build model
    model = model_class(cfg=cfg).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {n_params:,}")

    # Train
    trainer = trainer_class(model, cfg)
    trainer.train_full(train_loader, val_loader)

    train_time = time.time() - t0
    print(f"  Training time: {train_time:.0f}s")

    # Evaluate
    evaluator = Evaluator(model, cfg)
    report = evaluator.evaluate(test_loader, test_df)
    metrics = report["overall"]

    print(f"\n  Results:")
    print(f"    MAE  = {metrics['mae']:.3f}")
    print(f"    RMSE = {metrics['rmse']:.3f}")
    print(f"    R²   = {metrics['r2']:.4f}")

    return {
        "name": name,
        "n_params": n_params,
        "train_time_s": train_time,
        **metrics,
    }


def run_ablation_study(
    train_loader: DataLoader,
    val_loader: DataLoader,
    test_loader: DataLoader,
    device: torch.device,
    base_cfg: Optional[TGNNSolvConfig] = None,
    test_df: Optional[pd.DataFrame] = None,
    seeds: List[int] = None,
    skip: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Run full ablation study.

    Parameters
    ----------
    train_loader, val_loader, test_loader : DataLoaders
    device : torch device
    base_cfg : reference config (default: TGNNSolvConfig())
    test_df : test DataFrame for stratified metrics
    seeds : list of random seeds (default [42])
    skip : list of ablation names to skip

    Returns
    -------
    DataFrame with one row per (ablation, seed), sorted by MAE.
    """
    if base_cfg is None:
        base_cfg = TGNNSolvConfig()
    if seeds is None:
        seeds = [42]
    if skip is None:
        skip = []

    ablations = _define_ablations(base_cfg)

    all_results = []

    for name, cfg, model_cls, trainer_cls in ablations:
        if name in skip:
            print(f"\n  Skipping: {name}")
            continue

        for seed in seeds:
            seed_label = f" (seed={seed})" if len(seeds) > 1 else ""
            result = run_single_ablation(
                name=f"{name}{seed_label}" if len(seeds) > 1 else name,
                cfg=cfg,
                model_class=model_cls,
                trainer_class=trainer_cls,
                train_loader=train_loader,
                val_loader=val_loader,
                test_loader=test_loader,
                device=device,
                test_df=test_df,
                seed=seed,
            )
            result["seed"] = seed
            result["ablation"] = name
            all_results.append(result)

    results_df = pd.DataFrame(all_results)

    # Summary
    print("\n" + "=" * 70)
    print("  ABLATION STUDY — SUMMARY")
    print("=" * 70)

    if len(seeds) > 1:
        # Aggregate over seeds
        summary = results_df.groupby("ablation").agg(
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            r2_mean=("r2", "mean"),
            n_params=("n_params", "first"),
        ).sort_values("mae_mean")

        print(f"\n  {'Ablation':20s} {'MAE':>14s} {'RMSE':>10s} "
              f"{'R²':>8s} {'Params':>10s}")
        print("  " + "-" * 66)
        for name, row in summary.iterrows():
            print(
                f"  {name:20s} "
                f"{row['mae_mean']:.3f}±{row['mae_std']:.3f}  "
                f"{row['rmse_mean']:8.3f}  "
                f"{row['r2_mean']:8.4f}  "
                f"{row['n_params']:10,.0f}"
            )
    else:
        results_sorted = results_df.sort_values("mae")
        print(f"\n  {'Ablation':20s} {'MAE':>8s} {'RMSE':>8s} "
              f"{'R²':>8s} {'Params':>10s} {'Time':>8s}")
        print("  " + "-" * 66)
        for _, row in results_sorted.iterrows():
            print(
                f"  {row['name']:20s} "
                f"{row['mae']:8.3f} "
                f"{row['rmse']:8.3f} "
                f"{row['r2']:8.4f} "
                f"{row['n_params']:10,d} "
                f"{row['train_time_s']:7.0f}s"
            )

    # Delta from full model
    full_mae = results_df[results_df["ablation"] == "full"]["mae"].mean()
    print(f"\n  Reference (full): MAE = {full_mae:.3f}")
    print(f"\n  {'Ablation':20s} {'ΔMAE':>10s} {'Verdict':>20s}")
    print("  " + "-" * 55)

    for name in results_df["ablation"].unique():
        abl_mae = results_df[results_df["ablation"] == name]["mae"].mean()
        delta = abl_mae - full_mae
        if name == "full":
            verdict = "(reference)"
        elif delta > 0.05:
            verdict = f"IMPORTANT (+{delta:.3f})"
        elif delta > 0.01:
            verdict = f"helpful (+{delta:.3f})"
        elif delta > -0.01:
            verdict = f"negligible ({delta:+.3f})"
        else:
            verdict = f"harmful ({delta:+.3f})"
        print(f"  {name:20s} {delta:+10.3f} {verdict:>20s}")

    return results_df