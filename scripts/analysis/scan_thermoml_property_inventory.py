#!/usr/bin/env python3
"""Inventory property/variable labels in a local ThermoML JSON cache."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan local NIST ThermoML JSON records and count property, method, "
            "phase, variable, and constraint labels. This is a lightweight "
            "pre-flight for deciding whether GE/VLE/heat-capacity auxiliary "
            "tasks are worth implementing."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--json-dir",
        default="notebooks/data/raw/thermoml_json",
        help="Directory containing cached ThermoML JSON files.",
    )
    parser.add_argument(
        "--out-dir",
        default="results/thermoml_property_inventory",
        help="Output directory.",
    )
    return parser.parse_args()


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _labels(node: Any, key: str) -> list[str]:
    out: list[str] = []
    if isinstance(node, dict):
        for k, value in node.items():
            if k == key and isinstance(value, (str, int, float)):
                out.append(str(value))
            out.extend(_labels(value, key))
    elif isinstance(node, list):
        for value in node:
            out.extend(_labels(value, key))
    return out


def _counter_frame(counter: Counter[str], examples: dict[str, str]) -> pd.DataFrame:
    rows = [
        {"label": label, "count": int(count), "example_doi": examples.get(label)}
        for label, count in counter.most_common()
    ]
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    json_dir = Path(args.json_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    property_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    phase_counts: Counter[str] = Counter()
    variable_counts: Counter[str] = Counter()
    constraint_counts: Counter[str] = Counter()
    examples: dict[str, str] = {}
    failed = 0
    files = sorted(json_dir.glob("*.json"))

    for path in files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            failed += 1
            continue
        citation = record.get("Citation") if isinstance(record, dict) else {}
        doi = citation.get("sDOI") if isinstance(citation, dict) else str(path)

        for dataset in _as_list(record.get("PureOrMixtureData")):
            for prop in _as_list(dataset.get("Property")):
                prop_names = _labels(prop, "ePropName") or ["<none>"]
                methods = _labels(prop, "eMethodName") or ["<none>"]
                phases = _labels(prop, "ePropPhase") or ["<none>"]
                for label in prop_names:
                    property_counts[label] += 1
                    examples.setdefault(label, doi)
                for label in methods:
                    method_counts[label] += 1
                    examples.setdefault(label, doi)
                for label in phases:
                    phase_counts[label] += 1
                    examples.setdefault(label, doi)

            for variable in _as_list(dataset.get("Variable")):
                labels = (
                    _labels(variable, "eVariableType")
                    + _labels(variable, "eTemperature")
                    + _labels(variable, "eComponentComposition")
                    + _labels(variable, "ePressure")
                ) or ["<none>"]
                for label in labels:
                    variable_counts[label] += 1
                    examples.setdefault(label, doi)

            for constraint in _as_list(dataset.get("Constraint")):
                labels = (
                    _labels(constraint, "eConstraintType")
                    + _labels(constraint, "eTemperature")
                    + _labels(constraint, "eComponentComposition")
                    + _labels(constraint, "ePressure")
                ) or ["<none>"]
                for label in labels:
                    constraint_counts[label] += 1
                    examples.setdefault(label, doi)

    _counter_frame(property_counts, examples).to_csv(out_dir / "property_counts.csv", index=False)
    _counter_frame(method_counts, examples).to_csv(out_dir / "method_counts.csv", index=False)
    _counter_frame(phase_counts, examples).to_csv(out_dir / "phase_counts.csv", index=False)
    _counter_frame(variable_counts, examples).to_csv(out_dir / "variable_counts.csv", index=False)
    _counter_frame(constraint_counts, examples).to_csv(out_dir / "constraint_counts.csv", index=False)

    ge_like = {
        label: count
        for label, count in property_counts.items()
        if "excess" in label.lower() or "mixing" in label.lower()
    }
    vle_like = {
        label: count
        for label, count in property_counts.items()
        if "vapor" in label.lower()
        or "boiling" in label.lower()
        or "partial pressure" in label.lower()
        or "azeotropic" in label.lower()
    }
    crystal_like = {
        label: count
        for label, count in property_counts.items()
        if "fusion" in label.lower()
        or "melting" in label.lower()
        or "heat capacity" in label.lower()
        or "solid-liquid equilibrium" in label.lower()
    }
    summary = {
        "json_dir": str(json_dir),
        "n_json_files": int(len(files)),
        "n_failed_json_files": int(failed),
        "n_property_labels": int(len(property_counts)),
        "top_properties": dict(property_counts.most_common(25)),
        "ge_like_properties": dict(sorted(ge_like.items(), key=lambda kv: kv[1], reverse=True)),
        "vle_like_properties": dict(sorted(vle_like.items(), key=lambda kv: kv[1], reverse=True)),
        "crystal_like_properties": dict(sorted(crystal_like.items(), key=lambda kv: kv[1], reverse=True)),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
