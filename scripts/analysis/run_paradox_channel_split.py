#!/usr/bin/env python3
"""Verify R2's claim: is the e5 grounding paradox (grounded->oracle) driven by the solvent channel,
and ~0 on the both-reference subset? Slice the paradox by VT-2005 coverage of solute vs solvent."""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
from pathlib import Path
import numpy as np, pandas as pd
from rdkit import Chem
from rdkit import RDLogger
RDLogger.DisableLog("rdApp.*")

ROOT = Path("/Users/nikitapolomosnov/PycharmProjects/tgnn-solv")

def canon(s):
    m = Chem.MolFromSmiles(str(s))
    return Chem.MolToSmiles(m) if m else None

# VT-2005 coverage set
prof = pd.read_csv(ROOT / "results/sigma_profile_artifact/sigma_profiles.csv", usecols=["smiles"])
VT = set(c for c in (canon(s) for s in prof["smiles"]) if c)
print(f"VT-2005 profiles: {len(prof)} rows -> {len(VT)} canonical SMILES")

rows_all = []
for seed in ["seed_42", "seed_43"]:
    g = pd.read_csv(ROOT / f"results/e5_sigma_grounding/{seed}/grounded_a_predictions.csv")
    o = pd.read_csv(ROOT / f"results/e5_sigma_grounding/{seed}/oracle_predictions.csv")
    g = g[g["has_solubility"] == True].reset_index(drop=True)
    o = o[o["has_solubility"] == True].reset_index(drop=True)
    assert len(g) == len(o), f"{seed}: {len(g)} vs {len(o)}"
    # grounded and oracle are the SAME test set in the SAME order -> align by position
    assert (g["solute_smiles"].values == o["solute_smiles"].values).all(), "row order mismatch"
    assert (g["solvent_smiles"].values == o["solvent_smiles"].values).all(), "row order mismatch"
    m = g[["solute_smiles", "solvent_smiles", "abs_error"]].rename(columns={"abs_error": "abs_error_g"})
    m["abs_error_o"] = o["abs_error"].values
    m["seed"] = seed
    rows_all.append(m)
df = pd.concat(rows_all, ignore_index=True)
print(f"merged supervised rows (x3 seeds): {len(df)}  (per seed ~{len(df)//3})")

# coverage flags (canonicalize once per unique smiles)
uniq = {s: (canon(s) in VT) for s in pd.unique(df[["solute_smiles", "solvent_smiles"]].values.ravel())}
df["solute_vt"] = df["solute_smiles"].map(uniq)
df["solvent_vt"] = df["solvent_smiles"].map(uniq)

print(f"\nunique solutes: {df['solute_smiles'].nunique()}  in VT: {df.loc[df['solute_vt'],'solute_smiles'].nunique()}")
print(f"unique solvents: {df['solvent_smiles'].nunique()}  in VT: {df.loc[df['solvent_vt'],'solvent_smiles'].nunique()}")
print(f"rows solute_vt: {df['solute_vt'].mean()*100:.1f}%   solvent_vt: {df['solvent_vt'].mean()*100:.1f}%")

def rep(sub, label):
    if len(sub) == 0:
        print(f"  {label:34s} n=0"); return
    # per-seed paradox then average, so it matches the 3-seed headline
    per = sub.groupby("seed").apply(lambda x: x["abs_error_o"].mean() - x["abs_error_g"].mean())
    gm = sub.groupby("seed")["abs_error_g"].mean().mean()
    om = sub.groupby("seed")["abs_error_o"].mean().mean()
    print(f"  {label:34s} n/seed~{len(sub)//3:5d}  grounded={gm:.3f}  oracle={om:.3f}  paradox={per.mean():+.3f} (sd {per.std():.3f})")

print("\n=== paradox (oracle MAE - grounded MAE), per-seed then averaged ===")
rep(df, "ALL supervised")
rep(df[df["solute_vt"] & df["solvent_vt"]], "both in VT-2005 (both-reference)")
rep(df[~df["solute_vt"] & df["solvent_vt"]], "solvent-only in VT (solute NOT)")
rep(df[df["solute_vt"] & ~df["solvent_vt"]], "solute-only in VT (solvent NOT)")
rep(df[~df["solute_vt"] & ~df["solvent_vt"]], "neither in VT")
