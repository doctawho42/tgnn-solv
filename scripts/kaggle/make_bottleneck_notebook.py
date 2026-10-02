#!/usr/bin/env python
"""Ноутбук-диагност: где именно теряется скорость -- в видеокарте или в тракте данных.

ЗАЧЕМ. Зонд 2026-10-02 дал на T4 455 строк/с при батче 64 и ускорение лишь 1.43x от батча 512.
Для трёхслойного GNN с hidden 64 это на порядок ниже того, что T4 способна считать, а слабая
отдача от укрупнения батча означает, что доминирует работа НА СТРОКУ, а не на шаг. Обе приметы
указывают на голодающую видеокарту, но ни одна этого не доказывает.

ТРИ ЗАМЕРА, КОТОРЫЕ РАЗДЕЛЯЮТ ПРИЧИНЫ

  (1) ПОТОЛОК БЕЗ ЗАГРУЗЧИКА. Один батч собирается один раз, затем forward+backward гоняется по
      нему в цикле. Тракт данных исключён полностью. Если здесь кратно быстрее, чем в обучении,
      виноват загрузчик, и отношение сразу даёт запас.
  (2) ЗАГРУЗКА БЕЗ СЧЁТА. Проход по загрузчику без модели вообще: сколько строк в секунду он
      отдаёт сам по себе. Это верхняя граница скорости обучения при данном числе воркеров.
  (3) ЗАГРУЗКА GPU ВО ВРЕМЯ ОБУЧЕНИЯ, снятая nvidia-smi параллельно. Низкая загрузка при
      высокой скорости (2) означала бы, что узкое место не в них двоих, а в синхронизации.

ПОЧЕМУ ЭТО ВАЖНЕЕ, ЧЕМ ВТОРАЯ ВИДЕОКАРТА. Kaggle даёт режим T4 x2, но если видеокарта голодает,
вторая будет голодать тоже: DataParallel делит батч, а не ускоряет загрузку. Этот зонд говорит,
имеет ли смысл второй ускоритель, ДО того как на него потрачена квота.

    python scripts/kaggle/make_bottleneck_notebook.py --out /tmp/kaggle_bn/probe.ipynb
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
import numpy as np, pandas as pd, torch

OUT = Path("/kaggle/working/out"); OUT.mkdir(parents=True, exist_ok=True)
res = {{"hw": {{"cpu_count": os.cpu_count(),
               "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]}}}}
print("CPU:", res["hw"]["cpu_count"], "| GPU:", res["hw"]["gpus"])

sys.path.insert(0, "src"); sys.path.insert(0, "scripts/analysis")
import dataclasses, inspect
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.model import TGNNSolv
from tgnn_solv.data.dataset import make_loader
import yaml

y = yaml.safe_load(open("configs/cosmo_sac.yaml"))
flat = {{}}
for k, v in y.items():
    flat.update(v if isinstance(v, dict) else {{k: v}})
fields = {{f.name for f in dataclasses.fields(TGNNSolvConfig)}}
cfg = TGNNSolvConfig(**{{k: v for k, v in flat.items() if k in fields}})
BATCH = {batch}
df = pd.read_csv("notebooks/data/processed/train.csv", low_memory=False).head({rows})
print(f"строк {{len(df)}}, батч {{BATCH}}")

sig = set(inspect.signature(make_loader).parameters)
kw = {{k: getattr(cfg, k) for k in (sig & fields) - {{"batch_size","shuffle","num_workers","cache"}}}}
# ЗЕРКАЛИМ train.py:841. Там source_uncertainty_csv подставляется ТОЛЬКО при включённом
# use_source_uncertainty_weights, иначе пустая строка. Прямой вызов make_loader с сырым значением
# конфига уронил первый диагност: файл весит 31.7 МБ и в пакет не кладётся.
if not getattr(cfg, "use_source_uncertainty_weights", False):
    kw["source_uncertainty_csv"] = ""
print("source_uncertainty_csv:", repr(kw.get("source_uncertainty_csv", "<нет в сигнатуре>")))

dev = torch.device("cuda")

# ---------- (2) загрузчик БЕЗ модели, при разном числе воркеров ----------
res["loader_only"] = {{}}
for nw in {workers}:
    ld = make_loader(df, batch_size=BATCH, shuffle=True, num_workers=nw, cache=True, **kw)
    t0 = time.perf_counter(); n = 0
    for sol_b, slv_b, tg in ld:
        n += int(sol_b.num_graphs)
    dt = time.perf_counter() - t0
    res["loader_only"][nw] = {{"rows_per_s": n / dt, "wall_s": dt}}
    print(f"  загрузчик, воркеров {{nw}}: {{n/dt:7.0f}} строк/с")

# ---------- (1) потолок БЕЗ загрузчика: один батч в цикле ----------
ld = make_loader(df, batch_size=BATCH, shuffle=False, num_workers=0, cache=True, **kw)
sol_b, slv_b, tg = next(iter(ld))
model = TGNNSolv(node_feat_dim=sol_b.x.shape[1], edge_feat_dim=sol_b.edge_attr.shape[1],
                 cfg=cfg).to(dev)
opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
sol_d, slv_d = sol_b.to(dev), slv_b.to(dev)
tg_d = {{k: (v.to(dev) if torch.is_tensor(v) else v) for k, v in tg.items()}}
common = dict(solvent_type=tg_d.get("solvent_type"), solute_morgan_fp=tg_d.get("solute_morgan_fp"),
              solvent_morgan_fp=tg_d.get("solvent_morgan_fp"),
              solute_descriptors=tg_d.get("solute_descriptors"),
              solvent_descriptors=tg_d.get("solvent_descriptors"),
              ionic_features=tg_d.get("ionic_features"))
for _ in range(3):   # прогрев
    out, _ = model(sol_d, slv_d, tg_d["T"], **common, targets=tg_d, return_intermediates=True)
    out["ln_x2"].sum().backward(); opt.zero_grad(set_to_none=True)
torch.cuda.synchronize()
N = {steps}
t0 = time.perf_counter()
for _ in range(N):
    out, _ = model(sol_d, slv_d, tg_d["T"], **common, targets=tg_d, return_intermediates=True)
    out["ln_x2"].sum().backward(); opt.step(); opt.zero_grad(set_to_none=True)
torch.cuda.synchronize()
dt = time.perf_counter() - t0
res["compute_ceiling"] = {{"rows_per_s": N * BATCH / dt, "s_per_step": dt / N}}
print(f"\\n  ПОТОЛОК без загрузчика: {{N*BATCH/dt:7.0f}} строк/с ({{dt/N*1000:.1f}} мс/шаг)")

# ---------- (3) загрузка GPU во время полного цикла ----------
util = []
stop = threading.Event()
def sample():
    while not stop.is_set():
        try:
            o = subprocess.run(["nvidia-smi","--query-gpu=utilization.gpu","--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=5)
            util.append(int(o.stdout.strip().splitlines()[0]))
        except Exception:
            pass
        time.sleep(0.5)
th = threading.Thread(target=sample, daemon=True); th.start()
ld = make_loader(df, batch_size=BATCH, shuffle=True, num_workers={best_nw}, cache=True, **kw)
t0 = time.perf_counter(); n = 0
for sol_b, slv_b, tg in ld:
    sol_d, slv_d = sol_b.to(dev), slv_b.to(dev)
    tg_d = {{k: (v.to(dev) if torch.is_tensor(v) else v) for k, v in tg.items()}}
    c = dict(solvent_type=tg_d.get("solvent_type"), solute_morgan_fp=tg_d.get("solute_morgan_fp"),
             solvent_morgan_fp=tg_d.get("solvent_morgan_fp"),
             solute_descriptors=tg_d.get("solute_descriptors"),
             solvent_descriptors=tg_d.get("solvent_descriptors"),
             ionic_features=tg_d.get("ionic_features"))
    out, _ = model(sol_d, slv_d, tg_d["T"], **c, targets=tg_d, return_intermediates=True)
    out["ln_x2"].sum().backward(); opt.step(); opt.zero_grad(set_to_none=True)
    n += int(sol_b.num_graphs)
torch.cuda.synchronize(); dt = time.perf_counter() - t0
stop.set(); th.join(timeout=2)
res["full_pipeline"] = {{"rows_per_s": n / dt, "gpu_util_mean": float(np.mean(util)) if util else None,
                        "gpu_util_p90": float(np.percentile(util, 90)) if util else None,
                        "n_samples": len(util)}}
print(f"  полный цикл:            {{n/dt:7.0f}} строк/с, загрузка GPU "
      f"{{res['full_pipeline']['gpu_util_mean']:.0f}}% (p90 {{res['full_pipeline']['gpu_util_p90']:.0f}}%)")

ceil_ = res["compute_ceiling"]["rows_per_s"]; full = res["full_pipeline"]["rows_per_s"]
res["headroom"] = ceil_ / full
print(f"\\nЗАПАС: потолок / полный цикл = {{ceil_/full:.1f}}x")
if ceil_ / full > 2:
    print("  -> видеокарта ГОЛОДАЕТ: узкое место в тракте данных, вторая T4 не поможет")
else:
    print("  -> узкое место в самом счёте: вторая T4 имеет смысл")
(OUT / "bottleneck.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
print("\\nзаписано: /kaggle/working/out/bottleneck.json")

# УБИРАЕМ КОПИЮ РЕПОЗИТОРИЯ ИЗ ВЫГРУЗКИ. STAGE копирует 495 файлов в /kaggle/working/repo, и
# kaggle kernels output тянет их все -- на этом выгрузка обрывалась, не доходя до лога.
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
    ap.add_argument("--rows", type=int, default=12000)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--workers", type=int, nargs="+", default=[0, 2, 4])
    ap.add_argument("--best-nw", type=int, default=4)
    a = ap.parse_args()
    nb = {"cells": [cell(ENV), cell(INSTALL), cell(STAGE),
                    cell(BODY.format(rows=a.rows, batch=a.batch, steps=a.steps,
                                     workers=tuple(a.workers), best_nw=a.best_nw))],
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                      "name": "python3"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf8")
    print(f"записан {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
