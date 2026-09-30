#!/usr/bin/env python
"""Сходится ли сегментная неподвижная точка COSMO-SAC, и чего стоит то, что её не проверяют.

ОТКУДА ВОПРОС. Рецензент 2 разбора JCIM (ci-2026-030738, отклонена 2026-09-29): «It also seems to
me they have fixed iteration numbers for resolving the equations that need to be iterated. Is the
condition actually tested in the end if it is fulfilled, or is it assumed, that it is converged?»

Ответ по коду: **предполагается**. `layers.py:_segment_ln_gamma` крутит `for _ in range(n_iter)` --
ни допуска, ни невязки, ни выхода по критерию. Счётчики фиксированы: 16 при обучении, 30 при
оценке (`config.py:185-186`).

ЧТО ИМЕННО НАДО ОТДЕЛИТЬ, И ЭТО ГЛАВНОЕ. В проекте уже записано (CLAUDE.md), что один только
счётчик, при неизменных весах и строках, двигает ln x2 MAE с 1.92 (n=8) до 3.01 (n=300). Отсюда
легко сделать неверный вывод, что решатель не сходится и все числа испорчены. Это ДВА РАЗНЫХ
утверждения, и аудит их разделяет:

  (A) ЧИСЛЕННАЯ ошибка итерации -- насколько ln gamma при счётчике n далёк от предела n->inf.
      Свойство решателя. Если она мала, решатель в порядке.
  (B) СДВИГ MAE от смены счётчика -- насколько ln x2 уезжает, когда оператор меняют под
      неизменными весами. Свойство ОБУЧЕНИЯ: веса подогнаны против недосходившегося оператора,
      и сходимость уводит их с того оператора, против которого они фитились.

Если (B) >> (A), то сдвиг MAE -- артефакт обучения, а не отказ решателя, и лечится он
переобучением при сошедшемся операторе, а не увеличением счётчика при оценке.

ЧАСТЬ A -- РЕШАТЕЛЬ. Сегментная неподвижная точка на реальных входах IDAC (7889 записей,
PGL6ed), для ДВУХ источников профиля: депонированного VT-2005 и выученного. Второй нужен потому,
что выученный профиль физически негоден (results/idac_learned_vs_reference: AAD хуже в 2.3 раза,
площадь воды завышена втрое), и вопрос, не труднее ли он ещё и численно, сам по себе содержателен.
Опорная точка -- n=3000, её сходимость проверяется по убыванию поправки.

ЧАСТЬ B -- РАСПРОСТРАНЕНИЕ. Тот же чекпойнт, те же размеченные строки теста, счётчик при оценке
меняется; меряется ln x2 MAE и построчный сдвиг против n=300. Веса не трогаются.

ПОЧЕМУ НЕВЯЗКА НЕ ПО МАКСИМУМУ ПО БИНАМ. Первая версия диагностики брала
max|Gamma*sum(p Gamma E) - 1| по ВСЕМ бинам и показала ~1.0 даже при n=20000, что читалось как
«не сходится». Это артефакт: в пустых бинах Gamma вырождена (делится на ~eps и упирается в
clamp 1e8), а в свёртку она входит с весом p2_pure и потому на результат не влияет. Меряется
величина в единицах утверждения -- ln gamma, -- а не промежуточная Gamma.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_segment_convergence_audit.py
    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_segment_convergence_audit.py --skip-b
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts/analysis"))

from export_checkpoint_predictions import build_loader, forward_batch      # noqa: E402
from run_sigma_profile_residual import build_model, learned_profiles       # noqa: E402
from tgnn_solv.data.utils import canonicalize                              # noqa: E402
from tgnn_solv.layers import CosmoSacLayer                                 # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles                     # noqa: E402

CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
RECORDS = ROOT / "results/published_idac_check/scored_records.csv"
TEST = ROOT / "notebooks/data/processed/test.csv"
OUT = ROOT / "results/segment_convergence"

COUNTS_A = [8, 16, 30, 50, 100, 300, 1000]
COUNTS_B = [8, 16, 30, 100, 300]
N_REF = 3000


def segment_ln_gamma_inf(L, p2, A2, p1, A1, T, n: int) -> torch.Tensor:
    """ln gamma_2^inf при счётчике n, тем же путём, что _residual_ln_gamma2 при x2=0."""
    E = L._E_matrix(T)
    p_mix = p1 / A1.clamp_min(L.eps).unsqueeze(-1)     # при x2->0 смесь = чистый растворитель
    p2_pure = p2 / A2.clamp_min(L.eps).unsqueeze(-1)

    def seg(pn):
        g = torch.ones_like(pn)
        for _ in range(n):
            den = torch.bmm(E, (pn * g).unsqueeze(-1)).squeeze(-1)
            g = L.damping * (1.0 / (den + L.eps)) + (1.0 - L.damping) * g
            g = g.clamp(1e-8, 1e8)
        return torch.log(g + L.eps)

    return ((A2 / L.a_eff) * (p2_pure * (seg(p_mix) - seg(p2_pure))).sum(-1)).clamp(-50.0, 50.0)


def spread(d: torch.Tensor) -> dict:
    return {"median": float(d.median()), "p95": float(d.quantile(0.95)), "max": float(d.max()),
            "frac_gt_0.01": float((d > 0.01).float().mean()),
            "frac_gt_0.1": float((d > 0.1).float().mean())}


def part_a(seed_ckpt: Path) -> dict:
    L = CosmoSacLayer()
    L.eval()
    tab = load_sigma_profiles(str(PROFILES), n_bins=51)
    d = pd.read_csv(RECORDS)
    k2 = [canonicalize(str(s)) for s in d.solute_smiles]
    k1 = [canonicalize(str(s)) for s in d.solvent_smiles]
    ok = np.array([(a in tab) and (b in tab) for a, b in zip(k2, k1)])
    d = d[ok].reset_index(drop=True)
    k2 = [k for k, o in zip(k2, ok) if o]
    k1 = [k for k, o in zip(k1, ok) if o]
    T = torch.tensor(d["T_K"].to_numpy(float), dtype=torch.float)

    sources = {"reference_vt2005": (
        torch.tensor(np.stack([tab[k][0] for k in k2]), dtype=torch.float),
        torch.tensor([tab[k][1] for k in k2], dtype=torch.float),
        torch.tensor(np.stack([tab[k][0] for k in k1]), dtype=torch.float),
        torch.tensor([tab[k][1] for k in k1], dtype=torch.float))}

    model, ckd, cfg = build_model(seed_ckpt)
    tpl = pd.read_csv(TEST, nrows=1, low_memory=False)
    mols = sorted(set(d.solute_smiles.astype(str)) | set(d.solvent_smiles.astype(str)))
    u, v = learned_profiles(model, cfg, mols, tpl)
    U = {s: np.asarray(u[i], float) for i, s in enumerate(mols)}
    V = {s: np.asarray(v[i], float) for i, s in enumerate(mols)}
    p2 = np.stack([U[s] for s in d.solute_smiles.astype(str)])
    p1 = np.stack([V[s] for s in d.solvent_smiles.astype(str)])
    sources[f"learned_seed{int(ckd.get('seed', -1))}"] = (
        torch.tensor(p2, dtype=torch.float), torch.tensor(p2.sum(1), dtype=torch.float),
        torch.tensor(p1, dtype=torch.float), torch.tensor(p1.sum(1), dtype=torch.float))

    res = {"n_records": int(len(d)), "n_ref": N_REF, "damping": float(L.damping),
           "by_source": {}}
    with torch.no_grad():
        for name, (a, b, c, e) in sources.items():
            ref = segment_ln_gamma_inf(L, a, b, c, e, T, N_REF)
            # опорная точка сама должна быть сошедшейся: поправка от N_REF/3 до N_REF
            chk = (segment_ln_gamma_inf(L, a, b, c, e, T, N_REF // 3) - ref).abs().max()
            res["by_source"][name] = {"reference_self_check_max": float(chk), "counts": {}}
            print(f"\n{name}  (опорная n={N_REF}, поправка от n={N_REF // 3}: {chk:.2e})")
            print(f"{'n':>6}{'медиана':>12}{'95-й':>12}{'макс':>12}{'>0.01':>9}{'>0.1':>8}")
            for n in COUNTS_A:
                dl = (segment_ln_gamma_inf(L, a, b, c, e, T, n) - ref).abs()
                s = spread(dl)
                res["by_source"][name]["counts"][n] = s
                print(f"{n:>6}{s['median']:>12.3e}{s['p95']:>12.3e}{s['max']:>12.3e}"
                      f"{100 * s['frac_gt_0.01']:>8.1f}%{100 * s['frac_gt_0.1']:>7.1f}%")
    return res


def part_b(ckpts: list[Path], batch_size: int, device: torch.device) -> dict:
    test = pd.read_csv(TEST, low_memory=False)
    df = test[test["ln_x2"].notna()].reset_index(drop=True)
    out: dict = {"counts": COUNTS_B, "per_seed": {}}
    frames = []
    for ck in ckpts:
        model, ckd, cfg = build_model(ck)
        seed = int(ckd.get("seed", -1))
        model.to(device)
        layer = model.sle_solver.cosmo_sac_layer
        if layer is None:
            print("плечо не на COSMO-SAC -- часть B пропущена")
            return {}
        print(f"\nсид {seed}  (обучался при n={layer.n_iter_train})", flush=True)
        for n in COUNTS_B:
            layer.n_iter_eval = n
            rows = []
            loader = build_loader(df, cfg, batch_size, 0)
            with torch.no_grad():
                for sol_b, slv_b, targets in loader:
                    o, _ = forward_batch("tgnn", model, sol_b, slv_b, targets, device)
                    pred = o["ln_x2"].detach().cpu().numpy().astype(float)
                    true = targets["ln_x2"].detach().cpu().numpy().astype(float)
                    has = targets["has_solubility"].detach().cpu().numpy().astype(bool)
                    for j in range(len(pred)):
                        if has[j]:
                            rows.append({"row_idx": len(rows), "pred": pred[j],
                                         "abs_err": abs(pred[j] - true[j])})
            r = pd.DataFrame(rows)
            r["seed"], r["n_iter"] = seed, n
            frames.append(r)
            print(f"  n={n:<5} MAE {r.abs_err.mean():.4f}  (n_rows={len(r)})", flush=True)
    per_row = pd.concat(frames, ignore_index=True)
    w = per_row.pivot_table(index=["seed", "row_idx"], columns="n_iter", values="pred")
    mae = per_row.groupby(["seed", "n_iter"]).abs_err.mean().unstack()
    out["mae_per_seed"] = {int(s): {int(c): float(mae.loc[s, c]) for c in mae.columns}
                           for s in mae.index}
    out["mae_mean"] = {int(c): float(mae[c].mean()) for c in mae.columns}
    ref = COUNTS_B[-1]
    out["ln_x2_shift_vs_converged"] = {}
    for c in COUNTS_B[:-1]:
        d = (w[c] - w[ref]).abs()
        out["ln_x2_shift_vs_converged"][int(c)] = spread(torch.tensor(d.to_numpy(float)))
    out["per_row_csv"] = "per_row_lnx2.csv"
    return out, per_row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ckpt-dir", type=Path, default=CKPT_DIR)
    ap.add_argument("--arm-glob", default="grounded_a_seed*.pt")
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--skip-b", action="store_true", help="только решатель, без прогонов модели")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    cks = sorted(a.ckpt_dir.glob(a.arm_glob))
    if not cks:
        print(f"нет чекпойнтов в {a.ckpt_dir}/{a.arm_glob}")
        return 1
    a.out.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("ЧАСТЬ A -- сходимость сегментной неподвижной точки (IDAC, ln gamma_inf)")
    print("=" * 78)
    summary = {"part_a": part_a(cks[0])}

    if not a.skip_b:
        print("\n" + "=" * 78)
        print("ЧАСТЬ B -- распространение в ln x2 (те же веса, меняется только счётчик)")
        print("=" * 78)
        b, per_row = part_b(cks, a.batch_size, torch.device(a.device))
        summary["part_b"] = b
        per_row.to_csv(a.out / "per_row_lnx2.csv", index=False)

        print(f"\n{'n':>6}{'MAE (среднее по сидам)':>26}")
        for c, m in b["mae_mean"].items():
            print(f"{c:>6}{m:>26.4f}")
        print(f"\nпострочный сдвиг ln x2 против n={COUNTS_B[-1]}:")
        print(f"{'n':>6}{'медиана':>12}{'95-й':>12}{'макс':>12}")
        for c, s in b["ln_x2_shift_vs_converged"].items():
            print(f"{c:>6}{s['median']:>12.3e}{s['p95']:>12.3e}{s['max']:>12.3e}")

        # РАЗДЕЛЕНИЕ (A) от (B) -- то, ради чего аудит и делается.
        solver_max = max(v["counts"][30]["max"] for v in summary["part_a"]["by_source"].values())
        mae_shift = abs(b["mae_mean"][30] - b["mae_mean"][COUNTS_B[-1]])
        summary["separation"] = {
            "solver_error_at_30_max_ln_gamma": solver_max,
            "mae_shift_30_to_converged_ln_x2": mae_shift,
            "ratio": float(mae_shift / solver_max) if solver_max else None}
        print("\nРАЗДЕЛЕНИЕ")
        print(f"  (A) численная ошибка решателя при n=30, макс по строкам: {solver_max:.4f} ln gamma")
        print(f"  (B) сдвиг MAE от n=30 к сошедшемуся:                     {mae_shift:.4f} ln x2")
        if solver_max and mae_shift / solver_max > 3:
            print(f"  (B) больше (A) в {mae_shift / solver_max:.1f} раза -- сдвиг НЕ численный,")
            print("      это несоответствие оператора тем весам, что против него фитились.")

    (a.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                        encoding="utf8")
    print(f"\nзаписано: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
