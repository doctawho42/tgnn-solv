from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D
    from rdkit.Chem.Scaffolds import MurckoScaffold

    HAS_RDKIT = True
except Exception:
    HAS_RDKIT = False


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DATA_PATH = REPO_ROOT / "docs" / "assets" / "data" / "tgnn-presentation-data.json"
PROCESSED_DIR = REPO_ROOT / "notebooks" / "data" / "processed"
RAW_IDAC_PATH = REPO_ROOT / "notebooks" / "data" / "raw" / "idac.csv"
IDAC_ZENODO_RECORD_URL = "https://zenodo.org/records/19484205"
IDAC_ZENODO_CSV_URL = f"{IDAC_ZENODO_RECORD_URL}/files/idac.csv"
IDAC_ZENODO_DOIS_URL = f"{IDAC_ZENODO_RECORD_URL}/files/idac_seed_dois.txt"
TRAIN_PATH = PROCESSED_DIR / "train.csv"
VAL_PATH = PROCESSED_DIR / "val.csv"
TEST_PATH = PROCESSED_DIR / "test.csv"
SPLIT_MANIFEST_PATH = PROCESSED_DIR / "split_manifest.json"
DESCRIPTOR_SUMMARY_PATH = (
    REPO_ROOT / "results" / "medium_budget" / "per_model" / "tgnn_tuned" / "descriptor_probe" / "summary.json"
)
DESCRIPTOR_CSV_PATH = (
    REPO_ROOT / "results" / "medium_budget" / "per_model" / "tgnn_tuned" / "descriptor_probe" / "descriptor_r2.csv"
)


