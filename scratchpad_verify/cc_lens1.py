"""Lens-1 audit of the charge-conjugation gauge claim. Read-only; writes nothing."""
from __future__ import annotations
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import sys, csv
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.layers import CosmoSacLayer, CosmoSac2010Layer  # noqa: E402

torch.manual_seed(0)

print("=" * 78)
print("A. SYMBOLIC: is the 2002 hb term even under (sm,sn) -> (-sm,-sn)?")
import sympy as sp
sm, sn, s_hb, c = sp.symbols("sm sn s_hb c", real=True)
s_hb_pos = sp.Symbol("s_hb", positive=True)
Max, Min = sp.Max, sp.Min
def hb(a, b, h):
    return c * Max(Max(a, b) - h, 0) * Min(Min(a, b) + h, 0)
expr = sp.simplify(hb(sm, sn, s_hb_pos) - hb(-sm, -sn, s_hb_pos))
print("  simplify(hb(s) - hb(-s)) =", expr)
# exhaustive piecewise check on the sign/threshold cells
import itertools, random
random.seed(0)
bad = 0
for _ in range(200000):
    a = random.uniform(-0.03, 0.03); b = random.uniform(-0.03, 0.03); h = 0.0084
    f = lambda x, y: max(max(x, y) - h, 0.0) * min(min(x, y) + h, 0.0)
    if abs(f(a, b) - f(-a, -b)) > 1e-18:
        bad += 1
print(f"  random float check over 2e5 (sm,sn) draws: violations = {bad}")
# and the swap identity A' = -B, B' = -A
a, b = 0.02, -0.015
h = 0.0084
A = max(max(a, b) - h, 0.0); B = min(min(a, b) + h, 0.0)
A2 = max(max(-a, -b) - h, 0.0); B2 = min(min(-a, -b) + h, 0.0)
print(f"  swap identity: A={A:.6g} B={B:.6g} | A'={A2:.6g} (=-B? {abs(A2+B)<1e-15}) "
      f"B'={B2:.6g} (=-A? {abs(B2+A)<1e-15})")

print()
print("=" * 78)
print("B. 2002 kernel, reproduce the deposit")
L = CosmoSacLayer().eval()
dw = L.delta_w_base
print(f"  grid: n={L.n_bins} min={float(L.sigma_grid.min()):+.4f} max={float(L.sigma_grid.max()):+.4f} "
      f"| grid + flip(grid) max|.| = {float((L.sigma_grid + L.sigma_grid.flip(0)).abs().max()):.3e}")
print(f"  max|dw - JdwJ| = {float((dw - dw.flip(0).flip(1)).abs().max()):.4e}  "
      f"vs f32 eps*|dw|max = {np.finfo(np.float32).eps*float(dw.abs().max()):.4e}")
# float64 version: is the residual exactly zero in exact arithmetic?
g64 = torch.linspace(-0.025, 0.025, 51, dtype=torch.float64)
a_, b_ = g64.view(-1, 1), g64.view(1, -1)
dw64 = 0.5 * 16466.72 * (a_ + b_) ** 2 + 85580.0 * torch.clamp(
    torch.maximum(a_, b_) - 0.0084, min=0.0) * torch.clamp(
    torch.minimum(a_, b_) + 0.0084, max=0.0)
print(f"  float64 residual max|dw - JdwJ| = {float((dw64 - dw64.flip(0).flip(1)).abs().max()):.4e}")

print()
print("=" * 78)
print("C. 2010/dsp closure: is DELTAW even under the BLOCKWISE bin reversal?")
L10 = CosmoSac2010Layer().eval()
n = L10.n_bins
def J10(x, dim=-1):
    """reverse sigma bins WITHIN each of the 3 type blocks (NHB|OH|OT)."""
    sh = list(x.shape)
    return x.reshape(*sh[:dim] if dim == -1 else sh, ).clone() if False else None
