"""
GNN encoder pretraining for TGNN-Solv.

Two self-supervised / weakly-supervised tasks on unlabeled molecules:

Stage 0a — Masked Atom Prediction (self-supervised):
  Mask 15% of atom features, predict them from graph context.
  Teaches the GNN about chemical environments.

Stage 0b — RDKit Property Prediction (weakly-supervised):
  Predict computed molecular descriptors (logP, TPSA, MolWt, ...).
  These are free to compute for any SMILES — unlimited "labels".
  Teaches the GNN about molecular properties relevant to solubility.

Data source: ZINC250k (freely available, ~250k drug-like molecules)
or any large SMILES collection.

Usage::

    from tgnn_solv.pretrain import Pretrainer, download_zinc250k

    smiles_list = download_zinc250k()  # or your own SMILES
    pretrainer = Pretrainer(model.gnn, model.readout, cfg)
    pretrainer.pretrain(smiles_list, n_epochs=30)
    # model.gnn is now pretrained — proceed with normal training
"""

import random
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
from torch_geometric.data import Data, Batch

from .config import TGNNSolvConfig
from .features import (
    smiles_to_graph,
    get_atom_features,
    NODE_FEAT_DIM,
    EDGE_FEAT_DIM,
)
from .layers import GNNEncoder, PhysicsAwareReadout
from .data.utils import download_file, RAW_DIR, canonicalize


# ================================================================== #
#  ZINC250k download                                                  #
# ================================================================== #

ZINC_URL = (
    "https://raw.githubusercontent.com/aspuru-guzik-group/"
    "chemical_vae/master/models/zinc_properties/250k_rndm_zinc_drugs_clean_3.csv"
)


def download_zinc250k(max_molecules: int = 250000) -> List[str]:
    """
    Download ZINC250k dataset (~250k drug-like SMILES).

    Falls back to generating SMILES from BigSolDB + random
    enumeration if download fails.
    """
    print("\n" + "=" * 60)
    print("Loading pretraining SMILES")
    print("=" * 60)

    path = RAW_DIR / "zinc250k.csv"
    download_file(ZINC_URL, path, "ZINC250k")

    smiles_set = set()

    if path.exists():
        try:
            df = pd.read_csv(path)
            # ZINC250k has column 'smiles'
            smi_col = next(
                (c for c in df.columns if "smi" in c.lower()),
                df.columns[0],
            )
            for smi in df[smi_col]:
                can = canonicalize(str(smi))
                if can is not None:
                    smiles_set.add(can)
            print(f"  ZINC250k: {len(smiles_set):,} valid SMILES")
        except Exception as e:
            print(f"  ZINC250k error: {e}")

    if len(smiles_set) == 0:
        print("  Falling back to BigSolDB SMILES only")
        # Try to load from processed data
        for csv_name in ["train.csv", "val.csv", "test.csv"]:
            csv_path = RAW_DIR.parent / "processed" / csv_name
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                for col in ["solute_smiles", "solvent_smiles"]:
                    if col in df.columns:
                        for smi in df[col].dropna().unique():
                            can = canonicalize(smi)
                            if can:
                                smiles_set.add(can)
        print(f"  From BigSolDB: {len(smiles_set):,} unique SMILES")

    result = list(smiles_set)[:max_molecules]
    print(f"  Total for pretraining: {len(result):,}")
    return result


# ================================================================== #
#  RDKit property computation                                         #
# ================================================================== #

# Properties relevant to solubility, all computable from SMILES
PROPERTY_FUNCTIONS = {
    "MolLogP": Descriptors.MolLogP,
    "MolWt": Descriptors.MolWt,
    "TPSA": Descriptors.TPSA,
    "NumHAcceptors": Descriptors.NumHAcceptors,
    "NumHDonors": Descriptors.NumHDonors,
    "NumRotatableBonds": Descriptors.NumRotatableBonds,
    "FractionCSP3": Descriptors.FractionCSP3,
    "HeavyAtomCount": Descriptors.HeavyAtomCount,
    "NumAromaticRings": Descriptors.NumAromaticRings,
    "LabuteASA": Descriptors.LabuteASA,
    "BalabanJ": Descriptors.BalabanJ,
    "HallKierAlpha": Descriptors.HallKierAlpha,
}

# Normalization stats (approximate, will be refined on actual data)
PROPERTY_SCALES = {
    "MolLogP": (2.0, 2.0),      # mean, std
    "MolWt": (300.0, 100.0),
    "TPSA": (60.0, 40.0),
    "NumHAcceptors": (3.0, 2.0),
    "NumHDonors": (1.5, 1.5),
    "NumRotatableBonds": (4.0, 3.0),
    "FractionCSP3": (0.4, 0.3),
    "HeavyAtomCount": (20.0, 8.0),
    "NumAromaticRings": (1.5, 1.0),
    "LabuteASA": (120.0, 50.0),
    "BalabanJ": (2.0, 1.0),
    "HallKierAlpha": (-2.0, 2.0),
}

