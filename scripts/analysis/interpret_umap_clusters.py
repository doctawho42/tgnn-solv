#!/usr/bin/env python
"""Interpret UMAP chemical-space clusters with coarse chemical classes.

The cluster assignments are produced by ``run_chemical_space_projection.py``.
This script adds a human-readable layer for the report: dominant chemistry,
test coverage, model-error pattern, and representative structures nearest to
each UMAP cluster centroid.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


RU_LABELS: dict[int, str] = {
    0: "ароматические сульфоны и амины",
    1: "азотсодержащие гетероароматы и карбонильные ароматические соединения",
    2: "гидрофобные ароматические амины с длинными алкильными фрагментами",
    3: "гидрокси-карбонильные кислоты, спирты и гибкие алифатические фрагменты",
    4: "нитроароматические амины и полярные нитросоединения",
    5: "малый тестовый кластер гидрофобных длинноцепочечных ароматических аминов",
    6: "ароматические карбонильные, фенольные и эфирные соединения",
    7: "крупные гибкие гидрокси- и эфирсодержащие молекулы с длинными цепями",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--projection",
        default="results/chemical_space_projection/chemical_space_projection.csv",
        help="CSV with solute UMAP coordinates and cluster assignments.",
    )
    parser.add_argument(
        "--profiles",
        default="results/chemical_space_projection/cluster_profiles.csv",
        help="Cluster profile CSV produced by run_chemical_space_projection.py.",
    )
    parser.add_argument(
        "--errors",
        default="results/chemical_space_projection/cluster_model_errors.csv",
        help="Cluster model-error CSV produced by run_chemical_space_projection.py.",
    )
    parser.add_argument(
        "--output-csv",
        default="results/chemical_space_projection/cluster_class_interpretation.csv",
    )
    parser.add_argument(
        "--output-md",
        default="results/chemical_space_projection/cluster_class_interpretation.md",
    )
    parser.add_argument("--n-representatives", type=int, default=3)
    return parser.parse_args()


def fmt_pct(x: float) -> str:
    return f"{100.0 * x:.0f}%"


def fmt_groups(row: pd.Series) -> str:
    group_cols = [c for c in row.index if c.startswith("fg_")]
    ranked = sorted(
        ((float(row[c]), c.replace("fg_", "")) for c in group_cols if pd.notna(row[c])),
        reverse=True,
    )
    return "; ".join(f"{name} {fmt_pct(frac)}" for frac, name in ranked[:4] if frac > 0.0)


def build_representatives(proj: pd.DataFrame, n: int) -> pd.DataFrame:
    coord_cols = ["umap_1", "umap_2"] if proj[["umap_1", "umap_2"]].notna().all().all() else ["pca_1", "pca_2"]
    rows: list[dict[str, object]] = []
    for cluster, group in proj.groupby("cluster", sort=True):
        coords = group[coord_cols].to_numpy(dtype=float)
        centroid = coords.mean(axis=0)
        dist = ((coords - centroid) ** 2).sum(axis=1)
        picked = group.assign(_dist=dist).sort_values(["_dist", "n_rows"], ascending=[True, False]).head(n)
        rows.append(
            {
                "cluster": int(cluster),
                "representative_smiles": " | ".join(picked["solute_smiles"].astype(str).tolist()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    projection = pd.read_csv(args.projection, low_memory=False)
    profiles = pd.read_csv(args.profiles, low_memory=False)
    errors = pd.read_csv(args.errors, low_memory=False)

    wide_errors = errors.pivot(index="cluster", columns="model", values="mae").reset_index()
    if {"TGNN_MPNN", "DirectGNN"}.issubset(wide_errors.columns):
        wide_errors["tgnn_minus_direct_mae"] = wide_errors["TGNN_MPNN"] - wide_errors["DirectGNN"]
    else:
        wide_errors["tgnn_minus_direct_mae"] = np.nan

    reps = build_representatives(projection, args.n_representatives)
    merged = profiles.merge(wide_errors, on="cluster", how="left").merge(reps, on="cluster", how="left")
    merged["chemical_class_ru"] = merged["cluster"].map(RU_LABELS).fillna(merged["cluster_label"])
    merged["dominant_features_ru"] = merged.apply(fmt_groups, axis=1)
    merged["model_pattern_ru"] = np.where(
        merged["tgnn_minus_direct_mae"] < -0.15,
        "TGNN-Solv заметно лучше DirectGNN",
        np.where(
            merged["tgnn_minus_direct_mae"] > 0.15,
            "TGNN-Solv заметно хуже DirectGNN",
            "разница TGNN-Solv и DirectGNN мала",
        ),
    )
    merged["caveat_ru"] = np.where(
        merged["n_solutes"] < 40,
        "малый кластер; вывод только диагностический",
        np.where(
            merged["test_fraction"] > 0.5,
            "кластер сильно представлен тестовыми веществами; нужна проверка устойчивости",
            "интерпретация устойчива как химический срез, но не как причинное доказательство",
        ),
    )

    columns = [
        "cluster",
        "n_solutes",
        "train_fraction",
        "val_fraction",
        "test_fraction",
        "mean_ln_x2_mean",
        "mol_logp_mean",
        "tpsa_mean",
        "chemical_class_ru",
        "dominant_features_ru",
        "DirectGNN",
        "TGNN_MPNN",
        "RF_hybrid",
        "tgnn_minus_direct_mae",
        "model_pattern_ru",
        "caveat_ru",
        "representative_smiles",
    ]
    final = merged[[c for c in columns if c in merged.columns]].sort_values("cluster")

    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(out_csv, index=False)

    out_md = Path(args.output_md)
    with out_md.open("w", encoding="utf-8") as fh:
        fh.write("# UMAP cluster chemical interpretation\n\n")
        fh.write(
            "| Cluster | N | Test frac. | Chemical class | Dominant features | "
            "TGNN-Direct MAE | Pattern |\n"
        )
        fh.write("|---:|---:|---:|---|---|---:|---|\n")
        for _, row in final.iterrows():
            fh.write(
                f"| C{int(row['cluster'])} | {int(row['n_solutes'])} | "
                f"{fmt_pct(float(row['test_fraction']))} | {row['chemical_class_ru']} | "
                f"{row['dominant_features_ru']} | "
                f"{float(row['tgnn_minus_direct_mae']):+.3f} | {row['model_pattern_ru']} |\n"
            )

    print(f"Wrote {out_csv}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
