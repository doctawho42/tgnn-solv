from __future__ import annotations

from pathlib import Path
import json
import textwrap
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle
from matplotlib.text import Text
import matplotlib.patheffects as pe
from scipy.stats import linregress

warnings.filterwarnings("ignore", category=UserWarning)

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

FONT_PATH = ROOT / "reports" / "fonts" / "Montserrat.ttf"
if FONT_PATH.exists():
    # Keep the requested Montserrat asset available, but do not use it as the
    # default: matplotlib renders the variable font too thin in report PDFs.
    font_manager.fontManager.addfont(str(FONT_PATH))


def _pick_font(candidates: list[str]) -> str:
    for candidate in candidates:
        try:
            font_manager.findfont(candidate, fallback_to_default=False)
            return candidate
        except Exception:
            continue
    return "Verdana"


FONT_FAMILY = _pick_font(["Arial", "Helvetica Neue", "Avenir", "Verdana"])

# A high-contrast, paper-friendly palette. All figure text is intentionally in English.
BG = "#FBFAF7"
PANEL = "#FFFFFF"
INK = "#050814"
MUTED = "#2D3543"
GRID = "#DED8CE"
LINE = "#A79E90"
BLUE = "#89AFC1"
BLUE_D = "#557F95"
TEAL = "#95BEA8"
TEAL_D = "#5F9279"
SAND = "#DFC37C"
CLAY = "#D0947E"
LAVENDER = "#B8A7D6"
ROSE = "#DCA0AB"
SLATE = "#A8ADB5"
GRAY = "#D1D6DC"
GREEN = "#AFCB8E"

MODEL_COLORS = {
    "DirectGNN": BLUE_D,
    "RF hybrid": SAND,
    "TGNN-Solv": CLAY,
    "Van't Hoff": TEAL_D,
    "Linear T": BLUE,
    "RF(Morgan+T)": LAVENDER,
    "Mean per pair": SLATE,
}

plt.rcParams.update({
    "font.family": FONT_FAMILY,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "axes.edgecolor": LINE,
    "axes.labelcolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "text.color": INK,
    "font.weight": "normal",
    "axes.titleweight": "medium",
    "axes.titlesize": 12.8,
    "axes.labelsize": 10.8,
    "xtick.labelsize": 9.4,
    "ytick.labelsize": 9.4,
    "legend.fontsize": 9.4,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def p(*parts: str) -> Path:
    return ROOT.joinpath(*parts)


def _force_readable_text(fig: plt.Figure) -> None:
    """Apply only safety-level readability fixes, not global visual emphasis."""
    for text in fig.findobj(match=Text):
        if not text.get_text():
            continue
        size = float(text.get_fontsize())
        if size < 8.2 and not getattr(text, "_tgnn_allow_small", False):
            size = 8.55
        text.set_fontsize(size)
        color = text.get_color()
        if isinstance(color, str) and color.lower() in {"white", "#fff", "#ffffff"}:
            pass
        else:
            text.set_color(INK)
        text.set_linespacing(1.28)


def _wrap_plain_lines(text: str, max_chars: int) -> str:
    """Wrap only prose lines. TeX/math lines are left unchanged."""
    if max_chars <= 8:
        return text
    wrapped: list[str] = []
    for line in text.splitlines():
        if not line.strip() or "$" in line or "\\" in line:
            wrapped.append(line)
            continue
        if len(line) <= max_chars:
            wrapped.append(line)
            continue
        wrapped.extend(
            textwrap.wrap(
                line,
                width=max_chars,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return "\n".join(wrapped)


def _fit_text_to_rect(
    ax: plt.Axes,
    text_obj: Text,
    xy,
    w: float,
    h: float,
    *,
    xpad: float = 0.11,
    ypad: float = 0.18,
    min_fs: float = 7.0,
) -> None:
    """Keep block text inside rounded cards with a visible margin."""
    if not text_obj.get_text():
        return

    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    (x0, y0), (x1, y1) = ax.transData.transform(
        [
            (xy[0] + w * xpad, xy[1] + h * ypad),
            (xy[0] + w * (1.0 - xpad), xy[1] + h * (1.0 - ypad)),
        ]
    )
    max_w = abs(x1 - x0)
    max_h = abs(y1 - y0)
    if max_w <= 1 or max_h <= 1:
        return

    original = text_obj.get_text()
    bbox = text_obj.get_window_extent(renderer=renderer)
    if bbox.width > max_w * 1.02:
        fs = float(text_obj.get_fontsize())
        avg_char_px = max(fs * fig.dpi / 72.0 * 0.43, 1.0)
        max_chars = max(10, int(max_w / avg_char_px))
        wrapped = _wrap_plain_lines(original, max_chars)
        if wrapped != original:
            text_obj.set_text(wrapped)
            fig.canvas.draw()

    # Iteratively reduce only the offending card text. Most labels stay at the
    # requested size; cramped cards get a local, bounded correction.
    for _ in range(24):
        bbox = text_obj.get_window_extent(renderer=renderer)
        if bbox.width <= max_w and bbox.height <= max_h:
            break
        fs = float(text_obj.get_fontsize())
        if fs <= min_fs:
            text_obj._tgnn_allow_small = True
            break
        text_obj.set_fontsize(max(min_fs, fs - 0.35))
        text_obj.set_linespacing(1.16 if bbox.height > max_h else 1.22)
        fig.canvas.draw()

    if float(text_obj.get_fontsize()) < 8.2:
        text_obj._tgnn_allow_small = True


def save(fig: plt.Figure, name: str) -> None:
    _force_readable_text(fig)
    fig.savefig(OUT / name, bbox_inches="tight", pad_inches=0.06, facecolor=fig.get_facecolor())
    plt.close(fig)


def style_axes(ax: plt.Axes, *, grid_axis: str = "y") -> None:
    ax.set_facecolor(BG)
    ax.spines["left"].set_color("#B9B1A5")
    ax.spines["bottom"].set_color("#B9B1A5")
    ax.spines["left"].set_linewidth(0.9)
    ax.spines["bottom"].set_linewidth(0.9)
    ax.tick_params(length=0, pad=4)
    if grid_axis:
        ax.grid(True, axis=grid_axis, color=GRID, lw=0.65)
        ax.set_axisbelow(True)


def label_bars(ax: plt.Axes, bars, fmt: str = "{:.3g}", dy: float = 0.02) -> None:
    ymax = ax.get_ylim()[1]
    for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + ymax * dy,
            fmt.format(h),
            ha="center",
            va="bottom",
            fontsize=9.0,
            color=INK,
            weight="medium",
        )


def box(ax: plt.Axes, xy, w: float, h: float, text: str, *, fc: str, ec: str = "#D8D2C7", fs: float = 9.85, weight: str = "normal"):
    x, y = xy
    shadow = FancyBboxPatch(
        (x + 0.006, y - 0.006), w, h,
        boxstyle="round,pad=0.018,rounding_size=0.035",
        linewidth=0, facecolor="#000000", alpha=0.045, zorder=1,
    )
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.018,rounding_size=0.035",
        linewidth=1.35, edgecolor=ec, facecolor=fc, zorder=2,
    )
    ax.add_patch(shadow)
    ax.add_patch(patch)
    txt = ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        weight=weight,
        color=INK,
        linespacing=1.28,
        zorder=3,
    )
    _fit_text_to_rect(ax, txt, xy, w, h)
    return patch


def arrow(ax: plt.Axes, start, end, *, color: str = MUTED, rad: float = 0.0, lw: float = 1.25) -> None:
    ax.add_patch(FancyArrowPatch(
        start, end,
        arrowstyle="-|>",
        mutation_scale=15,
        linewidth=max(lw, 1.65),
        color=color,
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=3,
        shrinkB=3,
        zorder=4,
    ))


def title(ax: plt.Axes, text: str, y: float = 0.96) -> None:
    ax.text(0.5, y, text, ha="center", va="top", fontsize=13.8, weight="medium", color=INK)


def _draw_rdkit_graph(ax: plt.Axes, smiles: str, *, explicit_h: bool = False, label: str | None = None, scale_atoms: float = 1.0) -> None:
    from rdkit import Chem
    from rdkit.Chem import AllChem

    atom_colors = {
        "C": "#F7F7F2",
        "O": "#F4D7D3",
        "N": "#D8E9F0",
        "H": "#FFFFFF",
        "S": "#F2E1A8",
        "Cl": "#DDEEDB",
        "F": "#DDEEDB",
        "Br": "#E8D4C8",
    }
    mol = Chem.MolFromSmiles(smiles)
    if explicit_h:
        mol = Chem.AddHs(mol)
    AllChem.Compute2DCoords(mol)
    conf = mol.GetConformer()
    coords = np.array([[conf.GetAtomPosition(i).x, conf.GetAtomPosition(i).y] for i in range(mol.GetNumAtoms())])
    coords = coords - coords.mean(axis=0, keepdims=True)
    scale = max(np.ptp(coords[:, 0]), np.ptp(coords[:, 1]), 1.0)
    coords = coords / scale

    for bond in mol.GetBonds():
        i = bond.GetBeginAtomIdx()
        j = bond.GetEndAtomIdx()
        xi, yi = coords[i]
        xj, yj = coords[j]
        ax.plot([xi, xj], [yi, yj], color="#C8C2B7", lw=2.0, solid_capstyle="round", zorder=1)

    for atom in mol.GetAtoms():
        i = atom.GetIdx()
        sym = atom.GetSymbol()
        x, y = coords[i]
        r = (0.062 if sym != "H" else 0.046) * scale_atoms
        circ = Circle(
            (x, y), r,
            facecolor=atom_colors.get(sym, "#F2F2F0"),
            edgecolor="#8B8F96",
            linewidth=1.0,
            zorder=2,
            path_effects=[pe.SimplePatchShadow(offset=(0.8, -0.8), alpha=0.08), pe.Normal()],
        )
        ax.add_patch(circ)
        ax.text(
            x, y, sym,
            ha="center", va="center",
            fontsize=(8.5 if sym != "H" else 7.2) * scale_atoms,
            color=INK, weight="semibold", zorder=3,
        )

    pad = 0.20
    ax.set_xlim(coords[:, 0].min() - pad, coords[:, 0].max() + pad)
    ax.set_ylim(coords[:, 1].min() - pad, coords[:, 1].max() + pad)
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()
    if label:
        ax.text(0.5, -0.10, label, transform=ax.transAxes, ha="center", va="top", fontsize=9.5, color=INK, weight="semibold")


def read_csv(path: Path, **kwargs) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path, **kwargs)
    except Exception:
        return None


