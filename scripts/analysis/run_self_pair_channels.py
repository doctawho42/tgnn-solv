#!/usr/bin/env python3
"""Decompose the self-pair identity violation by the channel the role split reaches it through.

WHY THIS EXISTS.  methods.tex states that on a self-pair the violation "is the role gap and
nothing else", and then prescribes the repair: "Tying the two roles is the change this calls
for".  Both are true on the arm the number was measured on, and the prescription is incomplete
on the other arm.  The role-adapted readout feeds THREE numbers, not one:

  (1) the profile SHAPE p(sigma)/A          -> the residual term
  (2) the cavity AREA A                     -> the residual prefactor and the SG area fraction
  (3) the molar VOLUME V_m from head_aux    -> the Staverman-Guggenheim term only

Channel (3) never touches the sigma-profile.  It is dead when cosmo_sac_wire_volume is False
(the default and configs/cosmo_sac.yaml's arm A, residual-only), where model.py:570-571 passes
V=None and CosmoSacLayer.ln_gamma_2 skips the combinatorial term entirely.  It is live on arm B,
where model.py:568-569 reads V_m off head_aux applied to the SAME two role-adapted readouts that
split the sigma-head.  There, tying the sigma-head alone would leave the identity broken.

Each channel is measured in isolation: one channel is given a 20% role mismatch and the other
two are held exactly equal.  20% is the order the measured adapter divergence implies
(max|diff| 0.321 on the 64-d readout, cosine -0.0148; results/role_asymmetry/self_pair.json).

Deposits results/role_asymmetry/self_pair_channels.json.
"""
from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402

PROFILES = ROOT / "results" / "sigma_profile_artifact" / "sigma_profiles.csv"
OUT = ROOT / "results" / "role_asymmetry" / "self_pair_channels.json"
N = 256
T_REF = 298.15
MISMATCH = 0.20
SEED = 0


def load_reference_table(path: Path):
    with open(path) as fh:
        rdr = csv.reader(fh)
        header = next(rdr)
        rows = [r for r in rdr if len(r) == len(header)]
    i_area, i_p0, i_v = (header.index("sigma_area"), header.index("sigma_p_0"),
                         header.index("v_cosmo"))
    area = np.array([float(r[i_area]) for r in rows])
    vol = np.array([float(r[i_v]) for r in rows])
    prof = np.array([[float(v) for v in r[i_p0:i_p0 + 51]] for r in rows])
    return prof, area, vol


def main() -> int:
    prof, area, vol = load_reference_table(PROFILES)
    rng = np.random.default_rng(SEED)
    sel = rng.choice(len(prof), size=N, replace=False)
    p = torch.tensor(prof[sel], dtype=torch.float32)
    A = torch.tensor(area[sel], dtype=torch.float32)
    V = torch.tensor(vol[sel], dtype=torch.float32)
    T = torch.full((N,), T_REF)

    # one fixed shape perturbation, reused across every cell so the arms differ only in
    # which channel is perturbed and whether the combinatorial term is on
    d = torch.tensor(rng.standard_normal((N, 51)), dtype=torch.float32)
    d = d - d.mean(1, keepdim=True)

    out = {
        "what": (
            "the self-pair identity ln gamma_2(M,M) = 0, broken by the encoder's role split, "
            "decomposed by the channel the split reaches ln gamma_2 through"
        ),
        "reference_profiles": str(PROFILES.relative_to(ROOT)),
        "n_molecules": int(N),
        "temperature_K": T_REF,
        "role_mismatch_fraction": MISMATCH,
        "seed": SEED,
        "arms": {},
    }

    for combinatorial in (False, True):
        layer = CosmoSacLayer().eval()
        layer.use_combinatorial = combinatorial
        arm = "arm_B_combinatorial_live" if combinatorial else "arm_A_residual_only"
        cells = {}
        for x2v in (0.001, 0.1, 0.5):
            x2 = torch.full((N,), x2v)
            x1 = 1.0 - x2
            with torch.no_grad():
                identical = layer.ln_gamma_2(x1, x2, p, p, A, A, V, V, T)
                p_alt = (p / A.unsqueeze(-1) + MISMATCH * d / 51).clamp_min(1e-8)
                p_alt = p_alt / p_alt.sum(1, keepdim=True) * A.unsqueeze(-1)
                shape_only = layer.ln_gamma_2(x1, x2, p, p_alt, A, A, V, V, T)
                A_alt = A * (1.0 + MISMATCH)
                area_only = layer.ln_gamma_2(
                    x1, x2, p, p / A.unsqueeze(-1) * A_alt.unsqueeze(-1), A, A_alt, V, V, T)
                volume_only = layer.ln_gamma_2(
                    x1, x2, p, p, A, A, V, V * (1.0 + MISMATCH), T)
            cells[f"x2_{x2v}"] = {
                "identical_max_abs": float(identical.abs().max()),
                "shape_only_median_abs": float(shape_only.abs().median()),
                "area_only_median_abs": float(area_only.abs().median()),
                "volume_only_median_abs": float(volume_only.abs().median()),
            }
        out["arms"][arm] = cells

    a = out["arms"]["arm_A_residual_only"]["x2_0.001"]
    b = out["arms"]["arm_B_combinatorial_live"]["x2_0.001"]
    out["headline"] = {
        "arm_A_area_and_volume_cancel_exactly": (
            a["area_only_median_abs"] == 0.0 and a["volume_only_median_abs"] == 0.0
        ),
        "arm_A_shape_only_median_abs": a["shape_only_median_abs"],
        "arm_B_volume_only_median_abs": b["volume_only_median_abs"],
        "arm_B_area_only_median_abs": b["area_only_median_abs"],
        "reading": (
            "On arm A the residual term is a function of the two SHAPES alone: a 20% role "
            "mismatch on the area or on the volume moves ln gamma_2 by exactly zero, so the "
            "whole violation is the profile disagreement and tying the sigma-head restores the "
            "identity. On arm B the same role split also reaches ln gamma_2 through head_aux's "
            "V_m, and a volume mismatch alone breaks the identity with the profiles in perfect "
            "agreement -- so there the repair has to cover the aux head as well."
        ),
        "config_gate": (
            "cosmo_sac_wire_volume (config.py:184, default False; configs/cosmo_sac.yaml:36 "
            "sets arm A false, arm B flips it via --set). model.py:563-571 is the branch."
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for arm, cells in out["arms"].items():
        print(f"\n  {arm}")
        for k, c in cells.items():
            print(f"    {k:<10} identical {c['identical_max_abs']:8.2e} | "
                  f"shape {c['shape_only_median_abs']:7.4f} | "
                  f"area {c['area_only_median_abs']:7.4f} | "
                  f"volume {c['volume_only_median_abs']:7.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
