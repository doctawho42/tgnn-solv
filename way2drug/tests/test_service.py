"""Тесты сервиса. Запуск: KMP_DUPLICATE_LIB_OK=TRUE python -m pytest way2drug/tests -q

Проверяются инварианты, а не красота вывода: выравнивание ответа со вводом,
детерминированность, поведение на мусорном вводе и то, что предупреждения об области
применимости действительно зажигаются. Число само по себе не тестируется -- оно
проверяется скриптом verify_against_checkpoint.py против записанной метрики.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "way2drug"))

from w2d_solubility.predictor import (  # noqa: E402
    DILUTE_LIMIT_X2,
    SIMILARITY_WARN,
    SolubilityPredictor,
    canonical_smiles,
)

PARACETAMOL = "CC(=O)Nc1ccc(O)cc1"
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
CAFFEINE = "CN1C=NC2=C1C(=O)N(C)C(=O)N2C"


@pytest.fixture(scope="module")
def predictor() -> SolubilityPredictor:
    return SolubilityPredictor()


def test_ensemble_loads_three_seeds(predictor):
    d = predictor.describe()
    assert d["n_members"] == 3
    assert sorted(d["seeds"]) == [42, 43, 44]
    # Метрики из чекпойнтов должны быть в диапазоне, о котором говорит статья.
    assert all(1.5 < m < 1.9 for m in d["reported_test_mae_ln_x2"])


def test_panel_is_covered_and_sorted(predictor):
    res = predictor.predict_panel(PARACETAMOL)
    assert len(res["predictions"]) == predictor.panel["n_solvents"]
    names = {p["solvent_smiles"] for p in res["predictions"]}
    assert names == {s["smiles"] for s in predictor.panel["solvents"]}
    lnx = [p["ln_x2"] for p in res["predictions"]]
    assert lnx == sorted(lnx, reverse=True), "панель обязана приходить отсортированной"


def test_row_order_is_preserved(predictor):
    """Ответ должен соответствовать вводу построчно, а не «примерно».

    Датасет выбрасывает нераспознанные SMILES, и если бы сервис не выравнивал ответ,
    сдвиг проявился бы не падением, а тихой подменой: числа одного растворителя
    оказались бы приписаны другому.
    """
    pairs = [(PARACETAMOL, "O", 298.15),
             (PARACETAMOL, "CCO", 298.15),
             (ASPIRIN, "O", 298.15)]
    raw = predictor._predict_pairs(pairs)
    assert raw.shape == (3, 3)
    # Парацетамол в этаноле растворим заметно лучше, чем в воде -- это устойчивый факт,
    # и он же ловит перестановку первых двух строк.
    water, ethanol = raw[:, 0].mean(), raw[:, 1].mean()
    assert ethanol > water + 1.0


def test_prediction_is_deterministic(predictor):
    a = predictor.predict_panel(CAFFEINE)
    b = predictor.predict_panel(CAFFEINE)
    assert [p["ln_x2"] for p in a["predictions"]] == [p["ln_x2"] for p in b["predictions"]]


def test_bad_smiles_is_an_answer_not_a_crash(predictor):
    res = predictor.predict_panel("это не структура")
    assert "error" in res and "predictions" not in res


def test_known_compound_is_flagged_as_seen_in_training(predictor):
    res = predictor.predict_panel(PARACETAMOL)
    app = res["applicability"]
    assert app["nearest_training_similarity"] == pytest.approx(1.0, abs=1e-6)
    assert any("обучающей выборке" in n for n in app["notes"]), (
        "вещество из обучающей выборки обязано быть помечено: иначе пользователь "
        "примет его предсказание за независимую оценку точности")


def test_polymer_is_flagged_by_size_not_by_similarity(predictor):
    """Полимер обязан быть отвергнут -- и отвергает его именно сторож размера.

    Этот тест написан против конкретной слепоты метрики. Декапептид глицина даёт
    Танимото 0.90 к ДИПЕПТИДУ, потому что двоичный Morgan-фингерпринт радиуса 2 у
    полимера и его олигомера включает одни и те же биты. По одной похожести сервис
    объявил бы его «внутри области применимости» -- что и происходило, пока сторож
    размера не был добавлен.
    """
    peptide = "NCC(=O)" + "NCC(=O)" * 8 + "NCC(=O)O"
    app = predictor.predict_panel(peptide)["applicability"]
    assert app["nearest_training_similarity"] > SIMILARITY_WARN, (
        "если похожесть вдруг упала ниже порога, тест перестал проверять то, "
        "ради чего написан")
    assert not app["in_domain"]
    assert any("размер вне обучающего диапазона" in n for n in app["notes"])


def test_unusual_chemistry_is_flagged_by_similarity(predictor):
    """А здесь наоборот: размер обычный, но химии такой модель не видела."""
    app = predictor.predict_panel("[Pt](Cl)(Cl)(N)N")["applicability"]
    assert not app["in_domain"]
    assert any("Танимото" in n for n in app["notes"])


def test_interval_is_never_narrower_than_the_noise_floor(predictor):
    res = predictor.predict_panel(ASPIRIN)
    for p in res["predictions"]:
        lo, hi = p["ln_x2_interval"]
        assert hi - lo >= 2 * 1.96 * 0.7 - 1e-6, (
            "интервал уже межлабораторного разброса обещает точность, которой нет "
            "ни у одной модели")


def test_concentration_is_withheld_where_it_would_be_wrong(predictor):
    res = predictor.predict_panel(PARACETAMOL)
    for p in res["predictions"]:
        if p["concentration_g_per_l"] is None:
            assert p["concentration_note"], "отказ от пересчёта обязан объясняться"
        else:
            assert p["mole_fraction"] <= DILUTE_LIMIT_X2 + 1e-12
            assert p["concentration_g_per_l"] > 0


def test_temperature_changes_the_answer(predictor):
    cold = predictor.predict_panel(ASPIRIN, temperature=283.15)
    hot = predictor.predict_panel(ASPIRIN, temperature=333.15)
    cold_map = {p["solvent_smiles"]: p["ln_x2"] for p in cold["predictions"]}
    hot_map = {p["solvent_smiles"]: p["ln_x2"] for p in hot["predictions"]}
    diffs = [hot_map[k] - cold_map[k] for k in cold_map]
    assert any(abs(d) > 0.05 for d in diffs), "температура обязана влиять на предсказание"
    # Растворимость твёрдого тела почти всегда растёт с температурой.
    assert sum(d > 0 for d in diffs) > len(diffs) / 2


def test_extreme_temperature_is_flagged(predictor):
    app = predictor.predict_panel(ASPIRIN, temperature=500.0)["applicability"]
    assert any("температура" in n for n in app["notes"])


def test_canonicalisation():
    assert canonical_smiles("OCC") == canonical_smiles("CCO")
    assert canonical_smiles("нет") is None


def test_mole_fraction_matches_ln_x2(predictor):
    for p in predictor.predict_panel(CAFFEINE)["predictions"]:
        assert p["mole_fraction"] == pytest.approx(math.exp(p["ln_x2"]), rel=1e-3)
