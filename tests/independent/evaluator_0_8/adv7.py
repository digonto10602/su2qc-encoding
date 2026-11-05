from common import *
from su2plaq.exact.physical import gauss_residual, gauss_residuals_coo
rng = np.random.default_rng(20261104)
kl, al, ref = [], [], []
for t in range(40):
    k = int(rng.integers(0, 433))
    keys = np.asarray(basis.keys[k]).copy(); amps = np.asarray(basis.amps[k]).astype(complex).copy()
    if t % 2:
        extra = rng.integers(0, 5**12, size=30); ea = rng.normal(size=30) + 1j*rng.normal(size=30)
        keys = np.concatenate([keys, extra]); amps = np.concatenate([amps, 0.1*ea])
    else:
        amps = amps * np.exp(1j*rng.uniform(-3, 3))
    # duplicates keys allowed? merge
    uk, inv = np.unique(keys, return_inverse=True); ua = np.zeros(len(uk), complex); np.add.at(ua, inv, amps)
    kl.append(uk); al.append(ua)
    ref.append(gauss_residual(basis, uk, ua))
got = gauss_residuals_coo(basis, kl, al)
d = np.abs(np.array(ref) - got).max()
rec("gauss_residuals_coo vs gauss_residual (20 exact-phase + 20 noisy states)", "<=1e-13", f"max diff {d:.2e}; max noisy residual {max(ref):.3f}", 1e-13, d <= 1e-13)
json.dump(RES, open(OUT+"adv7.json", "w"), indent=1)
