import sys, time, json, pathlib
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.circuits.twelve import build_UE, build_UB, build_step
from su2plaq.lean import certify as C
enc = C._encoding()
a, b = 0.37, 0.61
out = {}
for kind, order, mk in (("UE",1,lambda: build_UE(a, with_outer=True)), ("UB",1,lambda: build_UB(b, with_outer=True)),
                        ("step",1,lambda: build_step(a,b,1,with_outer=True)), ("step",2,lambda: build_step(a,b,2,with_outer=True))):
    t0 = time.time()
    qc = mk()
    t1 = time.time()
    res = C.certify_circuit_kind(qc, enc, kind, a, b, order, out_dir="certs")
    out[f"{kind}{order}"] = dict(status=res.status, reason=res.reason[:200], cert=res.cert_path, total_s=round(time.time()-t0,1), n_gates=len(qc.data))
    print(kind, order, out[f"{kind}{order}"], flush=True)
json.dump(out, open("certs_summary.json","w"), indent=1)
