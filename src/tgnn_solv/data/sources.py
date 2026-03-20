"""
Data source loaders.

Each function downloads (if needed) and parses one data source,
returning a clean pandas DataFrame with canonical SMILES.

Sources:
  BigSolDBv2.1  — primary solubility (~121k records)
  Bradley ONS   — melting points (~28k)
  Curated       — T_m, ΔH_fus, Hansen, IDAC from NIST/literature
  CombiSolv-QM  — solvation free energies (~10k)
"""

from typing import Optional

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors

from .utils import (
    canonicalize,
    download_file,
    verify_csv,
    RAW_DIR,
)


# ================================================================== #
#  BigSolDBv2.1                                                       #
# ================================================================== #

BIGSOLDB_URL = "https://zenodo.org/records/18552681/files/BigSolDBv2.1.csv"
BIGSOLDB_PATH = RAW_DIR / "BigSolDBv2.1.csv"


def load_bigsoldb() -> pd.DataFrame:
    """
    Load BigSolDBv2.1 solubility database.

    Returns DataFrame with columns:
      solute_smiles, solvent_smiles, temperature, ln_x2, source
    """
    print("\n" + "=" * 60)
    print("Loading BigSolDBv2.1")
    print("=" * 60)

    got = download_file(BIGSOLDB_URL, BIGSOLDB_PATH, "BigSolDBv2.1")
    if not got or not verify_csv(BIGSOLDB_PATH):
        print("  BigSolDB not available — using synthetic fallback")
        return _synthetic_bigsoldb()

    df = pd.read_csv(BIGSOLDB_PATH, low_memory=False)
    n_raw = len(df)
    print(f"  Raw records: {n_raw:,}")
    print(f"  Columns: {list(df.columns)}")

    result = _process_bigsoldb_raw(df)
    return result


def _process_bigsoldb_raw(df: pd.DataFrame) -> pd.DataFrame:
    """Parse and clean raw BigSolDB CSV."""

    # --- Map columns (case-insensitive) ---
    col_map = {
        "smiles_solute": "solute_smiles",
        "smiles_solvent": "solvent_smiles",
        "temperature_k": "temperature",
        "solubility(mole_fraction)": "x2",
        "solvent": "solvent_name",
        "compound_name": "solute_name",
        "logs(mol/l)": "logS",
        "fda_approved": "fda_approved",
    }

    # Build lowercase → original column name mapping
    lower_map = {c.lower().replace(" ", ""): c for c in df.columns}

    result = pd.DataFrame()
    for key_lower, dst in col_map.items():
        src = lower_map.get(key_lower.replace(" ", ""))
        if src:
            result[dst] = df[src]

    # --- Canonicalize SMILES ---
    print("  Canonicalizing SMILES...")
    result["solute_smiles"] = result["solute_smiles"].apply(canonicalize)
    result["solvent_smiles"] = result["solvent_smiles"].apply(canonicalize)

    n_before = len(result)
    result = result.dropna(subset=["solute_smiles", "solvent_smiles"])
    print(f"  Invalid SMILES dropped: {n_before - len(result):,}")

    # --- Mole fraction → ln(x₂) ---
    if "x2" in result.columns:
        result["x2"] = pd.to_numeric(result["x2"], errors="coerce")
        valid_x2 = (result["x2"] > 0) & (result["x2"] <= 1.0)
        result.loc[~valid_x2, "x2"] = np.nan
        result["ln_x2"] = np.log(result["x2"])
    else:
        result["ln_x2"] = np.nan

    # Fallback: logS → x₂ where mole fraction is missing
    missing = result["ln_x2"].isna()
    if missing.any() and "logS" in result.columns:
        print(f"  Recovering ln(x₂) from logS for {missing.sum():,} records")
        logS = pd.to_numeric(result.loc[missing, "logS"], errors="coerce")
        S_mol_L = 10.0 ** logS

        water_smi = canonicalize("O")
        is_water = result.loc[missing, "solvent_smiles"] == water_smi

        C_solvent = pd.Series(np.nan, index=result.loc[missing].index)
        C_solvent[is_water] = 55.35

        for idx in C_solvent[C_solvent.isna()].index:
            slv = result.loc[idx, "solvent_smiles"]
            mol = Chem.MolFromSmiles(slv) if slv else None
            if mol:
                C_solvent[idx] = 850.0 / Descriptors.MolWt(mol)

        x2_calc = S_mol_L / (S_mol_L + C_solvent)
        ok = x2_calc.notna() & (x2_calc > 0) & (x2_calc <= 1)
        result.loc[ok[ok].index, "ln_x2"] = np.log(x2_calc[ok])

    result = result.dropna(subset=["ln_x2"])

    # --- Temperature ---
    if "temperature" in result.columns:
        result["temperature"] = pd.to_numeric(
            result["temperature"], errors="coerce"
        )
        result = result[
            (result["temperature"] >= 200) & (result["temperature"] <= 500)
        ]
    result["temperature"] = result["temperature"].fillna(298.15)

    # --- QC ---
    result = result[(result["ln_x2"] > -30) & (result["ln_x2"] <= 0)]

    # --- Dedup ---
    result = result.drop_duplicates(
        subset=["solute_smiles", "solvent_smiles", "temperature"],
        keep="first",
    )

    result["source"] = "BigSolDBv2.1"
    keep = ["solute_smiles", "solvent_smiles", "temperature", "ln_x2", "source"]
    for c in ["solute_name", "solvent_name", "fda_approved"]:
        if c in result.columns:
            keep.append(c)
    result = result[keep].reset_index(drop=True)

    _print_solubility_stats(result)
    return result


