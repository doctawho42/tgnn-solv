from __future__ import annotations

import argparse
import re
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Draw, Lipinski, rdMolDescriptors

from tgnn_solv.ionic_features import ionic_feature_summary

DELPHINIDIN_CHLORIDE = "Oc1cc(O)c2cc(O)c(-c3cc(O)c(O)c(O)c3)[o+]c2c1.[Cl-]"

ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a chemistry casebook for report example systems: selected temperature pairs, "
            "slope-level examples, baseline example pairs, and delphinidin solvents."
        )
    )
    parser.add_argument("--temperature-bundle", default="results/temperature_interpretability_bundle")
    parser.add_argument("--baseline-examples", default="results/temperature_extrapolation_baselines/example_pairs.csv")
    parser.add_argument("--train-low", default="results/temperature_extrapolation_baselines/splits/train_low.csv")
    parser.add_argument("--test-high", default="results/temperature_extrapolation_baselines/splits/test_high.csv")
    parser.add_argument("--difficult-audit", default="results/difficult_systems_audit")
    parser.add_argument("--output-dir", default="results/example_system_casebook")
    parser.add_argument("--max-slope-level", type=int, default=6)
    parser.add_argument(
        "--report-figures-dir",
        default="reports/figures",
        help="Directory for one-system-per-figure PDFs used by the report.",
    )
    return parser.parse_args()


