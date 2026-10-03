#!/usr/bin/env python
"""Гонять плечи на Kaggle через границу сессии: прогон -> выгрузка -> датасет -> прогон.

ЗАЧЕМ. У ядра Kaggle жёсткий предел 12 часов, а плечо при конфигурационном батче стоит около
16.6 (замерено на настоящем шаге, results/real_step_profile/summary.json). Значит ОДНО плечо
физически не укладывается в одну сессию, и вопрос не в квоте, а в переносе работы через
границу. Апарат для этого есть и описан в README: run_arms.py останавливается за час до
убийства, чекпойнт и файлы предсказаний лежат в /kaggle/working/out, а ячейка RESTORE
следующей сессии подхватывает их из приложенного датасета (глоб /kaggle/input/*/out).
Руками это четыре шага каждые одиннадцать часов; здесь они сведены в один цикл.

ЧТО ЦИКЛ ДЕЛАЕТ ЗА ОДИН ОБОРОТ
  1. толкает ядро (первый оборот -- только с пакетом кода, дальше -- ещё и с датасетом выхода);
  2. ждёт его завершения, опрашивая статус;
  3. забирает /kaggle/working/out;
  4. публикует это как версию датасета выхода и ждёт готовности;
  5. считает, у каких (сид, плечо) уже есть файл предсказаний, и если не у всех -- идёт на
     следующий оборот.

ЧЕГО ОН НЕ ДЕЛАЕТ, СОЗНАТЕЛЬНО. Не планирует себя по расписанию и не ходит бесконечно:
``--max-sessions`` обязателен и ограничивает число оборотов, а ``--budget-hours`` -- суммарное
время, которое разрешено потратить. Квота Kaggle недельная (порядка 30 ч), и цикл, который
её выест молча, хуже цикла, который остановится и скажет об этом.

НЕ ПОДНИМАЕТ БАТЧ ПО СВОЕЙ ВОЛЕ. ``--batch-size`` просто пробрасывается. Поднятый батч делает
плечи сравнимыми между собой и НЕ сравнимыми с опубликованной пятисидовой семьёй, а это
решение о назначении прогона, а не настройка пропускной способности -- и к тому же замер
показал, что выигрыш невелик: батч 256 даёт 282 строк/с против 205 при батче 64, то есть
1.38x, при росте времени шага с 312 до 906 мс.

    python scripts/kaggle/drive_sessions.py \\
        --arms grounded_a grounded_a_detachcrystal --seeds 42 \\
        --kernel polomoshnov/tgnn-solv-e2 --out-dataset polomoshnov/tgnn-solv-e2-out \\
        --code-dataset polomoshnov/tgnn-solv-e5 \\
        --work /tmp/e2 --max-sessions 4 --budget-hours 30
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

POLL_S = 120
#: Статусы, на которых ядро считается остановившимся.
TERMINAL = ("complete", "error", "cancel")


def kaggle(*args: str, check: bool = True) -> str:
    """Вызов CLI Kaggle. Токен берётся из ~/.kaggle/kaggle.json, здесь он не фигурирует."""
    p = subprocess.run(["kaggle", *args], capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    if check and p.returncode != 0:
        raise RuntimeError(f"kaggle {' '.join(args)} -> {p.returncode}\n{out[:800]}")
    return out


def wait_kernel(ref: str, *, timeout_h: float) -> str:
    """Ждать конца прогона. Возвращает последний статус.

    Таймаут здесь не декоративный: ядро, зависшее в очереди, иначе съело бы весь бюджет
    цикла ожиданием, не потратив ни минуты счёта.
    """
    deadline = time.time() + timeout_h * 3600
    last = ""
    while time.time() < deadline:
        last = kaggle("kernels", "status", ref, check=False).strip()
        low = last.lower()
        if any(t in low for t in TERMINAL):
            return last
        time.sleep(POLL_S)
    return f"ТАЙМАУТ ожидания после {timeout_h:.1f} ч; последний статус: {last}"


def wait_dataset(ref: str, *, timeout_min: float = 20.0) -> bool:
    """Ждать, пока версия датасета станет видимой и НЕПУСТОЙ.

    Проверять только слово ready нельзя: сразу после заливки оно уже стоит, а размер ещё
    нулевой, и приложенный в этот момент датасет отдал бы ядру ПРЕДЫДУЩУЮ версию. Эта
    ошибка в проекте уже случалась -- ядро получило пакет без правки, которую мерило.
    """
    deadline = time.time() + timeout_min * 60
    slug = ref.split("/")[-1]
    while time.time() < deadline:
        for line in kaggle("datasets", "list", "--mine", "-s", slug, check=False).splitlines():
            parts = line.split()
            if parts and parts[0] == ref and len(parts) > 1 and parts[1].isdigit():
                if int(parts[1]) > 0:
                    return True
        time.sleep(20)
    return False


def pending(out_root: Path, arms: list[str], seeds: list[int]) -> list[tuple[int, str]]:
    """(сид, плечо), у которых ещё нет файла предсказаний -- то есть незаконченные."""
    left = []
    for seed in seeds:
        for arm in arms:
            if not (out_root / "results" / f"seed_{seed}" / f"{arm}_predictions.csv").exists():
                left.append((seed, arm))
    return left


def push_kernel(work: Path, notebook: Path, kernel: str, datasets: list[str]) -> None:
    kdir = work / "kernel"
    kdir.mkdir(parents=True, exist_ok=True)
    shutil.copy(notebook, kdir / notebook.name)
    (kdir / "kernel-metadata.json").write_text(json.dumps({
        "id": kernel,
        "title": kernel.split("/")[-1].replace("-", " "),
        "code_file": notebook.name,
        "language": "python", "kernel_type": "notebook",
        "is_private": True, "enable_gpu": True, "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": datasets,
        "competition_sources": [], "kernel_sources": [], "model_sources": [],
    }, indent=1))
    print(kaggle("kernels", "push", "-p", str(kdir)).strip())


def publish_out(work: Path, out_dataset: str, session: int) -> bool:
    """Выложить выгрузку как версию датасета выхода; True, если версия стала видимой."""
    staged = work / "out_dataset"
    if staged.exists():
        shutil.rmtree(staged)
    staged.mkdir(parents=True)
    src = work / "download" / "out"
    if not src.is_dir():
        print(f"!! в выгрузке нет каталога out ({src}) -- переносить нечего")
        return False
    shutil.copytree(src, staged / "out")
    title = out_dataset.split("/")[-1]
    (staged / "dataset-metadata.json").write_text(json.dumps(
        {"title": title, "id": out_dataset, "licenses": [{"name": "CC0-1.0"}]}, indent=1))
    listing = kaggle("datasets", "list", "--mine", "-s", title, check=False)
    exists = any(line.split()[:1] == [out_dataset] for line in listing.splitlines() if line.split())
    verb = ["datasets", "version", "-p", str(staged), "-m",
            f"session {session}", "-r", "zip", "--dir-mode", "zip"] if exists else \
           ["datasets", "create", "-p", str(staged), "-r", "zip", "--dir-mode", "zip"]
    print(kaggle(*verb).strip())
    return wait_dataset(out_dataset)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--notebook", type=Path, required=True)
    ap.add_argument("--kernel", required=True, help="owner/slug ядра")
    ap.add_argument("--code-dataset", required=True, help="owner/slug пакета кода и данных")
    ap.add_argument("--out-dataset", required=True, help="owner/slug датасета выхода")
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--max-sessions", type=int, required=True,
                    help="жёсткий предел числа оборотов: цикл, съедающий недельную квоту "
                         "молча, хуже цикла, который остановится и скажет")
    ap.add_argument("--budget-hours", type=float, default=30.0,
                    help="суммарное время ожидания, после которого цикл останавливается")
    ap.add_argument("--session-timeout-h", type=float, default=12.5)
    a = ap.parse_args()

    a.work.mkdir(parents=True, exist_ok=True)
    journal = a.work / "sessions.json"
    log: list[dict] = json.loads(journal.read_text()) if journal.exists() else []
    t_start = time.time()
    out_root = a.work / "download" / "out"

    for session in range(len(log) + 1, len(log) + a.max_sessions + 1):
        spent = (time.time() - t_start) / 3600
        if spent >= a.budget_hours:
            print(f"== стоп: израсходовано {spent:.1f} ч из бюджета {a.budget_hours:.1f}")
            break
        left = pending(out_root, a.arms, a.seeds) if out_root.exists() else \
            [(s, arm) for s in a.seeds for arm in a.arms]
        if not left:
            print("== все (сид, плечо) закончены")
            break
        print(f"\n{'=' * 70}\n== сессия {session}: осталось {len(left)} плеч -> {left}\n{'=' * 70}")

        datasets = [a.code_dataset]
        if session > 1 and out_root.exists():
            datasets.append(a.out_dataset)
        push_kernel(a.work, a.notebook, a.kernel, datasets)
        status = wait_kernel(a.kernel, timeout_h=a.session_timeout_h)
        print(f"== статус: {status}")

        dl = a.work / "download"
        if dl.exists():
            shutil.rmtree(dl)
        dl.mkdir(parents=True)
        kaggle("kernels", "output", a.kernel, "-p", str(dl), check=False)
        got = pending(out_root, a.arms, a.seeds) if out_root.exists() else left
        done_now = len(left) - len(got)
        entry = {"session": session, "status": status, "arms_finished_this_session": done_now,
                 "still_pending": got, "hours_elapsed_total": (time.time() - t_start) / 3600}
        log.append(entry)
        journal.write_text(json.dumps(log, ensure_ascii=False, indent=2))
        print(f"== закончено за эту сессию: {done_now}; осталось: {got}")

        if "error" in status.lower():
            print("!! ядро упало -- цикл останавливается, читайте лог ядра, а не повторяйте")
            return 1
        if not got:
            break
        if not publish_out(a.work, a.out_dataset, session):
            print("!! версия датасета выхода не стала видимой -- следующая сессия не увидела "
                  "бы работу этой и начала бы заново; цикл останавливается")
            return 1

    print(f"\nжурнал: {journal}")
    for e in log:
        print(f"  сессия {e['session']}: {e['arms_finished_this_session']} плеч, "
              f"{e['hours_elapsed_total']:.1f} ч, статус {e['status'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
