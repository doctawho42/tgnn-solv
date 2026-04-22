from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import linregress

R = 8.314


@dataclass
class Paths:
    combined_predictions: Path
    train_low: Path
    test_high: Path
    example_pairs: Path
    tgnn_proxy_intermediates: Path
    output_dir: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build reproducible temperature-interpretability artifacts for the supervisor report."
    )
    parser.add_argument(
        "--combined-predictions",
        default="results/temperature_extrapolation_failure_diagnostics/combined_predictions.csv",
    )
    parser.add_argument(
        "--train-low",
        default="results/temperature_extrapolation_baselines/splits/train_low.csv",
    )
    parser.add_argument(
        "--test-high",
        default="results/temperature_extrapolation_baselines/splits/test_high.csv",
    )
    parser.add_argument(
        "--example-pairs",
        default="results/temperature_extrapolation_baselines/example_pairs.csv",
    )
    parser.add_argument(
        "--tgnn-proxy-intermediates",
        default="results/temperature_extrapolation_slope_diagnostics/tgnn_proxy_intermediates/intermediates.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="results/temperature_interpretability_bundle",
    )
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_inputs(paths: Paths) -> dict[str, pd.DataFrame]:
    combined = pd.read_csv(paths.combined_predictions)
    train_low = pd.read_csv(paths.train_low)
    test_high = pd.read_csv(paths.test_high)
    example_pairs = pd.read_csv(paths.example_pairs)
    proxy = pd.read_csv(paths.tgnn_proxy_intermediates)
    return {
        "combined": combined,
        "train_low": train_low,
        "test_high": test_high,
        "example_pairs": example_pairs,
        "proxy": proxy,
    }


