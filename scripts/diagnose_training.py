#!/usr/bin/env python
"""
Quick diagnostics for data quality and overfit capability.

Usage:
  python scripts/diagnose_training.py stats
  python scripts/diagnose_training.py overfit --sample-size 1000 --epochs 200
"""

from __future__ import annotations

import argparse
import math
import random
import time
from pathlib import Path

import csv
from tgnn_solv.progress import progress, trange


def _device_from_arg(arg: str | None):
    import torch

    if arg:
        return torch.device(arg)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _parse_bool(val: str) -> bool:
    return str(val).strip().lower() in {"1", "true", "yes", "y"}


def _summary_csv(name: str, path: str) -> None:
    solutes = set()
    solvents = set()
    temps = []
    lnx2 = []
    n = 0
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n += 1
            solutes.add(row["solute_smiles"])
            solvents.add(row["solvent_smiles"])
            try:
                temps.append(float(row["temperature"]))
            except Exception:
                pass
            try:
                lnx2.append(float(row["ln_x2"]))
            except Exception:
                pass
    if temps:
        temps_sorted = sorted(temps)
        t_min = temps_sorted[0]
        t_max = temps_sorted[-1]
        t_med = temps_sorted[len(temps_sorted) // 2]
    else:
        t_min = t_med = t_max = float("nan")
    if lnx2:
        lnx2_sorted = sorted(lnx2)
        ln_min = lnx2_sorted[0]
        ln_max = lnx2_sorted[-1]
        ln_med = lnx2_sorted[len(lnx2_sorted) // 2]
    else:
        ln_min = ln_med = ln_max = float("nan")
    print(
        f"{name:5s}: n={n:,} solutes={len(solutes):,} "
        f"solvents={len(solvents):,} "
        f"T=[{t_min:.1f},{t_med:.1f},{t_max:.1f}] "
        f"lnx2=[{ln_min:.2f},{ln_med:.2f},{ln_max:.2f}]"
    )


def _dup_stats_csv(path: str) -> None:
    stats = {}
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "has_solubility" in row and not _parse_bool(
                row["has_solubility"]
            ):
                continue
            key = (
                row["solute_smiles"],
                row["solvent_smiles"],
                row["temperature"],
            )
            try:
                x = float(row["ln_x2"])
            except Exception:
                continue
            count, mean, m2 = stats.get(key, (0, 0.0, 0.0))
            count += 1
            delta = x - mean
            mean += delta / count
            delta2 = x - mean
            m2 += delta * delta2
            stats[key] = (count, mean, m2)

    dup = {k: v for k, v in stats.items() if v[0] > 1}
    if not dup:
        print("Duplicates: none")
        return
    stds = []
    for count, mean, m2 in dup.values():
        var = m2 / max(count - 1, 1)
        stds.append(math.sqrt(max(var, 0.0)))
    stds = sorted(stds)
    n = len(stds)
    med = stds[n // 2]
    p90 = stds[int(0.9 * (n - 1))]
    max_v = stds[-1]
    print(f"Duplicates: {len(dup):,} groups (count>1)")
    print(
        f"  ln_x2 std: median={med:.3f}, "
        f"p90={p90:.3f}, max={max_v:.3f}"
    )
    # Top-5
    top = sorted(
        dup.items(),
        key=lambda kv: math.sqrt(
            max(kv[1][2] / max(kv[1][0] - 1, 1), 0.0)
        ),
        reverse=True,
    )[:5]
    print("  Top-5 groups by std:")
    for (sol, slv, T), (count, mean, m2) in top:
        std = math.sqrt(max(m2 / max(count - 1, 1), 0.0))
        print(f"    {sol} | {slv} | {float(T):.2f}K -> std={std:.3f}")


def run_stats(args: argparse.Namespace) -> None:
    _summary_csv("Train", args.train_csv)
    _summary_csv("Val", args.val_csv)
    _summary_csv("Test", args.test_csv)
    _dup_stats_csv(args.train_csv)


def _make_overfit_cfg(
    interaction_mode: str,
    use_moe: bool,
    use_implicit_diff: bool,
) -> TGNNSolvConfig:
    from tgnn_solv.config import TGNNSolvConfig

    return TGNNSolvConfig(
        hidden_dim=128,
        n_gnn_layers=4,
        n_cross_attn_layers=2,
        n_attn_heads=4,
        pair_dim=256,
        dropout=0.0,
        n_iter_train=10,
        n_iter_eval=20,
        use_implicit_diff=use_implicit_diff,
        interaction_mode=interaction_mode,
        use_solvent_moe=use_moe,
    )


def run_overfit(args: argparse.Namespace) -> None:
    import torch
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, Dataset
    from torch_geometric.data import Batch

    from tgnn_solv.features import smiles_to_graph
    from tgnn_solv.model import TGNNSolv
    from tgnn_solv.data.solvent_types import solvent_type_id_from_smiles

    device = _device_from_arg(args.device)
    print(f"Device: {device}")

    rows = []
    with open(args.train_csv, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "has_solubility" in row and not _parse_bool(
                row["has_solubility"]
            ):
                continue
            row = {
                "solute_smiles": row["solute_smiles"],
                "solvent_smiles": row["solvent_smiles"],
                "temperature": row["temperature"],
                "ln_x2": row["ln_x2"],
            }
            row["solvent_type"] = solvent_type_id_from_smiles(
                row["solvent_smiles"]
            )
            rows.append(row)

    if len(rows) == 0:
        raise ValueError("No solubility rows found in train CSV.")

    rng = random.Random(args.seed)
    sample_size = min(args.sample_size, len(rows))
    subset_rows = rng.sample(rows, k=sample_size)

    cfg = _make_overfit_cfg(
        interaction_mode=args.interaction_mode,
        use_moe=args.use_moe,
        use_implicit_diff=args.use_implicit_diff,
    )

    model = TGNNSolv(cfg=cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.0)

    class _CsvDataset(Dataset):
        def __init__(self, rows, cache=True):
            self.rows = rows
            self.cache = {} if cache else None

        def _graph(self, smi: str):
            if self.cache is not None and smi in self.cache:
                return self.cache[smi]
            g = smiles_to_graph(smi)
            if self.cache is not None and g is not None:
                self.cache[smi] = g
            return g

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, idx):
            r = self.rows[idx]
            sol_g = self._graph(r["solute_smiles"]).clone()
            slv_g = self._graph(r["solvent_smiles"]).clone()
            t = {
                "T": torch.tensor(float(r["temperature"]), dtype=torch.float),
                "ln_x2": torch.tensor(float(r["ln_x2"]), dtype=torch.float),
                "has_solubility": torch.tensor(True, dtype=torch.bool),
                "solvent_type": torch.tensor(
                    int(r["solvent_type"]), dtype=torch.long
                ),
            }
            return sol_g, slv_g, t

    def _collate_min(batch):
        sol_gs, slv_gs, tgts = zip(*batch)
        sol_batch = Batch.from_data_list(list(sol_gs))
        slv_batch = Batch.from_data_list(list(slv_gs))
        t_batch = {}
        for key in tgts[0]:
            t_batch[key] = torch.stack([t[key] for t in tgts])
        return sol_batch, slv_batch, t_batch

    ds = _CsvDataset(subset_rows, cache=True)
    loader = DataLoader(
        ds,
        batch_size=args.batch_size,
        shuffle=True,
        drop_last=False,
        collate_fn=_collate_min,
        num_workers=0,
    )

    for epoch in trange(args.epochs, desc="Overfit epochs"):
        model.train()
        losses = []
        t0 = time.time()
        for sol_b, slv_b, tgt in progress(
            loader, desc="Overfit train", leave=False
        ):
            sol_b = sol_b.to(device)
            slv_b = slv_b.to(device)
            T = tgt["T"].to(device)
            solvent_type = tgt.get("solvent_type")
            mask = tgt["has_solubility"].to(device)
            if not mask.any():
                continue
            opt.zero_grad()
            out = model(sol_b, slv_b, T, solvent_type=solvent_type)
            pred = out["ln_x2"][mask]
            true = tgt["ln_x2"].to(device)[mask]
            loss = F.huber_loss(pred, true, delta=1.0)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            losses.append(loss.item())

        # Train MAE on same subset
        model.eval()
        all_pred, all_true = [], []
        with torch.no_grad():
            for sol_b, slv_b, tgt in progress(
                loader, desc="Overfit eval", leave=False
            ):
                sol_b = sol_b.to(device)
                slv_b = slv_b.to(device)
                T = tgt["T"].to(device)
                solvent_type = tgt.get("solvent_type")
                mask = tgt["has_solubility"]
                if not mask.any():
                    continue
                out = model(sol_b, slv_b, T, solvent_type=solvent_type)
                all_pred.append(out["ln_x2"].cpu()[mask])
                all_true.append(tgt["ln_x2"][mask])
        pred = torch.cat(all_pred)
        true = torch.cat(all_true)
        mae = (pred - true).abs().mean().item()
        rmse = (pred - true).pow(2).mean().sqrt().item()
        dt = time.time() - t0

        if epoch % args.log_every == 0 or epoch == args.epochs - 1:
            avg_loss = float(sum(losses) / max(len(losses), 1)) if losses else math.nan
            print(
                f"Epoch {epoch:3d}/{args.epochs}: "
                f"loss={avg_loss:.4f} MAE={mae:.4f} RMSE={rmse:.4f} "
                f"({dt:.1f}s)"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Data diagnostics and overfit checks."
    )
    parser.add_argument(
        "--train-csv",
        default="notebooks/data/processed/train.csv",
    )
    parser.add_argument(
        "--val-csv",
        default="notebooks/data/processed/val.csv",
    )
    parser.add_argument(
        "--test-csv",
        default="notebooks/data/processed/test.csv",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    stats_p = sub.add_parser("stats", help="Dataset statistics")

    overfit_p = sub.add_parser("overfit", help="Overfit check")
    overfit_p.add_argument("--sample-size", type=int, default=1000)
    overfit_p.add_argument("--epochs", type=int, default=200)
    overfit_p.add_argument("--batch-size", type=int, default=64)
    overfit_p.add_argument("--lr", type=float, default=3e-4)
    overfit_p.add_argument("--seed", type=int, default=42)
    overfit_p.add_argument("--device", default=None)
    overfit_p.add_argument("--log-every", type=int, default=10)
    overfit_p.add_argument(
        "--interaction-mode",
        choices=["cross_attn", "bipartite"],
        default="cross_attn",
    )
    overfit_p.add_argument("--use-moe", action="store_true")
    overfit_p.add_argument(
        "--use-implicit-diff", action="store_true"
    )

    args = parser.parse_args()
    if args.cmd == "stats":
        run_stats(args)
    elif args.cmd == "overfit":
        run_overfit(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