N_PROPERTIES = len(PROPERTY_FUNCTIONS)


def compute_properties(smi: str) -> Optional[np.ndarray]:
    """Compute normalized RDKit properties for a SMILES."""
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None

    values = []
    for name, func in PROPERTY_FUNCTIONS.items():
        try:
            val = float(func(mol))
            mean, std = PROPERTY_SCALES[name]
            values.append((val - mean) / max(std, 1e-6))
        except Exception:
            values.append(0.0)

    return np.array(values, dtype=np.float32)


# ================================================================== #
#  Pretraining Dataset                                                #
# ================================================================== #

class PretrainDataset(Dataset):
    """
    Dataset for GNN pretraining.

    Each sample: (graph, masked_graph, atom_targets, property_targets)

    Atom masking: 15% of atoms have their features zeroed out.
    The model must predict the original features.
    """

    def __init__(
        self,
        smiles_list: List[str],
        mask_ratio: float = 0.15,
        cache: bool = True,
    ):
        self.mask_ratio = mask_ratio
        self.cache = {} if cache else None

        # Filter valid SMILES
        valid = []
        for smi in smiles_list:
            g = self._get_graph(smi)
            if g is not None:
                props = compute_properties(smi)
                if props is not None:
                    valid.append((smi, props))

        self.data = valid
        print(f"  PretrainDataset: {len(self.data):,} molecules")

    def _get_graph(self, smi):
        if self.cache is not None and smi in self.cache:
            return self.cache[smi]
        g = smiles_to_graph(smi)
        if self.cache is not None and g is not None:
            self.cache[smi] = g
        return g

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        smi, props = self.data[idx]
        graph = self._get_graph(smi).clone()

        # --- Mask atoms ---
        n_atoms = graph.x.shape[0]
        n_mask = max(1, int(n_atoms * self.mask_ratio))
        mask_indices = torch.randperm(n_atoms)[:n_mask]

        # Create mask boolean tensor
        mask = torch.zeros(n_atoms, dtype=torch.bool)
        mask[mask_indices] = True

        # Store original features as target
        atom_targets = graph.x[mask].clone()

        # Zero out masked atom features
        graph.x[mask] = 0.0

        # Property targets
        prop_tensor = torch.tensor(props, dtype=torch.float)

        return graph, mask, atom_targets, prop_tensor


def pretrain_collate(batch):
    """Collate for pretraining: batch graphs + collect masks/targets."""
    graphs, masks, atom_targets_list, prop_list = zip(*batch)

    batched_graph = Batch.from_data_list(list(graphs))
    props = torch.stack(prop_list)  # (B, N_properties)

    # Offset mask indices to match batched graph
    all_mask = []
    all_atom_targets = []
    offset = 0
    for i, (graph, mask, atom_tgt) in enumerate(
        zip(graphs, masks, atom_targets_list)
    ):
        n = graph.x.shape[0]
        # Global indices of masked atoms in the batched graph
        global_mask = torch.zeros(n, dtype=torch.bool)
        global_mask[mask] = True
        all_mask.append(global_mask)
        all_atom_targets.append(atom_tgt)
        offset += n

    # Concatenate masks and targets
    full_mask = torch.cat(all_mask)  # (N_total,)
    full_atom_targets = torch.cat(all_atom_targets)  # (N_masked, D_atom)

    return batched_graph, full_mask, full_atom_targets, props


# ================================================================== #
#  Pretraining heads                                                  #
# ================================================================== #

class AtomPredictionHead(nn.Module):
    """Predict masked atom features from GNN hidden states."""

    def __init__(self, hidden_dim: int, atom_feat_dim: int):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, atom_feat_dim),
        )

    def forward(self, h_atoms: torch.Tensor) -> torch.Tensor:
        return self.mlp(h_atoms)


class PropertyPredictionHead(nn.Module):
    """Predict molecular properties from graph-level vector."""

    def __init__(self, readout_dim: int, n_properties: int):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(readout_dim, 256),
            nn.SiLU(),
            nn.Dropout(0.1),
            nn.Linear(256, n_properties),
        )

    def forward(self, g_mol: torch.Tensor) -> torch.Tensor:
        return self.mlp(g_mol)


# ================================================================== #
#  Pretrainer                                                         #
# ================================================================== #

