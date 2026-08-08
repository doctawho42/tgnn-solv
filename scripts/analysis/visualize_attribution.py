#!/usr/bin/env python
"""Visualize atom-level Integrated Gradients attribution."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tgnn_solv.device import resolve_device  # noqa: E402
from tgnn_solv.inference import load_directgnn_model, load_model  # noqa: E402
from tgnn_solv.interpretation import (  # noqa: E402
    AtomAttribution,
    atom_labels_from_smiles,
    build_single_system_inputs,
)


def _load_any_model(checkpoint: Path, device: torch.device):
    try:
        model, cfg = load_model(str(checkpoint), device=device)
        return model, cfg, "TGNN-Solv"
    except Exception as tgnn_error:
        try:
            model, cfg = load_directgnn_model(str(checkpoint), device=device)
            return model, cfg, "DirectGNN"
        except Exception as direct_error:
            raise RuntimeError(
                f"Could not load checkpoint as TGNN-Solv or DirectGNN.\n"
                f"TGNN error: {tgnn_error}\nDirectGNN error: {direct_error}"
            ) from direct_error


def _blend_with_white(rgb: tuple[float, float, float], strength: float) -> tuple[float, float, float]:
    strength = float(np.clip(strength, 0.0, 1.0))
    return tuple((1.0 - strength) * 1.0 + strength * channel for channel in rgb)


def attribution_colors(values: np.ndarray) -> dict[int, tuple[float, float, float]]:
    """Map normalized attribution values to RDKit highlight colors."""
    colors: dict[int, tuple[float, float, float]] = {}
    red = (0.92, 0.20, 0.20)
    blue = (0.15, 0.35, 0.92)
    for idx, value in enumerate(values):
        strength = min(abs(float(value)), 1.0)
        colors[idx] = _blend_with_white(red if value >= 0 else blue, strength)
    return colors


def render_attribution(
    smiles: str,
    attributions: np.ndarray,
    output: Path,
    *,
    title: str,
    width: int = 900,
    height: int = 620,
) -> None:
    from rdkit import Chem
    from rdkit.Chem import rdDepictor
    from rdkit.Chem.Draw import rdMolDraw2D

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Cannot parse SMILES: {smiles}")
    mol = Chem.RemoveHs(mol)
    rdDepictor.Compute2DCoords(mol)

    max_abs = float(np.max(np.abs(attributions))) if attributions.size else 0.0
    values = attributions / max_abs if max_abs > 0 else np.zeros_like(attributions)
    highlight_atoms = list(range(mol.GetNumAtoms()))
    highlight_colors = attribution_colors(values)
    highlight_radii = {
        idx: 0.22 + 0.18 * min(abs(float(values[idx])), 1.0)
        for idx in highlight_atoms
    }

    drawer = rdMolDraw2D.MolDraw2DCairo(width, height)
    options = drawer.drawOptions()
    options.clearBackground = False
    options.padding = 0.08
    options.legendFontSize = 24
    options.atomHighlightsAreCircles = True
    try:
        options.useBWAtomPalette()
    except AttributeError:
        pass
    drawer.DrawMolecule(
        mol,
        legend=title,
        highlightAtoms=highlight_atoms,
        highlightAtomColors=highlight_colors,
        highlightAtomRadii=highlight_radii,
    )
    drawer.FinishDrawing()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(drawer.GetDrawingText())


def compute_for_checkpoint(
    checkpoint: Path,
    solute: str,
    solvent: str,
    temperature: float,
    device: torch.device,
    *,
    n_steps: int,
    attribute_to: str,
) -> tuple[np.ndarray, list[str], str]:
    model, _cfg, family = _load_any_model(checkpoint, device)
    solute_graph, solvent_graph, targets = build_single_system_inputs(
        model,
        solute,
        solvent,
        temperature,
        device=device,
    )
    attribution = AtomAttribution(model, device=device).integrated_gradients(
        solute_graph,
        solvent_graph,
        targets,
        n_steps=n_steps,
        attribute_to=attribute_to,
    )
    labels = atom_labels_from_smiles(solute if attribute_to == "solute" else solvent)
    return attribution.numpy(), labels, family


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--compare-checkpoint", type=Path, default=None)
    parser.add_argument("--solute", required=True)
    parser.add_argument("--solvent", required=True)
    parser.add_argument("--T", type=float, default=298.15)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--attribute-to", choices=["solute", "solvent"], default="solute")
    parser.add_argument("--n-steps", type=int, default=50)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    device = resolve_device(args.device)
    attr, labels, family = compute_for_checkpoint(
        args.checkpoint,
        args.solute,
        args.solvent,
        args.T,
        device,
        n_steps=args.n_steps,
        attribute_to=args.attribute_to,
    )
    render_attribution(
        args.solute if args.attribute_to == "solute" else args.solvent,
        attr,
        args.output,
        title=f"{family}: Integrated Gradients",
    )
    payload = {
        "checkpoint": str(args.checkpoint),
        "model_family": family,
        "solute": args.solute,
        "solvent": args.solvent,
        "T": args.T,
        "attribute_to": args.attribute_to,
        "atom_labels": labels,
        "attributions": [float(v) for v in attr],
    }
    args.output.with_suffix(".json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if args.compare_checkpoint is not None:
        compare_attr, _, compare_family = compute_for_checkpoint(
            args.compare_checkpoint,
            args.solute,
            args.solvent,
            args.T,
            device,
            n_steps=args.n_steps,
            attribute_to=args.attribute_to,
        )
        compare_output = args.output.with_name(f"{args.output.stem}_compare{args.output.suffix}")
        render_attribution(
            args.solute if args.attribute_to == "solute" else args.solvent,
            compare_attr,
            compare_output,
            title=f"{compare_family}: Integrated Gradients",
        )
        compare_payload = dict(payload)
        compare_payload.update(
            {
                "checkpoint": str(args.compare_checkpoint),
                "model_family": compare_family,
                "attributions": [float(v) for v in compare_attr],
            }
        )
        compare_output.with_suffix(".json").write_text(
            json.dumps(compare_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    print(f"[attribution] wrote {args.output}")


if __name__ == "__main__":
    main()