def _print_solubility_stats(df: pd.DataFrame):
    """Print summary statistics for a solubility DataFrame."""
    n = len(df)
    n_sol = df["solute_smiles"].nunique()
    n_slv = df["solvent_smiles"].nunique()
    print(f"\n  === Summary ===")
    print(f"  Records:    {n:,}")
    print(f"  Solutes:    {n_sol:,}")
    print(f"  Solvents:   {n_slv:,}")
    print(f"  T range:    {df['temperature'].min():.0f}–"
          f"{df['temperature'].max():.0f} K")
    print(f"  ln(x₂):    [{df['ln_x2'].min():.2f}, "
          f"{df['ln_x2'].max():.2f}]")


def _synthetic_bigsoldb() -> pd.DataFrame:
    """Minimal synthetic data for demo/testing (30 records)."""
    print("  Using synthetic BigSolDB (30 records)")
    data = [
        ("CC(=O)Nc1ccc(O)cc1", "CCO", 298.15, 0.043),
        ("CC(=O)Nc1ccc(O)cc1", "O", 298.15, 0.0017),
        ("CC(=O)Nc1ccc(O)cc1", "CCCCCC", 298.15, 1e-5),
        ("CC(=O)Nc1ccc(O)cc1", "CC(=O)C", 298.15, 0.025),
        ("CC(=O)Nc1ccc(O)cc1", "CCO", 313.15, 0.065),
        ("c1ccc2ccccc2c1", "c1ccccc1", 298.15, 0.295),
        ("c1ccc2ccccc2c1", "CCO", 298.15, 0.082),
        ("c1ccc2ccccc2c1", "CCCCCC", 298.15, 0.11),
        ("c1ccc2ccccc2c1", "O", 298.15, 2.5e-5),
        ("OC(=O)c1ccccc1", "CCO", 298.15, 0.18),
        ("OC(=O)c1ccccc1", "O", 298.15, 0.0043),
        ("OC(=O)c1ccccc1", "CC(=O)C", 298.15, 0.22),
        ("OC(=O)c1ccccc1", "CCCCCC", 298.15, 0.003),
        ("c1ccccc1", "O", 298.15, 0.00041),
        ("CCCCCC", "O", 298.15, 2.3e-5),
        ("Oc1ccccc1", "O", 298.15, 0.015),
        ("Oc1ccccc1", "CCO", 298.15, 0.35),
        ("CC(=O)Oc1ccccc1C(=O)O", "O", 298.15, 6e-4),
        ("CC(=O)Oc1ccccc1C(=O)O", "CCO", 298.15, 0.042),
        ("Nc1ccccc1", "O", 298.15, 0.0068),
        ("ClC(Cl)Cl", "O", 298.15, 0.0012),
        ("CCCCCCCC", "O", 298.15, 5.7e-7),
        ("O=Cc1ccccc1", "O", 298.15, 0.005),
        ("O=Cc1ccccc1", "CCO", 298.15, 0.45),
        ("CCOC(=O)c1ccccc1", "O", 298.15, 1.3e-4),
        ("CCOC(=O)c1ccccc1", "CCO", 298.15, 0.30),
        ("c1ccc(-c2ccccc2)cc1", "c1ccccc1", 298.15, 0.15),
        ("c1ccc(-c2ccccc2)cc1", "CCCCCC", 298.15, 0.08),
        ("OC(=O)c1ccccc1", "Cc1ccccc1", 298.15, 0.12),
        ("Oc1ccccc1", "CC(=O)C", 298.15, 0.28),
    ]

    df = pd.DataFrame(
        data, columns=["solute_smiles", "solvent_smiles", "temperature", "x2"]
    )
    df["solute_smiles"] = df["solute_smiles"].apply(canonicalize)
    df["solvent_smiles"] = df["solvent_smiles"].apply(canonicalize)
    df["ln_x2"] = np.log(df["x2"].clip(lower=1e-20))
    df["source"] = "synthetic"
    df = df.drop(columns=["x2"])
    return df.dropna(subset=["solute_smiles", "solvent_smiles"]).reset_index(
        drop=True
    )


