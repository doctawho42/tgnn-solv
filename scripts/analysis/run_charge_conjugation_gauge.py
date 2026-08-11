#!/usr/bin/env python3
"""Charge conjugation is an exact gauge freedom of the COSMO-SAC closure, and its per-molecule
version is cheap enough to be unidentifiable from solubility data.

WHY THIS EXISTS.  The paper reports that a sigma-profile trained through the closure alone stops
meaning the quantity it is named after, and attributes it to non-identifiability without saying
which directions are unidentified or why.  This file supplies the mechanism, and it is a property
of the CLOSURE and the CORPUS, not of any trained network -- every number here is computed on the
reference VT-2005 table.

THE INVARIANCE.  With J the bin reversal on the symmetric sigma grid (sigma -> -sigma),

    delta_w(-s_m, -s_n) = delta_w(s_m, s_n)   exactly.

The misfit 0.5*alpha'*(s_m+s_n)^2 is manifestly even.  The hydrogen-bond term survives for a less
obvious reason: under the flip the donor-side and acceptor-side factors SWAP,
    A = clamp(max(s_m,s_n) - s_hb, min=0) >= 0,  B = clamp(min(s_m,s_n) + s_hb, max=0) <= 0
    A' = -B,  B' = -A   =>   A'B' = AB,
so the product is preserved.  Mirroring every profile in a corpus therefore leaves every ln gamma
unchanged: donor and acceptor can be exchanged throughout and nothing measurable moves.

WHY THAT IS NOT MERELY A SIGN CONVENTION.  A global flip is one undetermined bit and would be fixed
by declaring a convention.  The measurement that decides whether this matters is the cost of
flipping ONE molecule while the rest of the corpus stays put -- the identifiability of a single
molecule's donor/acceptor assignment given its partners.  Stratified by the molecule's own
asymmetry, because a symmetric profile has no assignment to identify and a null there is trivial.

WHAT FOLLOWS FOR REPAIRS.  Any label-free constraint whose feasible set is itself J-invariant
leaves the degeneracy exactly where it found it: both branches remain feasible and equally good.
Charge neutrality (sum_k sigma_k p_k = 0), entropy penalties, symmetric support truncation and
role symmetry are all in that class.  So is intersecting several published kernel parameterisations,
since they are all parity-even -- measured here rather than assumed.  Only a parity-ODD constraint,
one that imports the donor/acceptor asymmetry of the molecular graph itself, can select a branch.

Deposits results/charge_conjugation/gauge.json.
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
OUT = ROOT / "results" / "charge_conjugation" / "gauge.json"
TEMPS = [273.15, 298.15, 323.15]
NOISE_FLOOR_LN = 0.7          # ~0.3 log10 inter-lab reproducibility, in natural-log units
N_PARTNERS = 60
N_PARTNER_DRAWS = 6
N_MOLECULES = 150
SEED = 3
# the solvent counts a solute actually gets: 2 is the sparse tail (26.5% of test solutes),
# 5 the test median, 9 the train median, 30 a generous set for reference
COVERAGE_S = [2, 5, 9, 30]
# label-noise standard deviations to read the detection threshold against, in natural-log units
NOISE_SIGMAS = [0.45, 0.7]
Z_DETECT = 2.0          # z = ||d||/sigma below this and the two branches are indistinguishable


def load_table():
    with open(PROFILES) as fh:
        rdr = csv.reader(fh)
        header = next(rdr)
        rows = [r for r in rdr if len(r) == len(header)]
    i_a, i_p = header.index("sigma_area"), header.index("sigma_p_0")
    area = np.array([float(r[i_a]) for r in rows])
    prof = np.array([[float(v) for v in r[i_p:i_p + 51]] for r in rows])
    return [r[0] for r in rows], area, prof


def main() -> int:
    smiles, area, P = load_table()
    shape = P / P.sum(1, keepdims=True)
    n_mol = len(P)
    layer = CosmoSacLayer().eval()
    grid = layer.sigma_grid
    rng = np.random.default_rng(SEED)

    out: dict = {
        "what": "charge conjugation sigma -> -sigma as a gauge freedom of the COSMO-SAC closure",
        "reference_profiles": str(PROFILES.relative_to(ROOT)),
        "n_reference_molecules": int(n_mol),
        "temperatures_K": TEMPS,
        "noise_floor_ln": NOISE_FLOOR_LN,
        "seed": SEED,
    }

    # ---- 1. the kernel is exactly parity-even ---------------------------------------------
    dw = layer.delta_w_base
    sm, sn = grid.view(-1, 1), grid.view(1, -1)
    misfit = 0.5 * layer.alpha_prime * (sm + sn) ** 2
    hb = layer.c_hb * torch.clamp(torch.maximum(sm, sn) - layer.sigma_hb, min=0.0) * torch.clamp(
        torch.minimum(sm, sn) + layer.sigma_hb, max=0.0)
    out["kernel"] = {
        "range_kcal_per_mol": [float(dw.min()), float(dw.max())],
        "max_abs_dw_minus_JdwJ": float((dw - dw.flip(0).flip(1)).abs().max()),
        "max_abs_misfit_residual": float((misfit - misfit.flip(0).flip(1)).abs().max()),
        "max_abs_hb_residual": float((hb - hb.flip(0).flip(1)).abs().max()),
        "float32_eps_times_max_abs_dw": float(
            np.finfo(np.float32).eps * dw.abs().max().item()),
        "reading": "the residual sits below float32 roundoff, so the invariance is exact",
    }

    # ---- 1b. the same, for the MODERN typed kernel, and the two conditions ------------------
    # The 2010/dsp kernel exists precisely to give donors and acceptors different coefficients,
    # and it does not break the symmetry: c_hb keys on the functional-group TYPE, never on the
    # sign of sigma, and the indicator sigma_m*sigma_n<0 is even. So this is a property of the
    # family, not of the 2002 algebraic form.
    # CONDITION ONE: the flip is BLOCKWISE. Reversing the whole 153-grid also permutes NHB<->OT
    # and is not a symmetry at all -- the residual there is larger than the effect.
    # CONDITION TWO: the grid must be symmetric about zero. cosmo_sac_sigma_min/max are
    # configurable to asymmetric values, and an asymmetric grid destroys the representability of
    # J as a bin permutation, so the invariance is not exact there.
    from tgnn_solv.layers import CosmoSac2010Layer  # noqa: E402  (local: only this section needs it)
    L10 = CosmoSac2010Layer().double().eval()
    nb = L10.n_bins
    j_block = torch.cat([torch.arange(t * nb + nb - 1, t * nb - 1, -1)
                         for t in range(L10.N_TYPE)])
    j_whole = torch.arange(L10.n_grid - 1, -1, -1)
    cond = {"blockwise": {}, "whole_grid_reversal_is_not_a_symmetry": {}}
    for t_k in (273.15, 298.15, 373.15):
        dw10 = L10._delta_w(torch.tensor([t_k], dtype=torch.float64))[0]
        cond["blockwise"][str(t_k)] = float(
            (dw10 - dw10[j_block][:, j_block]).abs().max())
        cond["whole_grid_reversal_is_not_a_symmetry"][str(t_k)] = float(
            (dw10 - dw10[j_whole][:, j_whole]).abs().max())
    # asymmetric support: build a 2002 kernel on a grid that is not centred on zero
    asym_layer = CosmoSacLayer().eval()
    g_asym = torch.linspace(-0.025, 0.030, 51)
    sm_a, sn_a = g_asym.view(-1, 1), g_asym.view(1, -1)
    dw_asym = 0.5 * asym_layer.alpha_prime * (sm_a + sn_a) ** 2 + asym_layer.c_hb * torch.clamp(
        torch.maximum(sm_a, sn_a) - asym_layer.sigma_hb, min=0.0) * torch.clamp(
        torch.minimum(sm_a, sn_a) + asym_layer.sigma_hb, max=0.0)
    out["scope_conditions"] = {
        "typed_2010_kernel_residual_by_T": cond["blockwise"],
        "whole_153_reversal_residual_by_T": cond["whole_grid_reversal_is_not_a_symmetry"],
        "asymmetric_grid_residual": float(
            (dw_asym - dw_asym.flip(0).flip(1)).abs().max()),
        "reading": (
            "the invariance holds for the modern typed kernel exactly, under the BLOCKWISE flip "
            "only, and only on a grid symmetric about zero; the whole-grid reversal permutes the "
            "profile types and an off-centre grid makes the flip unrepresentable as a bin "
            "permutation, and neither is the symmetry being claimed"
        ),
    }

    # ---- 2. mirroring the whole corpus is unobservable -------------------------------------
    k = 64
    i2 = rng.choice(n_mol, size=k, replace=False)
    i1 = rng.choice(n_mol, size=k, replace=False)
    p2, p1 = (torch.tensor(P[i2], dtype=torch.float32),
              torch.tensor(P[i1], dtype=torch.float32))
    a2, a1 = (torch.tensor(area[i2], dtype=torch.float32),
              torch.tensor(area[i1], dtype=torch.float32))
    T = torch.full((k,), 298.15)
    with torch.no_grad():
        y = layer._residual_ln_gamma2(p2, p1, a2, a1, torch.zeros(k), T, n_iter=30)
        ym = layer._residual_ln_gamma2(
            p2.flip(-1), p1.flip(-1), a2, a1, torch.zeros(k), T, n_iter=30)
    out["global_mirror"] = {
        "n_pairs": k,
        "mean_abs_ln_gamma": float(y.abs().mean()),
        "max_abs_change_under_mirror": float((y - ym).abs().max()),
    }

    # ---- 3. is one molecule's own branch identifiable from its measured pairs? ---------------
    # THE STATISTIC, and the first version of this got it wrong. Comparing a per-pair MEDIAN
    # displacement against a per-observation noise floor throws away the replication that
    # identifiability turns on: a flip invisible in 55 solvents and glaring in 5 is identifiable,
    # and a median calls it invisible. For y_j = f_j + eps_j with eps ~ N(0, sigma^2), the
    # log-likelihood ratio between the two branches is |d|^2 / 2 sigma^2, so the statistic is the
    # ROOT-SUM-SQUARE displacement in units of sigma, z = ||d|| / sigma, over the solvents the
    # molecule is actually measured in.
    # AND THE PER-SOLUTE CONSTANT IS PROJECTED OUT. A displacement common to every solvent of one
    # solute is absorbed free by the crystal head -- that is this paper's own compensation
    # finding -- so it does not identify anything. d is centred before the norm is taken.
    # COVERAGE IS THE POINT. The corpus gives a solute a median of 9 distinct solvents in train
    # and 5 in test, with 26.5% of test solutes at two or fewer, so the fraction is reported
    # against S rather than at one generous S=60.
    # BOTH FACTORS ARE RESAMPLED. The first version drew the molecule set once outside the loop,
    # so its spread moved only the partner factor and understated the uncertainty.
    asym = np.abs(shape - shape[:, ::-1]).sum(1)
    q_edges = np.quantile(asym, [0, 0.25, 0.5, 0.75, 1.0])

    def displacement(si, pj, alt_profile):
        """centred (ln gamma of the alternative) - (ln gamma of the molecule), over pj solvents"""
        n = len(pj)
        part = torch.tensor(P[pj], dtype=torch.float32)
        ap = torch.tensor(area[pj], dtype=torch.float32)
        a = float(area[si])

        def lng(p_np):
            pp = torch.tensor(np.repeat(p_np[None, :], n, axis=0), dtype=torch.float32)
            return torch.cat([
                layer._residual_ln_gamma2(pp, part, torch.full((n,), a), ap, torch.zeros(n),
                                          torch.full((n,), float(t)), n_iter=30)
                for t in TEMPS])

        d = (lng(alt_profile) - lng(P[si])).numpy()
        return d - d.mean()

    def matched_shift(si):
        """a WRONG profile of the same L1 size as the flip, to test specificity: rigid bin shift,
        the shift chosen so ||p_shift - p||_1 is closest to ||Jp - p||_1."""
        p = P[si]
        target = np.abs(p[::-1] - p).sum()
        best, best_gap = None, np.inf
        for k in range(1, 26):
            for s in (k, -k):
                q = np.roll(p, s)
                gap = abs(np.abs(q - p).sum() - target)
                if gap < best_gap:
                    best, best_gap = q, gap
        return best

    draws = []
    with torch.no_grad():
        for _ in range(N_PARTNER_DRAWS):
            picks = rng.choice(n_mol, size=N_MOLECULES, replace=False)
            cell = {"n_by_S": {}}
            for S in COVERAGE_S:
                zf, zs, aq = [], [], []
                for si in picks:
                    pj = rng.choice(n_mol, size=S, replace=False)
                    zf.append(float(np.linalg.norm(displacement(si, pj, P[si][::-1].copy()))))
                    zs.append(float(np.linalg.norm(displacement(si, pj, matched_shift(si)))))
                    aq.append(float(asym[si]))
                zf, zs, aq = np.array(zf), np.array(zs), np.array(aq)
                row = {"median_rss_flip": float(np.median(zf)),
                       "median_rss_matched_shift": float(np.median(zs))}
                for sig in NOISE_SIGMAS:
                    und_f, und_s = zf / sig < Z_DETECT, zs / sig < Z_DETECT
                    row[f"sigma_{sig}"] = {
                        "fraction_flip_undetectable": float(und_f.mean()),
                        "fraction_matched_shift_undetectable": float(und_s.mean()),
                        "by_own_asymmetry_quartile": [
                            float(und_f[(aq >= q_edges[q]) & (aq <= q_edges[q + 1] if q == 3
                                                              else aq < q_edges[q + 1])].mean())
                            for q in range(4)],
                    }
                cell["n_by_S"][str(S)] = row
            draws.append(cell)

    def over_draws(S, path):
        v = []
        for d in draws:
            node = d["n_by_S"][str(S)]
            for k in path:
                node = node[k]
            v.append(node)
        v = np.array(v, dtype=float)
        return {"median_over_draws": float(np.median(v)), "min": float(v.min()),
                "max": float(v.max())}

    out["single_molecule_flip"] = {
        "statistic": (
            "z = ||d|| / sigma where d is the per-solvent displacement in ln gamma under the "
            "flip, CENTRED (the per-solute constant is absorbed free by the crystal head); "
            f"a branch counts as unidentifiable when z < {Z_DETECT}"
        ),
        "n_molecules_per_draw": N_MOLECULES,
        "n_draws": N_PARTNER_DRAWS,
        "coverage_S": COVERAGE_S,
        "coverage_note": (
            "the corpus gives a solute a median of 9 distinct solvents in train and 5 in test, "
            "and 26.5% of test solutes have two or fewer"
        ),
        "noise_sigmas_ln": NOISE_SIGMAS,
        "by_coverage": {
            str(S): {
                "median_rss_flip": over_draws(S, ["median_rss_flip"]),
                "median_rss_matched_shift": over_draws(S, ["median_rss_matched_shift"]),
                **{f"sigma_{sig}": {
                    "fraction_flip_undetectable": over_draws(
                        S, [f"sigma_{sig}", "fraction_flip_undetectable"]),
                    "fraction_matched_shift_undetectable": over_draws(
                        S, [f"sigma_{sig}", "fraction_matched_shift_undetectable"]),
                    "top_asymmetry_quartile_flip_undetectable": {
                        "median_over_draws": float(np.median([
                            d["n_by_S"][str(S)][f"sigma_{sig}"]["by_own_asymmetry_quartile"][3]
                            for d in draws])),
                        "min": float(np.min([
                            d["n_by_S"][str(S)][f"sigma_{sig}"]["by_own_asymmetry_quartile"][3]
                            for d in draws])),
                        "max": float(np.max([
                            d["n_by_S"][str(S)][f"sigma_{sig}"]["by_own_asymmetry_quartile"][3]
                            for d in draws])),
                    },
                } for sig in NOISE_SIGMAS},
            } for S in COVERAGE_S},
        "specificity_control": (
            "the matched-shift arm is a WRONG profile of the same L1 size as the flip. It is the "
            "arm that decides whether charge conjugation is a special direction or whether the "
            "closure is simply insensitive to the profile; without it the flip fraction means "
            "nothing on its own."
        ),
        "per_draw": draws,
    }

    # ---- 4. intersecting parity-even kernels does not help ---------------------------------
    ones = np.ones(51) / np.sqrt(51)
    Q, _ = np.linalg.qr(np.eye(51) - np.outer(ones, ones))
    Tang, _ = np.linalg.qr(Q[:, :50] - ones[:, None] * (ones @ Q[:, :50]))
    donor = (grid.numpy() < -layer.sigma_hb)
    off = ~donor
    B = np.zeros((51, int(off.sum())))
    B[np.where(off)[0], np.arange(int(off.sum()))] = 1.0
    B = Tang.T @ B

    variants = []
    for s_hb in (0.0064, 0.0084, 0.0104):
        for c_hb in (85580.0, 42790.0):
            for ap_ in (16466.72, 8233.36):
                L = CosmoSacLayer().eval()
                a_, b_ = L.sigma_grid.view(-1, 1), L.sigma_grid.view(1, -1)
                L.delta_w_base = 0.5 * ap_ * (a_ + b_) ** 2 + c_hb * torch.clamp(
                    torch.maximum(a_, b_) - s_hb, min=0.0) * torch.clamp(
                    torch.minimum(a_, b_) + s_hb, max=0.0)
                variants.append(L)

    def jac(L, si, idx):
        a = float(area[si])
        s = torch.tensor(shape[si], dtype=torch.float32, requires_grad=True)
        pp = torch.tensor(P[idx], dtype=torch.float32)
        aa = torch.tensor(area[idx], dtype=torch.float32)
        n = len(idx)
        rowsj = []
        for t in TEMPS:
            yv = L._residual_ln_gamma2((s * a).unsqueeze(0).expand(n, -1), pp,
                                       torch.full((n,), a), aa, torch.zeros(n),
                                       torch.full((n,), float(t)), n_iter=30)
            for r in range(n):
                g, = torch.autograd.grad(yv[r], s, retain_graph=True)
                rowsj.append(g.detach().numpy().copy())
        return np.stack(rowsj) @ Tang

    idx60 = rng.choice(n_mol, size=60, replace=False)
    inter = []
    for si in rng.choice(n_mol, size=3, replace=False):
        d = np.zeros(51)
        d[donor] = 1.0 / donor.sum()
        d = Tang.T @ (d - shape[si])
        d /= np.linalg.norm(d)
        row = {"solute": smiles[si], "residual_by_n_kernels": {}}
        for kk in (1, 2, 4, 12):
            J = np.concatenate([jac(L, si, idx60) for L in variants[:kk]], axis=0)
            c, *_ = np.linalg.lstsq(J @ B, -(J @ d), rcond=None)
            row["residual_by_n_kernels"][str(kk)] = float(
                np.linalg.norm(J @ B @ c + J @ d) / np.linalg.norm(J @ d))
        inter.append(row)
    out["parity_even_kernel_intersection"] = {
        "n_variants": len(variants),
        "grid": "sigma_hb in {0.0064,0.0084,0.0104} x c_hb in {85580,42790} x alpha' in {16466.72,8233.36}",
        "what_is_measured": (
            "min over corrections supported OUTSIDE the donor window of the residual of J(d+c), "
            "relative to |J d|; d moves mass into the donor window"
        ),
        "per_solute": inter,
        "reading": (
            "stacking twelve kernels leaves the residual at the same order as one, because every "
            "variant is parity-even and intersecting their null spaces cannot break a symmetry "
            "they all share"
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    kr = out["kernel"]
    print(f"  kernel parity residual {kr['max_abs_dw_minus_JdwJ']:.3e} against float32 eps*|dw| "
          f"{kr['float32_eps_times_max_abs_dw']:.3e}")
    gm = out["global_mirror"]
    print(f"  global mirror moves ln gamma by at most {gm['max_abs_change_under_mirror']:.3e} "
          f"(|ln gamma| mean {gm['mean_abs_ln_gamma']:.3f})")
    sf = out["single_molecule_flip"]
    print(f"  branch identifiability, z = ||d||/sigma < {Z_DETECT}, over {sf['n_draws']} draws "
          f"of {sf['n_molecules_per_draw']} molecules")
    for sig in NOISE_SIGMAS:
        print(f"    sigma = {sig} ln")
        for S in COVERAGE_S:
            c = sf["by_coverage"][str(S)][f"sigma_{sig}"]
            f_, m_ = c["fraction_flip_undetectable"], c["fraction_matched_shift_undetectable"]
            q4 = c["top_asymmetry_quartile_flip_undetectable"]
            print(f"      S={S:<3} flip undetectable {f_['median_over_draws']:6.1%} "
                  f"[{f_['min']:.1%}, {f_['max']:.1%}]   "
                  f"matched wrong profile {m_['median_over_draws']:6.1%} "
                  f"[{m_['min']:.1%}, {m_['max']:.1%}]   "
                  f"top-asym quartile {q4['median_over_draws']:6.1%} "
                  f"[{q4['min']:.1%}, {q4['max']:.1%}]")
    for r in out["parity_even_kernel_intersection"]["per_solute"]:
        print(f"  intersection {r['solute'][:26]:<28} "
              + "  ".join(f"k={k}:{v:.4f}" for k, v in r["residual_by_n_kernels"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
