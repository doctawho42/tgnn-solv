"""Audit charged and formulation-sensitive systems in the TGNN-Solv corpus.

The script is intentionally diagnostic: it does not change the training data
or model inputs. It asks whether difficult rows are concentrated in salts,
zwitterions, low-dielectric organic solvents, or extreme solubility tails.
"""

from __future__ import annotations

import argparse
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors


R_GAS = 8.314462618
DELPHINIDIN_CHLORIDE = (
    "Oc1cc(O)c2cc(O)c(-c3cc(O)c(O)c(O)c3)[o+]c2c1.[Cl-]"
)


# Small curated table for high-coverage solvents in the current corpus.
# Values are static room-temperature relative permittivities and are used only
# to classify regimes coarsely, not as exact experimental conditions.
DIELECTRIC_BY_NAME = {
    "water": 78.4,
    "methanol": 32.6,
    "ethanol": 24.6,
    "n-propanol": 20.1,
    "1-propanol": 20.1,
    "propan-1-ol": 20.1,
    "isopropanol": 19.9,
    "2-propanol": 19.9,
    "propan-2-ol": 19.9,
    "1-butanol": 17.8,
    "n-butanol": 17.8,
    "2-butanol": 15.9,
    "tert-butanol": 12.5,
    "acetone": 20.7,
    "acetonitrile": 35.9,
    "dimethyl sulfoxide": 46.7,
    "dmso": 46.7,
    "n,n-dimethylformamide": 36.7,
    "dimethylformamide": 36.7,
    "dmf": 36.7,
    "tetrahydrofuran": 7.6,
    "thf": 7.6,
    "1,4-dioxane": 2.2,
    "dioxane": 2.2,
    "ethyl acetate": 6.0,
    "methyl acetate": 6.7,
    "dichloromethane": 8.9,
    "methylene chloride": 8.9,
    "chloroform": 4.8,
    "benzene": 2.3,
    "toluene": 2.4,
    "hexane": 1.9,
    "n-hexane": 1.9,
    "heptane": 1.9,
    "n-heptane": 1.9,
    "cyclohexane": 2.0,
}


def _canon(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True)


def _build_dielectric_by_smiles() -> dict[str, float]:
    values = {
        "O": 78.4,
        "CO": 32.6,
        "CCO": 24.6,
        "CCCO": 20.1,
        "CC(C)O": 19.9,
        "CCCCO": 17.8,
        "CCC(C)O": 15.9,
        "CC(C)(C)O": 12.5,
        "CC(C)=O": 20.7,
        "CC#N": 35.9,
        "CS(C)=O": 46.7,
        "CN(C)C=O": 36.7,
        "C1CCOC1": 7.6,
        "C1COCCO1": 2.2,
        "CCOC(C)=O": 6.0,
        "COC(C)=O": 6.7,
        "ClCCl": 8.9,
        "ClC(Cl)Cl": 4.8,
        "c1ccccc1": 2.3,
        "Cc1ccccc1": 2.4,
        "CCCCCC": 1.9,
        "CCCCCCC": 1.9,
        "C1CCCCC1": 2.0,
    }
    out: dict[str, float] = {}
    for smiles, eps in values.items():
        canon = _canon(smiles)
        if canon is not None:
            out[canon] = eps
    return out


DIELECTRIC_BY_SMILES = _build_dielectric_by_smiles()


@lru_cache(maxsize=None)
def molecule_flags(smiles: str) -> dict[str, Any]:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return {
            "mol_ok": False,
            "total_formal_charge": np.nan,
            "has_positive_charge": False,
            "has_negative_charge": False,
            "has_any_charge": False,
            "n_fragments": np.nan,
            "is_explicit_salt": False,
            "is_charged_single_fragment": False,
            "is_zwitterion": False,
            "n_hbd": np.nan,
            "n_hba": np.nan,
            "heavy_atoms": np.nan,
        }

    charges = [atom.GetFormalCharge() for atom in mol.GetAtoms()]
    total_charge = int(sum(charges))
    has_pos = any(c > 0 for c in charges)
    has_neg = any(c < 0 for c in charges)
    frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=False)
    frag_props = []
    for frag in frags:
        frag_charges = [atom.GetFormalCharge() for atom in frag.GetAtoms()]
        frag_props.append(
            {
                "net": int(sum(frag_charges)),
                "has_pos": any(c > 0 for c in frag_charges),
                "has_neg": any(c < 0 for c in frag_charges),
            }
        )

    n_fragments = len(frags)
    is_explicit_salt = n_fragments > 1 and (has_pos or has_neg)
    is_zwitterion = (
        n_fragments == 1
        and total_charge == 0
        and has_pos
        and has_neg
    ) or any(fp["net"] == 0 and fp["has_pos"] and fp["has_neg"] for fp in frag_props)
    is_charged_single = n_fragments == 1 and total_charge != 0

    return {
        "mol_ok": True,
        "total_formal_charge": total_charge,
        "has_positive_charge": has_pos,
        "has_negative_charge": has_neg,
        "has_any_charge": has_pos or has_neg,
        "n_fragments": n_fragments,
        "is_explicit_salt": is_explicit_salt,
        "is_charged_single_fragment": is_charged_single,
        "is_zwitterion": is_zwitterion,
        "n_hbd": int(rdMolDescriptors.CalcNumHBD(mol)),
        "n_hba": int(rdMolDescriptors.CalcNumHBA(mol)),
        "heavy_atoms": int(mol.GetNumHeavyAtoms()),
    }


