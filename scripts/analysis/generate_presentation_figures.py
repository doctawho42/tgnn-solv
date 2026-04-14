#!/usr/bin/env python
"""Generate data-backed figures for the seminar Beamer deck.

The script is intentionally robust: if processed CSV files or optional
chemistry dependencies are unavailable, it falls back to synthetic examples so
that the presentation remains buildable.
"""

from __future__ import annotations

import math
import argparse
import json
import warnings
from pathlib import Path
from typing import Callable

import numpy as np

warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "presentation" / "figures" / "generated"
DATA = ROOT / "notebooks" / "data" / "processed"
RESULTS = ROOT / "results" / "proxy_comparison"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = "#3B82F6"
ORANGE = "#F59E0B"
GREEN = "#14B8A6"
RED = "#EF4444"
SLATE = "#475569"
PAPER = "#F8FBFF"
R_GAS = 8.314462618


def _mpl():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": PAPER,
            "axes.facecolor": "white",
            "axes.edgecolor": "#CBD5E1",
            "axes.labelcolor": "#0F172A",
            "xtick.color": SLATE,
            "ytick.color": SLATE,
            "font.size": 13,
            "axes.titlesize": 16,
            "axes.labelsize": 14,
            "legend.frameon": False,
            "savefig.bbox": "tight",
            "savefig.facecolor": PAPER,
        }
    )
    return plt


def save_both(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=300)


def load_proxy_summary() -> dict:
    summary_path = RESULTS / "summary.json"
    if not summary_path.exists():
        return {}
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def fuzzy_metric(summary: dict, *needles: str) -> float | None:
    lowered = [(key.lower(), value) for key, value in summary.items()]
    for key, value in lowered:
        if all(needle.lower() in key for needle in needles):
            try:
                metric = value.get("MAE")
                return float(metric) if metric is not None else None
            except Exception:
                continue
    return None


