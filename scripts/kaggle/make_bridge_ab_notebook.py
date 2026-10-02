#!/usr/bin/env python
"""A/B векторизованного моста плоское/плотное и свёртка по числу воркеров загрузчика.

ЗАЧЕМ ИМЕННО ТАК. Профиль настоящего шага (results/real_step_profile/summary.json, T4,
2026-10-02) показал: 63% диспатчей растут РОВНО пропорционально батчу, то есть платятся за
каждую молекулу отдельно. Самые крупные -- lift_fresh 49.2 на граф, detach_ 46.3, slice
19.5, Memcpy DtoD 14.5. Отсюда две правки-кандидата, и они лечат РАЗНЫЕ источники:

  (A) ВЕКТОРИЗОВАННЫЙ МОСТ. model._to_dense_with_token заменил четыре питоновских цикла по
      графам (split булевой маской, cat токена, pad присваиванием, сборка batch из full) на
      to_dense_batch плюс один index_put. Нейтральность доказана: ln_x2 и loss побитово,
      по всем 5.26 млн элементов градиента max|Δ| = 1.49e-08 при 99.25% побитовых совпадений.

  (B) ВОРКЕРЫ ЗАГРУЗЧИКА. Плечо учится с num_workers=0 (config.py:258 -- значение по
      умолчанию, cosmo_sac.yaml его не переопределяет), то есть фичеризация и collate идут
      ПОСЛЕДОВАТЕЛЬНО внутри шага. Подозрение именно на collate: lift_fresh возникает при
      создании тензора из питоновского значения, а в моём мосте таких вызовов не было вовсе
      (там был full) -- значит 49 на граф приходят скорее из Batch.from_data_list. Воркеры
      этого не ускоряют, но выносят в другой процесс и перекрывают со счётом.
      Инфраструктура готова: dataset.py:1066 сама ставит persistent_workers=True.

ПОЧЕМУ СТАРЫЙ МОСТ -- ОТДЕЛЬНОЕ ПЛЕЧО, А НЕ ПРОШЛЫЙ ПРОГОН. Сравнивать с замеренными 312.3
мс нельзя: это была другая выданная T4, и расхождение двух оценок одной величины на разных
картах в этом проекте уже наблюдалось в 34%. Поэтому старое поведение воспроизводится здесь
же, подменой _to_dense_with_token на обёртку над теми же старыми помощниками, которые
никуда не удалены. Плечо "старый мост" -- это код записи, а не его имитация.

    python scripts/kaggle/make_bridge_ab_notebook.py --out /tmp/kaggle_br/probe.ipynb
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from make_notebook import ENV, INSTALL, STAGE  # noqa: E402

BODY = r'''
import json, os, subprocess, sys, threading, time
from collections import Counter
from pathlib import Path
import dataclasses, inspect
import numpy as np, pandas as pd, torch, yaml

OUT = Path("/kaggle/working/out"); OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, "src")
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer, pad_atom_features
from tgnn_solv.model import TGNNSolv
from tgnn_solv.trainer import TGNNSolvTrainer
from tgnn_solv.data.dataset import make_loader

res = {"hw": {"cpu_count": os.cpu_count(),
              "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
              "torch": torch.__version__}}
print("CPU:", res["hw"]["cpu_count"], "| GPU:", res["hw"]["gpus"], "| torch", torch.__version__)

y = yaml.safe_load(open("configs/cosmo_sac.yaml"))
flat = {}
for k, v in y.items():
    flat.update(v if isinstance(v, dict) else {k: v})
FIELDS = {f.name for f in dataclasses.fields(TGNNSolvConfig)}
cfg = TGNNSolvConfig(**{k: v for k, v in flat.items() if k in FIELDS})
assert hasattr(TGNNSolv, "_to_dense_with_token"), "ожидался пакет с векторизованным мостом"
print("num_workers в конфиге плеча:", cfg.num_workers)

FULL = pd.read_csv("notebooks/data/processed/train.csv", low_memory=False)
sig = set(inspect.signature(make_loader).parameters)
KW = {k: getattr(cfg, k) for k in (sig & FIELDS)
      - {"batch_size", "shuffle", "num_workers", "cache"}}
if not getattr(cfg, "use_source_uncertainty_weights", False):
    KW["source_uncertainty_csv"] = ""     # зеркалим train.py:841

CosmoSacLayer._segment_ln_gamma = torch.compile(
    CosmoSacLayer._segment_ln_gamma, dynamic=True)
print("сегментный цикл скомпилирован (как в выигравшем плече A/B)")

# --- восстановление СТАРОГО моста: те же питоновские циклы, новая подпись ---
_new_bridge = TGNNSolv._to_dense_with_token

def _old_bridge(self, h_atoms, data, token):
    lst = self._append_global_token(
        self._split_atoms_by_graph(h_atoms, data.batch), token)
    padded, full_mask = pad_atom_features(lst)
    counts = torch.tensor([h.shape[0] - 1 for h in lst], device=padded.device)
    rows = torch.arange(padded.shape[0], device=padded.device)
    atom_mask = full_mask.clone()
    atom_mask[rows, counts] = False
    return padded, atom_mask, full_mask, counts

def gpu_sampler():
    util, stop = [], threading.Event()
    def run():
        while not stop.is_set():
            try:
                o = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu",
                                    "--format=csv,noheader,nounits"],
                                   capture_output=True, text=True, timeout=5)
                util.append(int(o.stdout.strip().splitlines()[0]))
            except Exception:
                pass
            time.sleep(0.25)
    th = threading.Thread(target=run, daemon=True); th.start()
    return util, stop, th

BATCH = __BATCH__
N_SHORT, N_LONG = __N_SHORT__, __N_LONG__

def build():
    ld = make_loader(FULL.head(BATCH * 2), batch_size=BATCH, shuffle=False,
                     num_workers=0, cache=True, **KW)
    sol_b, _, _ = next(iter(ld))
    torch.manual_seed(0)
    model = TGNNSolv(node_feat_dim=sol_b.x.shape[1],
                     edge_feat_dim=sol_b.edge_attr.shape[1], cfg=cfg).to("cuda")
    return model, TGNNSolvTrainer(model, cfg), torch.optim.AdamW(model.parameters(), lr=1e-4)

def real_epoch(trainer, opt, steps, workers):
    ld = make_loader(FULL.head(BATCH * steps), batch_size=BATCH, shuffle=True,
                     num_workers=workers, cache=True, drop_last=True, **KW)
    t0 = time.perf_counter()
    trainer.train_epoch(ld, opt, phase=2, epoch=0, compute_mono=False)
    torch.cuda.synchronize()
    return time.perf_counter() - t0

def measure(bridge_new, workers):
    TGNNSolv._to_dense_with_token = _new_bridge if bridge_new else _old_bridge
    model, trainer, opt = build()
    real_epoch(trainer, opt, 3, workers)                       # прогрев
    torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
    util, stop, th = gpu_sampler()
    t_s = real_epoch(trainer, opt, N_SHORT, workers)
    t_l = real_epoch(trainer, opt, N_LONG, workers)
    stop.set(); th.join(timeout=2)
    marginal = (t_l - t_s) / (N_LONG - N_SHORT)
    out = {"s_per_step": marginal, "rows_per_s": BATCH / marginal,
           "gpu_util_mean": (float(np.mean(util)) if util else None),
           "peak_gb": torch.cuda.max_memory_allocated() / 2**30,
           "bridge": ("векторизованный" if bridge_new else "старый"), "workers": workers}
    del model, trainer, opt
    torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
    return out

ARMS = [("старый мост, воркеров 0", False, 0),
        ("новый мост,  воркеров 0", True, 0),
        ("новый мост,  воркеров 2", True, 2),
        ("новый мост,  воркеров 4", True, 4),
        ("старый мост, воркеров 4", False, 4)]
print(f"\nбатч {BATCH}, цена шага по наклону эпох {N_SHORT}/{N_LONG}")
res["arms"] = {}
for name, bn, w in ARMS:
    try:
        r = measure(bn, w)
        res["arms"][name] = r
        print(f"  {name:<26} {r['s_per_step']*1000:7.1f} мс/шаг  {r['rows_per_s']:6.0f} строк/с"
              f"  GPU {(r['gpu_util_mean'] or 0):3.0f}%  пик {r['peak_gb']:.2f} ГБ")
    except Exception as e:
        res["arms"][name] = {"error": f"{type(e).__name__}: {e}"[:400]}
        print(f"  {name:<26} ОШИБКА {type(e).__name__}: {e}"[:200])
        torch.cuda.empty_cache()

base = res["arms"].get("старый мост, воркеров 0", {}).get("s_per_step")
if base:
    print("\nУСКОРЕНИЕ относительно старого моста без воркеров:")
    for name, a in res["arms"].items():
        if "s_per_step" in a:
            a["speedup"] = base / a["s_per_step"]
            steps_ep = 111724 // BATCH
            a["arm_hours_110ep"] = a["s_per_step"] * steps_ep * 110 / 3600
            print(f"  {name:<26} {a['speedup']:.2f}x   плечо {a['arm_hours_110ep']:5.1f} ч")
    print("\n  (предел ядра Kaggle -- 12 ч, поэтому цель не 14, а <11)")

# --- профиль: упал ли счёт per-graph операций, названных профилем прошлого прогона ---
print("\nпрофиль: что стало со счётом операций, которые росли с батчем")
res["profile"] = {}
try:
    from torch.profiler import ProfilerActivity, profile
    def cuda_us(e):
        return float(getattr(e, "self_device_time_total",
                             getattr(e, "self_cuda_time_total", 0.0)))
    WATCH = ["aten::lift_fresh", "aten::detach_", "aten::slice", "aten::nonzero",
             "aten::full", "aten::copy_", "aten::empty", "aten::to",
             "Memcpy DtoD (Device -> Device)", "Memcpy DtoH (Device -> Pageable)",
             "cudaLaunchKernel", "aten::as_strided", "aten::_index_put_impl_"]
    for tag, bn, w in (("старый мост", False, 0), ("новый мост", True, 0)):
        TGNNSolv._to_dense_with_token = _new_bridge if bn else _old_bridge
        model, trainer, opt = build()
        real_epoch(trainer, opt, 3, w)
        torch.cuda.synchronize()
        NP = __PROFILE_STEPS__
        with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
                     record_shapes=False) as prof:
            real_epoch(trainer, opt, NP, w)
        ka = list(prof.key_averages())
        counts = {e.key: e.count / NP for e in ka}
        tot_cpu = sum(float(e.self_cpu_time_total) for e in ka) / NP
        tot_cuda = sum(cuda_us(e) for e in ka) / NP
        n_disp = sum(e.count for e in ka if cuda_us(e) > 0) / NP
        res["profile"][tag] = {
            "totals": {"self_cpu_us": tot_cpu, "self_cuda_us": tot_cuda,
                       "cuda_op_launches": n_disp,
                       "cpu_over_cuda": (tot_cpu / tot_cuda if tot_cuda else None)},
            "watched": {k: counts.get(k, 0.0) for k in WATCH},
            "top_by_count": [{"name": e.key, "count": e.count / NP}
                             for e in sorted(ka, key=lambda x: x.count, reverse=True)[:20]]}
        print(f"  {tag}: диспатчей ~{n_disp:.0f}, CPU/GPU {(tot_cpu/tot_cuda if tot_cuda else 0):.2f}x")
        del model, trainer, opt; torch.cuda.empty_cache()
    if len(res["profile"]) == 2:
        o, n = res["profile"]["старый мост"]["watched"], res["profile"]["новый мост"]["watched"]
        print(f"\n  {'операция':<36} {'старый':>9} {'новый':>9}  изменение")
        for k in WATCH:
            if o.get(k, 0) >= 20 or n.get(k, 0) >= 20:
                ch = (n[k] / o[k]) if o.get(k) else float("inf")
                print(f"  {k:<36} {o.get(k,0):9.0f} {n.get(k,0):9.0f}  x{ch:.2f}")
        res["dispatch_delta"] = {
            "old_total": res["profile"]["старый мост"]["totals"]["cuda_op_launches"],
            "new_total": res["profile"]["новый мост"]["totals"]["cuda_op_launches"]}
except Exception as e:
    res["profile"]["error"] = f"{type(e).__name__}: {e}"[:400]
    print(f"  ОШИБКА: {type(e).__name__}: {e}"[:250])

(OUT / "bridge_ab.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
print("\nзаписано: /kaggle/working/out/bridge_ab.json")

import shutil
os.chdir("/kaggle/working")
shutil.rmtree("/kaggle/working/repo", ignore_errors=True)
print("рабочая копия репозитория удалена из выгрузки")
'''


def cell(src: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": src.strip("\n").splitlines(keepends=True)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--n-short", type=int, default=6)
    ap.add_argument("--n-long", type=int, default=18)
    ap.add_argument("--profile-steps", type=int, default=4)
    a = ap.parse_args()
    if a.n_long <= a.n_short:
        ap.error("--n-long должен быть больше --n-short: цена шага берётся по наклону")
    tokens = {"__BATCH__": str(a.batch), "__N_SHORT__": str(a.n_short),
              "__N_LONG__": str(a.n_long), "__PROFILE_STEPS__": str(a.profile_steps)}
    body = BODY
    for t, v in tokens.items():
        assert t in body, t
        body = body.replace(t, v)
    assert not [t for t in tokens if t in body], "остался неподставленный токен"
    nb = {"cells": [cell(ENV), cell(INSTALL), cell(STAGE), cell(body)],
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3",
                                      "language": "python"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(nb, ensure_ascii=False, indent=1))
    print(f"ноутбук: {a.out}  (5 плеч, батч {a.batch}, эпохи {a.n_short}/{a.n_long})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
