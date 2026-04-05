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

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeAlias

import numpy as np
import torch
from rdkit import Chem
from rdkit.Chem import (
    AllChem,
    Crippen,
    Descriptors,
    Fragments,
    Lipinski,
    rdMolDescriptors,
)
from rdkit.ML.Descriptors import MoleculeDescriptors
from rdkit.DataStructs import ConvertToNumpyArray
from torch_geometric.data import Data

FeatureVector: TypeAlias = list[float]


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
RDKitDescriptorArray: TypeAlias = np.ndarray
RDKitDescriptorStats: TypeAlias = tuple[np.ndarray, np.ndarray]
RDKitDescriptorNames: TypeAlias = tuple[str, ...]
DESCRIPTOR_RAW_ABS_CLIP = 1.0e6
DESCRIPTOR_Z_CLIP = 10.0

RDKIT_DESCRIPTOR_NAMES: RDKitDescriptorNames = tuple(
    name for name, _ in Descriptors.descList
)
_RDKIT_DESCRIPTOR_CALCULATOR = MoleculeDescriptors.MolecularDescriptorCalculator(
    list(RDKIT_DESCRIPTOR_NAMES)
)


# ------------------------------------------------------------------ #
#  Helpers                                                            #
# ------------------------------------------------------------------ #

def _one_hot(value: object, choices: list[object]) -> FeatureVector:
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

def get_atom_features(atom: object) -> FeatureVector:
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


def get_bond_features(bond: object) -> FeatureVector:
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

def smiles_to_graph(smiles: str, compute_3d: bool = False) -> Data | None:
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


def smiles_to_morgan_fp(
    smiles: str,
    radius: int = 2,
    n_bits: int = 2048,
) -> np.ndarray | None:
    """Convert a SMILES string into a Morgan fingerprint bit vector."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    bitvect = AllChem.GetMorganFingerprintAsBitVect(
        mol,
        radius=radius,
        nBits=n_bits,
    )
    array = np.zeros((n_bits,), dtype=np.float32)
    ConvertToNumpyArray(bitvect, array)
    return array


def compute_pair_morgan_features(
    solute_smiles: str,
    solvent_smiles: str,
    temperature: float,
    *,
    radius: int = 2,
    n_bits: int = 2048,
) -> np.ndarray | None:
    """Build a pair feature vector from Morgan fingerprints and temperature."""
    solute_fp = smiles_to_morgan_fp(solute_smiles, radius=radius, n_bits=n_bits)
    solvent_fp = smiles_to_morgan_fp(solvent_smiles, radius=radius, n_bits=n_bits)
    if solute_fp is None or solvent_fp is None:
        return None

    temp = float(temperature)
    inv_temperature = 1.0 / temp
    return np.concatenate([solute_fp, solvent_fp, [temp, inv_temperature]]).astype(
        np.float32,
        copy=False,
    )


def compute_molecular_descriptors(smiles: str) -> RDKitDescriptorArray | None:
    """Compute the standard RDKit 2D descriptor vector for one molecule."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    try:
        descriptors = np.asarray(
            _RDKIT_DESCRIPTOR_CALCULATOR.CalcDescriptors(mol),
            dtype=np.float32,
        )
    except Exception:
        return None

    descriptors = np.nan_to_num(
        descriptors,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )
    # RDKit includes descriptors such as Ipc that can explode to ~1e18 for
    # large salts or highly connected molecules. Bounding the raw range keeps
    # the shared augmentation path numerically stable without changing the
    # descriptor dimensionality.
    return np.clip(
        descriptors,
        -DESCRIPTOR_RAW_ABS_CLIP,
        DESCRIPTOR_RAW_ABS_CLIP,
    )


