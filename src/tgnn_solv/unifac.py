"""Thin wrappers around `thermo` Modified UNIFAC for cached preprocessing.

The model should not call these functions inside a batched forward pass.
Use them in data-preparation scripts to precompute scalar priors/objectives.
"""

from __future__ import annotations

from functools import lru_cache
import math
from typing import Optional

from rdkit import Chem


@lru_cache(maxsize=1)
def _load_modified_unifac_tables():
    try:
        import thermo.unifac as unifac
        from thermo.unifac import load_group_assignments_DDBST, load_unifac_ip
    except ImportError as exc:
        raise ImportError(
            "Modified UNIFAC support requires optional packages: "
            "`pip install thermo chemicals lxml`."
        ) from exc

    load_group_assignments_DDBST()
    load_unifac_ip()
    return unifac


@lru_cache(maxsize=100_000)
def smiles_to_inchikey(smiles: str) -> Optional[str]:
    """Return RDKit Standard InChIKey for a SMILES string, or None."""
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    try:
        return Chem.MolToInchiKey(mol)
    except Exception:
        return None


@lru_cache(maxsize=100_000)
def modified_unifac_groups(smiles: str) -> Optional[tuple[tuple[int, int], ...]]:
    """Return DDBST Modified UNIFAC group assignment as a hashable tuple."""
    key = smiles_to_inchikey(str(smiles))
    if key is None:
        return None
    unifac = _load_modified_unifac_tables()
    groups = unifac.DDBST_MODIFIED_UNIFAC_assignments.get(key)
    if not groups:
        return None
    return tuple(sorted((int(k), int(v)) for k, v in groups.items()))


def _groups_dict(groups: tuple[tuple[int, int], ...]) -> dict[int, int]:
    return {int(k): int(v) for k, v in groups}


@lru_cache(maxsize=250_000)
def modified_unifac_lngamma_inf(
    solute_smiles: str,
    solvent_smiles: str,
    temperature: float,
    *,
    temperature_decimals: int = 3,
) -> Optional[float]:
    """Compute ln(gamma_inf) for solute infinitely diluted in solvent.

    Uses Modified UNIFAC Dortmund 2016 interaction parameters as exposed by
    `thermo.unifac`. Returns None when DDBST has no group assignment or when
    UNIFAC cannot evaluate the pair.
    """
    T = round(float(temperature), int(temperature_decimals))
    if not math.isfinite(T) or T <= 0.0:
        return None

    sol_groups = modified_unifac_groups(str(solute_smiles))
    slv_groups = modified_unifac_groups(str(solvent_smiles))
    if sol_groups is None or slv_groups is None:
        return None

    unifac = _load_modified_unifac_tables()
    try:
        ge = unifac.UNIFAC.from_subgroups(
            T=T,
            xs=[1e-9, 1.0 - 1e-9],
            chemgroups=[_groups_dict(sol_groups), _groups_dict(slv_groups)],
            subgroups=unifac.DOUFSG,
            interaction_data=unifac.DOUFIP2016,
            version=1,
        )
        gamma = float(ge.gammas_infinite_dilution()[0])
    except Exception:
        return None

    if not math.isfinite(gamma) or gamma <= 0.0:
        return None
    return float(math.log(gamma))
