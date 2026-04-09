#!/usr/bin/env python
"""Optimize process-facing solvent and temperature decisions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import torch

from tgnn_solv.applications import ProcessOptimizer
from tgnn_solv.inference import load_directgnn_model, load_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=["crystallization", "extraction", "reaction_medium", "solvent_system"])
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--device", default=None)
    parser.add_argument("--output", required=True)

    parser.add_argument("--solute", help="Target solute SMILES")
    parser.add_argument("--source-solvent", help="Source solvent for extraction")
    parser.add_argument("--reactant", action="append", default=None, help="Reactant SMILES; repeatable")
    parser.add_argument("--product", help="Product SMILES")

    parser.add_argument("--T", type=float, default=298.15, help="Single operating temperature in K")
    parser.add_argument("--T-min", type=float, default=273.0)
    parser.add_argument("--T-max", type=float, default=373.0)
    parser.add_argument("--target-yield", type=float, default=0.80)
    parser.add_argument("--target-solubility-min", type=float, default=None)
    parser.add_argument("--target-solubility-max", type=float, default=None)

    parser.add_argument("--min-green-score", type=int, default=None)
    parser.add_argument("--max-toxicity-class", type=int, default=None)
    parser.add_argument("--max-boiling-point-k", type=float, default=None)
    parser.add_argument("--min-dissolving-concentration-mg-ml", type=float, default=None)
    parser.add_argument("--min-partition-coefficient", type=float, default=None)
    parser.add_argument("--min-reactant-solubility-mg-ml", type=float, default=None)
    parser.add_argument("--min-selectivity-ratio", type=float, default=None)
    return parser.parse_args()


def detect_and_load_model(checkpoint_path: str, device: torch.device) -> tuple[Any, Any, str]:
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model_class = str(checkpoint.get("model_class", "")).lower()
    model_type = str(checkpoint.get("model_type", "")).lower()
    top_keys = {str(key) for key in checkpoint.keys()}
    if ("directgnn" in model_class or "direct" in model_type) and ({"model_state", "model_state_dict"} & top_keys):
        model, cfg = load_directgnn_model(checkpoint_path, device=device)
        return model, cfg, "direct_gnn"
    model, cfg = load_model(checkpoint_path, device=device)
    return model, cfg, "tgnn_solv"


def json_ready(obj: Any) -> Any:
    if isinstance(obj, pd.DataFrame):
        return obj.where(obj.notna(), None).to_dict(orient="records")
    if isinstance(obj, list):
        return [json_ready(item) for item in obj]
    if isinstance(obj, dict):
        return {key: json_ready(value) for key, value in obj.items()}
    return obj


def main() -> None:
    args = parse_args()
    device = torch.device(args.device) if args.device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, cfg, family = detect_and_load_model(args.checkpoint, device)
    optimizer = ProcessOptimizer(model, cfg, device)

    constraints = {
        "min_green_score": args.min_green_score,
        "max_toxicity_class": args.max_toxicity_class,
        "max_boiling_point_K": args.max_boiling_point_k,
        "min_dissolving_concentration_mg_mL": args.min_dissolving_concentration_mg_ml,
        "min_partition_coefficient": args.min_partition_coefficient,
        "min_reactant_solubility_mg_mL": args.min_reactant_solubility_mg_ml,
        "min_selectivity_ratio": args.min_selectivity_ratio,
    }
    constraints = {key: value for key, value in constraints.items() if value is not None}

    if args.mode == "crystallization":
        if not args.solute:
            raise SystemExit("--solute is required for crystallization mode")
        result = optimizer.optimize_crystallization(
            args.solute,
            target_yield=args.target_yield,
            T_range=(args.T_min, args.T_max),
            constraints=constraints,
        )
    elif args.mode == "extraction":
        if not args.solute or not args.source_solvent:
            raise SystemExit("--solute and --source-solvent are required for extraction mode")
        result = optimizer.optimize_extraction(
            args.solute,
            args.source_solvent,
            T=args.T,
            constraints=constraints,
        )
    elif args.mode == "reaction_medium":
        if not args.reactant or not args.product:
            raise SystemExit("--reactant and --product are required for reaction_medium mode")
        result = optimizer.optimize_reaction_medium(
            list(args.reactant),
            args.product,
            T_reaction=args.T,
            constraints=constraints,
        )
    else:
        if not args.solute or args.target_solubility_min is None or args.target_solubility_max is None:
            raise SystemExit("--solute, --target-solubility-min, and --target-solubility-max are required for solvent_system mode")
        result = optimizer.design_solvent_system(
            args.solute,
            (args.target_solubility_min, args.target_solubility_max),
            T=args.T,
        )

    payload = {
        "mode": args.mode,
        "checkpoint": args.checkpoint,
        "model_family": family,
        "constraints": constraints,
        "result": json_ready(result),
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote process optimization report to {output_path}")


if __name__ == "__main__":
    main()
