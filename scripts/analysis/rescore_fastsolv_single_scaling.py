#!/usr/bin/env python3
r"""Re-score the two FastSolv retraining runs through a correctly scaled prediction path.

WHY THIS EXISTS
---------------
`scripts/run_fastsolv.py::_predict_with_model` standardises the model's inputs with
the checkpoint's own buffers and then calls `trainer.predict`, whose
`fastsolv._classes._fastsolv.predict_step` standardises the same tensors again.  The
network's sigmoid input activation annihilates the twice-scaled temperature, so the
deposited predictions in

    results/external_baselines/{solute,pair_random}/fastsolv_contract_v2/test/

are exactly constant in temperature.  The training and validation steps do not
re-scale, so the fitted checkpoint is sound and the defect is confined to inference:
feeding the RAW features to the dataset and letting `predict_step` scale them once
reproduces the condition the network was trained under.

This script re-runs inference on the two saved checkpoints, both ways, and writes a
corrected bundle beside the defective one.  Nothing is retrained.  The doubly-scaled
arm is re-run too, as a control: it must reproduce the deposited metrics, which is
what establishes that the only thing this script changes is the scaling.

REPRODUCE
---------
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python \
        scripts/analysis/rescore_fastsolv_single_scaling.py

Writes results/external_baselines/{solute,pair_random}/fastsolv_contract_v2_singlescale/
(a full benchmark bundle: report, per-row predictions, summary) and
results/external_baselines/fastsolv_rescore_summary.json.  Edits no .tex in paper/.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("FASTPROP_SKIP_MAPE", "1")

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for extra in (REPO / "src", REPO / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

EXT = REPO / "results/external_baselines"

# Each family: the three split files the deposited run was trained/scored on (from the
# run's own metrics.json), and the checkpoint that run selected.
FAMILIES = {
    "solute": {
        "train": REPO / "notebooks/data/processed/train_solute.csv",
        "val": REPO / "notebooks/data/processed/val_solute.csv",
        "test": REPO / "notebooks/data/processed/test_solute.csv",
        "checkpoint": EXT / "solute/fastsolv_contract_v2/checkpoints/epoch=8-step=2970.ckpt",
        "deposited": EXT / "solute/fastsolv_contract_v2",
        "out": EXT / "solute/fastsolv_contract_v2_singlescale",
    },
    "pair_random": {
        "train": REPO / "results/metric_diagnosis_bundle/train_pair_random.csv",
        "val": REPO / "results/metric_diagnosis_bundle/val_pair_random.csv",
        "test": REPO / "results/metric_diagnosis_bundle/test_pair_random.csv",
        "checkpoint": EXT / "pair_random/fastsolv_contract_v2/checkpoints/epoch=29-step=9900.ckpt",
        "deposited": EXT / "pair_random/fastsolv_contract_v2",
        "out": EXT / "pair_random/fastsolv_contract_v2_singlescale",
    },
}


def _load_runner():
    """Import scripts/run_fastsolv.py as a module, reusing its data path verbatim."""
    spec = importlib.util.spec_from_file_location(
        "run_fastsolv_module", REPO / "scripts/run_fastsolv.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROW_KEY = ["solute_smiles", "solvent_smiles", "temperature", "ln_x2"]


def _row_keys(df: pd.DataFrame) -> pd.Series:
    return (
        df[ROW_KEY].round({"temperature": 6, "ln_x2": 9}).astype(str).agg("|".join, axis=1)
    )


def _prepare(runner, paths: dict, *, cache: Path | None) -> tuple[pd.DataFrame, dict]:
    """Reproduce run_train's data preparation, and return the scored test frame."""
    from tgnn_solv.external_benchmarking import logS_from_ln_x2

    frames = {}
    for name in ("train", "val", "test"):
        df = runner._clean_df(pd.read_csv(paths[name], low_memory=False), require_targets=True)
        df["logS"] = logS_from_ln_x2(df)
        df, _diag = runner._filter_finite_logS_rows(df, split_name=name)
        df["dlogS_dT"] = 0.0
        frames[name] = df

    unique_smiles = np.unique(
        np.hstack(
            [
                frames[n][col].unique()
                for n in ("train", "val", "test")
                for col in ("solute_smiles", "solvent_smiles")
            ]
        )
    )
    if cache is not None and cache.exists():
        blob = np.load(cache, allow_pickle=True)
        cached_smiles = list(blob["smiles"])
        if cached_smiles == list(unique_smiles):
            values = blob["values"]
            desc_map = {str(s): values[i] for i, s in enumerate(cached_smiles)}
            diagnostics = json.loads(str(blob["diagnostics"]))
            print(f"    descriptors read from cache {cache}", flush=True)
            return frames["test"], {"desc_map": desc_map, "descriptor_diagnostics": diagnostics}
    desc_map, diagnostics = runner._compute_descriptors(unique_smiles, descriptor_nproc=1)
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            cache,
            smiles=np.asarray(list(unique_smiles), dtype=object),
            values=np.stack([desc_map[str(s)] for s in unique_smiles]),
            diagnostics=json.dumps(diagnostics),
        )
    return frames["test"], {"desc_map": desc_map, "descriptor_diagnostics": diagnostics}


