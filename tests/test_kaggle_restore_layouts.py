"""The RESTORE cell must find a previous session's output wherever Kaggle chose to mount it.

This cell has now failed twice in production, both times silently in the sense that mattered: it
printed `0 checkpoints carried forward`, the arm retrained from epoch 0, and the budget was spent
before anyone looked.  The two causes were independent --

  * `kaggle datasets create --dir-mode zip` extracts each top-level directory's CONTENTS at the
    dataset root, so a staged `out/checkpoints/...` arrives as `checkpoints/...`; and
  * the dataset mounts at `/kaggle/input/datasets/<owner>/<slug>/`, two levels below
    `/kaggle/input`, so a one-level walk never reaches it.

-- which is why the test enumerates the CROSS of both axes rather than the two observed cases.  The
cell ships as a string, so the string is what gets executed here, with the two absolute roots
rewritten to a tmpdir.  Testing a reimplementation would have passed on both production failures.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "kaggle"))

import make_notebook  # noqa: E402


def _run(tmp_path: Path, *, expect_resume: bool = False, bundle: Path | None = None):
    """Execute the real RESTORE source against a fake mount tree, returning its namespace."""
    src = make_notebook.RESTORE
    assert '"/kaggle/input"' in src and '"/kaggle/working/out"' in src
    src = src.replace('"/kaggle/input"', repr(str(tmp_path / "input")))
    src = src.replace('"/kaggle/working/out"', repr(str(tmp_path / "working" / "out")))
    ns = {"__name__": "restore_cell"}
    if bundle is not None:
        ns["BUNDLE"] = bundle
    import os
    old = os.environ.get("TGNN_EXPECT_RESUME")
    if expect_resume:
        os.environ["TGNN_EXPECT_RESUME"] = "1"
    else:
        os.environ.pop("TGNN_EXPECT_RESUME", None)
    try:
        exec(compile(src, "RESTORE", "exec"), ns)
    finally:
        if old is None:
            os.environ.pop("TGNN_EXPECT_RESUME", None)
        else:
            os.environ["TGNN_EXPECT_RESUME"] = old
    return ns


def _seed_output(root: Path) -> None:
    """A previous session's output dataset: one checkpoint and one prediction file."""
    (root / "checkpoints").mkdir(parents=True, exist_ok=True)
    (root / "checkpoints" / "grounded_a_seed42.pt").write_bytes(b"ckpt")
    (root / "results" / "seed_42").mkdir(parents=True, exist_ok=True)
    (root / "results" / "seed_42" / "grounded_a_predictions.csv").write_text("x\n")


# The cross of both axes: {flat mount, nested mount} x {wrapper intact, wrapper stripped}.
LAYOUTS = {
    "flat_wrapped": "input/tgnn-solv-e2-out/out",
    "flat_stripped": "input/tgnn-solv-e2-out",
    "nested_wrapped": "input/datasets/polomoshnov/tgnn-solv-e2-out/out",
    "nested_stripped": "input/datasets/polomoshnov/tgnn-solv-e2-out",
}


@pytest.mark.parametrize("layout", sorted(LAYOUTS))
def test_restores_from_every_layout(tmp_path, layout):
    _seed_output(tmp_path / LAYOUTS[layout])
    ns = _run(tmp_path, expect_resume=True)
    assert len(ns["ckpts"]) == 1, f"{layout}: checkpoint not carried forward"
    assert len(ns["done"]) == 1, f"{layout}: predictions not carried forward"
    assert (tmp_path / "working/out/checkpoints/grounded_a_seed42.pt").read_bytes() == b"ckpt"


def test_nested_stripped_is_the_layout_that_failed_in_production(tmp_path):
    """The 2026-10-04 case, named on its own so a regression reads as itself in the report."""
    _seed_output(tmp_path / "input/datasets/polomoshnov/tgnn-solv-e2-out")
    ns = _run(tmp_path, expect_resume=True)
    assert [p.name for p in ns["ckpts"]] == ["grounded_a_seed42.pt"]


