#!/usr/bin/env python
"""Inspect parameter distributions by model block."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
for candidate in (SCRIPTS, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import _bootstrap  # noqa: F401,E402
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from tgnn_solv.device import resolve_device  # noqa: E402
from tgnn_solv.inference import load_directgnn_model, load_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize trained weight distributions by architectural block.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-points-per-group", type=int, default=6000)
    return parser.parse_args()


def _load_any(path: Path, device: torch.device):
    try:
        model, cfg = load_model(str(path), device=device)
        return model, cfg, "TGNN-Solv"
    except Exception as tgnn_error:
        try:
            model, cfg = load_directgnn_model(str(path), device=device)
            return model, cfg, "DirectGNN"
        except Exception as direct_error:
            raise RuntimeError(
                f"Could not load checkpoint as TGNN-Solv ({tgnn_error}) "
                f"or DirectGNN ({direct_error})."
            ) from direct_error


def _group_name(name: str) -> str:
    lower = name.lower()
    if ("phi_disp" in lower or "disp" in lower) and ("gnn" in lower or "encoder" in lower):
        return "timp_disp"
    if ("phi_polar" in lower or "polar" in lower) and ("gnn" in lower or "encoder" in lower):
        return "timp_polar"
    if lower.startswith("gnn.") or lower.startswith("encoder."):
        return "encoder"
    if "cross_attn" in lower or "bipartite" in lower or "interaction" in lower:
        return "interaction"
    if "head_fusion" in lower or "fusion_head" in lower:
        return "crystal_head"
    if "head_nrtl" in lower or "nrtl" in lower:
        return "nrtl_head"
    if "correction" in lower:
        return "correction"
    if "prediction_head" in lower or "direct" in lower:
        return "direct_head"
    if "hansen" in lower:
        return "hansen_head"
    if "solvent_moe" in lower or "moe" in lower:
        return "solvent_moe"
    return "other"


def _stats(values: np.ndarray) -> dict[str, float | int]:
    if values.size == 0:
        return {
            "n": 0,
            "mean": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "fraction_zero": float("nan"),
            "fraction_extreme": float("nan"),
        }
    mean = float(values.mean())
    std = float(values.std())
    return {
        "n": int(values.size),
        "mean": mean,
        "std": std,
        "min": float(values.min()),
        "max": float(values.max()),
        "q005": float(np.quantile(values, 0.005)),
        "q995": float(np.quantile(values, 0.995)),
        "fraction_zero": float(np.mean(np.abs(values) < 1.0e-6)),
        "fraction_extreme": float(
            np.mean(np.abs(values - mean) > 3.0 * max(std, 1.0e-12))
        ),
    }


def _plot(groups: dict[str, list[np.ndarray]], output_dir: Path, max_points: int) -> None:
    rng = np.random.default_rng(42)
    order = [
        "encoder",
        "timp_disp",
        "timp_polar",
        "interaction",
        "crystal_head",
        "nrtl_head",
        "correction",
        "direct_head",
        "hansen_head",
        "solvent_moe",
        "other",
    ]
    labels: list[str] = []
    data: list[np.ndarray] = []
    zero_fractions: list[float] = []
    extreme_fractions: list[float] = []
    for group in order:
        if group not in groups:
            continue
        values = np.concatenate(groups[group])
        q_low, q_high = np.quantile(values, [0.005, 0.995])
        clipped = np.clip(values, q_low, q_high)
        zero_fractions.append(float(np.mean(np.abs(values) < 1.0e-6)))
        mean = float(values.mean())
        std = float(values.std())
        extreme_fractions.append(
            float(np.mean(np.abs(values - mean) > 3.0 * max(std, 1.0e-12)))
        )
        values = clipped
        if values.size > max_points:
            values = rng.choice(values, size=max_points, replace=False)
        labels.append(group)
        data.append(values)
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(12.8, 5.5),
        gridspec_kw={"width_ratios": [2.6, 1.55], "wspace": 0.42},
    )
    ax = axes[0]
    parts = ax.violinplot(data, showmeans=True, showextrema=False)
    for body in parts["bodies"]:
        body.set_facecolor("#A8DADC")
        body.set_edgecolor("#4C78A8")
        body.set_alpha(0.78)
    parts["cmeans"].set_color("#E45756")
    ax.boxplot(
        data,
        positions=np.arange(1, len(labels) + 1),
        widths=0.16,
        showfliers=False,
        patch_artist=True,
        boxprops={"facecolor": "white", "edgecolor": "#4C5A67", "linewidth": 0.9},
        medianprops={"color": "#E45756", "linewidth": 1.4},
        whiskerprops={"color": "#7A8691", "linewidth": 0.8},
        capprops={"color": "#7A8691", "linewidth": 0.8},
    )
    ax.set_xticks(np.arange(1, len(labels) + 1), labels, rotation=30, ha="right")
    ax.set_ylabel("значение веса")
    ax.set_title("Центральные 99% значений весов")
    ax.axhline(0.0, color="#7A8691", lw=0.9, alpha=0.7)
    ax.grid(True, axis="y", alpha=0.25)
    ax2 = axes[1]
    y_pos = np.arange(len(labels))
    height = 0.34
    zero_pct = [100.0 * v for v in zero_fractions]
    extreme_pct = [100.0 * v for v in extreme_fractions]
    ax2.barh(
        y_pos - height / 2,
        zero_pct,
        height=height,
        color="#6BAED6",
        edgecolor="#3C6E91",
        alpha=0.9,
        label=r"$|w| < 10^{-6}$",
    )
    ax2.barh(
        y_pos + height / 2,
        extreme_pct,
        height=height,
        color="#F4A261",
        edgecolor="#C77000",
        alpha=0.9,
        label=r"$|w-\mu| > 3\sigma$",
    )
    ax2.set_yticks(y_pos, labels)
    ax2.invert_yaxis()
    max_pct = max(zero_pct + extreme_pct) if (zero_pct or extreme_pct) else 1.0
    ax2.set_xlim(0.0, max(0.6, max_pct * 1.35))
    ax2.set_xlabel("доля параметров, %")
    ax2.set_title("Нулевые и экстремальные веса")
    ax2.grid(True, axis="x", alpha=0.25)
    ax2.tick_params(axis="y", labelsize=8.5, pad=2)
    ax2.legend(loc="lower right", fontsize=7.2, frameon=True)
    fig.suptitle("Распределение весов по архитектурным блокам", y=1.02)
    fig.text(
        0.02,
        0.002,
        "Слева показаны центральные 99% значений; выбросы сохранены в CSV-статистике.",
        fontsize=8.5,
        color="#4C5A67",
    )
    fig.subplots_adjust(bottom=0.20)
    fig.savefig(output_dir / "weight_violin.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "weight_violin.png", dpi=220, bbox_inches="tight")


def main() -> None:
    args = parse_args()
    checkpoint = Path(args.checkpoint).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    model, cfg, family = _load_any(checkpoint, resolve_device(args.device))

    param_rows: list[dict[str, object]] = []
    grouped_values: dict[str, list[np.ndarray]] = {}
    for name, param in model.named_parameters():
        values = param.detach().cpu().float().numpy().ravel()
        group = _group_name(name)
        grouped_values.setdefault(group, []).append(values)
        param_rows.append(
            {
                "parameter": name,
                "group": group,
                **_stats(values),
            }
        )
    param_df = pd.DataFrame(param_rows)
    param_df.to_csv(output_dir / "parameter_stats.csv", index=False)

    group_rows = []
    for group, arrays in grouped_values.items():
        group_rows.append({"group": group, **_stats(np.concatenate(arrays))})
    group_df = pd.DataFrame(group_rows).sort_values("group")
    group_df.to_csv(output_dir / "group_stats.csv", index=False)
    _plot(grouped_values, output_dir, int(args.max_points_per_group))

    summary = {
        "checkpoint": str(checkpoint),
        "model_family": family,
        "encoder_type": str(getattr(cfg, "encoder_type", "unknown")),
        "groups": group_df.to_dict(orient="records"),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote weight analysis to {output_dir}")


if __name__ == "__main__":
    main()
