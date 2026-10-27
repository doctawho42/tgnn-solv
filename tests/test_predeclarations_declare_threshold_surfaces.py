r"""Храповик: каждая НОВАЯ предзаявка обязана выписать поверхности своих порогов.

ЗАЧЕМ ЭТО СУЩЕСТВУЕТ
--------------------
За три дня, 2026-10-25..27, ЧЕТЫРЕ предзаявленных порога оказались измерены не на той поверхности,
к которой приложены:

  * ``sigma_hb_retrained`` -- порог ``0.5 x out_mean`` привязан к величине, НЕ закреплённой между
    армами; прогнанный по опорному арму, он выдал тот же вердикт, то есть не различал гипотезы
    вовсе. Цена: 16.5 часов GPU на арм, которым нечего было прочитать;
  * ``e2_attribution_replicate`` -- условие записано через ОТНОШЕНИЕ, поэтому пережило смену знака
    своего числителя молча: любой отрицательный ``P_enc`` даёт "отношение <= 0.5" при любой
    величине;
  * ``delta_phi_reread`` -- пол 0.282 измерен на УРОВНЯХ по плечам и приложен к их РАЗНОСТИ, где
    источник метки сокращается по построению; проверено численно, сдвиг совпал до четвёртого знака
    при обеих метках;
  * ``cluster_certification`` -- пол 0.0744 выведен как ПАРНЫЙ из пяти сидов одного окружения и
    приложен к НЕПАРНОМУ одно-сидовому сравнению МЕЖДУ окружениями.

Это не четыре случайности, а одна привычка: порог назначается там, где его удобно измерить, а не
там, где он будет работать. Проза этого не лечит -- проект уже знает, что держат храповики
(``test_cited_deposits_carry_provenance.py``), а не напоминания.

ЧТО ТРЕБУЕТСЯ
-------------
Блок с машинной меткой, по идиоме, которую проект уже применяет к абзацу абстракта
(``%<abstract-numerals>``)::

    <!-- ПОРОГИ -->
    | порог | измерен на | что ограничивает | совпадает? |
    ...
    <!-- /ПОРОГИ -->

Внутри блока -- строка на каждый численный порог правила, с поверхностью измерения и поверхностью
применения. Порог, у которого эти две графы расходятся, в правило входить не должен; если входит,
это печатается в блоке, а не выясняется после траты.

Предзаявка, которая порогов не объявляет вовсе, пишет это внутри блока явно -- отказ от порога есть
решение и он тоже объявляется заранее.

ЧТО ЭТОТ ТЕСТ НЕ ДЕЛАЕТ
-----------------------
Не проверяет, что поверхности действительно совпадают: это суждение, а не разбор строк. Он
проверяет, что вопрос ЗАДАН до счёта, в месте, которое нельзя не заметить. Содержательную проверку
делает автор, и четыре случая выше показывают, что без этого напоминания он её не делает.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPEN, CLOSE = "<!-- ПОРОГИ -->", "<!-- /ПОРОГИ -->"

#: Предзаявки, написанные ДО введения правила 2026-10-27. Список может только СОКРАЩАТЬСЯ.
KNOWN_DEBT = {
    "b_insuff/glycol_oos_thermoml/PRE_DECLARATION.md",
    "b_insuff/glycol_oos_thermoml/PRE_DECLARATION_AMENDMENT_1.md",
    "cluster_certification/PRE_DECLARATION.md",
    "delta_phi_reread/PRE_DECLARATION.md",
    "e2_attribution_replicate/PRE_DECLARATION.md",
    "e2_crystal_detach/PRE_DECLARATION.md",
    "e2_seed43_pair/PRE_DECLARATION.md",
    "oracle_segment_sweep/PRE_DECLARATION.md",
    "sigma_core_boundary_sweep/PRE_DECLARATION.md",
    "sigma_core_boundary_water/PRE_DECLARATION.md",
    "sigma_corner_threshold_sweep/PRE_DECLARATION.md",
    "sigma_hb_retrained/PRE_DECLARATION.md",
    "sigma_hb_shift/PRE_DECLARATION.md",
    "sigma_location_robustness/PRE_DECLARATION.md",
    "sigma_role_injection/PRE_DECLARATION.md",
}


def _found() -> dict[str, Path]:
    return {str(p.relative_to(ROOT / "results")): p
            for p in sorted((ROOT / "results").glob("**/PRE_DECLARATION*.md"))}


def _has_block(p: Path) -> bool:
    t = p.read_text(encoding="utf8")
    i, j = t.find(OPEN), t.find(CLOSE)
    return i >= 0 and j > i


def test_every_new_predeclaration_declares_its_threshold_surfaces() -> None:
    missing = [name for name, p in _found().items()
               if name not in KNOWN_DEBT and not _has_block(p)]
    assert not missing, (
        "новая предзаявка без блока порогов: " + ", ".join(missing) + ".\n"
        f"Добавьте между {OPEN} и {CLOSE} строку на каждый численный порог: на чём он ИЗМЕРЕН и "
        "что ОГРАНИЧИВАЕТ. Если порогов нет -- напишите это внутри блока. Образец: "
        "results/class2_transfer/PRE_DECLARATION.md"
    )


def test_the_debt_list_only_shrinks() -> None:
    """Если долг починен, он обязан уйти из списка -- иначе список перестаёт что-то значить."""
    found = _found()
    fixed = [name for name in sorted(KNOWN_DEBT)
             if name in found and _has_block(found[name])]
    assert not fixed, (
        "в списке долга стоят предзаявки, у которых блок порогов УЖЕ есть: " + ", ".join(fixed)
        + ". Уберите их из KNOWN_DEBT."
    )


def test_the_debt_list_has_no_phantoms() -> None:
    found = _found()
    gone = sorted(n for n in KNOWN_DEBT if n not in found)
    assert not gone, f"в списке долга файлы, которых нет: {gone}"


def test_the_reference_block_is_a_table_and_not_a_sentence() -> None:
    """Образец должен оставаться образцом: таблица со всеми тремя графами."""
    p = ROOT / "results/class2_transfer/PRE_DECLARATION.md"
    t = p.read_text(encoding="utf8")
    block = t[t.find(OPEN):t.find(CLOSE)]
    head = re.search(r"\|\s*порог\s*\|\s*измерен на\s*\|\s*что ограничивает", block)
    assert head is not None, "в образце нет шапки таблицы «порог | измерен на | что ограничивает»"
    rows = [ln for ln in block.splitlines() if ln.strip().startswith("|")]
    assert len(rows) >= 5, f"в образце {len(rows)} строк таблицы, ожидается шапка плюс пороги"
