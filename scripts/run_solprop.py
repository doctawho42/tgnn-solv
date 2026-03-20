#!/usr/bin/env python
"""
Run SolProp (Vermeire et al., JACS 2022) predictions on TGNN-Solv test set.

Run in solprop conda environment:
    conda activate solprop
    python scripts/run_solprop.py \
        --input data/processed/test.csv \
        --output data/processed/solprop_predictions.csv \
        --temperature_dependent

Outputs CSV with columns:
    solute_smiles, solvent_smiles, temperature,
    log_S_solprop (log10 mol/L), ln_x2_solprop (converted)
"""

import argparse
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


def check_solprop_available():
    """Check if SolProp is importable."""
    try:
        # SolProp ML package
        from solprop_ml.solprop_ml import (
            SolPropPredictor,
        )
        print("SolProp ML package found.")
        return "package"
    except ImportError:
        pass

    try:
        # Direct import from cloned repo
        sys.path.insert(0, "SolProp_ML")
        from solprop_ml import SolPropPredictor
        print("SolProp found via local clone.")
        return "local"
    except ImportError:
        pass

    # Try notebook-style import
    try:
        from SolProp_ML.solprop_ml.solprop_ml import SolPropPredictor
        print("SolProp found via SolProp_ML directory.")
        return "subdir"
    except ImportError:
        pass

    print("ERROR: SolProp not found.")
    print("Install with: conda install -c fhvermei solprop_ml")
    print("Or clone: git clone https://github.com/fhvermei/SolProp_ML.git")
    return None


def load_solprop_predictor():
    """Load SolProp predictor, handling different import paths."""
    try:
        from solprop_ml.solprop_ml import SolPropPredictor
        return SolPropPredictor()
    except ImportError:
        pass

    try:
        from solprop_ml import SolPropPredictor
        return SolPropPredictor()
    except ImportError:
        pass

    # If package import fails, try the functional API
    try:
        from solprop_ml.solprop_ml import (
            predict_solubility as sp_predict,
        )
        return sp_predict
    except ImportError:
        raise ImportError("Cannot load SolProp predictor")


def convert_logS_to_ln_x2(
    log_S_mol_L: float,
    solvent_smiles: str,
    temperature: float = 298.15,
) -> float:
    """
    Convert log10(S in mol/L) to ln(x₂ mole fraction).

    x₂ = S / (S + C_solvent)
    where C_solvent = density_solvent / MW_solvent * 1000

    For water: C_water = 55.35 mol/L
    For others: approximate from MW, assuming density ≈ 0.85 g/mL
    """
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    S_mol_L = 10.0 ** log_S_mol_L

    # Solvent molar concentration
    mol = Chem.MolFromSmiles(solvent_smiles)
    if mol is None:
        return np.nan

    mw = Descriptors.MolWt(mol)

    # Known densities for common solvents (g/mL at 25°C)
    DENSITIES = {
        "O": 0.997,                    # water
        "CCO": 0.789,                  # ethanol
        "CO": 0.791,                   # methanol
        "CC(=O)C": 0.784,             # acetone
        "CCCCCC": 0.659,              # hexane
        "c1ccccc1": 0.879,            # benzene
        "Cc1ccccc1": 0.867,           # toluene
        "ClCCl": 1.327,               # DCM
        "ClC(Cl)Cl": 1.489,           # chloroform
        "CS(=O)C": 1.100,             # DMSO
        "CC#N": 0.786,                # acetonitrile
        "CCOCC": 0.713,               # diethyl ether
        "C1CCOC1": 0.889,             # THF
        "CCOC(=O)C": 0.902,           # ethyl acetate
        "CC(=O)O": 1.049,             # acetic acid
        "CCCCO": 0.810,               # 1-butanol
        "CC(O)C": 0.786,              # isopropanol
        "CCCO": 0.803,                # 1-propanol
        "C1CCCCC1": 0.779,            # cyclohexane
        "CCCCCCC": 0.684,             # heptane
        "CCCCCCCC": 0.703,            # octane
        "c1ccncc1": 0.982,            # pyridine
        "CN(C)C=O": 0.944,            # DMF
        "CN1CCCC1=O": 1.028,          # NMP
    }

    # Canonicalize for lookup
    can_smi = Chem.MolToSmiles(mol, canonical=True)
    density = DENSITIES.get(can_smi, 0.85)  # default 0.85 g/mL

    C_solvent = density * 1000.0 / mw  # mol/L

    # Mole fraction
    x2 = S_mol_L / (S_mol_L + C_solvent)

    if x2 <= 0 or x2 > 1:
        return np.nan

    return float(np.log(x2))


