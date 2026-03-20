"""
Model and training configuration.

All physical constants are fixed (not learnable).
Scale factors control the magnitude of predicted quantities
to keep them in a numerically stable range for the network.
"""

from dataclasses import dataclass


@dataclass
class TGNNSolvConfig:
    """Complete configuration for TGNN-Solv model."""

    # --- Architecture ---
    hidden_dim: int = 256
    n_gnn_layers: int = 6
    n_cross_attn_layers: int = 3
    n_attn_heads: int = 8
    dropout: float = 0.1
    pair_dim: int = 512

    # --- Physics constants (NOT learnable) ---
    R: float = 8.314          # Gas constant, J/(mol·K)
    T_ref: float = 298.15     # Reference temperature, K

    # --- Constrained activation ranges ---
    T_m_min: float = 100.0    # Min melting point, K
    T_m_max: float = 700.0    # Max melting point, K
    alpha_min: float = 0.1    # Min NRTL non-randomness
    alpha_max: float = 0.6    # Max NRTL non-randomness

    # --- Scale factors for prediction heads ---
    S_H: float = 5000.0       # dH_fus scale, J/mol
    S_Cp: float = 100.0       # dCp_fus scale, J/(mol·K)
    S_g: float = 5000.0      # NRTL energy scale, J/mol
    S_aT: float = 10.0        # NRTL temperature coeff scale
    S_delta: float = 10.0     # Hansen parameter scale, MPa^0.5

    # --- SLE solver ---
    n_iter_train: int = 5
    n_iter_eval: int = 20
    damping: float = 0.7
    use_implicit_diff: bool = True

    # --- Numerical stability ---
    eps: float = 1e-10
    tau_clamp: float = 30.0
    grad_clip: float = 1.0

    # --- Training ---
    batch_size: int = 64
    lr_phase1: float = 3e-4
    lr_phase2: float = 1e-4
    lr_phase3: float = 1e-6
    epochs_phase1: int = 50
    epochs_phase2: int = 200
    epochs_phase3: int = 50
    warmup_epochs: int = 5
    patience: int = 20