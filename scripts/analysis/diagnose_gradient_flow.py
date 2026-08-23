#!/usr/bin/env python
"""Compare gradient flow between TGNN-Solv and DirectGNN."""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tgnn_solv.baselines.direct_gnn import DirectGNN  # noqa: E402
from tgnn_solv.config import TGNNSolvConfig  # noqa: E402
from tgnn_solv.data.dataset import make_loader  # noqa: E402
from tgnn_solv.device import resolve_device  # noqa: E402
from tgnn_solv.diagnostics import GradientFlowMonitor  # noqa: E402
from tgnn_solv.features import graph_feature_spec_from_config  # noqa: E402
from tgnn_solv.model import TGNNSolv  # noqa: E402


def _parse_override_value(raw: str) -> Any:
    lowered = raw.strip().lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if lowered in {"none", "null"}:
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def _apply_overrides(cfg: TGNNSolvConfig, overrides: list[str]) -> None:
    valid_fields = {field.name for field in dataclasses.fields(cfg)}
    for item in overrides:
        if "=" not in item:
            raise ValueError(
                f"Invalid override {item!r}. Expected KEY=VALUE, for example "
                "use_aux_direct_sol_loss=true."
            )
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if key not in valid_fields:
            raise ValueError(f"Unknown TGNNSolvConfig override: {key}")
        setattr(cfg, key, _parse_override_value(raw_value.strip()))


def _loader_for_config(
    csv_path: Path,
    cfg: TGNNSolvConfig,
    *,
    batch_size: int,
    max_rows: int,
    seed: int,
) -> torch.utils.data.DataLoader:
    df = pd.read_csv(csv_path, low_memory=False)
    if max_rows > 0 and len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=seed).reset_index(drop=True)
    return make_loader(
        df,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        cache=True,
        use_pair_temperature_batching=False,
        use_morgan_features=cfg.use_morgan_features,
        morgan_radius=cfg.morgan_radius,
        morgan_n_bits=cfg.morgan_n_bits,
        use_descriptor_augmentation=cfg.use_descriptor_augmentation,
        use_ionic_features=cfg.use_ionic_features,
        use_descriptor_priors=cfg.use_descriptor_priors,
        use_group_priors=cfg.requires_group_prior_features,
        use_gc_priors_crystal=cfg.use_gc_priors_crystal,
        use_gasteiger_charges=cfg.use_gasteiger_charges,
        use_phys_edge_features=cfg.use_phys_edge_features,
        explicit_h_small_molecules=cfg.explicit_h_small_molecules,
        explicit_h_max_heavy_atoms=cfg.explicit_h_max_heavy_atoms,
        use_pseudo_hansen=(cfg.use_hansen_contrastive or cfg.use_hansen_delta_loss) and cfg.use_pseudo_hansen,
        pseudo_hansen_weight_discount=cfg.pseudo_hansen_weight_discount,
        seed=seed,
    )


def _move_targets(targets: dict[str, Any], device: torch.device) -> dict[str, Any]:
    moved: dict[str, Any] = {}
    for key, value in targets.items():
        moved[key] = value.to(device) if isinstance(value, torch.Tensor) else value
    return moved


def _optional_tensor(targets: dict[str, Any], name: str) -> torch.Tensor | None:
    value = targets.get(name)
    return value if isinstance(value, torch.Tensor) else None


def _forward_loss(
    model: TGNNSolv | DirectGNN,
    solute_batch,
    solvent_batch,
    targets: dict[str, Any],
) -> torch.Tensor | None:
    T = targets["T"]
    mask = targets["has_solubility"].bool()
    if not bool(mask.any()):
        return None
    common = {
        "solvent_type": _optional_tensor(targets, "solvent_type"),
        "solute_morgan_fp": _optional_tensor(targets, "solute_morgan_fp"),
        "solvent_morgan_fp": _optional_tensor(targets, "solvent_morgan_fp"),
        "solute_descriptors": _optional_tensor(targets, "solute_descriptors"),
        "solvent_descriptors": _optional_tensor(targets, "solvent_descriptors"),
        "ionic_features": _optional_tensor(targets, "ionic_features"),
    }
    if isinstance(model, DirectGNN):
        output = model(solute_batch, solvent_batch, T, **common)
    else:
        output = model(
            solute_batch,
            solvent_batch,
            T,
            solute_descriptor_prior_features=_optional_tensor(targets, "solute_descriptor_prior_features"),
            solvent_descriptor_prior_features=_optional_tensor(targets, "solvent_descriptor_prior_features"),
            solute_group_prior_features=_optional_tensor(targets, "solute_group_prior_features"),
            solvent_group_prior_features=_optional_tensor(targets, "solvent_group_prior_features"),
            T_m_gc=_optional_tensor(targets, "T_m_gc"),
            dH_fus_gc=_optional_tensor(targets, "dH_fus_gc"),
            dCp_fus_gc=_optional_tensor(targets, "dCp_fus_gc"),
            targets=targets,
            detach_crystal_from_encoder=model.cfg.detach_crystal_from_encoder,
            **common,
        )
    loss = F.huber_loss(output["ln_x2"][mask], targets["ln_x2"][mask], delta=1.0)
    if (
        isinstance(model, TGNNSolv)
        and model.cfg.use_aux_direct_sol_loss
        and isinstance(output.get("ln_x2_aux"), torch.Tensor)
    ):
        aux_loss = F.huber_loss(
            output["ln_x2_aux"][mask],
            targets["ln_x2"][mask],
            delta=1.0,
        )
        loss = loss + float(model.cfg.aux_direct_sol_loss_weight) * aux_loss
    return loss


