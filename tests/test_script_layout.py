from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PY_WRAPPERS = {
    "scripts/data/prepare_data.py": "scripts/prepare_data.py",
    "scripts/training/train.py": "scripts/train.py",
    "scripts/training/train_with_pretrain.py": "scripts/train_with_pretrain.py",
    "scripts/training/train_directgnn.py": "scripts/train_directgnn.py",
    "scripts/training/diagnose_training.py": "scripts/diagnose_training.py",
    "scripts/evaluation/evaluate_complete.py": "scripts/evaluate_complete.py",
    "scripts/evaluation/benchmark_tgnn_solv.py": "scripts/benchmark_tgnn_solv.py",
    "scripts/evaluation/validate_physics.py": "scripts/validate_physics.py",
    "scripts/evaluation/analyze_benchmark.py": "scripts/analyze_benchmark.py",
    "scripts/evaluation/compare_models.py": "scripts/compare_models.py",
    "scripts/evaluation/error_analysis.py": "scripts/error_analysis.py",
    "scripts/experiments/run_seeds.py": "scripts/run_seeds.py",
    "scripts/experiments/run_ablation.py": "scripts/run_ablation.py",
    "scripts/experiments/run_split_comparisons.py": "scripts/run_split_comparisons.py",
    "scripts/experiments/run_full_budget_experiment.py": "scripts/run_full_budget_experiment.py",
    "scripts/experiments/run_medium_budget_comparison.py": "scripts/run_medium_budget_comparison.py",
    "scripts/experiments/run_optuna.py": "scripts/run_optuna.py",
    "scripts/experiments/learning_curves.py": "scripts/learning_curves.py",
    "scripts/experiments/temperature_extrapolation.py": "scripts/temperature_extrapolation.py",
    "scripts/experiments/statistical_tests.py": "scripts/statistical_tests.py",
    "scripts/experiments/generate_paper_figures.py": "scripts/generate_paper_figures.py",
    "scripts/experiments/generate_supplementary.py": "scripts/generate_supplementary.py",
    "scripts/external/run_fastsolv.py": "scripts/run_fastsolv.py",
    "scripts/external/compare_fastsolv_tgnn.py": "scripts/compare_fastsolv_tgnn.py",
    "scripts/external/run_solprop.py": "scripts/run_solprop.py",
}

SH_WRAPPERS = {
    "scripts/training/run_resume_safe_train.sh": "scripts/run_resume_safe_train.sh",
}

GROUPED_ENTRY_POINTS = {
    "scripts/evaluation/benchmark_adapter_model.py",
    "scripts/evaluation/run_thermo_stress_suite.py",
    "scripts/experiments/build_benchmark_release.py",
}

TOP_LEVEL_COMPAT_WRAPPERS = {
    "scripts/benchmark_adapter_model.py": "scripts/evaluation/benchmark_adapter_model.py",
    "scripts/run_thermo_stress_suite.py": "scripts/evaluation/run_thermo_stress_suite.py",
    "scripts/build_benchmark_release.py": "scripts/experiments/build_benchmark_release.py",
}


def test_scripts_readme_exists() -> None:
    readme_path = ROOT / "scripts/README.md"
    assert readme_path.is_file()
    text = readme_path.read_text(encoding="utf-8")
    assert "Scripts Layout" in text
    assert "Legacy top-level paths remain supported" in text


def test_python_wrappers_delegate_to_legacy_entry_points() -> None:
    for wrapper_rel, legacy_rel in PY_WRAPPERS.items():
        wrapper_path = ROOT / wrapper_rel
        legacy_path = ROOT / legacy_rel

        assert wrapper_path.is_file(), wrapper_rel
        assert legacy_path.is_file(), legacy_rel

        text = wrapper_path.read_text(encoding="utf-8")
        assert "runpy.run_path" in text
        assert legacy_path.name in text


def test_grouped_entry_points_exist_as_real_scripts() -> None:
    for script_rel in GROUPED_ENTRY_POINTS:
        script_path = ROOT / script_rel
        assert script_path.is_file(), script_rel
        text = script_path.read_text(encoding="utf-8")
        assert "def main()" in text
        assert "runpy.run_path" not in text


def test_top_level_compat_wrappers_delegate_to_grouped_entry_points() -> None:
    for wrapper_rel, grouped_rel in TOP_LEVEL_COMPAT_WRAPPERS.items():
        wrapper_path = ROOT / wrapper_rel
        grouped_path = ROOT / grouped_rel

        assert wrapper_path.is_file(), wrapper_rel
        assert grouped_path.is_file(), grouped_rel

        text = wrapper_path.read_text(encoding="utf-8")
        assert "runpy.run_path" in text
        assert grouped_path.name in text


def test_shell_wrappers_delegate_to_legacy_entry_points() -> None:
    for wrapper_rel, legacy_rel in SH_WRAPPERS.items():
        wrapper_path = ROOT / wrapper_rel
        legacy_path = ROOT / legacy_rel

        assert wrapper_path.is_file(), wrapper_rel
        assert legacy_path.is_file(), legacy_rel

        text = wrapper_path.read_text(encoding="utf-8")
        assert legacy_path.name in text
        assert "exec bash" in text