# ================================================================== #
#  Melting Points                                                     #
# ================================================================== #

BRADLEY_MP_URL = (
    "https://zenodo.org/records/19012778/files/Bradley_Melting_Point_Dataset.csv"
)


def load_melting_points() -> pd.DataFrame:
    """
    Load melting points: Bradley ONS (°C) + curated NIST (K).

    Curated values override Bradley when both exist for the same
    compound (NIST is more reliable).

    Returns DataFrame: solute_smiles, T_m (K).
    """
    print("\n" + "=" * 60)
    print("Loading Melting Points")
    print("=" * 60)

    bradley_mp = {}
    curated_mp = {}

    # --- Bradley (always in °C) ---
    mp_path = RAW_DIR / "bradley_mp.csv"
    download_file(BRADLEY_MP_URL, mp_path, "Bradley Melting Points")

    if mp_path.exists() and verify_csv(mp_path):
        try:
            df = pd.read_csv(mp_path)
            smi_col = next(
                (c for c in df.columns if "smiles" in c.lower()),
                df.columns[0],
            )
            mp_col = next(
                (c for c in df.columns
                 if any(x in c.lower() for x in ["mpc", "mp", "melting", 'tm'])),
                None,
            )
            if mp_col is None:
                num_cols = df.select_dtypes(include=[np.number]).columns
                mp_col = num_cols[0] if len(num_cols) > 0 else df.columns[-1]

            for _, row in df.iterrows():
                smi = canonicalize(str(row[smi_col]))
                if smi is None:
                    continue
                try:
                    val_c = float(row[mp_col])
                except (ValueError, TypeError):
                    continue
                # Bradley is ALWAYS in °C
                val_k = val_c + 273.15
                if 80 < val_k < 800:
                    bradley_mp[smi] = val_k

            print(f"  Bradley valid: {len(bradley_mp):,}")
        except Exception as e:
            print(f"  Bradley error: {e}")

    # --- Curated NIST (in K, higher priority) ---
    curated_raw = {
        "CC(=O)Nc1ccc(O)cc1": 442.0,
        "c1ccc2ccccc2c1": 353.4,
        "OC(=O)c1ccccc1": 395.5,
        "c1ccccc1": 278.6,
        "Oc1ccccc1": 314.1,
        "CC(=O)Oc1ccccc1C(=O)O": 408.2,
        "O": 273.15,
        "CCO": 159.0,
        "CO": 175.5,
        "CC(=O)C": 178.2,
        "CCCCCC": 177.8,
        "CCCCCCC": 182.6,
        "CCCCCCCC": 216.4,
        "C1CCCCC1": 279.7,
        "c1ccncc1": 231.5,
        "Cc1ccccc1": 178.2,
        "CC#N": 227.2,
        "ClC(Cl)Cl": 209.6,
        "ClCCl": 176.0,
        "CS(=O)C": 291.7,
        "Nc1ccccc1": 267.1,
        "CC(=O)O": 289.8,
        "O=Cc1ccccc1": 247.2,
        "c1ccc(-c2ccccc2)cc1": 342.4,
        "c1ccc2cc3ccccc3cc2c1": 489.7,
        "c1ccc2c(c1)ccc1ccccc12": 372.4,
        "O=C(O)/C=C/c1ccccc1": 406.2,
        "OC(=O)c1cc(O)c(O)c(O)c1": 523.2,
        "O=C(O)C(O)(CC(=O)O)CC(=O)O": 426.2,
        "Clc1ccccc1": 228.0,
        "CC(=O)c1ccccc1": 293.2,
        "CCOC(=O)c1ccccc1": 238.5,
    }
    for smi, tm in curated_raw.items():
        can = canonicalize(smi)
        if can:
            curated_mp[can] = tm

    # Merge: curated overrides Bradley
    all_mp = {**bradley_mp, **curated_mp}
    n_override = len(set(bradley_mp) & set(curated_mp))
    print(f"  Curated: {len(curated_mp)}, overrides: {n_override}")
    print(f"  Total: {len(all_mp):,}")

    rows = [{"solute_smiles": s, "T_m": t} for s, t in all_mp.items()]
    result = pd.DataFrame(rows)
    print(f"  T_m range: [{result['T_m'].min():.0f}, "
          f"{result['T_m'].max():.0f}] K")
    return result