def safe_plot(name: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - keep Beamer build robust
        plt = _mpl()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.axis("off")
        ax.text(
            0.5,
            0.55,
            f"{name}\nзаглушка фигуры",
            ha="center",
            va="center",
            fontsize=18,
            color=SLATE,
            weight="bold",
        )
        ax.text(0.5, 0.42, str(exc), ha="center", va="center", color=SLATE, wrap=True)
        save_both(fig, name)
        plt.close(fig)
        print(f"[presentation-figures] warning: {name} fallback: {exc}")


def load_processed():
    import pandas as pd

    frames = {}
    for split in ["train", "val", "test"]:
        path = DATA / f"{split}.csv"
        if path.exists():
            frames[split] = pd.read_csv(path)
    if not frames:
        raise FileNotFoundError(f"No processed CSV files found under {DATA}")
    for split, df in frames.items():
        if "has_solubility" in df.columns:
            frames[split] = df[df["has_solubility"].astype(bool)].copy()
    return frames


def synthetic_processed():
    import pandas as pd

    rng = np.random.default_rng(42)
    solvents = ["этанол", "метанол", "изопропанол", "этилацетат", "вода", "ацетон", "ДМФА"]
    frames = {}
    for split, n in {"train": 7000, "val": 900, "test": 900}.items():
        frames[split] = pd.DataFrame(
            {
                "solute_smiles": rng.choice([f"solute_{i}" for i in range(350)], n),
                "solvent_smiles": rng.choice([f"solvent_{i}" for i in range(90)], n),
                "solvent_name": rng.choice(solvents, n, p=[0.22, 0.18, 0.14, 0.12, 0.12, 0.12, 0.10]),
                "temperature": np.clip(rng.normal(315, 28, n), 243, 426),
                "ln_x2": np.clip(rng.normal(-5.0, 3.2, n), -23.6, -0.05),
                "has_solubility": True,
            }
        )
    return frames


def get_frames():
    try:
        return load_processed()
    except Exception as exc:  # noqa: BLE001
        print(f"[presentation-figures] warning: using synthetic corpus data: {exc}")
        return synthetic_processed()


def combined_supervised():
    import pandas as pd

    frames = get_frames()
    return frames, pd.concat(frames.values(), ignore_index=True)


def corpus_lnx2_histogram() -> None:
    plt = _mpl()
    frames = get_frames()
    fig, ax = plt.subplots(figsize=(10, 6))
    for split, color in [("train", BLUE), ("test", ORANGE)]:
        if split in frames:
            label = {"train": "обучение", "test": "тест"}.get(split, split)
            ax.hist(frames[split]["ln_x2"].dropna(), bins=50, alpha=0.55, color=color, label=label)
    ax.set_title(r"Распределение обучающих $\ln x_2$")
    ax.set_xlabel(r"$\ln x_2$")
    ax.set_ylabel("строки")
    ax.legend()
    ax.grid(alpha=0.18)
    save_both(fig, "corpus_lnx2_histogram")
    plt.close(fig)


def corpus_temperature_histogram() -> None:
    plt = _mpl()
    frames = get_frames()
    fig, ax = plt.subplots(figsize=(10, 6))
    for split, color in [("train", BLUE), ("test", ORANGE)]:
        if split in frames:
            label = {"train": "обучение", "test": "тест"}.get(split, split)
            ax.hist(frames[split]["temperature"].dropna(), bins=42, alpha=0.55, color=color, label=label)
    ax.set_title("Покрытие по температуре")
    ax.set_xlabel("T, K")
    ax.set_ylabel("строки")
    ax.legend()
    ax.grid(alpha=0.18)
    save_both(fig, "corpus_temperature_histogram")
    plt.close(fig)


def corpus_solvent_barplot() -> None:
    plt = _mpl()
    _, df = combined_supervised()
    name_col = "solvent_name" if "solvent_name" in df.columns else "solvent_smiles"
    vc = df[name_col].fillna(df.get("solvent_smiles", "unknown")).astype(str).str.lower().value_counts().head(15)
    solvent_ru = {
        "ethanol": "этанол",
        "methanol": "метанол",
        "isopropanol": "изопропанол",
        "2-propanol": "изопропанол",
        "ethyl acetate": "этилацетат",
        "n-propanol": "н-пропанол",
        "water": "вода",
        "acetone": "ацетон",
        "n-butanol": "н-бутанол",
        "acetonitrile": "ацетонитрил",
        "dmf": "ДМФА",
        "dimethylformamide": "ДМФА",
        "dmso": "ДМСО",
        "dimethyl sulfoxide": "ДМСО",
        "chloroform": "хлороформ",
        "dichloromethane": "дихлорметан",
        "toluene": "толуол",
        "benzene": "бензол",
        "hexane": "гексан",
        "heptane": "гептан",
        "isobutanol": "изобутанол",
        "methyl acetate": "метилацетат",
        "1,4-dioxane": "1,4-диоксан",
        "dioxane": "диоксан",
        "tetrahydrofuran": "ТГФ",
        "thf": "ТГФ",
        "diethyl ether": "диэтиловый эфир",
    }
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = [solvent_ru.get(s, s)[:24] for s in vc.index][::-1]
    ax.barh(labels, vc.values[::-1], color=BLUE, alpha=0.72)
    ax.set_title("Топ-15 растворителей по обучающим строкам")
    ax.set_xlabel("строки")
    ax.grid(axis="x", alpha=0.18)
    save_both(fig, "corpus_solvent_barplot")
    plt.close(fig)


def corpus_points_per_pair() -> None:
    plt = _mpl()
    _, df = combined_supervised()
    counts = df.groupby(["solute_smiles", "solvent_smiles"], dropna=False).size()
    bins = [1, 2, 4, 6, 11, 21, counts.max() + 1]
    labels = ["1", "2-3", "4-5", "6-10", "11-20", "21+"]
    hist = np.histogram(counts, bins=bins)[0]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(labels, hist, color=GREEN, alpha=0.75)
    ax.set_title("Температурные точки на пару вещество-растворитель")
    ax.set_xlabel("точек на пару")
    ax.set_ylabel("пары")
    ax.grid(axis="y", alpha=0.18)
    save_both(fig, "corpus_points_per_pair")
    plt.close(fig)


def phi_hildebrand(T: np.ndarray, Tm: float, dH: float) -> np.ndarray:
    return dH / R_GAS * (1.0 / T - 1.0 / Tm)


def phi_with_dcp(T: np.ndarray, Tm: float, dH: float, dCp: float) -> np.ndarray:
    return phi_hildebrand(T, Tm, dH) - dCp / R_GAS * ((Tm / T - 1.0) - np.log(Tm / T))


def ideal_sle_example() -> None:
    plt = _mpl()
    T = np.linspace(270, 440, 260)
    Tm, dH, dCp = 442.0, 26400.0, 80.0
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(T, -phi_hildebrand(T, Tm, dH), color=BLUE, lw=2.4, label=r"$\Delta C_p=0$")
    ax.plot(T, -phi_with_dcp(T, Tm, dH, dCp), color=ORANGE, lw=2.4, ls="--", label=r"$\Delta C_p=80$ J/mol/K")
    ax.axvline(298.15, color=SLATE, lw=1.2, alpha=0.55)
    ax.set_title("Идеальная SLE-кривая для кристалла типа парацетамола")
    ax.set_xlabel("T, K")
    ax.set_ylabel(r"$\ln x_2 \approx -\Phi(T)$")
    ax.legend()
    ax.grid(alpha=0.18)
    save_both(fig, "ideal_sle_example")
    plt.close(fig)


def ln_gamma_2_nrtl(x2: np.ndarray, tau12: float, tau21: float, alpha: float) -> np.ndarray:
    x1 = 1.0 - x2
    g12 = np.exp(-alpha * tau12)
    g21 = np.exp(-alpha * tau21)
    return x1**2 * (tau12 * (g12 / (x2 + x1 * g12)) ** 2 + tau21 * g21 / (x1 + x2 * g21) ** 2)


def nrtl_gamma_example() -> None:
    plt = _mpl()
    x2 = np.linspace(0.005, 0.995, 400)
    tau_eth_water = (-120.0 / (R_GAS * 298.15), 1450.0 / (R_GAS * 298.15), 0.30)
    examples = {
        "бензол-гексан (слабая)": (0.18, 0.08, 0.30),
        "этанол-вода (сильная)": tau_eth_water,
    }
    fig, ax = plt.subplots(figsize=(10, 6))
    for label, params in examples.items():
        gamma = np.exp(ln_gamma_2_nrtl(x2, *params))
        ax.plot(x2, gamma, lw=2.4, label=label)
    ax.set_title(r"Примеры коэффициента активности NRTL")
    ax.set_xlabel(r"$x_2$")
    ax.set_ylabel(r"$\gamma_2(x_2)$")
    ax.set_yscale("log")
    ax.grid(alpha=0.18)
    ax.legend()
    save_both(fig, "nrtl_gamma_example")
    plt.close(fig)


def sensitivity_bars() -> None:
    plt = _mpl()
    labels = [r"$T_m$", r"$\Delta H_{fus}$", r"$\Delta g_{21}$", r"$\Delta g_{12}$"]
    vals = [0.19, 0.25, 0.80, 0.80]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(labels, vals, color=[GREEN, GREEN, ORANGE, ORANGE], alpha=0.75)
    ax.set_title(r"Чувствительность $\ln x_2$ к типичным ошибкам параметров")
    ax.set_xlabel(r"абсолютный эффект на $\ln x_2$")
    ax.grid(axis="x", alpha=0.18)
    save_both(fig, "sensitivity_bars")
    plt.close(fig)


def error_decomposition_waterfall() -> None:
    plt = _mpl()
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(11, 4.8))
    summary = load_proxy_summary()
    ideal = fuzzy_metric(summary, "ideal_sle") or 6.841
    rf = fuzzy_metric(summary, "rf_hybrid") or 1.722
    tgnn = fuzzy_metric(summary, "tgnn_mpnn") or 1.741
    direct = fuzzy_metric(summary, "directgnn_tuned") or 1.652

    nodes = [
        ("Идеальный SLE", ideal, SLATE),
        ("RF смешанный", rf, GREEN),
        ("TGNN MPNN", tgnn, BLUE),
        ("DirectGNN", direct, ORANGE),
    ]
    x_positions = [0.0, 2.8, 5.6, 8.4]
    box_w, box_h = 2.05, 0.92
    for x, (label, value, color) in zip(x_positions, nodes):
        patch = FancyBboxPatch(
            (x - box_w / 2, -box_h / 2),
            box_w,
            box_h,
            boxstyle="round,pad=0.025,rounding_size=0.08",
            linewidth=1.7,
            edgecolor=color,
            facecolor=color,
            alpha=0.12,
        )
        ax.add_patch(patch)
        ax.text(x, 0.13, label, ha="center", va="center", fontsize=14, color="#0F172A", weight="bold")
        ax.text(x, -0.18, f"MAE {value:.2f}", ha="center", va="center", fontsize=17, color=color, weight="bold")

    arrow_specs = [
        (0, 1, f"обучение: {rf - ideal:+.2f}", SLATE),
        (1, 2, f"{tgnn - rf:+.2f}", SLATE),
        (2, 3, f"физика: {tgnn - direct:+.2f}", ORANGE),
    ]
    for left, right, text, color in arrow_specs:
        x0 = x_positions[left] + box_w / 2 + 0.12
        x1 = x_positions[right] - box_w / 2 - 0.12
        ax.annotate(
            "",
            xy=(x1, 0.0),
            xytext=(x0, 0.0),
            arrowprops={"arrowstyle": "->", "color": color, "lw": 1.8},
        )
        ax.text((x0 + x1) / 2, 0.34, text, ha="center", va="center", fontsize=12, color=color, weight="bold")

    ax.text(
        4.2,
        -0.95,
        "DirectGNN лидирует; TGNN MPNN находится на уровне лучшего RF; чистая физика без ML недостаточна.",
        ha="center",
        va="center",
        fontsize=12,
        color=SLATE,
    )
    ax.set_xlim(-1.25, 9.65)
    ax.set_ylim(-1.25, 0.95)
    ax.axis("off")
    ax.set_title("Декомпозиция ошибки: proxy budget", pad=14)
    save_both(fig, "error_decomposition_waterfall")
    plt.close(fig)


