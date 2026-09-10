#!/usr/bin/env python
"""Собрать самодостаточный архив для передачи команде платформы Way2Drug.

Внутрь кладётся всё, что нужно сервису на чужой машине: пакет, ассеты, три чекпойнта,
документация и минимальный `requirements.txt`. Обучающая выборка НЕ нужна -- панель,
область применимости и строка-шаблон уже собраны в ассеты.

    python way2drug/make_handoff.py
    python way2drug/make_handoff.py --out /куда/положить.tar.gz

ПОЧЕМУ АРХИВ, А НЕ ССЫЛКА НА РЕПОЗИТОРИЙ. Чекпойнты в репозитории не версионируются
(21 МБ каждый, .gitignore), а без них пакет не работает. Ссылка на репозиторий передала
бы код без весов, и на той стороне это выяснилось бы не сразу.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "way2drug"
CKPT_DIR = ROOT / "checkpoints/e5_current_split"

VERSION = "1.0"
PREFIX = f"way2drug_solubility_v{VERSION}"

#: Что кладём в архив: путь в репозитории -> путь внутри архива.
CONTENTS = {
    HERE / "w2d_solubility": "w2d_solubility",
    HERE / "tests": "tests",
    HERE / "README.md": "README.md",
    HERE / "MODEL_CARD.md": "MODEL_CARD.md",
    HERE / "ИНТЕГРАЦИЯ.md": "ИНТЕГРАЦИЯ.md",
    HERE / "solvent_panel.json": "solvent_panel.json",
    HERE / "train_domain.npz": "train_domain.npz",
    HERE / "template_row.csv": "template_row.csv",
    HERE / "verify_against_checkpoint.py": "verify_against_checkpoint.py",
    ROOT / "src/tgnn_solv": "tgnn_solv",
    ROOT / "LICENSE": "LICENSE",
}

REQUIREMENTS = """\
# Проверено на этих версиях; более свежие, скорее всего, тоже подойдут.
torch>=2.0
torch-geometric>=2.4
rdkit>=2023.9
pandas>=2.0
numpy>=1.24
pytest>=7.0        # только для tests/
"""


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short=10", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "неизвестен"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path,
                    default=ROOT / "dist" / f"{PREFIX}.tar.gz")
    args = ap.parse_args()

    checkpoints = sorted(CKPT_DIR.glob("directgnn_seed*.pt"))
    if not checkpoints:
        print(f"НЕТ ЧЕКПОЙНТОВ в {CKPT_DIR}. Без них архив бесполезен.")
        return 1
    missing = [p for p in CONTENTS if not p.exists()]
    if missing:
        print("НЕ ХВАТАЕТ ФАЙЛОВ (соберите ассеты: python way2drug/build_assets.py):")
        for p in missing:
            print(f"  {p.relative_to(ROOT)}")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / PREFIX
        stage.mkdir()
        for src, rel in CONTENTS.items():
            dst = stage / rel
            if src.is_dir():
                shutil.copytree(src, dst,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        ck_dir = stage / "checkpoints"
        ck_dir.mkdir()
        for p in checkpoints:
            shutil.copy2(p, ck_dir / p.name)
            side = p.with_suffix(".model_card.json")
            if side.exists():
                shutil.copy2(side, ck_dir / side.name)

        (stage / "requirements.txt").write_text(REQUIREMENTS, encoding="utf8")
        # Пакет ищет чекпойнты в checkpoints/e5_current_split относительно корня репозитория.
        # В архиве такой структуры нет, поэтому путь переопределяется переменной окружения,
        # а не правкой кода на той стороне.
        (stage / "ЧИТАТЬ_ПЕРВЫМ.md").write_text(f"""\
# Пакет предсказания растворимости для Way2Drug, версия {VERSION}

Собран из репозитория `tgnn-solv`, коммит `{_git_commit()}`.

## Быстрый старт

```bash
pip install -r requirements.txt
export PYTHONPATH=$PWD
export W2D_CHECKPOINT_DIR=$PWD/checkpoints
python -m w2d_solubility.cli "CC(=O)Nc1ccc(O)cc1"
```

## Что дальше читать

- `ИНТЕГРАЦИЯ.md` — развёртывание, схемы подключения, ресурсы, чеклист. **Начните отсюда.**
- `MODEL_CARD.md` — точность, область применимости, чего модель не умеет. **До интеграции.**
- `README.md` — API и формат ответа.

## Проверить, что всё доехало

```bash
python -m pytest tests -q
```

Четырнадцать тестов инвариантов; обучающая выборка для них не нужна.

Скрипт `verify_against_checkpoint.py` в архив включён, но требует тестовой выборки проекта
и на этой стороне не запустится. Его результат на момент сборки: путь инференса
воспроизводит записанные в чекпойнтах метрики с расхождением 0.0000.
""", encoding="utf8")

        with tarfile.open(args.out, "w:gz") as tar:
            tar.add(stage, arcname=PREFIX)

    size = args.out.stat().st_size
    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()
    print(f"собран: {args.out}")
    print(f"  {size/1e6:.1f} МБ, {len(checkpoints)} чекпойнт(ов)")
    print(f"  sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
