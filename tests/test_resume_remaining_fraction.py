"""Раннер читает ОСТАТОК работы из курсора чекпойнта, а не считает плечо полным.

ЗАЧЕМ ЭТОТ ФАЙЛ. 2026-10-03 два плеча E2 были сняты по бюджету сессии на 75 и 80 эпохе из
110, потратив 10.73 ч каждое и не оставив файлов предсказаний. Каждому оставалось около пяти
часов, то есть одна сессия. Но прикидка «влезет ли плечо» в run_arms.py берёт медиану
УСПЕШНЫХ записей журнала, а у снятого плеча ok=False -- список пуст, и в дело идёт константа
ARM_HOURS_ASSUMED. Для возобновляемого плеча это завышение втрое, и при коротком остатке
бюджета раннер отказался бы начинать то, что успевает закончиться.

Курсор при этом лежит прямо в чекпойнте (resume_state), и train.py его честно исполняет:
проверено прогоном 2026-10-04 -- «Skipping sigma-warmup on resume», «Resuming from epoch
45/70», и train-loss 0.3135 как продолжение, а не значение с нуля.

ЧТО ЗАКРЕПЛЕНО: арифметика доли по фазам, пропуск чекпойнта без курсора или с завершённым
статусом, и устойчивость к битому файлу -- потому что недокачанный чекпойнт из выгрузки
обязан дать None, а не уронить сессию, которая на нём и держится.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/kaggle"))

from run_arms import ARM_HOURS_ASSUMED, remaining_fraction  # noqa: E402

PHASES = (30, 70, 10)          # расписание configs/cosmo_sac.yaml, 110 эпох всего


def _ckpt(tmp_path: Path, state: object, name: str = "arm_seed42.pt") -> Path:
    p = tmp_path / name
    torch.save({"seed": 42, "model_state": {}, "resume_state": state}, p)
    return p


@pytest.mark.parametrize(
    "phase,nxt,expected_left",
    [
        (1, 0, 110),     # ничего не сделано
        (1, 15, 95),     # середина фазы 1
        (2, 45, 35),     # grounded_a, снято 2026-10-03
        (2, 50, 30),     # grounded_a_detachcrystal
        (2, 70, 10),     # фаза 2 дошла до конца, остались только 10 фазы 3
        (3, 5, 5),       # середина фазы 3
    ],
)
def test_fraction_matches_the_phase_arithmetic(tmp_path, phase, nxt, expected_left) -> None:
    f = remaining_fraction(
        _ckpt(tmp_path, {"status": "in_progress", "phase": phase,
                         "next_epoch_in_phase": nxt, "phase_epochs": PHASES[phase - 1]}),
        PHASES)
    assert f == pytest.approx(expected_left / sum(PHASES), abs=1e-9), (
        f"фаза {phase}, следующая эпоха {nxt}: доля {f} не отвечает остатку {expected_left} "
        f"из {sum(PHASES)}"
    )


def test_two_real_positions_give_the_hours_we_expect(tmp_path) -> None:
    """Проверка в тех единицах, в которых решение и принимается -- в часах."""
    for nxt, want_h in ((45, 5.41), (50, 4.64)):
        f = remaining_fraction(
            _ckpt(tmp_path, {"status": "in_progress", "phase": 2,
                             "next_epoch_in_phase": nxt, "phase_epochs": 70},
                  name=f"arm_{nxt}.pt"), PHASES)
        got = ARM_HOURS_ASSUMED * f
        assert got == pytest.approx(want_h, abs=0.05), (
            f"следующая эпоха {nxt}: прикидка {got:.2f} ч, ожидалась около {want_h} ч"
        )
        assert got < ARM_HOURS_ASSUMED / 2, (
            "возобновляемое плечо обязано оцениваться заметно дешевле полного, иначе правка "
            "не делает того, ради чего написана"
        )


@pytest.mark.parametrize("state", [
    None,                                              # курсора нет вовсе
    {"status": "completed"},                           # плечо уже закончено
    {"status": "in_progress"},                         # курсор без фазы -- берутся умолчания
])
def test_no_usable_cursor_returns_none_or_full(tmp_path, state) -> None:
    f = remaining_fraction(_ckpt(tmp_path, state), PHASES)
    if state is not None and state.get("status") == "in_progress":
        # фаза и эпоха по умолчанию 1 и 0 -> остаток ПОЛНЫЙ, а не None
        assert f == pytest.approx(1.0)
    else:
        assert f is None, (
            "без годного курсора доля обязана быть None, чтобы прикидка упала на константу, "
            "а не на случайное число"
        )


def test_a_corrupt_checkpoint_does_not_kill_the_session(tmp_path) -> None:
    """Недокачанный чекпойнт обязан дать None, а не исключение.

    Файл приезжает из выгрузки Kaggle через версию датасета; обрыв на этом пути реален, и
    сессия, которая на нём держится, не должна от него падать.
    """
    bad = tmp_path / "broken_seed42.pt"
    bad.write_bytes(b"\x80\x02 not a torch file at all")
    assert remaining_fraction(bad, PHASES) is None