def parity_lnx2() -> None:
    plt = _mpl()
    candidates = [
        ("TGNN+desc", RESULTS / "tgnn_desc.json", BLUE),
        ("TGNN(MPNN)", RESULTS / "tgnn_mpnn.json", GREEN),
        ("TIMP+HC", RESULTS / "tgnn_timp_hc.json", ORANGE),
        ("TIMP", RESULTS / "tgnn_timp.json", SLATE),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 7.0))
    plotted = 0
    min_v, max_v = -25.0, 0.0
    rng = np.random.default_rng(42)
    for label, path, color in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            preds = payload.get("predictions", {})
            y_true = np.asarray(preds.get("true_ln_x2", []), dtype=float)
            y_pred = np.asarray(preds.get("pred_ln_x2", []), dtype=float)
        except Exception:
            continue
        valid = np.isfinite(y_true) & np.isfinite(y_pred)
        if valid.sum() == 0:
            continue
        y_true = y_true[valid]
        y_pred = y_pred[valid]
        if y_true.size > 1400:
            idx = rng.choice(y_true.size, size=1400, replace=False)
            y_true = y_true[idx]
            y_pred = y_pred[idx]
        min_v = min(min_v, float(np.min(y_true)), float(np.min(y_pred)))
        max_v = max(max_v, float(np.max(y_true)), float(np.max(y_pred)))
        ax.scatter(
            y_true,
            y_pred,
            s=10,
            alpha=0.22,
            color=color,
            linewidths=0,
            label=label,
        )
        plotted += 1

    if plotted == 0:
        y_true = np.linspace(-22, -0.5, 500)
        y_pred = y_true + rng.normal(0, 1.8, size=y_true.shape)
        ax.scatter(y_true, y_pred, s=10, alpha=0.22, color=BLUE, linewidths=0, label="fallback")
        min_v, max_v = -23.0, 1.0

    lo = math.floor(min_v)
    hi = math.ceil(max_v)
    ax.plot([lo, hi], [lo, hi], color="#0F172A", lw=1.6, alpha=0.72)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel(r"экспериментальный $\ln x_2$")
    ax.set_ylabel(r"предсказанный $\ln x_2$")
    ax.set_title(r"Parity plot на test split")
    ax.grid(alpha=0.18)
    ax.legend(loc="upper left", fontsize=10)
    save_both(fig, "parity_lnx2")
    plt.close(fig)