def _predict_single_scaled(runner, model, sol, slv, temp, *, batch_size: int = 256):
    """Feed RAW features; `predict_step` applies the one scaling the model was trained on."""
    import torch

    runner._load_fastsolv_runtime()
    dataset = runner.SolubilityDataset(
        torch.tensor(sol, dtype=torch.float32),
        torch.tensor(slv, dtype=torch.float32),
        torch.tensor(temp, dtype=torch.float32),
        torch.zeros(len(sol), dtype=torch.float32),
        torch.zeros(len(sol), dtype=torch.float32),
    )
    loader = runner.fastpropDataLoader(
        dataset, batch_size=batch_size, shuffle=False, num_workers=0, persistent_workers=False
    )
    trainer = runner.Trainer(logger=False, enable_checkpointing=False, accelerator="cpu", devices=1)
    with torch.inference_mode():
        preds = trainer.predict(model, loader)
    return torch.vstack(preds).cpu().numpy().reshape(-1)


def _temperature_response(df: pd.DataFrame, pred_col: str, *, min_span_K: float = 5.0) -> dict:
    """Per-(solute, solvent) pair spread of the prediction over the pair's temperatures."""
    spans_pred, spans_true, spans_T = [], [], []
    for _key, idx in df.groupby(["solute_smiles", "solvent_smiles"]).indices.items():
        T = df["temperature"].to_numpy(dtype=float)[idx]
        if float(T.max() - T.min()) <= min_span_K:
            continue
        p = df[pred_col].to_numpy(dtype=float)[idx]
        t = df["logS"].to_numpy(dtype=float)[idx]
        spans_pred.append(float(p.max() - p.min()))
        spans_true.append(float(t.max() - t.min()))
        spans_T.append(float(T.max() - T.min()))
    if not spans_pred:
        return {"n_pairs_spanning": 0}
    return {
        "n_pairs_spanning": int(len(spans_pred)),
        "min_span_K": float(min_span_K),
        "median_pred_span_log10S": float(np.median(spans_pred)),
        "max_pred_span_log10S": float(np.max(spans_pred)),
        "median_true_span_log10S": float(np.median(spans_true)),
        "median_T_span_K": float(np.median(spans_T)),
        "n_pairs_pred_span_below_1e-6": int(sum(s < 1e-6 for s in spans_pred)),
    }


