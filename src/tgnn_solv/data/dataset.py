"""
PyTorch Dataset and DataLoader factories for TGNN-Solv.

TGNNSolvDataset wraps a unified DataFrame and produces
(solute_graph, solvent_graph, targets_dict) triples.

All auxiliary targets carry boolean masks so the loss function
can skip missing values.
"""

from typing import Dict, Tuple

import torch
from torch.utils.data import Dataset, DataLoader
from torch_geometric.data import Batch

import pandas as pd

from ..features import smiles_to_graph
from .solvent_types import solvent_type_id_from_smiles


class TGNNSolvDataset(Dataset):
    """
    PyTorch Dataset for TGNN-Solv.

    Each sample is a tuple:
      (solute_graph, solvent_graph, targets_dict)

    targets_dict keys:
      T              — temperature (K)
      ln_x2          — log mole fraction (0.0 if no solubility data)
      has_solubility — bool mask
      solvent_type   — int solvent type id
      T_m, T_m_mask
      dH_fus, dH_mask
      hansen_sol (3,), hansen_mask
      ln_gamma_inf, gamma_mask
      dG_solv, dG_mask
    """

    def __init__(self, df: pd.DataFrame, cache: bool = True):
        self.cache: Dict[str, object] = {} if cache else None

        # Validate all SMILES upfront (fast: uses cache after first pass)
        valid = []
        for row in df.itertuples():
            sol_ok = self._graph(row.solute_smiles) is not None
            slv_ok = self._graph(row.solvent_smiles) is not None
            if sol_ok and slv_ok:
                valid.append(row.Index)

        self.df = df.loc[valid].reset_index(drop=True)
        # Precompute solvent type ids (for MoE routing)
        unique_solv = self.df["solvent_smiles"].unique()
        type_map = {
            smi: solvent_type_id_from_smiles(smi) for smi in unique_solv
        }
        self.df["solvent_type"] = self.df["solvent_smiles"].map(type_map)
        n_drop = len(df) - len(valid)
        n_cached = len(self.cache) if self.cache else 0
        print(
            f"  Dataset: {len(self.df):,} valid "
            f"({n_drop} dropped, {n_cached} cached graphs)"
        )

    def _graph(self, smi: str):
        """Get graph from cache or build it."""
        if self.cache is not None and smi in self.cache:
            return self.cache[smi]
        g = smiles_to_graph(smi)
        if self.cache is not None and g is not None:
            self.cache[smi] = g
        return g

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int):
        r = self.df.iloc[idx]

        sol_g = self._graph(r["solute_smiles"]).clone()
        slv_g = self._graph(r["solvent_smiles"]).clone()

        t = {
            "T": torch.tensor(float(r["temperature"]), dtype=torch.float),
            "ln_x2": torch.tensor(
                float(r["ln_x2"]) if r["has_solubility"] else 0.0,
                dtype=torch.float,
            ),
            "has_solubility": torch.tensor(
                bool(r["has_solubility"]), dtype=torch.bool
            ),
            "solvent_type": torch.tensor(
                int(r["solvent_type"]), dtype=torch.long
            ),
            "T_m": torch.tensor(float(r["T_m"]), dtype=torch.float),
            "T_m_mask": torch.tensor(
                bool(r["has_T_m"]), dtype=torch.bool
            ),
            "dH_fus": torch.tensor(float(r["dH_fus"]), dtype=torch.float),
            "dH_mask": torch.tensor(
                bool(r["has_dH_fus"]), dtype=torch.bool
            ),
            "hansen_sol": torch.tensor(
                [float(r["hansen_d"]), float(r["hansen_p"]),
                 float(r["hansen_h"])],
                dtype=torch.float,
            ),
            "hansen_mask": torch.tensor(
                bool(r["has_hansen"]), dtype=torch.bool
            ),
            "ln_gamma_inf": torch.tensor(
                float(r["ln_gamma_inf"]), dtype=torch.float
            ),
            "gamma_mask": torch.tensor(
                bool(r["has_gamma_inf"]), dtype=torch.bool
            )
        }
        return sol_g, slv_g, t


def collate_fn(batch):
    """
    Collate function for DataLoader.

    Batches solute/solvent graphs separately via PyG Batch,
    stacks all target tensors.
    """
    sol_gs, slv_gs, tgts = zip(*batch)

    sol_batch = Batch.from_data_list(list(sol_gs))
    slv_batch = Batch.from_data_list(list(slv_gs))

    t_batch = {}
    for key in tgts[0]:
        t_batch[key] = torch.stack([t[key] for t in tgts])

    return sol_batch, slv_batch, t_batch


def make_loaders(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    batch_size: int = 64,
    num_workers: int = 0,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Create train / val / test DataLoaders.

    Parameters
    ----------
    train_df, val_df, test_df : split DataFrames from scaffold_split
    batch_size : samples per batch
    num_workers : DataLoader workers (0 = main process)

    Returns
    -------
    (train_loader, val_loader, test_loader)
    """
    print("\nCreating DataLoaders...")

    train_ds = TGNNSolvDataset(train_df)
    val_ds = TGNNSolvDataset(val_df)
    test_ds = TGNNSolvDataset(test_df)

    kw = dict(
        collate_fn=collate_fn,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    train_ld = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True,
        drop_last=(len(train_ds) > batch_size), **kw,
    )
    val_ld = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False, **kw,
    )
    test_ld = DataLoader(
        test_ds, batch_size=batch_size, shuffle=False, **kw,
    )

    for name, ds, ld in [
        ("Train", train_ds, train_ld),
        ("Val", val_ds, val_ld),
        ("Test", test_ds, test_ld),
    ]:
        print(f"  {name}: {len(ds):,d} samples, {len(ld):,d} batches")

    return train_ld, val_ld, test_ld
