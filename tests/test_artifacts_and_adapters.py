from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tgnn_solv.benchmark_adapters import run_adapter_benchmark
from tgnn_solv.baselines.direct_gnn import DirectGNN
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.external_benchmarking import build_benchmark_artifacts, write_benchmark_artifacts
from tgnn_solv.uncertainty import EnsemblePredictor, MCDropoutPredictor


def _toy_eval_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "row_index": 0,
                "solute_smiles": "CCO",
                "solvent_smiles": "O",
                "temperature": 298.15,
                "ln_x2": -2.0,
                "has_solubility": True,
            },
            {
                "row_index": 1,
                "solute_smiles": "CC(=O)O",
                "solvent_smiles": "CCO",
                "temperature": 310.0,
                "ln_x2": -3.1,
                "has_solubility": True,
            },
        ]
    )


def test_write_benchmark_artifacts_emits_sidecars(tmp_path: Path) -> None:
    eval_df = _toy_eval_df()
    artifacts = build_benchmark_artifacts(
        model_name="toy_model",
        eval_df=eval_df,
        pred_ln_x2=eval_df["ln_x2"].to_numpy(),
        metadata={"model_family": "custom"},
        split_mode="solute_scaffold",
        test_data="dummy_test.csv",
    )
    write_benchmark_artifacts(tmp_path, artifacts, input_paths={"test_data": __file__})

    manifest_path = tmp_path / "run_manifest.json"
    card_path = tmp_path / "benchmark_card.json"
    assert manifest_path.exists()
    assert card_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    card = json.loads(card_path.read_text(encoding="utf-8"))
    assert manifest["run_type"] == "benchmark_bundle"
    assert card["card_type"] == "benchmark_card"
    assert card["model"]["family"] == "custom"


def test_direct_gnn_uncertainty_predictors_work() -> None:
    cfg = TGNNSolvConfig(
        hidden_dim=32,
        n_gnn_layers=2,
        n_cross_attn_layers=1,
        dropout=0.2,
    )
    model_a = DirectGNN(cfg=cfg)
    model_b = DirectGNN(cfg=cfg)

    mc = MCDropoutPredictor(model_a, n_samples=3)
    mc_result = mc.predict("CCO", "O", T=298.15)
    assert mc_result["model_family"] == "direct_gnn"
    assert "ln_x2_mean" in mc_result
    assert "gamma_2_mean" not in mc_result

    ensemble = EnsemblePredictor([model_a, model_b])
    ensemble_result = ensemble.predict("CCO", "O", T=298.15)
    assert ensemble_result["model_family"] == "direct_gnn"
    assert "ln_x2_std" in ensemble_result
    assert "T_m_mean" not in ensemble_result


def test_run_adapter_benchmark_end_to_end(tmp_path: Path, monkeypatch) -> None:
    adapter_module = tmp_path / "toy_adapter_module.py"
    adapter_module.write_text(
        """
from tgnn_solv.benchmark_adapters import BaseBenchmarkAdapter

class ToyAdapter(BaseBenchmarkAdapter):
    def describe(self):
        return {
            "adapter_name": "ToyAdapter",
            "model_family": "custom_adapter",
            "model_name": "toy_adapter",
        }

    def predict_frame(self, df):
        out = df[["row_index", "solute_smiles", "solvent_smiles", "temperature"]].copy()
        out["ln_x2_pred"] = df["ln_x2"].astype(float)
        return out
        """,
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    test_csv = tmp_path / "test.csv"
    _toy_eval_df().to_csv(test_csv, index=False)
    out_dir = tmp_path / "adapter_bundle"

    artifacts = run_adapter_benchmark(
        adapter_ref="toy_adapter_module:ToyAdapter",
        test_data=test_csv,
        out_dir=out_dir,
    )

    assert artifacts.report["overall"]["mae"] == 0.0
    assert (out_dir / "report.json").exists()
    assert (out_dir / "summary.csv").exists()
    assert (out_dir / "benchmark_card.json").exists()
    assert (out_dir / "adapter_description.json").exists()
