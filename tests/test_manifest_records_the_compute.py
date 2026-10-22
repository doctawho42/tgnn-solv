"""Манифест обязан записывать, ЧЕМ считали -- иначе провенанс теряется молча.

ЗАЧЕМ ЭТОТ ТЕСТ. В манифестах депонированных армов (`checkpoints/e5_leakfree/*.manifest.json`)
записаны `python_version` и `platform`, а версии torch, имени карты, драйвера и пика VRAM НЕТ.
Поэтому про те чекпойнты нельзя сказать, на каком torch они обучены, и при переезде на кластер
2026-10-22 это оказался первый вопрос, на который ответа не было. Снимок добавлен; тест держит его
на месте и, главное, держит его БЕЗОПАСНЫМ -- `runtime_snapshot` вызывают и чисто процессорные
скрипты, где torch может отсутствовать, а `nvidia-smi` отсутствует почти всегда.
"""
from __future__ import annotations

from tgnn_solv.artifacts import build_run_manifest, compute_snapshot, runtime_snapshot


def test_runtime_snapshot_carries_a_compute_block() -> None:
    snap = runtime_snapshot()
    assert "compute" in snap, (
        "в снимке нет блока compute -- вернулось то состояние, при котором нельзя сказать, "
        "на каком torch обучен чекпойнт")
    assert "torch" in snap["compute"]


def test_compute_snapshot_names_the_torch_version() -> None:
    c = compute_snapshot()
    # torch в тестовом окружении есть; если его нет, модуль обязан сказать это, а не упасть
    if c["torch"] is None:
        assert "note" in c
    else:
        assert c["torch"].count(".") >= 1, f"версия torch выглядит странно: {c['torch']!r}"
    assert "cuda_available" in c or c["torch"] is None


def test_compute_snapshot_is_safe_without_cuda_and_without_nvidia_smi() -> None:
    """Главное свойство: функция не ломает манифест там, где карты нет."""
    c = compute_snapshot()
    assert isinstance(c, dict)
    if not c.get("cuda_available"):
        # без карты полей про карту быть не должно, но и исключения -- тоже
        assert "peak_vram_allocated_gib" not in c
    assert "elapsed_since_module_import_s" in c


def test_peak_vram_is_reported_when_cuda_is_present() -> None:
    """На машине с картой пик обязан присутствовать -- это и есть ответ «влезет ли»."""
    c = compute_snapshot()
    if c.get("cuda_available"):
        assert "peak_vram_allocated_gib" in c, "CUDA есть, а пика VRAM в снимке нет"
        assert c["peak_vram_allocated_gib"] >= 0.0
        assert "gpu_name" in c


def test_manifest_end_to_end_contains_the_compute_block() -> None:
    m = build_run_manifest("train", model_name="x", model_family="tgnn_solv")
    assert "compute" in m["runtime"]
    assert set(m["runtime"]) >= {"python_version", "platform", "git_commit", "compute"}