# ================================================================== #
#  Fusion Enthalpies                                                  #
# ================================================================== #

def load_fusion_enthalpies() -> pd.DataFrame:
    """Curated ΔH_fus from NIST WebBook (J/mol)."""
    print("\n" + "=" * 60)
    print("Loading ΔH_fus data")
    print("=" * 60)

    data = {
        "CC(=O)Nc1ccc(O)cc1": 26400, "c1ccc2ccccc2c1": 19060,
        "OC(=O)c1ccccc1": 18020, "c1ccccc1": 9866,
        "Oc1ccccc1": 11290, "CC(=O)Oc1ccccc1C(=O)O": 29800,
        "O": 6010, "CCO": 4810, "CO": 3180, "CC(=O)C": 5770,
        "CCCCCC": 13080, "CCCCCCC": 14160, "CCCCCCCC": 20730,
        "C1CCCCC1": 2630, "c1ccncc1": 8280, "Cc1ccccc1": 6640,
        "CC#N": 8167, "O=Cc1ccccc1": 11300, "Nc1ccccc1": 10590,
        "CC(=O)O": 11540, "Clc1ccccc1": 9560,
        "c1ccc(-c2ccccc2)cc1": 18580, "c1ccc2cc3ccccc3cc2c1": 19200,
        "c1ccc2c(c1)ccc1ccccc12": 19300,
        "O=C(O)/C=C/c1ccccc1": 22400,
        "O=C(O)C(O)(CC(=O)O)CC(=O)O": 28700,
        "CCCO": 5200, "CC(O)C": 5370, "CCCCO": 9280,
        "OCCO": 9960, "ClC(Cl)Cl": 9500,
    }

    rows = []
    for smi, dh in data.items():
        can = canonicalize(smi)
        if can:
            rows.append({"solute_smiles": can, "dH_fus": float(dh)})

    df = pd.DataFrame(rows).drop_duplicates(subset=["solute_smiles"])
    print(f"  Records: {len(df)}")
    return df


# ================================================================== #
#  Hansen Solubility Parameters                                       #
# ================================================================== #

def load_hansen() -> pd.DataFrame:
    """Hansen parameters (δd, δp, δh) in MPa^0.5."""
    print("\n" + "=" * 60)
    print("Loading Hansen parameters")
    print("=" * 60)

    data = [
        ("O", 15.5, 16.0, 42.3),
        ("CO", 15.1, 12.3, 22.3),
        ("CCO", 15.8, 8.8, 19.4),
        ("CCCO", 16.0, 6.8, 17.4),
        ("CC(O)C", 15.8, 6.1, 16.4),
        ("CCCCO", 16.0, 5.7, 15.8),
        ("CCCCCO", 15.9, 4.5, 13.9),
        ("CCCCCCCCO", 16.0, 3.3, 11.9),
        ("OCCO", 17.0, 11.0, 26.0),
        ("OCC(O)CO", 17.4, 12.1, 29.3),
        ("CC(=O)C", 15.5, 10.4, 7.0),
        ("CCC(=O)C", 16.0, 9.0, 5.1),
        ("CC#N", 15.3, 18.0, 6.1),
        ("CS(=O)C", 18.4, 16.4, 10.2),
        ("CN(C)C=O", 17.4, 13.7, 11.3),
        ("C1CCOC1", 16.8, 5.7, 8.0),
        ("CCOCC", 14.5, 2.9, 5.1),
        ("ClCCl", 17.0, 7.3, 7.1),
        ("ClC(Cl)Cl", 17.8, 3.1, 5.7),
        ("ClC(Cl)(Cl)Cl", 17.8, 0.0, 0.6),
        ("c1ccccc1", 18.4, 0.0, 2.0),
        ("Cc1ccccc1", 18.0, 1.4, 2.0),
        ("CCCCCC", 14.9, 0.0, 0.0),
        ("CCCCCCC", 15.3, 0.0, 0.0),
        ("C1CCCCC1", 16.8, 0.0, 0.2),
        ("CCOC(=O)C", 15.8, 5.3, 7.2),
        ("CC(=O)O", 14.5, 8.0, 13.5),
        ("c1ccncc1", 19.0, 8.8, 5.9),
        ("CN1CCCC1=O", 18.0, 12.3, 7.2),
        ("C1COCCO1", 19.0, 1.8, 7.4),
        ("O=[N+]([O-])c1ccccc1", 20.0, 8.6, 4.1),
        ("CC(=O)Nc1ccc(O)cc1", 18.5, 10.2, 14.1),
        ("c1ccc2ccccc2c1", 19.2, 2.0, 5.9),
        ("OC(=O)c1ccccc1", 18.2, 7.0, 9.8),
        ("CC(=O)Oc1ccccc1C(=O)O", 17.6, 6.4, 10.6),
        ("Oc1ccccc1", 18.0, 5.9, 14.9),
        ("Nc1ccccc1", 19.4, 5.1, 10.2),
        ("c1ccc(-c2ccccc2)cc1", 19.7, 1.0, 2.0),
        ("c1ccc2cc3ccccc3cc2c1", 20.3, 0.7, 2.4),
        ("Clc1ccccc1", 19.0, 4.3, 2.0),
        ("CC(=O)c1ccccc1", 19.6, 8.6, 3.7),
        ("CCCCCCCC", 15.5, 0.0, 0.0),
        ("CC(C)CC(C)C", 14.5, 0.0, 0.0),
    ]

    rows = []
    for smi, dd, dp, dh in data:
        can = canonicalize(smi)
        if can:
            rows.append({
                "solute_smiles": can,
                "hansen_d": dd, "hansen_p": dp, "hansen_h": dh,
            })

    df = pd.DataFrame(rows).drop_duplicates(subset=["solute_smiles"])
    print(f"  Records: {len(df)}")
    return df


