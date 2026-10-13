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


def test_network_failure_never_ends_the_watch() -> None:
    """Опрос НЕ сдаётся по отказу связи -- он уводит интервал вверх и продолжает.

    Это третий вывод по счёту, а не косметика. Порог в шесть отказов дважды снял наблюдение с
    живого ядра; поднятый до двадцати (80 мин слепоты) он снял его в третий раз, и прямой запрос
    сразу после сдачи показывал running. Дефект был в самом правиле: ядро пишет выгрузку
    независимо от наблюдателя, значит цена редкого опроса -- только задержка в замечании, а цена
    сдачи -- потерянное наблюдение.

    Тест гоняет цикл на подменённых часах и сломанной сети и проверяет, что он НЕ выходит, что
    интервал растёт по удвоению до потолка, и что сообщение об отказах печатается ровно один раз.
    """
    m = _mod()
    assert not hasattr(m, "MAX_CONSECUTIVE_FAILURES"), (
        "порог сдачи вернулся -- именно он трижды снимал наблюдение с живого ядра")
    assert m.BACKOFF_CEILING_S == 1800.0 and m.BACKOFF_FACTOR == 2.0

    slept: list[float] = []
    calls = {"n": 0}

    def broken_then_done(url, params=None, auth=None, timeout=None):
        calls["n"] += 1
        # Сорок отказов подряд -- вдвое больше прежнего порога сдачи, потом терминальный статус.
        if calls["n"] <= 40:
            raise ConnectionError("сеть выпала")
        return _Resp({"status": "complete"})

    m.requests.get = broken_then_done
    m.time.sleep = slept.append
    printed: list[str] = []
    # Заглушка обязана принимать flush=, иначе падает сам код, а не проверяемое поведение.
    m.print = lambda *args, **kwargs: printed.append(" ".join(str(x) for x in args))
    rc = m.main(["status", "slug", "--every", "240"])
    assert rc == 0, "цикл обязан дожить до терминального статуса, а не выйти по сети"
    assert calls["n"] == 41, f"опросов {calls['n']}: цикл прервался на отказах"
    assert max(slept) == m.BACKOFF_CEILING_S, f"интервал не дорос до потолка: max {max(slept)}"
    assert slept[0] == 240 * m.BACKOFF_FACTOR, "первый отказ не удвоил интервал"
    notices = [x for x in printed if "опросов подряд не прошли" in x]
    assert len(notices) == 1, f"сообщений об отказах {len(notices)}, должно быть ровно одно"
    assert any("связь вернулась после 40 отказов" in x for x in printed), (
        "возврат связи не отмечен -- иначе не видно, что слепота кончилась")


def test_queued_counts_as_live_so_a_just_pushed_kernel_is_not_called_terminal() -> None:
    """Свежеотправленное ядро приходит в ``queued``; принять это за терминал -- потерять прогон."""
    m = _mod()
    assert "queued" in m.LIVE and "running" in m.LIVE
    for terminal in ("complete", "error", "cancelAcknowledged"):
        assert terminal not in m.LIVE

# --------------------------------------------------------------------------------------------
# Загрузка файла: обрыв НЕ оставляет обрезанный файл под конечным именем.
#
# Первая выгрузка плеча репликата оборвалась на IncompleteRead (17 МБ из 85), и на диске остался
# обрезанный grounded_a_seed43.pt ПОД ПРАВИЛЬНЫМ ИМЕНЕМ. Всё, что читает чекпойнты по пути,
# приняло бы его за целый: курсор возобновления вернул бы None и плечо начало бы обучение с нуля.
# Это тот же класс, что «0 чекпойнтов восстановлено» -- недостача, читаемая как норма.
# --------------------------------------------------------------------------------------------


class _Stream:
    """Отдаёт куски и, если задано, обрывается, не дочитав до Content-Length."""

    def __init__(self, chunks, length=None, raise_at=None):
        self._chunks, self._raise_at = list(chunks), raise_at
        self.headers = {} if length is None else {"Content-Length": str(length)}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, _n):
        for i, c in enumerate(self._chunks):
            if self._raise_at is not None and i == self._raise_at:
                raise ConnectionError("поток оборван")
            yield c


def test_a_broken_stream_leaves_no_file_at_the_final_name(tmp_path) -> None:
    m = _mod()
    out = tmp_path / "checkpoints" / "grounded_a_seed43.pt"
    out.parent.mkdir(parents=True)
    calls = {"n": 0}

    def always_broken(url, timeout=None, stream=None):
        calls["n"] += 1
        return _Stream([b"x" * 8, b"y" * 8], length=64, raise_at=1)

    import pytest as _pt
    with _pt.raises(ConnectionError):
        m.download("u", out, get=always_broken, attempts=3)
    assert calls["n"] == 3, f"повторов {calls['n']}, ожидалось 3"
    assert not out.exists(), (
        "обрезанный файл остался под конечным именем -- именно это и делало недостачу неотличимой "
        "от целого чекпойнта")
    assert not list(out.parent.glob("*.part")), "остаток .part не убран"


def test_a_short_stream_without_an_exception_is_still_rejected(tmp_path) -> None:
    """Поток может кончиться БЕЗ исключения. Без сверки длины это не отличить от успеха."""
    m = _mod()
    out = tmp_path / "f.bin"
    import pytest as _pt
    with _pt.raises(OSError, match="против объявленных"):
        m.download("u", out, get=lambda *a, **k: _Stream([b"z" * 10], length=100), attempts=1)
    assert not out.exists()


def test_a_complete_stream_is_renamed_into_place(tmp_path) -> None:
    m = _mod()
    out = tmp_path / "f.bin"
    n = m.download("u", out, get=lambda *a, **k: _Stream([b"a" * 50, b"b" * 50], length=100),
                   attempts=1)
    assert n == 100 and out.exists() and out.stat().st_size == 100
    assert not list(tmp_path.glob("*.part"))


def test_a_missing_content_length_does_not_block_the_download(tmp_path) -> None:
    """Сервер не обязан давать длину; тогда проверка -- отсутствие исключения, и файл кладётся."""
    m = _mod()
    out = tmp_path / "f.bin"
    n = m.download("u", out, get=lambda *a, **k: _Stream([b"q" * 7]), attempts=1)
    assert n == 7 and out.read_bytes() == b"q" * 7