def lookup_dielectric(solvent_smiles: str, solvent_name: str | float | None) -> float:
    name = str(solvent_name).strip().lower() if solvent_name is not None else ""
    if name and name != "nan":
        normalized = name.replace("_", " ").replace("-", "-")
        if normalized in DIELECTRIC_BY_NAME:
            return DIELECTRIC_BY_NAME[normalized]

    canon = _canon(str(solvent_smiles))
    if canon is not None and canon in DIELECTRIC_BY_SMILES:
        return DIELECTRIC_BY_SMILES[canon]
    return math.nan


def eps_regime(eps_r: float) -> str:
    if not np.isfinite(eps_r):
        return "eps_unknown"
    if eps_r < 30.0:
        return "low_eps"
    if eps_r < 40.0:
        return "mid_eps"
    return "high_eps"


def system_class(row: pd.Series) -> str:
    if bool(row["is_zwitterion"]):
        return "zwitterion"
    if bool(row["is_explicit_salt"]):
        return f"explicit_salt_{row['eps_regime']}"
    if bool(row["is_charged_single_fragment"]):
        return f"charged_single_{row['eps_regime']}"
    if bool(row["has_any_charge"]):
        return f"charged_other_{row['eps_regime']}"
    return "neutral"


def load_processed(processed_dir: Path) -> pd.DataFrame:
    frames = []
    for split in ["train", "val", "test"]:
        path = processed_dir / f"{split}.csv"
        df = pd.read_csv(path, low_memory=False)
        df["split"] = split
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df = df[df["has_solubility"].astype(bool)].copy()
    df["row_uid"] = np.arange(len(df))
    return df


def add_audit_columns(df: pd.DataFrame) -> pd.DataFrame:
    unique_solutes = sorted(df["solute_smiles"].dropna().astype(str).unique())
    props = pd.DataFrame(
        [{"solute_smiles": s, **molecule_flags(s)} for s in unique_solutes]
    )
    out = df.merge(props, on="solute_smiles", how="left")
    out["eps_r"] = [
        lookup_dielectric(smi, name)
        for smi, name in zip(out["solvent_smiles"], out["solvent_name"])
    ]
    out["eps_regime"] = out["eps_r"].map(eps_regime)
    out["system_class"] = out.apply(system_class, axis=1)
    names = out["solute_name"].fillna("").astype(str).str.lower()
    out["is_anthocyanidin_like"] = names.str.contains(
        "delphinidin|cyanidin|malvidin|pelargonidin|peonidin|petunidin|anthocyan",
        regex=True,
    )
    out["extreme_low_solubility"] = pd.to_numeric(out["ln_x2"], errors="coerce") < -15.0
    out["very_extreme_low_solubility"] = pd.to_numeric(out["ln_x2"], errors="coerce") < -20.0
    out["ionic_low_eps_contact_pair_candidate"] = (
        out["has_any_charge"].astype(bool) & out["eps_r"].lt(30.0)
    )
    out["ionic_high_eps_dissociation_candidate"] = (
        out["has_any_charge"].astype(bool) & out["eps_r"].ge(40.0)
    )
    out["formulation_audit_candidate"] = (
        out["extreme_low_solubility"]
        & (out["has_any_charge"].astype(bool) | out["is_anthocyanidin_like"])
    )
    return out


