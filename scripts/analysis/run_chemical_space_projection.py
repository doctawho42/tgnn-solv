#!/usr/bin/env python
"""Build a lightweight chemical-space projection for report diagnostics.

The script uses unique solute structures from the processed scaffold split,
computes Morgan fingerprints and simple RDKit descriptors, then writes PCA
coordinates. UMAP is optional and intentionally not required for reproducible
CPU-only runs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import Descriptors, rdFingerprintGenerator


RDLogger.DisableLog("rdApp.*")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-data", default="notebooks/data/processed/train.csv")
    parser.add_argument("--val-data", default="notebooks/data/processed/val.csv")
    parser.add_argument("--test-data", default="notebooks/data/processed/test.csv")
    parser.add_argument("--output-dir", default="results/chemical_space_projection")
    parser.add_argument("--max-train-solutes", type=int, default=2500)
    parser.add_argument("--n-bits", type=int, default=2048)
    parser.add_argument("--radius", type=int, default=2)
    parser.add_argument("--n-clusters", type=int, default=8)
    parser.add_argument("--prediction-root", default="results/prediction_error_slices_latest")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def load_unique_solutes(path: Path, split: str) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if "has_solubility" in df.columns:
        df = df[df["has_solubility"].fillna(True).astype(bool)]
    df = df.dropna(subset=["solute_smiles", "ln_x2"]).copy()
    stats = (
        df.groupby("solute_smiles", as_index=False)
        .agg(
            n_rows=("ln_x2", "size"),
            mean_ln_x2=("ln_x2", "mean"),
            min_ln_x2=("ln_x2", "min"),
            max_ln_x2=("ln_x2", "max"),
        )
    )
    stats["split"] = split
    return stats


FUNCTIONAL_GROUPS = {
    "aromatic": "a",
    "heteroaromatic_N": "[nH0,nH1]",
    "heteroaromatic_S": "[s]",
    "heteroaromatic_O": "[o]",
    "hydroxyl": "[OX2H]",
    "carboxyl": "C(=O)[OX2H1]",
    "amide": "C(=O)N",
    "ester": "C(=O)O[#6]",
    "carbonyl": "[CX3]=[OX1]",
    "ether": "[OD2]([#6])[#6]",
    "amine": "[NX3;H2,H1,H0;!$(NC=O)]",
    "halogen": "[F,Cl,Br,I]",
    "nitro": "[$([NX3](=O)=O),$([NX3+](=O)[O-])]",
    "nitrile": "C#N",
    "sulfone": "S(=O)(=O)",
    "thiol": "[SX2H]",
}


GROUP_PATTERNS = {
    name: Chem.MolFromSmarts(smarts)
    for name, smarts in FUNCTIONAL_GROUPS.items()
}


def morgan_bits(smiles: str, generator, n_bits: int) -> tuple[np.ndarray | None, dict | None]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None, None
    fp = generator.GetFingerprint(mol)
    arr = np.zeros((n_bits,), dtype=np.float32)
    DataStructs.ConvertToNumpyArray(fp, arr)
    desc = {
        "mol_logp": float(Descriptors.MolLogP(mol)),
        "tpsa": float(Descriptors.TPSA(mol)),
        "mol_wt": float(Descriptors.MolWt(mol)),
        "heavy_atoms": float(mol.GetNumHeavyAtoms()),
        "h_donors": float(Descriptors.NumHDonors(mol)),
        "h_acceptors": float(Descriptors.NumHAcceptors(mol)),
        "rotatable_bonds": float(Descriptors.NumRotatableBonds(mol)),
        "aromatic_rings": float(Descriptors.NumAromaticRings(mol)),
    }
    for name, patt in GROUP_PATTERNS.items():
        desc[f"fg_{name}"] = float(bool(patt is not None and mol.HasSubstructMatch(patt)))
    # Coarse shape flag useful for interpreting hydrophobic clusters.
    desc["fg_long_alkyl"] = float(bool(mol.HasSubstructMatch(Chem.MolFromSmarts("[CX4][CX4][CX4][CX4][CX4]"))))
    return arr, desc


def cluster_label(row: pd.Series, overall: pd.Series, group_cols: list[str]) -> str:
    enriched = []
    for col in group_cols:
        enrichment = float(row[col] - overall[col])
        if row[col] >= 0.35 and enrichment >= 0.12:
            enriched.append((enrichment, col.replace("fg_", "")))
    enriched = [name for _, name in sorted(enriched, reverse=True)[:2]]

    tags = []
    if row["mol_logp_mean"] >= overall["mol_logp_mean"] + 0.8:
        tags.append("hydrophobic")
    if row["tpsa_mean"] >= overall["tpsa_mean"] + 18:
        tags.append("polar")
    if row["heavy_atoms_mean"] >= overall["heavy_atoms_mean"] + 6:
        tags.append("large")
    tags.extend(enriched)
    if not tags:
        tags.append("mixed")
    return " / ".join(tags[:3])


def simple_kmeans(coords: np.ndarray, n_clusters: int, seed: int, n_iter: int = 80) -> np.ndarray:
    """Small deterministic k-means avoiding sklearn/joblib runtime issues."""
    rng = np.random.default_rng(seed)
    coords = np.asarray(coords, dtype=np.float32)
    if len(coords) < n_clusters:
        return np.arange(len(coords), dtype=int)
    centers = coords[rng.choice(len(coords), size=n_clusters, replace=False)].copy()
    labels = np.zeros(len(coords), dtype=int)
    for _ in range(n_iter):
        dist2 = ((coords[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = dist2.argmin(axis=1)
        new_centers = centers.copy()
        for k in range(n_clusters):
            mask = new_labels == k
            if mask.any():
                new_centers[k] = coords[mask].mean(axis=0)
            else:
                farthest = dist2.min(axis=1).argmax()
                new_centers[k] = coords[farthest]
                new_labels[farthest] = k
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        centers = new_centers
    return labels


def build_cluster_profiles(meta: pd.DataFrame, n_clusters: int, seed: int) -> pd.DataFrame:
    coord_cols = ["umap_1", "umap_2"] if meta["umap_1"].notna().all() else ["pca_1", "pca_2"]
    coords = meta[coord_cols].to_numpy(dtype=np.float32)
    labels = simple_kmeans(coords, n_clusters=n_clusters, seed=seed)
    meta["cluster"] = labels

    group_cols = [c for c in meta.columns if c.startswith("fg_")]
    agg = {
        "solute_smiles": "count",
        "mean_ln_x2": "mean",
        "mol_logp": "mean",
        "tpsa": "mean",
        "mol_wt": "mean",
        "heavy_atoms": "mean",
        "rotatable_bonds": "mean",
    }
    for col in group_cols:
        agg[col] = "mean"
    profiles = meta.groupby("cluster").agg(agg).reset_index()
    profiles = profiles.rename(
        columns={
            "solute_smiles": "n_solutes",
            "mean_ln_x2": "mean_ln_x2_mean",
            "mol_logp": "mol_logp_mean",
            "tpsa": "tpsa_mean",
            "mol_wt": "mol_wt_mean",
            "heavy_atoms": "heavy_atoms_mean",
            "rotatable_bonds": "rotatable_bonds_mean",
        }
    )
    split_counts = (
        meta.pivot_table(index="cluster", columns="split", values="solute_smiles", aggfunc="count", fill_value=0)
        .reset_index()
    )
    profiles = profiles.merge(split_counts, on="cluster", how="left")
    for split in ["train", "val", "test"]:
        if split not in profiles.columns:
            profiles[split] = 0
        profiles[f"{split}_fraction"] = profiles[split] / profiles["n_solutes"].clip(lower=1)

    overall = profiles.drop(columns=["cluster", "n_solutes", "train", "val", "test"], errors="ignore").mean(numeric_only=True)
    profiles["cluster_label"] = profiles.apply(cluster_label, axis=1, overall=overall, group_cols=group_cols)

    top_groups = []
    for _, row in profiles.iterrows():
        ranked = sorted(
            [(float(row[col]), col.replace("fg_", "")) for col in group_cols],
            reverse=True,
        )
        top_groups.append(", ".join(f"{name} {frac:.0%}" for frac, name in ranked[:4] if frac > 0))
    profiles["top_functional_groups"] = top_groups
    return profiles


def build_cluster_error_profiles(meta: pd.DataFrame, prediction_root: Path) -> pd.DataFrame:
    cluster_map = (
        meta.sort_values("split", key=lambda s: s.map({"test": 0, "val": 1, "train": 2}).fillna(3))
        .drop_duplicates("solute_smiles")
        [["solute_smiles", "cluster"]]
    )
    rows = []
    for model in ["DirectGNN", "TGNN_MPNN", "RF_hybrid"]:
        path = prediction_root / model / "predictions_with_errors.csv"
        if not path.exists():
            continue
        pred = pd.read_csv(path, low_memory=False)
        if "abs_error" not in pred.columns or "solute_smiles" not in pred.columns:
            continue
        joined = pred.merge(cluster_map, on="solute_smiles", how="left")
        joined = joined.dropna(subset=["cluster"])
        if joined.empty:
            continue
        grouped = joined.groupby("cluster").agg(
            n_rows=("abs_error", "size"),
            n_pairs=("pair_key", "nunique") if "pair_key" in joined.columns else ("abs_error", "size"),
            mae=("abs_error", "mean"),
            bias=("signed_error", "mean") if "signed_error" in joined.columns else ("abs_error", "mean"),
            low_solubility_fraction=("ln_x2_true", lambda x: float((x <= -8).mean())) if "ln_x2_true" in joined.columns else ("abs_error", "mean"),
        ).reset_index()
        grouped["model"] = model
        rows.append(grouped)
    if not rows:
        return pd.DataFrame()
    result = pd.concat(rows, ignore_index=True)
    result["cluster"] = result["cluster"].astype(int)
    return result


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    train = load_unique_solutes(Path(args.train_data), "train")
    val = load_unique_solutes(Path(args.val_data), "val")
    test = load_unique_solutes(Path(args.test_data), "test")

    if len(train) > args.max_train_solutes:
        train = train.sample(args.max_train_solutes, random_state=args.seed)

    df = pd.concat([train, val, test], ignore_index=True)
    df = df.drop_duplicates(subset=["solute_smiles", "split"]).reset_index(drop=True)

    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=args.radius,
        fpSize=args.n_bits,
    )

    fps: list[np.ndarray] = []
    rows: list[dict] = []
    invalid = 0
    for row in df.to_dict("records"):
        arr, desc = morgan_bits(row["solute_smiles"], generator, args.n_bits)
        if arr is None or desc is None:
            invalid += 1
            continue
        fps.append(arr)
        rows.append({**row, **desc})

    if not fps:
        raise RuntimeError("No valid solute structures were available for projection")

    X = np.vstack(fps)
    meta = pd.DataFrame(rows)

    scaler = StandardScaler(with_mean=True, with_std=True)
    X_scaled = scaler.fit_transform(X)
    pca = PCA(n_components=2, random_state=args.seed)
    coords = pca.fit_transform(X_scaled)
    meta["pca_1"] = coords[:, 0]
    meta["pca_2"] = coords[:, 1]
    pca_umap = PCA(n_components=min(50, X_scaled.shape[0] - 1, X_scaled.shape[1]), random_state=args.seed)
    X_umap_input = pca_umap.fit_transform(X_scaled)

    # Optional UMAP is deliberately best-effort. The report remains reproducible
    # without adding a new hard dependency to the project environment.
    umap_available = False
    try:
        import umap  # type: ignore

        reducer = umap.UMAP(
            n_neighbors=35,
            min_dist=0.12,
            metric="euclidean",
            random_state=args.seed,
        )
        umap_coords = reducer.fit_transform(X_umap_input)
        meta["umap_1"] = umap_coords[:, 0]
        meta["umap_2"] = umap_coords[:, 1]
        umap_available = True
    except Exception:
        meta["umap_1"] = np.nan
        meta["umap_2"] = np.nan

    profiles = build_cluster_profiles(meta, args.n_clusters, args.seed)
    error_profiles = build_cluster_error_profiles(meta, Path(args.prediction_root))

    csv_path = out_dir / "chemical_space_projection.csv"
    meta.to_csv(csv_path, index=False)
    profiles_path = out_dir / "cluster_profiles.csv"
    profiles.to_csv(profiles_path, index=False)
    error_profiles_path = out_dir / "cluster_model_errors.csv"
    error_profiles.to_csv(error_profiles_path, index=False)

    summary = {
        "n_valid": int(len(meta)),
        "n_invalid": int(invalid),
        "n_train": int((meta["split"] == "train").sum()),
        "n_val": int((meta["split"] == "val").sum()),
        "n_test": int((meta["split"] == "test").sum()),
        "n_bits": int(args.n_bits),
        "radius": int(args.radius),
        "pca_explained_variance_ratio": [float(x) for x in pca.explained_variance_ratio_],
        "pca_umap_input_variance_ratio_sum": float(pca_umap.explained_variance_ratio_.sum()),
        "umap_available": bool(umap_available),
        "n_clusters": int(args.n_clusters),
        "cluster_profiles_path": str(profiles_path),
        "cluster_model_errors_path": str(error_profiles_path),
        "mean_ln_x2_by_split": {
            split: float(group["mean_ln_x2"].mean())
            for split, group in meta.groupby("split")
        },
        "cluster_labels": {
            str(int(row["cluster"])): row["cluster_label"]
            for _, row in profiles.iterrows()
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Wrote {csv_path}")
    print(f"Wrote {profiles_path}")
    print(f"Wrote {error_profiles_path}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
