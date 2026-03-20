"""
Molecular featurization: SMILES -> PyG Data graph.

Atom features (~35 dims):
  - Atomic number (one-hot, 12 elements + unknown)
  - Hybridization (one-hot, 5 types + unknown)
  - Formal charge (one-hot, 5 values + unknown)
  - Total H count (one-hot, 0-3 + unknown)
  - Is aromatic (binary)
  - Is in ring (binary)
  - Electronegativity (Pauling, scaled)
  - VdW radius (scaled)
  - Polarizability (scaled)

Bond features (8 dims):
  - Bond type: single/double/triple/aromatic
  - Is conjugated
  - Is in ring
  - Stereo E / Z
"""

from typing import List, Optional

import torch
from rdkit import Chem
from rdkit.Chem import AllChem
from torch_geometric.data import Data


ELECTRONEG = {
    6: 2.55, 7: 3.04, 8: 3.44, 9: 3.98, 15: 2.19,
    16: 2.58, 17: 3.16, 35: 2.96, 53: 2.66, 1: 2.20,
    5: 2.04, 14: 1.90, 34: 2.55, 30: 1.65, 29: 1.90,
}

VDW_RADII = {
    6: 1.70, 7: 1.55, 8: 1.52, 9: 1.47, 15: 1.80,
    16: 1.80, 17: 1.75, 35: 1.85, 53: 1.98, 1: 1.20,
    5: 1.92, 14: 2.10, 34: 1.90, 30: 1.39, 29: 1.40,
}

POLARIZABILITY = {
    6: 1.76, 7: 1.10, 8: 0.80, 9: 0.56, 15: 3.63,
    16: 2.90, 17: 2.18, 35: 3.05, 53: 5.35, 1: 0.67,
    5: 3.03, 14: 5.38, 34: 3.77, 30: 5.75, 29: 6.10,
}

ATOM_LIST = [6, 7, 8, 9, 15, 16, 17, 35, 53, 5, 14, 34]

HYBRIDIZATION_LIST = [
    Chem.rdchem.HybridizationType.SP,
    Chem.rdchem.HybridizationType.SP2,
    Chem.rdchem.HybridizationType.SP3,
    Chem.rdchem.HybridizationType.SP3D,
    Chem.rdchem.HybridizationType.SP3D2,
]

FORMAL_CHARGE_LIST = [-2, -1, 0, 1, 2]


# ------------------------------------------------------------------ #
#  Helpers                                                            #
# ------------------------------------------------------------------ #

def _one_hot(value, choices: list) -> List[float]:
    """One-hot with an extra 'unknown' slot at the end."""
    enc = [0.0] * (len(choices) + 1)
    if value in choices:
        enc[choices.index(value)] = 1.0
    else:
        enc[-1] = 1.0
    return enc


# ------------------------------------------------------------------ #
#  Per-atom / per-bond feature vectors                                #
# ------------------------------------------------------------------ #

def get_atom_features(atom) -> List[float]:
    """Return ~35-dim feature vector for a single atom."""
    anum = atom.GetAtomicNum()
    feats = []
    feats += _one_hot(anum, ATOM_LIST)                       # 13
    feats += _one_hot(atom.GetHybridization(), HYBRIDIZATION_LIST)  # 6
    feats += _one_hot(atom.GetFormalCharge(), FORMAL_CHARGE_LIST)   # 6
    feats += _one_hot(atom.GetTotalNumHs(), [0, 1, 2, 3])         # 5
    feats.append(float(atom.GetIsAromatic()))                 # 1
    feats.append(float(atom.IsInRing()))                      # 1
    feats.append(ELECTRONEG.get(anum, 2.0) / 4.0)            # 1
    feats.append(VDW_RADII.get(anum, 1.7) / 2.0)             # 1
    feats.append(POLARIZABILITY.get(anum, 1.5) / 5.0)        # 1
    return feats  # total = 35


def get_bond_features(bond) -> List[float]:
    """Return 8-dim feature vector for a single bond."""
    bt = bond.GetBondType()
    return [
        float(bt == Chem.rdchem.BondType.SINGLE),
        float(bt == Chem.rdchem.BondType.DOUBLE),
        float(bt == Chem.rdchem.BondType.TRIPLE),
        float(bt == Chem.rdchem.BondType.AROMATIC),
        float(bond.GetIsConjugated()),
        float(bond.IsInRing()),
        float(bond.GetStereo() == Chem.rdchem.BondStereo.STEREOE),
        float(bond.GetStereo() == Chem.rdchem.BondStereo.STEREOZ),
    ]


# ------------------------------------------------------------------ #
#  SMILES → PyG graph                                                 #
# ------------------------------------------------------------------ #

def smiles_to_graph(smiles: str, compute_3d: bool = False) -> Optional[Data]:
    """
    Convert a SMILES string into a PyTorch-Geometric ``Data`` object.

    Parameters
    ----------
    smiles : str
        Input SMILES (will be sanitized and H-removed).
    compute_3d : bool
        If True, embed a 3-D conformer and attach ``data.pos``.

    Returns
    -------
    Data or None
        ``None`` when SMILES is invalid or molecule has no atoms.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    # Optional 3-D conformer (on the H-added molecule)
    pos = None
    if compute_3d:
        try:
            mol_3d = Chem.AddHs(mol)
            AllChem.EmbedMolecule(mol_3d, AllChem.ETKDGv3())
            AllChem.MMFFOptimizeMolecule(mol_3d, maxIters=200)
            conf = mol_3d.GetConformer()
            # Keep only heavy-atom positions
            pos = torch.tensor(
                [list(conf.GetAtomPosition(i))
                 for i in range(mol.GetNumAtoms())],
                dtype=torch.float,
            )
        except Exception:
            pos = None

    mol = Chem.RemoveHs(mol)
    if mol.GetNumAtoms() == 0:
        return None

    # Node features
    x = torch.tensor(
        [get_atom_features(a) for a in mol.GetAtoms()],
        dtype=torch.float,
    )

    # Edge features (undirected: add both directions)
    edge_indices, edge_attrs = [], []
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        bf = get_bond_features(bond)
        edge_indices += [[i, j], [j, i]]
        edge_attrs += [bf, bf]

    if len(edge_indices) == 0:
        # Single-atom molecule (e.g. noble gas) — add self-loop
        edge_index = torch.zeros((2, 1), dtype=torch.long)
        edge_attr = torch.zeros((1, 8), dtype=torch.float)
    else:
        edge_index = torch.tensor(edge_indices, dtype=torch.long).t().contiguous()
        edge_attr = torch.tensor(edge_attrs, dtype=torch.float)

    data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
    if pos is not None and pos.shape[0] == mol.GetNumAtoms():
        data.pos = pos
    data.smiles = smiles
    data.num_atoms = mol.GetNumAtoms()
    return data


# ------------------------------------------------------------------ #
#  Feature dimensions (computed once at import time)                   #
# ------------------------------------------------------------------ #

def _compute_dims():
    """Compute feature dimensions from a reference molecule."""
    g = smiles_to_graph("C")  # methane
    if g is None:
        return 35, 8  # fallback
    node_dim = g.x.shape[1]
    edge_dim = g.edge_attr.shape[1]
    return node_dim, edge_dim


NODE_FEAT_DIM, EDGE_FEAT_DIM = _compute_dims()