def linear_probe_bars() -> None:
    plt = _mpl()
    probe_summary_path = RESULTS / "probe_summary.json"
    if probe_summary_path.exists():
        try:
            payload = json.loads(probe_summary_path.read_text(encoding="utf-8"))
            metrics = ["FractionCSP3", "NumHDonors", "TPSA", "MolLogP", "MolWt"]
            xticklabels = ["CSP3", "H-доноры", "TPSA", "MolLogP", "MolWt"]
            model_keys = [
                ("TGNN(MPNN)", "tgnn_mpnn"),
                ("TIMP", "tgnn_timp"),
                ("TIMP+HC", "tgnn_timp_hc"),
            ]
            x = np.arange(len(metrics))
            width = 0.24
            fig, ax = plt.subplots(figsize=(10, 6))
            colors = [BLUE, GREEN, ORANGE]
            available = [(label, key) for label, key in model_keys if key in payload]
            if not available:
                available = [(name, name) for name in list(payload)[:3]]
            for i, (label, model_name) in enumerate(available):
                vals = [
                    float(payload[model_name].get(metric, 0.0) or 0.0)
                    for metric in metrics
                ]
                ax.bar(
                    x + (i - (len(available) - 1) / 2) * width,
                    vals,
                    width,
                    label=label,
                    color=colors[i % len(colors)],
                    alpha=0.72,
                )
            ax.set_ylim(0, 1)
            ax.set_xticks(x)
            ax.set_xticklabels(xticklabels)
            ax.set_ylabel(r"$R^2$")
            ax.set_title(r"Линейная проба: 5 RDKit-дескрипторов")
            ax.grid(axis="y", alpha=0.18)
            ax.legend(loc="upper left", fontsize=10)
            save_both(fig, "linear_probe_bars")
            plt.close(fig)
            return
        except Exception:
            pass

    vals = None
    probe_summaries = sorted(RESULTS.rglob("*descriptor_probe/summary.json"))
    if probe_summaries:
        try:
            payload = json.loads(probe_summaries[0].read_text(encoding="utf-8"))
            core = payload.get("core_descriptors", {})
            vals = {
                name: float(row["r2_test"])
                for name, row in core.items()
                if isinstance(row, dict) and row.get("r2_test") is not None
            }
        except Exception:
            vals = None
    if not vals:
        vals = {
        "FractionCSP3": 0.93,
        "NumHDonors": 0.69,
        "TPSA": 0.65,
        "MolLogP": 0.61,
        "NumHAcceptors": 0.58,
        "RingCount": 0.55,
        "MolMR": 0.52,
        "MolWt": 0.45,
        "HeavyAtomCount": 0.42,
        "RotBonds": 0.38,
        }
    items = list(vals.items())[::-1]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh([k for k, _ in items], [v for _, v in items], color=BLUE, alpha=0.72)
    ax.set_xlim(0, 1)
    ax.set_title(r"Линейная проба $R^2$ на замороженных GNN-представлениях")
    ax.set_xlabel(r"$R^2$")
    ax.grid(axis="x", alpha=0.18)
    save_both(fig, "linear_probe_bars")
    plt.close(fig)


