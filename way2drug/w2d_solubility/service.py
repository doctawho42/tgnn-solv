"""Минимальный HTTP-сервис поверх предиктора. Только стандартная библиотека.

    python -m w2d_solubility.service --port 8080

    GET  /health
    GET  /panel
    GET  /predict?smiles=CC(=O)Nc1ccc(O)cc1[&temperature=298.15]
    POST /predict     {"smiles": ["...", "..."], "temperature": 298.15}

ЭТО НЕ БОЕВОЙ СЕРВЕР. http.server однопоточен и не рассчитан на публичную нагрузку;
он здесь для того, чтобы команда платформы могла поднять сервис одной командой и
посмотреть на формат ответа. Для боевого развёртывания разумнее импортировать
SolubilityPredictor напрямую в существующий backend: модель грузится за доли секунды
и держится в памяти, а панель из 27 растворителей считается около 0.4 с на CPU.

ОГРАНИЧЕНИЕ РАЗМЕРА ПАРТИИ стоит не для красоты: каждый SMILES -- это 27 пар, и
тысяча структур в одном запросе займёт минуты, в течение которых однопоточный сервер
не ответит никому.
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .predictor import SolubilityPredictor

MAX_BATCH = 50

_predictor: SolubilityPredictor | None = None


def predictor() -> SolubilityPredictor:
    global _predictor
    if _predictor is None:
        _predictor = SolubilityPredictor()
    return _predictor


class Handler(BaseHTTPRequestHandler):
    server_version = "w2d-solubility/1.0"

    def _send(self, code: int, payload: dict | list) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _run(self, smiles: list[str], temperature: float | None) -> None:
        if not smiles:
            self._send(400, {"error": "не передан ни один SMILES"})
            return
        if len(smiles) > MAX_BATCH:
            self._send(413, {"error": f"за один запрос не больше {MAX_BATCH} структур, "
                                      f"получено {len(smiles)}"})
            return
        try:
            out = [predictor().predict_panel(s, temperature=temperature) for s in smiles]
        except Exception as exc:                       # noqa: BLE001
            # Пользователь не должен видеть трассировку, но в лог она обязана попасть.
            self.log_error("predict failed: %r", exc)
            self._send(500, {"error": "внутренняя ошибка предсказания"})
            return
        self._send(200, out if len(out) > 1 else out[0])

    def do_GET(self) -> None:                          # noqa: N802
        url = urlparse(self.path)
        if url.path == "/health":
            self._send(200, {"status": "ok", "model": predictor().describe()})
        elif url.path == "/panel":
            self._send(200, predictor().panel)
        elif url.path == "/predict":
            q = parse_qs(url.query)
            temp = q.get("temperature", [None])[0]
            self._run(q.get("smiles", []), float(temp) if temp else None)
        else:
            self._send(404, {"error": "нет такого пути",
                             "paths": ["/health", "/panel", "/predict"]})

    def do_POST(self) -> None:                         # noqa: N802
        if urlparse(self.path).path != "/predict":
            self._send(404, {"error": "нет такого пути"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "тело запроса не является корректным JSON"})
            return
        smiles = body.get("smiles", [])
        if isinstance(smiles, str):
            smiles = [smiles]
        self._run(list(smiles), body.get("temperature"))

    def log_message(self, format: str, *args) -> None:  # noqa: A002 (имя из базового класса)
        sys.stderr.write(f"{self.address_string()} {format % args}\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="w2d_solubility.service")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args(argv)

    predictor()                                        # прогреть до первого запроса
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"слушаю http://{args.host}:{args.port}  "
          f"(/health, /panel, /predict)", file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("останавливаюсь", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
