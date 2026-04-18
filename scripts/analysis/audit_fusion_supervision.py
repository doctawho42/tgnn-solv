#!/usr/bin/env python3
"""Audit crystal-property supervision for entropy-coupled FusionHead runs.

The audit is intentionally CPU-only. It quantifies how much direct supervision
is available for `T_m`, `dH_fus`, and the derived entropy of fusion
`dS_fus = dH_fus / T_m` in the maintained processed splits.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors
except ImportError as exc:  # pragma: no cover
    raise SystemExit("RDKit is required for this audit.") from exc


DEFAULT_SPLITS = (
    "train.csv",
    "val.csv",
    "test.csv",
    "train_solute.csv",
    "val_solute.csv",
    "test_solute.csv",
    "train_solvent.csv",
    "val_solvent.csv",
    "test_solvent.csv",
)


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    values = frame[column]
    if values.dtype == bool:
        return values.fillna(False)
    return values.astype(str).str.lower().isin({"true", "1", "yes"})


def _finite_numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index)
    values = pd.to_numeric(frame[column], errors="coerce")
    return values.where(np.isfinite(values))


def _safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return _safe_float(value)
    if isinstance(value, float):
        return _safe_float(value)
    return value


def _describe(values: pd.Series) -> dict[str, Any]:
    values = pd.to_numeric(values, errors="coerce").dropna()
    values = values[np.isfinite(values)]
    if values.empty:
        return {"n": 0}
    return {
        "n": int(len(values)),
        "mean": float(values.mean()),
        "std": float(values.std(ddof=0)),
        "median": float(values.median()),
        "p10": float(values.quantile(0.10)),
        "p90": float(values.quantile(0.90)),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def load_splits(processed_dir: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for name in DEFAULT_SPLITS:
        path = processed_dir / name
        if path.exists():
            frames[path.stem] = pd.read_csv(path, low_memory=False)
    return frames


def add_masks_and_entropy(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["has_T_m_bool"] = _bool_series(frame, "has_T_m")
    frame["has_dH_fus_bool"] = _bool_series(frame, "has_dH_fus")
    frame["T_m_numeric"] = _finite_numeric(frame, "T_m")
    frame["dH_fus_numeric"] = _finite_numeric(frame, "dH_fus")
    both = (
        frame["has_T_m_bool"]
        & frame["has_dH_fus_bool"]
        & frame["T_m_numeric"].gt(0.0)
        & frame["dH_fus_numeric"].gt(0.0)
    )
    frame["has_fusion_pair_bool"] = both
    frame["dS_fus_numeric"] = np.nan
    frame.loc[both, "dS_fus_numeric"] = (
        frame.loc[both, "dH_fus_numeric"] / frame.loc[both, "T_m_numeric"]
    )
    return frame


def summarize_split(
    split: str,
    frame: pd.DataFrame,
    *,
    walden_min: float,
    walden_max: float,
) -> dict[str, Any]:
    frame = add_masks_and_entropy(frame)
    sup_mask = _bool_series(frame, "has_solubility")
    both = frame["has_fusion_pair_bool"]
    entropy = frame.loc[both, "dS_fus_numeric"]
    outside = entropy.lt(walden_min) | entropy.gt(walden_max)
    return {
        "split": split,
        "rows": int(len(frame)),
        "supervised_solubility_rows": int(sup_mask.sum()),
        "unique_solutes": int(frame["solute_smiles"].nunique()),
        "T_m_rows": int(frame["has_T_m_bool"].sum()),
        "T_m_unique_solutes": int(
            frame.loc[frame["has_T_m_bool"], "solute_smiles"].nunique()
        ),
        "dH_fus_rows": int(frame["has_dH_fus_bool"].sum()),
        "dH_fus_unique_solutes": int(
            frame.loc[frame["has_dH_fus_bool"], "solute_smiles"].nunique()
        ),
        "paired_Tm_dH_rows": int(both.sum()),
        "paired_Tm_dH_unique_solutes": int(frame.loc[both, "solute_smiles"].nunique()),
        "paired_Tm_dH_row_fraction": float(both.mean()) if len(frame) else 0.0,
        "dS_fus_mean": _safe_float(entropy.mean()),
        "dS_fus_median": _safe_float(entropy.median()),
        "dS_fus_p10": _safe_float(entropy.quantile(0.10)) if len(entropy) else None,
        "dS_fus_p90": _safe_float(entropy.quantile(0.90)) if len(entropy) else None,
        "walden_outside_fraction": (
            float(outside.mean()) if len(outside) else None
        ),
    }


def molecule_features(smiles: str) -> dict[str, Any]:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return {"valid_mol": False}
    return {
        "valid_mol": True,
        "heavy_atoms": int(mol.GetNumHeavyAtoms()),
        "rotatable_bonds": int(rdMolDescriptors.CalcNumRotatableBonds(mol)),
        "rings": int(rdMolDescriptors.CalcNumRings(mol)),
        "aromatic_rings": int(rdMolDescriptors.CalcNumAromaticRings(mol)),
        "hetero_atoms": int(rdMolDescriptors.CalcNumHeteroatoms(mol)),
        "mol_wt": float(Descriptors.MolWt(mol)),
        "tpsa": float(Descriptors.TPSA(mol)),
        "mol_logp": float(Descriptors.MolLogP(mol)),
    }


def build_entropy_by_solute(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for split, frame in frames.items():
        enriched = add_masks_and_entropy(frame)
        paired = enriched[enriched["has_fusion_pair_bool"]].copy()
        if paired.empty:
            continue
        grouped = (
            paired.groupby("solute_smiles", as_index=False)
            .agg(
                split=("solute_smiles", lambda _x, split=split: split),
                solute_name=("solute_name", "first"),
                n_rows=("solute_smiles", "size"),
                T_m=("T_m_numeric", "mean"),
                dH_fus=("dH_fus_numeric", "mean"),
                dS_fus=("dS_fus_numeric", "mean"),
            )
        )
        rows.append(grouped)
    if not rows:
        return pd.DataFrame()
    result = pd.concat(rows, ignore_index=True)
    feature_rows = [molecule_features(smi) for smi in result["solute_smiles"]]
    features = pd.DataFrame(feature_rows)
    return pd.concat([result, features], axis=1)


def descriptor_correlations(entropy_by_solute: pd.DataFrame) -> pd.DataFrame:
    if entropy_by_solute.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    descriptors = [
        "heavy_atoms",
        "rotatable_bonds",
        "rings",
        "aromatic_rings",
        "hetero_atoms",
        "mol_wt",
        "tpsa",
        "mol_logp",
    ]
    for split, group in entropy_by_solute.groupby("split"):
        for descriptor in descriptors:
            subset = group[["dS_fus", descriptor]].dropna()
            subset = subset[np.isfinite(subset["dS_fus"]) & np.isfinite(subset[descriptor])]
            if len(subset) < 3:
                continue
            rows.append(
                {
                    "split": split,
                    "descriptor": descriptor,
                    "n": int(len(subset)),
                    "pearson": float(subset["dS_fus"].corr(subset[descriptor], method="pearson")),
                    "spearman": float(subset["dS_fus"].corr(subset[descriptor], method="spearman")),
                }
            )
    return pd.DataFrame(rows).sort_values(["split", "descriptor"])


def write_summary_md(
    path: Path,
    split_summary: pd.DataFrame,
    entropy_by_solute: pd.DataFrame,
    correlations: pd.DataFrame,
    *,
    walden_min: float,
    walden_max: float,
) -> None:
    canonical = split_summary[split_summary["split"].isin(["train", "val", "test"])]
    lines = [
        "# Fusion Supervision Audit",
        "",
        f"- Walden audit interval: `{walden_min:.1f}` to `{walden_max:.1f}` J/(mol*K).",
        "- `dS_fus` is derived as `dH_fus / T_m` for rows with both direct labels.",
        "- This audit does not train a model; it checks whether the entropy-coupled",
        "  crystal branch has enough existing supervision to be meaningful.",
        "",
        "## Canonical Splits",
        "",
        "| Split | Rows | Unique solutes | Tm rows | dH rows | paired rows | paired solutes | median dS | outside Walden |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in canonical.to_dict("records"):
        outside = row.get("walden_outside_fraction")
        outside_text = "n/a" if outside is None else f"{float(outside):.3f}"
        median = row.get("dS_fus_median")
        median_text = "n/a" if median is None else f"{float(median):.2f}"
        lines.append(
            "| {split} | {rows} | {unique} | {tm} | {dh} | {both} | {both_u} | {median} | {outside} |".format(
                split=row["split"],
                rows=row["rows"],
                unique=row["unique_solutes"],
                tm=row["T_m_rows"],
                dh=row["dH_fus_rows"],
                both=row["paired_Tm_dH_rows"],
                both_u=row["paired_Tm_dH_unique_solutes"],
                median=median_text,
                outside=outside_text,
            )
        )
    lines.extend(["", "## Derived Entropy By Solute", ""])
    if entropy_by_solute.empty:
        lines.append("- No paired `T_m`/`dH_fus` labels were found.")
    else:
        unique = entropy_by_solute.drop_duplicates(["split", "solute_smiles"])
        canonical_unique = unique[unique["split"].isin(["train", "val", "test"])]
        lines.append(f"- Unique split-solute entropy records: `{len(unique)}`")
        lines.append(
            f"- Canonical train/val/test split-solute entropy records: `{len(canonical_unique)}`"
        )
        lines.append(
            f"- Overall median `dS_fus`: `{unique['dS_fus'].median():.2f}` J/(mol*K)"
        )
        if not canonical_unique.empty:
            lines.append(
                f"- Canonical train/val/test median `dS_fus`: `{canonical_unique['dS_fus'].median():.2f}` J/(mol*K)"
            )
        lines.append(
            f"- Overall p10/p90 `dS_fus`: `{unique['dS_fus'].quantile(0.10):.2f}` / `{unique['dS_fus'].quantile(0.90):.2f}`"
        )
        outside = unique["dS_fus"].lt(walden_min) | unique["dS_fus"].gt(walden_max)
        lines.append(f"- Unique records outside Walden interval: `{outside.mean():.3f}`")
    lines.extend(["", "## Strongest dS Descriptor Correlations", ""])
    if correlations.empty:
        lines.append("- Not enough paired labels for descriptor correlations.")
    else:
        strongest = correlations.reindex(
            correlations["spearman"].abs().sort_values(ascending=False).index
        ).head(12)
        lines.extend(
            [
                "| Split | Descriptor | n | Pearson | Spearman |",
                "|---|---|---:|---:|---:|",
            ]
        )
        for row in strongest.to_dict("records"):
            lines.append(
                f"| {row['split']} | {row['descriptor']} | {row['n']} | "
                f"{row['pearson']:.3f} | {row['spearman']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `T_m` supervision is much denser than `dH_fus` supervision; entropy coupling",
            "  is therefore a structural regularizer, not a replacement for more fusion",
            "  enthalpy data.",
            "- If full runs use `fusion_output_mode='entropy_coupled'`, compare both",
            "  `T_m` MAE and `dH_fus` MAE against the direct fusion head, not only",
            "  final `ln_x2` MAE.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("notebooks/data/processed"),
        help="Directory with processed split CSV files.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("results/fusion_supervision_audit"),
        help="Output directory for CSV/JSON/Markdown artifacts.",
    )
    parser.add_argument("--walden-min", type=float, default=20.0)
    parser.add_argument("--walden-max", type=float, default=150.0)
    args = parser.parse_args()

    frames = load_splits(args.processed_dir)
    if not frames:
        raise SystemExit(f"No split CSV files found under {args.processed_dir}")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    split_summary = pd.DataFrame(
        [
            summarize_split(
                split,
                frame,
                walden_min=args.walden_min,
                walden_max=args.walden_max,
            )
            for split, frame in sorted(frames.items())
        ]
    )
    entropy_by_solute = build_entropy_by_solute(frames)
    correlations = descriptor_correlations(entropy_by_solute)

    split_summary.to_csv(args.out_dir / "split_summary.csv", index=False)
    entropy_by_solute.to_csv(args.out_dir / "entropy_by_solute.csv", index=False)
    correlations.to_csv(args.out_dir / "descriptor_correlations.csv", index=False)

    canonical = split_summary[split_summary["split"].isin(["train", "val", "test"])]
    summary = {
        "processed_dir": str(args.processed_dir),
        "walden_interval": [args.walden_min, args.walden_max],
        "n_splits": int(len(split_summary)),
        "canonical_split_summary": canonical.to_dict("records"),
        "all_split_summary": split_summary.to_dict("records"),
        "entropy_by_solute": _describe(entropy_by_solute.get("dS_fus", pd.Series(dtype=float))),
        "descriptor_correlations_top_abs_spearman": (
            correlations.reindex(
                correlations["spearman"].abs().sort_values(ascending=False).index
            )
            .head(12)
            .to_dict("records")
            if not correlations.empty
            else []
        ),
    }
    (args.out_dir / "summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )
    write_summary_md(
        args.out_dir / "SUMMARY.md",
        split_summary,
        entropy_by_solute,
        correlations,
        walden_min=args.walden_min,
        walden_max=args.walden_max,
    )


if __name__ == "__main__":
    main()