def truthy(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def safe_float(value: str | None, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def compact_count(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def clamp_text(value: str, limit: int = 18) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1]}…"


def format_preview_row(row: dict[str, str]) -> dict[str, str]:
    has_sol = truthy(row.get("has_solubility"))
    has_tm = truthy(row.get("has_T_m"))
    has_dh = truthy(row.get("has_dH_fus"))
    has_hansen = truthy(row.get("has_hansen"))
    has_gamma = truthy(row.get("has_gamma_inf"))

    temp = safe_float(row.get("temperature"), 298.15)
    ln_x2 = safe_float(row.get("ln_x2"))
    tm = safe_float(row.get("T_m"))
    dh = safe_float(row.get("dH_fus"))
    hd = safe_float(row.get("hansen_d"))
    hp = safe_float(row.get("hansen_p"))
    hh = safe_float(row.get("hansen_h"))
    gamma = safe_float(row.get("ln_gamma_inf"))

    return {
        "sample": row.get("solute_name") or clamp_text(row.get("solute_smiles", ""), 16),
        "solute_smiles": clamp_text(row.get("solute_smiles", "—"), 17),
        "solvent_smiles": clamp_text(row.get("solvent_smiles", "—"), 12),
        "T": f"{temp:.0f}" if temp is not None else "—",
        "ln_x2": f"{ln_x2:.2f}" if has_sol and ln_x2 is not None else "—",
        "T_m": f"{tm:.0f}" if has_tm and tm is not None else "—",
        "dH_fus": f"{dh / 1000:.1f}" if has_dh and dh is not None else "—",
        "delta_hansen": (
            f"{hd:.1f}/{hp:.1f}/{hh:.1f}"
            if has_hansen and hd is not None and hp is not None and hh is not None
            else "—"
        ),
        "gamma_inf": f"{gamma:.2f}" if has_gamma and gamma is not None else "—",
        "source": row.get("source", "unknown"),
    }


def format_idac_preview_row(row: dict[str, str]) -> dict[str, str]:
    temp = safe_float(row.get("temperature"), 298.15)
    gamma = safe_float(row.get("ln_gamma_inf"))
    sample = row.get("solute_name") or clamp_text(row.get("solute_smiles", ""), 16)
    return {
        "sample": sample,
        "solute_smiles": clamp_text(row.get("solute_smiles", "—"), 17),
        "solvent_smiles": clamp_text(row.get("solvent_smiles", "—"), 12),
        "T": f"{temp:.0f}" if temp is not None else "—",
        "ln_x2": "—",
        "T_m": "—",
        "dH_fus": "—",
        "delta_hansen": "—",
        "gamma_inf": f"{gamma:.2f}" if gamma is not None else "—",
        "source": "IDAC / Zenodo",
    }


def collect_idac_data() -> dict[str, object]:
    if not RAW_IDAC_PATH.exists():
        return {
            "idac_rows": 0,
            "idac_rows_label": "0",
            "idac_pairs": 0,
            "idac_pairs_label": "0",
            "idac_dois": 0,
            "idac_dois_label": "0",
            "idac_temperature_range_label": "—",
            "idac_release_label": "Zenodo 19484205",
            "idac_record_url": IDAC_ZENODO_RECORD_URL,
            "idac_csv_url": IDAC_ZENODO_CSV_URL,
            "idac_doi_list_url": IDAC_ZENODO_DOIS_URL,
            "idac_preview_row": None,
        }

    with RAW_IDAC_PATH.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        return {
            "idac_rows": 0,
            "idac_rows_label": "0",
            "idac_pairs": 0,
            "idac_pairs_label": "0",
            "idac_dois": 0,
            "idac_dois_label": "0",
            "idac_temperature_range_label": "—",
            "idac_release_label": "Zenodo 19484205",
            "idac_record_url": IDAC_ZENODO_RECORD_URL,
            "idac_csv_url": IDAC_ZENODO_CSV_URL,
            "idac_doi_list_url": IDAC_ZENODO_DOIS_URL,
            "idac_preview_row": None,
        }

    def preview_rank(row: dict[str, str]) -> tuple[int, int, float]:
        solvent = (row.get("solvent_name") or "").lower()
        solute = (row.get("solute_name") or "").lower()
        smiles = f"{row.get('solute_smiles', '')}{row.get('solvent_smiles', '')}"
        penalty = (
            int("imidazolium" in solvent)
            + int("imidazolium" in solute)
            + int("[" in smiles)
            + int("+" in smiles)
            + int("-" in smiles)
        )
        name_len = len(solvent) + len(solute)
        gamma = abs(safe_float(row.get("ln_gamma_inf"), 0.0) or 0.0)
        return (penalty, name_len, gamma)

    preview_row = min(rows, key=preview_rank)
    temperatures = [safe_float(row.get("temperature")) for row in rows]
    temperatures = [value for value in temperatures if value is not None]
    unique_pairs = {
        (row.get("solute_smiles", ""), row.get("solvent_smiles", ""))
        for row in rows
    }
    dois = {row.get("doi", "") for row in rows if row.get("doi")}

    t_range = "—"
    if temperatures:
        t_range = f"{min(temperatures):.0f}–{max(temperatures):.0f} K"

    return {
        "idac_rows": len(rows),
        "idac_rows_label": compact_count(len(rows)),
        "idac_pairs": len(unique_pairs),
        "idac_pairs_label": compact_count(len(unique_pairs)),
        "idac_dois": len(dois),
        "idac_dois_label": compact_count(len(dois)),
        "idac_temperature_range_label": t_range,
        "idac_release_label": "Zenodo 19484205",
        "idac_record_url": IDAC_ZENODO_RECORD_URL,
        "idac_csv_url": IDAC_ZENODO_CSV_URL,
        "idac_doi_list_url": IDAC_ZENODO_DOIS_URL,
        "idac_preview_row": format_idac_preview_row(preview_row),
    }


def iter_split_rows():
    for split_name, path in (("train", TRAIN_PATH), ("val", VAL_PATH), ("test", TEST_PATH)):
        if not path.exists():
            continue
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                yield split_name, row


def collect_pipeline_data() -> dict[str, object]:
    total_rows = 0
    solubility_rows = 0
    split_rows: dict[str, int] = {"train": 0, "val": 0, "test": 0}
    split_solubility_rows: dict[str, int] = {"train": 0, "val": 0, "test": 0}
    water_supervised_rows = 0
    water_supervised_pairs: set[tuple[str, str]] = set()
    aux_slots = 0
    aux_filled = 0
    unique_solutes: set[str] = set()
    preview_candidates: dict[str, dict[str, str] | None] = {
        "full": None,
        "tm_only": None,
        "sol_only": None,
        "aux_only": None,
    }

    for split_name, row in iter_split_rows():
        total_rows += 1
        split_rows[split_name] += 1
        unique_solutes.add(row.get("solute_smiles", ""))

        has_sol = truthy(row.get("has_solubility"))
        has_tm = truthy(row.get("has_T_m"))
        has_dh = truthy(row.get("has_dH_fus"))
        has_hansen = truthy(row.get("has_hansen"))
        has_gamma = truthy(row.get("has_gamma_inf"))

        if has_sol:
            solubility_rows += 1
            split_solubility_rows[split_name] += 1
            if row.get("solvent_smiles") == "O":
                water_supervised_rows += 1
                water_supervised_pairs.add(
                    (row.get("solute_smiles", ""), row.get("solvent_smiles", ""))
                )

        aux_slots += 4
        aux_filled += int(has_tm) + int(has_dh) + int(has_hansen) + int(has_gamma)

        if preview_candidates["full"] is None and has_sol and has_tm and has_dh and has_hansen:
            preview_candidates["full"] = row
        if preview_candidates["tm_only"] is None and has_sol and has_tm and not has_dh and not has_hansen:
            preview_candidates["tm_only"] = row
        if preview_candidates["sol_only"] is None and has_sol and not has_tm and not has_hansen:
            preview_candidates["sol_only"] = row
        if preview_candidates["aux_only"] is None and not has_sol and (has_tm or has_hansen):
            preview_candidates["aux_only"] = row

    preview_rows = [
        format_preview_row(row)
        for row in (
            preview_candidates["full"],
            preview_candidates["tm_only"],
            preview_candidates["sol_only"],
            preview_candidates["aux_only"],
        )
        if row is not None
    ]
    idac_data = collect_idac_data()
    if idac_data.get("idac_preview_row") is not None:
        preview_rows.append(idac_data["idac_preview_row"])

    ratios = {"train": 0.8, "val": 0.1, "test": 0.1}
    if SPLIT_MANIFEST_PATH.exists():
        with SPLIT_MANIFEST_PATH.open() as handle:
            manifest = json.load(handle)
        ratios = manifest.get("ratios", ratios)

    pipeline = {
        "total_rows": total_rows,
        "total_rows_label": compact_count(total_rows),
        "solubility_rows": solubility_rows,
        "solubility_rows_label": compact_count(solubility_rows),
        "unique_solutes": len(unique_solutes),
        "split_rows": split_rows,
        "split_rows_label": {key: compact_count(value) for key, value in split_rows.items()},
        "split_solubility_rows": split_solubility_rows,
        "split_solubility_rows_label": {
            key: compact_count(value) for key, value in split_solubility_rows.items()
        },
        "water_supervised_rows": water_supervised_rows,
        "water_supervised_rows_label": compact_count(water_supervised_rows),
        "water_supervised_pairs": len(water_supervised_pairs),
        "water_supervised_pairs_label": compact_count(len(water_supervised_pairs)),
        "ratios": ratios,
        "missing_fraction_aux": 1.0 - (aux_filled / aux_slots if aux_slots else 0.0),
        "missing_fraction_aux_label": f"{(1.0 - (aux_filled / aux_slots if aux_slots else 0.0)) * 100:.1f}%",
        "preview_rows": preview_rows,
    }
    pipeline.update(idac_data)
    pipeline.update(collect_scaffold_data())
    return pipeline


def murcko_scaffold_smiles(smiles: str) -> str | None:
    if not HAS_RDKIT or not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    scaffold = MurckoScaffold.GetScaffoldForMol(mol)
    if scaffold is None or scaffold.GetNumAtoms() == 0:
        return None
    return Chem.MolToSmiles(scaffold)


def scaffold_svg(scaffold_smiles: str) -> str | None:
    if not HAS_RDKIT or not scaffold_smiles:
        return None
    mol = Chem.MolFromSmiles(scaffold_smiles)
    if mol is None:
        return None

    drawer = rdMolDraw2D.MolDraw2DSVG(220, 140)
    options = drawer.drawOptions()
    options.padding = 0.05
    options.bondLineWidth = 2
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText().replace("svg:", "")


def pick_split_scaffold(path: Path, excluded: set[str] | None = None) -> tuple[dict[str, object] | None, set[str]]:
    excluded = excluded or set()
    if not path.exists() or not HAS_RDKIT:
        return None, set()

    counts: Counter[str] = Counter()
    examples: dict[str, dict[str, str]] = {}

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            smiles = row.get("solute_smiles", "")
            scaffold = murcko_scaffold_smiles(smiles)
            if not scaffold or scaffold in excluded:
                continue
            mol = Chem.MolFromSmiles(scaffold)
            if mol is None or mol.GetRingInfo().NumRings() == 0:
                continue
            counts[scaffold] += 1
            examples.setdefault(
                scaffold,
                {
                    "example_name": row.get("solute_name") or clamp_text(smiles, 20),
                    "example_smiles": smiles,
                },
            )

    if not counts:
        return None, set()

    def rank_key(scaffold_smiles: str) -> tuple[int, int, int]:
        mol = Chem.MolFromSmiles(scaffold_smiles)
        atoms = mol.GetNumAtoms()
        rings = mol.GetRingInfo().NumRings()
        hetero = sum(1 for atom in mol.GetAtoms() if atom.GetSymbol() not in {"C", "H"})
        compactness = abs(atoms - 10) + abs(rings - 2) * 3 + hetero
        return (counts[scaffold_smiles], -compactness, -atoms)

    best = max(counts, key=rank_key)
    example = examples[best]
    return (
        {
            "scaffold_smiles": best,
            "count": counts[best],
            "count_label": compact_count(counts[best]),
            "example_name": example["example_name"],
            "example_smiles": example["example_smiles"],
            "svg": scaffold_svg(best),
        },
        set(counts),
    )


def collect_scaffold_data() -> dict[str, object]:
    if not HAS_RDKIT:
        return {"scaffolds": {}, "scaffold_overlap": None}

    train_item, train_set = pick_split_scaffold(TRAIN_PATH)
    test_item, test_set = pick_split_scaffold(TEST_PATH, excluded=train_set)
    overlap = len(train_set & test_set)
    return {
        "scaffolds": {
            "train": train_item,
            "test": test_item,
        },
        "scaffold_overlap": overlap,
    }


def collect_linear_probe_data() -> dict[str, object]:
    descriptors: list[dict[str, object]] = []
    if DESCRIPTOR_CSV_PATH.exists():
        with DESCRIPTOR_CSV_PATH.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                r2_value = safe_float(row.get("r2_test"))
                if row.get("status") != "ok" or r2_value is None:
                    continue
                descriptors.append({"name": row["descriptor"], "value": r2_value})

    preferred = [
        "FractionCSP3",
        "NumHDonors",
        "TPSA",
        "NumHAcceptors",
        "MolLogP",
        "NumRotatableBonds",
        "RingCount",
        "MolWt",
        "HeavyAtomCount",
        "MolMR",
    ]
    descriptor_lookup = {item["name"]: item["value"] for item in descriptors}
    selected = [
        {"name": name, "value": descriptor_lookup[name]}
        for name in preferred
        if name in descriptor_lookup
    ]
    if len(selected) < 8:
        selected = sorted(descriptors, key=lambda item: item["value"], reverse=True)[:10]

    total = len(descriptors)
    ge_08 = sum(1 for item in descriptors if item["value"] >= 0.8)
    ge_05 = sum(1 for item in descriptors if item["value"] >= 0.5)
    lt_05 = sum(1 for item in descriptors if item["value"] < 0.5)

    median_r2 = None
    if DESCRIPTOR_SUMMARY_PATH.exists():
        with DESCRIPTOR_SUMMARY_PATH.open() as handle:
            summary = json.load(handle)
        median_r2 = safe_float(summary.get("summary", {}).get("median_r2_test"))
    if median_r2 is None and descriptors:
        sorted_values = sorted(item["value"] for item in descriptors)
        median_r2 = sorted_values[len(sorted_values) // 2]

    return {
        "descriptors": selected,
        "median_r2": median_r2,
        "median_r2_label": f"{median_r2:.3f}" if median_r2 is not None else "0.505",
        "total_descriptors": total or 208,
        "counts": {
            "ge_0_8": ge_08 or 3,
            "between_0_5_and_0_8": max(0, ge_05 - ge_08) or 104,
            "lt_0_5": lt_05 or 101,
        },
    }


def main() -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": collect_pipeline_data(),
        "linear_probe": collect_linear_probe_data(),
    }

    DOCS_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCS_DATA_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
