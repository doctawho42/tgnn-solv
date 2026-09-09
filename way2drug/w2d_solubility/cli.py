"""Командный интерфейс сервиса: SMILES на вход, таблица или JSON на выход.

    python -m w2d_solubility.cli "CC(=O)Nc1ccc(O)cc1"
    python -m w2d_solubility.cli --json "CC(=O)Nc1ccc(O)cc1" "CC(=O)Oc1ccccc1C(=O)O"
    python -m w2d_solubility.cli --input smiles.txt --json --out result.json
    python -m w2d_solubility.cli --temperature 310.15 "CN1C=NC2=C1C(=O)N(C)C(=O)N2C"

Одна структура на строку во входном файле; пустые строки и строки с # пропускаются.
Вторая колонка после пробела, если она есть, считается идентификатором и переносится
в ответ как "id".
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .predictor import SolubilityPredictor


def _read_input(path: Path) -> list[tuple[str, str | None]]:
    items = []
    for raw in path.read_text(encoding="utf8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        items.append((parts[0], parts[1].strip() if len(parts) > 1 else None))
    return items


def _table(result: dict, top: int) -> str:
    if "error" in result:
        return f"{result['input']}: ОШИБКА — {result['error']}"
    out = [f"{result['input']}   M = {result['molar_mass_g_per_mol']} г/моль, "
           f"T = {result['temperature_K']} K"]
    app = result["applicability"]
    out.append(f"  область применимости: сходство {app['nearest_training_similarity']} "
               f"({'внутри' if app['in_domain'] else 'ВНЕ ОБЛАСТИ'})")
    for n in app["notes"]:
        out.append(f"    ! {n}")
    out.append(f"  {'растворитель':<18}{'ln x2':>8}{'интервал 95%':>20}{'г/л':>10}")
    for r in result["predictions"][:top]:
        lo, hi = r["ln_x2_interval"]
        conc = "—" if r["concentration_g_per_l"] is None else f"{r['concentration_g_per_l']:.4g}"
        out.append(f"  {r['solvent_name']:<18}{r['ln_x2']:>8.2f}"
                   f"{f'[{lo:.2f}, {hi:.2f}]':>20}{conc:>10}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="w2d_solubility",
        description="Предсказание растворимости по панели растворителей (Way2Drug)")
    ap.add_argument("smiles", nargs="*", help="SMILES растворяемого вещества")
    ap.add_argument("--input", type=Path, help="файл со списком SMILES, по одному на строку")
    ap.add_argument("--json", action="store_true", help="выдать JSON вместо таблицы")
    ap.add_argument("--out", type=Path, help="записать в файл вместо stdout")
    ap.add_argument("--temperature", type=float, default=None,
                    help="температура в кельвинах (по умолчанию 298.15)")
    ap.add_argument("--top", type=int, default=10,
                    help="сколько растворителей показать в таблице (в JSON всегда все)")
    ap.add_argument("--checkpoints", type=Path, nargs="*",
                    help="явный список чекпойнтов ансамбля")
    args = ap.parse_args(argv)

    items: list[tuple[str, str | None]] = [(s, None) for s in args.smiles]
    if args.input:
        items += _read_input(args.input)
    if not items:
        ap.error("нужен хотя бы один SMILES или --input")

    predictor = SolubilityPredictor(checkpoints=args.checkpoints)
    results = []
    for smi, ident in items:
        res = predictor.predict_panel(smi, temperature=args.temperature)
        if ident:
            res["id"] = ident
        results.append(res)

    if args.json:
        text = json.dumps(results if len(results) > 1 else results[0],
                          ensure_ascii=False, indent=2)
    else:
        text = "\n\n".join(_table(r, args.top) for r in results)

    if args.out:
        args.out.write_text(text + "\n", encoding="utf8")
        print(f"записано: {args.out}", file=sys.stderr)
    else:
        print(text)
    # Непонятая структура -- это ошибка ввода, а не сбой сервиса: сообщаем в ответе и
    # возвращаем 0, чтобы пакетный запуск не падал на одной кривой строке из тысячи.
    return 0


if __name__ == "__main__":
    sys.exit(main())
