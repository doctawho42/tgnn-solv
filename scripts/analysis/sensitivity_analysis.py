#!/usr/bin/env python
"""Sensitivity analysis for TGNN-Solv physical parameters."""

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


ALIASES = {
    "T": ("T", "temperature"),
    "T_m": ("T_m_solver", "T_m_pred", "T_m"),
    "dH_fus": ("dH_fus_solver", "dH_fus_pred", "dH_fus"),
    "tau_12": ("tau_12", "tau_12_pred"),
    "tau_21": ("tau_21", "tau_21_pred"),
    "alpha": ("alpha_12", "alpha_pred"),
    "ln_x2": ("ln_x2_final", "ln_x2_pred", "ln_x2"),
    "true": ("ln_x2_true", "ln_x2"),
    "abs_error": ("abs_error",),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute per-sample sensitivities d ln(x2) / d physical parameter "
            "from an intermediates CSV."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--intermediates", required=True, help="CSV with TGNN intermediates.")
    parser.add_argument("--test-data", default=None, help="Optional test CSV for row alignment.")
    parser.add_argument("--output-dir", required=True, help="Directory for CSV and plots.")
    parser.add_argument("--r", type=float, default=8.314, help="Gas constant.")
    return parser.parse_args()


def _col(df: pd.DataFrame, name: str, *, required: bool = True) -> pd.Series | None:
    for candidate in ALIASES[name]:
        if candidate in df.columns:
            return pd.to_numeric(df[candidate], errors="coerce")
    if required:
        raise ValueError(
            f"Missing required column for {name!r}. Tried: {', '.join(ALIASES[name])}"
        )
    return None


def _nrtl_derivatives(
    *,
    x2_np: np.ndarray,
    tau12_np: np.ndarray,
    tau21_np: np.ndarray,
    alpha_np: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x2 = torch.tensor(x2_np, dtype=torch.float64, requires_grad=True)
    tau12 = torch.tensor(tau12_np, dtype=torch.float64, requires_grad=True)
    tau21 = torch.tensor(tau21_np, dtype=torch.float64, requires_grad=True)
    alpha = torch.tensor(alpha_np, dtype=torch.float64, requires_grad=True)
    x1 = 1.0 - x2
    G12 = torch.exp(-alpha * tau12)
    G21 = torch.exp(-alpha * tau21)
    eps = 1.0e-10
    A = x2 + x1 * G12 + eps
    B = x1 + x2 * G21 + eps
    ln_gamma = x1.pow(2) * (
        tau12 * (G12 / A).pow(2) + tau21 * G21 / B.pow(2)
    )
    grads = torch.autograd.grad(
        ln_gamma.sum(),
        (x2, tau12, tau21, alpha),
        allow_unused=False,
    )
    return tuple(g.detach().cpu().numpy() for g in grads)  # type: ignore[return-value]


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    if path.suffix.lower() != ".png":
        fig.savefig(path.with_suffix(".png"), dpi=220, bbox_inches="tight")


def _boxplot(out: pd.DataFrame, output_dir: Path) -> None:
    cols = [
        ("d_lnx2_dTm_abs", "$T_m$"),
        ("d_lnx2_ddH_abs", "$\\Delta H_{fus}$"),
        ("d_lnx2_dtau12_abs", "$\\tau_{12}$"),
        ("d_lnx2_dtau21_abs", "$\\tau_{21}$"),
        ("d_lnx2_dalpha_abs", "$\\alpha$"),
    ]
    data = [out[col].replace([np.inf, -np.inf], np.nan).dropna().to_numpy() for col, _ in cols]
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    box = ax.boxplot(
        data,
        tick_labels=[label for _, label in cols],
        showfliers=False,
        patch_artist=True,
    )
    for patch, color in zip(box["boxes"], ["#A8DADC", "#C7E9C0", "#FAD2A5", "#F8B4A5", "#D7C2F0"], strict=False):
        patch.set_facecolor(color)
    ax.set_yscale("log")
    ax.set_ylabel(r"$|\partial \ln x_2 / \partial \theta|$")
    ax.set_title("Распределение чувствительности по тестовым примерам")
    ax.grid(True, axis="y", alpha=0.25)
    _save(fig, output_dir / "sensitivity_boxplot.pdf")


def _scatter(out: pd.DataFrame, output_dir: Path) -> None:
    if "abs_error" not in out.columns or out["abs_error"].notna().sum() < 5:
        return
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    x = out["d_lnx2_dtau12_abs"].replace([np.inf, -np.inf], np.nan)
    y = out["abs_error"].replace([np.inf, -np.inf], np.nan)
    mask = x.notna() & y.notna()
    ax.scatter(x[mask], y[mask], s=9, alpha=0.35, color="#4C78A8")
    ax.set_xscale("log")
    ax.set_xlabel(r"$|\partial \ln x_2 / \partial \tau_{12}|$")
    ax.set_ylabel(r"$|\mathrm{ошибка}\ \ln x_2|$")
    ax.set_title("Чувствительность к $\\tau_{12}$ и ошибка")
    ax.grid(True, alpha=0.25)
    corr = np.corrcoef(np.log10(x[mask].clip(lower=1e-12)), y[mask])[0, 1] if mask.sum() > 2 else np.nan
    if np.isfinite(corr):
        ax.text(
            0.03,
            0.95,
            f"corr(log sens, error) = {corr:.2f}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=10,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#B8C2CC"},
        )
    _save(fig, output_dir / "sensitivity_vs_error.pdf")


def _heatmap(out: pd.DataFrame, output_dir: Path) -> None:
    if out["ln_x2_final"].notna().sum() < 5:
        return
    bins = [-30, -12, -8, -5, -3, -1, 1]
    labels = ["<-12", "-12..-8", "-8..-5", "-5..-3", "-3..-1", ">-1"]
    grouped = (
        out.assign(solubility_bin=pd.cut(out["ln_x2_final"], bins=bins, labels=labels))
        .groupby("solubility_bin", observed=False)[
            ["d_lnx2_dTm_abs", "d_lnx2_ddH_abs", "d_lnx2_dtau12_abs", "d_lnx2_dtau21_abs", "d_lnx2_dalpha_abs"]
        ]
        .median()
    )
    fig, ax = plt.subplots(figsize=(8.8, 4.3))
    matrix = np.log10(grouped.replace(0, np.nan).to_numpy(dtype=float))
    im = ax.imshow(matrix.T, aspect="auto", cmap="YlGnBu")
    ax.set_xticks(np.arange(len(grouped.index)), grouped.index.astype(str), rotation=25, ha="right")
    ax.set_yticks(
        np.arange(5),
        ["$T_m$", "$\\Delta H$", "$\\tau_{12}$", "$\\tau_{21}$", "$\\alpha$"],
    )
    ax.set_title("Медианная чувствительность по диапазонам растворимости")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(r"$\log_{10}|\partial \ln x_2 / \partial \theta|$")
    _save(fig, output_dir / "sensitivity_heatmap.pdf")


def main() -> None:
    args = parse_args()
    path = Path(args.intermediates).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(path, low_memory=False)

    T = _col(df, "T").to_numpy(dtype=float)
    Tm = _col(df, "T_m").to_numpy(dtype=float)
    dH = _col(df, "dH_fus").to_numpy(dtype=float)
    tau12 = _col(df, "tau_12").to_numpy(dtype=float)
    tau21 = _col(df, "tau_21").to_numpy(dtype=float)
    alpha = _col(df, "alpha").to_numpy(dtype=float)
    ln_x2 = _col(df, "ln_x2").to_numpy(dtype=float)
    x2 = np.clip(np.exp(ln_x2), 1.0e-12, 1.0 - 1.0e-8)

    eta, dgamma_dtau12, dgamma_dtau21, dgamma_dalpha = _nrtl_derivatives(
        x2_np=x2,
        tau12_np=tau12,
        tau21_np=tau21,
        alpha_np=alpha,
    )
    denom = 1.0 + x2 * eta
    denom = np.where(np.abs(denom) < 1.0e-8, np.nan, denom)

    out = pd.DataFrame(
        {
            "sample_id": np.arange(len(df)),
            "ln_x2_final": ln_x2,
            "T": T,
            "T_m": Tm,
            "dH_fus": dH,
            "tau_12": tau12,
            "tau_21": tau21,
            "alpha": alpha,
            "eta": eta,
            "denominator": denom,
            "d_lnx2_dTm": -(dH / (float(args.r) * np.square(Tm))) / denom,
            "d_lnx2_ddH": -(1.0 / float(args.r) * (1.0 / T - 1.0 / Tm)) / denom,
            "d_lnx2_dtau12": -dgamma_dtau12 / denom,
            "d_lnx2_dtau21": -dgamma_dtau21 / denom,
            "d_lnx2_dalpha": -dgamma_dalpha / denom,
        }
    )
    for col in ("d_lnx2_dTm", "d_lnx2_ddH", "d_lnx2_dtau12", "d_lnx2_dtau21", "d_lnx2_dalpha"):
        out[f"{col}_abs"] = out[col].abs()
    err = _col(df, "abs_error", required=False)
    if err is not None:
        out["abs_error"] = err.to_numpy(dtype=float)
    elif {"ln_x2_true", "ln_x2_final"}.issubset(df.columns):
        out["abs_error"] = (df["ln_x2_final"].astype(float) - df["ln_x2_true"].astype(float)).abs()

    out.to_csv(output_dir / "sensitivity_per_sample.csv", index=False)
    _boxplot(out, output_dir)
    _scatter(out, output_dir)
    _heatmap(out, output_dir)

    summary = {
        "n_samples": int(len(out)),
        "median_abs": {
            name: float(out[f"{name}_abs"].median())
            for name in ("d_lnx2_dTm", "d_lnx2_ddH", "d_lnx2_dtau12", "d_lnx2_dtau21", "d_lnx2_dalpha")
        },
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote sensitivity outputs to {output_dir}")


if __name__ == "__main__":
    main()
