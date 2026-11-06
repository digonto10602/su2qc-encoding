import sys, time, json, os, subprocess
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.circuits.twelve import build_UE, build_UB, build_step
from su2plaq.lean import certify as C
enc = C._encoding()
a, b = 0.37, 0.61
out = {}
os.makedirs("certs", exist_ok=True)
for kind, order, mk in (("UE",1,lambda: build_UE(a, with_outer=True)), ("UB",1,lambda: build_UB(b, with_outer=True)),
                        ("step",1,lambda: build_step(a,b,1,with_outer=True)), ("step",2,lambda: build_step(a,b,2,with_outer=True))):
    t0 = time.time(); qc = mk()
    res = C.certify_circuit_kind(qc, enc, kind, a, b, order, out_dir="certs")
    tot = time.time() - t0
    t1 = time.time()
    r = subprocess.run(["/home/digimonk/Projects/su2qc-encoding/lean/.lake/build/bin/su2plaq_cert", "check", res.cert_path], capture_output=True, text=True) if res.cert_path else None
    out[f"{kind}{order}"] = dict(status=res.status, reason=res.reason[:200], cert=res.cert_path, total_s=round(tot,1), bare_check_s=round(time.time()-t1,1), bare_out=r.stdout.strip() if r else None, n_gates=len(qc.data))
    print(kind, order, out[f"{kind}{order}"], os.getloadavg(), flush=True)
json.dump(out, open("certs_summary.json","w"), indent=1)