def _summarize_rescue_signal(results: dict[str, Any]) -> dict[str, float | None]:
    groups = results.get("TGNN-Solv", {}).get("groups", {})
    direct_groups = results.get("DirectGNN", {}).get("groups", {})

    def get(group: str, source: dict[str, Any] = groups) -> float | None:
        value = source.get(group, {}).get("mean_norm")
        return float(value) if value is not None else None

    interaction = get("interaction")
    direct_interaction = get("interaction", direct_groups)
    solvent = get("encoder.other")
    nrtl = get("nrtl_head")
    layer0 = get("encoder.layer.0")
    return {
        "tgnn_interaction": interaction,
        "direct_interaction": direct_interaction,
        "interaction_ratio_tgnn_direct": (
            interaction / direct_interaction
            if interaction is not None
            and direct_interaction is not None
            and direct_interaction > 0
            else None
        ),
        "tgnn_encoder_layer0": layer0,
        "tgnn_nrtl_head": nrtl,
        "encoder0_to_nrtl_ratio": (
            layer0 / nrtl
            if layer0 is not None and nrtl is not None and nrtl > 0
            else None
        ),
        "tgnn_encoder_other": solvent,
    }


def _parameter_group(name: str) -> str:
    match = re.search(r"(?:gnn|encoder).*layers\.(\d+)", name)
    if match:
        return f"encoder.layer.{match.group(1)}"
    if name.startswith("gnn.") or name.startswith("encoder."):
        return "encoder.other"
    if "head_nrtl" in name:
        return "nrtl_head"
    if "head_fusion" in name:
        return "crystal_head"
    if "head_hansen" in name or "head_aux" in name:
        return "aux_heads"
    if "cross_attn" in name or "bipartite" in name:
        return "interaction"
    if "readout" in name or "pair" in name or "token" in name:
        return "readout_pair"
    if "correction" in name:
        return "correction_head"
    if "prediction_head" in name:
        return "direct_head"
    return "other"


def _aggregate_groups(param_summary: dict[str, dict[str, float | int]]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for name, stats in param_summary.items():
        grouped[_parameter_group(name)].append(float(stats["mean_norm"]))
    return {
        group: {
            "mean_norm": float(np.mean(values)),
            "max_norm": float(np.max(values)),
            "n_params": len(values),
        }
        for group, values in sorted(grouped.items())
        if values
    }


def _run_steps(
    model: TGNNSolv | DirectGNN,
    loader,
    *,
    device: torch.device,
    n_steps: int,
    lr: float,
) -> dict[str, Any]:
    model.to(device).train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.0)
    monitor = GradientFlowMonitor(model)
    steps = 0
    losses: list[float] = []
    try:
        while steps < n_steps:
            for solute_batch, solvent_batch, targets in loader:
                solute_batch = solute_batch.to(device)
                solvent_batch = solvent_batch.to(device)
                targets = _move_targets(targets, device)
                optimizer.zero_grad(set_to_none=True)
                loss = _forward_loss(model, solute_batch, solvent_batch, targets)
                if loss is None:
                    continue
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach().cpu().item()))
                steps += 1
                if steps >= n_steps:
                    break
    finally:
        param_summary = monitor.summary()
        monitor.remove_hooks()
    group_summary = _aggregate_groups(param_summary)
    return {
        "loss_mean": float(np.mean(losses)) if losses else None,
        "loss_last": float(losses[-1]) if losses else None,
        "n_steps": steps,
        "parameters": param_summary,
        "groups": group_summary,
    }


def _ordered_groups(payload: dict[str, Any]) -> list[str]:
    preferred = [
        *[f"encoder.layer.{idx}" for idx in range(12)],
        "encoder.other",
        "interaction",
        "readout_pair",
        "crystal_head",
        "nrtl_head",
        "correction_head",
        "direct_head",
    ]
    groups = payload["groups"].keys()
    ordered = [group for group in preferred if group in groups]
    ordered.extend(sorted(group for group in groups if group not in ordered))
    return ordered