def safe_read(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def slugify(text: str, max_len: int = 90) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", str(text)).strip("_")
    text = re.sub(r"_+", "_", text)
    return text[:max_len] or "case"


def canonical_smiles(smiles: str) -> str:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return str(smiles)
    return Chem.MolToSmiles(mol, canonical=True)


def mol_summary(smiles: str) -> dict[str, Any]:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return {
            "formula": "",
            "mw": np.nan,
            "logp": np.nan,
            "tpsa": np.nan,
            "hbd": np.nan,
            "hba": np.nan,
            "rotatable": np.nan,
            "aromatic_rings": np.nan,
            "formal_charge": np.nan,
            "charged_atoms": np.nan,
            "fragments": np.nan,
            "heavy_atoms": np.nan,
        }
    charges = [a.GetFormalCharge() for a in mol.GetAtoms()]
    return {
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "mw": float(Descriptors.MolWt(mol)),
        "logp": float(Crippen.MolLogP(mol)),
        "tpsa": float(rdMolDescriptors.CalcTPSA(mol)),
        "hbd": int(Lipinski.NumHDonors(mol)),
        "hba": int(Lipinski.NumHAcceptors(mol)),
        "rotatable": int(Lipinski.NumRotatableBonds(mol)),
        "aromatic_rings": int(rdMolDescriptors.CalcNumAromaticRings(mol)),
        "formal_charge": int(sum(charges)),
        "charged_atoms": int(sum(1 for c in charges if c != 0)),
        "fragments": int(len(Chem.GetMolFrags(mol))),
        "heavy_atoms": int(mol.GetNumHeavyAtoms()),
    }


def short(text: Any, n: int = 40) -> str:
    text = str(text)
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def append_case(cases: list[dict[str, Any]], row: dict[str, Any], *, role: str, priority: int) -> None:
    pair_key = str(row.get("pair_key", f"{row.get('solute_smiles')}>>{row.get('solvent_smiles')}"))
    cases.append(
        {
            "role": role,
            "report_priority": priority,
            "pair_key": pair_key,
            "solute_smiles": str(row.get("solute_smiles", pair_key.split(">>")[0] if ">>" in pair_key else "")),
            "solvent_smiles": str(row.get("solvent_smiles", pair_key.split(">>")[1] if ">>" in pair_key else "")),
            "solute_name": str(row.get("solute_name", "")),
            "solvent_name": str(row.get("solvent_name", "")),
            "mae_tgnn": row.get("mae_tgnn", np.nan),
            "mae_direct": row.get("mae_direct", np.nan),
            "mae_vant_hoff": row.get("mae_vant_hoff", np.nan),
            "bias_tgnn": row.get("bias_tgnn", np.nan),
            "delta_tgnn_direct": row.get("delta_tgnn_direct", np.nan),
            "min_true": row.get("min_true", np.nan),
            "required_activity_abs_mean": row.get("required_activity_abs_mean", np.nan),
            "slope_error_tgnn": row.get("slope_error_tgnn", np.nan),
            "n_high": row.get("n_high", np.nan),
        }
    )


def choose_slope_level_examples(slope_pairs: pd.DataFrame, max_cases: int) -> pd.DataFrame:
    if slope_pairs.empty:
        return slope_pairs
    preferred = [
        "O=C(O)c1ccccc1C(=O)O>>CC(=O)N(C)C",
        "Cc1cccc(C(=O)O)c1>>CC(C)CO",
        "CC1=CC(=O)c2ccccc2C1=O>>c1ccccc1",
        "CC1(C)[C@@H]2CC[C@@]1(C)[C@@H](O)C2>>Cc1ccc(C)cc1",
        "O=C(O)CCCC(=O)O>>CC(=O)O",
        "OC[C@@H](O)C(O)[C@@H](O)CO>>Cc1ccccc1",
        "COC(=O)/C=C(\\C)N[C@@H](C(=O)[O-])c1ccc(O)cc1.[K+]>>CCC(C)O",
        "CN(C)CCn1[nH]nnc1=S>>CC(C)O",
    ]
    chosen: list[str] = []
    available = set(slope_pairs["pair_key"].astype(str))
    for key in preferred:
        if key in available and key not in chosen:
            chosen.append(key)
        if len(chosen) >= max_cases:
            break
    if len(chosen) < max_cases:
        work = slope_pairs.copy()
        work["name_len"] = work["solute_name"].astype(str).str.len() + work["solvent_name"].astype(str).str.len()
        work = work.sort_values(
            ["abs_level_bias", "slope_error_tgnn", "name_len"],
            ascending=[False, True, True],
        )
        for key in work["pair_key"].astype(str):
            if key not in chosen:
                chosen.append(key)
            if len(chosen) >= max_cases:
                break
    return slope_pairs[slope_pairs["pair_key"].astype(str).isin(chosen)].copy()


def merge_metadata_for_baseline_examples(examples: pd.DataFrame, train_low: pd.DataFrame, test_high: pd.DataFrame) -> pd.DataFrame:
    if examples.empty:
        return examples
    meta = pd.concat(
        [
            train_low[["pair_key", "solute_smiles", "solvent_smiles", "solute_name", "solvent_name"]],
            test_high[["pair_key", "solute_smiles", "solvent_smiles", "solute_name", "solvent_name"]],
        ],
        ignore_index=True,
    ).drop_duplicates("pair_key")
    out = examples.merge(meta, on="pair_key", how="left")
    return out


def delphinidin_cases(summary: pd.DataFrame, errors: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    rows = []
    for _, row in summary.iterrows():
        solvent = str(row.get("solvent_name", ""))
        direct = errors[(errors["solvent_name"].astype(str).str.lower() == solvent.lower()) & (errors["model"] == "DirectGNN")]
        tgnn = errors[(errors["solvent_name"].astype(str).str.lower() == solvent.lower()) & (errors["model"].astype(str).str.match(r"^TGNN", case=False, na=False))]
        rows.append(
            {
                "pair_key": f"{DELPHINIDIN_CHLORIDE}>>{row['solvent_smiles']}",
                "solute_smiles": DELPHINIDIN_CHLORIDE,
                "solvent_smiles": row["solvent_smiles"],
                "solute_name": "Delphinidin chloride",
                "solvent_name": row["solvent_name"],
                "mae_tgnn": float(tgnn["mae"].iloc[0]) if not tgnn.empty else np.nan,
                "mae_direct": float(direct["mae"].iloc[0]) if not direct.empty else np.nan,
                "mae_vant_hoff": np.nan,
                "bias_tgnn": float(tgnn["bias"].iloc[0]) if not tgnn.empty else np.nan,
                "delta_tgnn_direct": np.nan,
                "min_true": float(row.get("ln_x2_min", np.nan)),
                "required_activity_abs_mean": np.nan,
                "slope_error_tgnn": np.nan,
                "n_high": int(row.get("n_rows", 0)),
            }
        )
    return pd.DataFrame(rows)



def _system_class_from_ionic(summary: Any) -> str:
    if not summary:
        return "unknown"
    if getattr(summary, "is_zwitterion", False):
        return "zwitterion"
    if getattr(summary, "is_explicit_salt", False):
        eps = float(getattr(summary, "solvent_eps_r", np.nan))
        if np.isfinite(eps):
            if eps < 30.0:
                return "explicit_salt_low_eps"
            if eps > 50.0:
                return "explicit_salt_high_eps"
            return "explicit_salt_mid_eps"
        return "explicit_salt_eps_unknown"
    if int(getattr(summary, "n_charged_atoms", 0) or 0) > 0:
        return "charged_single_fragment"
    return "neutral"

def infer_chemistry_reason(case: pd.Series) -> tuple[str, str, str]:
    sol = str(case["solute_smiles"])
    slv = str(case["solvent_smiles"])
    pair = str(case["pair_key"])
    sol_name = str(case.get("solute_name", ""))
    solvent_name = str(case.get("solvent_name", ""))
    role = str(case.get("role", ""))
    bias = case.get("bias_tgnn", np.nan)
    bias_text = "overpredicts solubility" if pd.notna(bias) and float(bias) > 0 else "underpredicts solubility"

    if canonical_smiles(sol) == canonical_smiles(DELPHINIDIN_CHLORIDE):
        eps_note = "low-eps contact-ion-pair regime" if slv in {"CC(C)=O", "CCO"} else "polar/protic solvent regime"
        return (
            "anthocyanidin chloride salt; flavylium cation + chloride, many phenolic OH groups",
            f"{eps_note}; no processed Tm/dHfus, so the crystal term must be inferred from an unusual salt/decomposition-like solid",
            "All models regress toward ordinary organic-solute levels and strongly overpredict solubility. The temperature slope is coherent, so the main failure is the vertical level: missing crystal parameters plus contact-pair/ionic-solvation chemistry, not a simple bad temperature trend.",
        )
    if pair == "C=CC(=O)NC(C)(C)C>>NC=O":
        return (
            "neutral acrylamide with one amide donor/acceptor and a bulky tert-butyl hydrophobe",
            "formamide is very polar and H-bonding; activity correction needed is small, so the main constraint is crystal/temperature shape",
            "TGNN wins because the physical branch restrains the high-temperature level. DirectGNN reads the polar amide-formamide match too optimistically and predicts solubility that is much too high.",
        )
    if "dinitro" in sol_name.lower() or "[N+](=O)[O-]" in sol and "C(=O)O" in sol and "N[C@@H]" in sol:
        return (
            "amino-acid-like solute with carboxyl/amine functionality and two strongly electron-withdrawing nitro groups",
            "water can H-bond and solvate polar groups, but the aromatic dinitro scaffold and possible zwitterionic/protonation states create a large positive activity penalty",
            "TGNN overpredicts solubility because collapsed/weak NRTL activity cannot supply the required positive ln(gamma) level shift. DirectGNN happens to learn this water-specific empirical level better in the proxy run.",
        )
    if "Xylitol" in sol_name or "OC[C@@H](O)C(O)[C@@H](O)CO" in sol:
        return (
            "small polyol with five hydroxyl groups: extremely polar and dense H-bond donor/acceptor surface",
            "toluene is apolar and cannot satisfy the H-bond network; the true system needs a large unfavorable activity contribution",
            "TGNN keeps a reasonable slope but predicts the curve too high because NRTL does not express the strong polyol/apolar-solvent mismatch.",
        )
    if "hydroxyphenylglycine" in sol_name.lower() or ".[K+]" in sol:
        return (
            "explicit potassium salt / amino-acid derivative with phenol, carboxylate, ester and conjugated imine/enamine functionality",
            f"{solvent_name} is an alcohol, so it can H-bond, but the solute is still an ion-pair-like multifunctional salt",
            "The level error is a contact-pair/crystal-branch problem: the temperature shape is partly captured, while the absolute solubility needs stronger ionic and specific-solvation features.",
        )
    if "mercapto" in sol_name.lower() or "tetrazole" in sol_name.lower() or "n1[nH]nnc1=S" in sol:
        return (
            "heteroatom-rich dimethylaminoethyl mercaptotetrazole; ionizable/basic amine plus thione/tetrazole tautomerism",
            f"{solvent_name} can stabilize some polar sites, but tautomer/protonation and H-bond patterns are not explicit in the graph labels",
            "The models mainly disagree on vertical level. This is a chemical-form/tautomer and specific-interaction case rather than a pure temperature-slope problem.",
        )
    if "phthalic" in sol_name.lower() or "O=C(O)c1ccccc1C(=O)O" in sol:
        return (
            "aromatic dicarboxylic acid with strong donor/acceptor sites and possible intramolecular H-bonding",
            f"{solvent_name} is a polar aprotic/acid-compatible solvent that can strongly stabilize carboxylic-acid interactions",
            "TGNN often predicts the correct slope but too low a level here, consistent with overestimated crystal penalty or missing favorable acid-solvent association.",
        )
    if "methylbenzoic acid" in sol_name.lower() or "Cc1cccc(C(=O)O)c1" in sol:
        return (
            "hydrophobic aromatic carboxylic acid; one strong carboxyl H-bonding center plus methyl-substituted ring",
            f"{solvent_name} is an alcohol that can both donate and accept H-bonds, giving favorable acid-alcohol association",
            "TGNN underpredicts solubility in several alcohol/aromatic-solvent cases, suggesting the activity branch is not adding enough favorable specific-solvation level shift.",
        )

    if "Vitamin K3" in sol_name or "CC1=CC(=O)c2ccccc2C1=O" in sol:
        return (
            "compact hydrophobic quinone with two strong carbonyl acceptors and an aromatic fused ring",
            f"{solvent_name} is apolar/aromatic, so dispersion and pi-compatible solvation can make the level much higher than an ideal-crystal-dominated estimate",
            "TGNN underpredicts solubility here: the slope is acceptable, but the favorable aromatic/dispersion solvent level is missing from the activity branch.",
        )
    if "Borneol" in sol_name or "[C@@H](O)C2" in sol:
        return (
            "compact terpene alcohol: mostly hydrocarbon surface with one hydroxyl group",
            f"{solvent_name} is apolar/aromatic, so dispersion and hydrophobic compatibility dominate over strong polarity mismatch",
            "The true solubility is high; TGNN tends to make the curve too low, likely because the crystal/ideal-solubility term dominates while favorable dispersion compatibility is underrepresented.",
        )
    if "glutaric" in sol_name.lower() or "O=C(O)CCCC(=O)O" in sol:
        return (
            "aliphatic dicarboxylic acid with flexible chain and two carboxyl groups",
            f"{solvent_name} can participate in carbonyl/acid interactions; acid-acid or acid-ketone association changes the level strongly",
            "Slope can look reasonable, but the level is sensitive to association chemistry that a collapsed NRTL branch cannot represent.",
        )
    if "NC(N)=O.O=P" in sol:
        return (
            "urea-phosphoric-acid adduct / salt-like highly H-bonded solid",
            "water strongly solvates the polar network; the same-pair Van't Hoff line works because the experimental temperature series is internally consistent",
            "This is a good reminder that same-pair temperature extrapolation can be easy even when the molecular form is hard for a general new-solute model.",
        )
    if "COC(=O)c1ccc2" in sol:
        return (
            "rigid aromatic diester with large hydrophobic pi surface and two ester acceptors",
            f"{solvent_name} controls the balance between dispersion and polar carbonyl interactions",
            "The example is mainly a clean same-pair temperature-series case: Van't Hoff interpolation/extrapolation benefits from stable slope, whereas general models must infer the level from structure.",
        )
    if "O=C(O)CCCCC(=O)O" in sol:
        return (
            "flexible aliphatic dicarboxylic acid with two carboxyl groups",
            f"{solvent_name} provides carbonyl/dispersion compatibility but association can shift the absolute level",
            "Van't Hoff handles the pair-specific trend; neural models need explicit activity/association signal to reproduce the level for new chemistry.",
        )

    sol_desc = mol_summary(sol)
    if sol_desc.get("formal_charge", 0) or sol_desc.get("charged_atoms", 0):
        interaction = "charged or zwitterionic solute; activity depends on ion-pairing, dielectric regime and specific solvation"
    elif sol_desc.get("hbd", 0) >= 3 or sol_desc.get("hba", 0) >= 5:
        interaction = "highly H-bonding solute; solvent mismatch can dominate ln(gamma)"
    elif sol_desc.get("logp", 0) > 3:
        interaction = "hydrophobic/aromatic solute; dispersion compatibility and crystal packing dominate"
    else:
        interaction = "neutral molecular solute with moderate polarity"
    reason = "TGNN " + bias_text + "; inspect whether crystal level or activity level is providing the missing vertical shift."
    return (interaction, f"solvent: {solvent_name}", reason)


def build_cases(args: argparse.Namespace) -> pd.DataFrame:
    bundle = Path(args.temperature_bundle)
    selected = safe_read(bundle / "selected_pairs.csv")
    slope_pairs = safe_read(bundle / "slope_level_pairs.csv")
    examples = safe_read(Path(args.baseline_examples))
    train_low = safe_read(Path(args.train_low))
    test_high = safe_read(Path(args.test_high))
    delph_summary = safe_read(Path(args.difficult_audit) / "delphinidin_summary.csv")
    delph_errors = safe_read(Path(args.difficult_audit) / "delphinidin_model_errors.csv")

    cases: list[dict[str, Any]] = []
    priority = 10
    if not selected.empty:
        for _, row in selected.iterrows():
            append_case(cases, row.to_dict(), role=f"temperature_profile:{row.get('category')}", priority=priority)
            priority += 10
    if not slope_pairs.empty:
        slope_examples = choose_slope_level_examples(slope_pairs, args.max_slope_level)
        for _, row in slope_examples.iterrows():
            append_case(cases, row.to_dict(), role="slope_level_gallery", priority=priority)
            priority += 10
    if not examples.empty and not train_low.empty and not test_high.empty:
        ex = merge_metadata_for_baseline_examples(examples, train_low, test_high)
        for _, row in ex.iterrows():
            append_case(cases, row.to_dict(), role="temperature_baseline_example", priority=priority)
            priority += 10
    delph = delphinidin_cases(delph_summary, delph_errors)
    if not delph.empty:
        for _, row in delph.iterrows():
            append_case(cases, row.to_dict(), role="delphinidin_solvent_series", priority=priority)
            priority += 10

    if not cases:
        return pd.DataFrame()
    df = pd.DataFrame(cases)
    # Merge duplicate pair keys while preserving all roles.
    agg: dict[str, Any] = {
        "role": lambda s: "; ".join(dict.fromkeys(map(str, s))),
        "report_priority": "min",
        "solute_smiles": "first",
        "solvent_smiles": "first",
        "solute_name": "first",
        "solvent_name": "first",
    }
    for col in [
        "mae_tgnn",
        "mae_direct",
        "mae_vant_hoff",
        "bias_tgnn",
        "delta_tgnn_direct",
        "min_true",
        "required_activity_abs_mean",
        "slope_error_tgnn",
        "n_high",
    ]:
        agg[col] = lambda s: next((x for x in s if pd.notna(x)), np.nan)
    df = df.groupby("pair_key", as_index=False).agg(agg)

    rows = []
    for _, row in df.iterrows():
        sol_desc = mol_summary(row["solute_smiles"])
        slv_desc = mol_summary(row["solvent_smiles"])
        try:
            ionic = ionic_feature_summary(row["solute_smiles"], row["solvent_smiles"])
        except Exception:
            ionic = {}
        chem_class, interaction, interpretation = infer_chemistry_reason(row)
        out = row.to_dict()
        for k, v in sol_desc.items():
            out[f"solute_{k}"] = v
        for k, v in slv_desc.items():
            out[f"solvent_{k}"] = v
        out.update(
            {
                "solvent_eps_r": getattr(ionic, "solvent_eps_r", np.nan),
                "system_class": _system_class_from_ionic(ionic),
                "chemistry_class": chem_class,
                "dominant_interactions": interaction,
                "interpretation": interpretation,
                "case_title": f"{short(row['solute_name'], 34)} / {short(row['solvent_name'], 22)}",
            }
        )
        rows.append(out)
    return pd.DataFrame(rows).sort_values(["report_priority", "pair_key"]).reset_index(drop=True)


def write_images(df: pd.DataFrame, image_dir: Path) -> pd.DataFrame:
    image_dir.mkdir(parents=True, exist_ok=True)
    solute_paths = []
    solvent_paths = []
    pair_paths = []
    for i, row in df.iterrows():
        slug = f"{i:02d}_{slugify(row['solute_name'])}_{slugify(row['solvent_name'])}"
        mol_sol = Chem.MolFromSmiles(str(row["solute_smiles"]))
        mol_slv = Chem.MolFromSmiles(str(row["solvent_smiles"]))
        solute_path = image_dir / f"{slug}_solute.png"
        solvent_path = image_dir / f"{slug}_solvent.png"
        pair_path = image_dir / f"{slug}_pair.png"
        if mol_sol is not None:
            Draw.MolToFile(mol_sol, str(solute_path), size=(520, 360), legend=str(row["solute_name"]))
        if mol_slv is not None:
            Draw.MolToFile(mol_slv, str(solvent_path), size=(280, 220), legend=str(row["solvent_name"]))
        mols = [m for m in [mol_sol, mol_slv] if m is not None]
        legends = [str(row["solute_name"]), str(row["solvent_name"])] if len(mols) == 2 else []
        if mols:
            img = Draw.MolsToGridImage(mols, molsPerRow=2, subImgSize=(360, 260), legends=legends)
            img.save(pair_path)
        solute_paths.append(str(solute_path))
        solvent_paths.append(str(solvent_path))
        pair_paths.append(str(pair_path))
    df = df.copy()
    df["solute_image"] = solute_paths
    df["solvent_image"] = solvent_paths
    df["pair_image"] = pair_paths
    return df


def write_markdown(df: pd.DataFrame, output: Path) -> None:
    lines = ["# Example System Chemistry Casebook", ""]
    for _, row in df.iterrows():
        lines.extend(
            [
                f"## {row['case_title']}",
                "",
                f"- Role: `{row['role']}`",
                f"- Pair key: `{row['pair_key']}`",
                f"- System class: `{row['system_class']}`; solvent eps_r: `{row['solvent_eps_r']}`",
                f"- Metrics: TGNN MAE `{row.get('mae_tgnn', np.nan):.3g}`, DirectGNN MAE `{row.get('mae_direct', np.nan):.3g}`, Van't Hoff MAE `{row.get('mae_vant_hoff', np.nan):.3g}`",
                f"- Solute descriptors: formula `{row['solute_formula']}`, MW `{row['solute_mw']:.1f}`, LogP `{row['solute_logp']:.2f}`, TPSA `{row['solute_tpsa']:.1f}`, HBD/HBA `{row['solute_hbd']}/{row['solute_hba']}`, charged atoms `{row['solute_charged_atoms']}`",
                f"- Chemistry: {row['chemistry_class']}",
                f"- Interactions: {row['dominant_interactions']}",
                f"- Interpretation: {row['interpretation']}",
                "",
            ]
        )
    output.write_text("\n".join(lines), encoding="utf-8")


def write_report_structure_figures(df: pd.DataFrame, figures_dir: Path, manifest_path: Path) -> None:
    """Write readable one-system structure PDFs for report text.

    The report intentionally does not use a dense gallery/card figure. Each
    selected example gets its own structure image, while the chemical
    interpretation remains in normal body text.
    """
    figures_dir.mkdir(parents=True, exist_ok=True)
    keep_titles = [
        "N-tert-butylacrylamide / formamide",
        "2,4-dinitro-L-phenylalanine / water",
        "Delphinidin / acetone",
        "Delphinidin / ethanol",
        "Xylitol / toluene",
        "Vitamin K3 / benzene",
        "Borneol / p-xylene",
        "o-phthalic acid / DMAc",
        "m-methylbenzoic acid / isobutanol",
        "Glutaric acid / acetic acid",
    ]
    rows: list[dict[str, Any]] = []
    work = df[df["case_title"].isin(keep_titles)].copy()
    for _, row in work.iterrows():
        image_path = Path(str(row["pair_image"]))
        if not image_path.is_absolute():
            image_path = ROOT / image_path
        if not image_path.exists():
            continue
        img = plt.imread(str(image_path))
        fig, ax = plt.subplots(figsize=(6.8, 3.3))
        ax.imshow(img)
        ax.axis("off")
        fig.tight_layout(pad=0.02)
        filename = f"example_system_{slugify(str(row['case_title']).lower())}.pdf"
        fig.savefig(figures_dir / filename, bbox_inches="tight", pad_inches=0.02, facecolor="white")
        plt.close(fig)
        rows.append(
            {
                "case_title": row["case_title"],
                "figure_file": filename,
                "role": row["role"],
                "mae_tgnn": row.get("mae_tgnn"),
                "mae_direct": row.get("mae_direct"),
                "bias_tgnn": row.get("bias_tgnn"),
                "system_class": row.get("system_class"),
            }
        )
    pd.DataFrame(rows).to_csv(manifest_path, index=False)


def main() -> None:
    args = parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = build_cases(args)
    if df.empty:
        raise SystemExit("No example systems found. Run temperature interpretability and difficult-system audits first.")
    df = write_images(df, out / "molecules")
    df.to_csv(out / "example_system_casebook.csv", index=False)
    write_markdown(df, out / "example_system_casebook.md")
    write_report_structure_figures(
        df,
        Path(args.report_figures_dir),
        out / "report_structure_figures.csv",
    )
    print(f"Wrote {len(df)} example-system cases to {out}")


if __name__ == "__main__":
    main()
