#!/usr/bin/env python
"""Зонд: даёт ли вторая T4 выигрыш при ЗАДАЧНОМ параллелизме (два процесса, две карты).

ЗАЧЕМ, И ЧЕМ ЭТО ОТЛИЧАЕТСЯ ОТ УЖЕ ОТВЕРГНУТОГО. Данные параллельно делить бессмысленно:
DataParallel режет батч между картами, но не уменьшает число запусков ядер, которые обязан
выдать единственный питоновский поток, а шаг ограничен именно выдачей -- 195 мс при батче
64, из которых GPU занята меньше четверти (results/bridge_workers_ab/summary.json). Две
карты в одном процессе дали бы две простаивающие карты вместо одной.

ЗАДАЧНЫЙ параллелизм -- другое дело: два НЕЗАВИСИМЫХ процесса, по одному на карту, каждый со
своим потоком выдачи. За дефицитный внутри процесса ресурс они не конкурируют. Они
конкурируют за ядра, и вот тут цифра из документации Kaggle решает всё: режим T4 x2 даёт
2 Nvidia Tesla T4, но **4 CPU cores и 29 ГБ RAM** -- то есть обе карты сидят на тех же
четырёх ядрах.

Бюджет на процесс -- примерно одно ядро на выдачу плюс воркеры загрузчика. При двух
воркерах на процесс это 2 главных + 4 воркера = 6 процессов на 4 ядра, то есть
передподписка; а передподписка на этой машине уже дала ОДИН замеренный обвал в 40 раз
(плечо "новый мост, воркеров 4": 3631.7 мс/шаг против 264.8 при нуле воркеров). Поэтому
мерятся три конфигурации, а не одна.

ДЕФЕКТ УСТРОЙСТВА, НАЙДЕННЫЙ ПОСЛЕ ПРОГОНА 2026-10-03, и он обесценивает парные цифры.
Процессы получают фиксированное число ЭПОХ, а не фиксированное окно по стене, поэтому
закончивший первым оставляет второму машину посвободнее, и наклонная цена шага описывает
смесь конкурентного и одиночного режима. Видно прямо в результате
(results/dualgpu_probe/summary.json): в каждом парном плече карты расходятся в 1.15-1.80
раза, хотя железо одинаковое. Считать по стене тоже нельзя -- на коротком зонде она съедена
компиляцией и сборкой загрузчика: 1472 строки за 60 с, то есть 24 строки/с против устойчивых
376. Чтобы получить ответ, оба процесса должны крутиться ФИКСИРОВАННОЕ ОКНО ПО СТЕНЕ и
останавливаться по времени, а не по числу эпох.

Устойчиво из этого прогона только одиночное плечо: 170 мс/шаг при двух воркерах (один
процесс, перекрытия нет), что воспроизводит прежние 195 мс в пределах известного
межмашинного разброса.

ЗАЧЕМ ФАЙЛ ВСЁ РАВНО ОСТАВЛЕН. Вопрос, который он ставил, оказался НЕНУЖНЫМ: две сессии
Kaggle идут одновременно (проверено 2026-10-03 -- tgnn-solv-e2 и tgnn-solv-dualgpu в статусе
RUNNING в один момент), а у каждого ядра СВОИ 4 ядра CPU и 29 ГБ. Значит раздельные ядра
дают параллелизм без конкуренции вообще, по одному плечу на ядро, 9.1 ч на плечо при той же
сумме квоты -- строго лучше, чем две карты на четырёх общих ядрах. Переделывать зонд стоит
только если раздельные ядра окажутся ограничены (предел числа сессий, отдельная квота).

ЧТО СЧИТАЕТСЯ ОТВЕТОМ. Метрика -- время шага ОДНОГО процесса, а не суммарная пропускная
способность: суммарная вырастет почти всегда и ответа не содержит. Если при двух
одновременных процессах время шага каждого остаётся около одиночного, пропускная
способность удваивается и вторая карта имеет смысл. Если время шага удваивается, выигрыша
нет вовсе -- процессы просто поделили те же ядра. Если обваливается кратно, это
передподписка, и конфигурацию надо отбросить.

Рабочий скрипт пишется из ноутбука в /kaggle/working, а не кладётся в пакет: зонд тогда
работает против УЖЕ загруженной версии датасета и не требует её пересборки.

    python scripts/kaggle/make_dualgpu_notebook.py --out /tmp/kaggle_dg/probe.ipynb
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from make_notebook import ENV, INSTALL, STAGE  # noqa: E402

# Рабочий скрипт: N настоящих шагов train_epoch на заданной карте, цена шага по наклону.
WORKER = r'''
import argparse, dataclasses, inspect, json, os, sys, time
import pandas as pd, torch, yaml

ap = argparse.ArgumentParser()
ap.add_argument("--device", required=True)
ap.add_argument("--workers", type=int, required=True)
ap.add_argument("--batch", type=int, default=64)
ap.add_argument("--n-short", type=int, default=5)
ap.add_argument("--n-long", type=int, default=15)
ap.add_argument("--out", required=True)
ap.add_argument("--repo", required=True)
a = ap.parse_args()

os.chdir(a.repo)
sys.path.insert(0, "src")
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer
from tgnn_solv.model import TGNNSolv
from tgnn_solv.trainer import TGNNSolvTrainer
from tgnn_solv.data.dataset import make_loader

y = yaml.safe_load(open("configs/cosmo_sac.yaml")); flat = {}
for k, v in y.items():
    flat.update(v if isinstance(v, dict) else {k: v})
F = {f.name for f in dataclasses.fields(TGNNSolvConfig)}
cfg = TGNNSolvConfig(**{k: v for k, v in flat.items() if k in F})
FULL = pd.read_csv("notebooks/data/processed/train.csv", low_memory=False)
sig = set(inspect.signature(make_loader).parameters)
KW = {k: getattr(cfg, k) for k in (sig & F) - {"batch_size","shuffle","num_workers","cache"}}
if not getattr(cfg, "use_source_uncertainty_weights", False):
    KW["source_uncertainty_csv"] = ""        # зеркалим train.py:841

CosmoSacLayer._segment_ln_gamma = torch.compile(
    CosmoSacLayer._segment_ln_gamma, dynamic=True)

dev = torch.device(a.device)
ld0 = make_loader(FULL.head(a.batch * 2), batch_size=a.batch, shuffle=False,
                  num_workers=0, cache=True, **KW)
sol_b, _, _ = next(iter(ld0))
torch.manual_seed(0)
model = TGNNSolv(node_feat_dim=sol_b.x.shape[1],
                 edge_feat_dim=sol_b.edge_attr.shape[1], cfg=cfg).to(dev)
trainer = TGNNSolvTrainer(model, cfg)
opt = torch.optim.AdamW(model.parameters(), lr=1e-4)

def epoch(steps):
    ld = make_loader(FULL.head(a.batch * steps), batch_size=a.batch, shuffle=True,
                     num_workers=a.workers, cache=True, drop_last=True, **KW)
    t0 = time.perf_counter()
    trainer.train_epoch(ld, opt, phase=2, epoch=0, compute_mono=False)
    torch.cuda.synchronize(dev)
    return time.perf_counter() - t0

epoch(3)                                      # прогрев и компиляция
torch.cuda.synchronize(dev)
t_s = epoch(a.n_short)
t_l = epoch(a.n_long)
marginal = (t_l - t_s) / (a.n_long - a.n_short)
json.dump({"device": a.device, "workers": a.workers, "s_per_step": marginal,
           "rows_per_s": a.batch / marginal, "t_short": t_s, "t_long": t_l,
           "peak_gb": torch.cuda.max_memory_allocated(dev) / 2**30},
          open(a.out, "w"))
print(f"[{a.device} w={a.workers}] {marginal*1000:.1f} мс/шаг", flush=True)
'''

BODY = r'''
import json, os, subprocess, sys, time
from pathlib import Path
import torch

OUT = Path("/kaggle/working/out"); OUT.mkdir(parents=True, exist_ok=True)
REPO = os.getcwd()
NGPU = torch.cuda.device_count()
print(f"CPU: {os.cpu_count()} | GPU: {NGPU} x "
      f"{torch.cuda.get_device_name(0) if NGPU else 'нет'}")
assert NGPU >= 2, ("нужен режим T4 x2: один ускоритель задачный параллелизм проверить не "
                   f"даёт (видно {NGPU})")

WORKER_SRC = Path("/kaggle/working/dual_worker.py")
WORKER_SRC.write_text(__WORKER__)
print("рабочий скрипт записан:", WORKER_SRC)

res = {"hw": {"cpu_count": os.cpu_count(), "n_gpu": NGPU,
              "gpus": [torch.cuda.get_device_name(i) for i in range(NGPU)],
              "torch": torch.__version__}}

def launch(devices, workers, tag):
    """Запустить по процессу на каждую карту ОДНОВРЕМЕННО и собрать их времена шага."""
    procs, outs = [], []
    for d in devices:
        o = OUT / f"{tag}_{d.replace(':','')}.json"
        if o.exists():
            o.unlink()
        outs.append(o)
        procs.append(subprocess.Popen(
            [sys.executable, "-u", str(WORKER_SRC), "--device", d,
             "--workers", str(workers), "--batch", "__BATCH__",
             "--n-short", "__N_SHORT__", "--n-long", "__N_LONG__",
             "--out", str(o), "--repo", REPO],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True))
    logs = []
    for p in procs:
        logs.append(p.communicate()[0] or "")
    got = []
    for o, lg, p in zip(outs, logs, procs):
        if o.exists():
            got.append(json.loads(o.read_text()))
        else:
            tail = "\n".join(lg.strip().splitlines()[-6:])
            got.append({"error": f"rc={p.returncode}", "tail": tail[:600]})
    return got

#                 метка                        карты              воркеров
PLAN = [("одиночно, cuda:0, воркеров 2",   ["cuda:0"],            2),
        ("одиночно, cuda:0, воркеров 1",   ["cuda:0"],            1),
        ("две карты, воркеров 0",          ["cuda:0", "cuda:1"],  0),
        ("две карты, воркеров 1",          ["cuda:0", "cuda:1"],  1),
        ("две карты, воркеров 2",          ["cuda:0", "cuda:1"],  2)]

res["runs"] = {}
for tag, devs, w in PLAN:
    t0 = time.perf_counter()
    got = launch(devs, w, tag.replace(" ", "_").replace(",", ""))
    wall = time.perf_counter() - t0
    ok = [g for g in got if "s_per_step" in g]
    res["runs"][tag] = {"per_process": got, "wall_s": wall, "n_proc": len(devs),
                        "workers": w}
    if ok:
        slowest = max(g["s_per_step"] for g in ok)
        total_rows = sum(g["rows_per_s"] for g in ok)
        res["runs"][tag].update({"slowest_s_per_step": slowest,
                                 "total_rows_per_s": total_rows})
        each = "  ".join(f"{g['device']}={g['s_per_step']*1000:.0f}мс" for g in ok)
        print(f"  {tag:<30} {each:<34} суммарно {total_rows:6.0f} строк/с")
    else:
        print(f"  {tag:<30} ВСЕ ПРОЦЕССЫ УПАЛИ")
        for g in got:
            print("    ", str(g)[:300])

# --- вердикт: время шага ОДНОГО процесса, а не суммарная пропускная способность ---
solo = res["runs"].get("одиночно, cuda:0, воркеров 1", {}).get("slowest_s_per_step")
dual = res["runs"].get("две карты, воркеров 1", {}).get("slowest_s_per_step")
if solo and dual:
    res["verdict"] = {"solo_s_per_step": solo, "dual_s_per_step": dual,
                      "per_process_slowdown": dual / solo,
                      "throughput_gain": 2.0 * solo / dual}
    print(f"\nпри одном воркере: одиночно {solo*1000:.0f} мс/шаг, вдвоём "
          f"{dual*1000:.0f} мс/шаг -> замедление процесса x{dual/solo:.2f}, "
          f"выигрыш пропускной способности x{2*solo/dual:.2f}")
    if dual / solo < 1.3:
        print("  -> вторая карта РАБОТАЕТ: процессы почти не мешают друг другу")
    elif dual / solo < 1.8:
        print("  -> частичный выигрыш: ядра поделены, но суммарно всё ещё быстрее")
    else:
        print("  -> выигрыша нет: процессы просто поделили те же четыре ядра")

best = max((v for v in res["runs"].values() if "total_rows_per_s" in v),
           key=lambda v: v["total_rows_per_s"], default=None)
if best:
    steps_ep = 111724 // __BATCH__
    res["best"] = dict(best)
    # Плечо-часы на ПЛЕЧО при лучшей конфигурации: если плеч столько же, сколько процессов,
    # они идут одновременно, поэтому делим на число процессов.
    h = best["slowest_s_per_step"] * steps_ep * 110 / 3600
    res["best"]["arm_hours_per_arm"] = h
    res["best"]["arms_in_parallel"] = best["n_proc"]
    print(f"\nлучшая конфигурация: {best['n_proc']} процесс(ов), воркеров "
          f"{best['workers']}, {best['total_rows_per_s']:.0f} строк/с суммарно")
    print(f"  плечо {h:.1f} ч, и таких плеч идёт {best['n_proc']} одновременно "
          f"-> пара за {h:.1f} ч вместо {2*h:.1f}" if best["n_proc"] > 1 else
          f"  плечо {h:.1f} ч, по одному")

(OUT / "dualgpu.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
print("\nзаписано: /kaggle/working/out/dualgpu.json")

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
    ap.add_argument("--n-short", type=int, default=5)
    ap.add_argument("--n-long", type=int, default=15)
    a = ap.parse_args()
    if a.n_long <= a.n_short:
        ap.error("--n-long должен быть больше --n-short: цена шага берётся по наклону")

    body = BODY.replace("__WORKER__", repr(WORKER))
    for tok, val in (("__BATCH__", str(a.batch)),
                     ("__N_SHORT__", str(a.n_short)),
                     ("__N_LONG__", str(a.n_long))):
        assert tok in body, tok
        body = body.replace(tok, val)
    left = [t for t in ("__WORKER__", "__BATCH__", "__N_SHORT__", "__N_LONG__") if t in body]
    assert not left, f"не подставлены: {left}"

    nb = {"cells": [cell(ENV), cell(INSTALL), cell(STAGE), cell(body)],
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3",
                                      "language": "python"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(nb, ensure_ascii=False, indent=1))
    print(f"ноутбук: {a.out}  (5 конфигураций, батч {a.batch}, эпохи "
          f"{a.n_short}/{a.n_long}; нужен режим T4 x2)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
