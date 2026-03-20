"""
Data pipeline for TGNN-Solv.

Modules:
  utils    — SMILES canonicalization, download, scaffold
  sources  — BigSolDB, Bradley MP, Hansen, IDAC, CombiSolv loaders
  builder  — DataBuilder merging all sources
  dataset  — PyTorch Dataset and DataLoader factories
  split    — Scaffold-based train/val/test splitting
"""

from .utils import canonicalize, get_scaffold, DATA_DIR, RAW_DIR, PROCESSED_DIR
from .sources import (
    load_bigsoldb,
    load_melting_points,
    load_fusion_enthalpies,
    load_hansen,
    load_idac,
)
from .builder import DataBuilder, filter_for_sle
from .dataset import TGNNSolvDataset, collate_fn, make_loaders
from .split import scaffold_split