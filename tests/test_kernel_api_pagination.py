"""Выгрузка ядра Kaggle обходит ВСЕ страницы -- иначе неполный список читается как полный.

ЗАЧЕМ ЭТОТ ТЕСТ. Эндпойнт ``kernels/output`` отдаёт по 500 файлов на страницу и несёт
``hasNextPageToken``. У ядра ``tgnn-solv-e2rb`` файлов было 558, то есть одностраничный обход
вернул бы 500 и промолчал. В этом проекте ровно такая форма отказа -- «не нашёл» вместо «не
посмотрел» -- уже дважды стоила GPU-ядра: ячейка восстановления искала чекпойнт одним уровнем
каталога, печатала «0 checkpoints carried forward» и плечо начинало обучение с нуля.

Тест подменяет HTTP, а не сеть, и проверяет три вещи, которые ломаются независимо: число страниц,
полноту склеенного списка и то, что обход останавливается по КАЖДОМУ из двух сигналов конца.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _mod():
    spec = importlib.util.spec_from_file_location(
        "kernel_api", Path("scripts/kaggle/kernel_api.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules["kernel_api"] = m
    spec.loader.exec_module(m)
    return m


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls: list = []

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _pager(pages: list[dict]):
    """HTTP-заглушка: отдаёт страницы по порядку, записывая переданные pageToken."""
    seen: list[str | None] = []

    def get(url, params=None, auth=None, timeout=None):
        seen.append((params or {}).get("pageToken"))
        return _Resp(pages[len(seen) - 1])

    get.seen = seen  # type: ignore[attr-defined]
    return get


def test_walks_every_page_and_concatenates_all_files() -> None:
    m = _mod()
    first = {"files": [{"fileName": f"a{i}"} for i in range(500)],
             "hasNextPageToken": True, "nextPageToken": "T1", "log": "LOG"}
    second = {"files": [{"fileName": f"b{i}"} for i in range(58)],
              "hasNextPageToken": False, "nextPageToken": None}
    get = _pager([first, second])
    files, log, pages = m.list_output("slug", user="u", auth=("u", "k"), get=get)

    assert pages == 2, "обход остановился на первой странице -- это и есть исходный дефект"
    assert len(files) == 558, (
        f"склеено {len(files)} файлов вместо 558: одностраничный обход вернул бы ровно 500 и "
        f"промолчал, а отсутствие нужного файла прочиталось бы как «его нет»")
    assert files[0]["fileName"] == "a0" and files[-1]["fileName"] == "b57"
    assert log == "LOG", "лог берётся с первой страницы, где он и приходит"
    assert get.seen == [None, "T1"], "токен второй страницы не передан"


def test_stops_on_a_cleared_flag_even_when_a_token_is_still_present() -> None:
    """Сервер может оставить непустой токен при снятом флаге -- обход обязан остановиться."""
    m = _mod()
    get = _pager([{"files": [{"fileName": "x"}],
                   "hasNextPageToken": False, "nextPageToken": "STALE"}])
    files, _, pages = m.list_output("s", user="u", auth=("u", "k"), get=get)
    assert pages == 1 and len(files) == 1


def test_stops_on_a_missing_token_even_when_the_flag_is_set() -> None:
    """И наоборот: флаг выставлен, токена нет. Без второго условия это вечный цикл."""
    m = _mod()
    get = _pager([{"files": [{"fileName": "x"}],
                   "hasNextPageToken": True, "nextPageToken": None}])
    files, _, pages = m.list_output("s", user="u", auth=("u", "k"), get=get)
    assert pages == 1 and len(files) == 1


def test_blindness_before_giving_up_is_the_measured_eighty_minutes() -> None:
    """Порог подобран по измерению: шесть отказов дважды сняли наблюдение с живого ядра.

    Это не косметика. Наблюдение, сдающееся через четыре минуты выпадения связи, молчит о ядре,
    которое ещё работает, и следующий отчёт о нём получается из догадки вместо запроса.
    """
    m = _mod()
    assert m.MAX_CONSECUTIVE_FAILURES * 240 / 60 == pytest.approx(80.0)
    assert m.MAX_CONSECUTIVE_FAILURES > 6


def test_queued_counts_as_live_so_a_just_pushed_kernel_is_not_called_terminal() -> None:
    """Свежеотправленное ядро приходит в ``queued``; принять это за терминал -- потерять прогон."""
    m = _mod()
    assert "queued" in m.LIVE and "running" in m.LIVE
    for terminal in ("complete", "error", "cancelAcknowledged"):
        assert terminal not in m.LIVE