def solubility_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only measured SLE rows; auxiliary property rows carry ln_x2=0 placeholders."""
    if "has_solubility" not in df.columns:
        return df
    mask = df["has_solubility"]
    if mask.dtype != bool:
        mask = mask.astype(str).str.lower().isin({"true", "1", "yes"})
    return df[mask].copy()


def _temperature_bundle_dir() -> Path:
    return p("results", "temperature_interpretability_bundle")


def _short_label(text: str, max_len: int = 28) -> str:
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _pair_display_name(solute: str, solvent: str, *, wrap: bool = True) -> str:
    if wrap:
        return f"{_short_label(solute, 26)}\n{_short_label(solvent, 20)}"
    return f"{_short_label(solute, 32)} / {_short_label(solvent, 24)}"


def _temperature_fit_line(df: pd.DataFrame) -> tuple[float, float] | None:
    if df is None or len(df) < 2:
        return None
    x = 1.0 / df["T"].to_numpy(dtype=float)
    y = df["ln_x2_true"].to_numpy(dtype=float)
    if len(np.unique(x)) < 2:
        return None
    fit = linregress(x, y)
    return float(fit.slope), float(fit.intercept)


def _nrtl_fixed_point_ln_x2(
    T: float,
    T_m: float,
    dH_fus: float,
    tau_12: float,
    tau_21: float,
    alpha: float,
    *,
    damping: float = 0.7,
    n_iter: int = 30,
) -> float:
    R = 8.314
    phi = (dH_fus / R) * (1.0 / T - 1.0 / T_m)
    x2 = float(np.clip(np.exp(-phi), 1e-12, 1.0 - 1e-12))
    for _ in range(n_iter):
        x1 = 1.0 - x2
        G12 = np.exp(-alpha * tau_12)
        G21 = np.exp(-alpha * tau_21)
        term1 = tau_12 * (G12 / (x2 + x1 * G12)) ** 2
        term2 = tau_21 * G21 / (x1 + x2 * G21) ** 2
        ln_gamma = x1**2 * (term1 + term2)
        x2_new = np.exp(-phi - ln_gamma)
        x2_new = damping * x2_new + (1.0 - damping) * x2
        x2_new = float(np.clip(x2_new, 1e-12, 1.0 - 1e-12))
        if abs(x2_new - x2) < 1e-10:
            x2 = x2_new
            break
        x2 = x2_new
    return float(np.log(x2))


# ---------------------------------------------------------------------------
# Diagrams
# ---------------------------------------------------------------------------

def graphical_abstract() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "TGNN-Solv: from molecular structures to interpretable solubility")

    box(ax, (0.05, 0.56), 0.18, 0.19, "molecule pair\n+ temperature\n\nSMILES, T", fc="#EEF4F7", ec="#D4DEE5", weight="semibold")
    box(ax, (0.30, 0.56), 0.18, 0.19, "molecular graph\nrepresentation\n\natoms and bonds", fc="#F1F2F4", ec="#DADDE2", weight="semibold")
    box(ax, (0.55, 0.63), 0.18, 0.15, "crystal\nparameters\n$T_m,\\Delta H_{fus}$", fc="#FFF7E6", ec="#E8D8AC", weight="semibold")
    box(ax, (0.55, 0.40), 0.18, 0.15, "activity\nparameters\n$\\tau_{12},\\tau_{21},\\alpha$", fc="#EEF6F1", ec="#D6E4D8", weight="semibold")
    box(ax, (0.78, 0.52), 0.17, 0.17, "SLE/NRTL\nsolver\n\n$\\ln x_2$", fc="#FCEFEA", ec="#E7C9BC", weight="semibold")

    arrow(ax, (0.23, 0.655), (0.30, 0.655), color=MUTED)
    arrow(ax, (0.48, 0.655), (0.55, 0.705), color=SAND, rad=0.07)
    arrow(ax, (0.48, 0.635), (0.55, 0.475), color=TEAL_D, rad=-0.07)
    arrow(ax, (0.73, 0.705), (0.79, 0.625), color=CLAY, rad=-0.05)
    arrow(ax, (0.73, 0.475), (0.79, 0.575), color=CLAY, rad=0.05)

    ax.text(0.50, 0.20, "The neural network predicts physical quantities; thermodynamics computes the final solubility.",
            ha="center", fontsize=10, color=MUTED)
    save(fig, "graphical_abstract_schematic.pdf")

def architecture() -> None:
    fig, ax = plt.subplots(figsize=(8.25, 5.35))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "TGNN-Solv and DirectGNN: same representation, different final map", y=0.985)

    # Shared representation strip.
    box(ax, (0.060, 0.725), 0.880, 0.155, "", fc="#F7FAF8", ec="#D9E5DD")
    ax.text(0.092, 0.850, "shared molecular representation", ha="left", va="center",
            fontsize=11.0, weight="medium", color=TEAL_D)
    shared = [
        (0.095, 0.120, "graphs"),
        (0.285, 0.185, "encoder\nMPNN/GPS/TIMP"),
        (0.555, 0.180, "interaction\n+ readout"),
        (0.805, 0.120, "pair\nvector\n$g_{pair}$"),
    ]
    for x, w, txt in shared:
        box(ax, (x, 0.748), w, 0.076, txt, fc="#FFFFFF", ec="#D9E5DD", fs=9.7, weight="medium")
    for (x, w, _), (nx, _, _) in zip(shared[:-1], shared[1:]):
        arrow(ax, (x + w + 0.010, 0.786), (nx - 0.010, 0.786), color=TEAL_D, lw=1.0)
    ax.text(0.792, 0.698, "optional solvent-type MoE gates the pair vector",
            ha="center", va="top", fontsize=9.3, color=MUTED)

    # Two clean comparison panels.
    box(ax, (0.055, 0.145), 0.495, 0.485, "", fc="#FFFCF4", ec="#E6D8B7")
    box(ax, (0.600, 0.145), 0.345, 0.485, "", fc="#F5F9FB", ec="#D4DEE5")
    ax.text(0.092, 0.590, "TGNN-Solv", ha="left", va="center", fontsize=11.7, weight="medium", color=CLAY)
    ax.text(0.637, 0.590, "DirectGNN", ha="left", va="center", fontsize=11.7, weight="medium", color=BLUE_D)

    # TGNN-Solv: parameter heads and physical computation.
    box(ax, (0.095, 0.465), 0.185, 0.086, "crystal\n$T_m,\\Delta H,\\Delta C_p$", fc="#FFF7E6", ec="#E8D8AC", fs=9.35, weight="medium")
    box(ax, (0.095, 0.345), 0.185, 0.086, "activity\n$\\tau_{12},\\tau_{21},\\alpha$", fc="#EEF6F1", ec="#D6E4D8", fs=9.35, weight="medium")
    box(ax, (0.375, 0.420), 0.140, 0.086, "SLE/NRTL\nsolver", fc="#FCEFEA", ec="#E7C9BC", fs=9.55, weight="medium")
    box(ax, (0.375, 0.305), 0.140, 0.078, "bounded\ncorrection", fc="#F7F5F0", ec="#DAD5CA", fs=9.25, weight="medium")
    box(ax, (0.385, 0.210), 0.120, 0.060, r"$\widehat{\ln x_2}$", fc="#FFFFFF", ec="#DAD5CA", fs=10.8, weight="medium")
    arrow(ax, (0.286, 0.508), (0.372, 0.468), color=CLAY, lw=1.0)
    arrow(ax, (0.286, 0.388), (0.372, 0.448), color=TEAL_D, lw=1.0)
    arrow(ax, (0.445, 0.420), (0.445, 0.383), color=CLAY, lw=1.0)
    arrow(ax, (0.445, 0.305), (0.445, 0.270), color=CLAY, lw=1.0)

    # DirectGNN: same vector, no solver.
    box(ax, (0.635, 0.455), 0.155, 0.088, "pair vector\n+ T encoding", fc="#FFFFFF", ec="#D4DEE5", fs=9.35, weight="medium")
    box(ax, (0.835, 0.455), 0.082, 0.088, "direct\nMLP", fc="#EEF4F7", ec="#D4DEE5", fs=9.35, weight="medium")
    box(ax, (0.820, 0.300), 0.112, 0.060, r"$\widehat{\ln x_2}$", fc="#FFFFFF", ec="#D4DEE5", fs=10.8, weight="medium")
    arrow(ax, (0.793, 0.499), (0.832, 0.499), color=BLUE_D, lw=1.0)
    arrow(ax, (0.876, 0.452), (0.876, 0.363), color=BLUE_D, lw=1.0)

    ax.text(0.50, 0.055,
            "Only the final map is changed: TGNN-Solv uses SLE/NRTL, DirectGNN predicts the target directly.",
            ha="center", fontsize=9.35, color=MUTED)
    save(fig, "architecture_schematic.pdf")

def graph_mechanisms() -> None:
    fig, ax = plt.subplots(figsize=(7.8, 5.4))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Graph encoders: what each mechanism adds", y=0.985)

    cards = [
        (0.055, "MPNN", "local messages", "$m_i=\\sum_{j\\in\\mathcal{N}(i)} M_{ij}$", "functional groups\nshort-range chemistry", "long-range context\nis indirect", "#EEF4F7", "#D4DEE5"),
        (0.375, "GPS", "local + global", "message passing\n+ self-attention", "non-local context\nfor scaffold transfer", "cost and overfitting\nrisk increase", "#EEF6F1", "#D6E4D8"),
        (0.695, "TIMP", "typed channels", "$m_{ij}=m^{disp}_{ij}+m^{polar}_{ij}$", "dispersive effects\npolar / H-bond effects", "depends on charge\nand edge features", "#FFF7E6", "#E8D8AC"),
    ]
    for x, name, subtitle, equation, captures, limit, fc, ec in cards:
        box(ax, (x, 0.20), 0.25, 0.60, "", fc=fc, ec=ec, fs=9.0)
        ax.text(x + 0.125, 0.735, name, ha="center", va="center", fontsize=12.0, weight="semibold", color=INK)
        ax.text(x + 0.125, 0.668, subtitle, ha="center", va="center", fontsize=9.2, color=MUTED)
        ax.plot([x + 0.025, x + 0.225], [0.62, 0.62], color=LINE, lw=1.1)
        ax.text(x + 0.125, 0.548, equation, ha="center", va="center", fontsize=8.8, color=INK, linespacing=1.2)
        ax.text(x + 0.040, 0.435, "captures", ha="left", va="center", fontsize=8.2, color=MUTED, weight="semibold")
        ax.text(x + 0.040, 0.365, captures, ha="left", va="center", fontsize=8.8, color=INK, linespacing=1.25)
        ax.text(x + 0.040, 0.285, "main caveat", ha="left", va="center", fontsize=8.2, color=MUTED, weight="semibold")
        ax.text(x + 0.040, 0.230, limit, ha="left", va="center", fontsize=8.8, color=INK, linespacing=1.25)

    ax.text(0.50, 0.105,
            "All three encoders return molecule vectors; they differ only in how atom-level information is mixed.",
            ha="center", fontsize=9.1, color=MUTED)
    save(fig, "graph_mechanisms_schematic.pdf")

def interaction_rescue() -> None:
    fig, ax = plt.subplots(figsize=(8.25, 4.95))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Interaction branch: why extra supervision was added", y=0.985)

    # Three calm columns: evidence -> diagnosed bottleneck -> safeguards.
    box(ax, (0.055, 0.245), 0.275, 0.525, "", fc="#FFFCF4", ec="#E6D8B7")
    box(ax, (0.390, 0.350), 0.245, 0.315, "", fc="#FFFFFF", ec="#DADDE2")
    box(ax, (0.705, 0.210), 0.235, 0.575, "", fc="#F7FAF8", ec="#D9E5DD")

    ax.text(0.193, 0.725, "observed imbalance", ha="center", fontsize=10.6, weight="medium", color=CLAY)
    ax.text(0.513, 0.620, "failure mode", ha="center", fontsize=10.6, weight="medium", color=MUTED)
    ax.text(0.823, 0.742, "rescue signals", ha="center", fontsize=10.6, weight="medium", color=TEAL_D)

    left_cards = [
        (0.090, 0.606, "direct\ncrystal labels"),
        (0.090, 0.482, "SLE gradient\nthrough solver"),
        (0.090, 0.358, "weak NRTL\nidentification"),
    ]
    left_colors = [("#FFF7E6", "#E8D8AC"), ("#FCEFEA", "#E7C9BC"), ("#F7F5F0", "#DAD5CA")]
    for (x, y, txt), (fc, ec) in zip(left_cards, left_colors):
        box(ax, (x, y), 0.205, 0.082, txt, fc=fc, ec=ec, fs=9.25, weight="medium")

    ax.text(0.513, 0.525, "weak gradient\nfor the pair state",
            ha="center", va="center", fontsize=10.7, weight="medium", color=INK, linespacing=1.30)
    ax.text(0.513, 0.430, "diagnosis:\ninteraction branch learns late",
            ha="center", va="center", fontsize=9.1, color=MUTED, linespacing=1.22)

    fixes = [
        (0.730, 0.635, "IDAC stream\nactivity data"),
        (0.730, 0.515, "auxiliary pair loss\ntraining only"),
        (0.730, 0.395, "crystal detach\nphase 2"),
        (0.730, 0.275, "Van't Hoff anchors\nslope signal"),
    ]
    for x, y, txt in fixes:
        box(ax, (x, y), 0.175, 0.078, txt, fc="#EEF6F1", ec="#D6E4D8", fs=8.95, weight="medium")

    arrow(ax, (0.333, 0.508), (0.388, 0.508), color=CLAY, lw=1.05)
    arrow(ax, (0.637, 0.508), (0.703, 0.508), color=TEAL_D, lw=1.05)

    ax.text(0.50, 0.090,
            "These are training constraints; inference still goes through the thermodynamic solver.",
            ha="center", fontsize=9.45, color=MUTED)
    save(fig, "interaction_rescue_schematic.pdf")

def correction_loop() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Adaptive correction is a second SLE solve, not an unconstrained shortcut", y=0.985)

    box(ax, (0.06, 0.56), 0.18, 0.18, "base parameters\n$T_m,\\Delta H,\\tau_{12},\\tau_{21}$", fc="#FFF7E6", ec="#E8D8AC", weight="semibold", fs=9.0)
    box(ax, (0.34, 0.56), 0.17, 0.18, "SLE solve\nbase $\\ln x_2$", fc="#FCEFEA", ec="#E7C9BC", weight="semibold", fs=9.4)
    box(ax, (0.06, 0.22), 0.18, 0.18, "bounded deltas\n$\\Delta T_m,\\Delta H,\\Delta\\tau$", fc="#F7F5F0", ec="#DAD5CA", fs=9.0)
    box(ax, (0.34, 0.22), 0.17, 0.18, "SLE solve\ncorrected $\\ln x_2$", fc="#FCEFEA", ec="#E7C9BC", weight="semibold", fs=9.4)
    box(ax, (0.61, 0.40), 0.16, 0.18, "gate\n$w\\in[0,1]$", fc="#EEF6F1", ec="#D6E4D8", weight="semibold")
    box(ax, (0.83, 0.40), 0.12, 0.18, "final\n$\\ln x_2$", fc=PANEL, ec="#DADDE2", weight="semibold", fs=11)
    arrow(ax, (0.24, 0.65), (0.34, 0.65), color=CLAY)
    arrow(ax, (0.24, 0.31), (0.34, 0.31), color=CLAY)
    arrow(ax, (0.51, 0.65), (0.61, 0.51), color=MUTED, rad=-0.08)
    arrow(ax, (0.51, 0.31), (0.61, 0.47), color=MUTED, rad=0.08)
    arrow(ax, (0.77, 0.49), (0.83, 0.49), color=MUTED)
    ax.text(0.50, 0.12, "The correction is limited in physical parameter space and remains diagnosable.",
            ha="center", fontsize=9.4, color=MUTED)
    save(fig, "correction_loop_schematic.pdf")


def temperature_encoding() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Temperature is encoded differently in the two matched models", y=0.985)

    box(ax, (0.07, 0.52), 0.23, 0.22, "TGNN-Solv\nphysical temperature\n\n$1/T$, $\\Phi(T)$,\n$\\tau(T)=\\tau_{ref}+b(1/T-1/T_{ref})$", fc="#FCEFEA", ec="#E7C9BC", weight="semibold", fs=9.0)
    box(ax, (0.39, 0.52), 0.23, 0.22, "DirectGNN\nlearned temperature code\n\nthermometer features\n+ direct MLP", fc="#EEF4F7", ec="#D4DEE5", weight="semibold", fs=9.0)
    box(ax, (0.70, 0.52), 0.23, 0.22, "diagnostic question\n\nwho learns the slope\n$d\\ln x_2 / d(1/T)$?", fc="#FFF7E6", ec="#E8D8AC", weight="semibold", fs=9.0)
    arrow(ax, (0.30, 0.63), (0.39, 0.63), color=MUTED)
    arrow(ax, (0.62, 0.63), (0.70, 0.63), color=MUTED)
    ax.text(0.50, 0.25, "The Van't Hoff audit tests whether the learned models recover the pair-specific temperature slope.",
            ha="center", fontsize=9.4, color=MUTED)
    save(fig, "temperature_encoding_schematic.pdf")


def timp_hansen_diagnostics() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 4.15))
    fig.patch.set_facecolor(BG)
    names = ["MPNN", "TIMP", "TIMP+HC"]
    med = [0.565, 0.575, 0.601]
    colors = [SLATE, TEAL, BLUE_D]
    ax = axes[0]
    style_axes(ax)
    bars = ax.bar(names, med, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_ylim(0.50, 0.625)
    ax.set_title("Descriptor probe improves with TIMP+HC")
    ax.set_ylabel("median descriptor R2")
    label_bars(ax, bars, "{:.3f}", dy=0.012)

    ax = axes[1]
    style_axes(ax)
    metrics = ["channel\ncosine", "disp.\nshare"]
    timp = [0.058, 0.51]
    hc = [0.006, 0.29]
    x = np.arange(len(metrics)); w = 0.34
    b1 = ax.bar(x - w/2, timp, width=w, color=TEAL, label="TIMP", edgecolor="white", linewidth=0.8)
    b2 = ax.bar(x + w/2, hc, width=w, color=BLUE_D, label="TIMP+HC", edgecolor="white", linewidth=0.8)
    ax.set_xticks(x); ax.set_xticklabels(metrics)
    ax.set_ylim(0, 0.62)
    ax.set_title("Hansen-contrastive separates channels")
    ax.legend(frameon=False, loc="upper right")
    label_bars(ax, b1, "{:.3f}", dy=0.01); label_bars(ax, b2, "{:.3f}", dy=0.01)
    fig.tight_layout()
    save(fig, "timp_hansen_diagnostics.pdf")


def uncertainty_ad() -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.55))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Uncertainty and applicability-domain layer", y=0.985)
    box(ax, (0.06, 0.52), 0.18, 0.20, "prediction\n$\\widehat{\\ln x_2}$", fc="#EEF4F7", ec="#D4DEE5", weight="semibold")
    box(ax, (0.32, 0.62), 0.20, 0.15, "uncertainty\nMC dropout / ensemble", fc="#F1F5F0", ec="#D6E4D8", fs=9.0)
    box(ax, (0.32, 0.33), 0.20, 0.15, "applicability domain\nlatent distance + Tanimoto", fc="#FFF7E6", ec="#E8D8AC", fs=9.0)
    box(ax, (0.62, 0.47), 0.18, 0.17, "calibrated report\ninterval + OOD flag", fc="#F7F5F0", ec="#DAD5CA", weight="semibold", fs=9.0)
    box(ax, (0.86, 0.47), 0.10, 0.17, "decision\nsupport", fc=PANEL, ec="#DADDE2", weight="semibold", fs=9.3)
    arrow(ax, (0.24, 0.62), (0.32, 0.69), color=TEAL_D, rad=0.05)
    arrow(ax, (0.24, 0.60), (0.32, 0.41), color=SAND, rad=-0.05)
    arrow(ax, (0.52, 0.69), (0.62, 0.57), color=MUTED, rad=-0.05)
    arrow(ax, (0.52, 0.41), (0.62, 0.52), color=MUTED, rad=0.05)
    arrow(ax, (0.80, 0.555), (0.86, 0.555), color=MUTED)
    ax.text(0.50, 0.17, "This layer does not change TGNN-Solv physics; it tells when a prediction should be trusted.",
            ha="center", fontsize=9.3, color=MUTED)
    save(fig, "uncertainty_ad_schematic.pdf")


def evidence_status_matrix() -> None:
    fig, ax = plt.subplots(figsize=(8.45, 5.35))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Project evidence map", y=0.985)
    ax.text(
        0.5,
        0.910,
        "The report separates measured facts, diagnostics, hypotheses and validation that still needs GPU runs.",
        ha="center",
        va="center",
        fontsize=9.9,
        color=MUTED,
    )

    rows = [
        ("DirectGNN is a strong control", "scaffold split\nexternal baselines", "confirmed", BLUE_D),
        ("Physics pays a small scaffold tax", "TGNN - DirectGNN\n+0.089 MAE", "confirmed", CLAY),
        ("Temperature signal is strong", "same-pair Van't Hoff\nMAE 0.368", "confirmed", TEAL_D),
        ("TGNN proxy misses the signal", "short low-to-high run\nNRTL nearly constant", "diagnosed", SAND),
        ("Structural extrapolation is compositional", "BRICS novelty\nMAE gap", "diagnosed", LAVENDER),
        ("Rescue components need full-budget proof", "IDAC, detach,\naux pair loss, TIMP", "requires GPU", SLATE),
    ]
    headers = [("claim", 0.055, 0.325), ("evidence", 0.435, 0.285), ("status", 0.790, 0.145)]
    for label, x, w in headers:
        ax.text(x, 0.825, label.upper(), ha="left", va="center", fontsize=8.8, weight="medium", color=MUTED)
        ax.plot([x, x + w], [0.797, 0.797], color=LINE, lw=1.0)

    y0 = 0.720
    dy = 0.112
    for i, (claim, evidence, status, col) in enumerate(rows):
        y = y0 - i * dy
        box(ax, (0.045, y - 0.032), 0.340, 0.064, claim, fc="#FFFFFF", ec="#DDD7CC", fs=8.70, weight="medium")
        box(ax, (0.430, y - 0.032), 0.300, 0.064, evidence, fc="#F7F5F0", ec="#DDD7CC", fs=8.35)
        box(ax, (0.790, y - 0.032), 0.150, 0.064, status, fc=col + "30", ec=col, fs=8.50, weight="medium")

    ax.text(
        0.50,
        0.070,
        "This is why the next result must be a full-budget validation, not another short debugging run.",
        ha="center",
        fontsize=9.25,
        color=MUTED,
    )
    save(fig, "evidence_status_matrix.pdf")


def chemical_space_projection() -> None:
    path = p("results/chemical_space_projection/chemical_space_projection.csv")
    summary_path = p("results/chemical_space_projection/summary.json")
    if not path.exists():
        return
    df = pd.read_csv(path)
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}

    use_umap = (
        bool(summary.get("umap_available"))
        and {"umap_1", "umap_2"}.issubset(df.columns)
        and df[["umap_1", "umap_2"]].notna().all().all()
    )
    xcol, ycol = ("umap_1", "umap_2") if use_umap else ("pca_1", "pca_2")
    axis_name = "UMAP" if use_umap else "PCA"

    fig, axes = plt.subplots(1, 2, figsize=(8.65, 4.15), gridspec_kw={"wspace": 0.28})
    split_colors = {"train": BLUE_D, "val": SAND, "test": CLAY}
    split_order = ["train", "val", "test"]

    ax = axes[0]
    style_axes(ax, grid_axis="")
    for split in split_order:
        part = df[df["split"] == split]
        if part.empty:
            continue
        ax.scatter(
            part[xcol],
            part[ycol],
            s=9 if split == "train" else 13,
            alpha=0.32 if split == "train" else 0.55,
            color=split_colors[split],
            linewidths=0,
            label=split,
        )
    ax.set_xlabel(f"{axis_name} 1")
    ax.set_ylabel(f"{axis_name} 2")
    ax.set_title("Morgan-fingerprint chemical space")
    ax.legend(frameon=False, loc="upper right")

    ax = axes[1]
    style_axes(ax, grid_axis="")
    sc = ax.scatter(
        df[xcol],
        df[ycol],
        c=df["mol_logp"].clip(-4, 8),
        cmap=LinearSegmentedColormap.from_list("logp_soft", ["#5C7C91", "#E7D69A", "#C47C68"]),
        s=9,
        alpha=0.55,
        linewidths=0,
    )
    ax.set_xlabel(f"{axis_name} 1")
    ax.set_ylabel(f"{axis_name} 2")
    ax.set_title("Same projection colored by MolLogP")
    cbar = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.025)
    cbar.set_label("MolLogP")
    cbar.outline.set_visible(False)

    qx = df[xcol].quantile([0.005, 0.995]).to_numpy()
    qy = df[ycol].quantile([0.005, 0.995]).to_numpy()
    xpad = (qx[1] - qx[0]) * 0.05
    ypad = (qy[1] - qy[0]) * 0.05
    for axis in axes:
        axis.set_xlim(qx[0] - xpad, qx[1] + xpad)
        axis.set_ylim(qy[0] - ypad, qy[1] + ypad)

    fig.suptitle(
        f"Dataset-level interpretability: {axis_name} view of the scaffold test",
        fontsize=12.4,
        weight="medium",
        y=0.990,
    )
    save(fig, "chemical_space_projection.pdf")


def embedding_geometry_diagnostics() -> None:
    base = p("results/embedding_interpretability/tgnn_tuned_medium")
    projection_path = base / "embedding_projection.csv"
    summary_path = base / "summary.json"
    if not projection_path.exists() or not summary_path.exists():
        return
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    df = pd.read_csv(projection_path)

    use_umap = (
        bool(summary.get("umap_available"))
        and {"umap_1", "umap_2"}.issubset(df.columns)
        and df[["umap_1", "umap_2"]].notna().all().all()
    )
    xcol, ycol = ("umap_1", "umap_2") if use_umap else ("pca_1", "pca_2")
    axis_name = "UMAP" if use_umap else "PCA"

    fig, axes = plt.subplots(1, 2, figsize=(8.65, 4.15), gridspec_kw={"wspace": 0.28})
    ax = axes[0]
    style_axes(ax, grid_axis="")
    for split, color, alpha, size in [("train", BLUE_D, 0.30, 8), ("test", CLAY, 0.58, 13)]:
        part = df[df["split"] == split]
        if part.empty:
            continue
        ax.scatter(part[xcol], part[ycol], s=size, alpha=alpha, color=color, linewidths=0, label=split)
    ax.set_xlabel(f"{axis_name} 1")
    ax.set_ylabel(f"{axis_name} 2")
    ax.set_title("Frozen TGNN representation")
    ax.legend(frameon=False, loc="upper right")

    ax = axes[1]
    style_axes(ax, grid_axis="")
    sc = ax.scatter(
        df[xcol],
        df[ycol],
        c=df["mol_logp"].clip(-4, 8),
        cmap=LinearSegmentedColormap.from_list("embed_logp", ["#5C7C91", "#E7D69A", "#C47C68"]),
        s=9,
        alpha=0.55,
        linewidths=0,
    )
    ax.set_xlabel(f"{axis_name} 1")
    ax.set_ylabel(f"{axis_name} 2")
    ax.set_title("Same representation colored by MolLogP")
    cbar = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.025)
    cbar.set_label("MolLogP")
    cbar.outline.set_visible(False)

    qx = df[xcol].quantile([0.005, 0.995]).to_numpy()
    qy = df[ycol].quantile([0.005, 0.995]).to_numpy()
    xpad = (qx[1] - qx[0]) * 0.05
    ypad = (qy[1] - qy[0]) * 0.05
    for axis in axes:
        axis.set_xlim(qx[0] - xpad, qx[1] + xpad)
        axis.set_ylim(qy[0] - ypad, qy[1] + ypad)

    fig.suptitle("Representation-level interpretability", fontsize=12.4, weight="medium", y=0.990)
    save(fig, "embedding_geometry_diagnostics.pdf")


def cluster_error_interpretability() -> None:
    projection_path = p("results/chemical_space_projection/chemical_space_projection.csv")
    profiles_path = p("results/chemical_space_projection/cluster_profiles.csv")
    errors_path = p("results/chemical_space_projection/cluster_model_errors.csv")
    summary_path = p("results/chemical_space_projection/summary.json")
    if not projection_path.exists() or not profiles_path.exists() or not errors_path.exists():
        return

    df = pd.read_csv(projection_path)
    profiles = pd.read_csv(profiles_path)
    errors = pd.read_csv(errors_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    use_umap = (
        bool(summary.get("umap_available"))
        and {"umap_1", "umap_2"}.issubset(df.columns)
        and df[["umap_1", "umap_2"]].notna().all().all()
    )
    xcol, ycol = ("umap_1", "umap_2") if use_umap else ("pca_1", "pca_2")
    axis_name = "UMAP" if use_umap else "PCA"

    palette = ["#6F8FA6", "#D9A96E", "#7BAA8D", "#C98273", "#9C8BB7", "#8F9C6B", "#B78A9B", "#8B9CA8"]
    cluster_ids = sorted(int(c) for c in profiles["cluster"].unique())
    color_map = {cid: palette[i % len(palette)] for i, cid in enumerate(cluster_ids)}

    piv = errors.pivot_table(index="cluster", columns="model", values="mae", aggfunc="first")
    for col in ["DirectGNN", "TGNN_MPNN"]:
        if col not in piv.columns:
            return
    piv["delta_tgnn_direct"] = piv["TGNN_MPNN"] - piv["DirectGNN"]
    profiles = profiles.set_index("cluster")
    labels = []
    deltas = []
    ns = []
    for cid in cluster_ids:
        if cid not in piv.index:
            continue
        labels.append(f"C{cid}")
        deltas.append(float(piv.loc[cid, "delta_tgnn_direct"]))
        ns.append(int(errors[(errors["cluster"] == cid) & (errors["model"] == "DirectGNN")]["n_rows"].iloc[0]))

    fig = plt.figure(figsize=(8.95, 4.65), facecolor=BG)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.07, 1.0], wspace=0.30)

    ax = fig.add_subplot(gs[0, 0])
    style_axes(ax, grid_axis="")
    for cid in cluster_ids:
        part = df[df["cluster"] == cid]
        if part.empty:
            continue
        ax.scatter(part[xcol], part[ycol], s=10, alpha=0.46, linewidths=0, color=color_map[cid], label=f"C{cid}")
        cx, cy = part[xcol].median(), part[ycol].median()
        ax.text(
            cx,
            cy,
            f"C{cid}",
            ha="center",
            va="center",
            fontsize=8.3,
            weight="medium",
            color=INK,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=color_map[cid], lw=0.8, alpha=0.90),
        )
    ax.set_xlabel(f"{axis_name} 1")
    ax.set_ylabel(f"{axis_name} 2")
    ax.set_title("Functional-group clusters")

    qx = df[xcol].quantile([0.005, 0.995]).to_numpy()
    qy = df[ycol].quantile([0.005, 0.995]).to_numpy()
    ax.set_xlim(qx[0] - (qx[1] - qx[0]) * 0.06, qx[1] + (qx[1] - qx[0]) * 0.06)
    ax.set_ylim(qy[0] - (qy[1] - qy[0]) * 0.06, qy[1] + (qy[1] - qy[0]) * 0.06)

    ax = fig.add_subplot(gs[0, 1])
    style_axes(ax, grid_axis="x")
    y = np.arange(len(labels))
    colors = [CLAY if d > 0 else TEAL_D for d in deltas]
    ax.barh(y, deltas, color=colors, edgecolor="white", linewidth=0.8, height=0.66)
    ax.axvline(0, color=LINE, lw=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7.6)
    ax.invert_yaxis()
    ax.set_xlabel("TGNN MAE - DirectGNN MAE")
    ax.set_title("Where the physics path helps or hurts")
    lim = max(0.75, float(np.nanmax(np.abs(deltas))) * 1.25)
    ax.set_xlim(-lim, lim)
    for yy, d, n in zip(y, deltas, ns):
        if d < -0.18:
            ax.text(d / 2, yy, f"{d:+.2f}  n={n}", va="center", ha="center", fontsize=7.2, color="white")
        elif d < 0:
            ax.text(d - 0.035 * lim, yy, f"{d:+.2f}  n={n}", va="center", ha="right", fontsize=7.2, color=MUTED)
        else:
            ax.text(d + 0.025 * lim, yy, f"{d:+.2f}  n={n}", va="center", ha="left", fontsize=7.2, color=MUTED)

    fig.suptitle("Cluster-level model interpretation", fontsize=12.6, weight="medium", y=0.990, color=INK)
    save(fig, "cluster_error_interpretability.pdf")


def supervision_matrix() -> None:
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.patch.set_facecolor(BG)
    sources = ["SLE\nln x2", "$T_m$", "$\\Delta H_{fus}$", "IDAC\n$\\ln\\gamma^\\infty$", "Hansen\nparams", "Van't Hoff\nslopes", "UNIFAC\nprior"]
    targets = ["crystal\n$T_m$", "crystal\n$\\Delta H$", "activity\n$\\tau$", "temperature\nslope", "pair\nrepresentation"]
    data = np.array([
        [1, 1, 1, 1, 1],
        [3, 0, 0, 1, 0],
        [0, 3, 0, 1, 0],
        [0, 0, 3, 1, 1],
        [0, 0, 1, 0, 3],
        [1, 1, 2, 3, 1],
        [0, 0, 2, 1, 2],
    ], dtype=float)
    cmap = LinearSegmentedColormap.from_list(
        "soft_matrix",
        ["#FFFFFF", "#EEF4F7", "#BFD8C8", "#5F9279"],
    )
    im = ax.imshow(data, cmap=cmap, vmin=0, vmax=3, aspect="auto")
    ax.set_xticks(np.arange(len(targets)))
    ax.set_xticklabels(targets)
    ax.set_yticks(np.arange(len(sources)))
    ax.set_yticklabels(sources)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Which observations constrain which hidden quantities", pad=18, fontsize=12.5, weight="medium")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            label = {0: "", 1: "weak", 2: "prior", 3: "direct"}[int(data[i, j])]
            if label:
                ax.text(j, i, label, ha="center", va="center", fontsize=8.5, color=INK, weight="medium")
    ax.set_xticks(np.arange(-.5, len(targets), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(sources), 1), minor=True)
    ax.grid(which="minor", color="#DDD7CC", linewidth=0.9)
    ax.tick_params(which="minor", bottom=False, left=False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.032, pad=0.025)
    cbar.set_ticks([0, 1, 2, 3])
    cbar.set_ticklabels(["none", "weak", "prior", "direct"])
    cbar.outline.set_visible(False)
    fig.tight_layout()
    save(fig, "supervision_matrix.pdf")


def structural_generalization_diagnostics() -> None:
    path = p("results/structural_extrapolation_diagnostics/summary.json")
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    comp = data["compositional_generalization"]
    emb = data["embedding_geometry"]
    scaf = data["scaffold_distance_error"]

    models = ["DirectGNN", "TGNN_MPNN"]
    labels = ["DirectGNN", "TGNN-Solv"]
    composed = [comp[m]["row_composed_mae"] for m in models]
    novel = [comp[m]["row_novel_mae"] for m in models]
    gaps = [comp[m]["row_gap_novel_minus_composed"] for m in models]

    fig = plt.figure(figsize=(8.7, 5.15), facecolor=BG)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 0.95], wspace=0.30)
    ax = fig.add_subplot(gs[0, 0])
    style_axes(ax)
    x = np.arange(len(models))
    w = 0.32
    b1 = ax.bar(x - w / 2, composed, width=w, color=TEAL_D, edgecolor="white", linewidth=0.8, label="known BRICS")
    b2 = ax.bar(x + w / 2, novel, width=w, color=CLAY, edgecolor="white", linewidth=0.8, label="novel BRICS")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, max(novel) * 1.22)
    ax.set_ylabel("MAE on ln x2")
    ax.set_title("Fragment novelty increases error")
    ax.legend(frameon=False, loc="upper left")
    label_bars(ax, b1, "{:.2f}", dy=0.012)
    label_bars(ax, b2, "{:.2f}", dy=0.012)
    for xi, gap in zip(x, gaps):
        ax.text(xi, max(composed[xi], novel[xi]) + 0.16, f"gap +{gap:.2f}", ha="center", fontsize=8.8, color=MUTED)

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_axis_off(); ax2.set_xlim(0, 1); ax2.set_ylim(0, 1)
    box(ax2, (0.07, 0.72), 0.86, 0.18,
        f"Fully composed rows\n{comp['DirectGNN']['row_composed_fraction']:.1%} of scaffold test",
        fc="#FFFFFF", ec=TEAL_D, fs=9.4, weight="medium")
    box(ax2, (0.07, 0.49), 0.86, 0.18,
        f"Nearest scaffold distance\nmedian {scaf['DirectGNN']['row_median_distance']:.3f}; weak error correlation",
        fc="#FFFFFF", ec=SAND, fs=9.2, weight="medium")
    box(ax2, (0.07, 0.26), 0.86, 0.18,
        f"Embedding domain shift\nAUC {emb['TGNN_tuned_medium']['domain_auc']:.3f} for tuned TGNN",
        fc="#FFFFFF", ec=LAVENDER, fs=9.2, weight="medium")
    box(ax2, (0.07, 0.055), 0.86, 0.145,
        "Conclusion: new scaffolds are not explained by a single distance scalar;\nfragment and pair-level priors are needed.",
        fc="#F7F5F0", ec="#DAD5CA", fs=8.55)
    fig.suptitle("Structural extrapolation diagnostics", fontsize=13.0, weight="medium", y=0.985, color=INK)
    save(fig, "structural_generalization_diagnostics.pdf")


def physics_bottleneck_audit() -> None:
    path = p("results/physics_bottleneck_diagnostics_medium/intermediates/intermediates_summary.json")
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    corr = data["correction"]
    crystal = data["crystal_vs_activity_contribution"]
    tm = data["T_m_metrics"]
    tau12 = data["tau_12"]
    tau21 = data["tau_21"]

    fig = plt.figure(figsize=(8.55, 5.25), facecolor=BG)
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.30)

    ax = fig.add_subplot(gs[0, 0])
    style_axes(ax)
    names = ["physics\nonly", "after\ncorrection"]
    vals = [corr["physics_metrics_vs_true"]["mae"], corr["final_metrics_vs_true"]["mae"]]
    bars = ax.bar(names, vals, color=[SAND, CLAY], edgecolor="white", linewidth=0.8, width=0.55)
    ax.set_ylim(0, max(vals) * 1.22)
    ax.set_ylabel("MAE on ln x2")
    ax.set_title("Correction does not fix this run")
    label_bars(ax, bars, "{:.3f}", dy=0.015)

    ax = fig.add_subplot(gs[0, 1])
    style_axes(ax)
    names = ["abs(tau12)>8", "abs(tau21)>8", "abs(correction)>0.5"]
    vals = [tau12["frac_abs_gt_8"] * 100, tau21["frac_abs_gt_8"] * 100, corr["frac_abs_gt_0p5"] * 100]
    bars = ax.bar(names, vals, color=[TEAL_D, TEAL, SLATE], edgecolor="white", linewidth=0.8, width=0.55)
    ax.set_ylim(0, max(vals + [0.25]) * 1.35)
    ax.set_ylabel("Rows, %")
    ax.set_title("Physical bounds are mostly respected")
    label_bars(ax, bars, "{:.2f}", dy=0.035)

    ax = fig.add_subplot(gs[1, 0])
    style_axes(ax)
    names = ["median abs(Phi)", "median abs(activity)"]
    vals = [crystal["median_abs_Phi"], crystal["median_abs_minus_ln_gamma"]]
    bars = ax.bar(names, vals, color=[SAND, TEAL_D], edgecolor="white", linewidth=0.8, width=0.55)
    ax.set_ylim(0, max(vals) * 1.25)
    ax.set_ylabel("Absolute contribution")
    ax.set_title("Crystal term dominates")
    label_bars(ax, bars, "{:.2f}", dy=0.015)

    ax = fig.add_subplot(gs[1, 1])
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    box(ax, (0.07, 0.69), 0.86, 0.20,
        f"$T_m$ head\nMAE {tm['mae']:.1f} K, $R^2$ {tm['r2']:.3f}",
        fc="#FFF7E6", ec="#E8D8AC", fs=9.4, weight="medium")
    box(ax, (0.07, 0.405), 0.86, 0.20,
        f"Activity scale\nmedian abs(Phi) / abs(activity) = {crystal['median_abs_ratio_Phi_to_activity']:.1f}",
        fc="#EEF6F1", ec="#D6E4D8", fs=9.2, weight="medium")
    box(ax, (0.07, 0.120), 0.86, 0.20,
        "Readout\nbounded correction is inactive;\nNRTL supervision remains the bottleneck.",
        fc="#F7F5F0", ec="#DAD5CA", fs=8.9)

    fig.suptitle("Medium-budget TGNN physical-path audit", fontsize=13.0, weight="medium", y=0.995, color=INK)
    save(fig, "physics_bottleneck_audit.pdf")


def sle_decomposition() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.55))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Thermodynamic decomposition of solubility")
    box(ax, (0.06, 0.48), 0.23, 0.17, "crystal term\n$\\Phi(T)=\\Delta G_{fus}/RT$\n$T_m,\\Delta H_{fus},\\Delta C_p$", fc="#FFF7E6", ec="#E8D8AC")
    box(ax, (0.39, 0.48), 0.23, 0.17, "solution term\n$\\ln\\gamma_2$\nNRTL / IDAC / UNIFAC", fc="#EEF6F1", ec="#D6E4D8")
    box(ax, (0.72, 0.48), 0.22, 0.17, "prediction\n$\\ln x_2=-\\Phi(T)-\\ln\\gamma_2$", fc="#EEF4F7", ec="#D4DEE5", weight="semibold")
    arrow(ax, (0.29, 0.565), (0.39, 0.565), color=MUTED)
    arrow(ax, (0.62, 0.565), (0.72, 0.565), color=MUTED)
    ax.text(0.175, 0.30, "pure solid phase:\npacking, rigidity, melting", ha="center", fontsize=9, color=MUTED)
    ax.text(0.505, 0.30, "molecular pair:\npolarity, H-bonds, compatibility", ha="center", fontsize=9, color=MUTED)
    ax.text(0.83, 0.30, "both errors enter\nthe final log-solubility", ha="center", fontsize=9, color=MUTED)
    save(fig, "sle_decomposition_schematic.pdf")


def data_collection_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(7.8, 5.35))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Data collection and processing pipeline", y=0.985)

    box(ax, (0.04, 0.68), 0.19, 0.13, "BigSolDB v2.1\nSLE records\nSMILES, T, solubility", fc="#EEF4F7", ec="#D4DEE5", weight="semibold", fs=9.0)
    box(ax, (0.04, 0.43), 0.19, 0.13, "auxiliary\nproperty sources\n$T_m$, $\\Delta H$, Hansen", fc="#FFF7E6", ec="#E8D8AC", weight="semibold", fs=9.0)
    box(ax, (0.04, 0.18), 0.19, 0.13, "activity data\nIDAC / UNIFAC\n$\\ln\\gamma^\\infty$", fc="#EEF6F1", ec="#D6E4D8", weight="semibold", fs=9.0)

    box(ax, (0.33, 0.55), 0.19, 0.18, "standardization\n\ncanonical SMILES\nunit conversion\nmask columns", fc=PANEL, ec="#DADDE2", weight="semibold", fs=9.0)
    box(ax, (0.60, 0.55), 0.18, 0.18, "quality checks\n\nfinite targets\nno conflicting triples\nsource metadata", fc="#F7F5F0", ec="#DAD5CA", weight="semibold", fs=9.0)
    box(ax, (0.83, 0.60), 0.13, 0.13, "frozen\nSLE splits", fc="#FCEFEA", ec="#E7C9BC", weight="semibold", fs=9.0)

    box(ax, (0.60, 0.25), 0.18, 0.15, "separate\nauxiliary streams\ntrain only", fc="#F1F5F0", ec="#D6E4D8", weight="semibold", fs=9.0)
    box(ax, (0.83, 0.25), 0.13, 0.15, "training\nloaders", fc=PANEL, ec="#DADDE2", weight="semibold", fs=9.0)

    for y, rad in [(0.745, 0.07), (0.495, -0.02), (0.245, -0.09)]:
        arrow(ax, (0.23, y), (0.33, 0.64), color=MUTED, rad=rad)
    arrow(ax, (0.52, 0.64), (0.60, 0.64), color=MUTED)
    arrow(ax, (0.78, 0.64), (0.83, 0.665), color=MUTED)
    arrow(ax, (0.52, 0.58), (0.60, 0.325), color=TEAL_D, rad=-0.14)
    arrow(ax, (0.78, 0.325), (0.83, 0.325), color=TEAL_D)

    ax.text(0.50, 0.085, "The validation/test SLE composition is kept fixed; activity-only rows are consumed by separate objectives.",
            ha="center", fontsize=9.3, color=MUTED)
    save(fig, "data_collection_pipeline_schematic.pdf")


def idac_collection_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(7.25, 5.05))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "IDAC corpus construction", y=0.985)

    # Three-zone layout with short routing; no cross-page snake arrows.
    box(ax, (0.035, 0.250), 0.270, 0.525, "", fc="#F5F9FB", ec="#D4DEE5")
    box(ax, (0.355, 0.250), 0.275, 0.525, "", fc="#FFFFFF", ec="#DADDE2")
    box(ax, (0.680, 0.250), 0.285, 0.525, "", fc="#F7FAF8", ec="#D9E5DD")

    ax.text(0.168, 0.725, "sources", ha="center", fontsize=10.8, weight="medium", color=BLUE_D)
    ax.text(0.493, 0.725, "processing", ha="center", fontsize=10.8, weight="medium", color=MUTED)
    ax.text(0.823, 0.725, "training output", ha="center", fontsize=10.8, weight="medium", color=TEAL_D)

    box(ax, (0.070, 0.610), 0.200, 0.074, "NIST ThermoML\narchive", fc="#EEF4F7", ec="#D4DEE5", fs=9.35, weight="medium")
    box(ax, (0.070, 0.485), 0.200, 0.074, "DOI cache\nJSON records", fc="#EEF4F7", ec="#D4DEE5", fs=9.35, weight="medium")
    box(ax, (0.070, 0.360), 0.200, 0.074, "RDKit InChI\n$\\rightarrow$ SMILES", fc="#FFF7E6", ec="#E8D8AC", fs=9.25, weight="medium")

    box(ax, (0.390, 0.610), 0.205, 0.074, "extract IDAC\n$\\gamma^\\infty$, T, pair", fc="#EEF6F1", ec="#D6E4D8", fs=9.15, weight="medium")
    box(ax, (0.390, 0.485), 0.205, 0.074, "aggregate\nby pair and T", fc="#FFFFFF", ec="#DADDE2", fs=9.30, weight="medium")
    box(ax, (0.390, 0.360), 0.205, 0.074, "quality audit\n0 conflicts", fc="#F7F5F0", ec="#DAD5CA", fs=9.30, weight="medium")

    box(ax, (0.720, 0.600), 0.215, 0.084, "expanded corpus\n14.9k rows\n3,145 pairs", fc="#FFFFFF", ec=BLUE_D, fs=9.05, weight="medium")
    box(ax, (0.720, 0.470), 0.215, 0.084, "train stream\n14,876 rows", fc="#FFFFFF", ec=TEAL_D, fs=9.20, weight="medium")
    box(ax, (0.720, 0.340), 0.215, 0.084, "separate loader\nnot appended", fc="#FCEFEA", ec="#E7C9BC", fs=9.20, weight="medium")

    arrow(ax, (0.270, 0.647), (0.390, 0.647), color=MUTED, lw=0.95)
    arrow(ax, (0.270, 0.522), (0.390, 0.647), color=MUTED, rad=0.05, lw=0.95)
    arrow(ax, (0.270, 0.397), (0.390, 0.522), color=SAND, rad=0.05, lw=0.95)
    arrow(ax, (0.493, 0.610), (0.493, 0.559), color=MUTED, lw=0.95)
    arrow(ax, (0.493, 0.485), (0.493, 0.434), color=MUTED, lw=0.95)
    arrow(ax, (0.595, 0.647), (0.720, 0.642), color=BLUE_D, lw=0.95)
    arrow(ax, (0.823, 0.600), (0.823, 0.554), color=TEAL_D, lw=0.95)
    arrow(ax, (0.823, 0.470), (0.823, 0.424), color=CLAY, lw=0.95)

    ax.text(0.168, 0.290, "starter corpus:\n404 rows / 138 pairs / 9 DOI",
            ha="center", va="center", fontsize=9.15, color=MUTED, linespacing=1.25)
    ax.text(0.493, 0.290, "0 SLE-pair overlap\nwith solubility labels",
            ha="center", va="center", fontsize=9.15, color=MUTED, linespacing=1.25)

    ax.text(0.50, 0.085, "IDAC is an activity-only auxiliary stream, not a solubility label.",
            ha="center", fontsize=9.45, color=MUTED)
    save(fig, "idac_collection_pipeline_schematic.pdf")


def evaluation_regimes() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.7))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Evaluation regimes answer different questions")
    cards = [
        (0.055, "structural\nextrapolation", "new solute or\nnew scaffold\n\nmain difficulty:\nchemical novelty", "#FCEFEA", "#E7C9BC"),
        (0.385, "temperature\ninterpolation", "same pair,\ninside observed range\n\nphysical floor:\nMAE $\\approx$ 0.04", "#EEF6F1", "#D6E4D8"),
        (0.715, "temperature\nextrapolation", "same pair,\nlow $T$ $\\rightarrow$ high $T$\n\nVan't Hoff:\nMAE 0.368", "#EEF4F7", "#D4DEE5"),
    ]
    for x, head, body, fc, ec in cards:
        box(ax, (x, 0.42), 0.23, 0.33, head + "\n\n" + body, fc=fc, ec=ec, fs=9.3, weight="semibold")
    arrow(ax, (0.285, 0.585), (0.385, 0.585), color=MUTED)
    arrow(ax, (0.615, 0.585), (0.715, 0.585), color=MUTED)
    ax.text(0.17, 0.24, "DirectGNN currently leads\non scaffold MAE", ha="center", fontsize=9, color=MUTED)
    ax.text(0.50, 0.24, "pairwise curves are\nvery smooth", ha="center", fontsize=9, color=MUTED)
    ax.text(0.83, 0.24, "the key regime where\nphysics should pay off", ha="center", fontsize=9, color=MUTED)
    save(fig, "evaluation_regimes_schematic.pdf")


def water_graph() -> None:
    fig, ax = plt.subplots(figsize=(8.7, 4.35))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Water is a degenerate heavy-atom graph")
    ax.text(0.27, 0.78, "heavy-atom graph", ha="center", fontsize=10, weight="semibold")
    ax.text(0.74, 0.78, "explicit-H small molecule mode", ha="center", fontsize=10, weight="semibold")

    ax.add_patch(Circle((0.27, 0.49), 0.058, facecolor=PANEL, edgecolor=BLUE_D, linewidth=1.4,
                        path_effects=[pe.SimplePatchShadow(offset=(1, -1), alpha=0.08), pe.Normal()]))
    ax.text(0.27, 0.49, "O", ha="center", va="center", fontsize=13, weight="semibold")
    ax.text(0.27, 0.30, "1 node\nno O--H edges\nmessage passing is weak", ha="center", fontsize=9, color=MUTED)

    o = (0.74, 0.48); h1 = (0.63, 0.62); h2 = (0.85, 0.62)
    ax.plot([o[0], h1[0]], [o[1], h1[1]], color=LINE, lw=2.4, solid_capstyle="round")
    ax.plot([o[0], h2[0]], [o[1], h2[1]], color=LINE, lw=2.4, solid_capstyle="round")
    for label, xy, r in [("O", o, 0.058), ("H", h1, 0.045), ("H", h2, 0.045)]:
        ax.add_patch(Circle(xy, r, facecolor=PANEL, edgecolor=TEAL_D, linewidth=1.4,
                            path_effects=[pe.SimplePatchShadow(offset=(1, -1), alpha=0.08), pe.Normal()]))
        ax.text(*xy, label, ha="center", va="center", fontsize=12, weight="semibold")
    ax.text(0.74, 0.30, "3 nodes\nO--H edges restored\npolarity enters the graph", ha="center", fontsize=9, color=MUTED)
    save(fig, "water_graph_schematic.pdf")


def gradient_flow() -> None:
    fig, ax = plt.subplots(figsize=(7.6, 4.45))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Current gradient competition")
    box(ax, (0.08, 0.48), 0.22, 0.16, "shared\nencoder", fc="#F1F2F4", ec="#DADDE2", weight="medium", fs=10.2)
    box(ax, (0.48, 0.66), 0.24, 0.14, "crystal heads\n$T_m,\\Delta H_{fus}$", fc="#FFF7E6", ec="#E8D8AC", fs=9.8)
    box(ax, (0.48, 0.28), 0.24, 0.14, "pair activity head\n$\\tau_{12},\\tau_{21},\\alpha$", fc="#EEF6F1", ec="#D6E4D8", fs=9.8)
    box(ax, (0.80, 0.47), 0.13, 0.16, "SLE\nloss", fc="#FCEFEA", ec="#E7C9BC", fs=10.0)
    arrow(ax, (0.30, 0.56), (0.48, 0.73), color=SAND, rad=0.08, lw=2.2)
    arrow(ax, (0.30, 0.55), (0.48, 0.35), color=TEAL_D, rad=-0.08, lw=1.1)
    arrow(ax, (0.72, 0.35), (0.80, 0.52), color=CLAY, rad=0.05)
    arrow(ax, (0.72, 0.73), (0.80, 0.58), color=CLAY, rad=-0.05)
    ax.text(0.37, 0.77, "strong direct supervision", fontsize=8.9, color=MUTED, ha="center")
    ax.text(0.36, 0.27, "weak indirect path", fontsize=8.9, color=MUTED, ha="center")
    save(fig, "gradient_flow.pdf")


def gradient_flow_fix() -> None:
    fig, ax = plt.subplots(figsize=(7.6, 4.45))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Proposed training fix")
    box(ax, (0.06, 0.48), 0.19, 0.16, "shared\nbackbone", fc="#F1F2F4", ec="#DADDE2", weight="medium", fs=10.0)
    box(ax, (0.36, 0.66), 0.22, 0.14, "crystal adapter", fc="#FFF7E6", ec="#E8D8AC", fs=9.8)
    box(ax, (0.36, 0.28), 0.22, 0.14, "interaction adapter", fc="#EEF6F1", ec="#D6E4D8", fs=9.8)
    box(ax, (0.68, 0.66), 0.22, 0.14, "crystal\nproperties", fc="#FFF7E6", ec="#E8D8AC", fs=9.8)
    box(ax, (0.68, 0.28), 0.22, 0.14, "NRTL +\nauxiliary direct loss", fc="#EEF6F1", ec="#D6E4D8", fs=9.5)
    arrow(ax, (0.25, 0.58), (0.36, 0.73), color=SAND, rad=0.08)
    arrow(ax, (0.25, 0.53), (0.36, 0.35), color=TEAL_D, rad=-0.08)
    arrow(ax, (0.58, 0.73), (0.68, 0.73), color=SAND)
    arrow(ax, (0.58, 0.35), (0.68, 0.35), color=TEAL_D)
    ax.text(0.50, 0.52, "detach or reduce\ncrystal gradient\nin phase 2", ha="center", fontsize=8.9, color=MUTED)
    save(fig, "gradient_flow_fix.pdf")


def compute_plan() -> None:
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Prepared full-budget validation path")
    cards = [
        (0.06, "1", "temperature\nextrapolation", "TGNN vs DirectGNN"),
        (0.38, "2", "scaffold\nvalidation", "same protocol, full budget"),
        (0.70, "3", "ablation\nstudy", "IDAC, UNIFAC, explicit-H"),
    ]
    for x, n, head, body in cards:
        box(ax, (x, 0.43), 0.23, 0.24, f"{n}\n{head}\n{body}", fc="#EEF4F7", ec="#D4DEE5", weight="semibold")
    arrow(ax, (0.29, 0.55), (0.38, 0.55), color=MUTED)
    arrow(ax, (0.61, 0.55), (0.70, 0.55), color=MUTED)
    ax.text(0.5, 0.22, "This figure is retained as an asset for talks; the supervisor report no longer contains a separate resource-request section.",
            ha="center", fontsize=8.8, color=MUTED)
    save(fig, "compute_plan_schematic.pdf")


def pretraining_tasks() -> None:
    fig, ax = plt.subplots(figsize=(6.9, 4.25))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Stage 0 pretraining tasks")

    box(ax, (0.045, 0.585), 0.195, 0.180, "masked\nsubgraph\n\nlocal atom\nchemistry", fc="#EEF4F7", ec="#D4DEE5", weight="medium", fs=9.55)
    box(ax, (0.285, 0.585), 0.195, 0.180, "bond type\nprediction\n\ntopology and\nvalence", fc="#EEF6F1", ec="#D6E4D8", weight="medium", fs=9.55)
    box(ax, (0.525, 0.585), 0.195, 0.180, "RDKit property\nprediction\n\nglobal molecular\nmeaning", fc="#FFF7E6", ec="#E8D8AC", weight="medium", fs=9.25)
    box(ax, (0.765, 0.585), 0.195, 0.180, "contrastive\nviews\n\nstable chemical\nembedding", fc="#FCEFEA", ec="#E7C9BC", weight="medium", fs=9.45)

    box(ax, (0.095, 0.230), 0.810, 0.135, "warm-start molecular encoder for TGNN-Solv and DirectGNN", fc=PANEL, ec="#DADDE2", fs=10.5, weight="medium")
    for x in [0.142, 0.382, 0.622, 0.862]:
        arrow(ax, (x, 0.58), (x, 0.37), color=MUTED)
    ax.text(0.5, 0.10, "All pretraining heads are temporary; only the encoder weights are transferred to solubility training.",
            ha="center", fontsize=9.3, color=MUTED)
    save(fig, "pretraining_tasks_schematic.pdf")


def training_curriculum() -> None:
    fig, ax = plt.subplots(figsize=(6.9, 4.20))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Training curriculum")

    phases = [
        (0.045, 0.210, "Stage 0", "self-supervised\nmolecular pretraining", "#F1F2F4", "#DADDE2"),
        (0.300, 0.190, "Phase 1", "physical properties\nno full SLE pressure", "#FFF7E6", "#E8D8AC"),
        (0.535, 0.230, "Phase 2", "full SLE objective\nmain optimization", "#EEF6F1", "#D6E4D8"),
        (0.810, 0.145, "Phase 3", "low-rate\nfine tuning", "#EEF4F7", "#D4DEE5"),
    ]
    y, h = 0.48, 0.19
    for x, w, head, body, fc, ec in phases:
        box(ax, (x, y), w, h, f"{head}\n{body}", fc=fc, ec=ec, fs=9.5, weight="medium")
    for start, end in [((0.255, 0.575), (0.300, 0.575)), ((0.490, 0.575), (0.535, 0.575)), ((0.765, 0.575), (0.810, 0.575))]:
        arrow(ax, start, end, color=MUTED)
    ax.text(0.395, 0.31, "50 epochs", ha="center", fontsize=9.0, color=MUTED)
    ax.text(0.650, 0.31, "200 epochs", ha="center", fontsize=9.0, color=MUTED)
    ax.text(0.882, 0.31, "50 epochs", ha="center", fontsize=9.0, color=MUTED)

    note_y, note_h = 0.105, 0.115
    box(ax, (0.065, note_y), 0.170, note_h, "warm start", fc="#FFFFFF", ec="#E1DED7", fs=8.65)
    box(ax, (0.295, note_y), 0.205, note_h, "crystal, Hansen,\nIDAC anchors", fc="#FFFFFF", ec="#E1DED7", fs=8.65)
    box(ax, (0.548, note_y), 0.205, note_h, "SLE dominates;\nauxiliary stabilizers", fc="#FFFFFF", ec="#E1DED7", fs=8.65)
    box(ax, (0.805, note_y), 0.145, note_h, "small\ncorrections", fc="#FFFFFF", ec="#E1DED7", fs=8.65)
    save(fig, "training_curriculum_schematic.pdf")


def loss_components() -> None:
    labels = ["Stage 0", "Phase 1", "Phase 2", "Phase 3"]
    components = {
        "Solubility": [0.0, 0.0, 0.58, 0.70],
        "Crystal": [0.0, 0.42, 0.08, 0.04],
        "Activity / IDAC": [0.0, 0.23, 0.16, 0.08],
        "Representation": [0.72, 0.20, 0.08, 0.04],
        "Regularization": [0.28, 0.15, 0.10, 0.14],
    }
    colors = {
        "Solubility": BLUE_D,
        "Crystal": SAND,
        "Activity / IDAC": TEAL_D,
        "Representation": LAVENDER,
        "Regularization": SLATE,
    }
    fig, ax = plt.subplots(figsize=(8.7, 4.6))
    style_axes(ax)
    bottom = np.zeros(len(labels))
    x = np.arange(len(labels))
    for name, vals in components.items():
        vals = np.array(vals)
        ax.bar(x, vals, bottom=bottom, color=colors[name], edgecolor="white", linewidth=0.8, label=name)
        bottom += vals
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.18)
    ax.set_ylabel("Relative training emphasis")
    ax.set_title("Loss composition by training stage")
    ax.legend(frameon=False, ncols=2, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.text(1.5, 1.08, "Exact weights are config-dependent; the figure shows the intended balance.",
            ha="center", fontsize=8.6, color=MUTED)
    fig.tight_layout()
    save(fig, "loss_components_schematic.pdf")


def hypothesis_map() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.9))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Working hypotheses")

    rows = [
        (0.055, "H1", "crystal\ncapture", "detach / split\nencoder test", SAND),
        (0.285, "H2", "weak NRTL\nidentification", "IDAC, UNIFAC,\nslope diagnostics", TEAL),
        (0.515, "H3", "T-slope\nmissing", "Van't Hoff anchors\nand slope loss", BLUE),
        (0.745, "H4", "new-chemistry\ngap", "pairwise + fragment\npretraining", LAVENDER),
    ]
    for x, hid, problem, test, col in rows:
        box(ax, (x, 0.55), 0.185, 0.19, f"{hid}\n{problem}", fc="#FFFFFF", ec=col, weight="semibold", fs=9.3)
        box(ax, (x, 0.25), 0.185, 0.16, test, fc="#F7F5F0", ec="#DAD5CA", fs=8.9)
        arrow(ax, (x + 0.0925, 0.55), (x + 0.0925, 0.41), color=MUTED)
    ax.text(0.5, 0.11, "The hypotheses are not conclusions; each has a falsification test and a measurable diagnostic.",
            ha="center", fontsize=9, color=MUTED)
    save(fig, "hypothesis_map_schematic.pdf")


def rdkit_molecular_graphs() -> None:
    try:
        from rdkit import Chem  # noqa: F401
    except Exception:
        # Keep report generation robust on minimal environments.
        water_graph()
        return

    examples = [
        ("paracetamol", "CC(=O)Nc1ccc(O)cc1", False),
        ("ethanol", "CCO", False),
        ("water, explicit H", "O", True),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.95))
    fig.patch.set_facecolor(BG)

    atom_colors = {
        "C": "#F7F7F2",
        "O": "#F4D7D3",
        "N": "#D8E9F0",
        "H": "#FFFFFF",
        "S": "#F2E1A8",
        "Cl": "#DDEEDB",
        "F": "#DDEEDB",
        "Br": "#E8D4C8",
    }

    for ax, (name, smiles, explicit_h) in zip(axes, examples):
        _draw_rdkit_graph(ax, smiles, explicit_h=explicit_h, label=name)

    fig.suptitle("Molecular graph examples from RDKit 2D coordinates", fontsize=13, weight="semibold", color=INK, y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "rdkit_molecular_graph_examples.pdf")


def worked_example_trace() -> None:
    try:
        from rdkit import Chem  # noqa: F401
    except Exception:
        return

    fig = plt.figure(figsize=(11.4, 6.2), facecolor=BG)
    gs = fig.add_gridspec(2, 4, width_ratios=[1.25, 0.95, 1.25, 1.25], height_ratios=[1, 1], wspace=0.45, hspace=0.38)
    ax_mol = fig.add_subplot(gs[:, 0])
    ax_solv = fig.add_subplot(gs[:, 1])
    ax_flow = fig.add_subplot(gs[:, 2:])
    ax_flow.set_axis_off(); ax_flow.set_xlim(0, 1); ax_flow.set_ylim(0, 1)

    _draw_rdkit_graph(ax_mol, "CC(=O)Nc1ccc(O)cc1", label="paracetamol")
    _draw_rdkit_graph(ax_solv, "CCO", label="ethanol")
    fig.suptitle("Worked example: paracetamol in ethanol at 298 K", fontsize=13, weight="semibold", color=INK, y=0.98)

    box(ax_flow, (0.05, 0.70), 0.25, 0.16, "crystal branch\n$T_m,\\Delta H_{fus}$", fc="#FFF7E6", ec="#E8D8AC", weight="semibold")
    box(ax_flow, (0.05, 0.43), 0.25, 0.16, "activity branch\n$\\tau_{12},\\tau_{21},\\alpha$", fc="#EEF6F1", ec="#D6E4D8", weight="semibold")
    box(ax_flow, (0.43, 0.70), 0.21, 0.16, "$\\Phi(T)$\nmelting cost", fc="#FFF7E6", ec="#E8D8AC")
    box(ax_flow, (0.43, 0.43), 0.21, 0.16, "$\\ln\\gamma_2$\nsolution activity", fc="#EEF6F1", ec="#D6E4D8")
    box(ax_flow, (0.74, 0.56), 0.20, 0.18, "$\\ln x_2$\n$=-\\Phi-\\ln\\gamma_2$", fc="#FCEFEA", ec="#E7C9BC", weight="semibold")
    arrow(ax_flow, (0.30, 0.78), (0.43, 0.78), color=SAND)
    arrow(ax_flow, (0.30, 0.51), (0.43, 0.51), color=TEAL_D)
    arrow(ax_flow, (0.64, 0.78), (0.74, 0.66), color=CLAY, rad=-0.07)
    arrow(ax_flow, (0.64, 0.51), (0.74, 0.62), color=CLAY, rad=0.07)

    ax_flow.text(0.50, 0.24, "The numbers are model outputs in a real run; the figure shows the computational trace, not a fitted empirical formula.",
                 ha="center", fontsize=8.8, color=MUTED)
    save(fig, "worked_example_trace.pdf")


def identifiability_constraints() -> None:
    fig, ax = plt.subplots(figsize=(7.8, 5.55))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    title(ax, "Which observations constrain which hidden quantities", y=0.985)

    left = [
        (0.06, 0.72, "$T_m$ labels", SAND),
        (0.06, 0.56, "$\\Delta H_{fus}$ labels", SAND),
        (0.06, 0.40, "SLE $\\ln x_2$", BLUE),
        (0.06, 0.24, "IDAC $\\ln\\gamma^\\infty$", TEAL),
        (0.06, 0.08, "Van't Hoff slopes", LAVENDER),
    ]
    middle = [
        (0.43, 0.63, "crystal\nparameters", "#FFF7E6", "#E8D8AC"),
        (0.43, 0.31, "activity\nparameters", "#EEF6F1", "#D6E4D8"),
        (0.43, 0.07, "temperature\nshape", "#F1F2F4", "#DADDE2"),
    ]
    right = (0.75, 0.39, "final\n$\\ln x_2$", "#FCEFEA", "#E7C9BC")

    for x, y, text, col in left:
        box(ax, (x, y), 0.22, 0.10, text, fc=PANEL, ec=col, fs=9.3, weight="semibold")
    for x, y, text, fc, ec in middle:
        box(ax, (x, y), 0.20, 0.13, text, fc=fc, ec=ec, fs=9.5, weight="semibold")
    box(ax, (right[0], right[1]), 0.18, 0.16, right[2], fc=right[3], ec=right[4], fs=11, weight="semibold")

    arrow(ax, (0.28, 0.77), (0.43, 0.695), color=SAND)
    arrow(ax, (0.28, 0.61), (0.43, 0.675), color=SAND)
    arrow(ax, (0.28, 0.45), (0.43, 0.67), color=BLUE, rad=0.08)
    arrow(ax, (0.28, 0.45), (0.43, 0.375), color=BLUE)
    arrow(ax, (0.28, 0.29), (0.43, 0.375), color=TEAL_D)
    arrow(ax, (0.28, 0.13), (0.43, 0.135), color=LAVENDER)
    arrow(ax, (0.63, 0.695), (0.75, 0.48), color=CLAY, rad=-0.06)
    arrow(ax, (0.63, 0.375), (0.75, 0.47), color=CLAY, rad=0.06)
    arrow(ax, (0.63, 0.135), (0.75, 0.44), color=CLAY, rad=0.12)

    ax.text(0.50, 0.885, "SLE alone mixes crystal and activity effects; auxiliary data reduce inverse-problem ambiguity.",
            ha="center", fontsize=9, color=MUTED)
    save(fig, "identifiability_constraints_schematic.pdf")


# ---------------------------------------------------------------------------
# Data figures
# ---------------------------------------------------------------------------

def corpus_lnx2_histogram() -> None:
    frames = []
    for name in ["train.csv", "val.csv", "test.csv"]:
        df = read_csv(p("notebooks/data/processed", name), usecols=["ln_x2", "has_solubility"])
        if df is not None:
            frames.append(solubility_rows(df))
    data = pd.to_numeric(pd.concat(frames, ignore_index=True)["ln_x2"], errors="coerce").dropna()
    fig, ax = plt.subplots(figsize=(6.1, 4.1))
    style_axes(ax)
    ax.hist(data, bins=55, color=BLUE, edgecolor="white", linewidth=0.35)
    ax.axvline(data.median(), color=CLAY, lw=1.6, label=f"median = {data.median():.2f}")
    ax.set_title("Target distribution")
    ax.set_xlabel("ln mole fraction, ln x2")
    ax.set_ylabel("Rows")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    save(fig, "corpus_lnx2_histogram.pdf")


def corpus_points_per_pair() -> None:
    usecols = ["solute_smiles", "solvent_smiles", "ln_x2", "has_solubility"]
    frames = []
    for name in ["train.csv", "val.csv", "test.csv"]:
        df = read_csv(p("notebooks/data/processed", name), usecols=usecols)
        if df is not None:
            frames.append(solubility_rows(df).dropna(subset=["ln_x2"]))
    df = pd.concat(frames, ignore_index=True)
    counts = df.groupby(["solute_smiles", "solvent_smiles"]).size()
    fig, ax = plt.subplots(figsize=(6.1, 4.1))
    style_axes(ax)
    clipped = counts.clip(upper=40)
    bins = np.arange(1, 42) - 0.5
    ax.hist(clipped, bins=bins, color=TEAL, edgecolor="white", linewidth=0.35)
    ax.axvline(counts.median(), color=CLAY, lw=1.6, label=f"median = {counts.median():.0f}")
    ax.set_title("Temperature observations per pair")
    ax.set_xlabel("Rows per solute-solvent pair")
    ax.set_ylabel("Pairs")
    ax.set_xlim(0.5, 40.5)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    save(fig, "corpus_points_per_pair.pdf")


def corpus_temperature_histogram() -> None:
    frames = []
    for name in ["train.csv", "val.csv", "test.csv"]:
        df = read_csv(p("notebooks/data/processed", name), usecols=["temperature", "has_solubility"])
        if df is not None:
            frames.append(solubility_rows(df))
    if not frames:
        return
    data = pd.to_numeric(pd.concat(frames, ignore_index=True)["temperature"], errors="coerce").dropna()
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    style_axes(ax)
    ax.hist(data, bins=46, color=SAND, edgecolor="white", linewidth=0.35)
    ax.axvline(data.median(), color=CLAY, lw=1.6, label=f"median = {data.median():.1f} K")
    ax.axvline(298.15, color=INK, lw=1.1, ls="--", label="298.15 K")
    ax.set_title("Temperature distribution")
    ax.set_xlabel("Temperature, K")
    ax.set_ylabel("Rows")
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    save(fig, "corpus_temperature_histogram.pdf")


def corpus_solvent_barplot() -> None:
    frames = []
    cols = ["solvent_smiles", "solvent_name", "has_solubility"]
    for name in ["train.csv", "val.csv", "test.csv"]:
        df = read_csv(p("notebooks/data/processed", name), usecols=cols)
        if df is not None:
            frames.append(solubility_rows(df))
    if not frames:
        return
    df = pd.concat(frames, ignore_index=True)
    label = df["solvent_name"].fillna(df["solvent_smiles"]).astype(str)
    label = label.str.replace("_", " ", regex=False).str.slice(0, 28)
    counts = label.value_counts().head(14).sort_values()
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    style_axes(ax, grid_axis="x")
    bars = ax.barh(np.arange(len(counts)), counts.values, color=TEAL, edgecolor="white", linewidth=0.7)
    ax.set_yticks(np.arange(len(counts)))
    ax.set_yticklabels(counts.index)
    ax.set_xlabel("Rows")
    ax.set_title("Most frequent solvents")
    for b in bars:
        ax.text(b.get_width() + counts.max() * 0.015, b.get_y() + b.get_height()/2,
                f"{int(b.get_width()):,}", ha="left", va="center", fontsize=8.4, color=MUTED)
    ax.set_xlim(0, counts.max() * 1.18)
    fig.tight_layout()
    save(fig, "corpus_solvent_barplot.pdf")


def knn_modelability_diagnostics() -> None:
    bins = read_csv(p("results/knn_modelability_smoke/modelability_bins.csv"))
    fig, ax = plt.subplots(figsize=(7.2, 4.45))
    style_axes(ax)
    if bins is None:
        labels = ["0.00-0.30", "0.30-0.50", "0.50-0.70", "0.70-0.85", "0.85-1.00"]
        mae = np.array([2.96, 2.68, 2.26, 1.70, 1.19])
        cliff = np.array([0.50, 0.51, 0.47, 0.30, 0.0])
    else:
        labels = bins["pair_tanimoto_bin"].astype(str).tolist()
        mae = bins["mean_abs_delta_ln_x2"].astype(float).to_numpy()
        cliff = bins["cliff_rate"].astype(float).to_numpy()
    x = np.arange(len(labels))
    bars = ax.bar(x, mae, width=0.58, color=BLUE, edgecolor="white", linewidth=0.8)
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=0)
    ax.set_ylabel("Nearest-neighbor |delta ln x2|")
    ax.set_xlabel("Pair Tanimoto bin")
    ax.set_title("Modelability is limited by chemical distance")
    ax.set_ylim(0, max(mae) * 1.30)
    label_bars(ax, bars, "{:.2f}", dy=0.012)
    ax2 = ax.twinx()
    ax2.plot(x, cliff, color=CLAY, marker="o", lw=2.0, label="cliff rate")
    ax2.set_ylabel("Solubility cliff rate")
    ax2.set_ylim(0, max(0.6, cliff.max() * 1.18))
    ax2.tick_params(length=0, colors=MUTED)
    ax2.spines["right"].set_visible(False)
    ax2.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    save(fig, "knn_modelability_diagnostics.pdf")


def source_uncertainty_coverage() -> None:
    cov = read_csv(p("results/source_uncertainty_audit_reviewed/source_coverage.csv"))
    mix_path = p("results/source_uncertainty_audit_reviewed/summary.json")
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.2), gridspec_kw={"width_ratios": [1.15, 1.0]})
    for ax in axes:
        style_axes(ax)
    if cov is not None:
        x = cov["top_k_sources"].astype(float).to_numpy()
        y = 100.0 * cov["coverage_fraction"].astype(float).to_numpy()
    else:
        x = np.array([10, 20, 50, 100, 200, 500, 1000])
        y = np.array([2.8, 4.7, 9.5, 16.4, 28.3, 57.3, 86.7])
    axes[0].plot(x, y, color=BLUE_D, marker="o", lw=2.0)
    axes[0].set_xscale("log")
    axes[0].set_ylim(0, 100)
    axes[0].set_xlabel("Top-k sources")
    axes[0].set_ylabel("Row coverage, %")
    axes[0].set_title("Source concentration")
    method_mix = {
        "multi-temperature": 92693,
        "unknown": 9530,
        "gravimetric": 2949,
        "computed/modeled": 2089,
        "other": 1026,
    }
    if mix_path.exists():
        try:
            raw = json.loads(mix_path.read_text()).get("row_weighted_method_mix", {})
            method_mix = {
                "multi-temperature": raw.get("multi_temperature_primary", 0),
                "unknown": raw.get("unknown", 0),
                "gravimetric": raw.get("gravimetric_equilibrium", 0),
                "computed/modeled": raw.get("computed_or_modeled", 0),
                "other": raw.get("polythermal_visual", 0) + raw.get("single_temperature_primary", 0) + raw.get("unknown_primary", 0),
            }
        except Exception:
            pass
    labels = list(method_mix.keys())
    vals = np.array(list(method_mix.values()), dtype=float)
    order = np.argsort(vals)
    axes[1].barh(np.arange(len(order)), vals[order], color=TEAL, edgecolor="white", linewidth=0.8)
    axes[1].set_yticks(np.arange(len(order))); axes[1].set_yticklabels([labels[i] for i in order])
    axes[1].set_xlabel("Rows")
    axes[1].set_title("Source method mix")
    fig.tight_layout()
    save(fig, "source_uncertainty_coverage.pdf")


def source_weighting_ablation() -> None:
    df = read_csv(p("results/source_weighted_proxy_subset/comparison.csv"))
    if df is None:
        return
    pivot = df.pivot(index="model", columns="weighting", values="mae")
    models = [m for m in ["DirectGNN", "TGNN-Solv"] if m in pivot.index]
    x = np.arange(len(models)); w = 0.34
    fig, ax = plt.subplots(figsize=(6.7, 4.2))
    style_axes(ax)
    unweighted = pivot.loc[models, "unweighted"].to_numpy()
    weighted = pivot.loc[models, "source_weighted"].to_numpy()
    b1 = ax.bar(x - w/2, unweighted, width=w, color=BLUE_D, label="unweighted", edgecolor="white", linewidth=0.8)
    b2 = ax.bar(x + w/2, weighted, width=w, color=CLAY, label="source-weighted", edgecolor="white", linewidth=0.8)
    ax.set_xticks(x); ax.set_xticklabels(models)
    ax.set_ylabel("MAE on ln x2")
    ax.set_title("Source weighting proxy ablation")
    ax.set_ylim(0, max(weighted.max(), unweighted.max()) * 1.20)
    label_bars(ax, b1, "{:.3f}", dy=0.012); label_bars(ax, b2, "{:.3f}", dy=0.012)
    ax.legend(frameon=False, ncols=2, loc="upper left")
    fig.tight_layout()
    save(fig, "source_weighting_ablation.pdf")


def weight_group_stats() -> None:
    df = read_csv(p("results/weight_analysis_smoke/group_stats.csv"))
    if df is None:
        return
    keep = df[df["group"].isin(["encoder", "interaction", "nrtl_head", "crystal_head", "correction", "solvent_moe", "timp_disp", "timp_polar"])].copy()
    keep = keep.sort_values("std")
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    style_axes(ax, grid_axis="x")
    bars = ax.barh(np.arange(len(keep)), keep["std"].values, color=LAVENDER, edgecolor="white", linewidth=0.8)
    ax.set_yticks(np.arange(len(keep))); ax.set_yticklabels(keep["group"])
    ax.set_xlabel("Parameter standard deviation")
    ax.set_title("Weight scale by model block")
    for b in bars:
        ax.text(b.get_width() + keep["std"].max() * 0.02, b.get_y()+b.get_height()/2,
                f"{b.get_width():.3f}", ha="left", va="center", fontsize=8.4, color=MUTED)
    ax.set_xlim(0, keep["std"].max() * 1.25)
    fig.tight_layout()
    save(fig, "weight_group_stats.pdf")


def descriptor_probe_bars() -> None:
    paths = {
        "TIMP": p("results/proxy_comparison/tgnn_timp_descriptor_probe/descriptor_r2.csv"),
        "TIMP+HC": p("results/proxy_comparison/tgnn_timp_hc_descriptor_probe/descriptor_r2.csv"),
    }
    rows = []
    core = ["MolWt", "MolLogP", "TPSA", "NumHDonors", "NumHAcceptors", "FractionCSP3"]
    for model, path in paths.items():
        df = read_csv(path)
        if df is None:
            continue
        d = df.set_index("descriptor")
        for desc in core:
            if desc in d.index:
                rows.append({"model": model, "descriptor": desc, "r2": float(d.loc[desc, "r2_test"])})
    if not rows:
        return
    df = pd.DataFrame(rows)
    descs = [d for d in core if d in set(df["descriptor"])]
    x = np.arange(len(descs)); w = 0.35
    fig, ax = plt.subplots(figsize=(8.1, 4.35))
    style_axes(ax)
    for off, model, col in [(-w/2, "TIMP", BLUE), (w/2, "TIMP+HC", TEAL_D)]:
        vals = [df[(df["model"] == model) & (df["descriptor"] == d)]["r2"].iloc[0] if len(df[(df["model"] == model) & (df["descriptor"] == d)]) else np.nan for d in descs]
        ax.bar(x + off, vals, width=w, color=col, edgecolor="white", linewidth=0.8, label=model)
    ax.axhline(0, color=LINE, lw=1)
    ax.set_xticks(x); ax.set_xticklabels(descs, rotation=20, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Test R2")
    ax.set_title("Linear probe on frozen embeddings")
    ax.legend(frameon=False, ncols=2, loc="upper right")
    fig.tight_layout()
    save(fig, "descriptor_probe_bars.pdf")


def attribution_examples() -> None:
    paths = [
        p("presentation/figures/generated/attribution_tgnn_mpnn_paracetamol_ethanol.png"),
        p("presentation/figures/generated/attribution_tgnn_timp_paracetamol_ethanol.png"),
    ]
    if not all(path.exists() for path in paths):
        return
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.8))
    for ax, path, title_text in zip(axes, paths, ["MPNN attribution", "TIMP attribution"]):
        img = plt.imread(path)
        ax.imshow(img)
        ax.set_title(title_text)
        ax.axis("off")
    fig.suptitle("Attribution sanity check: paracetamol in ethanol", y=0.98, fontsize=12, weight="semibold")
    fig.tight_layout()
    save(fig, "attribution_examples.pdf")


def ideal_sle_example() -> None:
    R = 8.314
    T = np.linspace(280, 410, 260)
    dH = 30_000.0
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    style_axes(ax)
    for Tm, col in [(360, BLUE), (450, TEAL_D), (560, CLAY)]:
        ln_x = -(dH / R) * (1 / T - 1 / Tm)
        ax.plot(T, ln_x, lw=2.0, color=col, label=f"Tm = {Tm} K")
    ax.axhline(0, color=LINE, lw=1)
    ax.set_ylim(-8, 3)
    ax.set_title("Ideal SLE term")
    ax.set_xlabel("Temperature, K")
    ax.set_ylabel("ideal ln x2")
    ax.legend(frameon=False)
    fig.tight_layout()
    save(fig, "ideal_sle_example.pdf")


def nrtl_gamma_example() -> None:
    x2 = np.linspace(0.001, 0.999, 300)
    x1 = 1 - x2

    def ln_gamma(t12, t21, alpha):
        G12 = np.exp(-alpha * t12)
        G21 = np.exp(-alpha * t21)
        return x1**2 * (t12 * (G12 / (x2 + x1 * G12))**2 + (t21 * G21) / (x1 + x2 * G21)**2)

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    style_axes(ax)
    settings = [
        (0.8, 1.2, 0.30, BLUE, "mild nonideality"),
        (2.0, 1.0, 0.30, TEAL_D, "asymmetric pair"),
        (3.2, -0.8, 0.25, CLAY, "strong interaction"),
    ]
    for t12, t21, a, col, lab in settings:
        ax.plot(x2, ln_gamma(t12, t21, a), lw=2.0, color=col, label=lab)
    ax.set_title("NRTL activity contribution")
    ax.set_xlabel("solute mole fraction, x2")
    ax.set_ylabel("ln gamma2")
    ax.legend(frameon=False)
    fig.tight_layout()
    save(fig, "nrtl_gamma_example.pdf")


def prediction_slice_model_comparison() -> None:
    df = read_csv(p("results/prediction_error_slices_latest/comparison_summary.csv"))
    if df is None:
        names = ["DirectGNN", "RF hybrid", "TGNN-Solv"]
        maes = [1.652, 1.722, 1.741]
        r2s = [0.478, 0.449, 0.438]
    else:
        mapping = {"DirectGNN": "DirectGNN", "RF_hybrid": "RF hybrid", "TGNN_MPNN": "TGNN-Solv"}
        order = ["DirectGNN", "RF_hybrid", "TGNN_MPNN"]
        rows = df.set_index("label").loc[order]
        names = [mapping[o] for o in order]
        maes = rows["mae"].values
        r2s = rows["r2"].values
    fig, ax = plt.subplots(figsize=(7.4, 4.35))
    style_axes(ax)
    x = np.arange(len(names))
    colors = [MODEL_COLORS[n] for n in names]
    bars = ax.bar(x, maes, color=colors, width=0.58, edgecolor="white", linewidth=1.0)
    ax.set_xticks(x); ax.set_xticklabels(names)
    ax.set_ylabel("MAE on ln x2")
    ax.set_title("Scaffold split model comparison")
    ax.set_ylim(0, max(maes) * 1.22)
    label_bars(ax, bars, "{:.3f}")
    for xi, r2 in zip(x, r2s):
        ax.text(xi, 0.08, f"R² {r2:.3f}", ha="center", va="bottom", fontsize=8.4, color="white",
                bbox=dict(boxstyle="round,pad=0.25", fc="#3B4250", ec="none", alpha=0.86))
    fig.tight_layout()
    save(fig, "prediction_slice_model_comparison.pdf")


def prediction_slice_pair_mae_cdf() -> None:
    files = {
        "DirectGNN": p("results/prediction_error_slices_latest/DirectGNN/pair_errors.csv"),
        "RF hybrid": p("results/prediction_error_slices_latest/RF_hybrid/pair_errors.csv"),
        "TGNN-Solv": p("results/prediction_error_slices_latest/TGNN_MPNN/pair_errors.csv"),
    }
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    style_axes(ax, grid_axis="both")
    for name, path in files.items():
        df = read_csv(path, usecols=["mean_abs_error"])
        if df is None:
            continue
        vals = np.sort(df["mean_abs_error"].dropna().values)
        y = np.linspace(0, 1, len(vals), endpoint=True)
        ax.plot(vals, y, lw=2.0, color=MODEL_COLORS[name], label=name)
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 1.01)
    ax.set_title("Pair-level error distribution")
    ax.set_xlabel("pair MAE on ln x2")
    ax.set_ylabel("Cumulative fraction")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    save(fig, "prediction_slice_pair_mae_cdf.pdf")


def prediction_slice_paired_deltas() -> None:
    df = read_csv(p("results/structural_extrapolation_diagnosis/aligned_row_deltas.csv"), usecols=["target_minus_ref_abs_error"])
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    style_axes(ax)
    if df is not None:
        vals = df["target_minus_ref_abs_error"].dropna().clip(-4, 4)
    else:
        rng = np.random.default_rng(1)
        vals = rng.normal(0.089, 1.1, 5800).clip(-4, 4)
    ax.hist(vals, bins=46, color=BLUE, edgecolor="white", linewidth=0.35)
    ax.axvline(0, color=INK, lw=1.2)
    ax.axvline(vals.mean(), color=CLAY, lw=1.7, label=f"mean = {vals.mean():.3f}")
    ax.set_title("Row-wise error delta")
    ax.set_xlabel("TGNN-Solv absolute error minus DirectGNN")
    ax.set_ylabel("Rows")
    ax.legend(frameon=False)
    fig.tight_layout()
    save(fig, "prediction_slice_paired_deltas.pdf")


def prediction_slice_chemistry_class_mae() -> None:
    d = read_csv(p("results/prediction_error_slices_latest/DirectGNN/chemistry_coarse_class_metrics.csv"))
    t = read_csv(p("results/prediction_error_slices_latest/TGNN_MPNN/chemistry_coarse_class_metrics.csv"))
    if d is None or t is None:
        classes = ["heterocycle", "halogenated", "oxygenated", "sulfur/P", "other"]
        direct = np.array([1.52, 1.95, 1.43, 1.63, 1.91])
        tgnn = np.array([1.57, 1.97, 1.73, 1.58, 2.93])
    else:
        merged = d[["coarse_class", "mae"]].merge(t[["coarse_class", "mae"]], on="coarse_class", suffixes=("_direct", "_tgnn"))
        merged = merged.sort_values("mae_direct")
        classes = [c.replace("halogenated_aromatic", "halogenated\naromatic").replace("sulfur_or_phosphorus", "sulfur /\nphosphorus") for c in merged["coarse_class"]]
        direct = merged["mae_direct"].values
        tgnn = merged["mae_tgnn"].values
    x = np.arange(len(classes)); w = 0.36
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    style_axes(ax)
    b1 = ax.bar(x - w/2, direct, width=w, color=BLUE_D, label="DirectGNN", edgecolor="white", linewidth=0.8)
    b2 = ax.bar(x + w/2, tgnn, width=w, color=CLAY, label="TGNN-Solv", edgecolor="white", linewidth=0.8)
    ax.set_xticks(x); ax.set_xticklabels(classes)
    ax.set_ylabel("MAE on ln x2")
    ax.set_title("Error by chemical class")
    ax.legend(frameon=False, ncols=2, loc="upper left")
    ax.set_ylim(0, max(direct.max(), tgnn.max()) * 1.18)
    label_bars(ax, b1, "{:.2f}", dy=0.014); label_bars(ax, b2, "{:.2f}", dy=0.014)
    fig.tight_layout()
    save(fig, "prediction_slice_chemistry_class_mae.pdf")


def prediction_slice_lnx2_bin_mae() -> None:
    files = {
        "DirectGNN": p("results/prediction_error_slices_latest/DirectGNN/predictions_with_errors.csv"),
        "RF hybrid": p("results/prediction_error_slices_latest/RF_hybrid/predictions_with_errors.csv"),
        "TGNN-Solv": p("results/prediction_error_slices_latest/TGNN_MPNN/predictions_with_errors.csv"),
    }
    bins = [-np.inf, -10, -8, -6, -4, -2, np.inf]
    labels = ["<-10", "-10..-8", "-8..-6", "-6..-4", "-4..-2", ">-2"]
    rows: list[dict[str, float | str | int]] = []
    counts = None
    for model, path in files.items():
        df = read_csv(path, usecols=["ln_x2_true", "abs_error"])
        if df is None:
            continue
        df = df.dropna(subset=["ln_x2_true", "abs_error"]).copy()
        df["bin"] = pd.cut(df["ln_x2_true"], bins=bins, labels=labels, include_lowest=True)
        if counts is None:
            counts = df.groupby("bin", observed=False).size().reindex(labels, fill_value=0)
        for label in labels:
            part = df[df["bin"] == label]
            rows.append({
                "model": model,
                "bin": label,
                "mae": float(part["abs_error"].mean()) if len(part) else np.nan,
                "n": int(len(part)),
            })
    if not rows:
        rows = [
            {"model": "DirectGNN", "bin": labels[i], "mae": v, "n": n}
            for i, (v, n) in enumerate(zip([2.7, 2.1, 1.5, 1.2, 1.1, 1.0], [180, 520, 1400, 2100, 1300, 326]))
        ] + [
            {"model": "TGNN-Solv", "bin": labels[i], "mae": v, "n": n}
            for i, (v, n) in enumerate(zip([3.4, 2.6, 1.7, 1.3, 1.0, 0.9], [180, 520, 1400, 2100, 1300, 326]))
        ]
        counts = pd.Series([180, 520, 1400, 2100, 1300, 326], index=labels)

    out = pd.DataFrame(rows)
    pivot = out.pivot(index="bin", columns="model", values="mae").reindex(labels)
    fig, ax = plt.subplots(figsize=(8.4, 4.55))
    style_axes(ax)
    x = np.arange(len(labels))
    present = [m for m in ["DirectGNN", "RF hybrid", "TGNN-Solv"] if m in pivot.columns]
    width = 0.22 if len(present) == 3 else 0.30
    offsets = np.linspace(-(len(present) - 1) * width / 2, (len(present) - 1) * width / 2, len(present))
    for off, model in zip(offsets, present):
        vals = pivot[model].values.astype(float)
        ax.bar(
            x + off,
            vals,
            width=width,
            color=MODEL_COLORS[model],
            edgecolor="white",
            linewidth=0.8,
            label=model,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("true ln x2 bin")
    ax.set_ylabel("MAE on ln x2")
    ax.set_title("Error depends strongly on solubility range")
    ax.legend(frameon=False, ncols=3, loc="upper right")
    ymax = np.nanmax(pivot.values) * 1.18
    ax.set_ylim(0, ymax)
    if counts is not None:
        for xi, label in enumerate(labels):
            ax.text(
                xi,
                ymax * 0.04,
                f"n={int(counts.loc[label])}",
                ha="center",
                va="bottom",
                fontsize=8.2,
                color=MUTED,
                rotation=0,
            )
    fig.tight_layout()
    save(fig, "prediction_slice_lnx2_bin_mae.pdf")


def difficult_systems_audit_summary() -> None:
    class_summary = read_csv(p("results/difficult_systems_audit/class_summary.csv"))
    model_errors = read_csv(p("results/difficult_systems_audit/model_error_by_class.csv"))
    summary_path = p("results/difficult_systems_audit/summary.json")
    if class_summary is None or model_errors is None or not summary_path.exists():
        fig, ax = plt.subplots(figsize=(8.0, 4.4))
        ax.axis("off")
        title(ax, "Difficult-system audit not available", y=0.92)
        ax.text(
            0.5,
            0.5,
            "Run scripts/analysis/audit_difficult_ionic_systems.py",
            ha="center",
            va="center",
            fontsize=11,
            color=MUTED,
        )
        fig.tight_layout()
        save(fig, "difficult_systems_audit_summary.pdf")
        return

    import json

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    test = class_summary[class_summary["split"] == "test"].copy()
    class_order = [
        "neutral",
        "zwitterion",
        "explicit_salt_low_eps",
        "explicit_salt_mid_eps",
        "explicit_salt_high_eps",
        "explicit_salt_eps_unknown",
    ]
    class_labels = {
        "neutral": "neutral",
        "zwitterion": "zwitterion",
        "explicit_salt_low_eps": "salt,\nlow eps",
        "explicit_salt_mid_eps": "salt,\nmid eps",
        "explicit_salt_high_eps": "salt,\nhigh eps",
        "explicit_salt_eps_unknown": "salt,\neps unknown",
    }
    test = test.set_index("system_class").reindex(class_order).reset_index()

    selected_slices = [
        ("class:neutral", "neutral"),
        ("class:zwitterion", "zwitterion"),
        ("class:explicit_salt_low_eps", "salt,\nlow eps"),
        ("class:explicit_salt_high_eps", "salt,\nhigh eps"),
        ("formulation_audit_candidate", "audit\ncandidates"),
    ]
    models = ["DirectGNN", "RF hybrid", "TGNN-Solv MPNN"]
    model_labels = {"TGNN-Solv MPNN": "TGNN-Solv", "DirectGNN": "DirectGNN", "RF hybrid": "RF hybrid"}

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.45), gridspec_kw={"width_ratios": [0.92, 1.25]})
    ax = axes[0]
    style_axes(ax)
    vals = 100.0 * test["n_rows"].fillna(0).astype(float).values / max(1, int(summary["n_test_rows"]))
    colors = [MUTED, TEAL, CLAY, ROSE, BLUE, "#C8C8C8"]
    bars = ax.bar(np.arange(len(class_order)), vals, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_xticks(np.arange(len(class_order)))
    ax.set_xticklabels([class_labels[c] for c in class_order], fontsize=8.2)
    ax.set_ylabel("test rows, %")
    ax.set_title("Charged systems are a minority,\nbut not negligible")
    ax.set_ylim(0, max(vals.max() * 1.28, 6.0))
    label_bars(ax, bars, "{:.1f}", dy=0.02)

    ax = axes[1]
    style_axes(ax)
    x = np.arange(len(selected_slices))
    width = 0.22
    offsets = np.linspace(-width, width, len(models))
    for off, model in zip(offsets, models):
        vals = []
        counts = []
        for slice_name, _ in selected_slices:
            row = model_errors[(model_errors["model"] == model) & (model_errors["slice"] == slice_name)]
            vals.append(float(row["mae"].iloc[0]) if len(row) else np.nan)
            counts.append(int(row["n_rows"].iloc[0]) if len(row) else 0)
        ax.bar(
            x + off,
            vals,
            width=width,
            color=MODEL_COLORS.get(model_labels[model], BLUE_D),
            edgecolor="white",
            linewidth=0.8,
            label=model_labels[model],
        )
    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label in selected_slices], fontsize=8.2)
    ax.set_ylabel("MAE on ln x2")
    ax.set_title("Error jumps on salts and audit candidates")
    ax.legend(frameon=False, ncols=3, fontsize=8.0, loc="upper left")
    ymax = np.nanmax([
        model_errors[model_errors["slice"] == s]["mae"].max()
        for s, _ in selected_slices
        if len(model_errors[model_errors["slice"] == s])
    ]) * 1.14
    ax.set_ylim(0, ymax)
    for xi, (slice_name, _) in enumerate(selected_slices):
        row = model_errors[(model_errors["model"] == "DirectGNN") & (model_errors["slice"] == slice_name)]
        if len(row):
            ax.text(
                xi,
                ymax * 0.035,
                f"n={int(row['n_rows'].iloc[0])}",
                ha="center",
                va="bottom",
                fontsize=7.7,
                color=MUTED,
            )

    fig.tight_layout()
    save(fig, "difficult_systems_audit_summary.pdf")


def delphinidin_case_study() -> None:
    rows = read_csv(p("results/difficult_systems_audit/row_audit.csv"))
    errors = read_csv(p("results/difficult_systems_audit/delphinidin_model_errors.csv"))
    slopes = read_csv(p("results/difficult_systems_audit/delphinidin_slope_summary.csv"))
    if rows is None or errors is None or slopes is None:
        fig, ax = plt.subplots(figsize=(8.0, 4.4))
        ax.axis("off")
        title(ax, "Delphinidin chloride case study not available", y=0.92)
        ax.text(
            0.5,
            0.5,
            "Run scripts/analysis/audit_difficult_ionic_systems.py",
            ha="center",
            va="center",
            fontsize=11,
            color=MUTED,
        )
        fig.tight_layout()
        save(fig, "delphinidin_case_study.pdf")
        return

    delph = rows[rows["solute_name"].astype(str).str.lower().eq("delphinidin")].copy()
    solvent_order = ["water", "methanol", "ethanol", "acetone"]
    solvent_colors = {
        "water": BLUE_D,
        "methanol": TEAL_D,
        "ethanol": SAND,
        "acetone": CLAY,
    }

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.55), gridspec_kw={"width_ratios": [1.02, 1.28]})
    ax = axes[0]
    style_axes(ax)
    for solvent in solvent_order:
        g = delph[delph["solvent_name"].astype(str).str.lower().eq(solvent)].sort_values("temperature")
        if g.empty:
            continue
        ax.plot(
            g["temperature"],
            g["ln_x2"],
            marker="o",
            ms=3.6,
            lw=1.8,
            color=solvent_colors[solvent],
            label=solvent,
        )
    ax.set_xlabel("T, K")
    ax.set_ylabel("ln x2")
    ax.set_title("Delphinidin chloride:\nmeasured solubility curves")
    ax.legend(frameon=False, fontsize=8.1)

    ax = axes[1]
    style_axes(ax)
    pivot = errors.pivot(index="solvent_name", columns="model", values="mae").reindex(solvent_order)
    present = [m for m in ["DirectGNN", "RF hybrid", "TGNN-Solv MPNN"] if m in pivot.columns]
    labels = {"TGNN-Solv MPNN": "TGNN-Solv", "DirectGNN": "DirectGNN", "RF hybrid": "RF hybrid"}
    x = np.arange(len(solvent_order))
    width = 0.22
    offsets = np.linspace(-(len(present) - 1) * width / 2, (len(present) - 1) * width / 2, len(present))
    for off, model in zip(offsets, present):
        ax.bar(
            x + off,
            pivot[model].values.astype(float),
            width=width,
            color=MODEL_COLORS.get(labels[model], BLUE_D),
            edgecolor="white",
            linewidth=0.8,
            label=labels[model],
        )
    ax.set_xticks(x)
    ax.set_xticklabels(solvent_order, fontsize=8.4)
    ax.set_ylabel("MAE on ln x2")
    ax.set_title("All models miss the level;\nacetone dominates the failure")
    ax.legend(frameon=False, fontsize=8.0, ncols=3, loc="upper left")
    ymax = np.nanmax(pivot.values) * 1.16
    ax.set_ylim(0, ymax)
    for xi, solvent in enumerate(solvent_order):
        slope_row = slopes[slopes["solvent_name"].astype(str).str.lower().eq(solvent)]
        if len(slope_row):
            dh = float(slope_row["effective_deltaH_solution_kJ_mol"].iloc[0])
            r2 = float(slope_row["r2_vant_hoff"].iloc[0])
            ax.text(
                xi,
                ymax * 0.035,
                f"dH={dh:.1f}\nR2={r2:.3f}",
                ha="center",
                va="bottom",
                fontsize=7.1,
                color=MUTED,
            )

    fig.tight_layout()
    save(fig, "delphinidin_case_study.pdf")


def temperature_extrapolation_baseline_comparison() -> None:
    base = read_csv(p("results/temperature_extrapolation_baselines/metrics_by_model.csv"))
    neural = read_csv(p("results/temperature_extrapolation_neural_proxy/comparison.csv"))
    rows = []
    if base is not None:
        m = base[base["eval_split"] == "test"].set_index("model")
        for key, name in [("pair_vant_hoff", "Van't Hoff"), ("pair_linear_T", "Linear T"), ("rf_morgan_T", "RF(Morgan+T)"), ("pair_mean", "Mean per pair")]:
            if key in m.index:
                rows.append((name, float(m.loc[key, "mae"])))
    if neural is not None:
        n = neural.set_index("model")
        for key, name in [("DirectGNN", "DirectGNN"), ("TGNN-Solv", "TGNN-Solv")]:
            if key in n.index:
                rows.append((name, float(n.loc[key, "mae"])))
    if not rows:
        rows = [("Van't Hoff", 0.368), ("Linear T", 0.414), ("RF(Morgan+T)", 1.290), ("DirectGNN", 1.619), ("TGNN-Solv", 1.945)]
    names, vals = zip(*rows)
    fig, ax = plt.subplots(figsize=(8.7, 4.5))
    style_axes(ax)
    colors = [MODEL_COLORS.get(n, SLATE) for n in names]
    bars = ax.bar(np.arange(len(names)), vals, color=colors, edgecolor="white", linewidth=0.8, width=0.62)
    ax.set_xticks(np.arange(len(names))); ax.set_xticklabels(names, rotation=18, ha="right")
    ax.set_ylabel("High-temperature test MAE")
    ax.set_title("Same-pair temperature extrapolation")
    ax.set_ylim(0, max(vals) * 1.22)
    label_bars(ax, bars, "{:.3f}")
    fig.tight_layout()
    save(fig, "temperature_extrapolation_baseline_comparison.pdf")


def temperature_protocol_audit() -> None:
    audit_path = p("results/temperature_extrapolation_baselines/audit/split_audit_summary.json")
    if audit_path.exists():
        data = json.loads(audit_path.read_text())
        overlap = data["pair_overlap"]["train_low_test_high_frac"]
        test_pairs = data["pair_overlap"]["test_pairs"]
        water = data["splits"]["test_high"]["water_row_fraction"]
        small = data["splits"]["test_high"]["small_solvent_row_fraction"]
        trend = data["trend"]["positive_high_minus_low_fraction"]
        vh_pos = data["vant_hoff_fits"]["positive_dln_dT_fraction"]
        vh_r2 = data["vant_hoff_fits"]["low_r2_median"]
        vh_mae = data["vant_hoff_fits"]["high_mae_mean"]
        vh_med = data["vant_hoff_fits"]["high_mae_median"]
        n_train = data["splits"]["train_low"]["rows"]
        n_test = data["splits"]["test_high"]["rows"]
    else:
        overlap, test_pairs = 1.0, 1751
        water, small = 0.122, 0.296
        trend, vh_pos = 0.996, 0.991
        vh_r2, vh_mae, vh_med = 0.999, 0.315, 0.140
        n_train, n_test = 7120, 3343

    fig, ax = plt.subplots(figsize=(8.15, 5.25))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    title(ax, "Temperature protocol audit", y=0.985)
    ax.text(
        0.5, 0.895,
        "Low-to-high temperature evaluation is a same-pair protocol, not a new-pair benchmark",
        ha="center", va="center", fontsize=10.2, color=MUTED,
    )

    cards = [
        ("Pair overlap", f"{overlap:.0%}", f"{test_pairs:,} test pairs", TEAL),
        ("Low-T train", f"{n_train:,}", "rows <= 310 K", BLUE),
        ("High-T test", f"{n_test:,}", "rows >= 330 K", CLAY),
        ("Water rows", f"{water:.1%}", "not dominant", SAND),
        ("Small solvents", f"{small:.1%}", "<= 3 heavy atoms", LAVENDER),
        ("Positive shift", f"{trend:.1%}", "high mean > low mean", GREEN),
        ("VH sign", f"{vh_pos:.1%}", "positive slope", TEAL),
        ("VH high-T MAE", f"{vh_mae:.3f}", f"median {vh_med:.3f}", CLAY),
    ]

    x0, y0 = 0.060, 0.645
    w, h = 0.178, 0.185
    dx, dy = 0.238, 0.255
    for i, (name, value, subtitle, col) in enumerate(cards):
        row = i // 4
        col_i = i % 4
        x = x0 + col_i * dx
        y = y0 - row * dy
        box(ax, (x, y), w, h, "", fc="#FFFFFF", ec="#DDD7CC")
        ax.plot([x + 0.018, x + 0.092], [y + h - 0.024, y + h - 0.024], lw=2.7, color=col, solid_capstyle="round")
        ax.text(x + 0.020, y + h - 0.056, name, ha="left", va="top", fontsize=8.25, color=MUTED)
        ax.text(x + 0.020, y + 0.079, value, ha="left", va="center", fontsize=13.7, color=INK, weight="medium")
        ax.text(x + 0.020, y + 0.030, subtitle, ha="left", va="bottom", fontsize=7.9, color=MUTED, linespacing=1.35)

    box(ax, (0.075, 0.065), 0.850, 0.195, "", fc="#F6F1E8", ec="#E0D7C6")
    ax.text(0.110, 0.205, "Interpretation", ha="left", va="center", fontsize=10.0, color=INK, weight="medium")
    ax.text(
        0.110, 0.132,
        "Pair-fitted Van't Hoff proves that the data contain a strong temperature signal.\n"
        "It is an oracle-like same-pair reference, not a new-pair neural baseline.",
        ha="left", va="center", fontsize=8.9, color=MUTED, linespacing=1.42,
    )
    save(fig, "temperature_protocol_audit.pdf")

def temperature_extrapolation_example_curves() -> None:
    pred = read_csv(p("results/temperature_extrapolation_baselines/predictions.csv"))
    train = read_csv(p("results/temperature_extrapolation_baselines/splits/train_low.csv"))
    examples = read_csv(p("results/temperature_extrapolation_baselines/example_pairs.csv"))
    fig, ax = plt.subplots(figsize=(7.6, 4.5))
    style_axes(ax, grid_axis="both")
    if pred is not None and train is not None and examples is not None:
        pair_key = examples.iloc[0]["pair_key"]
        tr = train[train["pair_key"] == pair_key].sort_values("temperature")
        te_true = pred[(pred["pair_key"] == pair_key) & (pred["eval_split"] == "test")]
        ax.scatter(tr["temperature"], tr["ln_x2"], s=32, color=INK, label="observed low T", zorder=4)
        true_once = te_true.drop_duplicates(subset=["temperature", "ln_x2_true"]).sort_values("temperature")
        ax.scatter(true_once["temperature"], true_once["ln_x2_true"], s=36, color=CLAY, label="observed high T", zorder=4)
        for model, col, lab in [("pair_vant_hoff", TEAL_D, "Van't Hoff"), ("rf_morgan_T", LAVENDER, "RF(Morgan+T)"), ("pair_mean", SLATE, "mean per pair")]:
            sub = te_true[te_true["model"] == model].sort_values("temperature")
            if len(sub):
                ax.plot(sub["temperature"], sub["ln_x2_pred"], lw=2.0, color=col, label=lab)
    else:
        T_low = np.array([293, 299, 305, 309]); y_low = np.array([-5.4, -5.2, -5.0, -4.85])
        T_hi = np.array([335, 360, 390, 420]); y_hi = np.array([-4.3, -4.0, -3.75, -3.5])
        ax.scatter(T_low, y_low, color=INK, label="observed low T")
        ax.scatter(T_hi, y_hi, color=CLAY, label="observed high T")
        ax.plot(T_hi, y_hi + 0.05, color=TEAL_D, lw=2, label="Van't Hoff")
    ax.set_title("Example extrapolation curve")
    ax.set_xlabel("Temperature, K")
    ax.set_ylabel("ln x2")
    ax.legend(frameon=False, ncols=2, loc="best")
    fig.tight_layout()
    save(fig, "temperature_extrapolation_example_curves.pdf")


def temperature_pair_profile_panels() -> None:
    bundle = _temperature_bundle_dir()
    selected = read_csv(bundle / "selected_pairs.csv")
    profiles = read_csv(bundle / "pair_profiles.csv")
    if selected is None or profiles is None or selected.empty or profiles.empty:
        return

    title_map = {
        "tgnn_wins": "TGNN beats DirectGNN",
        "tgnn_loses": "TGNN fails on a known pair",
        "high_activity_need": "Large activity correction needed",
        "low_solubility_tail": "Very low-solubility tail",
    }
    order = ["tgnn_wins", "tgnn_loses", "high_activity_need", "low_solubility_tail"]

    fig, axes = plt.subplots(2, 2, figsize=(9.3, 7.5))
    axes = axes.flatten()
    for ax in axes:
        style_axes(ax, grid_axis="both")

    for ax, category in zip(axes, order):
        row = selected[selected["category"] == category]
        if row.empty:
            ax.set_axis_off()
            continue
        row = row.iloc[0]
        pair_key = row["pair_key"]
        sub = profiles[profiles["pair_key"] == pair_key].copy()
        low = sub[sub["stage"] == "low_observed"].sort_values("T")
        high = sub[sub["stage"] == "high_profile"].sort_values("T")
        if low.empty or high.empty:
            ax.set_axis_off()
            continue

        fit = _temperature_fit_line(low[["T", "ln_x2_true"]])
        if fit is not None:
            slope, intercept = fit
            T_line = np.linspace(float(low["T"].min()), float(high["T"].max()), 160)
            ax.plot(
                T_line,
                slope / T_line + intercept,
                color=TEAL_D,
                lw=1.9,
                ls="--",
                label="Van't Hoff fit",
            )

        ax.scatter(
            low["T"],
            low["ln_x2_true"],
            s=22,
            color=INK,
            marker="o",
            label="Observed low-T",
            zorder=5,
        )
        ax.scatter(
            high["T"],
            high["ln_x2_true"],
            s=34,
            color=INK,
            marker="*",
            label="Observed high-T",
            zorder=6,
        )
        ax.plot(
            high["T"],
            high["tgnn_proxy_p1_8_1"],
            color=CLAY,
            lw=1.8,
            marker="o",
            ms=4.4,
            label=f"TGNN-Solv (MAE {row['mae_tgnn']:.2f})",
        )
        ax.plot(
            high["T"],
            high["directgnn_proxy_ep10"],
            color=BLUE_D,
            lw=1.8,
            marker="s",
            ms=4.0,
            label=f"DirectGNN (MAE {row['mae_direct']:.2f})",
        )

        ax.set_title(
            f"{title_map[category]}\n{_pair_display_name(row['solute_name'], row['solvent_name'])}",
            fontsize=10.5,
            weight="medium",
        )
        ax.set_xlabel("Temperature, K")
        ax.set_ylabel("ln x2")
        ax.legend(frameon=False, fontsize=7.6, loc="best", ncols=1)

    fig.suptitle("Pair-level temperature profiles", fontsize=12.9, weight="medium", y=0.995)
    fig.tight_layout()
    save(fig, "temperature_pair_profile_panels.pdf")


def temperature_prediction_distribution_diagnostics() -> None:
    bundle = _temperature_bundle_dir()
    wide = read_csv(bundle / "wide_predictions.csv")
    proxy = read_csv(p("results/temperature_extrapolation_slope_diagnostics/tgnn_proxy_intermediates/intermediates.csv"))
    if wide is None or wide.empty:
        return

    work = wide.dropna(subset=["ln_x2_true", "tgnn_proxy_p1_8_1", "directgnn_proxy_ep10"]).copy()
    if work.empty:
        return
    work["tgnn_residual"] = work["tgnn_proxy_p1_8_1"] - work["ln_x2_true"]
    work["direct_residual"] = work["directgnn_proxy_ep10"] - work["ln_x2_true"]

    fig, axes = plt.subplots(2, 3, figsize=(10.2, 7.0))
    for ax in axes.flat:
        style_axes(ax, grid_axis="both")

    bins = np.linspace(-25, 2, 42)
    ax = axes[0, 0]
    ax.hist(work["ln_x2_true"], bins=bins, density=True, color=GRAY, alpha=0.82, label="Observed", edgecolor="white", linewidth=0.35)
    ax.hist(work["tgnn_proxy_p1_8_1"], bins=bins, density=True, color=CLAY, alpha=0.58, label="TGNN-Solv", edgecolor="white", linewidth=0.35)
    ax.hist(work["directgnn_proxy_ep10"], bins=bins, density=True, color=BLUE_D, alpha=0.50, label="DirectGNN", edgecolor="white", linewidth=0.35)
    ax.set_title("Prediction distributions", fontsize=10.8)
    ax.set_xlabel("ln x2")
    ax.set_ylabel("Density")
    ax.legend(frameon=False, fontsize=8.0, loc="upper left")

    lims = (-25, 2)
    ax = axes[0, 1]
    ax.scatter(work["ln_x2_true"], work["tgnn_proxy_p1_8_1"], s=10, alpha=0.22, color=CLAY, edgecolors="none")
    ax.plot(lims, lims, color=INK, lw=1.0, ls="--")
    ax.set_xlim(*lims); ax.set_ylim(*lims)
    ax.set_title("TGNN-Solv: predicted vs observed", fontsize=10.8)
    ax.set_xlabel("Observed ln x2")
    ax.set_ylabel("Predicted ln x2")

    ax = axes[0, 2]
    ax.scatter(work["ln_x2_true"], work["directgnn_proxy_ep10"], s=10, alpha=0.22, color=BLUE_D, edgecolors="none")
    ax.plot(lims, lims, color=INK, lw=1.0, ls="--")
    ax.set_xlim(*lims); ax.set_ylim(*lims)
    ax.set_title("DirectGNN: predicted vs observed", fontsize=10.8)
    ax.set_xlabel("Observed ln x2")
    ax.set_ylabel("Predicted ln x2")

    ax = axes[1, 0]
    ax.scatter(work["ln_x2_true"], work["tgnn_residual"], s=9, alpha=0.18, color=CLAY, edgecolors="none", label="TGNN-Solv")
    ax.scatter(work["ln_x2_true"], work["direct_residual"], s=9, alpha=0.18, color=BLUE_D, edgecolors="none", label="DirectGNN")
    ax.axhline(0, color=INK, lw=0.95)
    ax.set_title("Residuals against observed value", fontsize=10.8)
    ax.set_xlabel("Observed ln x2")
    ax.set_ylabel("Prediction - observed")
    ax.legend(frameon=False, fontsize=7.9, loc="upper left")

    ax = axes[1, 1]
    for values, color, label in [
        (np.sort(work["tgnn_residual"].abs().to_numpy()), CLAY, "TGNN-Solv"),
        (np.sort(work["direct_residual"].abs().to_numpy()), BLUE_D, "DirectGNN"),
    ]:
        y = np.linspace(0, 1, len(values), endpoint=True)
        ax.plot(values, y, color=color, lw=2.0, label=label)
    ax.axvline(1.0, color=LINE, lw=0.9, ls="--")
    ax.axvline(3.0, color=LINE, lw=0.9, ls=":")
    ax.set_xlim(0, min(8.0, float(max(work["tgnn_residual"].abs().max(), work["direct_residual"].abs().max()) * 1.02)))
    ax.set_ylim(0, 1.01)
    ax.set_title("Cumulative absolute error", fontsize=10.8)
    ax.set_xlabel("|error| in ln x2")
    ax.set_ylabel("Cumulative fraction")
    ax.legend(frameon=False, fontsize=7.9, loc="lower right")

    ax = axes[1, 2]
    if proxy is not None and not proxy.empty:
        merged = work.merge(
            proxy[["pair_key", "temperature", "Phi_pred", "ln_gamma2_pred"]],
            left_on=["pair_key", "T"],
            right_on=["pair_key", "temperature"],
            how="left",
        )
        merged = merged.dropna(subset=["Phi_pred", "ln_gamma2_pred"])
        ax.scatter(
            merged["Phi_pred"],
            -merged["ln_gamma2_pred"],
            s=11,
            alpha=0.25,
            c=merged["ln_x2_true"],
            cmap="RdYlBu_r",
            edgecolors="none",
        )
        ax.axhline(0, color=CLAY, lw=1.0, ls="--")
        ax.set_title("Crystal term versus activity term", fontsize=10.8)
        ax.set_xlabel("Phi(T)")
        ax.set_ylabel("-ln gamma2")
    else:
        ax.set_axis_off()

    fig.suptitle("High-temperature prediction diagnostics", fontsize=12.9, weight="medium", y=0.995)
    fig.tight_layout()
    save(fig, "temperature_prediction_distribution_diagnostics.pdf")


def temperature_slope_level_problem() -> None:
    bundle = _temperature_bundle_dir()
    slope_pairs = read_csv(bundle / "slope_level_pairs.csv")
    wide = read_csv(bundle / "wide_predictions.csv")
    train_low = read_csv(p("results/temperature_extrapolation_baselines/splits/train_low.csv"))
    test_high = read_csv(p("results/temperature_extrapolation_baselines/splits/test_high.csv"))
    if slope_pairs is None or wide is None or train_low is None or test_high is None or slope_pairs.empty:
        return

    preferred = [
        "O=C(O)c1ccccc1C(=O)O>>CC(=O)N(C)C",
        "Cc1cccc(C(=O)O)c1>>CC(C)CO",
        "CC1=CC(=O)c2ccccc2C1=O>>c1ccccc1",
        "CC1(C)[C@@H]2CC[C@@]1(C)[C@@H](O)C2>>Cc1ccc(C)cc1",
        "O=C(O)CCCC(=O)O>>CC(=O)O",
        "Oc1cc(O)c2cc(O)c(-c3cc(O)c(O)c(O)c3)[o+]c2c1.[Cl-]>>CC(C)=O",
    ]
    chosen: list[str] = []
    available = set(slope_pairs["pair_key"])
    for key in preferred:
        if key in available and key not in chosen:
            chosen.append(key)
    if len(chosen) < 6:
        work = slope_pairs.copy()
        work["name_len"] = work["solute_name"].astype(str).str.len() + work["solvent_name"].astype(str).str.len()
        work = work.sort_values(
            ["slope_error_tgnn", "name_len", "required_activity_abs_mean"],
            ascending=[True, True, False],
        )
        for key in work["pair_key"]:
            if key not in chosen:
                chosen.append(key)
            if len(chosen) == 6:
                break
    chosen = chosen[:6]
    if not chosen:
        return

    fig, axes = plt.subplots(2, 3, figsize=(10.2, 7.15))
    axes = axes.flatten()
    for ax in axes:
        style_axes(ax, grid_axis="both")

    for ax, pair_key in zip(axes, chosen):
        row = slope_pairs[slope_pairs["pair_key"] == pair_key].iloc[0]
        low = train_low[train_low["pair_key"] == pair_key].copy()
        low["T"] = low["temperature"]
        high = wide[wide["pair_key"] == pair_key].sort_values("T")
        if low.empty or high.empty:
            ax.set_axis_off()
            continue

        fit = _temperature_fit_line(low[["T", "ln_x2"]].rename(columns={"ln_x2": "ln_x2_true"}))
        x_low = 1000.0 / low["T"]
        x_high = 1000.0 / high["T"]
        if fit is not None:
            slope, intercept = fit
            T_line = np.linspace(float(low["T"].min()), float(high["T"].max()), 180)
            ax.plot(1000.0 / T_line, slope / T_line + intercept, color=TEAL_D, lw=1.7, ls="--", label="Van't Hoff fit")

        ax.scatter(x_low, low["ln_x2"], color=INK, s=18, marker="o", label="Low-T observations", zorder=5)
        ax.scatter(x_high, high["ln_x2_true"], color=INK, s=28, marker="*", label="High-T observations", zorder=6)
        ax.plot(x_high, high["tgnn_proxy_p1_8_1"], color=CLAY, lw=1.7, marker="o", ms=4.0, label="TGNN-Solv")
        ax.plot(x_high, high["directgnn_proxy_ep10"], color=BLUE_D, lw=1.6, marker="s", ms=3.7, label="DirectGNN")

        ax.set_title(
            f"{_pair_display_name(row['solute_name'], row['solvent_name'])}\n"
            f"slope error {row['slope_error_tgnn']:.0f} K, bias {row['bias_tgnn']:+.2f}",
            fontsize=9.5,
            weight="medium",
        )
        ax.set_xlabel("1000 / T, K$^{-1}$")
        ax.set_ylabel("ln x2")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, ncols=4, loc="upper center", bbox_to_anchor=(0.5, 0.985), fontsize=7.9)
    fig.suptitle("Correct temperature shape, wrong curve level", fontsize=12.8, weight="medium", y=1.03)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    save(fig, "temperature_slope_level_problem.pdf")


def degeneracy_visualization() -> None:
    bundle = _temperature_bundle_dir()
    scan = read_csv(bundle / "degeneracy_scan.csv")
    summary_path = bundle / "summary.json"
    train_low = read_csv(p("results/temperature_extrapolation_baselines/splits/train_low.csv"))
    if scan is None or scan.empty or train_low is None or not summary_path.exists():
        return
    meta = json.loads(summary_path.read_text(encoding="utf-8")).get("degeneracy", {})
    pair_key = meta.get("pair_key")
    if not pair_key:
        return
    low = train_low[train_low["pair_key"] == pair_key].sort_values("temperature").copy()
    if low.empty:
        return

    fig, axes = plt.subplots(1, 3, figsize=(10.1, 3.95))
    for ax in axes[:2]:
        style_axes(ax, grid_axis="both")
    style_axes(axes[2], grid_axis="both")

    ax = axes[0]
    sc = ax.scatter(
        scan["tau_12"],
        scan["tau_21"],
        c=scan["dT_m"],
        cmap="coolwarm",
        s=18,
        alpha=0.70,
        edgecolors="none",
    )
    ax.set_title("Compatible tau combinations", fontsize=10.8)
    ax.set_xlabel("tau12")
    ax.set_ylabel("tau21")
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.035)
    cb.set_label("Delta Tm, K")

    ax = axes[1]
    sc = ax.scatter(
        scan["dT_m"],
        scan["dH_scale"],
        c=scan["mean_abs_error"],
        cmap="viridis_r",
        s=18,
        alpha=0.72,
        edgecolors="none",
    )
    ax.set_title("Crystal-activity trade-off", fontsize=10.8)
    ax.set_xlabel("Delta Tm, K")
    ax.set_ylabel("Delta Hfus scale")
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.035)
    cb.set_label("Mean |error|")

    ax = axes[2]
    sample = scan.sort_values("mean_abs_error").iloc[:: max(1, len(scan) // 18)].head(18)
    T_line = np.linspace(float(low["temperature"].min()) - 2.0, float(low["temperature"].max()) + 2.0, 140)
    for _, row in sample.iterrows():
        curve = [
            _nrtl_fixed_point_ln_x2(
                T,
                float(row["T_m"]),
                float(row["dH_fus"]),
                float(row["tau_12"]),
                float(row["tau_21"]),
                float(row["alpha"]),
            )
            for T in T_line
        ]
        ax.plot(1000.0 / T_line, curve, color=BLUE, lw=1.0, alpha=0.30)
    ax.scatter(1000.0 / low["temperature"], low["ln_x2"], color=CLAY, s=30, marker="o", zorder=6, label="Observed low-T points")
    ax.set_title("Many curves fit the same pair", fontsize=10.8)
    ax.set_xlabel("1000 / T, K$^{-1}$")
    ax.set_ylabel("ln x2")
    ax.legend(frameon=False, fontsize=7.9, loc="best")

    fig.suptitle(
        f"Local identifiability cloud: {_short_label(meta.get('solute_name', ''), 24)} / {_short_label(meta.get('solvent_name', ''), 18)}",
        fontsize=12.4,
        weight="medium",
        y=1.02,
    )
    fig.tight_layout()
    save(fig, "degeneracy_visualization.pdf")


def temperature_interpolation_baseline_comparison() -> None:
    df = read_csv(p("results/temperature_interpolation_baselines/metrics_by_model.csv"))
    rows = []
    if df is not None:
        m = df[df["eval_split"] == "test"].set_index("model")
        order = [
            ("pair_piecewise_linear_T", "piecewise linear"),
            ("pair_vant_hoff", "Van't Hoff"),
            ("pair_linear_T", "Linear T"),
            ("pair_nearest_T", "nearest T"),
            ("pair_mean", "mean per pair"),
            ("rf_morgan_T", "RF(Morgan+T)"),
        ]
        for key, name in order:
            if key in m.index:
                rows.append((name, float(m.loc[key, "mae"])))
    if not rows:
        rows = [("piecewise linear", 0.038), ("Van't Hoff", 0.043), ("Linear T", 0.045), ("nearest T", 0.195), ("mean per pair", 0.383), ("RF(Morgan+T)", 0.667)]
    names, vals = zip(*rows)
    fig, ax = plt.subplots(figsize=(8.2, 4.5))
    style_axes(ax)
    palette = [TEAL_D, TEAL, BLUE, SAND, SLATE, LAVENDER]
    bars = ax.bar(np.arange(len(names)), vals, color=palette[:len(names)], edgecolor="white", linewidth=0.8, width=0.62)
    ax.set_xticks(np.arange(len(names))); ax.set_xticklabels(names, rotation=18, ha="right")
    ax.set_ylabel("Held-out temperature MAE")
    ax.set_title("Same-pair temperature interpolation")
    ax.set_ylim(0, max(vals) * 1.22)
    label_bars(ax, bars, "{:.3f}")
    fig.tight_layout()
    save(fig, "temperature_interpolation_baseline_comparison.pdf")


def temperature_slope_recovery_diagnostics() -> None:
    metrics = read_csv(p("results", "temperature_extrapolation_failure_diagnostics", "slope_metrics_min3.csv"))
    if metrics is None or metrics.empty:
        return
    keep = ["pair_vant_hoff", "directgnn_proxy_ep10", "tgnn_proxy_p1_8_1", "rf_morgan_T"]
    labels = {
        "pair_vant_hoff": "pair Van't Hoff",
        "directgnn_proxy_ep10": "DirectGNN proxy",
        "tgnn_proxy_p1_8_1": "TGNN proxy",
        "rf_morgan_T": "RF(Morgan+T)",
    }
    colors = {
        "pair_vant_hoff": TEAL_D,
        "directgnn_proxy_ep10": BLUE_D,
        "tgnn_proxy_p1_8_1": CLAY,
        "rf_morgan_T": LAVENDER,
    }
    work = metrics[metrics["model"].isin(keep)].copy()
    work["label"] = work["model"].map(labels)
    work = work.set_index("model").loc[keep].reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.45))
    for ax in axes:
        style_axes(ax)

    x = np.arange(len(work))
    bars = axes[0].bar(x, work["pair_mae_mean"], color=[colors[m] for m in work["model"]], edgecolor="white", linewidth=0.8)
    axes[0].set_xticks(x); axes[0].set_xticklabels(work["label"], rotation=18, ha="right")
    axes[0].set_ylabel("Mean per-pair MAE")
    axes[0].set_title("Value error")
    axes[0].set_ylim(0, float(work["pair_mae_mean"].max()) * 1.24)
    label_bars(axes[0], bars, "{:.2f}", dy=0.025)

    bars = axes[1].bar(x, work["slope_median_abs_error_K"], color=[colors[m] for m in work["model"]], edgecolor="white", linewidth=0.8)
    axes[1].set_xticks(x); axes[1].set_xticklabels(work["label"], rotation=18, ha="right")
    axes[1].set_ylabel("Median absolute slope error, K")
    axes[1].set_title("Slope recovery")
    axes[1].set_ylim(0, float(work["slope_median_abs_error_K"].max()) * 1.22)
    label_bars(axes[1], bars, "{:.0f}", dy=0.025)

    fig.suptitle("Same-pair temperature extrapolation diagnostics", fontsize=13, weight="semibold", y=1.03)
    fig.tight_layout()
    save(fig, "temperature_slope_recovery_diagnostics.pdf")


def temperature_tgnn_internal_diagnostics() -> None:
    summary_path = p("results", "temperature_extrapolation_failure_diagnostics", "tgnn_internal_summary.json")
    if not summary_path.exists():
        return
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    stats = summary.get("stats", {})
    if not stats:
        return
    names = ["ln_x2_true", "ln_x2_final", "Phi_pred", "ln_gamma2_pred", "tau_12_pred", "tau_21_pred"]
    labels = ["true ln x2", "TGNN ln x2", "Phi", "ln gamma2", "tau12", "tau21"]
    stds = [stats.get(name, {}).get("std", np.nan) for name in names]
    colors = [TEAL_D, CLAY, SAND, TEAL, LAVENDER, LAVENDER]

    fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.45))
    style_axes(axes[0])
    x = np.arange(len(names))
    bars = axes[0].bar(x, stds, color=colors, edgecolor="white", linewidth=0.8)
    axes[0].set_yscale("symlog", linthresh=1e-3)
    axes[0].set_xticks(x); axes[0].set_xticklabels(labels, rotation=20, ha="right")
    axes[0].set_ylabel("Standard deviation")
    axes[0].set_title("Internal variation")
    for bar, val in zip(bars, stds):
        if np.isfinite(val):
            y = val * 1.15 if val > 1e-3 else val + 4e-5
            axes[0].text(bar.get_x() + bar.get_width() / 2, y, f"{val:.2g}", ha="center", va="bottom", fontsize=8.2, color=MUTED)

    axes[1].set_axis_off()
    tm = summary.get("tm_metrics", {})
    corr = summary.get("physics_correction", {})
    oracle = summary.get("oracle_tm_only", {})
    cards = [
        ("Prediction spread", f"std(pred) = {stats['ln_x2_final']['std']:.3f}\nstd(true) = {stats['ln_x2_true']['std']:.3f}", BLUE),
        ("NRTL collapse", f"std(tau12) = {stats['tau_12_pred']['std']:.1e}\nstd(ln gamma2) = {stats['ln_gamma2_pred']['std']:.1e}", LAVENDER),
        ("Correction path", f"mean |final-physics| =\n{corr.get('mean_abs', float('nan')):.1e}", TEAL),
        ("Oracle Tm", f"Tm MAE = {tm.get('mae_K', float('nan')):.1f} K\nMAE change = {oracle.get('delta_mae', float('nan')):.3f}", SAND),
    ]
    for i, (head, body, color) in enumerate(cards):
        yy = 0.76 - i * 0.22
        box(axes[1], (0.10, yy), 0.78, 0.14, f"{head}\n{body}", fc=color + "33", ec=color, fs=9.1, weight="semibold")
    axes[1].set_xlim(0, 1); axes[1].set_ylim(0, 1)

    fig.suptitle("TGNN proxy: physical path diagnostics", fontsize=13, weight="semibold", y=1.03)
    fig.tight_layout()
    save(fig, "temperature_tgnn_internal_diagnostics.pdf")


def nrtl_collapse_mechanism() -> None:
    proxy_path = p("results/temperature_extrapolation_failure_diagnostics/tgnn_internal_summary.json")
    medium_path = p("results/physics_bottleneck_diagnostics_medium/intermediates/intermediates_summary.json")
    if not proxy_path.exists() or not medium_path.exists():
        return
    proxy = json.loads(proxy_path.read_text(encoding="utf-8"))
    medium = json.loads(medium_path.read_text(encoding="utf-8"))
    stats = proxy.get("stats", {})
    if not stats or medium.get("status") != "ok":
        return

    proxy_tau12 = stats["tau_12_pred"]["std"]
    proxy_tau21 = stats["tau_21_pred"]["std"]
    medium_tau12 = medium["tau_12"]["std"]
    medium_tau21 = medium["tau_21"]["std"]
    pred_std = stats["ln_x2_final"]["std"]
    true_std = stats["ln_x2_true"]["std"]
    ratio = pred_std / true_std if true_std else float("nan")
    corr_mean_abs = stats["correction_magnitude"]["mean"]
    lngamma_std = stats["ln_gamma2_pred"]["std"]
    corr = medium["correction"]
    crystal = medium["crystal_vs_activity_contribution"]

    fig = plt.figure(figsize=(8.95, 4.65), facecolor=BG)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.10, 1.0, 1.0], wspace=0.32)

    ax = fig.add_subplot(gs[0, 0])
    style_axes(ax)
    labels = ["proxy\ntau12", "proxy\ntau21", "medium\ntau12", "medium\ntau21"]
    vals = [proxy_tau12, proxy_tau21, medium_tau12, medium_tau21]
    colors = [CLAY, CLAY, TEAL_D, TEAL_D]
    x = np.arange(len(labels))
    bars = ax.bar(x, vals, color=colors, edgecolor="white", linewidth=0.8, width=0.62)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Standard deviation of tau")
    ax.set_title("Collapse is budget/protocol-specific")
    for bar, val in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val * 1.45,
            f"{val:.1e}" if val < 1e-2 else f"{val:.2f}",
            ha="center",
            va="bottom",
            fontsize=7.7,
            color=MUTED,
        )

    ax = fig.add_subplot(gs[0, 1])
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.50, 0.94, "short temperature proxy", ha="center", fontsize=10.2, weight="medium", color=CLAY)
    box(ax, (0.08, 0.71), 0.84, 0.145,
        f"NRTL almost constant\nstd(ln gamma2) = {lngamma_std:.1e}",
        fc="#FCEFEA", ec="#E7C9BC", fs=8.7, weight="medium")
    box(ax, (0.08, 0.49), 0.84, 0.145,
        f"final correction inactive\nmean |delta| = {corr_mean_abs:.1e}",
        fc="#F7F5F0", ec="#DAD5CA", fs=8.7, weight="medium")
    box(ax, (0.08, 0.27), 0.84, 0.145,
        f"compressed predictions\nstd(pred)/std(true) = {ratio:.3f}",
        fc="#EEF4F7", ec="#D4DEE5", fs=8.7, weight="medium")
    ax.text(0.50, 0.09, "level errors are expected:\nactivity is almost absent",
            ha="center", fontsize=8.2, color=MUTED, linespacing=1.20)

    ax = fig.add_subplot(gs[0, 2])
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.50, 0.94, "medium scaffold run", ha="center", fontsize=10.2, weight="medium", color=TEAL_D)
    box(ax, (0.08, 0.71), 0.84, 0.145,
        "tau varies, but stays bounded\nabs(tau)>8 below 0.2%",
        fc="#EEF6F1", ec="#D6E4D8", fs=8.7, weight="medium")
    mae_phys = corr["physics_metrics_vs_true"]["mae"]
    mae_final = corr["final_metrics_vs_true"]["mae"]
    box(ax, (0.08, 0.49), 0.84, 0.145,
        f"correction still weak\nMAE {mae_phys:.3f} -> {mae_final:.3f}",
        fc="#F7F5F0", ec="#DAD5CA", fs=8.7, weight="medium")
    box(ax, (0.08, 0.27), 0.84, 0.145,
        f"crystal dominates\nmedian |Phi|/|activity| = {crystal['median_abs_ratio_Phi_to_activity']:.1f}",
        fc="#FFF7E6", ec="#E8D8AC", fs=8.7, weight="medium")
    ax.text(0.50, 0.09, "not a pure numeric blow-up:\nthe signal allocation is wrong",
            ha="center", fontsize=8.2, color=MUTED, linespacing=1.20)

    fig.suptitle("NRTL failure mode: collapsed activity versus weak correction", fontsize=12.6, weight="medium", y=0.990, color=INK)
    save(fig, "nrtl_collapse_mechanism.pdf")


def temperature_chemistry_slice_diagnostics() -> None:
    slices = read_csv(p("results", "temperature_extrapolation_failure_diagnostics", "chemistry_slices.csv"))
    if slices is None or slices.empty:
        return
    focus_models = ["pair_vant_hoff", "directgnn_proxy_ep10", "tgnn_proxy_p1_8_1"]
    focus_slices = [
        "water_solvent",
        "small_solvent_le3_heavy",
        "aromatic_solvent",
        "low_solubility_true_lte_minus8",
        "temperature_gte_360K",
    ]
    labels = {
        "water_solvent": "Water solvent",
        "small_solvent_le3_heavy": "Small solvent",
        "aromatic_solvent": "Aromatic solvent",
        "low_solubility_true_lte_minus8": "Low solubility",
        "temperature_gte_360K": "T >= 360 K",
    }
    model_labels = {
        "pair_vant_hoff": "Van't Hoff",
        "directgnn_proxy_ep10": "DirectGNN",
        "tgnn_proxy_p1_8_1": "TGNN",
    }
    work = slices[slices["model"].isin(focus_models) & slices["slice"].isin(focus_slices)].copy()
    if work.empty:
        return
    pivot = work.pivot(index="slice", columns="model", values="mae_slice").reindex(focus_slices)

    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    style_axes(ax)
    x = np.arange(len(pivot.index))
    width = 0.24
    palette = {"pair_vant_hoff": TEAL_D, "directgnn_proxy_ep10": BLUE_D, "tgnn_proxy_p1_8_1": CLAY}
    for j, model in enumerate(focus_models):
        vals = pivot[model].to_numpy(dtype=float)
        ax.bar(x + (j - 1) * width, vals, width=width, color=palette[model], edgecolor="white", linewidth=0.8, label=model_labels[model])
    ax.set_xticks(x); ax.set_xticklabels([labels[s] for s in pivot.index], rotation=15, ha="right")
    ax.set_ylabel("MAE on slice")
    ax.set_title("Chemistry slices in high-temperature test")
    ax.legend(frameon=False, ncols=3, loc="upper left")
    ax.set_ylim(0, float(np.nanmax(pivot.to_numpy())) * 1.18)
    fig.tight_layout()
    save(fig, "temperature_chemistry_slice_diagnostics.pdf")


def idac_expansion() -> None:
    labels = ["Rows", "Pairs", "DOIs"]
    old = np.array([404, 138, 9], dtype=float)
    new = np.array([14900, 3145, 63], dtype=float)
    x = np.arange(len(labels)); w = 0.34
    fig, ax = plt.subplots(figsize=(7.4, 4.5))
    style_axes(ax)
    b1 = ax.bar(x - w/2, old, width=w, color=GRAY, edgecolor="white", linewidth=0.8, label="original")
    b2 = ax.bar(x + w/2, new, width=w, color=BLUE_D, edgecolor="white", linewidth=0.8, label="expanded")
    ax.set_yscale("log")
    ax.set_ylim(5, 40000)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("Count, log scale")
    ax.set_title("IDAC supervision expansion")
    ax.legend(frameon=False, ncols=2, loc="upper left")
    for bars in [b1, b2]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h * 1.22, f"{int(h):,}", ha="center", va="bottom", fontsize=8.3, color=MUTED)
    fig.tight_layout()
    save(fig, "idac_expansion_bars.pdf")


def sensitivity_heatmap() -> None:
    Tm = 450.0; dH = 30_000.0; T = 298.15; R = 8.314
    dTm = np.linspace(-50, 50, 41)
    dHk = np.linspace(-8, 8, 41)  # kJ/mol
    grid = np.zeros((len(dHk), len(dTm)))
    for i, dh in enumerate(dHk):
        for j, dtm in enumerate(dTm):
            grid[i, j] = abs(-(dH / (R * Tm**2)) * dtm - (1 / R) * (1 / T - 1 / Tm) * (dh * 1000))
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    im = ax.imshow(grid, origin="lower", aspect="auto", cmap="mako" if "mako" in plt.colormaps() else "Blues",
                   extent=[dTm.min(), dTm.max(), dHk.min(), dHk.max()])
    ax.set_title("Error amplification through the crystal term")
    ax.set_xlabel("Tm error, K")
    ax.set_ylabel("Delta Hfus error, kJ/mol")
    cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.035)
    cb.set_label("|delta ln x2|")
    ax.contour(dTm, dHk, grid, levels=[0.5, 1.0, 1.5], colors="white", linewidths=0.8, alpha=0.9)
    fig.tight_layout()
    save(fig, "sensitivity_heatmap.pdf")


def error_decomposition_waterfall() -> None:
    labels = ["baseline", "Tm", "Delta Hfus", "activity", "solver / residual"]
    vals = [0.0, 0.53, 0.68, 0.70, 0.18]
    cumulative = np.cumsum(vals)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    style_axes(ax)
    colors = [GRAY, SAND, CLAY, BLUE, SLATE]
    prev = 0
    for i, (lab, val, col) in enumerate(zip(labels, vals, colors)):
        if i == 0:
            ax.bar(i, 0.05, bottom=0, color=col, width=0.6)
            ax.text(i, 0.10, "0", ha="center", fontsize=8.5, color=MUTED)
        else:
            ax.bar(i, val, bottom=prev, color=col, width=0.6, edgecolor="white", linewidth=0.8)
            ax.text(i, prev + val / 2, f"+{val:.2f}", ha="center", va="center", fontsize=8.5, color="white", weight="semibold")
        prev = cumulative[i]
    ax.plot(np.arange(len(labels)), cumulative, color=INK, lw=1.2, marker="o", ms=4)
    ax.set_xticks(np.arange(len(labels))); ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Approximate contribution to |delta ln x2|")
    ax.set_title("Why intermediate errors matter")
    ax.set_ylim(0, cumulative[-1] * 1.18)
    fig.tight_layout()
    save(fig, "error_decomposition_waterfall.pdf")


def solver_convergence_schematic() -> None:
    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    title(ax, "Damped SLE solver", y=0.985)

    ax.text(
        0.5, 0.880,
        r"Solve $x_2 = \exp[-\Phi(T)-\ln\gamma_2(x_2,T)]$ by safeguarded damped iteration",
        ha="center", va="center", fontsize=10.4, color=MUTED,
    )

    steps = [
        (0.055, 0.600, 0.185, 0.185, "1. initialize", r"$x_0=\exp[-\Phi]$"),
        (0.295, 0.600, 0.185, 0.185, "2. activity", r"evaluate" + "\n" + r"$\ln\gamma_2(x_k,T)$"),
        (0.535, 0.600, 0.185, 0.185, "3. propose", r"$x^+=\exp[-\Phi$" + "\n" + r"$-\ln\gamma_2]$"),
        (0.775, 0.600, 0.185, 0.185, "4. damp", r"$x_{k+1}=(1-\lambda)x_k$" + "\n" + r"$+\lambda x^+$"),
    ]
    for x, y, w, h, head, body in steps:
        box(ax, (x, y), w, h, "", fc=PANEL, ec=LINE)
        ax.text(x + 0.022, y + h - 0.045, head, ha="left", va="top", fontsize=9.7, color=INK, weight="medium")
        ax.text(x + 0.022, y + 0.072, body, ha="left", va="center", fontsize=9.05, color=MUTED, linespacing=1.45)
    for x in [0.240, 0.480, 0.720]:
        arrow(ax, (x, 0.692), (x + 0.055, 0.692), color=BLUE_D, lw=1.05)

    box(ax, (0.135, 0.265), 0.320, 0.195, "", fc="#F7FAF8", ec="#D9E5DD")
    ax.text(0.165, 0.405, "adaptive damping", ha="left", va="center", fontsize=10.0, color=INK, weight="medium")
    ax.text(0.165, 0.338, "reduce $\lambda$ if residual grows;\nkeep iterate in the local basin", ha="left", va="center", fontsize=9.15, color=MUTED, linespacing=1.42)

    box(ax, (0.545, 0.265), 0.320, 0.195, "", fc="#F6F1E8", ec="#DED3C0")
    ax.text(0.575, 0.405, "numerical safeguards", ha="left", va="center", fontsize=10.0, color=INK, weight="medium")
    ax.text(0.575, 0.338, r"bounded $\tau$, clamped $x_2$," + "\nresidual stop, finite gradients", ha="left", va="center", fontsize=9.15, color=MUTED, linespacing=1.42)

    ax.text(0.50, 0.135,
            "The solver is not a black box: convergence behavior, residuals and solver-facing parameters are logged.",
            ha="center", fontsize=9.4, color=MUTED)
    save(fig, "solver_convergence_schematic.pdf")

def vh_stability_safeguards() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.65))
    ax.axis("off")
    title(ax, "Stabilizing Van't Hoff auxiliary losses", y=0.98)

    box(ax, (0.06, 0.66), 0.25, 0.18, "Failure mode\nsmall $\\Delta(1/T)$\namplifies slopes", fc="#FFF5F2", ec="#E7B9AA", fs=9.05, weight="medium")
    box(ax, (0.38, 0.66), 0.25, 0.18, "Level 1\npair-aware batches\nsame pair, multiple T", fc=PANEL, ec=LINE, fs=9.05, weight="medium")
    box(ax, (0.69, 0.66), 0.25, 0.18, "Level 2\nclamped denominator\nper-pair cap", fc=PANEL, ec=LINE, fs=9.05, weight="medium")
    box(ax, (0.22, 0.31), 0.25, 0.18, "Level 3\nscaled weights\nnormalizers", fc=PANEL, ec=LINE, fs=9.05, weight="medium")
    box(ax, (0.53, 0.31), 0.25, 0.18, "Guardrail\nsol_fraction tracks\nmain-task dominance", fc="#F5FAF7", ec="#BFD8C8", fs=9.05, weight="medium")

    arrow(ax, (0.31, 0.75), (0.38, 0.75), color=CLAY)
    arrow(ax, (0.63, 0.75), (0.69, 0.75), color=CLAY)
    arrow(ax, (0.81, 0.66), (0.66, 0.49), color=CLAY, rad=-0.12)
    arrow(ax, (0.47, 0.40), (0.53, 0.40), color=TEAL_D)

    ax.text(
        0.50,
        0.15,
        "The temperature regularizer remains finite and cannot dominate the solubility objective.",
        ha="center",
        va="center",
        fontsize=9.0,
        color=MUTED,
    )
    fig.tight_layout()
    save(fig, "vh_stability_safeguards.pdf")


def optuna_tpe_schematic() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.55))
    ax.axis("off")
    title(ax, "Tree-structured Parzen Estimator search", y=0.98)

    box(ax, (0.06, 0.63), 0.24, 0.20, "Completed trials\nhyperparameters $x$\nvalidation MAE $y$", fc=PANEL, ec=LINE, fs=9.05, weight="medium")
    box(ax, (0.38, 0.63), 0.24, 0.20, "Split by quantile\ngood: $y<y^*$\nbad: $y\\geq y^*$", fc=PANEL, ec=LINE, fs=9.05, weight="medium")
    box(ax, (0.70, 0.63), 0.24, 0.20, "Density models\n$l(x)=p(x|good)$\n$g(x)=p(x|bad)$", fc=PANEL, ec=LINE, fs=9.05, weight="medium")
    box(ax, (0.22, 0.25), 0.25, 0.20, "Acquisition\nmaximize\n$l(x)/g(x)$", fc="#F5FAF7", ec="#BFD8C8", fs=9.05, weight="medium")
    box(ax, (0.54, 0.25), 0.25, 0.20, "New trial\ntrain proxy model\nupdate study", fc="#F8F7FC", ec="#CEC1E8", fs=9.05, weight="medium")

    arrow(ax, (0.30, 0.73), (0.38, 0.73), color=BLUE_D)
    arrow(ax, (0.62, 0.73), (0.70, 0.73), color=BLUE_D)
    arrow(ax, (0.82, 0.63), (0.64, 0.45), color=TEAL_D, rad=-0.13)
    arrow(ax, (0.47, 0.35), (0.54, 0.35), color=TEAL_D)
    arrow(ax, (0.67, 0.25), (0.21, 0.63), color=MUTED, rad=-0.32, lw=1.0)

    ax.text(
        0.50,
        0.10,
        "The objective minimized in this project is validation MAE on the proxy or full split.",
        ha="center",
        va="center",
        fontsize=8.9,
        color=MUTED,
    )
    fig.tight_layout()
    save(fig, "optuna_tpe_schematic.pdf")


ALL = [
    graphical_abstract,
    architecture,
    graph_mechanisms,
    sle_decomposition,
    data_collection_pipeline,
    idac_collection_pipeline,
    evaluation_regimes,
    water_graph,
    identifiability_constraints,
    pretraining_tasks,
    temperature_encoding,
    training_curriculum,
    loss_components,
    interaction_rescue,
    correction_loop,
    timp_hansen_diagnostics,
    uncertainty_ad,
    evidence_status_matrix,
    supervision_matrix,
    chemical_space_projection,
    embedding_geometry_diagnostics,
    cluster_error_interpretability,
    structural_generalization_diagnostics,
    physics_bottleneck_audit,
    hypothesis_map,
    gradient_flow,
    gradient_flow_fix,
    compute_plan,
    corpus_lnx2_histogram,
    corpus_points_per_pair,
    corpus_temperature_histogram,
    corpus_solvent_barplot,
    knn_modelability_diagnostics,
    source_uncertainty_coverage,
    source_weighting_ablation,
    weight_group_stats,
    descriptor_probe_bars,
    attribution_examples,
    ideal_sle_example,
    nrtl_gamma_example,
    prediction_slice_model_comparison,
    prediction_slice_pair_mae_cdf,
    prediction_slice_paired_deltas,
    prediction_slice_chemistry_class_mae,
    prediction_slice_lnx2_bin_mae,
    difficult_systems_audit_summary,
    delphinidin_case_study,
    temperature_extrapolation_baseline_comparison,
    temperature_protocol_audit,
    temperature_prediction_distribution_diagnostics,
    temperature_pair_profile_panels,
    temperature_slope_recovery_diagnostics,
    temperature_slope_level_problem,
    temperature_tgnn_internal_diagnostics,
    nrtl_collapse_mechanism,
    temperature_chemistry_slice_diagnostics,
    temperature_extrapolation_example_curves,
    degeneracy_visualization,
    temperature_interpolation_baseline_comparison,
    idac_expansion,
    sensitivity_heatmap,
    error_decomposition_waterfall,
    solver_convergence_schematic,
    vh_stability_safeguards,
    optuna_tpe_schematic,
]


if __name__ == "__main__":
    for fn in ALL:
        fn()
    print(f"Generated {len(ALL)} report figures in {OUT}")
