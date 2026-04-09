#!/usr/bin/env python
"""Screen a built-in solvent library for one solute."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import torch

from tgnn_solv.applications import SolventScreener
from tgnn_solv.inference import load_directgnn_model, load_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solute", required=True, help="Target solute SMILES")
    parser.add_argument("--checkpoint", required=True, help="TGNN-Solv or DirectGNN checkpoint")
    parser.add_argument("--T", type=float, default=298.15, help="Screen temperature in K")
    parser.add_argument("--top-k", type=int, default=20, help="Return top K solvents")
    parser.add_argument("--min-solubility-mg-ml", type=float, default=None, help="Minimum approximate mg/mL")
    parser.add_argument("--max-toxicity-class", type=int, default=None, help="Maximum toxicity severity (1=Class 3/not classified, 2=Class 2, 3=Class 1)")
    parser.add_argument("--min-green-score", type=int, default=None, help="Minimum green score")
    parser.add_argument("--max-boiling-point-k", type=float, default=None, help="Maximum boiling point")
    parser.add_argument("--exclude-class", action="append", default=None, help="Exclude solvent class; repeatable")
    parser.add_argument("--require-water-miscible", action="store_true", help="Keep only water-miscible solvents")
    parser.add_argument("--output", required=True, help="Path to JSON output")
    parser.add_argument("--device", default=None, help="Torch device, default auto")
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


def json_ready_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    return df.where(df.notna(), None).to_dict(orient="records")


def main() -> None:
    args = parse_args()
    device = torch.device(args.device) if args.device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, cfg, family = detect_and_load_model(args.checkpoint, device)
    screener = SolventScreener(model, cfg, device)

    filters = {
        "min_solubility_mg_mL": args.min_solubility_mg_ml,
        "max_toxicity_class": args.max_toxicity_class,
        "min_green_score": args.min_green_score,
        "max_boiling_point_K": args.max_boiling_point_k,
        "exclude_classes": args.exclude_class or [],
        "require_water_miscible": args.require_water_miscible,
    }
    filters = {key: value for key, value in filters.items() if value not in (None, [], False)}

    screen_df = screener.screen(
        args.solute,
        T=args.T,
        top_k=args.top_k,
        filters=filters,
        return_details=True,
    )
    best_solvent = None
    crystallization_payload: dict[str, Any] | None = None
    green_payload: list[dict[str, Any]] | None = None
    if not screen_df.empty:
        best_row = screen_df.iloc[0]
        best_solvent = {
            "name": best_row["solvent_name"],
            "smiles": best_row["solvent_smiles"],
            "approx_mg_mL": best_row["solubility_mg_mL"],
            "ln_x2": best_row["ln_x2"],
        }
        crystallization = screener.crystallization_window(
            args.solute,
            str(best_row["solvent_smiles"]),
            n_points=18,
        )
        crystallization_payload = {
            key: (json_ready_records(value) if isinstance(value, pd.DataFrame) else value)
            for key, value in crystallization.items()
        }
        green_payload = json_ready_records(
            screener.green_solvent_replacement(
                args.solute,
                str(best_row["solvent_smiles"]),
                T=args.T,
                min_solubility_fraction=0.5,
            ).head(10)
        )

    output_payload = {
        "solute_smiles": args.solute,
        "checkpoint": str(args.checkpoint),
        "model_family": family,
        "temperature_K": args.T,
        "top_k": args.top_k,
        "filters": filters,
        "screening_rows": json_ready_records(screen_df),
        "best_solvent": best_solvent,
        "crystallization_window_top_solvent": crystallization_payload,
        "green_replacements_top_solvent": green_payload,
        "assumptions": screen_df.attrs.get("assumptions", {}),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")
    print(f"Wrote solvent screening report to {output_path}")


if __name__ == "__main__":
    main()