def flip_block(x, dim):
    parts = torch.split(x, n, dim=dim)
    return torch.cat([p.flip(dim) for p in parts], dim=dim)
for T in (273.15, 298.15, 323.15):
    W = L10._delta_w(torch.tensor([T]))[0]
    WJ = flip_block(flip_block(W, 0), 1)
    print(f"  T={T}: max|W| = {float(W.abs().max()):.4g}  max|W - JWJ| = "
          f"{float((W - WJ).abs().max()):.4e}  (f32 eps*|W|max = "
          f"{np.finfo(np.float32).eps*float(W.abs().max()):.3e})")
# and each piece separately
print(f"  sumsq   residual: {float((L10.sumsq - flip_block(flip_block(L10.sumsq,0),1)).abs().max()):.3e}")
print(f"  diffsq  residual: {float((L10.diffsq - flip_block(flip_block(L10.diffsq,0),1)).abs().max()):.3e}")
print(f"  signneg residual: {float((L10.sign_neg - flip_block(flip_block(L10.sign_neg,0),1)).abs().max()):.3e}")
print(f"  chb     residual: {float((L10.chb - flip_block(flip_block(L10.chb,0),1)).abs().max()):.3e}")

print()
print("  full 2010 ln_gamma_inf under a global blockwise mirror of every profile:")
B = 32
p2 = torch.rand(B, 3 * n).abs(); p1 = torch.rand(B, 3 * n).abs()
A2 = 100 + 50 * torch.rand(B); A1 = 80 + 40 * torch.rand(B)
p2 = p2 / p2.sum(-1, keepdim=True) * A2.unsqueeze(-1)
p1 = p1 / p1.sum(-1, keepdim=True) * A1.unsqueeze(-1)
V2 = 150 + 50 * torch.rand(B); V1 = 120 + 40 * torch.rand(B)
e2 = 100 + 50 * torch.rand(B); e1 = 90 + 40 * torch.rand(B)
T = torch.full((B,), 298.15)
with torch.no_grad():
    y = L10.ln_gamma_inf(p2, p1, A2, A1, V2, V1, T, e2, e1)
    ym = L10.ln_gamma_inf(flip_block(p2, -1), flip_block(p1, -1), A2, A1, V2, V1, T, e2, e1)
print(f"    mean|ln gamma| = {float(y.abs().mean()):.4f}  max change = {float((y-ym).abs().max()):.3e}")
# what if we mirror WITHOUT respecting type blocks (a naive 153-reversal, which also
# permutes NHB<->OT)?  that is NOT the symmetry and should break.
with torch.no_grad():
    ymn = L10.ln_gamma_inf(p2.flip(-1), p1.flip(-1), A2, A1, V2, V1, T, e2, e1)
print(f"    naive whole-153 reversal (permutes types): max change = {float((y-ymn).abs().max()):.3e}")

print()
print("=" * 78)
print("D. Is the invariance an artefact of the symmetric DISCRETISATION?")
class Cfg:
    pass
def mk(nb, lo, hi):
    c = Cfg(); c.cosmo_sac_n_bins = nb; c.cosmo_sac_sigma_min = lo; c.cosmo_sac_sigma_max = hi
    return CosmoSacLayer(c).eval()
for nb, lo, hi, tag in [(51, -0.025, 0.025, "default, odd, centred"),
                        (50, -0.025, 0.025, "even bin count, centred"),
                        (51, -0.025, 0.030, "asymmetric support"),
                        (51, -0.020, 0.025, "asymmetric support (other side)")]:
    Lx = mk(nb, lo, hi)
    d = Lx.delta_w_base
    r = float((d - d.flip(0).flip(1)).abs().max())
    gr = float((Lx.sigma_grid + Lx.sigma_grid.flip(0)).abs().max())
    print(f"  n={nb} [{lo},{hi}] {tag:34s} max|grid+Jgrid|={gr:.3e}  max|dw-JdwJ|={r:.4e}")