def build_pair_metadata(train_low: pd.DataFrame, test_high: pd.DataFrame, proxy: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for df in (train_low, test_high):
        cols = ["pair_key", "solute_smiles", "solvent_smiles", "solute_name", "solvent_name"]
        frames.append(df[cols].drop_duplicates("pair_key"))
    frames.append(
        proxy[
            ["pair_key", "solute_smiles", "solvent_smiles", "solute_name", "solvent_name"]
        ].drop_duplicates("pair_key")
    )
    meta = pd.concat(frames, ignore_index=True).drop_duplicates("pair_key")
    return meta


def build_wide_predictions(combined: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    wide = combined.pivot_table(
        index=["pair_key", "solute_smiles", "solvent_smiles", "temperature", "ln_x2_true"],
        columns="model",
        values="ln_x2_pred",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    wide = wide.rename(columns={"temperature": "T"})
    wide = wide.merge(
        meta[["pair_key", "solute_name", "solvent_name"]].drop_duplicates("pair_key"),
        on="pair_key",
        how="left",
    )
    return wide


def build_pair_metrics(wide: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for pair_key, group in wide.groupby("pair_key"):
        if len(group) < 2:
            continue
        slope_true = np.nan
        slope_tgnn = np.nan
        slope_direct = np.nan
        if len(group) >= 3:
            x = 1.0 / group["T"].to_numpy()
            slope_true = linregress(x, group["ln_x2_true"].to_numpy()).slope
            slope_tgnn = linregress(x, group["tgnn_proxy_p1_8_1"].to_numpy()).slope
            slope_direct = linregress(x, group["directgnn_proxy_ep10"].to_numpy()).slope
        rows.append(
            {
                "pair_key": pair_key,
                "solute_smiles": group["solute_smiles"].iloc[0],
                "solvent_smiles": group["solvent_smiles"].iloc[0],
                "solute_name": group["solute_name"].iloc[0],
                "solvent_name": group["solvent_name"].iloc[0],
                "n_high": len(group),
                "mae_tgnn": (group["tgnn_proxy_p1_8_1"] - group["ln_x2_true"]).abs().mean(),
                "mae_direct": (group["directgnn_proxy_ep10"] - group["ln_x2_true"]).abs().mean(),
                "mae_vant_hoff": (group["pair_vant_hoff"] - group["ln_x2_true"]).abs().mean(),
                "bias_tgnn": (group["tgnn_proxy_p1_8_1"] - group["ln_x2_true"]).mean(),
                "bias_direct": (group["directgnn_proxy_ep10"] - group["ln_x2_true"]).mean(),
                "delta_tgnn_direct": (
                    (group["tgnn_proxy_p1_8_1"] - group["ln_x2_true"]).abs().mean()
                    - (group["directgnn_proxy_ep10"] - group["ln_x2_true"]).abs().mean()
                ),
                "min_true": group["ln_x2_true"].min(),
                "max_true": group["ln_x2_true"].max(),
                "pred_std_tgnn": group["tgnn_proxy_p1_8_1"].std(),
                "pred_std_direct": group["directgnn_proxy_ep10"].std(),
                "slope_true": slope_true,
                "slope_tgnn": slope_tgnn,
                "slope_direct": slope_direct,
                "slope_error_tgnn": abs(slope_tgnn - slope_true) if np.isfinite(slope_true) else np.nan,
                "slope_error_direct": abs(slope_direct - slope_true) if np.isfinite(slope_true) else np.nan,
            }
        )
    metrics = pd.DataFrame(rows)
    return metrics.sort_values(["delta_tgnn_direct", "mae_tgnn", "pair_key"]).reset_index(drop=True)


def build_required_activity(proxy: pd.DataFrame) -> pd.DataFrame:
    work = proxy.copy()
    work["required_activity_to_match_true"] = -work["Phi_pred"] - work["ln_x2_true"]
    agg = (
        work.groupby("pair_key")
        .agg(
            solute_name=("solute_name", "first"),
            solvent_name=("solvent_name", "first"),
            n_proxy=("temperature", "size"),
            required_activity_mean=("required_activity_to_match_true", "mean"),
            required_activity_abs_mean=("required_activity_to_match_true", lambda s: s.abs().mean()),
            min_true=("ln_x2_true", "min"),
            mean_phi=("Phi_pred", "mean"),
            mean_ln_gamma_pred=("ln_gamma2_pred", "mean"),
        )
        .reset_index()
    )
    return agg


def build_slope_level_pairs(pair_metrics: pd.DataFrame, required_activity: pd.DataFrame) -> pd.DataFrame:
    work = pair_metrics[pair_metrics["n_high"] >= 3].copy()
    if work.empty:
        return work
    slope_cut = work["slope_error_tgnn"].quantile(0.30)
    bias_cut = work["bias_tgnn"].abs().quantile(0.70)
    work["abs_level_bias"] = work["bias_tgnn"].abs()
    selected = work[
        (work["slope_error_tgnn"] <= slope_cut)
        & (work["abs_level_bias"] >= bias_cut)
    ].copy()
    selected = selected.merge(
        required_activity[
            ["pair_key", "required_activity_mean", "required_activity_abs_mean"]
        ],
        on="pair_key",
        how="left",
    )
    return selected.sort_values(
        ["abs_level_bias", "required_activity_abs_mean", "pair_key"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def _readable_name_score(name: str) -> tuple[int, int]:
    if not isinstance(name, str) or not name:
        return (10_000, 10_000)
    return (len(name), name.count(",") + name.count("[") + name.count("@"))


def pick_pair(
    frame: pd.DataFrame,
    *,
    used: set[str],
    sort_by: list[str],
    ascending: list[bool],
    min_high: int = 3,
    filters: list[tuple[str, str, float]] | None = None,
) -> str | None:
    work = frame.copy()
    work = work[work["n_high"] >= min_high]
    for col, op, value in filters or []:
        if op == "<=":
            work = work[work[col] <= value]
        elif op == ">=":
            work = work[work[col] >= value]
        elif op == "<":
            work = work[work[col] < value]
        elif op == ">":
            work = work[work[col] > value]
    work = work[~work["pair_key"].isin(used)].copy()
    if work.empty:
        return None
    work["solute_name_score"] = work["solute_name"].map(lambda x: _readable_name_score(str(x))[0])
    work["solute_symbol_score"] = work["solute_name"].map(lambda x: _readable_name_score(str(x))[1])
    order = sort_by + ["solute_name_score", "solute_symbol_score", "pair_key"]
    asc = ascending + [True, True, True]
    return str(work.sort_values(order, ascending=asc).iloc[0]["pair_key"])


def pick_preferred_pair(
    frame: pd.DataFrame,
    candidates: list[str],
    *,
    used: set[str],
    min_high: int = 3,
) -> str | None:
    work = frame.copy()
    if "n_high" in work.columns:
        work = work[work["n_high"] >= min_high]
    work = work[~work["pair_key"].isin(used)]
    candidate_set = [key for key in candidates if key in set(work["pair_key"])]
    if not candidate_set:
        return None
    for key in candidate_set:
        return key
    return None


def select_representative_pairs(
    pair_metrics: pd.DataFrame,
    slope_level_pairs: pd.DataFrame,
    required_activity: pd.DataFrame,
) -> pd.DataFrame:
    used: set[str] = set()
    rows: list[dict[str, str | float | int]] = []

    preferred_by_category = {
        "tgnn_wins": [
            "C=CC(=O)NC(C)(C)C>>NC=O",
            "Cn1c(=O)c2c(ncn2C)n(C)c1=O>>O",
            "Cc1ccccc1S(=O)(=O)N[C@@H](C)C(=O)O>>CO",
        ],
        "tgnn_loses": [
            "N[C@@H](Cc1ccc([N+](=O)[O-])cc1[N+](=O)[O-])C(=O)O>>O",
            "O=C(O)c1ccccc1>>Cc1cccc(C)c1",
            "CC(=O)NC1=CC=C(O)C=C1>>CC(C)CO",
        ],
        "high_activity_need": [
            "Oc1cc(O)c2cc(O)c(-c3cc(O)c(O)c(O)c3)[o+]c2c1.[Cl-]>>CC(C)=O",
            "O=C(O)CCCCCCC(=O)O>>O",
            "OC[C@@H](O)C(O)[C@@H](O)CO>>Cc1ccccc1",
        ],
        "low_solubility_tail": [
            "Oc1cc(O)c2cc(O)c(-c3cc(O)c(O)c(O)c3)[o+]c2c1.[Cl-]>>CCO",
            "N[C@@H](Cc1ccc([N+](=O)[O-])cc1[N+](=O)[O-])C(=O)O>>O",
            "O=C(O)c1ccccc1>>Cc1cccc(C)c1",
        ],
    }

    winners = pick_preferred_pair(
        pair_metrics[
            (pair_metrics["delta_tgnn_direct"] < -1.0)
            & (pair_metrics["mae_tgnn"] < 1.5)
            & (pair_metrics["mae_vant_hoff"] < 1.0)
        ],
        preferred_by_category["tgnn_wins"],
        used=used,
    )
    if winners is None:
        winners = pick_pair(
            pair_metrics,
            used=used,
            sort_by=["delta_tgnn_direct", "mae_tgnn"],
            ascending=[True, True],
            filters=[
                ("delta_tgnn_direct", "<", -1.0),
                ("mae_tgnn", "<", 1.5),
                ("mae_vant_hoff", "<", 1.0),
            ],
        )
    if winners is not None:
        used.add(winners)
        rows.append({"category": "tgnn_wins", "pair_key": winners})

    losers = pick_preferred_pair(
        pair_metrics[
            (pair_metrics["delta_tgnn_direct"] > 1.5)
            & (pair_metrics["mae_direct"] < 1.0)
        ],
        preferred_by_category["tgnn_loses"],
        used=used,
    )
    if losers is None:
        losers = pick_pair(
            pair_metrics,
            used=used,
            sort_by=["delta_tgnn_direct"],
            ascending=[False],
            filters=[
                ("delta_tgnn_direct", ">", 1.5),
                ("mae_direct", "<", 1.0),
            ],
        )
    if losers is not None:
        used.add(losers)
        rows.append({"category": "tgnn_loses", "pair_key": losers})

    activity_df = slope_level_pairs.merge(
        required_activity[["pair_key", "required_activity_abs_mean"]],
        on="pair_key",
        how="left",
        suffixes=("", "_dup"),
    )
    activity_work = activity_df.rename(columns={"required_activity_abs_mean": "activity_need"})
    high_activity = pick_preferred_pair(
        activity_work[activity_work["activity_need"] > 2.0],
        preferred_by_category["high_activity_need"],
        used=used,
    )
    if high_activity is None:
        high_activity = pick_pair(
            activity_work,
            used=used,
            sort_by=["activity_need", "abs_level_bias"],
            ascending=[False, False],
            filters=[
                ("activity_need", ">", 2.0),
            ],
        )
    if high_activity is not None:
        used.add(high_activity)
        rows.append({"category": "high_activity_need", "pair_key": high_activity})

    low_tail = pick_preferred_pair(
        pair_metrics[pair_metrics["min_true"] <= -8.0],
        preferred_by_category["low_solubility_tail"],
        used=used,
    )
    if low_tail is None:
        low_tail = pick_pair(
            pair_metrics,
            used=used,
            sort_by=["mae_tgnn", "min_true"],
            ascending=[False, True],
            filters=[
                ("min_true", "<=", -8.0),
            ],
        )
    if low_tail is not None:
        used.add(low_tail)
        rows.append({"category": "low_solubility_tail", "pair_key": low_tail})

    selected = pd.DataFrame(rows)
    if selected.empty:
        return selected
    selected = selected.merge(
        pair_metrics[
            [
                "pair_key",
                "solute_name",
                "solvent_name",
                "solute_smiles",
                "solvent_smiles",
                "n_high",
                "mae_tgnn",
                "mae_direct",
                "mae_vant_hoff",
                "bias_tgnn",
                "delta_tgnn_direct",
                "min_true",
                "slope_error_tgnn",
            ]
        ],
        on="pair_key",
        how="left",
    )
    selected = selected.merge(
        required_activity[
            ["pair_key", "required_activity_mean", "required_activity_abs_mean"]
        ],
        on="pair_key",
        how="left",
    )
    return selected


def build_pair_profile_rows(
    selected_pairs: pd.DataFrame,
    train_low: pd.DataFrame,
    test_high: pd.DataFrame,
    wide: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, str | float]] = []
    for _, item in selected_pairs.iterrows():
        pair_key = item["pair_key"]
        category = item["category"]
        low = train_low[train_low["pair_key"] == pair_key].sort_values("temperature")
        high = test_high[test_high["pair_key"] == pair_key].sort_values("temperature")
        high_pred = wide[wide["pair_key"] == pair_key].sort_values("T")
        for _, row in low.iterrows():
            rows.append(
                {
                    "category": category,
                    "pair_key": pair_key,
                    "stage": "low_observed",
                    "T": row["temperature"],
                    "ln_x2_true": row["ln_x2"],
                    "solute_name": row.get("solute_name", ""),
                    "solvent_name": row.get("solvent_name", ""),
                }
            )
        merged = high[
            ["pair_key", "temperature", "ln_x2", "solute_name", "solvent_name"]
        ].merge(
            high_pred[
                [
                    "pair_key",
                    "T",
                    "ln_x2_true",
                    "pair_vant_hoff",
                    "directgnn_proxy_ep10",
                    "tgnn_proxy_p1_8_1",
                ]
            ],
            left_on=["pair_key", "temperature"],
            right_on=["pair_key", "T"],
            how="left",
        )
        for _, row in merged.iterrows():
            rows.append(
                {
                    "category": category,
                    "pair_key": pair_key,
                    "stage": "high_profile",
                    "T": row["temperature"],
                    "ln_x2_true": row["ln_x2"],
                    "solute_name": row.get("solute_name", ""),
                    "solvent_name": row.get("solvent_name", ""),
                    "pair_vant_hoff": row.get("pair_vant_hoff"),
                    "directgnn_proxy_ep10": row.get("directgnn_proxy_ep10"),
                    "tgnn_proxy_p1_8_1": row.get("tgnn_proxy_p1_8_1"),
                }
            )
    return pd.DataFrame(rows)


def fixed_point_ln_x2(
    T: float,
    T_m: float,
    dH_fus: float,
    tau_12: float,
    tau_21: float,
    alpha: float,
    damping: float = 0.7,
    n_iter: int = 30,
) -> float:
    phi = (dH_fus / R) * (1.0 / T - 1.0 / T_m)
    x2 = float(np.clip(np.exp(-phi), 1e-12, 1 - 1e-12))
    for _ in range(n_iter):
        x1 = 1.0 - x2
        G12 = np.exp(-alpha * tau_12)
        G21 = np.exp(-alpha * tau_21)
        term1 = tau_12 * (G12 / (x2 + x1 * G12)) ** 2
        term2 = tau_21 * G21 / (x1 + x2 * G21) ** 2
        ln_gamma = x1**2 * (term1 + term2)
        x2_new = np.exp(-phi - ln_gamma)
        x2_new = damping * x2_new + (1.0 - damping) * x2
        x2_new = float(np.clip(x2_new, 1e-12, 1 - 1e-12))
        if abs(x2_new - x2) < 1e-10:
            x2 = x2_new
            break
        x2 = x2_new
    return float(np.log(x2))


def build_degeneracy_scan(
    example_pairs: pd.DataFrame,
    train_low: pd.DataFrame,
    proxy: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float | str | int]]:
    pair_key = str(example_pairs.iloc[0]["pair_key"])
    low = train_low[train_low["pair_key"] == pair_key].sort_values("temperature").copy()
    proxy_pair = proxy[proxy["pair_key"] == pair_key].copy()
    if low.empty or proxy_pair.empty:
        return pd.DataFrame(), {}

    T_obs = low["temperature"].to_numpy(dtype=float)
    y_obs = low["ln_x2"].to_numpy(dtype=float)
    ref_Tm = float(proxy_pair["T_m_solver"].mean())
    ref_dH = float(proxy_pair["dH_fus_solver"].mean())
    ref_tau12 = float(proxy_pair["tau_12_pred"].mean())
    ref_tau21 = float(proxy_pair["tau_21_pred"].mean())
    ref_alpha = float(proxy_pair["alpha_pred"].mean())

    tm_offsets = np.linspace(-80.0, 80.0, 13)
    dh_scales = np.linspace(0.70, 1.30, 11)
    tau12_values = np.linspace(ref_tau12 - 3.0, ref_tau12 + 3.0, 21)
    tau21_values = np.linspace(ref_tau21 - 3.0, ref_tau21 + 3.0, 21)

    compatible: list[dict[str, float]] = []
    tolerance_used = None
    grid_size = len(tm_offsets) * len(dh_scales) * len(tau12_values) * len(tau21_values)
    for tolerance in (0.15, 0.20, 0.25, 0.30):
        compatible.clear()
        for d_tm in tm_offsets:
            T_m = ref_Tm + d_tm
            for dh_scale in dh_scales:
                dH = ref_dH * dh_scale
                for tau_12 in tau12_values:
                    for tau_21 in tau21_values:
                        preds = np.array(
                            [
                                fixed_point_ln_x2(T, T_m, dH, tau_12, tau_21, ref_alpha)
                                for T in T_obs
                            ],
                            dtype=float,
                        )
                        abs_err = np.abs(preds - y_obs)
                        max_err = float(abs_err.max())
                        if max_err <= tolerance:
                            compatible.append(
                                {
                                    "pair_key": pair_key,
                                    "dT_m": d_tm,
                                    "T_m": T_m,
                                    "dH_scale": dh_scale,
                                    "dH_fus": dH,
                                    "tau_12": tau_12,
                                    "tau_21": tau_21,
                                    "alpha": ref_alpha,
                                    "max_abs_error": max_err,
                                    "mean_abs_error": float(abs_err.mean()),
                                }
                            )
        if len(compatible) >= 40:
            tolerance_used = tolerance
            break
    if tolerance_used is None:
        tolerance_used = tolerance

    meta = {
        "pair_key": pair_key,
        "solute_name": str(low["solute_name"].iloc[0]),
        "solvent_name": str(low["solvent_name"].iloc[0]),
        "n_low_points": int(len(low)),
        "reference_T_m": ref_Tm,
        "reference_dH_fus": ref_dH,
        "reference_tau_12": ref_tau12,
        "reference_tau_21": ref_tau21,
        "reference_alpha": ref_alpha,
        "grid_size": int(grid_size),
        "tolerance_used": float(tolerance_used),
        "n_compatible": int(len(compatible)),
    }
    return pd.DataFrame(compatible), meta


def main() -> None:
    args = parse_args()
    paths = Paths(
        combined_predictions=Path(args.combined_predictions),
        train_low=Path(args.train_low),
        test_high=Path(args.test_high),
        example_pairs=Path(args.example_pairs),
        tgnn_proxy_intermediates=Path(args.tgnn_proxy_intermediates),
        output_dir=Path(args.output_dir),
    )
    ensure_dir(paths.output_dir)
    data = load_inputs(paths)
    meta = build_pair_metadata(data["train_low"], data["test_high"], data["proxy"])
    wide = build_wide_predictions(data["combined"], meta)
    pair_metrics = build_pair_metrics(wide)
    required_activity = build_required_activity(data["proxy"])
    slope_level_pairs = build_slope_level_pairs(pair_metrics, required_activity)
    selected_pairs = select_representative_pairs(pair_metrics, slope_level_pairs, required_activity)
    pair_profiles = build_pair_profile_rows(selected_pairs, data["train_low"], data["test_high"], wide)
    degeneracy_scan, degeneracy_meta = build_degeneracy_scan(
        data["example_pairs"], data["train_low"], data["proxy"]
    )

    wide.to_csv(paths.output_dir / "wide_predictions.csv", index=False)
    pair_metrics.to_csv(paths.output_dir / "pair_metrics.csv", index=False)
    required_activity.to_csv(paths.output_dir / "required_activity_summary.csv", index=False)
    slope_level_pairs.to_csv(paths.output_dir / "slope_level_pairs.csv", index=False)
    selected_pairs.to_csv(paths.output_dir / "selected_pairs.csv", index=False)
    pair_profiles.to_csv(paths.output_dir / "pair_profiles.csv", index=False)
    degeneracy_scan.to_csv(paths.output_dir / "degeneracy_scan.csv", index=False)

    summary = {
        "n_rows_high": int(len(wide)),
        "n_pairs_high": int(wide["pair_key"].nunique()),
        "selected_pair_categories": selected_pairs[["category", "pair_key", "solute_name", "solvent_name"]].to_dict(
            orient="records"
        )
        if not selected_pairs.empty
        else [],
        "degeneracy": degeneracy_meta,
    }
    (paths.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