def run_family(runner, name: str, paths: dict, *, batch_size: int, cache: Path | None) -> dict:
    print(f"\n=== {name}: preparing splits and descriptors", flush=True)
    test_df, prep = _prepare(runner, paths, cache=cache)
    print(f"    test rows {len(test_df)}, unique SMILES {prep['descriptor_diagnostics']['n_smiles']}",
          flush=True)

    # The deposited run's own row set.  `prepare_pair_dataframe` and the solvent-molarity
    # table have both moved since that run, so the current preparation keeps rows the
    # deposit does not; the deposited rows are a strict subset.  The row this table prints
    # is scored on the deposited set, which is the set the block's other rows use, and the
    # wider current set is reported beside it.
    dep_pred = pd.read_csv(paths["deposited"] / "test/predictions.csv", low_memory=False)
    dep_keys = set(_row_keys(dep_pred))
    in_deposit = _row_keys(test_df).isin(dep_keys)
    row_sets = {
        "deposited_row_set": test_df.loc[in_deposit].reset_index(drop=True),
        "current_row_set": test_df,
    }
    print(f"    deposited row set {int(in_deposit.sum())} of {len(dep_pred)} deposited rows; "
          f"current preparation keeps {len(test_df)}", flush=True)

    model = runner._load_fastsolv_models_from_checkpoint(str(paths["checkpoint"]))[0]

    out = {}
    for row_set_name, frame in row_sets.items():
        sol, slv, temp = runner._assemble_features(frame, prep["desc_map"])
        print(f"    [{row_set_name}] forward pass, deposited (doubly scaled) path", flush=True)
        pred_double = runner._predict_with_model(model, sol, slv, temp, batch_size=batch_size)
        print(f"    [{row_set_name}] forward pass, corrected (singly scaled) path", flush=True)
        pred_single = _predict_single_scaled(runner, model, sol, slv, temp, batch_size=batch_size)

        for arm, pred in (("double_scaled_control", pred_double), ("single_scaled", pred_single)):
            artifacts = runner._evaluate_prediction_bundle(
                model_name="fastsolv",
                split_name="test",
                split_df=frame,
                pred_logS=pred,
                split_mode=name,
                test_data=str(paths["test"].relative_to(REPO)),
                metadata={
                    "checkpoint": str(paths["checkpoint"].relative_to(REPO)),
                    "target_space": "logS",
                    "scaling_path": arm,
                    "row_set": row_set_name,
                    "descriptor_diagnostics": prep["descriptor_diagnostics"],
                },
            )
            row = artifacts.summary.iloc[0]
            record = {
                "n": int(row["n_samples"]),
                "mae_ln_x2": float(row["mae"]),
                "rmse_ln_x2": float(row["rmse"]),
                "r2_ln_x2": float(row["r2"]),
                "n_logS": int(row["n_samples_logS_finite_subset"]),
                "mae_logS": float(row["mae_logS_finite_subset"]),
                "rmse_logS": float(row["rmse_logS_finite_subset"]),
                "r2_logS": float(row["r2_logS_finite_subset"]),
            }
            scored = frame.copy().reset_index(drop=True)
            scored["pred_logS"] = np.asarray(pred, dtype=float)
            record["temperature_response"] = _temperature_response(scored, "pred_logS")
            record["mean_logS_error"] = float(
                np.mean(
                    scored["pred_logS"].to_numpy(dtype=float)
                    - scored["logS"].to_numpy(dtype=float)
                )
            )
            out[f"{row_set_name}/{arm}"] = record
            if arm == "single_scaled" and row_set_name == "deposited_row_set":
                runner.write_benchmark_artifacts(paths["out"] / "test", artifacts)
                (paths["out"] / "summary.csv").write_text(
                    artifacts.summary.to_csv(index=False), encoding="utf-8"
                )
            print(f"      {arm}: n {record['n']}  MAE ln x2 {record['mae_ln_x2']:.4f}  "
                  f"RMSE log10S {record['rmse_logS']:.4f}  R2 {record['r2_ln_x2']:.4f}  "
                  f"median pred span "
                  f"{record['temperature_response'].get('median_pred_span_log10S')}",
                  flush=True)

    dep = pd.read_csv(paths["deposited"] / "summary.csv")
    dep = dep[(dep["split"] == "test") & (dep["model"] == "fastsolv")].iloc[0]
    out["deposited_on_disk"] = {
        "n": int(dep["n_samples"]),
        "mae_ln_x2": float(dep["mae"]),
        "rmse_ln_x2": float(dep["rmse"]),
        "r2_ln_x2": float(dep["r2"]),
        "n_logS": int(dep["n_samples_logS_finite_subset"]),
        "mae_logS": float(dep["mae_logS_finite_subset"]),
        "rmse_logS": float(dep["rmse_logS_finite_subset"]),
        "r2_logS": float(dep["r2_logS_finite_subset"]),
    }
    ctrl = out["deposited_row_set/double_scaled_control"]
    out["control_reproduces_deposit"] = bool(
        ctrl["n"] == out["deposited_on_disk"]["n"]
        and abs(ctrl["mae_ln_x2"] - out["deposited_on_disk"]["mae_ln_x2"]) < 1e-4
        and abs(ctrl["rmse_logS"] - out["deposited_on_disk"]["rmse_logS"]) < 1e-4
    )
    print(f"    control reproduces the deposit: {out['control_reproduces_deposit']}", flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--families", nargs="*", default=list(FAMILIES))
    ap.add_argument("--descriptor-cache", default=None,
                    help="optional .npz path; descriptors are read from it when the SMILES "
                         "set matches and written to it otherwise")
    args = ap.parse_args()

    runner = _load_runner()
    runner._load_fastsolv_runtime(descriptor_nproc=1)

    summary = {}
    for name in args.families:
        cache = Path(args.descriptor_cache).with_suffix(f".{name}.npz") if args.descriptor_cache else None
        summary[name] = run_family(
            runner, name, FAMILIES[name], batch_size=int(args.batch_size), cache=cache
        )

    EXT.mkdir(parents=True, exist_ok=True)
    (EXT / "fastsolv_rescore_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print("\nwrote results/external_baselines/fastsolv_rescore_summary.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
