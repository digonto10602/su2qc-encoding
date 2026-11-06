import sys, json, time
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from fractions import Fraction
from su2plaq.circuits.twelve import build_UE, build_UB, build_step
from su2plaq.lean import certify as C
enc = C._encoding()
rows = []
for (a, b) in ((0.5, 0.25), (0.25, 0.5), (0.5, 0.5), (0.3, 0.9), (0.9, 0.3), (0.37, 0.61)):
    for kind, mk in (("UE", lambda a, b: build_UE(a, with_outer=True)), ("UB", lambda a, b: build_UB(b, with_outer=True)), ("step", lambda a, b: build_step(a, b, 1, with_outer=True))):
        t = time.time()
        r = C.certify_circuit_kind(mk(a, b), enc, kind, a, b, 1, out_dir="certs_amb2")
        rows.append(dict(alpha=a, beta=b, kind=kind, status=r.status, reason=r.reason[:70], s=round(time.time() - t, 1)))
        print(f"alpha={a} beta={b} (a/b={Fraction(a)/Fraction(b):.3g}) {kind:4s}: {r.status:9s} {r.reason[:70]!r} {time.time()-t:.0f}s", flush=True)
json.dump(rows, open("ambig2.json", "w"), indent=1)