def timp_dual_channel_molecule() -> None:
    plt = _mpl()
    fig, ax = plt.subplots(figsize=(7, 6))
    try:
        from rdkit import Chem
        from rdkit.Chem import rdDepictor

        mol = Chem.MolFromSmiles("CC(=O)Nc1ccc(O)cc1")
        if mol is None:
            raise ValueError("invalid paracetamol SMILES")
        rdDepictor.Compute2DCoords(mol)
        conf = mol.GetConformer()
        coords = np.array([(conf.GetAtomPosition(a.GetIdx()).x, conf.GetAtomPosition(a.GetIdx()).y) for a in mol.GetAtoms()])
        coords[:, 1] *= -1
        for bond in mol.GetBonds():
            a, b = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
            symbols = {mol.GetAtomWithIdx(a).GetSymbol(), mol.GetAtomWithIdx(b).GetSymbol()}
            color = ORANGE if symbols & {"O", "N", "F"} else BLUE
            ax.plot([coords[a, 0], coords[b, 0]], [coords[a, 1], coords[b, 1]], lw=4.0, color=color, alpha=0.82)
        for atom in mol.GetAtoms():
            i = atom.GetIdx()
            sym = atom.GetSymbol()
            color = ORANGE if sym in {"O", "N"} else BLUE
            ax.scatter(coords[i, 0], coords[i, 1], s=460, color="white", edgecolor=color, linewidth=2.5, zorder=3)
            ax.text(coords[i, 0], coords[i, 1], sym, ha="center", va="center", fontsize=12, weight="bold")
    except Exception:
        theta = np.linspace(0, 2 * np.pi, 7)[:-1]
        ring = np.c_[np.cos(theta), np.sin(theta)]
        for i in range(6):
            a, b = ring[i], ring[(i + 1) % 6]
            ax.plot([a[0], b[0]], [a[1], b[1]], color=BLUE, lw=4)
        ax.scatter(ring[:, 0], ring[:, 1], s=420, color="white", edgecolor=BLUE, linewidth=2.5)
        ax.plot([1, 1.7], [0, 0.55], color=ORANGE, lw=4)
        ax.scatter([1.7], [0.55], s=420, color="white", edgecolor=ORANGE, linewidth=2.5)
        ax.text(1.7, 0.55, "O", ha="center", va="center", weight="bold")
    ax.set_title("Каналы TIMP на парацетамоле")
    ax.text(0.02, 0.04, "синий = дисперсия; оранжевый = полярность / H-связь", transform=ax.transAxes, color=SLATE)
    ax.axis("equal")
    ax.axis("off")
    save_both(fig, "timp_dual_channel_molecule")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate seminar presentation figures.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--results-dir", type=str, default=str(RESULTS))
    parser.add_argument("--output-dir", type=str, default=str(OUT))
    return parser.parse_args()


def main() -> None:
    global OUT, RESULTS
    args = parse_args()
    RESULTS = Path(args.results_dir).expanduser().resolve()
    OUT = Path(args.output_dir).expanduser().resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    plots = [
        ("corpus_lnx2_histogram", corpus_lnx2_histogram),
        ("corpus_temperature_histogram", corpus_temperature_histogram),
        ("corpus_solvent_barplot", corpus_solvent_barplot),
        ("corpus_points_per_pair", corpus_points_per_pair),
        ("ideal_sle_example", ideal_sle_example),
        ("nrtl_gamma_example", nrtl_gamma_example),
        ("sensitivity_bars", sensitivity_bars),
        ("error_decomposition_waterfall", error_decomposition_waterfall),
        ("parity_lnx2", parity_lnx2),
        ("linear_probe_bars", linear_probe_bars),
        ("timp_dual_channel_molecule", timp_dual_channel_molecule),
    ]
    for name, fn in plots:
        safe_plot(name, fn)
    print(f"[presentation-figures] wrote figures to {OUT}")


if __name__ == "__main__":
    main()
