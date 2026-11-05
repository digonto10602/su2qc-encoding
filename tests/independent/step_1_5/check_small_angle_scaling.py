"""Target-level: ||T_order1 - T_order2|| vs alpha*beta -> slope 1 (first order in the commutator)."""
import numpy as np, warnings; warnings.filterwarnings("ignore")
from su2plaq.encodings.twelve import TwelveQubit
enc = TwelveQubit()
def d(A, B):
    ov = np.trace(B.conj().T @ A); return float(np.linalg.norm(A - ov / abs(ov) * B, 2))
H = []
for s in (0.2, 0.1, 0.05, 0.025):
    a, b = s, s
    H.append((a * b, d(enc.target("step", a, b, order=1), enc.target("step", a, b, order=2)), d(enc.target("step", a, b, order=2), enc.target("step", a, b, order=1))))
    print(H[-1])
x = np.log([h[0] for h in H]); y = np.log([h[1] for h in H])
print("log-log slope (err vs alpha*beta):", np.polyfit(x, y, 1)[0], "ratio err/(alpha*beta):", [h[1] / h[0] for h in H])