def compute_descriptor_normalization_stats(
    smiles_iterable: Iterable[str],
) -> RDKitDescriptorStats:
    """Compute per-feature mean/std for the shared RDKit descriptor set."""
    descriptor_rows: list[np.ndarray] = []
    for smiles in smiles_iterable:
        descriptors = compute_molecular_descriptors(str(smiles))
        if descriptors is not None:
            descriptor_rows.append(descriptors)

    if not descriptor_rows:
        raise ValueError(
            "No valid molecules were available to compute descriptor statistics."
        )

    stacked = np.stack(descriptor_rows, axis=0).astype(np.float32, copy=False)
    mean = np.nan_to_num(
        stacked.mean(axis=0),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    ).astype(np.float32, copy=False)
    std = np.nan_to_num(
        stacked.std(axis=0),
        nan=1.0,
        posinf=1.0,
        neginf=1.0,
    ).astype(np.float32, copy=False)
    std = np.where(std < 1e-8, 1.0, std).astype(np.float32, copy=False)
    return mean, std


def validate_descriptor_normalization_stats(
    mean: np.ndarray | torch.Tensor | Iterable[float],
    std: np.ndarray | torch.Tensor | Iterable[float],
    *,
    descriptor_dim: int | None = None,
) -> RDKitDescriptorStats:
    """Validate shared descriptor normalization stats against the clipped pipeline."""
    mean_arr = np.asarray(mean, dtype=np.float32).reshape(-1)
    std_arr = np.asarray(std, dtype=np.float32).reshape(-1)

    if mean_arr.shape != std_arr.shape:
        raise ValueError(
            "Descriptor normalization mean/std must have the same shape."
        )
    if descriptor_dim is not None and mean_arr.shape[0] != int(descriptor_dim):
        raise ValueError(
            "Descriptor normalization size mismatch: "
            f"got {mean_arr.shape[0]}, expected {int(descriptor_dim)}."
        )
    if not np.isfinite(mean_arr).all() or not np.isfinite(std_arr).all():
        raise ValueError("Descriptor normalization stats must be finite.")
    if np.any(std_arr <= 0.0):
        raise ValueError("Descriptor normalization std must be strictly positive.")

    raw_clip_limit = DESCRIPTOR_RAW_ABS_CLIP * 1.01
    max_abs_mean = float(np.abs(mean_arr).max(initial=0.0))
    max_std = float(std_arr.max(initial=0.0))
    if max_abs_mean > raw_clip_limit:
        raise ValueError(
            "Descriptor normalization mean exceeds the shared raw descriptor clip. "
            "This checkpoint or cache likely came from an older unclipped "
            "descriptor pipeline."
        )
    if max_std > raw_clip_limit:
        raise ValueError(
            "Descriptor normalization std exceeds the shared raw descriptor clip. "
            "This checkpoint or cache likely came from an older unclipped "
            "descriptor pipeline."
        )

    return mean_arr, std_arr


class DescriptorNormalizer:
    """Fit and apply train-set normalization for RDKit descriptor augmentation."""

    def __init__(
        self,
        mean: np.ndarray | None = None,
        std: np.ndarray | None = None,
    ) -> None:
        self.mean = mean
        self.std = std

    def fit(self, source: object) -> "DescriptorNormalizer":
        """Fit descriptor statistics from a dataset, dataframe, or SMILES iterable."""
        source_obj = getattr(source, "df", source)
        if hasattr(source_obj, "columns"):
            columns = {str(column) for column in source_obj.columns}
            if {"solute_smiles", "solvent_smiles"}.issubset(columns):
                smiles_iterable = list(source_obj["solute_smiles"].astype(str)) + list(
                    source_obj["solvent_smiles"].astype(str)
                )
            elif "smiles" in columns:
                smiles_iterable = list(source_obj["smiles"].astype(str))
            else:
                raise ValueError(
                    "DescriptorNormalizer.fit() expected a dataframe with "
                    "`solute_smiles`/`solvent_smiles` or `smiles` columns."
                )
        else:
            smiles_iterable = [str(item) for item in source_obj]
        self.mean, self.std = compute_descriptor_normalization_stats(smiles_iterable)
        return self

    def transform(self, descriptors: np.ndarray) -> np.ndarray:
        """Apply z-score normalization with clipping for numerical stability."""
        if self.mean is None or self.std is None:
            raise ValueError("DescriptorNormalizer must be fit before transform().")
        normalized = (descriptors - self.mean) / np.clip(self.std, 1.0e-8, None)
        return np.clip(normalized, -DESCRIPTOR_Z_CLIP, DESCRIPTOR_Z_CLIP).astype(
            np.float32,
            copy=False,
        )


