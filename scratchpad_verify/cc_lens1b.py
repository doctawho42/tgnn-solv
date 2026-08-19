from __future__ import annotations
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import sys
from pathlib import Path
import numpy as np, torch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.layers import CosmoSac2010Layer  # noqa: E402

n = 51
L = CosmoSac2010Layer().eval()
g = L.sigma_grid if hasattr(L, "sigma_grid") else torch.linspace(-0.025, 0.025, 51)
gg = torch.linspace(-0.025, 0.025, 51)
print("grid[24:27] =", [f"{v:.3e}" for v in gg[24:27].tolist()])
print("grid[25] exactly zero?", float(gg[25]) == 0.0, " value:", repr(float(gg[25])))
print("grid + Jgrid at 24:27 =", [f"{v:.3e}" for v in (gg + gg.flip(0))[24:27].tolist()])

W = L._delta_w(torch.tensor([298.15]))[0]
def fb(x, dim):
    return torch.cat([p.flip(dim) for p in torch.split(x, n, dim=dim)], dim=dim)
R = (W - fb(fb(W, 0), 1)).abs()
idx = (R > 1e-4).nonzero()
rows = sorted(set((idx[:, 0] % n).tolist()))
cols = sorted(set((idx[:, 1] % n).tolist()))
print(f"violating entries: {idx.shape[0]}; within-block ROW indices involved: {rows}; COL indices: {cols}")
print(f"max residual {float(R.max()):.4f};  c_OH_OH*(0.025)^2 = {4013.78*0.025**2:.4f}")

# exact-arithmetic 2010 kernel with a bitwise antisymmetric float64 grid
g64 = torch.linspace(-0.025, 0.025, 51, dtype=torch.float64)
g64 = 0.5 * (g64 - g64.flip(0))          # force exact antisymmetry
g64[25] = 0.0
cat = g64.repeat(3)
sm, sn = cat.view(-1, 1), cat.view(1, -1)
chb = L.chb.double()
c_ES = 6525.69 + 1.4859e8 / 298.15 ** 2
W64 = c_ES * (sm + sn) ** 2 - chb * (sm - sn) ** 2 * (sm * sn < 0).double()
print(f"float64, exactly antisymmetric grid: max|W| = {float(W64.abs().max()):.4f}  "
      f"max|W - JWJ| = {float((W64 - fb(fb(W64, 0), 1)).abs().max()):.3e}")

# even bin count -> no zero bin at all
class C: pass
c = C(); c.cosmo_sac_n_bins = 50
L50 = CosmoSac2010Layer(c).eval()
n = 50
W50 = L50._delta_w(torch.tensor([298.15]))[0]
print(f"n_bins=50 (no sigma=0 bin), float32: max|W-JWJ| = "
      f"{float((W50 - fb(fb(W50,0),1)).abs().max()):.3e}  (max|W| {float(W50.abs().max()):.3f})")

# how big is the zero-bin artefact on ln gamma, and does it vanish at even bins?
n = 51
torch.manual_seed(0)
B = 64
def mk(L, nb):
    p2 = torch.rand(B, 3 * nb); p1 = torch.rand(B, 3 * nb)
    A2 = 100 + 50 * torch.rand(B); A1 = 80 + 40 * torch.rand(B)
    p2 = p2 / p2.sum(-1, True) * A2.unsqueeze(-1); p1 = p1 / p1.sum(-1, True) * A1.unsqueeze(-1)
    return p2, p1, A2, A1
for L_, nb, tag in [(CosmoSac2010Layer().eval(), 51, "n=51 (zero bin present)"),
                    (L50, 50, "n=50 (no zero bin)")]:
    n = nb
    p2, p1, A2, A1 = mk(L_, nb)
    T = torch.full((B,), 298.15)
    with torch.no_grad():
        y = L_.ln_gamma_inf(p2, p1, A2, A1, None, None, T)
        ym = L_.ln_gamma_inf(fb(p2, -1), fb(p1, -1), A2, A1, None, None, T)
    print(f"  {tag}: mean|lng| {float(y.abs().mean()):.4f}  max change under blockwise mirror "
          f"{float((y - ym).abs().max()):.3e}")

# zeroing the zero-bin hb by hand at n=51 -> does invariance return?
n = 51
L51 = CosmoSac2010Layer().eval()
sn_ = L51.sign_neg.clone()
for b in range(3):
    sn_[b * 51 + 25, :] = 0.0
    sn_[:, b * 51 + 25] = 0.0
L51.sign_neg.copy_(sn_)
p2, p1, A2, A1 = mk(L51, 51)
T = torch.full((B,), 298.15)
with torch.no_grad():
    y = L51.ln_gamma_inf(p2, p1, A2, A1, None, None, T)
    ym = L51.ln_gamma_inf(fb(p2, -1), fb(p1, -1), A2, A1, None, None, T)
print(f"  n=51 with the sigma=0 row/col of sign_neg zeroed: max change {float((y-ym).abs().max()):.3e}"
      f"  (mean|lng| {float(y.abs().mean()):.4f})")
