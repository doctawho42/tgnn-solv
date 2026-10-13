#!/usr/bin/env python
"""Опрос статуса и выборочная выгрузка ядра Kaggle ЧЕРЕЗ API, минуя CLI.

ПОЧЕМУ НЕ CLI. На машине разработки ``kaggle kernels status`` и ``kaggle kernels output``
периодически падают ``ConnectTimeout``, тогда как тот же эндпойнт через ``requests`` с теми же
ключами отвечает 200 за 0.6-1.1 с. Измерено 2026-10-04/05: curl проходил, Python CLI нет, прямой
``requests`` проходил, и сайт при этом отдавал 200 -- то есть дело не в сети и не в ключах. Вторая
причина -- ``kernels output`` тянет ВСЮ выгрузку, а из 558 файлов ядра нужны восемь.

ДВА ДЕФЕКТА, ИСПРАВЛЕННЫЕ ИЗМЕРЕНИЕМ, А НЕ ДОГАДКОЙ.

(1) ПАГИНАЦИЯ ОБЯЗАТЕЛЬНА. Ответ несёт ``hasNextPageToken``, и первая страница отдаёт 500 файлов
    при 558 фактических. Без обхода страниц отсутствие нужного файла читается как «его нет» -- та
    же форма тихого отказа, что в этом проекте уже дважды стоила ядра.

(2) ОТКАЗ СЕТИ НЕ ЕСТЬ ОСНОВАНИЕ ПРЕКРАТИТЬ НАБЛЮДЕНИЕ. Порог в шесть отказов подряд дважды снял
    наблюдение с ЖИВОГО ядра; поднятый до двадцати, то есть до 80 минут слепоты, он снял его в
    третий раз -- связь до kaggle.com здесь выпадает и на дольше, а прямой запрос сразу после
    сдачи показывал running. Дефект был не в величине порога, а в самом правиле: выгрузку ядро
    пишет само, поэтому цена редкого опроса -- только задержка в замечании, а цена сдачи --
    потерянное наблюдение. Отказы уводят интервал вверх по удвоению до получаса и НИКОГДА не
    прекращают цикл; единственный выход -- терминальный статус.

ПОЧЕМУ ЭТОТ ФАЙЛ ЛЕЖИТ В РЕПОЗИТОРИИ. Обе функции были написаны и проверены в эфемерном
скрэтчпаде сессии, который за неделю вычистился, -- и наблюдение за следующим ядром упало на
``No such file or directory``. Проверенный измерением инструмент не должен жить там, откуда его
удалят.

Статус печатается ТОЛЬКО при смене, иначе наблюдение превращается в шум. Токен не печатается
никогда.

    python scripts/kaggle/kernel_api.py status <slug> [--every 240]
    python scripts/kaggle/kernel_api.py fetch  <slug> <dest> [--only PREFIX ...]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

BASE = "https://www.kaggle.com/api/v1"
#: ОТКАЗ СЕТИ НЕ ЕСТЬ ОСНОВАНИЕ ПРЕКРАТИТЬ НАБЛЮДЕНИЕ, и это третий вывод по счёту. Порог в шесть
#: отказов дважды снял наблюдение с живого ядра; поднятый до двадцати (80 мин слепоты) он снял его
#: в третий раз -- связь до kaggle.com здесь выпадает и на дольше, а прямой запрос сразу после
#: сдачи показывал running. Правило неверно само по себе: ядро пишет выгрузку независимо от того,
#: смотрит ли кто-то, поэтому цена редкого опроса -- только задержка в замечании, а цена сдачи --
#: потерянное наблюдение. Поэтому отказы уводят интервал ВВЕРХ по удвоению до потолка и никогда не
#: прекращают цикл: единственный выход -- терминальный статус.
BACKOFF_FACTOR = 2.0
#: Потолок интервала при отказах: полчаса. Выше смысла нет -- прогоны здесь длятся часы.
BACKOFF_CEILING_S = 1800.0
#: Через сколько отказов подряд сказать об этом вслух один раз, а не молчать и не частить.
FAILURES_BEFORE_NOTICE = 5
#: Статусы, при которых опрос продолжается. Всё остальное считается терминальным.
LIVE = ("running", "queued")
#: По умолчанию берём результаты и чекпойнты, а не скопированное в выгрузку дерево репозитория.
DEFAULT_ONLY = ("/".join(("out", "results")) + "/", "/".join(("out", "checkpoints")) + "/")


def credentials() -> tuple[str, str]:
    cfg = json.loads((Path.home() / ".kaggle" / "kaggle.json").read_text())
    return cfg["username"], cfg["key"]


def status(slug: str, *, user: str, auth: tuple[str, str], timeout: float = 30.0,
          get: Any = None) -> dict:
    get = get or requests.get
    r = get(f"{BASE}/kernels/status",
            params={"userName": user, "kernelSlug": slug}, auth=auth, timeout=timeout)
    r.raise_for_status()
    return r.json()


def list_output(slug: str, *, user: str, auth: tuple[str, str],
                timeout: float = 60.0, get: Any = None) -> tuple[list[dict], Any, int]:
    """Все файлы выгрузки, ОБХОДЯ СТРАНИЦЫ. Возвращает (файлы, лог, число страниц).

    ``get`` подменяется в тестах; по умолчанию ``requests.get``.
    """
    get = get or requests.get
    files: list[dict] = []
    token, pages, log = None, 0, None
    while True:
        params = {"userName": user, "kernelSlug": slug}
        if token:
            params["pageToken"] = token
        r = get(f"{BASE}/kernels/output", params=params, auth=auth, timeout=timeout)
        r.raise_for_status()
        d = r.json()
        files += d.get("files") or []
        log = log or d.get("log")
        pages += 1
        token = d.get("nextPageToken") or None
        # ОБА условия: сервер может прислать пустой токен при выставленном флаге и наоборот,
        # и любой из двух промахов вернул бы неполный список молча.
        if not d.get("hasNextPageToken") or not token:
            break
    return files, log, pages


def _cmd_status(a: argparse.Namespace) -> int:
    user, key = credentials()
    auth = (user, key)
    last, fails, delay = None, 0, a.every
    while True:
        try:
            st = (status(a.slug, user=user, auth=auth).get("status") or "?").lower()
            if fails:
                print(f"{a.slug}: связь вернулась после {fails} отказов", flush=True)
            fails, delay = 0, a.every
        except Exception as exc:
            fails += 1
            delay = min(delay * BACKOFF_FACTOR, BACKOFF_CEILING_S)
            # Говорим об этом РОВНО ОДИН раз: молчание нельзя отличить от работающего ядра, а
            # строка на каждый отказ утопит настоящую смену статуса.
            if fails == FAILURES_BEFORE_NOTICE:
                print(f"{a.slug}: {fails} опросов подряд не прошли ({type(exc).__name__}); "
                      f"интервал уведён до {delay / 60:.0f} мин, наблюдение продолжается -- "
                      f"ядро пишет выгрузку независимо от того, видно ли его отсюда", flush=True)
            time.sleep(delay)
            continue
        if st != last:
            print(f"{a.slug}: {st}", flush=True)
            last = st
        if st not in LIVE:
            print(f"{a.slug}: ТЕРМИНАЛЬНЫЙ статус {st}", flush=True)
            return 0
        time.sleep(delay)


#: Обрыв потока на 85-мегабайтном чекпойнте -- не редкость на этой связи, он случился на первой
#: же выгрузке плеча репликата (IncompleteRead: 17 МБ из 85).
DOWNLOAD_ATTEMPTS = 4


def download(url: str, out: Path, *, get: Any = None, attempts: int = DOWNLOAD_ATTEMPTS) -> int:
    """Скачать в ``.part``, сверить длину и только потом переименовать. Вернуть размер.

    ПОЧЕМУ НЕ ПРЯМО В КОНЕЧНОЕ ИМЯ. Первая выгрузка плеча репликата оборвалась на
    ``IncompleteRead(17045616 bytes read, 67814996 more expected)``, и на диске остался обрезанный
    файл ПОД ПРАВИЛЬНЫМ ИМЕНЕМ ``grounded_a_seed43.pt``. Всё, что читает чекпойнты по пути, приняло
    бы его за целый: в лучшем случае курсор возобновления вернул бы None и плечо начало бы обучение
    с нуля, в худшем -- сессия упала бы в непонятном месте. Это тот же класс, что и «0 чекпойнтов
    восстановлено» -- недостача, читаемая как норма.

    Длина сверяется с ``Content-Length``, когда сервер её даёт: без сверки «поток кончился без
    исключения» не отличимо от «поток кончился раньше времени».
    """
    get = get or requests.get
    part = out.with_suffix(out.suffix + ".part")
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with get(url, timeout=600, stream=True) as resp:
                resp.raise_for_status()
                expected = resp.headers.get("Content-Length")
                written = 0
                with part.open("wb") as fh:
                    for chunk in resp.iter_content(1 << 20):
                        fh.write(chunk)
                        written += len(chunk)
            if expected is not None and written != int(expected):
                raise OSError(f"получено {written} B против объявленных {expected} B")
            part.replace(out)          # атомарно, и только после успеха
            return written
        except Exception as exc:
            last = exc
            part.unlink(missing_ok=True)
            if attempt < attempts:
                print(f"  .. {out.name}: попытка {attempt} оборвалась "
                      f"({type(exc).__name__}), повтор", flush=True)
                time.sleep(2.0 * attempt)
    assert last is not None
    raise last


def _cmd_fetch(a: argparse.Namespace) -> int:
    user, key = credentials()
    auth = (user, key)
    files, log, pages = list_output(a.slug, user=user, auth=auth)
    print(f"страниц {pages}, файлов всего {len(files)}")
    want = [f for f in files if any(p in (f.get("fileName") or "") for p in a.only)]
    print(f"подходит под {list(a.only)}: {len(want)}")
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    for f in want:
        out = dest / f["fileName"]
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            n = download(f["url"], out)
        except Exception as exc:
            print(f"  !! {f['fileName']}: НЕ ЗАГРУЖЕН после {DOWNLOAD_ATTEMPTS} попыток "
                  f"({type(exc).__name__}). Файла под конечным именем НЕТ -- обрезанный остаток "
                  f"не оставлен, чтобы его не прочли как целый.", flush=True)
            continue
        print(f"  {f['fileName']}  {n} B")
    if log:
        (dest / "kernel_log.txt").write_text(log if isinstance(log, str) else json.dumps(log))
        print(f"  kernel_log.txt  {(dest / 'kernel_log.txt').stat().st_size} B")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="опрашивать до терминального статуса, печатать только смены")
    s.add_argument("slug")
    s.add_argument("--every", type=float, default=240.0,
                   help="интервал опроса, с. Терпимость к выпадениям связи считается от него: "
                        "сдача наступает через MAX_CONSECUTIVE_FAILURES интервалов.")
    s.set_defaults(func=_cmd_status)

    f = sub.add_parser("fetch", help="забрать ТОЛЬКО подходящие файлы выгрузки")
    f.add_argument("slug")
    f.add_argument("dest")
    f.add_argument("--only", nargs="+", default=list(DEFAULT_ONLY),
                   help="подстроки пути файла в выгрузке")
    f.set_defaults(func=_cmd_fetch)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
