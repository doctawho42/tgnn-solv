#!/usr/bin/env python
"""Гейт GPU: падает на ПЕРВОЙ МИНУТЕ, если счёт фактически идёт не на карте.

ЗАЧЕМ. В этом проекте записан отказ: после смены ядра карта отваливается, а обучение
ПРОДОЛЖАЕТСЯ на ЦПУ и доходит до конца с бессмысленными числами. `torch.cuda.is_available()`
этого не ловит -- он может вернуть True, пока сама работа идёт на процессоре. Поэтому гейт
проверяет три разные вещи, и третья -- внешняя:

  1. torch видит CUDA и умеет считать на ней (реальный matmul, сверка результата);
  2. параметры тестовой модели ЛЕЖАТ на карте (`.device.type == 'cuda'`);
  3. `nvidia-smi` приписывает НАШЕМУ pid ненулевую память -- то есть процесс действительно
     присутствует на карте с точки зрения драйвера, а не только по мнению torch.

Третья проверка и есть та, которой не было: первые две живут внутри того же процесса, который
может ошибаться, а `nvidia-smi` -- независимый свидетель.

Заодно печатает провенанс, которого НЕ БЫЛО в манифестах депонированных армов: там записаны
python_version и platform, а версия torch, имя карты и драйвер -- нет, поэтому про те чекпойнты
нельзя сказать, на каком torch они обучены.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time


def nvidia_smi_memory_for_pid(pid: int) -> int | None:
    """МиБ, которые драйвер приписывает этому pid. None -- если nvidia-smi недоступен."""
    exe = shutil.which("nvidia-smi")
    if exe is None:
        return None
    try:
        out = subprocess.run(
            [exe, "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=20, check=True).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    total = 0
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2 and parts[0].isdigit() and int(parts[0]) == pid:
            try:
                total += int(parts[1])
            except ValueError:
                pass
    return total


def provenance(torch) -> dict:
    d: dict = {
        "torch": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "python": sys.version.split()[0],
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "(не задан)"),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }
    if d["device_count"]:
        d["gpu_name"] = torch.cuda.get_device_name(0)
        d["gpu_capability"] = list(torch.cuda.get_device_capability(0))
        free, tot = torch.cuda.mem_get_info(0)
        d["gpu_mem_total_gib"] = round(tot / 2**30, 2)
        d["gpu_mem_free_gib"] = round(free / 2**30, 2)
    exe = shutil.which("nvidia-smi")
    if exe:
        try:
            d["driver"] = subprocess.run(
                [exe, "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=20, check=True).stdout.strip().splitlines()[0]
        except (subprocess.SubprocessError, OSError, IndexError):
            d["driver"] = "(не прочитан)"
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-mib", type=int, default=64,
                    help="сколько МиБ драйвер обязан приписать нашему pid")
    ap.add_argument("--json-out", default=None, help="куда записать провенанс")
    ap.add_argument("--expect-commit", default=None,
                    help="префикс коммита, из которого ОЖИДАЕТСЯ запуск; иначе падаем")
    a = ap.parse_args()

    failures: list[str] = []

    # --- 0. из того ли кода мы запущены ---
    if a.expect_commit:
        try:
            head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                  timeout=20, check=True).stdout.strip()
            dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                        text=True, timeout=30, check=True).stdout.strip())
        except (subprocess.SubprocessError, OSError) as e:
            failures.append(f"git недоступен, снимок кода не подтверждён: {e}")
            head, dirty = "", False
        if head and not head.startswith(a.expect_commit):
            failures.append(f"КОД НЕ ТОТ: HEAD {head[:12]}, ожидался {a.expect_commit}")
        if dirty:
            print("  ВНИМАНИЕ: рабочее дерево ГРЯЗНОЕ -- коммит не описывает запущенный код "
                  "(именно так потерян провенанс депонированных армов)", flush=True)

    try:
        import torch
    except ImportError as e:
        print(f"ГЕЙТ ПРОВАЛЕН: torch не импортируется: {e}", flush=True)
        return 2

    prov = provenance(torch)
    print("=== провенанс ===", flush=True)
    for k, v in prov.items():
        print(f"  {k} = {v}", flush=True)

    # --- 1. torch видит карту и СЧИТАЕТ на ней ---
    if not torch.cuda.is_available():
        failures.append("torch.cuda.is_available() == False")
    else:
        t0 = time.time()
        x = torch.randn(512, 512, device="cuda")
        y = x @ x.T
        torch.cuda.synchronize()
        ref = (x.cpu() @ x.cpu().T)
        if not torch.allclose(y.cpu(), ref, atol=1e-3):
            failures.append("matmul на карте не совпал с ЦПУ-эталоном")
        print(f"  matmul на карте: {time.time()-t0:.2f} с, результат сверен с ЦПУ", flush=True)

        # --- 2. параметры модели реально на карте ---
        m = torch.nn.Linear(64, 64).cuda()
        devs = {p.device.type for p in m.parameters()}
        if devs != {"cuda"}:
            failures.append(f"параметры модели не на карте: {devs}")
        else:
            print("  параметры тестовой модели на карте: да", flush=True)

        # --- 3. ВНЕШНИЙ свидетель: драйвер видит наш pid ---
        held = torch.empty(int(96 * 2**20 / 4), device="cuda")  # ~96 МиБ, чтобы было что увидеть
        torch.cuda.synchronize()
        mib = None
        for _ in range(10):                       # драйвер обновляет список не мгновенно
            mib = nvidia_smi_memory_for_pid(os.getpid())
            if mib is not None and mib >= a.min_mib:
                break
            time.sleep(2)
        del held
        if mib is None:
            failures.append("nvidia-smi недоступен -- ВНЕШНЕГО подтверждения нет, "
                            "а именно его отсутствие дало молчаливый откат на ЦПУ")
        elif mib < a.min_mib:
            failures.append(f"драйвер приписывает нашему pid {mib} МиБ < {a.min_mib} -- "
                            "процесс на карте не присутствует")
        else:
            print(f"  nvidia-smi подтверждает: нашему pid приписано {mib} МиБ", flush=True)

    prov["gate_passed"] = not failures
    prov["failures"] = failures
    if a.json_out:
        with open(a.json_out, "w", encoding="utf8") as fh:
            json.dump(prov, fh, indent=2, ensure_ascii=False)

    if failures:
        print("\nГЕЙТ ПРОВАЛЕН:", flush=True)
        for f in failures:
            print(f"  * {f}", flush=True)
        return 1
    print("\nГЕЙТ ПРОЙДЕН: счёт фактически идёт на карте, подтверждено внешне", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
