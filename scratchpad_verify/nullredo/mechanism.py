#!/usr/bin/env python3
r"""Why the null's D distribution moves: level or spread?

D is a MAX over 59 strata of MSE - 2 B_insuff.  Two things can move it: the LEVEL of B (a looser
bound lowers every margin) and the SPREAD of B across strata (a bound that varies hands the max a
second source of variation).  Under the coarsening B is nearly flat by construction; under the
cross-fit it is not.  This records, per null draw and per estimator, the across-stratum
distribution of B and of the margin at the headline cell, so the two effects are separated
instead of asserted.

Same rows, same permutations, same seed as redo_null.py.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd

ROOT = Path("/Users/nikitapolomosnov/PycharmProjects/tgnn-solv")
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_b_insuff_map_multiplicity_null as ORIG                     # noqa: E402
from run_b_insuff_estimator_grid import lotv                          # noqa: E402
from run_b_insuff_stratified_map import (                             # noqa: E402
    DDOF, MIN_BOUNDABLE, N_BINS, pair_unit, prepare,
)
import run_b_insuff_crossfit_scoring as SCORE                         # noqa: E402
import run_b_insuff_crossfit_estimator as DECL                        # noqa: E402
from redo_null import harness, permutations                           # noqa: E402

OUT = Path(__file__).resolve().parent / "mechanism.json"


def main() -> int:
    n_draws = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    broad477, conv = prepare(DECL.BROAD, "broad")
    exact, by14 = SCORE.profile_table()
    broad, Zb, info = SCORE.attach_zstar(broad477, exact, by14)
    assert info["n_out"] == 473
    h = harness(broad, conv)
    d = broad.reset_index(drop=True)
    groups = d["pair_key"].astype(str).to_numpy()
    sq, _ = SCORE.oof_sq(Zb, d["m"].to_numpy(float), groups, groups,
                         d["source_doi"].astype(str).to_numpy(), "rf")

    g = h["gs"]["row"]["res"]
    m = h["ms"]["row"]

    def panel(row_class, row_coarse, row_fine, row_solfam, row_role):
        """Across the strata of ONE labelling: B and margin at row::res, boundable strata only."""
        rows = []
        for name, msk in ORIG.build_strata(row_class, row_coarse, row_fine, row_solfam,
                                           row_role, len(m)):
            idx = np.flatnonzero(msk)
            if len(idx) < MIN_BOUNDABLE:
                continue
            gg, mm = g[idx], m[idx]
            mse = float(np.mean((mm - gg) ** 2))
            bb = lotv(gg, mm, N_BINS, DDOF)
            bc = float(np.mean(sq[idx]))
            rows.append((mse, bb, bc, mse - 2 * bb, mse - 2 * bc))
        a = np.array(rows)
        return {
            "n_boundable_strata": int(len(a)),
            "mean_B_bin": float(a[:, 1].mean()), "sd_B_bin": float(a[:, 1].std(ddof=1)),
            "range_B_bin": float(np.ptp(a[:, 1])),
            "mean_B_cf": float(a[:, 2].mean()), "sd_B_cf": float(a[:, 2].std(ddof=1)),
            "range_B_cf": float(np.ptp(a[:, 2])),
            "sd_margin_bin": float(a[:, 3].std(ddof=1)),
            "sd_margin_cf": float(a[:, 4].std(ddof=1)),
            "max_margin_bin": float(a[:, 3].max()), "max_margin_cf": float(a[:, 4].max()),
            "mean_margin_bin": float(a[:, 3].mean()), "mean_margin_cf": float(a[:, 4].mean()),
        }

    obs = panel(*h["rows_from"](np.arange(h["n_sv"]), np.arange(h["n_su"])))
    perms = permutations(h["n_sv"], h["n_su"], n_draws)
    draws = [panel(*h["rows_from"](a, b)) for a, b in perms]
    df = pd.DataFrame(draws)
    res = {
        "n_draws": n_draws,
        "observed_chemical_labelling": obs,
        "null_median": {k: round(float(df[k].median()), 4) for k in df.columns},
        "null_p90_max_margin_bin": round(float(np.percentile(df["max_margin_bin"], 90)), 4),
        "null_p90_max_margin_cf": round(float(np.percentile(df["max_margin_cf"], 90)), 4),
        "reading": (
            "sd_B_cf >> sd_B_bin under BOTH the chemical labelling and a random one means the "
            "cross-fit's extra spread across strata is a property of the estimator, not of "
            "chemistry; a max-over-strata statistic inherits it."),
    }
    OUT.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
