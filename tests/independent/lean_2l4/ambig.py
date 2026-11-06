import sys, json
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from fractions import Fraction
from su2plaq.circuits.twelve import build_UE
from su2plaq.lean import certify as C, exact as E
enc = C._encoding()
for (a, b, note) in ((0.37, 0.61, "nominal"), (0.5, 0.25, "alpha/beta = 2 (ambiguous)"), (0.25, 0.5, "alpha/beta = 1/2"), (0.5, 0.5, "alpha = beta")):
    qc = build_UE(a, with_outer=True)
    ang = float(qc.data[0].operation.params[0])
    cls = C._classify_angle(ang, a, b)
    r = C.certify_circuit_kind(qc, enc, "UE", a, b, 1, out_dir="certs_amb")
    print(f"alpha={a} beta={b} ({note}): gate angle {ang:.5f} -> (r_alpha,r_beta)={tuple(map(str,cls))}; status={r.status} reason={r.reason[:80]!r}")
# Check float-agreement statement: the circuit is correct numerically (identity check at nominal angles) irrespective
