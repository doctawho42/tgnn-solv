#!/usr/bin/env python3
"""Build finite-composition Modified-UNIFAC pseudo-coverage for SLE pairs."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from tqdm import tqdm

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPT_DIR.parents[0]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tgnn_solv.unifac import modified_unifac_groups, modified_unifac_lngamma_binary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a finite-composition Modified-UNIFAC pseudo-coverage artifact "
            "for exact SLE pairs, with optional restriction to the current "
            "measurement-backed ThermoML gap list."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--processed-dir",
        default="notebooks/data/processed",
        help="Directory containing canonical train.csv / val.csv / test.csv.",
    )
    parser.add_argument(
        "--target-split",
        action="append",
        default=[],
        choices=("train", "val", "test"),
        help="Restrict the SLE target set to one or more splits. Defaults to all.",
    )
    parser.add_argument(
        "--gap-csv",
        default="results/thermoml_targeted_coverage/candidate_measurement_missing_sle_pairs.csv",
        help=(
            "Optional directed-pair gap list used to focus pseudo-coverage on "
            "the current missing activity-signal pairs. Pass an empty string to "
            "disable restriction."
        ),
    )
    parser.add_argument(
        "--temperature-mode",
        choices=("pair_median", "exact_rows"),
        default="pair_median",
        help=(
            "Use one representative median temperature per directed pair or "
            "evaluate every unique supervised pair-temperature row."
        ),
    )
    parser.add_argument(
        "--composition-grid",
        default="0.01,0.02,0.05,0.10,0.20",
        help="Comma-separated solute mole-fraction grid used for pseudo activity states.",
    )
    parser.add_argument(
        "--temperature-decimals",
        type=int,
        default=3,
        help="Round temperatures before UNIFAC evaluation and deduplication.",
    )
    parser.add_argument(
        "--composition-decimals",
        type=int,
        default=6,
        help="Round composition values before UNIFAC evaluation and deduplication.",
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=0,
        help="Optional debug cap on directed pairs after all filtering.",
    )
    parser.add_argument(
        "--allow-approximate-fallback",
        action="store_true",
        help=(
            "Allow low-cost SMILES standardization fallbacks when exact DDBST "
            "group lookup fails: no stereo, largest fragment, neutralized form."
        ),
    )
    parser.add_argument(
        "--out-dir",
        default="results/unifac_finite_activity_coverage",
        help="Output directory for the pseudo-coverage artifact.",
    )
    return parser.parse_args()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _parse_grid(spec: str, *, decimals: int) -> list[float]:
    values: list[float] = []
    for chunk in str(spec).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        value = round(float(chunk), int(decimals))
        if not math.isfinite(value) or value <= 0.0 or value >= 1.0:
            raise ValueError(f"Invalid composition value {chunk!r}; expected 0 < x < 1.")
        values.append(value)
    values = sorted(dict.fromkeys(values))
    if not values:
        raise ValueError("Composition grid is empty after parsing.")
    return values


def _load_sle_rows(processed_dir: Path, splits: list[str], *, temperature_decimals: int) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for split in splits:
        path = processed_dir / f"{split}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing processed split CSV: {path}")
        df = pd.read_csv(path, low_memory=False)
        if "has_solubility" in df.columns:
            df = df.loc[_bool_series(df["has_solubility"])].copy()
        if df.empty:
            continue
        df["split"] = split
        df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce").round(
            int(temperature_decimals)
        )
        df = df.dropna(subset=["solute_smiles", "solvent_smiles", "temperature"]).copy()
        df["directed_pair_key"] = (
            df["solute_smiles"].astype(str).str.strip()
            + ">>"
            + df["solvent_smiles"].astype(str).str.strip()
        )
        frames.append(
            df[
                [
                    "split",
                    "solute_smiles",
                    "solvent_smiles",
                    "solute_name",
                    "solvent_name",
                    "temperature",
                    "directed_pair_key",
                ]
            ].copy()
        )
    if not frames:
        return pd.DataFrame(
            columns=[
                "split",
                "solute_smiles",
                "solvent_smiles",
                "solute_name",
                "solvent_name",
                "temperature",
                "directed_pair_key",
            ]
        )
    return pd.concat(frames, ignore_index=True).drop_duplicates().reset_index(drop=True)


def _load_gap_pairs(path: str | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    gap_path = Path(path)
    if not gap_path.exists():
        raise FileNotFoundError(f"Missing gap CSV: {gap_path}")
    frame = pd.read_csv(gap_path, low_memory=False).copy()
    required = {"split", "solute_smiles", "solvent_smiles", "directed_pair_key"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{gap_path} is missing required columns: {sorted(missing)}")
    return frame


def _build_target_states(
    rows: pd.DataFrame,
    *,
    temperature_mode: str,
) -> pd.DataFrame:
    if rows.empty:
        return rows.copy()

    group_cols = [
        "split",
        "solute_smiles",
        "solvent_smiles",
        "directed_pair_key",
    ]
    pair_summary = (
        rows.groupby(group_cols, dropna=False, sort=True)
        .agg(
            solute_name=("solute_name", "first"),
            solvent_name=("solvent_name", "first"),
            n_source_rows=("temperature", "size"),
            n_temperatures=("temperature", "nunique"),
            temp_min=("temperature", "min"),
            temp_max=("temperature", "max"),
            temperature_median=("temperature", "median"),
        )
        .reset_index()
    )
    if temperature_mode == "pair_median":
        out = pair_summary.copy()
        out["temperature"] = pd.to_numeric(out["temperature_median"], errors="coerce")
        out["temperature_mode"] = "pair_median"
        return out

    exact = rows.merge(pair_summary, on=group_cols, how="left")
    exact["temperature_mode"] = "exact_rows"
    return exact


def _pair_group_status(
    states: pd.DataFrame,
    *,
    allow_approximate_fallback: bool,
) -> pd.DataFrame:
    if states.empty:
        return pd.DataFrame()
    pair_cols = [
        "split",
        "solute_smiles",
        "solvent_smiles",
        "solute_name",
        "solvent_name",
        "directed_pair_key",
        "n_source_rows",
        "n_temperatures",
        "temp_min",
        "temp_max",
    ]
    pair_meta = states[pair_cols].drop_duplicates().reset_index(drop=True)
    statuses: list[dict[str, Any]] = []
    for row in tqdm(pair_meta.itertuples(index=False), total=len(pair_meta), desc="UNIFAC pair groups"):
        sol_groups = modified_unifac_groups(
            str(row.solute_smiles),
            allow_approximate_fallback=allow_approximate_fallback,
        )
        slv_groups = modified_unifac_groups(
            str(row.solvent_smiles),
            allow_approximate_fallback=allow_approximate_fallback,
        )
        has_solute_groups = sol_groups is not None
        has_solvent_groups = slv_groups is not None
        if has_solute_groups and has_solvent_groups:
            status = "ready"
        elif not has_solute_groups and not has_solvent_groups:
            status = "missing_both_groups"
        elif not has_solute_groups:
            status = "missing_solute_groups"
        else:
            status = "missing_solvent_groups"
        statuses.append(
            {
                "split": row.split,
                "solute_smiles": row.solute_smiles,
                "solvent_smiles": row.solvent_smiles,
                "solute_name": row.solute_name,
                "solvent_name": row.solvent_name,
                "directed_pair_key": row.directed_pair_key,
                "n_source_rows": int(row.n_source_rows),
                "n_temperatures": int(row.n_temperatures),
                "temp_min": row.temp_min,
                "temp_max": row.temp_max,
                "has_solute_groups": bool(has_solute_groups),
                "has_solvent_groups": bool(has_solvent_groups),
                "pair_group_status": status,
            }
        )
    return pd.DataFrame(statuses)


def _coverage_by_split(
    targets: pd.DataFrame,
    covered_rows: pd.DataFrame,
    pair_status: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in sorted(targets["split"].dropna().unique().tolist()):
        target_subset = targets.loc[targets["split"] == split].copy()
        covered_subset = covered_rows.loc[covered_rows["split"] == split].copy() if not covered_rows.empty else pd.DataFrame()
        status_subset = pair_status.loc[pair_status["split"] == split].copy() if not pair_status.empty else pd.DataFrame()
        rows.append(
            {
                "split": split,
                "n_target_pairs": int(target_subset["directed_pair_key"].nunique()),
                "n_target_states": int(
                    target_subset[["directed_pair_key", "temperature"]].drop_duplicates().shape[0]
                ),
                "n_source_pair_temperature_states": int(status_subset["n_source_rows"].sum())
                if not status_subset.empty
                else 0,
                "n_source_pair_temperature_states_with_groups": int(
                    status_subset.loc[
                        status_subset["pair_group_status"].eq("ready"),
                        "n_source_rows",
                    ].sum()
                )
                if not status_subset.empty
                else 0,
                "n_pairs_with_groups": int(
                    status_subset.loc[
                        status_subset["pair_group_status"].eq("ready"),
                        "directed_pair_key",
                    ].nunique()
                )
                if not status_subset.empty
                else 0,
                "n_pairs_covered": int(covered_subset["directed_pair_key"].nunique()) if not covered_subset.empty else 0,
                "n_states_covered": int(
                    covered_subset[["directed_pair_key", "temperature"]].drop_duplicates().shape[0]
                )
                if not covered_subset.empty
                else 0,
                "pair_coverage_fraction": (
                    float(covered_subset["directed_pair_key"].nunique() / target_subset["directed_pair_key"].nunique())
                    if not target_subset.empty
                    else 0.0
                ),
                "state_coverage_fraction": (
                    float(
                        covered_subset[["directed_pair_key", "temperature"]].drop_duplicates().shape[0]
                        / max(target_subset[["directed_pair_key", "temperature"]].drop_duplicates().shape[0], 1)
                    )
                    if not target_subset.empty
                    else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


def _write_summary_md(
    summary: dict[str, Any],
    *,
    coverage_by_split: pd.DataFrame,
    path: Path,
) -> None:
    lines = [
        "# UNIFAC Finite-Activity Coverage",
        "",
        f"- Target directed pairs: `{summary.get('n_target_pairs', 0)}`",
        f"- Target pair-temperature states: `{summary.get('n_target_states', 0)}`",
        f"- Composition grid: `{', '.join(str(v) for v in summary.get('composition_grid', []))}`",
        f"- Generated pseudo rows: `{summary.get('n_generated_rows', 0)}`",
        f"- Covered directed pairs: `{summary.get('n_covered_pairs', 0)}`",
        f"- Covered pair-temperature states: `{summary.get('n_covered_states', 0)}`",
        f"- Pair coverage: `{summary.get('pair_coverage_fraction', 0.0):.2%}`",
        f"- State coverage: `{summary.get('state_coverage_fraction', 0.0):.2%}`",
        f"- Source pair-temperature states on the target set: `{summary.get('n_source_pair_temperature_states', 0)}`",
        f"- Source pair-temperature states with UNIFAC groups: `{summary.get('n_source_pair_temperature_states_with_groups', 0)}`",
        f"- Potential exact-row source-state coverage: `{summary.get('source_state_coverage_fraction', 0.0):.2%}`",
        "",
        "## Coverage By Split",
        "",
        "| Split | Target pairs | Covered pairs | Pair coverage | Target states | Covered states | State coverage | Source states | Source states with groups | Pairs with groups |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in coverage_by_split.to_dict(orient="records"):
        lines.append(
            "| {split} | {n_target_pairs} | {n_pairs_covered} | {pair_coverage_fraction:.4f} | {n_target_states} | {n_states_covered} | {state_coverage_fraction:.4f} | {n_source_pair_temperature_states} | {n_source_pair_temperature_states_with_groups} | {n_pairs_with_groups} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    splits = args.target_split or ["train", "val", "test"]
    composition_grid = _parse_grid(args.composition_grid, decimals=int(args.composition_decimals))
    sle_rows = _load_sle_rows(
        Path(args.processed_dir),
        splits,
        temperature_decimals=int(args.temperature_decimals),
    )
    targets = _build_target_states(sle_rows, temperature_mode=args.temperature_mode)

    gap_pairs = _load_gap_pairs(args.gap_csv)
    if not gap_pairs.empty:
        gap_pair_keys = set(gap_pairs["directed_pair_key"].astype(str))
        targets = targets.loc[targets["directed_pair_key"].astype(str).isin(gap_pair_keys)].copy()
        targets["pair_in_gap"] = True
    else:
        targets["pair_in_gap"] = False

    if args.max_pairs > 0 and not targets.empty:
        keep_pairs = (
            targets[
                [
                    "split",
                    "directed_pair_key",
                    "n_source_rows",
                    "n_temperatures",
                ]
            ]
            .drop_duplicates()
            .sort_values(["split", "n_source_rows", "n_temperatures"], ascending=[True, False, False])
            .head(int(args.max_pairs))
        )
        keep_keys = set(keep_pairs["directed_pair_key"].astype(str))
        targets = targets.loc[targets["directed_pair_key"].astype(str).isin(keep_keys)].copy()

    targets = targets.sort_values(
        ["split", "n_source_rows", "n_temperatures", "directed_pair_key"],
        ascending=[True, False, False, True],
    ).reset_index(drop=True)

    pair_status = _pair_group_status(
        targets,
        allow_approximate_fallback=bool(args.allow_approximate_fallback),
    )
    status_lookup = (
        pair_status.set_index("directed_pair_key")["pair_group_status"].to_dict()
        if not pair_status.empty
        else {}
    )

    rows: list[dict[str, Any]] = []
    eval_failures: list[dict[str, Any]] = []
    for record in tqdm(
        targets.itertuples(index=False),
        total=len(targets),
        desc="UNIFAC finite-activity states",
    ):
        pair_status_value = status_lookup.get(str(record.directed_pair_key), "unknown")
        if pair_status_value != "ready":
            continue
        for x_solute in composition_grid:
            lng = modified_unifac_lngamma_binary(
                str(record.solute_smiles),
                str(record.solvent_smiles),
                float(record.temperature),
                float(x_solute),
                temperature_decimals=int(args.temperature_decimals),
                composition_decimals=int(args.composition_decimals),
                allow_approximate_fallback=bool(args.allow_approximate_fallback),
            )
            if lng is None:
                eval_failures.append(
                    {
                        "split": record.split,
                        "directed_pair_key": record.directed_pair_key,
                        "solute_smiles": record.solute_smiles,
                        "solvent_smiles": record.solvent_smiles,
                        "temperature": record.temperature,
                        "solute_mole_fraction": x_solute,
                        "failure_reason": "evaluation_failed",
                    }
                )
                continue
            rows.append(
                {
                    "split": record.split,
                    "solute_smiles": record.solute_smiles,
                    "solvent_smiles": record.solvent_smiles,
                    "solute_name": record.solute_name,
                    "solvent_name": record.solvent_name,
                    "directed_pair_key": record.directed_pair_key,
                    "temperature": float(record.temperature),
                    "solute_mole_fraction": float(x_solute),
                    "composition_basis": "mole_fraction",
                    "ln_gamma_unifac": float(lng),
                    "gamma_unifac": float(math.exp(lng)),
                    "source_label": "unifac_finite_activity_modified",
                    "temperature_mode": record.temperature_mode,
                    "pair_in_gap": bool(record.pair_in_gap),
                }
            )

    pseudo = pd.DataFrame(rows)
    failures = pd.DataFrame(eval_failures)
    covered_pairs = (
        pseudo[
            [
                "split",
                "directed_pair_key",
            ]
        ]
        .drop_duplicates()
        .reset_index(drop=True)
        if not pseudo.empty
        else pd.DataFrame(columns=["split", "directed_pair_key"])
    )
    covered_states = (
        pseudo[
            [
                "split",
                "directed_pair_key",
                "temperature",
            ]
        ]
        .drop_duplicates()
        .reset_index(drop=True)
        if not pseudo.empty
        else pd.DataFrame(columns=["split", "directed_pair_key", "temperature"])
    )

    pair_status = pair_status.merge(
        covered_pairs.assign(has_generated_rows=True),
        on=["split", "directed_pair_key"],
        how="left",
    )
    pair_status["has_generated_rows"] = (
        pair_status["has_generated_rows"].fillna(False).astype(bool)
    )
    missing_pairs = pair_status.loc[pair_status["has_generated_rows"].eq(False)].copy()

    coverage_by_split = _coverage_by_split(targets, pseudo, pair_status)

    pseudo.to_csv(out_dir / "unifac_finite_activity_pseudo.csv", index=False)
    pair_status.to_csv(out_dir / "pair_status.csv", index=False)
    missing_pairs.to_csv(out_dir / "missing_pairs.csv", index=False)
    failures.to_csv(out_dir / "evaluation_failures.csv", index=False)
    coverage_by_split.to_csv(out_dir / "coverage_by_split.csv", index=False)

    n_target_pairs = int(targets["directed_pair_key"].nunique()) if not targets.empty else 0
    n_target_states = int(
        targets[["directed_pair_key", "temperature"]].drop_duplicates().shape[0]
    ) if not targets.empty else 0
    n_covered_pairs = int(covered_pairs["directed_pair_key"].nunique()) if not covered_pairs.empty else 0
    n_covered_states = int(len(covered_states))
    n_source_pair_temperature_states = int(pair_status["n_source_rows"].sum()) if not pair_status.empty else 0
    n_source_pair_temperature_states_with_groups = int(
        pair_status.loc[pair_status["pair_group_status"].eq("ready"), "n_source_rows"].sum()
    ) if not pair_status.empty else 0
    summary = {
        "processed_dir": args.processed_dir,
        "gap_csv": args.gap_csv or None,
        "target_splits": splits,
        "temperature_mode": args.temperature_mode,
        "allow_approximate_fallback": bool(args.allow_approximate_fallback),
        "composition_grid": composition_grid,
        "n_target_pairs": n_target_pairs,
        "n_target_states": n_target_states,
        "n_generated_rows": int(len(pseudo)),
        "n_covered_pairs": n_covered_pairs,
        "n_covered_states": n_covered_states,
        "n_source_pair_temperature_states": n_source_pair_temperature_states,
        "n_source_pair_temperature_states_with_groups": n_source_pair_temperature_states_with_groups,
        "pair_coverage_fraction": float(n_covered_pairs / max(n_target_pairs, 1)),
        "state_coverage_fraction": float(n_covered_states / max(n_target_states, 1)),
        "source_state_coverage_fraction": float(
            n_source_pair_temperature_states_with_groups
            / max(n_source_pair_temperature_states, 1)
        ),
        "pair_group_status_counts": (
            pair_status["pair_group_status"].value_counts(dropna=False).to_dict()
            if not pair_status.empty
            else {}
        ),
        "n_pairs_with_groups": int(
            pair_status.loc[pair_status["pair_group_status"].eq("ready"), "directed_pair_key"].nunique()
        )
        if not pair_status.empty
        else 0,
        "n_eval_failures": int(len(failures)),
        "coverage_by_split": coverage_by_split.to_dict(orient="records"),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_summary_md(summary, coverage_by_split=coverage_by_split, path=out_dir / "SUMMARY.md")
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
