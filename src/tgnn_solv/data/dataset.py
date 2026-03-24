"""
PyTorch Dataset and DataLoader factories for TGNN-Solv.

TGNNSolvDataset wraps a unified DataFrame and produces
(solute_graph, solvent_graph, targets_dict) triples.

All auxiliary targets carry boolean masks so the loss function
can skip missing values.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterator, Sequence
from typing import TypeAlias

import torch
from torch.utils.data import DataLoader, Dataset, Sampler
from torch_geometric.data import Batch, Data

import pandas as pd

from ..features import smiles_to_graph
from .solvent_types import solvent_type_id_from_smiles

TargetValue: TypeAlias = torch.Tensor | str
BatchTargetValue: TypeAlias = torch.Tensor | list[str]
TargetDict: TypeAlias = dict[str, TargetValue]
Sample: TypeAlias = tuple[Data, Data, TargetDict]
BatchTargetDict: TypeAlias = dict[str, BatchTargetValue]
BatchTriplet: TypeAlias = tuple[Batch, Batch, BatchTargetDict]


class PairTemperatureBatchSampler(Sampler[list[int]]):
    """Batch sampler that keeps multi-temperature solute/solvent pairs together."""

    def __init__(
        self,
        pair_keys: Sequence[str],
        batch_size: int,
        *,
        drop_last: bool = False,
        min_group_size: int = 2,
        group_chunk_size: int = 4,
        seed: int = 42,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if min_group_size < 2:
            raise ValueError("min_group_size must be at least 2")
        if group_chunk_size < min_group_size:
            raise ValueError("group_chunk_size must be >= min_group_size")

        self.pair_keys = [str(key) for key in pair_keys]
        self.batch_size = batch_size
        self.drop_last = drop_last
        self.min_group_size = min_group_size
        self.group_chunk_size = max(min(group_chunk_size, batch_size), min_group_size)
        self.seed = seed
        self._epoch = 0
        self._groups = self._build_groups()

    def _build_groups(self) -> dict[str, list[int]]:
        groups: dict[str, list[int]] = {}
        for idx, key in enumerate(self.pair_keys):
            groups.setdefault(key, []).append(idx)
        return groups

    def _split_group(
        self,
        indices: list[int],
        leftovers: list[int],
    ) -> list[list[int]]:
        chunks: list[list[int]] = []
        start = 0
        remaining = len(indices)

        while remaining >= self.min_group_size:
            take = min(self.group_chunk_size, remaining)
            if remaining - take == 1:
                take -= 1
            if take < self.min_group_size:
                break
            chunks.append(indices[start:start + take])
            start += take
            remaining -= take

        if start < len(indices):
            leftovers.extend(indices[start:])

        return chunks

    def __len__(self) -> int:
        if self.drop_last:
            return len(self.pair_keys) // self.batch_size
        return math.ceil(len(self.pair_keys) / self.batch_size)

    def __iter__(self) -> Iterator[list[int]]:
        rng = random.Random(self.seed + self._epoch)
        self._epoch += 1

        pair_chunks: list[list[int]] = []
        leftovers: list[int] = []
        for indices in self._groups.values():
            shuffled = indices.copy()
            rng.shuffle(shuffled)
            if len(shuffled) < self.min_group_size:
                leftovers.extend(shuffled)
                continue
            pair_chunks.extend(self._split_group(shuffled, leftovers))

        rng.shuffle(pair_chunks)
        pair_chunks.sort(key=len, reverse=True)
        rng.shuffle(leftovers)

        candidate_batches: list[list[int]] = []
        current_batch: list[int] = []
        for chunk in pair_chunks:
            if len(current_batch) + len(chunk) > self.batch_size:
                if current_batch:
                    candidate_batches.append(current_batch)
                current_batch = []
            current_batch.extend(chunk)
        if current_batch:
            candidate_batches.append(current_batch)

        leftover_cursor = 0
        finalized_batches: list[list[int]] = []
        for batch in candidate_batches:
            while len(batch) < self.batch_size and leftover_cursor < len(leftovers):
                batch.append(leftovers[leftover_cursor])
                leftover_cursor += 1
            if len(batch) == self.batch_size or not self.drop_last:
                rng.shuffle(batch)
                finalized_batches.append(batch)

        remaining = leftovers[leftover_cursor:]
        while remaining:
            batch = remaining[:self.batch_size]
            remaining = remaining[self.batch_size:]
            if len(batch) == self.batch_size or not self.drop_last:
                rng.shuffle(batch)
                finalized_batches.append(batch)

        if not finalized_batches and not self.drop_last and not self.pair_keys:
            return

        rng.shuffle(finalized_batches)
        yield from finalized_batches


class TGNNSolvDataset(Dataset):
    """
    PyTorch Dataset for TGNN-Solv.

    Each sample is a tuple:
      (solute_graph, solvent_graph, targets_dict)

    targets_dict keys:
      T              — temperature (K)
      ln_x2          — log mole fraction (0.0 if no solubility data)
      has_solubility — bool mask
      pair_key       — string key "{solute}>>{solvent}" for same-pair temperature losses
      solvent_type   — int solvent type id
      T_m, T_m_mask
      dH_fus, dH_mask
      hansen_sol (3,), hansen_mask
      ln_gamma_inf, gamma_mask
      dG_solv, dG_mask
    """

    def __init__(self, df: pd.DataFrame, cache: bool = True) -> None:
        self.cache: dict[str, Data] | None = {} if cache else None

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
        self.df["pair_key"] = (
            self.df["solute_smiles"].astype(str)
            + ">>"
            + self.df["solvent_smiles"].astype(str)
        )
        self.pair_keys: list[str] = self.df["pair_key"].tolist()
        n_drop = len(df) - len(valid)
        n_cached = len(self.cache) if self.cache else 0
        print(
            f"  Dataset: {len(self.df):,} valid "
            f"({n_drop} dropped, {n_cached} cached graphs)"
        )

    def _graph(self, smi: str) -> Data | None:
        """Get graph from cache or build it."""
        if self.cache is not None and smi in self.cache:
            return self.cache[smi]
        g = smiles_to_graph(smi)
        if self.cache is not None and g is not None:
            self.cache[smi] = g
        return g

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Sample:
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
            "T_m": torch.tensor(
                float(r["T_m"]) if r["has_T_m"] else 0.0,
                dtype=torch.float,
            ),
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
            ),
            "pair_key": str(r["pair_key"]),
            "solute_smiles": str(r["solute_smiles"]),
            "solvent_smiles": str(r["solvent_smiles"]),
        }
        return sol_g, slv_g, t


def collate_fn(batch: list[Sample]) -> BatchTriplet:
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
        first_value = tgts[0][key]
        if isinstance(first_value, torch.Tensor):
            t_batch[key] = torch.stack([t[key] for t in tgts])
        else:
            t_batch[key] = [t[key] for t in tgts]

    return sol_batch, slv_batch, t_batch


def make_loader(
    df: pd.DataFrame,
    batch_size: int,
    *,
    shuffle: bool,
    num_workers: int = 0,
    cache: bool = True,
    drop_last: bool | None = None,
    use_pair_temperature_batching: bool = False,
    pair_temperature_min_group_size: int = 2,
    pair_temperature_group_chunk_size: int = 4,
    seed: int = 42,
) -> DataLoader:
    """Create a single DataLoader with optional same-pair temperature batching."""
    dataset = TGNNSolvDataset(df, cache=cache)

    if drop_last is None:
        drop_last = shuffle and len(dataset) > batch_size

    kwargs = dict(
        collate_fn=collate_fn,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    if shuffle and use_pair_temperature_batching:
        batch_sampler = PairTemperatureBatchSampler(
            dataset.pair_keys,
            batch_size=batch_size,
            drop_last=drop_last,
            min_group_size=pair_temperature_min_group_size,
            group_chunk_size=pair_temperature_group_chunk_size,
            seed=seed,
        )
        return DataLoader(dataset, batch_sampler=batch_sampler, **kwargs)

    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        drop_last=drop_last,
        **kwargs,
    )


def make_loaders(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    batch_size: int = 64,
    num_workers: int = 0,
    use_pair_temperature_batching: bool = False,
    pair_temperature_min_group_size: int = 2,
    pair_temperature_group_chunk_size: int = 4,
    seed: int = 42,
) -> tuple[DataLoader, DataLoader, DataLoader]:
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

    train_ld = make_loader(
        train_df,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        cache=True,
        drop_last=(len(train_df) > batch_size),
        use_pair_temperature_batching=use_pair_temperature_batching,
        pair_temperature_min_group_size=pair_temperature_min_group_size,
        pair_temperature_group_chunk_size=pair_temperature_group_chunk_size,
        seed=seed,
    )
    val_ld = make_loader(
        val_df,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        cache=True,
        drop_last=False,
    )
    test_ld = make_loader(
        test_df,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        cache=True,
        drop_last=False,
    )

    for name, frame, loader in [
        ("Train", train_df, train_ld),
        ("Val", val_df, val_ld),
        ("Test", test_df, test_ld),
    ]:
        print(f"  {name}: {len(frame):,d} samples, {len(loader):,d} batches")

    return train_ld, val_ld, test_ld
