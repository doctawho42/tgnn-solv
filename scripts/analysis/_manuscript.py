"""Одно место, где назван документ записи.

ЗАЧЕМ. До 2026-11-13 имя пары стояло в девятнадцати файлах. Когда рукопись сменилась с
``grounding_paradox`` на ``learned_sigma_profile``, они остались смотреть на отозванную: десять
проверок каждый день проходили зелёными на документе, который никто больше не правит, а живую
рукопись не гейтило почти ничто. Имя названо здесь; остальные спрашивают.

ДВЕ РУКОПИСИ УСТРОЕНЫ ПО-РАЗНОМУ, и это ловушка для всякой проверки, читающей текст.
Отозванная статья -- один файл. Живая -- обёртка, которая втягивает ``sections/*-v2.tex``, так
что проверка, прочитавшая только обёртку, не увидит ни одного предложения тела и пройдёт
зелёной, потому что искать будет нечего. Поэтому текст берётся через :func:`flatten`, а не
``Path.read_text``.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"

#: Пара документа записи: статья и Supporting Information, без ``.tex``.
LIVE = ("learned_sigma_profile", "learned_sigma_profile_si")
#: Отозванная пара. Это другой довод, а не редакция живого, и она намеренно остаётся собираемой.
RETIRED = ("grounding_paradox", "grounding_paradox_si")

_INPUT = re.compile(r"^[^%\n]*?\\input\{([^}]+)\}", re.M)
#: ``\input`` преамбулы и библиографии -- не текст рукописи.
_SKIP = ("preamble",)


def tex(stem: str) -> Path:
    """Путь к ``.tex`` по основе имени."""
    return PAPER / f"{stem}.tex"


def flatten(stem_or_path: str | Path, _seen: set[Path] | None = None) -> str:
    """Текст документа с рекурсивно вставленными ``\\input``.

    Пропускает преамбулу и уже вставленные файлы, так что цикл не зациклит. Отсутствующий
    ``\\input`` оставляется как есть: это сигнал, а не повод упасть внутри проверки.
    """
    path = stem_or_path if isinstance(stem_or_path, Path) else tex(str(stem_or_path))
    seen = set() if _seen is None else _seen
    if path in seen or not path.exists():
        return ""
    seen.add(path)
    out = path.read_text(encoding="utf8")
    for name in _INPUT.findall(out):
        if any(s in name for s in _SKIP):
            continue
        # LaTeX разрешает \input относительно каталога ГЛАВНОГО документа, а не включающего
        # файла. Разрешение от path.parent даёт paper/sections/sections/... и тихо не находит
        # ничего: таблица, втянутая из si-v2.tex, пропала из текста, а проверка на ней прошла бы
        # зелёной. Сначала PAPER, и только потом сосед.
        rel = Path(name)
        child = PAPER / rel
        if not child.suffix:
            child = child.with_suffix(".tex")
        if not child.exists():
            sib = path.parent / rel
            child = sib if sib.suffix else sib.with_suffix(".tex")
        out += "\n" + flatten(child, seen)
    return out


def article_text(pair: tuple[str, str] = LIVE) -> str:
    """Полный текст статьи, обёртка плюс её секции."""
    return flatten(pair[0])


def si_text(pair: tuple[str, str] = LIVE) -> str:
    """Полный текст Supporting Information."""
    return flatten(pair[1])


if __name__ == "__main__":
    for nm, pair in (("живая", LIVE), ("отозванная", RETIRED)):
        a, s = article_text(pair), si_text(pair)
        print(f"{nm:11s} статья {len(a):7d} знаков, SI {len(s):7d} знаков")