def smiles_to_descriptor_prior_features(smiles: str) -> np.ndarray | None:
    """Compute a compact fixed descriptor vector for prior-style heads."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    features = np.array(
        [
            Descriptors.MolWt(mol) / 500.0,
            Crippen.MolLogP(mol) / 5.0,
            Crippen.MolMR(mol) / 150.0,
            rdMolDescriptors.CalcTPSA(mol) / 200.0,
            float(Lipinski.NumHDonors(mol)) / 10.0,
            float(Lipinski.NumHAcceptors(mol)) / 12.0,
            float(rdMolDescriptors.CalcNumRotatableBonds(mol)) / 15.0,
            float(rdMolDescriptors.CalcNumRings(mol)) / 8.0,
            float(mol.GetNumHeavyAtoms()) / 60.0,
            float(rdMolDescriptors.CalcFractionCSP3(mol)),
        ],
        dtype=np.float32,
    )
    return np.nan_to_num(features, nan=0.0, posinf=10.0, neginf=-10.0)


def smiles_to_group_prior_features(smiles: str) -> np.ndarray | None:
    """Compute fixed fragment-count features for group-contribution priors."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    heavy_atom_count = float(mol.GetNumHeavyAtoms())
    sp3_carbon_count = 0.0
    sp2_sp_carbon_count = 0.0
    aromatic_carbon_count = 0.0
    n_count = 0.0
    o_count = 0.0
    s_p_count = 0.0
    halogen_count = 0.0

    for atom in mol.GetAtoms():
        atomic_num = atom.GetAtomicNum()
        if atomic_num == 6:
            if atom.GetIsAromatic():
                aromatic_carbon_count += 1.0
            elif atom.GetHybridization() == Chem.rdchem.HybridizationType.SP3:
                sp3_carbon_count += 1.0
            else:
                sp2_sp_carbon_count += 1.0
        elif atomic_num == 7:
            n_count += 1.0
        elif atomic_num == 8:
            o_count += 1.0
        elif atomic_num in (15, 16):
            s_p_count += 1.0
        elif atomic_num in (9, 17, 35, 53):
            halogen_count += 1.0

    features = np.array(
        [
            heavy_atom_count,
            sp3_carbon_count,
            sp2_sp_carbon_count,
            aromatic_carbon_count,
            n_count,
            o_count,
            s_p_count,
            halogen_count,
            float(rdMolDescriptors.CalcNumRings(mol)),
            float(rdMolDescriptors.CalcNumRotatableBonds(mol)),
            float(Fragments.fr_Al_OH(mol)),
            float(Fragments.fr_Ar_OH(mol)),
            float(Fragments.fr_COO(mol)),
            float(Fragments.fr_ester(mol)),
            float(Fragments.fr_ether(mol)),
            float(Fragments.fr_amide(mol)),
            float(
                Fragments.fr_NH0(mol)
                + Fragments.fr_NH1(mol)
                + Fragments.fr_NH2(mol)
            ),
            float(Fragments.fr_nitrile(mol)),
            float(Fragments.fr_nitro(mol)),
            float(Fragments.fr_C_O_noCOO(mol)),
        ],
        dtype=np.float32,
    )
    return np.nan_to_num(features, nan=0.0, posinf=100.0, neginf=0.0)


# ------------------------------------------------------------------ #
#  Feature dimensions (computed once at import time)                   #
# ------------------------------------------------------------------ #

def _compute_dims() -> tuple[int, int]:
    """Compute feature dimensions from a reference molecule."""
    g = smiles_to_graph("C")  # methane
    if g is None:
        return 35, 8  # fallback
    node_dim = g.x.shape[1]
    edge_dim = g.edge_attr.shape[1]
    return node_dim, edge_dim


NODE_FEAT_DIM, EDGE_FEAT_DIM = _compute_dims()
RDKIT_DESCRIPTOR_DIM = len(RDKIT_DESCRIPTOR_NAMES)
DESCRIPTOR_PRIOR_DIM = int(
    smiles_to_descriptor_prior_features("CCO").shape[0]
)
GROUP_PRIOR_DIM = int(
    smiles_to_group_prior_features("CCO").shape[0]
)
