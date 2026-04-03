from tgnn_solv.ablation import run_ablation_study as legacy_run_ablation_study
from tgnn_solv.baselines.direct_gnn import DirectGNN as LegacyDirectGNN
from tgnn_solv.config import TGNNSolvConfig as LegacyConfig
from tgnn_solv.evaluate import Evaluator as LegacyEvaluator
from tgnn_solv.features import compute_molecular_descriptors as legacy_compute_descriptors
from tgnn_solv.group_contribution import compute_gc_priors as legacy_compute_gc_priors
from tgnn_solv.heads import FusionHead as LegacyFusionHead
from tgnn_solv.inference import load_model as legacy_load_model
from tgnn_solv.loss import TGNNSolvLoss as LegacyLoss
from tgnn_solv.model import TGNNSolv as LegacyTGNNSolv
from tgnn_solv.optuna_tuner import OptunaTuner as LegacyOptunaTuner
from tgnn_solv.pretrain import Pretrainer as LegacyPretrainer
from tgnn_solv.seed import set_seed as legacy_set_seed
from tgnn_solv.solver import SLESolver as LegacySLESolver
from tgnn_solv.trainer import TGNNSolvTrainer as LegacyTrainer

from tgnn_solv.chemistry.features import compute_molecular_descriptors
from tgnn_solv.chemistry.group_contribution import compute_gc_priors
from tgnn_solv.core.config import TGNNSolvConfig
from tgnn_solv.core.seed import set_seed
from tgnn_solv.evaluation.evaluator import Evaluator
from tgnn_solv.evaluation.inference import load_model
from tgnn_solv.models.direct_gnn import DirectGNN
from tgnn_solv.models.heads import FusionHead
from tgnn_solv.models.tgnn import TGNNSolv
from tgnn_solv.physics.solver import SLESolver
from tgnn_solv.research.ablation import run_ablation_study
from tgnn_solv.training.losses import TGNNSolvLoss
from tgnn_solv.training.pretrain import Pretrainer
from tgnn_solv.training.trainer import TGNNSolvTrainer
from tgnn_solv.training.tuner import OptunaTuner


def test_grouped_package_readme_exists() -> None:
    import pathlib

    readme_path = pathlib.Path(__file__).resolve().parents[1] / "src" / "tgnn_solv" / "README.md"
    assert readme_path.is_file()
    text = readme_path.read_text(encoding="utf-8")
    assert "Internal Package Layout" in text
    assert "legacy flat modules" in text


def test_grouped_namespace_exports_match_legacy_symbols() -> None:
    assert TGNNSolv is LegacyTGNNSolv
    assert DirectGNN is LegacyDirectGNN
    assert FusionHead is LegacyFusionHead
    assert SLESolver is LegacySLESolver
    assert TGNNSolvTrainer is LegacyTrainer
    assert TGNNSolvLoss is LegacyLoss
    assert Pretrainer is LegacyPretrainer
    assert OptunaTuner is LegacyOptunaTuner
    assert TGNNSolvConfig is LegacyConfig
    assert Evaluator is LegacyEvaluator
    assert load_model is legacy_load_model
    assert set_seed is legacy_set_seed
    assert compute_molecular_descriptors is legacy_compute_descriptors
    assert compute_gc_priors is legacy_compute_gc_priors
    assert run_ablation_study is legacy_run_ablation_study