def test_guard_fires_when_a_resume_session_restores_nothing(tmp_path):
    (tmp_path / "input/datasets/polomoshnov/tgnn-solv-e5/code").mkdir(parents=True)
    with pytest.raises(AssertionError, match="TGNN_EXPECT_RESUME"):
        _run(tmp_path, expect_resume=True)


def test_first_session_may_restore_nothing(tmp_path):
    (tmp_path / "input").mkdir(parents=True)
    ns = _run(tmp_path, expect_resume=False)
    assert ns["ckpts"] == [] and ns["done"] == []


def test_input_bundle_is_not_mistaken_for_previous_output(tmp_path):
    """The code/data bundle carries its own `results/` tree; restoring it would be a false positive.

    The guard must still fire: a bundle on disk is not a previous session's work.
    """
    bundle = tmp_path / "input/datasets/polomoshnov/tgnn-solv-e5"
    (bundle / "code").mkdir(parents=True)
    art = bundle / "data" / "results" / "sigma_profile_artifact"
    art.mkdir(parents=True)
    (art / "sigma_profiles.csv").write_text("sigma\n")
    with pytest.raises(AssertionError, match="TGNN_EXPECT_RESUME"):
        _run(tmp_path, expect_resume=True, bundle=bundle)
    assert not (tmp_path / "working/out/results/sigma_profile_artifact").exists()


def test_output_dataset_restored_while_bundle_is_attached(tmp_path):
    """Both datasets attached at once -- the real configuration of a resume session."""
    bundle = tmp_path / "input/datasets/polomoshnov/tgnn-solv-e5"
    (bundle / "code").mkdir(parents=True)
    art = bundle / "data" / "results" / "sigma_profile_artifact"
    art.mkdir(parents=True)
    (art / "sigma_profiles.csv").write_text("sigma\n")
    _seed_output(tmp_path / "input/datasets/polomoshnov/tgnn-solv-e2-out")
    ns = _run(tmp_path, expect_resume=True, bundle=bundle)
    assert len(ns["ckpts"]) == 1
    assert not (tmp_path / "working/out/results/sigma_profile_artifact").exists()

def test_two_output_datasets_both_restore_into_one_tree(tmp_path):
    """Репликат пишет ДВА выходных датасета -- по одному на плечо, и восстановить надо оба.

    Плечи сида 43 идут параллельными ядрами, каждое со своим выходным датасетом, и следующая
    сессия подключает оба. Это НОВОЕ условие: прежние тесты покрывали один выходной датасет рядом
    с бандлом. Если цикл по кандидатам возьмёт только первый, одно плечо тихо начнётся с нуля --
    та же форма отказа, что дважды стоила ядра.
    """
    bundle = tmp_path / "input/datasets/polomoshnov/tgnn-solv-e5"
    (bundle / "code").mkdir(parents=True)
    a = tmp_path / "input/datasets/polomoshnov/tgnn-solv-e2r43a"
    b = tmp_path / "input/datasets/polomoshnov/tgnn-solv-e2r43b"
    for root, arm in ((a, "grounded_a"), (b, "grounded_a_detachcrystal")):
        (root / "checkpoints").mkdir(parents=True)
        (root / "checkpoints" / f"{arm}_seed43.pt").write_bytes(arm.encode())
        (root / "results" / "seed_43").mkdir(parents=True)
        (root / "results" / "seed_43" / f"{arm}_predictions.csv").write_text("x\n")
    ns = _run(tmp_path, expect_resume=True, bundle=bundle)
    names = sorted(p.name for p in ns["ckpts"])
    assert names == ["grounded_a_detachcrystal_seed43.pt", "grounded_a_seed43.pt"], (
        f"восстановлено {names}: из двух выходных датасетов подхвачен не оба, и плечо, чей "
        f"чекпойнт потерян, начнёт обучение с нуля")
    assert len(ns["done"]) == 2
    out = tmp_path / "working/out/checkpoints"
    assert (out / "grounded_a_seed43.pt").read_bytes() == b"grounded_a"
    assert (out / "grounded_a_detachcrystal_seed43.pt").read_bytes() == b"grounded_a_detachcrystal"
