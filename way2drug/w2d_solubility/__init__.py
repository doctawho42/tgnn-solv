"""Веб-версия модели растворимости TGNN-Solv для платформы Way2Drug."""
from .predictor import SolubilityPredictor, canonical_smiles

__all__ = ["SolubilityPredictor", "canonical_smiles"]
