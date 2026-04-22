#!/usr/bin/env python
"""Build UMAP/PCA diagnostics for saved TGNN-Solv molecular representations."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors


RDLogger.DisableLog("rdApp.*")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--train-embeddings",
        default="results/medium_budget/per_model/tgnn_tuned/descriptor_probe/train_solute_embeddings.npz",
    )
    parser.add_argument(
        "--test-embeddings",
        default="results/medium_budget/per_model/tgnn_tuned/descriptor_probe/test_solute_embeddings.npz",
    )
    parser.add_argument("--output-dir", default="results/embedding_interpretability/tgnn_tuned_medium")
    parser.add_argument("--max-train", type=int, default=3000)
    parser.add_argument("--max-test", type=int, default=2500)
    parser.add_argument("--n-clusters", type=int, default=8)
    parser.add_argument(
        "--use-umap",
        action="store_true",
        help="Attempt UMAP on embeddings. Off by default because this environment segfaults in numba/umap on the saved TGNN vectors.",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def load_npz_compat(path: Path) -> dict[str, np.ndarray]:
    # Some artifacts were created under a newer NumPy namespace.
    sys.modules.setdefault("numpy._core", np.core)
    sys.modules.setdefault("numpy._core.multiarray", np.core.multiarray)
    sys.modules.setdefault("numpy._core.numeric", np.core.numeric)
    z = np.load(path, allow_pickle=True)
    return {key: z[key] for key in z.files}


def descriptor_row(smiles: str) -> dict[str, float]:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return {
            "mol_logp": np.nan,
            "tpsa": np.nan,
            "mol_wt": np.nan,
            "heavy_atoms": np.nan,
            "aromatic_rings": np.nan,
        }
    return {
        "mol_logp": float(Descriptors.MolLogP(mol)),
        "tpsa": float(Descriptors.TPSA(mol)),
        "mol_wt": float(Descriptors.MolWt(mol)),
        "heavy_atoms": float(mol.GetNumHeavyAtoms()),
        "aromatic_rings": float(Descriptors.NumAromaticRings(mol)),
    }


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


def main() -> None:
    args = parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    train = load_npz_compat(Path(args.train_embeddings))
    test = load_npz_compat(Path(args.test_embeddings))

    train_emb = train["embeddings"]
    test_emb = test["embeddings"]
    train_idx = rng.choice(len(train_emb), size=min(args.max_train, len(train_emb)), replace=False)
    test_idx = rng.choice(len(test_emb), size=min(args.max_test, len(test_emb)), replace=False)

    X = np.vstack([train_emb[train_idx], test_emb[test_idx]]).astype(np.float32)
    smiles = [str(x) for x in np.concatenate([train["smiles"][train_idx], test["smiles"][test_idx]]).tolist()]
    split = ["train"] * len(train_idx) + ["test"] * len(test_idx)

    X_scaled = StandardScaler().fit_transform(X)
    pca50 = PCA(n_components=min(50, X_scaled.shape[0] - 1, X_scaled.shape[1]), random_state=args.seed)
    X_reduced = pca50.fit_transform(X_scaled)
    pca2 = PCA(n_components=2, random_state=args.seed)
    pca_coords = pca2.fit_transform(X_scaled)

    if args.use_umap:
        import umap  # type: ignore

        reducer = umap.UMAP(
            n_neighbors=35,
            min_dist=0.12,
            metric="euclidean",
            random_state=args.seed,
        )
        umap_coords = reducer.fit_transform(X_reduced)
        umap_available = True
    else:
        umap_coords = np.full((len(X_scaled), 2), np.nan)
        umap_available = False

    cluster_input = umap_coords if umap_available else pca_coords
    cluster = simple_kmeans(cluster_input, n_clusters=args.n_clusters, seed=args.seed)

    desc_rows = [descriptor_row(smi) for smi in smiles]
    rows = []
    for i, smi in enumerate(smiles):
        rows.append(
            {
                "solute_smiles": smi,
                "split": split[i],
                "pca_1": float(pca_coords[i, 0]),
                "pca_2": float(pca_coords[i, 1]),
                "umap_1": float(umap_coords[i, 0]),
                "umap_2": float(umap_coords[i, 1]),
                "cluster": int(cluster[i]),
                **desc_rows[i],
            }
        )
    projection_path = out / "embedding_projection.csv"
    with projection_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    profile_rows = []
    numeric_cols = ["mol_logp", "tpsa", "mol_wt", "heavy_atoms", "aromatic_rings"]
    for k in sorted(set(int(x) for x in cluster)):
        members = [row for row in rows if int(row["cluster"]) == k]
        n = len(members)
        profile = {
            "cluster": k,
            "n_solutes": n,
            "train_fraction": sum(row["split"] == "train" for row in members) / max(n, 1),
            "test_fraction": sum(row["split"] == "test" for row in members) / max(n, 1),
        }
        for col in numeric_cols:
            vals = np.asarray([row[col] for row in members], dtype=float)
            profile[f"{col}_mean"] = float(np.nanmean(vals))
        profile_rows.append(profile)
    profiles_path = out / "embedding_cluster_profiles.csv"
    with profiles_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(profile_rows[0].keys()))
        writer.writeheader()
        writer.writerows(profile_rows)

    summary = {
        "n_rows": int(len(rows)),
        "n_train": int(sum(row["split"] == "train" for row in rows)),
        "n_test": int(sum(row["split"] == "test" for row in rows)),
        "embedding_dim": int(X.shape[1]),
        "pca_2_variance": float(pca2.explained_variance_ratio_.sum()),
        "pca_50_variance": float(pca50.explained_variance_ratio_.sum()),
        "umap_available": bool(umap_available),
        "n_clusters": int(args.n_clusters),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