def _plot(results: dict[str, Any], output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    all_groups: list[str] = []
    for model_payload in results.values():
        for group in _ordered_groups(model_payload):
            if group not in all_groups:
                all_groups.append(group)
    x = np.arange(len(all_groups))
    fig, ax = plt.subplots(figsize=(11, 5.8))
    colors = {"TGNN-Solv": "#3B82F6", "DirectGNN": "#F59E0B"}
    for label, payload in results.items():
        values = [
            float(payload["groups"].get(group, {}).get("mean_norm", np.nan))
            for group in all_groups
        ]
        ax.plot(x, values, marker="o", lw=2.0, color=colors.get(label), label=label)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(all_groups, rotation=35, ha="right")
    ax.set_ylabel("средняя норма градиента")
    ax.set_title("Поток градиентов по блокам модели")
    ax.grid(axis="y", alpha=0.22)
    ax.legend()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output)
    if output.suffix.lower() == ".pdf":
        fig.savefig(output.with_suffix(".png"), dpi=300)
    plt.close(fig)


def _make_model(cfg: TGNNSolvConfig, family: str):
    feature_spec = graph_feature_spec_from_config(cfg)
    if family == "direct":
        return DirectGNN(
            node_feat_dim=feature_spec.node_dim,
            edge_feat_dim=feature_spec.edge_dim,
            cfg=cfg,
        )
    return TGNNSolv(
        node_feat_dim=feature_spec.node_dim,
        edge_feat_dim=feature_spec.edge_dim,
        cfg=cfg,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--directgnn-config", required=True, type=Path)
    parser.add_argument("--train-data", required=True, type=Path)
    parser.add_argument("--n-steps", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-rows", type=int, default=5000)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output", type=Path, default=Path("results/gradient_flow"))
    parser.add_argument("--plot", type=Path, default=Path("figures/gradient_flow.pdf"))
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        help=(
            "Override TGNN config field as KEY=VALUE. Can be passed multiple "
            "times, e.g. --override use_aux_direct_sol_loss=true."
        ),
    )
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = resolve_device(args.device)

    tgnn_cfg = TGNNSolvConfig.from_yaml(str(args.config))
    _apply_overrides(tgnn_cfg, args.override)
    direct_cfg = TGNNSolvConfig.from_yaml(str(args.directgnn_config))
    tgnn_loader = _loader_for_config(
        args.train_data,
        tgnn_cfg,
        batch_size=args.batch_size,
        max_rows=args.max_rows,
        seed=args.seed,
    )
    direct_loader = _loader_for_config(
        args.train_data,
        direct_cfg,
        batch_size=args.batch_size,
        max_rows=args.max_rows,
        seed=args.seed,
    )

    results = {
        "TGNN-Solv": _run_steps(
            _make_model(tgnn_cfg, "tgnn"),
            tgnn_loader,
            device=device,
            n_steps=args.n_steps,
            lr=args.lr,
        ),
        "DirectGNN": _run_steps(
            _make_model(direct_cfg, "direct"),
            direct_loader,
            device=device,
            n_steps=args.n_steps,
            lr=args.lr,
        ),
    }

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "gradient_flow_summary.json").write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )
    rescue_summary = _summarize_rescue_signal(results)
    (args.output / "gradient_flow_rescue_summary.json").write_text(
        json.dumps(
            {
                "tgnn_config": str(args.config),
                "directgnn_config": str(args.directgnn_config),
                "overrides": args.override,
                "summary": rescue_summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _plot(results, args.plot)

    tgnn_groups = results["TGNN-Solv"]["groups"]
    layer0 = float(tgnn_groups.get("encoder.layer.0", {}).get("mean_norm", float("nan")))
    nrtl = float(tgnn_groups.get("nrtl_head", {}).get("mean_norm", float("nan")))
    ratio = layer0 / nrtl if np.isfinite(layer0) and np.isfinite(nrtl) and nrtl > 0 else float("nan")
    print(f"[gradient-flow] wrote {args.output / 'gradient_flow_summary.json'}")
    print(f"[gradient-flow] wrote {args.output / 'gradient_flow_rescue_summary.json'}")
    print(f"[gradient-flow] wrote {args.plot}")
    print(f"[gradient-flow] TGNN encoder.layer.0 / nrtl_head = {ratio:.3g}")
    interaction_ratio = rescue_summary["interaction_ratio_tgnn_direct"]
    if interaction_ratio is not None:
        print(
            "[gradient-flow] TGNN interaction / DirectGNN interaction = "
            f"{interaction_ratio:.3g}"
        )


if __name__ == "__main__":
    main()