class Pretrainer:
    """
    Two-task GNN pretrainer.

    Trains the GNN encoder and readout on:
      1. Masked atom prediction (atom-level)
      2. RDKit property prediction (graph-level)

    After pretraining, the GNN weights are used as initialization
    for the full TGNN-Solv model.

    Parameters
    ----------
    gnn : GNNEncoder to pretrain (modified in-place)
    readout : PhysicsAwareReadout to pretrain (modified in-place)
    cfg : model config
    device : torch device
    """

    def __init__(
        self,
        gnn: GNNEncoder,
        readout: PhysicsAwareReadout,
        cfg: TGNNSolvConfig,
        device: torch.device = None,
    ):
        self.gnn = gnn
        self.readout = readout
        self.cfg = cfg

        if device is None:
            self.device = next(gnn.parameters()).device
        else:
            self.device = device

        # Pretraining heads (discarded after pretraining)
        self.atom_head = AtomPredictionHead(
            cfg.hidden_dim, NODE_FEAT_DIM
        ).to(self.device)

        self.prop_head = PropertyPredictionHead(
            readout.output_dim, N_PROPERTIES
        ).to(self.device)

    def pretrain(
        self,
        smiles_list: List[str],
        n_epochs: int = 30,
        batch_size: int = 128,
        lr: float = 3e-4,
        mask_ratio: float = 0.15,
        atom_loss_weight: float = 1.0,
        prop_loss_weight: float = 1.0,
    ) -> Dict[str, List[float]]:
        """
        Run pretraining.

        Parameters
        ----------
        smiles_list : SMILES for pretraining (e.g. from ZINC250k)
        n_epochs : number of pretraining epochs
        batch_size : batch size
        lr : learning rate
        mask_ratio : fraction of atoms to mask
        atom_loss_weight : weight for masked atom prediction loss
        prop_loss_weight : weight for property prediction loss

        Returns
        -------
        dict with loss history
        """
        print("\n" + "=" * 60)
        print("GNN Pretraining (Stage 0)")
        print("=" * 60)
        print(f"  Molecules: {len(smiles_list):,}")
        print(f"  Epochs: {n_epochs}")
        print(f"  Tasks: masked atom prediction + property prediction")

        # Build dataset
        dataset = PretrainDataset(
            smiles_list, mask_ratio=mask_ratio
        )
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            collate_fn=pretrain_collate,
            num_workers=0,
            drop_last=len(dataset) > batch_size,
        )

        # Optimizer for GNN + readout + heads
        params = (
            list(self.gnn.parameters())
            + list(self.readout.parameters())
            + list(self.atom_head.parameters())
            + list(self.prop_head.parameters())
        )
        optimizer = torch.optim.AdamW(params, lr=lr, weight_decay=1e-5)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=n_epochs
        )

        history = {"total": [], "atom": [], "prop": []}

        for epoch in range(n_epochs):
            self.gnn.train()
            self.readout.train()
            self.atom_head.train()
            self.prop_head.train()

            epoch_loss = {"total": 0, "atom": 0, "prop": 0}
            n_batches = 0

            for batch_graph, mask, atom_targets, props in loader:
                batch_graph = batch_graph.to(self.device)
                mask = mask.to(self.device)
                atom_targets = atom_targets.to(self.device)
                props = props.to(self.device)

                optimizer.zero_grad()

                # Forward through GNN (using solute adapter by default)
                h_atoms = self.gnn(
                    batch_graph.x,
                    batch_graph.edge_index,
                    batch_graph.edge_attr,
                    role="solute",
                )

                # Task 1: Masked atom prediction
                h_masked = h_atoms[mask]  # (N_masked, hidden)
                atom_pred = self.atom_head(h_masked)  # (N_masked, D_atom)
                loss_atom = F.mse_loss(atom_pred, atom_targets)

                # Task 2: Property prediction
                g_mol = self.readout(h_atoms, batch_graph.batch)
                prop_pred = self.prop_head(g_mol)  # (B, N_properties)
                loss_prop = F.mse_loss(prop_pred, props)

                # Combined loss
                loss = (
                    atom_loss_weight * loss_atom
                    + prop_loss_weight * loss_prop
                )

                loss.backward()
                nn.utils.clip_grad_norm_(params, 1.0)
                optimizer.step()

                epoch_loss["total"] += loss.item()
                epoch_loss["atom"] += loss_atom.item()
                epoch_loss["prop"] += loss_prop.item()
                n_batches += 1

            scheduler.step()

            for k in epoch_loss:
                epoch_loss[k] /= max(n_batches, 1)
                history[k].append(epoch_loss[k])

            if epoch % 5 == 0 or epoch == n_epochs - 1:
                print(
                    f"  Epoch {epoch:3d}/{n_epochs}: "
                    f"total={epoch_loss['total']:.4f}, "
                    f"atom={epoch_loss['atom']:.4f}, "
                    f"prop={epoch_loss['prop']:.4f}"
                )

        # Discard pretraining heads (not needed for fine-tuning)
        del self.atom_head
        del self.prop_head

        print(f"\n  Pretraining complete.")
        print(f"  GNN and Readout weights updated in-place.")
        print(f"  Pretraining heads discarded.")

        return history
