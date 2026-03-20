"""
Baseline: Dual-GNN with thermometer temperature encoding.

Same GNN backbone for solute and solvent, graph-level vectors
concatenated, temperature encoded as thermometer bins.
No physics layer, no NRTL, no SLE — pure data-driven.
"""

from .direct_gnn import DirectGNN, DirectGNNTrainer
from .runner import run_baseline, compare_with_tgnn