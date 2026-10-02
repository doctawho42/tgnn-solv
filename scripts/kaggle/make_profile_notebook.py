#!/usr/bin/env python
"""Профилировщик НАСТОЯЩЕГО шага обучения: куда уходят остальные 70% и что даёт крупный батч.

ПОЧЕМУ ЭТОТ ФАЙЛ ПЕРЕПИСАН НА train_epoch. Первая его версия, как и
make_speedup_notebook.py, мерила самодельный шаг: model(...) -> ln_x2.sum().backward() ->
opt.step(). В нём НЕТ ни TGNNSolvLoss (одна взвешенная сумма примерно из 30 слагаемых), ни
clip_grad_norm_ (trainer.py:1544, в реальном шаге безусловный), ни _move_batch_to_device, ни
загрузчика. То есть 220.4 мс и ускорение 1.75x из results/solver_speedup_ab/summary.json
измерены на поверхности, которая НЕ равна шагу обучения, и делить 26.9 плечо-часов на 1.75
нельзя. Это пятый случай того самого дефекта, который в проекте уже записан под именем
"мерь ту поверхность, которой будешь пользоваться", и лечится он здесь не поправкой к
самодельному шагу, а отказом от него: ниже вызывается TGNNSolvTrainer.train_epoch, то есть
ровно тот код, который крутится на GPU-прогоне.

ДВЕ ДЛИНЫ ЭПОХИ, А НЕ ОДНА. train_epoch несёт постоянные накладные (сборка загрузчика,
прогрев, сводка в конце), которые при коротком прогоне исказили бы цену шага. Поэтому каждая
точка мерится на двух длинах, и берётся НАКЛОН: (t_long - t_short) / (n_long - n_short). Это
предельная цена шага, нечувствительная к постоянной части, и именно её надо умножать на
число шагов, когда считаешь плечо-часы.

РЕЖИМ МОНОТОННОСТИ МЕРИТСЯ ОТДЕЛЬНО. loss.py:1194 вызывает model(...) заново, то есть член
монотонности добавляет к шагу ещё один полный прогон сети. Но включается он не всегда:
trainer.py:1962 ставит compute_mono = phase >= 2 and epoch % 5 == 0, а вес mono на фазе 2 в
configs/cosmo_sac.yaml равен 0.0 (ненулевой он только на фазе 3). Значит на фазе 2 это
каждая пятая эпоха, и считать её ценой каждого шага было бы завышением. Мерятся оба режима,
а в сводку идёт средневзвешенное 4:1.

ЧТО ЭТОТ ПРОГОН РАЗЛИЧАЕТ, А НЕ ПРОСТО С ЧЕМ СОГЛАСУЕТСЯ

  (1) СВЁРТКА ПО БАТЧУ 64..512 плюс загрузка карты и N_max. Решающий замер. Если шаг
      ограничен выдачей работы с CPU, время шага от батча почти не растёт, а строки в
      секунду растут кратно. Если растёт время -- упираемся в арифметику, и борьба с
      диспетчеризацией закончена. N_max (максимум атомов в графе батча) печатается рядом,
      потому что без него нельзя отличить "батч вырос" от "padding вырос": cross-attention
      идёт по плотному представлению и стоит B x N_max^2 x D.
  (2) РАЗЛОЖЕНИЕ СЧЁТА ДИСПАТЧЕЙ по батчу: профиль снимается при 64 и при 512, и сравнивается
      не время, а число запусков по операциям. Операции в питоновских циклах по графам
      обязаны вырасти в 8 раз, операции на шаг -- остаться на месте. Это разрезает бюджет на
      два класса без единой правки кода и отличает "цена в плюмбинге" от нулевой гипотезы
      "цена размазана по телу сети", чего топ-по-времени не делает.
  (3) СЧЁТЧИК СИНХРОНИЗАЦИЙ через set_sync_debug_mode("warn"), с сохранением ТЕКСТОВ. Прямая
      проверка догадки, что булева индексация на CUDA синхронизируется через nonzero: она
      выведена из чтения исходников и на карте не наблюдена.
  (4) ТОП ПО ЧИСЛУ ЗАПУСКОВ отдельно от топа по времени. Для модели, ограниченной
      задержкой, первый важнее: тысяча ядер по 20 микросекунд не попадёт во второй.
  (5) СЧЁТЧИКИ torch._dynamo: сколько рекомпиляций и разрывов графа даёт dynamic=True на
      батчах разной длины. Если их много, выигрыш компиляции съедается.

    python scripts/kaggle/make_profile_notebook.py --out /tmp/kaggle_pr/profile.ipynb
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from make_notebook import ENV, INSTALL, STAGE  # noqa: E402

# Подстановка через уникальные токены, а не str.format: тело полно словарей и f-строк, и
# экранирование фигурных скобок в прошлой версии уже стоило одного упавшего ядра.
BODY = r'''
import json, os, subprocess, sys, threading, time, warnings
from collections import Counter
from pathlib import Path
import dataclasses
import numpy as np, pandas as pd, torch, yaml

OUT = Path("/kaggle/working/out"); OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, "src")
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer
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
assert not cfg.solver_cosmo_break_on_tol, "ожидался пакет с коммита a8b5bff или новее"
print("плечо: configs/cosmo_sac.yaml |", cfg.activity_model,
      "| n_iter_train", cfg.n_iter_train, "| сегментных итераций", cfg.cosmo_sac_gamma_iter_train)

FULL = pd.read_csv("notebooks/data/processed/train.csv", low_memory=False)
VAL = pd.read_csv("notebooks/data/processed/val.csv", low_memory=False)
print(f"корпус: train {len(FULL)} строк, val {len(VAL)}")

COMPILE_SEGMENT = __COMPILE_SEGMENT__
if COMPILE_SEGMENT:
    CosmoSacLayer._segment_ln_gamma = torch.compile(
        CosmoSacLayer._segment_ln_gamma, dynamic=True)
    print("сегментный цикл скомпилирован (как в выигравшем плече A/B)")

def loader_kwargs():
    import inspect
    sig = set(inspect.signature(make_loader).parameters)
    kw = {k: getattr(cfg, k) for k in (sig & FIELDS)
          - {"batch_size", "shuffle", "num_workers", "cache"}}
    if not getattr(cfg, "use_source_uncertainty_weights", False):
        kw["source_uncertainty_csv"] = ""   # зеркалим train.py:841
    return kw

KW = loader_kwargs()

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

def build(batch):
    """Настоящий тренер на настоящей модели; возвращает ещё и N_max батча."""
    ld = make_loader(FULL.head(batch * 2), batch_size=batch, shuffle=False,
                     num_workers=0, cache=True, **KW)
    sol_b, _, _ = next(iter(ld))
    n_max = int(sol_b.ptr.diff().max()) if hasattr(sol_b, "ptr") else -1
    torch.manual_seed(0)
    model = TGNNSolv(node_feat_dim=sol_b.x.shape[1],
                     edge_feat_dim=sol_b.edge_attr.shape[1], cfg=cfg).to("cuda")
    trainer = TGNNSolvTrainer(model, cfg)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    return model, trainer, opt, n_max

def real_epoch(trainer, opt, batch, steps, mono, workers=0):
    """ОДНА эпоха настоящего train_epoch на ровно `steps` шагах."""
    df = FULL.head(batch * steps)
    ld = make_loader(df, batch_size=batch, shuffle=True, num_workers=workers,
                     cache=True, drop_last=True, **KW)
    t0 = time.perf_counter()
    trainer.train_epoch(ld, opt, phase=2, epoch=0, compute_mono=mono)
    torch.cuda.synchronize()
    return time.perf_counter() - t0

# ---------- (1) СВЁРТКА ПО БАТЧУ, цена шага по НАКЛОНУ двух длин эпохи ----------
print("\n(1) настоящий train_epoch: свёртка по батчу, цена шага по наклону")
print("    (две длины эпохи снимают постоянные накладные train_epoch)")
N_SHORT, N_LONG = __N_SHORT__, __N_LONG__
res["batch_sweep"] = {}
for batch in __BATCHES__:
    try:
        model, trainer, opt, n_max = build(batch)
        real_epoch(trainer, opt, batch, 3, mono=False)            # прогрев
        torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
        util, stop, th = gpu_sampler()
        t_short = real_epoch(trainer, opt, batch, N_SHORT, mono=False)
        t_long = real_epoch(trainer, opt, batch, N_LONG, mono=False)
        stop.set(); th.join(timeout=2)
        marginal = (t_long - t_short) / (N_LONG - N_SHORT)
        fixed = t_short - marginal * N_SHORT
        peak = torch.cuda.max_memory_allocated() / 2**30
        res["batch_sweep"][batch] = {
            "s_per_step_marginal": marginal, "rows_per_s": batch / marginal,
            "epoch_fixed_overhead_s": fixed, "n_max_atoms": n_max,
            "gpu_util_mean": (float(np.mean(util)) if util else None),
            "gpu_util_p90": (float(np.percentile(util, 90)) if util else None),
            "peak_gb": peak, "t_short_s": t_short, "t_long_s": t_long}
        print(f"  батч {batch:>4}: {marginal*1000:7.1f} мс/шаг  {batch/marginal:7.0f} строк/с"
              f"  GPU {(np.mean(util) if util else 0):3.0f}%  N_max {n_max:>3}"
              f"  пик {peak:.2f} ГБ  постоянная часть {fixed:+.2f} с")
        del model, trainer, opt
        torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
    except RuntimeError as e:
        res["batch_sweep"][batch] = {"error": str(e)[:300]}
        print(f"  батч {batch:>4}: ОШИБКА {str(e)[:140]}")
        torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()

ok = {k: v for k, v in res["batch_sweep"].items() if "s_per_step_marginal" in v}
if len(ok) >= 2:
    lo, hi = min(ok), max(ok)
    tr = ok[hi]["s_per_step_marginal"] / ok[lo]["s_per_step_marginal"]
    rr = ok[hi]["rows_per_s"] / ok[lo]["rows_per_s"]
    res["latency_verdict"] = {"batch_ratio": hi / lo, "step_time_ratio": tr,
                              "throughput_ratio": rr,
                              "gpu_util_lo": ok[lo]["gpu_util_mean"],
                              "gpu_util_hi": ok[hi]["gpu_util_mean"],
                              "n_max_lo": ok[lo]["n_max_atoms"], "n_max_hi": ok[hi]["n_max_atoms"]}
    print(f"\n  батч x{hi/lo:.0f}: время шага x{tr:.2f}, строк/с x{rr:.2f}, "
          f"GPU {ok[lo]['gpu_util_mean']:.0f}% -> {ok[hi]['gpu_util_mean']:.0f}%, "
          f"N_max {ok[lo]['n_max_atoms']} -> {ok[hi]['n_max_atoms']}")
    if ok[hi]["gpu_util_mean"] and ok[hi]["gpu_util_mean"] > 55:
        print("  -> карта ЗАГРУЗИЛАСЬ: фронт диспетчеризации закрыт, достаточно поднять батч")
    elif tr > 0.5 * (hi / lo):
        print("  -> время шага растёт с батчем: цена PER-GRAPH на хосте, батч её не амортизирует")
    else:
        print("  -> всё ещё ограничен ЗАДЕРЖКОЙ при низкой загрузке: цена фиксированная на шаг")

# ---------- (2) РЕЖИМ МОНОТОННОСТИ: лишний прогон модели, но раз в пять эпох ----------
print("\n(2) цена члена монотонности (loss.py:1194 зовёт model заново)")
res["mono"] = {}
try:
    model, trainer, opt, _ = build(64)
    real_epoch(trainer, opt, 64, 3, mono=False)
    torch.cuda.synchronize()
    out = {}
    for mono in (False, True):
        s = real_epoch(trainer, opt, 64, N_SHORT, mono=mono)
        lg = real_epoch(trainer, opt, 64, N_LONG, mono=mono)
        out[mono] = (lg - s) / (N_LONG - N_SHORT)
        print(f"  compute_mono={str(mono):<5}: {out[mono]*1000:7.1f} мс/шаг")
    # trainer.py:1962 -- каждая пятая эпоха фазы 2, поэтому 4:1, а не 1:1
    blended = 0.8 * out[False] + 0.2 * out[True]
    res["mono"] = {"s_per_step_no_mono": out[False], "s_per_step_with_mono": out[True],
                   "overhead_x": out[True] / out[False],
                   "blended_4to1_s_per_step": blended}
    print(f"  надбавка x{out[True]/out[False]:.2f}; средневзвешенное 4:1 = {blended*1000:.1f} мс/шаг")
    del model, trainer, opt; torch.cuda.empty_cache()
except Exception as e:
    res["mono"] = {"error": f"{type(e).__name__}: {e}"[:300]}
    print(f"  ОШИБКА: {type(e).__name__}: {e}"[:220])

# ---------- (3) СИНХРОНИЗАЦИИ ХОСТА за шаг, с текстами ----------
print("\n(3) синхронизации хоста на НАСТОЯЩЕМ шаге")
res["host_syncs"] = {}
try:
    model, trainer, opt, _ = build(64)
    real_epoch(trainer, opt, 64, 3, mono=False)
    torch.cuda.synchronize()
    NS = 4
    torch.cuda.set_sync_debug_mode("warn")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        real_epoch(trainer, opt, 64, NS, mono=False)
    torch.cuda.set_sync_debug_mode("default")
    msgs = [str(x.message) for x in w]
    syncs = [m for m in msgs if "sync" in m.lower()]
    res["host_syncs"] = {"steps": NS, "n_warnings_total": len(msgs),
                         "n_sync_warnings": len(syncs),
                         "per_step": len(syncs) / NS,
                         "by_message": {m: c / NS for m, c in
                                        Counter(s[:200] for s in syncs).most_common(25)},
                         "sample_texts": syncs[:5]}
    print(f"  за {NS} шагов: предупреждений {len(msgs)}, про синхронизацию {len(syncs)}"
          f" -> {len(syncs)/NS:.1f} на шаг")
    for m, c in Counter(s[:150] for s in syncs).most_common(12):
        print(f"    {c/NS:6.1f}/шаг  {m}")
    if not syncs:
        print("    ни одной -- гипотеза про .item() и nonzero на пути шага МЕРТВА")
    del model, trainer, opt; torch.cuda.empty_cache()
except Exception as e:
    torch.cuda.set_sync_debug_mode("default")
    res["host_syncs"] = {"error": f"{type(e).__name__}: {e}"[:300]}
    print(f"  ОШИБКА: {type(e).__name__}: {e}"[:220])

# ---------- (4) ПРОФИЛЬ при ДВУХ батчах: разложение счёта диспатчей ----------
# Операции в питоновских циклах по графам обязаны вырасти пропорционально батчу,
# операции на шаг -- остаться на месте. Это и есть разрез бюджета на два класса.
print("\n(4) профиль при двух батчах: что растёт с батчем, а что нет")
res["profile"] = {}
try:
    from torch.profiler import ProfilerActivity, profile
    def cuda_us(e):
        return float(getattr(e, "self_device_time_total",
                             getattr(e, "self_cuda_time_total", 0.0)))
    for batch in __PROFILE_BATCHES__:
        model, trainer, opt, n_max = build(batch)
        real_epoch(trainer, opt, batch, 3, mono=False)
        torch.cuda.synchronize()
        NP = __PROFILE_STEPS__
        with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
                     record_shapes=True, with_stack=False) as prof:
            real_epoch(trainer, opt, batch, NP, mono=False)
        ka = list(prof.key_averages())
        def rows(key, n=30):
            return [{"name": e.key, "count": e.count / NP,
                     "self_cuda_us": cuda_us(e) / NP,
                     "self_cpu_us": float(e.self_cpu_time_total) / NP}
                    for e in sorted(ka, key=key, reverse=True)[:n]]
        tot_cpu = sum(float(e.self_cpu_time_total) for e in ka) / NP
        tot_cuda = sum(cuda_us(e) for e in ka) / NP
        n_launch = sum(e.count for e in ka if cuda_us(e) > 0) / NP
        res["profile"][batch] = {
            "n_max_atoms": n_max, "steps": NP,
            "totals_per_step": {"self_cpu_us": tot_cpu, "self_cuda_us": tot_cuda,
                                "cuda_op_launches": n_launch,
                                "cpu_over_cuda": (tot_cpu / tot_cuda if tot_cuda else None)},
            "top_by_launch_count": rows(lambda e: e.count),
            "top_by_cuda_time": rows(cuda_us),
            "counts_by_op": {e.key: e.count / NP for e in ka if e.count / NP >= 4}}
        print(f"\n  батч {batch} (N_max {n_max}): CPU {tot_cpu/1000:.1f} мс, GPU {tot_cuda/1000:.1f} мс,"
              f" отношение {(tot_cpu/tot_cuda if tot_cuda else 0):.2f}x, диспатчей ~{n_launch:.0f}")
        print("    топ-10 ПО ЧИСЛУ ЗАПУСКОВ:")
        for r in res["profile"][batch]["top_by_launch_count"][:10]:
            print(f"      {r['count']:8.0f}x {r['self_cuda_us']/1000:7.2f} мс  {r['name'][:58]}")
        print("    топ-10 ПО ВРЕМЕНИ НА GPU:")
        for r in res["profile"][batch]["top_by_cuda_time"][:10]:
            print(f"      {r['self_cuda_us']/1000:7.2f} мс {r['count']:8.0f}x  {r['name'][:58]}")
        del model, trainer, opt; torch.cuda.empty_cache()

    pbs = [b for b in res["profile"] if "counts_by_op" in res["profile"][b]]
    if len(pbs) >= 2:
        a, b = min(pbs), max(pbs)
        ca, cb = res["profile"][a]["counts_by_op"], res["profile"][b]["counts_by_op"]
        ratio = b / a
        scaling = []
        for op in set(ca) | set(cb):
            na, nb = ca.get(op, 0.0), cb.get(op, 0.0)
            if na >= 8:
                scaling.append({"op": op, "count_lo": na, "count_hi": nb,
                                "growth": (nb / na if na else None),
                                "class": ("per_graph" if na and nb / na > 0.6 * ratio
                                          else "per_step" if na and nb / na < 1.6 else "смешанный")}) 
        scaling.sort(key=lambda r: -r["count_lo"])
        res["dispatch_scaling"] = {"batch_lo": a, "batch_hi": b, "batch_ratio": ratio,
                                   "ops": scaling[:40]}
        pg = sum(r["count_lo"] for r in scaling if r["class"] == "per_graph")
        ps = sum(r["count_lo"] for r in scaling if r["class"] == "per_step")
        tot = sum(r["count_lo"] for r in scaling) or 1
        res["dispatch_scaling"]["share_per_graph"] = pg / tot
        res["dispatch_scaling"]["share_per_step"] = ps / tot
        print(f"\n  РАЗЛОЖЕНИЕ при батче x{ratio:.0f}: per-graph {pg:.0f} ({pg/tot:.0%}),"
              f" per-step {ps:.0f} ({ps/tot:.0%}) из {tot:.0f} учтённых диспатчей")
        print("    растут с батчем сильнее всего:")
        for r in sorted([r for r in scaling if r["growth"]], key=lambda r: -r["growth"])[:8]:
            print(f"      x{r['growth']:5.1f}  {r['count_lo']:7.0f} -> {r['count_hi']:7.0f}  {r['op'][:50]}")
        print("    НЕ растут (цена на шаг):")
        for r in [r for r in scaling if r["class"] == "per_step"][:8]:
            print(f"      x{(r['growth'] or 0):5.1f}  {r['count_lo']:7.0f} -> {r['count_hi']:7.0f}  {r['op'][:50]}")
except Exception as e:
    res["profile"]["error"] = f"{type(e).__name__}: {e}"[:500]
    print(f"  ОШИБКА: {type(e).__name__}: {e}"[:300])

# ---------- (5) СЧЁТЧИКИ КОМПИЛЯТОРА ----------
try:
    import torch._dynamo as dyn
    c = {k: dict(v) if hasattr(v, "items") else v for k, v in dyn.utils.counters.items()}
    res["dynamo_counters"] = json.loads(json.dumps(c, default=str))
    gb = sum(c.get("graph_break", {}).values()) if isinstance(c.get("graph_break"), dict) else 0
    print(f"\n(5) dynamo: разрывов графа {gb}, разделов счётчиков {len(c)}")
    if "stats" in c:
        print("    stats:", c["stats"])
except Exception as e:
    res["dynamo_counters"] = {"error": str(e)[:200]}

(OUT / "profile.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
print("\nзаписано: /kaggle/working/out/profile.json")

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
    ap.add_argument("--batches", default="64,128,256,512")
    ap.add_argument("--profile-batches", default="64,512")
    ap.add_argument("--n-short", type=int, default=6)
    ap.add_argument("--n-long", type=int, default=18)
    ap.add_argument("--profile-steps", type=int, default=4)
    ap.add_argument("--no-compile-segment", action="store_true")
    a = ap.parse_args()

    if a.n_long <= a.n_short:
        ap.error("--n-long должен быть больше --n-short: цена шага берётся по наклону")
    batches = [int(x) for x in a.batches.split(",")]
    pbatches = [int(x) for x in a.profile_batches.split(",")]
    # Подстановка по точным токенам. Проверять "нет ли вообще __" нельзя: в теле законно
    # живут torch.__version__ и type(e).__name__, и такой охранник даёт ложную тревогу.
    tokens = {
        "__BATCHES__": repr(batches),
        "__PROFILE_BATCHES__": repr(pbatches),
        "__N_SHORT__": str(a.n_short),
        "__N_LONG__": str(a.n_long),
        "__PROFILE_STEPS__": str(a.profile_steps),
        "__COMPILE_SEGMENT__": repr(not a.no_compile_segment),
    }
    body = BODY
    for token, value in tokens.items():
        assert token in body, f"токен {token} не найден в теле"
        body = body.replace(token, value)
    left = [t for t in tokens if t in body]
    assert not left, f"не подставлены: {left}"

    nb = {"cells": [cell(ENV), cell(INSTALL), cell(STAGE), cell(body)],
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3",
                                      "language": "python"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(nb, ensure_ascii=False, indent=1))
    print(f"ноутбук: {a.out}")
    print(f"  батчи {batches}, профиль при {pbatches}, "
          f"эпохи {a.n_short}/{a.n_long} шагов (цена по наклону)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
