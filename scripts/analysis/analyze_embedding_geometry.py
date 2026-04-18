#!/usr/bin/env python
"""Analyze train/test geometry for saved solute embedding NPZ files.

Expected input files are produced by ``scripts/probe_gsol_descriptor_recovery.py``
and contain:

- ``smiles``: object array of unique solute SMILES
- ``embeddings``: float array of shape (n_solutes, embedding_dim)

The script reports domain separation metrics and writes PCA/t-SNE plots.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.manifold import TSNE
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler


_MISSING = object()


def _install_numpy_pickle_compat() -> dict[str, object]:
    """Allow NumPy-2-created object NPZ files to load under NumPy 1.x.

    Some existing descriptor-probe artifacts pickle object arrays with module
    references under ``numpy._core``. NumPy 1.x exposes these modules as
    ``numpy.core`` instead. The aliases below are harmless under NumPy 2 and
    avoid rerunning expensive embedding extraction just to refresh old NPZs.
    """
    names = ("numpy._core", "numpy._core.multiarray", "numpy._core.numeric")
    previous = {name: sys.modules.get(name, _MISSING) for name in names}
    if "numpy._core" not in sys.modules and hasattr(np, "core"):
        sys.modules["numpy._core"] = np.core
    if "numpy._core.multiarray" not in sys.modules and hasattr(np.core, "multiarray"):
        sys.modules["numpy._core.multiarray"] = np.core.multiarray
    if "numpy._core.numeric" not in sys.modules and hasattr(np.core, "numeric"):
        sys.modules["numpy._core.numeric"] = np.core.numeric
    return previous


def _restore_numpy_pickle_compat(previous: dict[str, object]) -> None:
    for name, value in previous.items():
        if value is _MISSING:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = value  # type: ignore[assignment]


def _load_npz(path: Path) -> tuple[np.ndarray, np.ndarray]:
    previous_modules = _install_numpy_pickle_compat()
    try:
        data = np.load(path, allow_pickle=True)
        keys = set(data.files)
        if "smiles" not in keys or "embeddings" not in keys:
            raise ValueError(f"{path} must contain 'smiles' and 'embeddings'.")
        smiles = data["smiles"].astype(str)
        embeddings = data["embeddings"].astype(np.float32, copy=False)
    finally:
        _restore_numpy_pickle_compat(previous_modules)
    return smiles, embeddings


def _subsample_indices(n: int, max_n: int, rng: np.random.Generator) -> np.ndarray:
    if n <= max_n:
        return np.arange(n)
    return np.sort(rng.choice(n, size=max_n, replace=False))


def _median_heuristic_gamma(X: np.ndarray, Y: np.ndarray, rng: np.random.Generator) -> float:
    Z = np.concatenate([X, Y], axis=0)
    if len(Z) > 1000:
        Z = Z[rng.choice(len(Z), size=1000, replace=False)]
    diffs = Z[:, None, :] - Z[None, :, :]
    dist2 = np.sum(diffs * diffs, axis=-1)
    vals = dist2[np.triu_indices_from(dist2, k=1)]
    vals = vals[np.isfinite(vals) & (vals > 0)]
    if vals.size == 0:
        return 1.0 / max(1, Z.shape[1])
    median_dist2 = float(np.median(vals))
    return 1.0 / max(median_dist2, 1e-12)


def _rbf_mmd2(X: np.ndarray, Y: np.ndarray, gamma: float) -> float:
    def kernel(A: np.ndarray, B: np.ndarray) -> np.ndarray:
        dist2 = (
            np.sum(A * A, axis=1)[:, None]
            + np.sum(B * B, axis=1)[None, :]
            - 2.0 * A @ B.T
        )
        return np.exp(-gamma * np.maximum(dist2, 0.0))

    return float(kernel(X, X).mean() + kernel(Y, Y).mean() - 2.0 * kernel(X, Y).mean())


def _logp_values(smiles: np.ndarray) -> np.ndarray:
    values = []
    for smi in smiles:
        mol = Chem.MolFromSmiles(str(smi))
        values.append(np.nan if mol is None else float(Descriptors.MolLogP(mol)))
    return np.asarray(values, dtype=float)


def _plot_2d(
    coords: np.ndarray,
    split_labels: np.ndarray,
    logp: np.ndarray,
    title: str,
    out_path: Path,
) -> None:
    train_mask = split_labels == 0
    test_mask = ~train_mask

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].scatter(coords[train_mask, 0], coords[train_mask, 1], s=8, alpha=0.25, label="train")
    axes[0].scatter(coords[test_mask, 0], coords[test_mask, 1], s=10, alpha=0.55, label="test")
    axes[0].set_title(f"{title}: train/test")
    axes[0].legend(frameon=False)
    axes[0].set_xticks([])
    axes[0].set_yticks([])

    scatter = axes[1].scatter(coords[:, 0], coords[:, 1], c=logp, cmap="viridis", s=8, alpha=0.55)
    axes[1].set_title(f"{title}: MolLogP")
    axes[1].set_xticks([])
    axes[1].set_yticks([])
    fig.colorbar(scatter, ax=axes[1], label="MolLogP")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def run_analysis(
    train_embeddings_path: Path,
    test_embeddings_path: Path,
    output_dir: Path,
    seed: int = 42,
    pca_components: int = 50,
    max_mmd_points: int = 1500,
    max_tsne_points: int = 3000,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    train_smiles, X_train = _load_npz(train_embeddings_path)
    test_smiles, X_test = _load_npz(test_embeddings_path)

    scaler = StandardScaler()
    X_all = scaler.fit_transform(np.concatenate([X_train, X_test], axis=0))
    split_labels = np.concatenate(
        [
            np.zeros(len(X_train), dtype=int),
            np.ones(len(X_test), dtype=int),
        ],
        axis=0,
    )
    all_smiles = np.concatenate([train_smiles, test_smiles], axis=0)

    n_components = min(pca_components, X_all.shape[1], len(X_all) - 1)
    pca = PCA(n_components=n_components, random_state=seed)
    X_pca = pca.fit_transform(X_all)
    explained_10 = float(np.sum(pca.explained_variance_ratio_[: min(10, n_components)]))
    explained_all = float(np.sum(pca.explained_variance_ratio_))

    train_idx = np.where(split_labels == 0)[0]
    test_idx = np.where(split_labels == 1)[0]
    train_sub = train_idx[_subsample_indices(len(train_idx), max_mmd_points, rng)]
    test_sub = test_idx[_subsample_indices(len(test_idx), max_mmd_points, rng)]
    gamma = _median_heuristic_gamma(X_pca[train_sub], X_pca[test_sub], rng)
    mmd2 = _rbf_mmd2(X_pca[train_sub], X_pca[test_sub], gamma=gamma)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    clf = LogisticRegression(max_iter=2000, class_weight="balanced")
    domain_scores = cross_val_predict(clf, X_pca, split_labels, cv=cv, method="predict_proba")[:, 1]
    domain_auc = float(roc_auc_score(split_labels, domain_scores))

    logp = _logp_values(all_smiles)
    pca_2d = X_pca[:, :2]
    _plot_2d(pca_2d, split_labels, logp, "PCA", output_dir / "embedding_pca_train_test_logp.png")

    tsne_idx = _subsample_indices(len(X_pca), max_tsne_points, rng)
    X_tsne = TSNE(
        n_components=2,
        perplexity=min(30.0, max(5.0, (len(tsne_idx) - 1) / 3.0)),
        init="pca",
        learning_rate="auto",
        random_state=seed,
    ).fit_transform(X_pca[tsne_idx])
    _plot_2d(
        X_tsne,
        split_labels[tsne_idx],
        logp[tsne_idx],
        "t-SNE",
        output_dir / "embedding_tsne_train_test_logp.png",
    )

    summary = {
        "train_embeddings_path": str(train_embeddings_path),
        "test_embeddings_path": str(test_embeddings_path),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "embedding_dim": int(X_train.shape[1]),
        "pca_components": int(n_components),
        "pca_variance_explained_first_10": explained_10,
        "pca_variance_explained_used_components": explained_all,
        "mmd2_rbf_pca": mmd2,
        "mmd_gamma_median_heuristic": float(gamma),
        "domain_classifier_auc_cv": domain_auc,
        "max_mmd_points_per_split": int(max_mmd_points),
        "max_tsne_points": int(max_tsne_points),
        "interpretation": _interpret(mmd2, domain_auc),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_markdown(summary, output_dir / "SUMMARY.md")
    return summary


def _interpret(mmd2: float, domain_auc: float) -> str:
    if domain_auc >= 0.85:
        return "Train and test embeddings are strongly separable by split; this indicates a real embedding-domain shift."
    if domain_auc >= 0.70:
        return "Train and test embeddings are moderately separable; structural extrapolation remains visible in embedding space."
    return "Train and test embeddings are weakly separable by split; downstream heads or pair interactions may dominate the gap."


def _write_markdown(summary: dict, path: Path) -> None:
    lines = [
        "# Embedding Geometry Diagnostic",
        "",
        f"- train embeddings: `{summary['train_embeddings_path']}`",
        f"- test embeddings: `{summary['test_embeddings_path']}`",
        f"- n train/test: `{summary['n_train']}` / `{summary['n_test']}`",
        f"- embedding dim: `{summary['embedding_dim']}`",
        f"- PCA variance first 10: `{summary['pca_variance_explained_first_10']:.3f}`",
        f"- PCA variance used components: `{summary['pca_variance_explained_used_components']:.3f}`",
        f"- RBF MMD² on PCA space: `{summary['mmd2_rbf_pca']:.4f}`",
        f"- split-domain classifier AUC, 5-fold CV: `{summary['domain_classifier_auc_cv']:.3f}`",
        "",
        f"**Interpretation:** {summary['interpretation']}",
        "",
        "Plots:",
        "",
        "- `embedding_pca_train_test_logp.png`",
        "- `embedding_tsne_train_test_logp.png`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-embeddings", type=Path, required=True)
    parser.add_argument("--test-embeddings", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pca-components", type=int, default=50)
    parser.add_argument("--max-mmd-points", type=int, default=1500)
    parser.add_argument("--max-tsne-points", type=int, default=3000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_analysis(
        train_embeddings_path=args.train_embeddings,
        test_embeddings_path=args.test_embeddings,
        output_dir=args.output_dir,
        seed=args.seed,
        pca_components=args.pca_components,
        max_mmd_points=args.max_mmd_points,
        max_tsne_points=args.max_tsne_points,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
