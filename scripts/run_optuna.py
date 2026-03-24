#!/usr/bin/env python
"""
Run Optuna hyperparameter tuning for TGNN-Solv models and baselines.
"""

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
import torch

from tgnn_solv.optuna_tuner import AVAILABLE_MODELS, OptunaTuner


def _parse_models(args: argparse.Namespace) -> list[str]:
    if args.all_models:
        return list(AVAILABLE_MODELS)
    if args.models:
        models = []
        for item in args.models:
            models.extend([m.strip() for m in item.split(",") if m.strip()])
        return models
    return ["tgnn_solv"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Optuna tuning for TGNN-Solv and baselines."
    )
    parser.add_argument(
        "--train-csv",
        default="notebooks/data/processed/train.csv",
        help="Path to train CSV",
    )
    parser.add_argument(
        "--val-csv",
        default="notebooks/data/processed/val.csv",
        help="Path to val CSV",
    )
    parser.add_argument(
        "--test-csv",
        default="notebooks/data/processed/test.csv",
        help="Path to test CSV",
    )
    parser.add_argument(
        "--models",
        action="append",
        help="Comma-separated model list (repeatable).",
    )
    parser.add_argument(
        "--all-models",
        action="store_true",
        help="Tune all available models.",
    )
    parser.add_argument("--n-trials", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default=None)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Fix batch size (skip tuning).",
    )
    parser.add_argument(
        "--no-tune-arch",
        action="store_true",
        help="Disable architecture tuning.",
    )
    parser.add_argument("--epochs-phase1", type=int, default=None)
    parser.add_argument("--epochs-phase2", type=int, default=None)
    parser.add_argument("--epochs-phase3", type=int, default=None)
    parser.add_argument("--patience", type=int, default=None)
    parser.add_argument("--warmup-epochs", type=int, default=None)
    parser.add_argument("--baseline-epochs", type=int, default=200)
    parser.add_argument("--baseline-patience", type=int, default=20)
    parser.add_argument("--storage", default=None)
    parser.add_argument("--study-name", default=None)
    parser.add_argument("--out-dir", default=None)

    args = parser.parse_args()
    models = _parse_models(args)

    device = torch.device(
        args.device if args.device else ("cuda" if torch.cuda.is_available() else "cpu")
    )

    overrides = {
        "epochs_phase1": args.epochs_phase1,
        "epochs_phase2": args.epochs_phase2,
        "epochs_phase3": args.epochs_phase3,
        "patience": args.patience,
        "warmup_epochs": args.warmup_epochs,
    }

    train_df, val_df, test_df = OptunaTuner.load_csv_splits(
        args.train_csv, args.val_csv, args.test_csv
    )
    datasets = OptunaTuner.build_datasets(
        train_df, val_df, test_df, cache=True
    )

    tuner = OptunaTuner(
        datasets=datasets,
        device=device,
        seed=args.seed,
        num_workers=args.num_workers,
        fixed_batch_size=args.batch_size,
        tune_arch=not args.no_tune_arch,
        cfg_overrides=overrides,
        baseline_epochs=args.baseline_epochs,
        baseline_patience=args.baseline_patience,
    )

    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for model_name in models:
        study_name = args.study_name
        if study_name:
            study_name = f"{study_name}_{model_name}"

        print("\n" + "=" * 60)
        print(f"Tuning model: {model_name}")
        print("=" * 60)

        study = tuner.run_study(
            model_name=model_name,
            n_trials=args.n_trials,
            storage=args.storage,
            study_name=study_name,
            timeout=args.timeout,
        )

        print(f"Best val MAE: {study.best_value:.4f}")
        print(f"Best params: {study.best_params}")

        if out_dir:
            best_path = out_dir / f"{model_name}_best.json"
            with best_path.open("w") as f:
                json.dump(
                    {
                        "model": model_name,
                        "best_value": study.best_value,
                        "best_params": study.best_params,
                    },
                    f,
                    indent=2,
                    sort_keys=True,
                )
            trials_path = out_dir / f"{model_name}_trials.csv"
            study.trials_dataframe().to_csv(trials_path, index=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