def run_solprop_predictions(
    df: pd.DataFrame,
    temperature_dependent: bool = True,
    batch_size: int = 100,
) -> pd.DataFrame:
    """
    Run SolProp on a DataFrame with solute_smiles, solvent_smiles, temperature.

    Returns DataFrame with predictions appended.
    """
    print(f"\nRunning SolProp on {len(df):,} records...")
    print(f"  Temperature-dependent: {temperature_dependent}")

    # Filter to solubility records only
    if "has_solubility" in df.columns:
        work_df = df[df["has_solubility"]].copy()
    else:
        work_df = df.copy()

    results = []
    n_success = 0
    n_fail = 0
    t0 = time.time()

    # Try to use SolProp's batch API if available
    try:
        predictor = load_solprop_predictor()
        use_predictor = True
        print("  Using SolProp predictor object")
    except Exception as e:
        print(f"  Predictor load failed: {e}")
        use_predictor = False

    if not use_predictor:
        raise RuntimeError(
            "SolProp predictor not available. Install solprop_ml or add a "
            "local SolProp_ML clone to PYTHONPATH."
        )

    if use_predictor:
        for i, (_, row) in enumerate(work_df.iterrows()):
            sol_smi = row["solute_smiles"]
            slv_smi = row["solvent_smiles"]
            T = row.get("temperature", 298.15)

            try:
                # SolProp API varies by version
                # Try different calling conventions
                result = _call_solprop(
                    predictor, sol_smi, slv_smi, T,
                    temperature_dependent,
                )

                if result is not None:
                    log_S = result
                    ln_x2 = convert_logS_to_ln_x2(log_S, slv_smi, T)

                    results.append({
                        "solute_smiles": sol_smi,
                        "solvent_smiles": slv_smi,
                        "temperature": T,
                        "log_S_solprop": log_S,
                        "ln_x2_solprop": ln_x2,
                    })
                    n_success += 1
                else:
                    n_fail += 1

            except Exception as e:
                n_fail += 1
                if n_fail <= 5:
                    print(f"    Error on {sol_smi[:30]}/{slv_smi}: {e}")

            if (i + 1) % 500 == 0:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed
                print(f"    {i+1:,}/{len(work_df):,} "
                      f"({n_success} ok, {n_fail} fail, "
                      f"{rate:.1f} samples/s)")

    elapsed = time.time() - t0
    print(f"\n  Completed in {elapsed:.0f}s")
    print(f"  Success: {n_success:,}, Failed: {n_fail:,}")

    if not results:
        print("  No successful predictions!")
        return pd.DataFrame()

    return pd.DataFrame(results)


def _call_solprop(predictor, sol_smi, slv_smi, T, T_dependent):
    """
    Call SolProp predictor with different API versions.

    SolProp API has changed between versions.
    Try multiple calling conventions.
    """
    # Version 1: SolPropPredictor object
    if hasattr(predictor, "predict"):
        try:
            result = predictor.predict(
                solute_smiles=sol_smi,
                solvent_smiles=slv_smi,
                T=T if T_dependent else 298.15,
            )
            # result might be dict or float
            if isinstance(result, dict):
                return result.get("log_S", result.get("logS", None))
            return float(result)
        except TypeError:
            pass

    # Version 2: predict_solubility function
    if callable(predictor):
        try:
            result = predictor(
                solute=sol_smi,
                solvent=slv_smi,
                temp=T if T_dependent else 298.15,
            )
            if isinstance(result, dict):
                return result.get("log_S", None)
            return float(result)
        except Exception:
            pass

    # Version 3: SolProp class with separate methods
    if hasattr(predictor, "calc_solubility"):
        try:
            result = predictor.calc_solubility(
                sol_smi, slv_smi,
                T=T if T_dependent else 298.15,
            )
            return float(result)
        except Exception:
            pass

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Run SolProp predictions on TGNN-Solv test data"
    )
    parser.add_argument(
        "--input", type=str, required=True,
        help="Input CSV (from TGNN-Solv data pipeline)"
    )
    parser.add_argument(
        "--output", type=str, required=True,
        help="Output CSV with SolProp predictions"
    )
    parser.add_argument(
        "--temperature_dependent", action="store_true",
        help="Use temperature-dependent predictions"
    )
    parser.add_argument(
        "--max_records", type=int, default=None,
        help="Limit number of records (for testing)"
    )
    args = parser.parse_args()

    # Check SolProp
    status = check_solprop_available()
    if status is None:
        sys.exit(1)

    # Load data
    print(f"\nLoading {args.input}...")
    df = pd.read_csv(args.input)
    print(f"  Records: {len(df):,}")

    if args.max_records:
        df = df.head(args.max_records)
        print(f"  Limited to: {len(df):,}")

    # Run predictions
    results = run_solprop_predictions(
        df,
        temperature_dependent=args.temperature_dependent,
    )

    # Save
    if len(results) > 0:
        results.to_csv(args.output, index=False)
        print(f"\nSaved {len(results):,} predictions to {args.output}")
    else:
        print("\nNo predictions generated!")


if __name__ == "__main__":
    main()