def add_required_gamma(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    has = (
        out["has_T_m"].astype(bool)
        & out["has_dH_fus"].astype(bool)
        & pd.to_numeric(out["T_m"], errors="coerce").gt(0)
        & pd.to_numeric(out["dH_fus"], errors="coerce").gt(0)
    )
    T = pd.to_numeric(out["temperature"], errors="coerce")
    Tm = pd.to_numeric(out["T_m"], errors="coerce")
    dH = pd.to_numeric(out["dH_fus"], errors="coerce")
    y = pd.to_numeric(out["ln_x2"], errors="coerce")
    phi = (dH / R_GAS) * (1.0 / T - 1.0 / Tm)
    out["Phi_oracle"] = np.where(has, phi, np.nan)
    out["ln_gamma_req"] = np.where(has, -y - phi, np.nan)
    out["abs_ln_gamma_req"] = out["ln_gamma_req"].abs()
    out["has_required_gamma"] = np.isfinite(out["ln_gamma_req"])
    return out


def summarize_classes(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total = len(df)
    for (split, cls), g in df.groupby(["split", "system_class"], dropna=False):
        req = g[g["has_required_gamma"]]
        rows.append(
            {
                "split": split,
                "system_class": cls,
                "n_rows": int(len(g)),
                "fraction_of_all_rows": len(g) / total,
                "fraction_with_eps": float(np.isfinite(g["eps_r"]).mean()),
                "mean_ln_x2": float(pd.to_numeric(g["ln_x2"], errors="coerce").mean()),
                "median_ln_x2": float(pd.to_numeric(g["ln_x2"], errors="coerce").median()),
                "frac_ln_x2_lt_minus15": float(g["extreme_low_solubility"].mean()),
                "frac_ln_x2_lt_minus20": float(g["very_extreme_low_solubility"].mean()),
                "n_required_gamma": int(len(req)),
                "median_abs_ln_gamma_req": float(req["abs_ln_gamma_req"].median())
                if len(req)
                else math.nan,
                "frac_abs_ln_gamma_req_gt4": float((req["abs_ln_gamma_req"] > 4.0).mean())
                if len(req)
                else math.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["split", "n_rows"], ascending=[True, False])


def summarize_model_errors(audit_df: pd.DataFrame, prediction_dir: Path) -> pd.DataFrame:
    model_files = {
        "DirectGNN": prediction_dir / "DirectGNN" / "predictions_with_errors.csv",
        "TGNN-Solv MPNN": prediction_dir / "TGNN_MPNN" / "predictions_with_errors.csv",
        "RF hybrid": prediction_dir / "RF_hybrid" / "predictions_with_errors.csv",
    }
    key_cols = [
        "solute_smiles",
        "solvent_smiles",
        "temperature",
        "ln_x2",
        "system_class",
        "eps_r",
        "eps_regime",
        "has_any_charge",
        "is_explicit_salt",
        "is_zwitterion",
        "is_anthocyanidin_like",
        "formulation_audit_candidate",
        "ionic_low_eps_contact_pair_candidate",
        "ionic_high_eps_dissociation_candidate",
    ]
    test_flags = audit_df[audit_df["split"].eq("test")][key_cols].copy()
    rows = []
    for model, path in model_files.items():
        if not path.exists():
            continue
        pred = pd.read_csv(path, low_memory=False)
        merged = pred.merge(
            test_flags,
            on=["solute_smiles", "solvent_smiles", "temperature", "ln_x2"],
            how="left",
        )
        for cls, g in merged.groupby("system_class", dropna=False):
            rows.append(
                {
                    "model": model,
                    "slice": f"class:{cls}",
                    "n_rows": int(len(g)),
                    "mae": float(g["abs_error"].mean()),
                    "bias": float(g["signed_error"].mean()),
                }
            )
        binary_slices = [
            "has_any_charge",
            "is_explicit_salt",
            "is_zwitterion",
            "is_anthocyanidin_like",
            "formulation_audit_candidate",
            "ionic_low_eps_contact_pair_candidate",
            "ionic_high_eps_dissociation_candidate",
        ]
        for col in binary_slices:
            g = merged[merged[col].fillna(False).astype(bool)]
            if len(g):
                rows.append(
                    {
                        "model": model,
                        "slice": col,
                        "n_rows": int(len(g)),
                        "mae": float(g["abs_error"].mean()),
                        "bias": float(g["signed_error"].mean()),
                    }
                )
    return pd.DataFrame(rows).sort_values(["slice", "model"])


def delphinidin_model_errors(audit_df: pd.DataFrame, prediction_dir: Path) -> pd.DataFrame:
    model_files = {
        "DirectGNN": prediction_dir / "DirectGNN" / "predictions_with_errors.csv",
        "TGNN-Solv MPNN": prediction_dir / "TGNN_MPNN" / "predictions_with_errors.csv",
        "RF hybrid": prediction_dir / "RF_hybrid" / "predictions_with_errors.csv",
    }
    test = audit_df[
        audit_df["split"].eq("test")
        & audit_df["solute_smiles"].eq(DELPHINIDIN_CHLORIDE)
    ][
        [
            "solute_smiles",
            "solvent_smiles",
            "temperature",
            "ln_x2",
            "eps_r",
            "eps_regime",
            "formulation_audit_candidate",
            "has_T_m",
            "has_dH_fus",
        ]
    ].copy()
    if test.empty:
        return pd.DataFrame()

    rows = []
    for model, path in model_files.items():
        if not path.exists():
            continue
        pred = pd.read_csv(path, low_memory=False)
        merged = pred.merge(
            test,
            on=["solute_smiles", "solvent_smiles", "temperature", "ln_x2"],
            how="inner",
        )
        for solvent, g in merged.groupby("solvent_name", dropna=False):
            rows.append(
                {
                    "model": model,
                    "solvent_name": solvent,
                    "n_rows": int(len(g)),
                    "eps_r": float(g["eps_r"].iloc[0]),
                    "ln_x2_min": float(g["ln_x2_true"].min()),
                    "ln_x2_max": float(g["ln_x2_true"].max()),
                    "mae": float(g["abs_error"].mean()),
                    "bias": float(g["signed_error"].mean()),
                    "all_formulation_audit_candidate": bool(
                        g["formulation_audit_candidate"].all()
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(["solvent_name", "model"])


def delphinidin_slope_summary(df: pd.DataFrame) -> pd.DataFrame:
    d = df[
        df["split"].eq("test")
        & df["solute_smiles"].eq(DELPHINIDIN_CHLORIDE)
    ].copy()
    if d.empty:
        return pd.DataFrame()
    rows = []
    for solvent, g in d.groupby("solvent_name", dropna=False):
        g = g.sort_values("temperature")
        if len(g) < 2:
            continue
        x = 1.0 / pd.to_numeric(g["temperature"], errors="coerce").to_numpy()
        y = pd.to_numeric(g["ln_x2"], errors="coerce").to_numpy()
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 2:
            continue
        slope, intercept = np.polyfit(x[mask], y[mask], deg=1)
        pred = slope * x[mask] + intercept
        ss_res = float(np.sum((y[mask] - pred) ** 2))
        ss_tot = float(np.sum((y[mask] - y[mask].mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else math.nan
        rows.append(
            {
                "solvent_name": solvent,
                "solvent_smiles": g["solvent_smiles"].iloc[0],
                "eps_r": float(g["eps_r"].iloc[0]),
                "n_rows": int(mask.sum()),
                "T_min": float(g["temperature"].min()),
                "T_max": float(g["temperature"].max()),
                "ln_x2_min": float(y[mask].min()),
                "ln_x2_max": float(y[mask].max()),
                "slope_dlnx_dinvT_K": float(slope),
                "effective_deltaH_solution_kJ_mol": float(-R_GAS * slope / 1000.0),
                "r2_vant_hoff": float(r2),
                "monotone_increases_with_T": bool(np.all(np.diff(y[mask]) > 0)),
            }
        )
    return pd.DataFrame(rows).sort_values("eps_r", ascending=False)


def summarize_delphinidin(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["solute_smiles"].eq(DELPHINIDIN_CHLORIDE)].copy()
    if d.empty:
        return pd.DataFrame()
    group_cols = ["split", "solvent_smiles", "solvent_name", "eps_r", "eps_regime"]
    return (
        d.groupby(group_cols, dropna=False)
        .agg(
            n_rows=("ln_x2", "size"),
            T_min=("temperature", "min"),
            T_max=("temperature", "max"),
            ln_x2_min=("ln_x2", "min"),
            ln_x2_max=("ln_x2", "max"),
            has_T_m=("has_T_m", "max"),
            has_dH_fus=("has_dH_fus", "max"),
            has_required_gamma=("has_required_gamma", "max"),
            sources=("source", lambda s: "; ".join(sorted(set(map(str, s))))),
        )
        .reset_index()
        .sort_values(["split", "ln_x2_min"])
    )


def write_summary_json(df: pd.DataFrame, out_dir: Path) -> None:
    test = df[df["split"].eq("test")]
    req = df[df["has_required_gamma"]]
    summary = {
        "n_rows_supervised": int(len(df)),
        "n_test_rows": int(len(test)),
        "fraction_charged_all": float(df["has_any_charge"].mean()),
        "fraction_charged_test": float(test["has_any_charge"].mean()),
        "fraction_explicit_salt_test": float(test["is_explicit_salt"].mean()),
        "fraction_zwitterion_test": float(test["is_zwitterion"].mean()),
        "fraction_ionic_low_eps_test": float(
            test["ionic_low_eps_contact_pair_candidate"].mean()
        ),
        "fraction_ionic_high_eps_test": float(
            test["ionic_high_eps_dissociation_candidate"].mean()
        ),
        "fraction_formulation_audit_candidate_test": float(
            test["formulation_audit_candidate"].mean()
        ),
        "dielectric_coverage_all": float(np.isfinite(df["eps_r"]).mean()),
        "dielectric_coverage_test": float(np.isfinite(test["eps_r"]).mean()),
        "required_gamma_rows": int(len(req)),
        "median_abs_ln_gamma_req": float(req["abs_ln_gamma_req"].median())
        if len(req)
        else math.nan,
        "fraction_abs_ln_gamma_req_gt4": float((req["abs_ln_gamma_req"] > 4.0).mean())
        if len(req)
        else math.nan,
        "delphinidin_rows_test": int(
            test["solute_smiles"].eq(DELPHINIDIN_CHLORIDE).sum()
        ),
        "delphinidin_formulation_audit_rows_test": int(
            (
                test["solute_smiles"].eq(DELPHINIDIN_CHLORIDE)
                & test["formulation_audit_candidate"]
            ).sum()
        ),
        "formulation_audit_rows_test": int(
            test["formulation_audit_candidate"].sum()
        ),
        "note": (
            "Required ln_gamma is computed only when experimental T_m and dH_fus "
            "are both present. In the canonical scaffold test, dH_fus is absent, "
            "so test-set required-gamma analysis is not available from processed CSVs."
        ),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("notebooks/data/processed"),
    )
    parser.add_argument(
        "--prediction-dir",
        type=Path,
        default=Path("results/prediction_error_slices_latest"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("results/difficult_systems_audit"),
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    df = load_processed(args.processed_dir)
    df = add_audit_columns(df)
    df = add_required_gamma(df)

    keep_cols = [
        "split",
        "row_uid",
        "solute_smiles",
        "solvent_smiles",
        "temperature",
        "ln_x2",
        "source",
        "solute_name",
        "solvent_name",
        "T_m",
        "has_T_m",
        "dH_fus",
        "has_dH_fus",
        "eps_r",
        "eps_regime",
        "system_class",
        "total_formal_charge",
        "has_positive_charge",
        "has_negative_charge",
        "has_any_charge",
        "n_fragments",
        "is_explicit_salt",
        "is_charged_single_fragment",
        "is_zwitterion",
        "n_hbd",
        "n_hba",
        "heavy_atoms",
        "is_anthocyanidin_like",
        "ionic_low_eps_contact_pair_candidate",
        "ionic_high_eps_dissociation_candidate",
        "formulation_audit_candidate",
        "Phi_oracle",
        "ln_gamma_req",
        "abs_ln_gamma_req",
        "has_required_gamma",
    ]
    df[keep_cols].to_csv(args.out_dir / "row_audit.csv", index=False)
    summarize_classes(df).to_csv(args.out_dir / "class_summary.csv", index=False)
    summarize_model_errors(df, args.prediction_dir).to_csv(
        args.out_dir / "model_error_by_class.csv", index=False
    )
    summarize_delphinidin(df).to_csv(args.out_dir / "delphinidin_summary.csv", index=False)
    delphinidin_model_errors(df, args.prediction_dir).to_csv(
        args.out_dir / "delphinidin_model_errors.csv", index=False
    )
    delphinidin_slope_summary(df).to_csv(
        args.out_dir / "delphinidin_slope_summary.csv", index=False
    )
    anomalies = df[df["abs_ln_gamma_req"].gt(4.0)].sort_values(
        "abs_ln_gamma_req", ascending=False
    )
    anomalies[keep_cols].head(500).to_csv(
        args.out_dir / "required_gamma_anomalies_top500.csv", index=False
    )
    write_summary_json(df, args.out_dir)

    print(f"Wrote difficult-system audit to {args.out_dir}")


if __name__ == "__main__":
    main()