print()
print("=" * 78)
print("E. Does anything else in the physics path see the profile?")
print("  SG combinatorial args: (A2,A1,V2,V1,x2) -- no p. dispersion args: (eps2,eps1,w) -- no p.")
Lc = CosmoSacLayer().eval()
c1 = Lc._combinatorial_ln_gamma2(A2, A1, V2, V1, torch.zeros(B))
print(f"    combinatorial is profile-free by signature -> invariant by construction "
      f"(sample mean {float(c1.mean()):.4f})")

print()
print("=" * 78)
print("F. 2002: global corpus mirror on REAL reference profiles, incl. area & solver path")
PROF = ROOT / "results" / "sigma_profile_artifact" / "sigma_profiles.csv"
with open(PROF) as fh:
    rdr = csv.reader(fh); header = next(rdr)
    rows = [r for r in rdr if len(r) == len(header)]
i_a, i_p = header.index("sigma_area"), header.index("sigma_p_0")
area = np.array([float(r[i_a]) for r in rows])
P = np.array([[float(v) for v in r[i_p:i_p + 51]] for r in rows])
print(f"  reference table: {P.shape[0]} molecules, 51 bins, area mean {area.mean():.1f} A^2")
rng = np.random.default_rng(11)
k = 128
i2 = rng.choice(len(P), k, replace=False); i1 = rng.choice(len(P), k, replace=False)
t2 = torch.tensor(P[i2], dtype=torch.float32); t1 = torch.tensor(P[i1], dtype=torch.float32)
a2 = torch.tensor(area[i2], dtype=torch.float32); a1 = torch.tensor(area[i1], dtype=torch.float32)
Tt = torch.full((k,), 298.15)
with torch.no_grad():
    y = L._residual_ln_gamma2(t2, t1, a2, a1, torch.zeros(k), Tt, n_iter=30)
    ym = L._residual_ln_gamma2(t2.flip(-1), t1.flip(-1), a2, a1, torch.zeros(k), Tt, n_iter=30)
print(f"  mean|ln gamma_res| = {float(y.abs().mean()):.4f}, max = {float(y.abs().max()):.3f}")
print(f"  max change under global mirror = {float((y-ym).abs().max()):.3e}")
# float64 replay of the whole residual pipeline to rule out a roundoff-masked violation
def res64(p2, p1, A2, A1, T, n_iter=60):
    g = torch.linspace(-0.025, 0.025, 51, dtype=torch.float64)
    a_, b_ = g.view(-1, 1), g.view(1, -1)
    W = 0.5 * 16466.72 * (a_ + b_) ** 2 + 85580.0 * torch.clamp(
        torch.maximum(a_, b_) - 0.0084, min=0.0) * torch.clamp(
        torch.minimum(a_, b_) + 0.0084, max=0.0)
    rt = (1.987204e-3 * T).view(-1, 1, 1)
    E = torch.exp((-W.unsqueeze(0) / rt).clamp(-30, 30))
    p2n = p2 / A2.unsqueeze(-1); p1n = p1 / A1.unsqueeze(-1)
    pmix = p1n  # x2 = 0
    def seg(pn):
        gam = torch.ones_like(pn)
        for _ in range(n_iter):
            den = torch.bmm(E, (pn * gam).unsqueeze(-1)).squeeze(-1)
            gam = 0.7 / (den + 1e-10) + 0.3 * gam
            gam = gam.clamp(1e-8, 1e8)
        return torch.log(gam + 1e-10)
    return (A2 / 7.5) * (p2n * (seg(pmix) - seg(p2n))).sum(-1)
d2 = t2.double(); d1 = t1.double()
y64 = res64(d2, d1, a2.double(), a1.double(), Tt.double())
y64m = res64(d2.flip(-1), d1.flip(-1), a2.double(), a1.double(), Tt.double())
print(f"  float64 replay: mean|ln gamma| = {float(y64.abs().mean()):.4f}, "
      f"max change under mirror = {float((y64 - y64m).abs().max()):.3e}")
