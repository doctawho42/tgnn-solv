#!/usr/bin/env python
"""Run PK-relevant solubility profiling for one candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import torch

from tgnn_solv.applications import PKSolubilityProfiler
from tgnn_solv.inference import load_directgnn_model, load_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smiles", required=True, help="Candidate SMILES")
    parser.add_argument("--dose-mg", type=float, default=100.0, help="Dose strength for oral GI profiling")
    parser.add_argument("--checkpoint", required=True, help="TGNN-Solv or DirectGNN checkpoint")
    parser.add_argument("--output", required=True, help="Path to JSON output")
    parser.add_argument("--device", default=None, help="Torch device; default auto")
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


def json_ready_df(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    return df.where(df.notna(), None).to_dict(orient="records")


def main() -> None:
    args = parse_args()
    device = torch.device(args.device) if args.device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, cfg, family = detect_and_load_model(args.checkpoint, device)
    profiler = PKSolubilityProfiler(model, cfg, device)

    gi_profile = profiler.gi_tract_profile(args.smiles, dose_mg=float(args.dose_mg))
    media_screen = profiler.biorelevant_media_screen(args.smiles)
    iv_screen = profiler.iv_formulation_screening(args.smiles)
    topical_screen = profiler.topical_vehicle_screening(args.smiles)

    payload = {
        "smiles": args.smiles,
        "checkpoint": args.checkpoint,
        "model_family": family,
        "dose_mg": float(args.dose_mg),
        "gi_tract_profile": gi_profile,
        "biorelevant_media_screen": media_screen,
        "iv_formulation_screening": json_ready_df(iv_screen),
        "topical_vehicle_screening": json_ready_df(topical_screen),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote PK profile report to {output_path}")


if __name__ == "__main__":
    main()
