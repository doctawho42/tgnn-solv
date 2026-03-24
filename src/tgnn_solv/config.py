"""
Model and training configuration.

All physical constants are fixed (not learnable).
Scale factors control the magnitude of predicted quantities
to keep them in a numerically stable range for the network.
"""

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Dict, Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class TGNNSolvConfig:
    """Complete configuration for TGNN-Solv model."""

    # --- Architecture ---
    hidden_dim: int = 256
    n_gnn_layers: int = 6
    encoder_role_mode: str = "shared_residual"  # "shared_residual" or "split_late"
    encoder_role_specific_layers: int = 2
    n_cross_attn_layers: int = 3
    n_attn_heads: int = 8
    dropout: float = 0.1
    pair_dim: int = 512
    interaction_mode: str = "cross_attn"  # "cross_attn" or "bipartite"
    nrtl_tau_mode: str = "ref_invT"  # "ref_invT", "legacy", or "abc"
    set2set_steps: int = 3
    use_solvent_moe: bool = True
    solvent_moe_experts: int = 6
    solvent_moe_hidden: int = 256
    solvent_type_emb_dim: int = 16
    use_temperature_in_encoder: bool = False
    use_temperature_in_interaction: bool = False
    use_temperature_in_nrtl_head: bool = True

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
    S_tau_a: float = 1.0      # NRTL tau offset scale (dimensionless)
    S_tau_b: float = 300.0    # NRTL tau 1/T scale (K)
    S_tau_c: float = 1.0      # NRTL tau log(T/T_ref) scale (dimensionless)
    S_tau_ref: float = 1.0    # NRTL tau(T_ref) scale (dimensionless)
    S_tau_inv: float = 1.0    # NRTL inverse-temperature slope scale (dimensionless)
    S_delta: float = 10.0     # Hansen parameter scale, MPa^0.5

    # --- SLE solver ---
    n_iter_train: int = 5
    n_iter_eval: int = 20
    damping: float = 0.7
    solver_min_damping: float = 0.1
    solver_tol_train: float = 1e-5
    solver_tol_eval: float = 1e-7
    solver_adaptive_damping: bool = True
    use_implicit_diff: bool = True

    # --- Numerical stability ---
    eps: float = 1e-10
    tau_clamp: float = 30.0
    grad_clip: float = 1.0
    correction_max_abs: float = 2.0
    correction_Tm_max_delta: float = 60.0
    correction_dH_fraction: float = 0.25
    correction_tau_max_delta: float = 2.0
    monotonicity_force_explicit: bool = False

    # --- Training ---
    batch_size: int = 64
    use_pair_temperature_batching: bool = True
    pair_temperature_min_group_size: int = 2
    pair_temperature_group_chunk_size: int = 4
    lr_phase1: float = 3e-4
    lr_phase2: float = 1e-4
    lr_phase3: float = 1e-6
    epochs_phase1: int = 50
    epochs_phase2: int = 200
    epochs_phase3: int = 50
    warmup_epochs: int = 5
    patience: int = 20

    phase1_loss_weights: Optional[Dict[str, float]] = None
    phase2_loss_weights: Optional[Dict[str, float]] = None
    phase3_loss_weights: Optional[Dict[str, float]] = None

    @classmethod
    def from_yaml(cls, path: str) -> "TGNNSolvConfig":
        """
        Load configuration from a YAML file.

        Supports nested YAML structure (model, training, data, loss_weights
        sections).  Flattens nested dicts and filters to only fields present
        in TGNNSolvConfig.  The ``loss_weights`` section receives special
        handling: its ``phase1``/``phase2``/``phase3`` sub-dicts are mapped
        to ``phase1_loss_weights`` etc.

        Unknown keys are silently ignored.
        """
        if yaml is None:
            raise ImportError(
                "PyYAML is required for from_yaml(). "
                "Install with: pip install pyyaml"
            )

        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)

        if config_dict is None:
            config_dict = {}

        # ✦ CHANGED — two-level flattening with phase-weight mapping
        _PHASE_MAP = {
            "phase1": "phase1_loss_weights",
            "phase2": "phase2_loss_weights",
            "phase3": "phase3_loss_weights",
        }

        flat_dict: dict = {}
        for key, value in config_dict.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    mapped = _PHASE_MAP.get(nested_key)
                    if mapped is not None and isinstance(nested_value, dict):
                        flat_dict[mapped] = nested_value
                    elif not isinstance(nested_value, dict):
                        flat_dict[nested_key] = nested_value
                    # else: deeper nesting without mapping → skip
            else:
                flat_dict[key] = value

        valid_fields = {f.name for f in fields(cls)}
        filtered_dict = {
            k: v for k, v in flat_dict.items() if k in valid_fields
        }

        return cls(**filtered_dict)

    
    def to_yaml(self, path: str) -> None:
        """
        Save configuration to a YAML file.
        
        Args:
            path: Path to output YAML file. Parent directories are created if needed.
        """
        # Create parent directories if they don't exist
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        # Convert dataclass to dict and save to YAML
        config_dict = asdict(self)
        
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
