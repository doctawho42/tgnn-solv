#!/usr/bin/env python
"""Ноутбук A/B: что из двух правок ради скорости сколько даёт, на одной и той же карте.

ЗАЧЕМ ИМЕННО A/B В ОДНОМ ЯДРЕ. Диагност 2026-10-02 показал, что шаг стоит 331 мс при батче
64, а T4 занята на 25%: ни данные (загрузчик отдаёт 648-714 строк/с против потолка счёта
193), ни арифметика не узкое место -- время уходит на выдачу работы с CPU. Отсюда две
правки, обе проверенные как численно нейтральные (tests/test_solver_launch_cost_rewrites.py):

  (A) СТОПКА. Сегментная точка для смеси и чистого растворяемого решается одним вызовом
      вместо двух последовательных -- минус половина запусков внутреннего цикла.
  (C) КОМПИЛЯЦИЯ СЕГМЕНТНОГО ЦИКЛА. torch.compile применяется ТОЛЬКО к
      _segment_ln_gamma, а не ко всей модели. Зонд probe2 (2026-10-02) показал, что
      TGNN_COMPILE на всей модели даёт 752 с против 96 с, то есть замедление в 7.8 раза:
      компилятор натыкается на кастомную IFT-функцию решателя и на питоновские циклы и
      рекомпилирует без конца. Внутренний же цикл -- чистые тензорные операции со
      статическими формами, без разрывов графа, и слить его семь поэлементных ядер в одно
      это именно то, что нужно. Плечо измеряет, работает ли это рассуждение.

  (B) БЕЗ СИНХРОНИЗАЦИИ. Ранний выход внешнего цикла по solver_tol выключен на пути
      COSMO-SAC: его residual.max().item() -- блокирующая синхронизация CUDA n_iter раз за
      forward, а срабатывает он там, по run_solver_break_audit.py, ни разу. Путь NRTL не
      тронут -- там выход при нештатных счётчиках срабатывает.

Сравнивать с прошлым прогоном нельзя: это была другая выданная T4, другой сосед по хосту и
другая версия окружения. Поэтому все четыре комбинации мерятся в ОДНОМ ядре, на одном
батче, одной моделью, подряд -- и единственное, что между ними меняется, это код пути.

Старое последовательное поведение воспроизводится не откатом файла, а обёрткой над
_segment_ln_gamma, которая на вход (B,K,G) честно делает K отдельных решений. Точка вызова
при этом не меняется, так что плечо «baseline» -- это именно код записи, а не его имитация.

    python scripts/kaggle/make_speedup_notebook.py --out /tmp/kaggle_sp/probe.ipynb
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from make_notebook import ENV, INSTALL, STAGE  # noqa: E402

BODY = '''
import json, os, subprocess, sys, threading, time
from pathlib import Path
import dataclasses, inspect
import numpy as np, pandas as pd, torch, yaml

OUT = Path("/kaggle/working/out"); OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, "src")
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer
from tgnn_solv.model import TGNNSolv
from tgnn_solv.data.dataset import make_loader

res = {{"hw": {{"cpu_count": os.cpu_count(),
               "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]}}}}
print("CPU:", res["hw"]["cpu_count"], "| GPU:", res["hw"]["gpus"])

y = yaml.safe_load(open("configs/cosmo_sac.yaml"))
flat = {{}}
for k, v in y.items():
    flat.update(v if isinstance(v, dict) else {{k: v}})
fields = {{f.name for f in dataclasses.fields(TGNNSolvConfig)}}
base_kw = {{k: v for k, v in flat.items() if k in fields}}
BATCH = {batch}
df = pd.read_csv("notebooks/data/processed/train.csv", low_memory=False).head({rows})
print(f"строк {{len(df)}}, батч {{BATCH}}")

cfg0 = TGNNSolvConfig(**base_kw)
sig = set(inspect.signature(make_loader).parameters)
kw = {{k: getattr(cfg0, k) for k in (sig & fields) - {{"batch_size","shuffle","num_workers","cache"}}}}
if not getattr(cfg0, "use_source_uncertainty_weights", False):
    kw["source_uncertainty_csv"] = ""   # зеркалим train.py:841; иначе ядро падает

dev = torch.device("cuda")
ld = make_loader(df, batch_size=BATCH, shuffle=False, num_workers=0, cache=True, **kw)
sol_b, slv_b, tg = next(iter(ld))
sol_d, slv_d = sol_b.to(dev), slv_b.to(dev)
tg_d = {{k: (v.to(dev) if torch.is_tensor(v) else v) for k, v in tg.items()}}
common = dict(solvent_type=tg_d.get("solvent_type"), solute_morgan_fp=tg_d.get("solute_morgan_fp"),
              solvent_morgan_fp=tg_d.get("solvent_morgan_fp"),
              solute_descriptors=tg_d.get("solute_descriptors"),
              solvent_descriptors=tg_d.get("solvent_descriptors"),
              ionic_features=tg_d.get("ionic_features"))

# --- восстановление ПОСЛЕДОВАТЕЛЬНОГО пути: K отдельных решений на вход (B,K,G) ---
_stacked = CosmoSacLayer._segment_ln_gamma
def _sequential(self, p_norm, E, n_iter):
    if p_norm.dim() == 3:
        return torch.stack([_stacked(self, p_norm[:, k], E, n_iter)
                            for k in range(p_norm.shape[1])], dim=1)
    return _stacked(self, p_norm, E, n_iter)

def measure(stacked: bool, break_on_tol: bool, n_steps: int, compile_segment: bool = False):
    fn = _stacked if stacked else _sequential
    if compile_segment:
        # dynamic=True: последний батч эпохи короче, иначе будет вторая компиляция.
        fn = torch.compile(fn, dynamic=True)
    CosmoSacLayer._segment_ln_gamma = fn
    cfg = TGNNSolvConfig(**{{**base_kw, "solver_cosmo_break_on_tol": break_on_tol}})
    torch.manual_seed(0)
    model = TGNNSolv(node_feat_dim=sol_b.x.shape[1], edge_feat_dim=sol_b.edge_attr.shape[1],
                     cfg=cfg).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    for _ in range(4):
        out, _ = model(sol_d, slv_d, tg_d["T"], **common, targets=tg_d, return_intermediates=True)
        out["ln_x2"].sum().backward(); opt.zero_grad(set_to_none=True)
    torch.cuda.synchronize()
    util, stop = [], threading.Event()
    def sample():
        while not stop.is_set():
            try:
                o = subprocess.run(["nvidia-smi","--query-gpu=utilization.gpu",
                                    "--format=csv,noheader,nounits"],
                                   capture_output=True, text=True, timeout=5)
                util.append(int(o.stdout.strip().splitlines()[0]))
            except Exception:
                pass
            time.sleep(0.25)
    th = threading.Thread(target=sample, daemon=True); th.start()
    t0 = time.perf_counter()
    for _ in range(n_steps):
        out, _ = model(sol_d, slv_d, tg_d["T"], **common, targets=tg_d, return_intermediates=True)
        out["ln_x2"].sum().backward(); opt.step(); opt.zero_grad(set_to_none=True)
    torch.cuda.synchronize(); dt = time.perf_counter() - t0
    stop.set(); th.join(timeout=2)
    lnx2 = float(out["ln_x2"].detach().sum())
    del model, opt
    torch.cuda.empty_cache()
    return {{"s_per_step": dt / n_steps, "rows_per_s": n_steps * BATCH / dt,
            "gpu_util_mean": (float(np.mean(util)) if util else None),
            "lnx2_sum_after_warmup": lnx2}}

ARMS = [("baseline (как было)",    False, True,  False),
        ("только стопка",          True,  True,  False),
        ("только без синхр.",      False, False, False),
        ("обе (новое по умолч.)",  True,  False, False),
        ("обе + компиляция сегм.", True,  False, True)]
N = {steps}
res["arms"] = {{}}
for name, st, br, cp in ARMS:
    try:
        r = measure(st, br, N, cp)
    except Exception as e:                 # компиляция может не собраться -- не роняем прогон
        print(f"  {{name:<24}} ОШИБКА: {{type(e).__name__}}: {{e}}"[:300])
        res["arms"][name] = {{"error": f"{{type(e).__name__}}: {{e}}"[:500],
                             "stacked": st, "break_on_tol": br, "compile_segment": cp}}
        continue
    res["arms"][name] = dict(r, stacked=st, break_on_tol=br, compile_segment=cp)
    print(f"  {{name:<24}} {{r['s_per_step']*1000:7.1f}} мс/шаг  {{r['rows_per_s']:6.0f}} строк/с"
          f"  GPU {{(r['gpu_util_mean'] or 0):3.0f}}%")

base = res["arms"]["baseline (как было)"]["s_per_step"]
print("\\nУСКОРЕНИЕ относительно baseline:")
for name, a in res["arms"].items():
    if "s_per_step" not in a:
        print(f"  {{name:<24}} -- (не измерено)"); continue
    a["speedup"] = base / a["s_per_step"]
    print(f"  {{name:<24}} {{a['speedup']:.2f}}x")

vals = [a["lnx2_sum_after_warmup"] for a in res["arms"].values() if "lnx2_sum_after_warmup" in a]
# Контроль, что между плечами менялся ТОЛЬКО код пути: сеть пересоздаётся с одним сидом,
# батч один и тот же, поэтому после одинакового числа шагов сумма ln x2 должна совпадать
# до шума суммирования. Расхождение здесь означало бы, что плечи несравнимы.
print(f"\\nразброс sum(ln x2) по плечам: {{max(vals) - min(vals):.3e}} (должен быть шумом)")
res["lnx2_spread"] = max(vals) - min(vals)

(OUT / "speedup.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
print("записано: /kaggle/working/out/speedup.json")

import shutil
os.chdir("/kaggle/working")   # STAGE сделал chdir ВНУТРЬ удаляемого каталога
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
    ap.add_argument("--rows", type=int, default=4000)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--dataset", default="polomoshnov/tgnn-solv-e5")
    a = ap.parse_args()

    body = BODY.format(rows=a.rows, batch=a.batch, steps=a.steps)
    nb = {"cells": [cell(ENV), cell(INSTALL),
                    cell(STAGE), cell(body)],
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3",
                                      "language": "python"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(nb, ensure_ascii=False, indent=1))
    print(f"ноутбук: {a.out}  ({a.steps} шагов x 5 плеч, батч {a.batch})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
