from __future__ import annotations

from pathlib import Path

from tgnn_solv.chemistry.cosmors import embed_smiles_3d
from tgnn_solv.chemistry.cosmors import infer_charge_and_multiplicity
from tgnn_solv.chemistry.cosmors import write_cosmorsxyz
from tgnn_solv.chemistry.cosmors import write_orca_cosmors_input


def test_infer_charge_and_multiplicity_handles_ionic_and_radical_cases() -> None:
    charge, multiplicity = infer_charge_and_multiplicity(
        embed_smiles_3d("[NH4+]")[0]
    )
    assert charge == 1
    assert multiplicity == 1


def test_write_cosmors_files_from_embedded_smiles(tmp_path: Path) -> None:
    mol, charge, multiplicity = embed_smiles_3d("CCO")

    cosmorsxyz = write_cosmorsxyz(
        mol,
        tmp_path / "ethanol.cosmorsxyz",
        charge=charge,
        multiplicity=multiplicity,
    )
    inp = write_orca_cosmors_input(
        mol,
        tmp_path / "ethanol.inp",
        basename="ethanol",
        charge=charge,
        multiplicity=multiplicity,
        nprocs=2,
        maxcore_mb=750,
    )

    xyz_text = cosmorsxyz.read_text(encoding="utf-8")
    inp_text = inp.read_text(encoding="utf-8")

    assert xyz_text.splitlines()[1] == f"{charge} {multiplicity}"
    assert 'solventfilename "ethanol"' in inp_text
    assert "%pal nprocs 2 end" in inp_text
    assert "%maxcore 750" in inp_text