# ================================================================== #
#  IDAC (γ∞)                                                          #
# ================================================================== #

def load_idac() -> pd.DataFrame:
    """Infinite dilution activity coefficients ln(γ∞)."""
    print("\n" + "=" * 60)
    print("Loading IDAC data")
    print("=" * 60)

    data = [
        ("CCCCCC", "O", 7.60, 298.15),
        ("c1ccccc1", "O", 7.78, 298.15),
        ("Cc1ccccc1", "O", 8.15, 298.15),
        ("C1CCCCC1", "O", 7.80, 298.15),
        ("CCCCCCC", "O", 8.60, 298.15),
        ("CCCCCCCC", "O", 9.65, 298.15),
        ("c1ccc2ccccc2c1", "O", 8.60, 298.15),
        ("CCO", "O", 1.39, 298.15),
        ("CO", "O", 0.69, 298.15),
        ("CC(=O)C", "O", 1.95, 298.15),
        ("CC#N", "O", 0.92, 298.15),
        ("CCCCO", "O", 3.33, 298.15),
        ("Oc1ccccc1", "O", 3.90, 298.15),
        ("O", "CCO", 0.47, 298.15),
        ("O", "CCCCCC", 5.70, 298.15),
        ("O", "c1ccccc1", 5.30, 298.15),
        ("O", "CC(=O)C", 0.30, 298.15),
        ("O", "ClC(Cl)Cl", 5.50, 298.15),
        ("CCCCCC", "CCO", 3.80, 298.15),
        ("c1ccccc1", "CCO", 2.50, 298.15),
        ("CCO", "CCCCCC", 4.80, 298.15),
        ("CC(=O)C", "CCCCCC", 3.20, 298.15),
        ("CCCCCC", "c1ccccc1", 1.05, 298.15),
        ("c1ccc2ccccc2c1", "c1ccccc1", 0.15, 298.15),
        ("Cc1ccccc1", "c1ccccc1", 0.05, 298.15),
        ("CC(=O)C", "CCO", 0.75, 298.15),
        ("CCO", "CC(=O)C", 0.50, 298.15),
        ("CCO", "O", 1.30, 313.15),
        ("CCO", "O", 1.47, 283.15),
        ("CCCCCC", "O", 7.45, 313.15),
        ("c1ccccc1", "O", 7.50, 313.15),
    ]

    rows = []
    for sol, slv, lng, T in data:
        sol_c, slv_c = canonicalize(sol), canonicalize(slv)
        if sol_c and slv_c:
            rows.append({
                "solute_smiles": sol_c,
                "solvent_smiles": slv_c,
                "ln_gamma_inf": lng,
                "temperature": T,
            })

    df = pd.DataFrame(rows)
    print(f"  Records: {len(df)}")
    return df
