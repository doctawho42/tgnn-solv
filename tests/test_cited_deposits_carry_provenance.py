"""Депозит, на который ссылается НЕСУЩИЙ документ, обязан нести провенанс. Храповик.

ЗАЧЕМ. 2026-10-23 выяснилось, что центральное сравнение проекта -- nrtl 1.795 против
directgnn 1.702 из `results/e5_sigma_grounding/THREE_SEED_SUMMARY.md` -- посчитано с CSV
предсказаний, у которых нет ни манифеста, ни коммита, ни даты обучения, ни записи об окружении.
Узнать это удалось только прямым поиском, через три месяца после того, как число попало в статью.

ПОЧЕМУ ТЕСТ, А НЕ ПРАВКА `.gitignore`. Соблазнительно разрешить провенанс по шаблону
(`!results/**/*.manifest.json`). Так нельзя: git не умеет вернуть файл, если исключён его
родительский каталог, а `results/*` исключает каталоги первого уровня. Рабочий вариант требовал бы
разрешать спуск на каждом уровне вложенности, и один промах в этой лестнице начал бы тащить в
репозиторий гигабайты предсказаний. Предсказания не отслеживаются НАМЕРЕННО -- их 3.2 ГБ.

Поэтому чинится не хранение, а ОТСУТСТВИЕ: тест ловит депозит, который процитировали, не записав,
откуда он. Существующие нарушения перечислены ниже и признаны долгом; список может только
СОКРАЩАТЬСЯ. Новое нарушение роняет набор.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Документы, ссылка из которых делает депозит несущим.
LOAD_BEARING = (
    "CLAUDE.md",
    "PROJECT_DESCRIPTION.md",
    "paper/grounding_paradox.tex",
    "paper/grounding_paradox_si.tex",
    "results/PAPER_PHASE0_FINDINGS.md",
)
CLAIM_FILES = ("RESULTS.md", "summary.json", "comparison.json", "reading.json")
CLAIM_GLOBS = ("*SUMMARY*.md", "*VERDICT*.json", "*verdict*.json")
PROV_GLOBS = ("*.manifest.json", "run_meta.json", "provenance.json", "gate.json")
DATE = re.compile(r"20\d\d-\d\d-\d\d")
CKPT = re.compile(r"checkpoints?/[A-Za-z0-9_./{}-]+")

#: ДОЛГ на 2026-10-23. Восемь депозитов процитированы несущими документами без провенанса.
#: Для прогонов, случившихся месяцы назад, провенанс уже не восстановить -- это и есть цена.
#: Список может только сокращаться: добавление сюда нового имени означает, что защита не сработала.
KNOWN_DEBT = {
    "results/b_insuff",                      # статья; crossfit_verdict.json
    "results/dcp_correction_audit",          # CLAUDE.md
    "results/e5_sigma_grounding",            # статья + CLAUDE.md; ИЗМЕРЕНИЕ ЗАПИСИ
    "results/external_baseline_comparison",  # статья
    "results/identifiability_audit",         # PHASE0; входы самоописаны конфигом (аналитика)
    "results/noise_floor",                   # PHASE0
    "results/segment_convergence",           # CLAUDE.md
    "results/sigma_profile_artifact",        # статья + PHASE0
}


def _has_claim(d: Path) -> bool:
    return any((d / c).is_file() for c in CLAIM_FILES) or any(
        any(d.glob(g)) for g in CLAIM_GLOBS)


def _provenance_level(d: Path) -> str:
    if any(any(d.glob(g)) for g in PROV_GLOBS):
        return "МАШИННЫЙ"
    for md in d.glob("*.md"):
        try:
            t = md.read_text(encoding="utf8", errors="replace")
        except OSError:
            continue
        if CKPT.search(t) and DATE.search(t):
            return "ПРОЗА"
    return "НЕТ"


def _cited_deposits() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for src in LOAD_BEARING:
        p = ROOT / src
        if not p.exists():
            continue
        text = p.read_text(encoding="utf8", errors="replace")
        for raw in re.findall(r"results/[A-Za-z0-9_./-]+", text):
            raw = raw.rstrip(".,);`\"'").rstrip("/")
            parts = raw.split("/")
            for n in (3, 2):
                cand = "/".join(parts[:n])
                if (ROOT / cand).is_dir() and _has_claim(ROOT / cand):
                    out.setdefault(cand, set()).add(src)
                    break
    return out


def test_no_new_cited_deposit_lacks_provenance() -> None:
    """Храповик: нарушений не больше, чем в признанном долге."""
    cited = _cited_deposits()
    missing = {k for k in cited if _provenance_level(ROOT / k) == "НЕТ"}
    new = sorted(missing - KNOWN_DEBT)
    assert not new, (
        "НОВЫЕ депозиты процитированы несущими документами без провенанса:\n  "
        + "\n  ".join(f"{k}  <- цитируют: {', '.join(sorted(cited[k]))}" for k in new)
        + "\n\nЗапишите рядом со сводкой манифест (`build_run_manifest` из tgnn_solv.artifacts) "
          "или назовите в RESULTS.md чекпойнты И дату прогона. Иначе через три месяца "
          "будет нельзя сказать, на каком коде посчитано -- как с results/e5_sigma_grounding.")


def test_the_debt_list_is_not_stale() -> None:
    """Имя, которое уже починили, обязано уйти из долга -- иначе храповик не затягивается."""
    cited = _cited_deposits()
    missing = {k for k in cited if _provenance_level(ROOT / k) == "НЕТ"}
    fixed = sorted(KNOWN_DEBT & set(cited) - missing)
    assert not fixed, (
        "эти депозиты уже несут провенанс, но всё ещё перечислены в KNOWN_DEBT -- уберите их, "
        f"чтобы храповик затянулся: {fixed}")


def test_the_measurement_of_record_is_in_the_debt_and_the_reason_is_recorded() -> None:
    """Самый дорогой случай прибит отдельно, чтобы его нельзя было молча потерять."""
    assert "results/e5_sigma_grounding" in KNOWN_DEBT
    audit = ROOT / "results/crossdating_audit/AUDIT.md"
    assert audit.exists(), "разбор кросс-датировки исчез -- причина долга перестала быть записанной"
    t = audit.read_text(encoding="utf8", errors="replace")
    assert "THREE_SEED_SUMMARY" in t and "1.702" in t, (
        "в разборе больше не названы ни сводка измерения записи, ни её число")
